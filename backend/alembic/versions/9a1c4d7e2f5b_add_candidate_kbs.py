"""Add candidate_kbs table for persisted Candidate Knowledge Base

Revision ID: 9a1c4d7e2f5b
Revises: 8f7e2a1b9c3d
Create Date: 2026-10-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9a1c4d7e2f5b"
down_revision: Union[str, None] = "8f7e2a1b9c3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "candidate_kbs",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("change_note", sa.String(length=512), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_candidate_kbs_user_id"), "candidate_kbs", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_candidate_kbs_is_active"), "candidate_kbs", ["is_active"], unique=False
    )
    op.create_index(op.f("ix_candidate_kbs_id"), "candidate_kbs", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_candidate_kbs_id"), table_name="candidate_kbs")
    op.drop_index(op.f("ix_candidate_kbs_is_active"), table_name="candidate_kbs")
    op.drop_index(op.f("ix_candidate_kbs_user_id"), table_name="candidate_kbs")
    op.drop_table("candidate_kbs")