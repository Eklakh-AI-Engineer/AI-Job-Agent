from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid


class Job(BaseModel):
    id: str = None  # UUID, assigned on creation
    source: str
    source_job_id: str
    company: Optional[str] = None
    title: Optional[str] = None
    location: Optional[str] = None
    work_mode: Optional[str] = None  # remote/hybrid/onsite
    job_url: str
    application_url: Optional[str] = None
    description: Optional[str] = None
    posted_date: Optional[datetime] = None
    closing_date: Optional[datetime] = None
    experience_requirement: Optional[str] = None
    education_requirement: Optional[str] = None
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    eligibility: Optional[str] = None
    compensation: Optional[str] = None
    internship_information: Optional[str] = None
    discovered_at: datetime
    updated_at: Optional[datetime] = None
    raw_source_reference: Optional[dict] = None

    def model_post_init(self, __context):
        if self.id is None:
            self.id = str(uuid.uuid4())
