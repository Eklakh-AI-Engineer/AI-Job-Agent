"""
backend/app/agents/workday.py

Workday job board discovery agent.
"""

import asyncio
import logging
import re
from typing import List, Dict, Any
from urllib.parse import urlparse, urljoin, parse_qs
from playwright.async_api import async_playwright
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class WorkdayDiscoveryAgent:
    """
    Agent responsible for discovering job postings from Workday job boards.
    """

    def __init__(self, board_url: str):
        self.board_url = board_url
        self.company_name = self._extract_company_name(board_url)

    def _extract_company_name(self, board_url: str) -> str:
        """Extract company name from Workday board URL."""
        # https://{company}.wd1.myworkdayjobs.com/{career_site}
        parsed = urlparse(board_url)
        host_parts = parsed.netloc.split(".")
        if host_parts:
            return host_parts[0].replace("-", " ").title()
        return "Unknown"

    def _extract_source_job_id(self, job_url: str) -> str:
        """Extract Workday job ID from URL."""
        # Workday job URLs contain jobId parameter or path
        match = re.search(r"/job/([^/]+)", job_url)
        if match:
            return f"wd_{match.group(1)}"
        # Check query params
        parsed = urlparse(job_url)
        params = parse_qs(parsed.query)
        if "jobId" in params:
            return f"wd_{params['jobId'][0]}"
        # Fallback: hash of URL
        return f"wd_{abs(hash(job_url)) % 1000000}"

    async def discover_jobs(self) -> List[Dict[str, Any]]:
        """
        Scrapes a Workday job board for active job listings.
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

                # Workday uses specific structure - jobs are often in a table or list
                # Try multiple selectors for different Workday configurations
                job_links = await page.query_selector_all('a[data-automation-id="jobTitle"]')
                if not job_links:
                    job_links = await page.query_selector_all('a[href*="/job/"]')
                
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
                    title = await link.inner_text()
                    title = title.strip() if title else "Unknown Title"

                    # Get location - usually in a sibling cell
                    location = ""
                    # Try to find parent row and get location cell
                    row = await link.evaluate_handle("el => el.closest('tr')")
                    if row:
                        location_cell = await row.query_selector('[data-automation-id="location"]')
                        if not location_cell:
                            location_cell = await row.query_selector('td:nth-child(2)')
                        if location_cell:
                            location = (await location_cell.inner_text()).strip()

                    source_job_id = self._extract_source_job_id(url)

                    jobs.append(
                        {
                            "title": title,
                            "url": url,
                            "location": location,
                            "source": "Workday",
                            "company": self.company_name,
                            "source_job_id": source_job_id,
                            "application_url": url,
                            "work_mode": self._infer_work_mode(location),
                            "raw_source_reference": {
                                "board_url": self.board_url,
                                "discovered_from": "workday_board",
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
    board_url = "https://company.wd1.myworkdayjobs.com/careers"
    agent = WorkdayDiscoveryAgent(board_url)
    print(f"Discovering jobs on {board_url}...")
    jobs = await agent.discover_jobs()
    print(f"Found {len(jobs)} jobs.")
    for j in jobs[:5]:
        print(j)


if __name__ == "__main__":
    asyncio.run(test_agent())