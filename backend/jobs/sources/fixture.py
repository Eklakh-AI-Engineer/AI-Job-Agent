from backend.jobs.sources.base import JobSource
from typing import List


class FixtureSource(JobSource):
    @property
    def source_name(self) -> str:
        return "fixture"

    def fetch(self) -> List[dict]:
        return [
            {
                "source_id": "job_1",
                "title": " Software Engineer ",
                "company": " Tech Corp ",
                "location": " San Francisco, CA ",
                "mode": "hybrid",
                "url": "https://techcorp.com/jobs/1",
                "apply": "https://techcorp.com/apply/1",
            },
            {
                "source_id": "job_2",
                "title": "Data Scientist",
                "company": "Data Inc",
                "location": "New York",
                "url": "data-inc.com/jobs/2",  # Malformed URL
            },
            {
                "source_id": "job_3",
                "title": "Product Manager",
                "company": "Product LLC",
                "location": "Remote",
                "url": "https://productllc.com/jobs/3",
                # missing optional fields
            },
            {
                "source_id": "job_1",  # duplicate of job 1 by source_id
                "title": " Software Engineer ",
                "company": " Tech Corp ",
                "location": " San Francisco, CA ",
                "mode": "hybrid",
                "url": "https://techcorp.com/jobs/1",
                "apply": "https://techcorp.com/apply/1",
            },
            {
                "source_id": "job_5",
                "title": "Software Engineer",  # same title as job_1, different company
                "company": "Another Tech",
                "location": "Remote",
                "url": "https://anothertech.com/jobs/5",
            },
        ]
