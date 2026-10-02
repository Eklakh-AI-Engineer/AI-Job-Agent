import asyncio
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from app.core.config import get_settings

settings = get_settings()


class GreenhouseDiscoveryAgent:
    """
    Agent responsible for discovering job postings from Greenhouse job boards.
    """

    def __init__(self, board_url: str):
        self.board_url = board_url

    async def discover_jobs(self) -> List[Dict[str, Any]]:
        """
        Scrapes a Greenhouse job board for active job listings.
        Returns a list of dictionaries containing title, url, location, and department.
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

                # Greenhouse typically loads job postings within sections or divs with class 'level-0'
                # or a specific section for departments.

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
                        from urllib.parse import urlparse

                        parsed_url = urlparse(self.board_url)
                        url = f"{parsed_url.scheme}://{parsed_url.netloc}{url}"

                    jobs.append(
                        {
                            "title": title,
                            "url": url,
                            "location": location,
                            "source": "Greenhouse",
                            "company": self.board_url.rstrip("/")
                            .split("/")[-1]
                            .capitalize(),
                        }
                    )

            except Exception as e:
                print(f"Error discovering jobs on {self.board_url}: {e}")
            finally:
                await browser.close()

        return jobs

    async def save_jobs(self, jobs: List[Dict[str, Any]], db_session):
        """
        Saves discovered jobs to the database. Ignores duplicates based on URL.
        """
        from app.models.job import JobPosting
        from sqlalchemy.dialects.postgresql import insert

        if not jobs:
            return

        values = []
        for j in jobs:
            values.append(
                {
                    "title": j["title"],
                    "company": j.get("company", "Unknown"),
                    "location": j["location"],
                    "url": j["url"],
                    "source": j["source"],
                    "job_description": "Pending extraction...",  # To be filled by another task
                }
            )

        stmt = insert(JobPosting).values(values)
        # On conflict do nothing for unique URL constraint
        stmt = stmt.on_conflict_do_nothing(index_elements=["url"])

        await db_session.execute(stmt)
        await db_session.commit()


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
