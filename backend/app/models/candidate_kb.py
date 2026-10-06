from typing import TYPE_CHECKING, Optional, Any
from sqlalchemy import String, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:  # pragma: no cover - import cycle safe
    from app.models.user import User


class CandidateKBRecord(Base):
    """
    Persisted Candidate Knowledge Base for a user.

    The KB is stored as a single JSON document validated against the
    ``CandidateKB`` Pydantic schema on write. Each user may have multiple
    versions for audit purposes; the highest ``version`` is the active KB.
    """

    __tablename__ = "candidate_kbs"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    #: True for the currently active version of the KB.
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    #: Validated CandidateKB serialised as JSON.
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    #: Optional human-readable note explaining the change.
    change_note: Mapped[Optional[str]] = mapped_column(String(512))

    user: Mapped["User"] = relationship("User", back_populates="candidate_kbs")
