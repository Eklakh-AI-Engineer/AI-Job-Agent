"""
backend/app/agents/lever.py

Lever job board discovery agent.
"""

import asyncio
import logging
import re
from typing import List, Dict, Any
from urllib.parse import urlparse, urljoin
from playwright.async_api import async_playwright
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class LeverDiscoveryAgent:
    """
    Agent responsible for discovering job postings from Lever job boards.
    """

    def __init__(self, board_url: str):
        self.board_url = board_url
        self.company_name = self._extract_company_name(board_url)

    def _extract_company_name(self, board_url: str) -> str:
        """Extract company name from Lever board URL."""
        # https://jobs.lever.co/{company_name}
        parsed = urlparse(board_url)
        if parsed.netloc == "jobs.lever.co":
            path_parts = parsed.path.strip("/").split("/")
            if path_parts:
                return path_parts[0].replace("-", " ").title()
        return "Unknown"

    def _extract_source_job_id(self, job_url: str) -> str:
        """Extract Lever job ID from URL."""
        # https://jobs.lever.co/company/abc123
        match = re.search(r"/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})", job_url)
        if match:
            return f"lev_{match.group(1)}"
        # Fallback: hash of URL
        return f"lev_{abs(hash(job_url)) % 1000000}"

    async def discover_jobs(self) -> List[Dict[str, Any]]:
        """
        Scrapes a Lever job board for active job listings.
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
                await page.wait_for_timeout(3000)

                # Lever uses specific selectors for job postings
                # Job links are typically in <a> tags with data-qa="posting-name"
                job_links = await page.query_selector_all('a[data-qa="posting-name"]')
                seen_urls = set()

                for link in job_links:
                    url = await link.get_attribute("href")
                    if not url:
                        continue

                    # Make absolute URL
                    if url.startswith("/"):
                        url = urljoin(self.board_url, url)

                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    # Get title
                    title_elem = await link.query_selector('span[data-qa="posting-name"]')
                    if not title_elem:
                        title_elem = link
                    title = await title_elem.inner_text()
                    title = title.strip() if title else "Unknown Title"

                    # Get location (usually in a sibling element)
                    location = ""
                    location_elem = await link.query_selector('span[data-qa="posting-location"]')
                    if location_elem:
                        location = (await location_elem.inner_text()).strip()

                    # Get commitment (full-time, part-time, etc.)
                    commitment = ""
                    commitment_elem = await link.query_selector('span[data-qa="posting-commitment"]')
                    if commitment_elem:
                        commitment = (await commitment_elem.inner_text()).strip()

                    source_job_id = self._extract_source_job_id(url)

                    jobs.append(
                        {
                            "title": title,
                            "url": url,
                            "location": location,
                            "source": "Lever",
                            "company": self.company_name,
                            "source_job_id": source_job_id,
                            "application_url": url,
                            "work_mode": self._infer_work_mode(location, commitment),
                            "raw_source_reference": {
                                "board_url": self.board_url,
                                "discovered_from": "lever_board",
                                "commitment": commitment,
                            },
                        }
                    )

            except Exception as e:
                logger.error(f"Error discovering jobs on {self.board_url}: {e}")
            finally:
                await browser.close()

        return jobs

    def _infer_work_mode(self, location: str, commitment: str) -> str:
        """Infer work mode from location and commitment strings."""
        text = f"{location} {commitment}".lower()
        if "remote" in text:
            return "remote"
        elif "hybrid" in text:
            return "hybrid"
        return "onsite"


async def test_agent():
    board_url = "https://jobs.lever.co/stripe"
    agent = LeverDiscoveryAgent(board_url)
    print(f"Discovering jobs on {board_url}...")
    jobs = await agent.discover_jobs()
    print(f"Found {len(jobs)} jobs.")
    for j in jobs[:5]:
        print(j)


if __name__ == "__main__":
    asyncio.run(test_agent())