from typing import TYPE_CHECKING, Optional, List
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, JSON, DateTime, UniqueConstraint, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.models.base import Base

if (
    TYPE_CHECKING
):  # pragma: no cover - import cycle safe, resolves at runtime via registry
    from app.models.user import User
    from app.models.document import GeneratedDocument


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

    # Canonical normalized JD fields used by ranking/search. Raw source wording
    # remains preserved above for evidence and auditability.
    normalized_required_skills: Mapped[Optional[List[str]]] = mapped_column(JSON)
    normalized_preferred_skills: Mapped[Optional[List[str]]] = mapped_column(JSON)
    experience_min_years: Mapped[Optional[float]] = mapped_column(Float)
    experience_max_years: Mapped[Optional[float]] = mapped_column(Float)
    education_level: Mapped[Optional[str]] = mapped_column(String(50))
    education_fields: Mapped[Optional[List[str]]] = mapped_column(JSON)
    jd_normalization_version: Mapped[Optional[str]] = mapped_column(String(50))
    jd_normalization_status: Mapped[Optional[str]] = mapped_column(String(50))

    # The vector representation for semantic search
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(1536))

    # Relationships
    applications: Mapped[list["ApplicationStatus"]] = relationship(
        "ApplicationStatus", back_populates="job_posting"
    )
    documents: Mapped[list["GeneratedDocument"]] = relationship(
        "GeneratedDocument", back_populates="job_posting", cascade="all, delete-orphan"
    )


class ApplicationStatus(Base):
    __tablename__ = "application_statuses"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "job_posting_id", name="uq_application_user_job"
        ),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    job_posting_id: Mapped[int] = mapped_column(ForeignKey("job_postings.id"))

    status: Mapped[str] = mapped_column(
        String(50), default="Discovered", index=True
    )  # Discovered, Matched, Approved, Applied, Rejected
    match_score: Mapped[Optional[float]] = mapped_column()

    # Tailored documents
    tailored_resume_s3_key: Mapped[Optional[str]] = mapped_column(String(512))
    cover_letter_s3_key: Mapped[Optional[str]] = mapped_column(String(512))

    # Workflow timestamps
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Submission idempotency + error tracking
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(255), index=True, unique=True
    )
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="job_applications")
    job_posting: Mapped["JobPosting"] = relationship(
        "JobPosting", back_populates="applications"
    )
    events: Mapped[List["ApplicationEvent"]] = relationship(
        "ApplicationEvent",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationEvent.id",
    )


class ApplicationEvent(Base):
    """
    Immutable audit-log entry for every application state change.

    Events are append-only. They record who (actor) changed the status, the
    from/to states, an optional reason, and an idempotency key for external
    submissions that must not be repeated.
    """

    __tablename__ = "application_events"

    application_id: Mapped[int] = mapped_column(
        ForeignKey("application_statuses.id", ondelete="CASCADE"), index=True
    )
    #: e.g. "Discovered", "Matched", "Approved", "Applied", "Rejected"
    from_status: Mapped[Optional[str]] = mapped_column(String(50))
    to_status: Mapped[str] = mapped_column(String(50), index=True)
    #: "user:42", "system", "worker", etc.
    actor: Mapped[str] = mapped_column(String(255), default="system")
    reason: Mapped[Optional[str]] = mapped_column(Text)
    #: For external submissions: dedupe key so a retry is a no-op.
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(255), index=True
    )
    #: Optional structured payload (e.g. external submission response).
    event_meta: Mapped[Optional[dict]] = mapped_column(JSON)

    application: Mapped["ApplicationStatus"] = relationship(
        "ApplicationStatus", back_populates="events"
    )
