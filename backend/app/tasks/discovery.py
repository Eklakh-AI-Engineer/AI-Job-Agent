"""
backend/app/tasks/discovery.py

Celery tasks for job discovery and ingestion.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, Protocol
from dataclasses import dataclass
from abc import ABC, abstractmethod

from app.agents.discovery import GreenhouseDiscoveryAgent
from app.agents.lever import LeverDiscoveryAgent
from app.agents.workday import WorkdayDiscoveryAgent
from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


# Lazy imports for database-dependent functions
def _get_db_session():
    from app.core.database import AsyncSessionLocal
    return AsyncSessionLocal


def _get_bulk_upsert_jobs():
    from app.services.job_discovery_service import bulk_upsert_jobs
    return bulk_upsert_jobs


def _get_job_discovery_create():
    from app.schemas.job_discovery import JobDiscoveryCreate
    return JobDiscoveryCreate


def _get_metrics():
    from app.core.metrics import jobs_ingested_total, celery_tasks_total, celery_task_duration_seconds
    return jobs_ingested_total, celery_tasks_total, celery_task_duration_seconds


# =============================================================================
# Job Source Plugin Architecture
# =============================================================================

class JobSourcePlugin(Protocol):
    """Protocol for job source plugins."""
    
    @property
    def source_name(self) -> str:
        """Unique identifier for this source (e.g., 'greenhouse', 'lever')."""
        ...
    
    @property
    def source_urls(self) -> List[str]:
        """List of URLs to scrape for this source."""
        ...
    
    async def discover_jobs(self, url: str) -> List[Dict[str, Any]]:
        """Discover jobs from a single URL."""
        ...
    
    def normalize_job(self, raw_job: Dict[str, Any], source_url: str) -> Dict[str, Any]:
        """Normalize raw job data to standard format."""
        ...


class BaseJobSource(ABC):
    """Base class for job source implementations."""
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def source_urls(self) -> List[str]:
        pass
    
    @abstractmethod
    async def discover_jobs(self, url: str) -> List[Dict[str, Any]]:
        pass
    
    def normalize_job(self, raw_job: Dict[str, Any], source_url: str) -> Dict[str, Any]:
        """Default normalization - can be overridden by subclasses."""
        return raw_job


class GreenhouseJobSource(BaseJobSource):
    """Greenhouse job board source."""
    
    def __init__(self, board_urls: Optional[List[str]] = None):
        self._board_urls = board_urls or GREENHOUSE_BOARDS
    
    @property
    def source_name(self) -> str:
        return "greenhouse"
    
    @property
    def source_urls(self) -> List[str]:
        return self._board_urls
    
    async def discover_jobs(self, url: str) -> List[Dict[str, Any]]:
        agent = GreenhouseDiscoveryAgent(url)
        return await agent.discover_jobs()
    
    def normalize_job(self, raw_job: Dict[str, Any], source_url: str) -> Dict[str, Any]:
        # Greenhouse agent already returns normalized data
        return raw_job


class LeverJobSource(BaseJobSource):
    """Lever job board source."""
    
    def __init__(self, board_urls: Optional[List[str]] = None):
        self._board_urls = board_urls or LEVER_BOARDS
    
    @property
    def source_name(self) -> str:
        return "lever"
    
    @property
    def source_urls(self) -> List[str]:
        return self._board_urls
    
    async def discover_jobs(self, url: str) -> List[Dict[str, Any]]:
        agent = LeverDiscoveryAgent(url)
        return await agent.discover_jobs()
    
    def normalize_job(self, raw_job: Dict[str, Any], source_url: str) -> Dict[str, Any]:
        # Lever agent already returns normalized data
        return raw_job


class WorkdayJobSource(BaseJobSource):
    """Workday job board source."""
    
    def __init__(self, board_urls: Optional[List[str]] = None):
        self._board_urls = board_urls or WORKDAY_BOARDS
    
    @property
    def source_name(self) -> str:
        return "workday"
    
    @property
    def source_urls(self) -> List[str]:
        return self._board_urls
    
    async def discover_jobs(self, url: str) -> List[Dict[str, Any]]:
        agent = WorkdayDiscoveryAgent(url)
        return await agent.discover_jobs()
    
    def normalize_job(self, raw_job: Dict[str, Any], source_url: str) -> Dict[str, Any]:
        # Workday agent already returns normalized data
        return raw_job


# Pre-configured sources (can be overridden via config)
GREENHOUSE_BOARDS = [
    "https://boards.greenhouse.io/anthropic",
    "https://boards.greenhouse.io/openai",
    "https://boards.greenhouse.io/stripe",
    "https://boards.greenhouse.io/airbnb",
]

LEVER_BOARDS = [
    "https://jobs.lever.co/stripe",
    "https://jobs.lever.co/airbnb",
    "https://jobs.lever.co/coinbase",
    "https://jobs.lever.co/robinhood",
]

WORKDAY_BOARDS = [
    "https://stripe.wd1.myworkdayjobs.com/careers",
    "https://airbnb.wd1.myworkdayjobs.com/careers",
]

# Source registry
SOURCE_REGISTRY: Dict[str, BaseJobSource] = {
    "greenhouse": GreenhouseJobSource(),
    "lever": LeverJobSource(),
    "workday": WorkdayJobSource(),
}


def register_source(source: BaseJobSource) -> None:
    """Register a new job source."""
    SOURCE_REGISTRY[source.source_name] = source
    logger.info(f"Registered job source: {source.source_name}")


def get_source(source_name: str) -> Optional[BaseJobSource]:
    """Get a job source by name."""
    return SOURCE_REGISTRY.get(source_name)


def get_all_sources() -> List[BaseJobSource]:
    """Get all registered job sources."""
    return list(SOURCE_REGISTRY.values())


# =============================================================================
# Discovery Task with Metrics and Error Handling
# =============================================================================

@dataclass
class DiscoveryResult:
    """Result of a single source discovery."""
    source: str
    url: str
    discovered: int
    ingested: int
    duplicates: int
    errors: List[str]
    duration_seconds: float


async def _discover_from_source(source: BaseJobSource, url: str) -> DiscoveryResult:
    """Discover jobs from a single source URL with timing and error handling."""
    start_time = time.time()
    errors: List[str] = []
    discovered = 0
    
    JobDiscoveryCreate = _get_job_discovery_create()
    all_payloads: List[JobDiscoveryCreate] = []
    
    try:
        logger.info(f"Discovering jobs from {source.source_name}: {url}")
        jobs = await source.discover_jobs(url)
        
        if not jobs:
            logger.warning(f"No jobs found on {url}")
            return DiscoveryResult(
                source=source.source_name,
                url=url,
                discovered=0,
                ingested=0,
                duplicates=0,
                errors=[],
                duration_seconds=time.time() - start_time,
            )
        
        discovered = len(jobs)
        
        # Convert to discovery payloads
        for job_data in jobs:
            try:
                # Apply source-specific normalization
                normalized = source.normalize_job(job_data, url)
                
                payload = JobDiscoveryCreate(
                    title=normalized.get("title", ""),
                    company=normalized.get("company", ""),
                    location=normalized.get("location", ""),
                    job_description=normalized.get("job_description", "Pending extraction..."),
                    url=normalized["url"],
                    source=normalized["source"],
                    source_job_id=normalized.get("source_job_id"),
                    application_url=normalized.get("application_url"),
                    work_mode=normalized.get("work_mode"),
                    raw_source_reference=normalized,
                )
                all_payloads.append(payload)
            except Exception as e:
                error_msg = f"Failed to create payload for {job_data.get('url', 'unknown')}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                
    except Exception as e:
        error_msg = f"Failed to discover from {url}: {e}"
        logger.exception(error_msg)
        errors.append(error_msg)
    
    # Bulk upsert
    ingested = 0
    duplicates = 0
    if all_payloads:
        try:
            AsyncSessionLocal = _get_db_session()
            bulk_upsert_jobs = _get_bulk_upsert_jobs()
            async with AsyncSessionLocal() as db:
                result = await bulk_upsert_jobs(db, all_payloads)
                ingested = result["inserted"]
                duplicates = result["duplicates"]
                errors.extend(result.get("errors", []))
        except Exception as e:
            error_msg = f"Failed to ingest jobs from {url}: {e}"
            logger.exception(error_msg)
            errors.append(error_msg)
    
    duration = time.time() - start_time
    return DiscoveryResult(
        source=source.source_name,
        url=url,
        discovered=discovered,
        ingested=ingested,
        duplicates=duplicates,
        errors=errors,
        duration_seconds=duration,
    )


async def _discover_all_sources() -> Dict[str, Any]:
    """Discover jobs from all registered sources."""
    total_discovered = 0
    total_ingested = 0
    total_duplicates = 0
    all_errors: List[str] = []
    source_results: List[Dict[str, Any]] = []
    
    jobs_ingested_total, _, _ = _get_metrics()
    
    for source in get_all_sources():
        for url in source.source_urls:
            result = await _discover_from_source(source, url)
            
            total_discovered += result.discovered
            total_ingested += result.ingested
            total_duplicates += result.duplicates
            all_errors.extend(result.errors)
            
            source_results.append({
                "source": result.source,
                "url": result.url,
                "discovered": result.discovered,
                "ingested": result.ingested,
                "duplicates": result.duplicates,
                "errors": result.errors,
                "duration_seconds": round(result.duration_seconds, 2),
            })
            
            # Record metrics
            jobs_ingested_total.labels(
                source=result.source,
                status="inserted"
            ).inc(result.ingested)
            jobs_ingested_total.labels(
                source=result.source,
                status="duplicate"
            ).inc(result.duplicates)
    
    return {
        "discovered": total_discovered,
        "ingested": total_ingested,
        "duplicates": total_duplicates,
        "errors": all_errors,
        "sources": source_results,
    }


@celery_app.task(
    name="app.tasks.discovery.discover_jobs_task",
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,  # Max 10 minutes
    retry_jitter=True,
)
def discover_jobs_task(self) -> dict:
    """
    Celery task to discover jobs from all configured job sources.
    
    Runs every 6 hours via Celery Beat.
    Includes automatic retry with exponential backoff.
    """
    task_start = time.time()
    logger.info("Starting job discovery task")
    
    try:
        # Run async discovery in sync context
        result = asyncio.run(_discover_all_sources())
        
        duration = time.time() - task_start
        result["duration_seconds"] = round(duration, 2)
        
        # Record task metrics
        _, celery_tasks_total, celery_task_duration_seconds = _get_metrics()
        celery_tasks_total.labels(
            task_name="discover_jobs_task",
            status="success"
        ).inc()
        celery_task_duration_seconds.labels(
            task_name="discover_jobs_task"
        ).observe(duration)
        
        logger.info(f"Job discovery completed in {duration:.2f}s: {result}")
        return result
        
    except Exception as exc:
        duration = time.time() - task_start
        _, celery_tasks_total, celery_task_duration_seconds = _get_metrics()
        celery_tasks_total.labels(
            task_name="discover_jobs_task",
            status="failure"
        ).inc()
        celery_task_duration_seconds.labels(
            task_name="discover_jobs_task"
        ).observe(duration)
        
        logger.exception("Job discovery task failed")
        # Retry will be handled by Celery's autoretry_for
        raise


# =============================================================================
# Manual trigger task for testing
# =============================================================================

@celery_app.task(name="app.tasks.discovery.discover_single_source")
def discover_single_source_task(source_name: str, url: str) -> dict:
    """
    Discover jobs from a single source URL.
    
    Useful for testing new sources or manual triggers.
    """
    source = get_source(source_name)
    if not source:
        raise ValueError(f"Unknown source: {source_name}")
    
    logger.info(f"Manual discovery for {source_name}: {url}")
    result = asyncio.run(_discover_from_source(source, url))
    
    return {
        "source": result.source,
        "url": result.url,
        "discovered": result.discovered,
        "ingested": result.ingested,
        "duplicates": result.duplicates,
        "errors": result.errors,
        "duration_seconds": round(result.duration_seconds, 2),
    }


# =============================================================================
# Utility: Add custom job sources
# =============================================================================

def add_greenhouse_boards(board_urls: List[str]) -> None:
    """Add additional Greenhouse boards to the default source."""
    source = get_source("greenhouse")
    if isinstance(source, GreenhouseJobSource):
        source._board_urls.extend(board_urls)
        logger.info(f"Added {len(board_urls)} Greenhouse boards")


def add_lever_boards(board_urls: List[str]) -> None:
    """Add additional Lever boards to the default source."""
    source = get_source("lever")
    if isinstance(source, LeverJobSource):
        source._board_urls.extend(board_urls)
        logger.info(f"Added {len(board_urls)} Lever boards")


def add_workday_boards(board_urls: List[str]) -> None:
    """Add additional Workday boards to the default source."""
    source = get_source("workday")
    if isinstance(source, WorkdayJobSource):
        source._board_urls.extend(board_urls)
        logger.info(f"Added {len(board_urls)} Workday boards")


if __name__ == "__main__":
    # For manual testing
    import sys
    
    if len(sys.argv) > 2:
        # Test single source
        source_name = sys.argv[1]
        url = sys.argv[2]
        result = asyncio.run(_discover_from_source(get_source(source_name), url))
        print(result)
    else:
        # Test all sources
        result = asyncio.run(_discover_all_sources())
        print(result)