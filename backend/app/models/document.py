from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Text, ForeignKey, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:  # pragma: no cover - import cycle safe
    from app.models.user import User
    from app.models.job import JobPosting


class GeneratedDocument(Base):
    """
    A generated, human-reviewable document (tailored resume or cover letter).

    Documents are always tied to a (user, job) pair. They begin in ``draft``
    state and must be explicitly approved before they can be used for an
    application. Restricted candidate evidence must never be included in a
    generated document; the generator enforces this, and ``used_claim_ids``
    records exactly which candidate claims were referenced.
    """

    __tablename__ = "generated_documents"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    job_posting_id: Mapped[int] = mapped_column(
        ForeignKey("job_postings.id", ondelete="CASCADE"), index=True
    )

    #: "resume" or "cover_letter"
    doc_type: Mapped[str] = mapped_column(String(50), index=True)
    #: draft | approved | rejected
    status: Mapped[str] = mapped_column(String(50), default="draft", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

    #: Human-readable rendered text (the actual document body).
    content: Mapped[str] = mapped_column(Text)
    #: Structured metadata: sections, ATS score, matched keywords, etc.
    meta: Mapped[Optional[dict]] = mapped_column(JSON)
    #: Claim IDs (CLAIM-n) referenced by this document — audit trail.
    used_claim_ids: Mapped[Optional[list]] = mapped_column(JSON)

    #: Storage location of the rendered artifact (if persisted to object store).
    storage_key: Mapped[Optional[str]] = mapped_column(String(1024))

    user: Mapped["User"] = relationship("User", back_populates="documents")
    job_posting: Mapped["JobPosting"] = relationship(
        "JobPosting", back_populates="documents"
    )
