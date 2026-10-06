from typing import TYPE_CHECKING, Optional, List
from sqlalchemy import String, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.models.base import Base

if (
    TYPE_CHECKING
):  # pragma: no cover - import cycle safe, resolves at runtime via registry
    from app.models.user import User


class JobPosting(Base):
    __tablename__ = "job_postings"

    title: Mapped[str] = mapped_column(String(255), index=True)
    company: Mapped[str] = mapped_column(String(255), index=True)
    location: Mapped[Optional[str]] = mapped_column(String(255))
    job_description: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(1024), unique=True)
    source: Mapped[str] = mapped_column(String(100))  # e.g., 'LinkedIn', 'Greenhouse'

    # Extended fields for job discovery pipeline
    source_job_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    application_url: Mapped[Optional[str]] = mapped_column(String(1024))
    work_mode: Mapped[Optional[str]] = mapped_column(String(50))  # remote/hybrid/onsite
    posted_date: Mapped[Optional[str]] = mapped_column(String(100))
    closing_date: Mapped[Optional[str]] = mapped_column(String(100))
    experience_requirement: Mapped[Optional[str]] = mapped_column(Text)
    education_requirement: Mapped[Optional[str]] = mapped_column(Text)
    required_skills: Mapped[Optional[List[str]]] = mapped_column(JSON)
    preferred_skills: Mapped[Optional[List[str]]] = mapped_column(JSON)
    eligibility: Mapped[Optional[str]] = mapped_column(Text)
    compensation: Mapped[Optional[str]] = mapped_column(String(512))
    internship_information: Mapped[Optional[str]] = mapped_column(Text)
    raw_source_reference: Mapped[Optional[dict]] = mapped_column(JSON)

    # The vector representation for semantic search
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(1536))

    # Relationships
    applications: Mapped[list["ApplicationStatus"]] = relationship(
        "ApplicationStatus", back_populates="job_posting"
    )


class ApplicationStatus(Base):
    __tablename__ = "application_statuses"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    job_posting_id: Mapped[int] = mapped_column(ForeignKey("job_postings.id"))

    status: Mapped[str] = mapped_column(
        String(50), default="Discovered"
    )  # Matched, Approved, Applied, Rejected
    match_score: Mapped[Optional[float]] = mapped_column()

    # Tailored documents
    tailored_resume_s3_key: Mapped[Optional[str]] = mapped_column(String(512))
    cover_letter_s3_key: Mapped[Optional[str]] = mapped_column(String(512))

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="job_applications")
    job_posting: Mapped["JobPosting"] = relationship(
        "JobPosting", back_populates="applications"
    )
