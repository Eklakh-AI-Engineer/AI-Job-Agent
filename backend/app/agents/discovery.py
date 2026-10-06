"""
backend/app/agents/discovery.py

Job discovery agents for various job boards.
"""

import asyncio
import logging
import re
from typing import List, Dict, Any
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class GreenhouseDiscoveryAgent:
    """
    Agent responsible for discovering job postings from Greenhouse job boards.
    """

    def __init__(self, board_url: str):
        self.board_url = board_url
        self.company_name = self._extract_company_name(board_url)

    def _extract_company_name(self, board_url: str) -> str:
        """Extract company name from Greenhouse board URL."""
        # boards.greenhouse.io/{company_name}
        parsed = urlparse(board_url)
        path_parts = parsed.path.strip("/").split("/")
        if path_parts:
            return path_parts[0].replace("-", " ").title()
        return "Unknown"

    def _extract_source_job_id(self, job_url: str) -> str:
        """Extract Greenhouse job ID from URL."""
        # https://boards.greenhouse.io/company/jobs/123456
        match = re.search(r"/jobs/(\d+)", job_url)
        if match:
            return f"gh_{match.group(1)}"
        # Fallback: hash of URL
        return f"gh_{abs(hash(job_url)) % 1000000}"

    async def discover_jobs(self) -> List[Dict[str, Any]]:
        """
        Scrapes a Greenhouse job board for active job listings.
        Returns a list of dictionaries with all relevant job data.
        """
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=settings.playwright_headless,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            page = await browser.new_page()

            try:
                await page.goto(self.board_url, wait_until="domcontentloaded")

                # Modern Greenhouse boards (SPA) might not use .posting
                # Wait extra time for React/SPA to render
                await page.wait_for_timeout(3000)

                # Extract all links that contain '/jobs/'
                links = await page.query_selector_all("a")
                seen_urls = set()

                for link in links:
                    url = await link.get_attribute("href")
                    if not url or "/jobs/" not in url:
                        continue

                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    text = await link.inner_text()
                    if not text:
                        continue

                    # Split text by newlines. Usually: Title \n Location
                    parts = [p.strip() for p in text.split("\n") if p.strip()]
                    title = parts[0] if len(parts) > 0 else "Unknown Title"
                    location = parts[1] if len(parts) > 1 else ""

                    # Fix relative URLs
                    if url.startswith("/"):
                        parsed_url = urlparse(self.board_url)
                        url = f"{parsed_url.scheme}://{parsed_url.netloc}{url}"

                    source_job_id = self._extract_source_job_id(url)

                    jobs.append(
                        {
                            "title": title,
                            "url": url,
                            "location": location,
                            "source": "Greenhouse",
                            "company": self.company_name,
                            "source_job_id": source_job_id,
                            "application_url": url,  # Greenhouse uses same URL for apply
                            "work_mode": self._infer_work_mode(location),
                            "raw_source_reference": {
                                "board_url": self.board_url,
                                "discovered_from": "greenhouse_board",
                            },
                        }
                    )

            except Exception as e:
                logger.error(f"Error discovering jobs on {self.board_url}: {e}")
            finally:
                await browser.close()

        return jobs

    def _infer_work_mode(self, location: str) -> str:
        """Infer work mode from location string."""
        location_lower = location.lower()
        if "remote" in location_lower:
            return "remote"
        elif "hybrid" in location_lower:
            return "hybrid"
        return "onsite"


async def test_agent():
    # Example test with a well known public greenhouse board
    board_url = "https://boards.greenhouse.io/anthropic"
    agent = GreenhouseDiscoveryAgent(board_url)
    print(f"Discovering jobs on {board_url}...")
    jobs = await agent.discover_jobs()
    print(f"Found {len(jobs)} jobs.")
    if len(jobs) == 0:
        # Debugging: let's fetch raw html using playwright to see what is going on
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(board_url, wait_until="networkidle")

            # Wait extra time for React/SPA to render
            await page.wait_for_timeout(3000)

            print("ALL LINKS ON PAGE:")
            links = await page.query_selector_all("a")
            for link in links:
                href = await link.get_attribute("href")
                text = await link.inner_text()
                if href and text:
                    print(f"- {text.strip()} -> {href}")

            await browser.close()

    for j in jobs[:5]:
        print(j)


if __name__ == "__main__":
    asyncio.run(test_agent())