from typing import List, Set
from backend.jobs.models import Job

class Deduplicator:
    def __init__(self):
        self.seen_fingerprints: Set[str] = set()

    def _normalize_url(self, url: str) -> str:
        if not url:
            return ""
        return url.rstrip("/").lower()

    def is_duplicate(self, job: Job) -> bool:
        pk = f"{job.source}:{job.source_job_id}"
        if pk in self.seen_fingerprints:
            return True

        if job.application_url:
            app_url = self._normalize_url(job.application_url)
            if app_url in self.seen_fingerprints:
                return True

        if job.job_url:
            job_url = self._normalize_url(job.job_url)
            if job_url in self.seen_fingerprints:
                return True

        if job.title and job.company and job.location:
            fallback = str(hash(job.source + job.title.lower() + job.company.lower() + job.location.lower()))
            if fallback in self.seen_fingerprints:
                return True

        return False

    def mark_seen(self, job: Job):
        self.seen_fingerprints.add(f"{job.source}:{job.source_job_id}")
        
        if job.application_url:
            self.seen_fingerprints.add(self._normalize_url(job.application_url))
            
        if job.job_url:
            self.seen_fingerprints.add(self._normalize_url(job.job_url))
            
        if job.title and job.company and job.location:
            fallback = str(hash(job.source + job.title.lower() + job.company.lower() + job.location.lower()))
            self.seen_fingerprints.add(fallback)

    def filter(self, jobs: List[Job]) -> List[Job]:
        kept = []
        for job in jobs:
            if not self.is_duplicate(job):
                self.mark_seen(job)
                kept.append(job)
        return kept
