"""
backend/app/agents/apify.py

Apify-based job source for API-driven job boards.
"""

import asyncio
import logging
import os
from typing import List, Dict, Any, Optional
import httpx
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class ApifyJobSource:
    """
    Job source that uses Apify actors to scrape job boards.
    Supports LinkedIn, Indeed, Glassdoor, and other Apify-supported boards.
    """

    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or os.getenv("APIFY_API_TOKEN")
        self.base_url = "https://api.apify.com/v2"
        self.client = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=300.0,  # 5 minute timeout for long-running actors
                headers={"Authorization": f"Bearer {self.api_token}"}
            )
        return self.client

    async def run_actor(self, actor_id: str, input_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Run an Apify actor and return the dataset items.
        """
        if not self.api_token:
            raise ValueError("APIFY_API_TOKEN not configured")

        client = await self._get_client()

        # Start the actor run
        run_response = await client.post(
            f"{self.base_url}/acts/{actor_id}/runs",
            json=input_data,
        )
        run_response.raise_for_status()
        run_data = run_response.json()
        run_id = run_data["data"]["id"]

        # Wait for completion
        while True:
            await asyncio.sleep(10)
            status_response = await client.get(f"{self.base_url}/actor-runs/{run_id}")
            status_response.raise_for_status()
            status_data = status_response.json()
            status = status_data["data"]["status"]
            
            if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                break

        if status != "SUCCEEDED":
            raise RuntimeError(f"Actor run failed with status: {status}")

        # Get dataset items
        dataset_id = status_data["data"]["defaultDatasetId"]
        items_response = await client.get(
            f"{self.base_url}/datasets/{dataset_id}/items",
            params={"format": "json", "clean": "true"}
        )
        items_response.raise_for_status()
        return items_response.json()

    async def discover_linkedin_jobs(
        self,
        keywords: List[str],
        locations: List[str],
        max_results: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Discover jobs from LinkedIn using Apify actor.
        """
        # LinkedIn Jobs Scraper actor
        actor_id = "BHzREzZ6zG3eQ5hTZ/linkedin-jobs-scraper"
        
        input_data = {
            "keywords": keywords,
            "locations": locations,
            "maxResults": max_results,
            "datePosted": "pastWeek",  # Only recent jobs
        }
        
        items = await self.run_actor(actor_id, input_data)
        return self._normalize_linkedin_items(items)

    async def discover_indeed_jobs(
        self,
        keywords: List[str],
        locations: List[str],
        max_results: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Discover jobs from Indeed using Apify actor.
        """
        actor_id = "apify/indeed-scraper"
        
        input_data = {
            "keywords": keywords,
            "locations": locations,
            "maxResults": max_results,
        }
        
        items = await self.run_actor(actor_id, input_data)
        return self._normalize_indeed_items(items)

    def _normalize_linkedin_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize LinkedIn job items to standard format."""
        normalized = []
        for item in items:
            try:
                normalized.append({
                    "title": item.get("title", ""),
                    "url": item.get("jobUrl", ""),
                    "location": item.get("location", ""),
                    "source": "LinkedIn",
                    "company": item.get("companyName", ""),
                    "source_job_id": f"li_{item.get('jobId', '')}",
                    "application_url": item.get("applyUrl", item.get("jobUrl", "")),
                    "job_description": item.get("description", ""),
                    "work_mode": self._infer_work_mode(item.get("location", ""), item.get("workplaceType", "")),
                    "posted_date": item.get("postedDate", ""),
                    "raw_source_reference": {
                        "source": "linkedin_apify",
                        "original_data": item,
                    },
                })
            except Exception as e:
                logger.warning(f"Failed to normalize LinkedIn item: {e}")
        return normalized

    def _normalize_indeed_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize Indeed job items to standard format."""
        normalized = []
        for item in items:
            try:
                normalized.append({
                    "title": item.get("title", ""),
                    "url": item.get("jobUrl", ""),
                    "location": item.get("location", ""),
                    "source": "Indeed",
                    "company": item.get("company", ""),
                    "source_job_id": f"ind_{item.get('jobId', '')}",
                    "application_url": item.get("applyUrl", item.get("jobUrl", "")),
                    "job_description": item.get("description", ""),
                    "work_mode": self._infer_work_mode(item.get("location", ""), item.get("jobType", "")),
                    "posted_date": item.get("date", ""),
                    "raw_source_reference": {
                        "source": "indeed_apify",
                        "original_data": item,
                    },
                })
            except Exception as e:
                logger.warning(f"Failed to normalize Indeed item: {e}")
        return normalized

    def _infer_work_mode(self, location: str, job_type: str) -> str:
        """Infer work mode from location and job type."""
        text = f"{location} {job_type}".lower()
        if "remote" in text:
            return "remote"
        elif "hybrid" in text:
            return "hybrid"
        return "onsite"


# Convenience function for Celery task
async def discover_apify_jobs(
    source: str,
    keywords: List[str],
    locations: List[str],
    max_results: int = 100,
) -> List[Dict[str, Any]]:
    """Discover jobs from Apify-supported sources."""
    apify = ApifyJobSource()
    
    if source.lower() == "linkedin":
        return await apify.discover_linkedin_jobs(keywords, locations, max_results)
    elif source.lower() == "indeed":
        return await apify.discover_indeed_jobs(keywords, locations, max_results)
    else:
        raise ValueError(f"Unknown Apify source: {source}")


if __name__ == "__main__":
    # Test with API token
    import sys
    if not os.getenv("APIFY_API_TOKEN"):
        print("Set APIFY_API_TOKEN to test")
        sys.exit(1)
    
    async def test():
        jobs = await discover_apify_jobs("linkedin", ["python", "machine learning"], ["San Francisco", "Remote"], 10)
        print(f"Found {len(jobs)} jobs")
        for j in jobs[:3]:
            print(j)
    
    asyncio.run(test())