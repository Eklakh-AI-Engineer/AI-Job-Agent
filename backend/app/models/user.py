from typing import TYPE_CHECKING, Optional, List
from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if (
    TYPE_CHECKING
):  # pragma: no cover - import cycle safe, resolves at runtime via registry
    from app.models.job import ApplicationStatus
    from app.models.candidate_kb import CandidateKBRecord
    from app.models.document import GeneratedDocument


class User(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))

    # Store JSON representation of their resume/profile data for the matching agent
    profile_data: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    job_applications: Mapped[List["ApplicationStatus"]] = relationship(
        "ApplicationStatus", back_populates="user"
    )
    candidate_kbs: Mapped[List["CandidateKBRecord"]] = relationship(
        "CandidateKBRecord", back_populates="user", cascade="all, delete-orphan"
    )
    documents: Mapped[List["GeneratedDocument"]] = relationship(
        "GeneratedDocument", back_populates="user", cascade="all, delete-orphan"
    )
