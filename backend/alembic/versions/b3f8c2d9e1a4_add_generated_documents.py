"""Add generated_documents table for resume/cover-letter generation

Revision ID: b3f8c2d9e1a4
Revises: 9a1c4d7e2f5b
Create Date: 2026-10-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b3f8c2d9e1a4"
down_revision: Union[str, None] = "9a1c4d7e2f5b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "generated_documents",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("job_posting_id", sa.Integer(), nullable=False),
        sa.Column("doc_type", sa.String(length=50), nullable=False),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default="draft"
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("used_claim_ids", sa.JSON(), nullable=True),
        sa.Column("storage_key", sa.String(length=1024), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["job_posting_id"], ["job_postings.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_generated_documents_user_id"),
        "generated_documents",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_generated_documents_job_posting_id"),
        "generated_documents",
        ["job_posting_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_generated_documents_doc_type"),
        "generated_documents",
        ["doc_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_generated_documents_status"),
        "generated_documents",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_generated_documents_id"), "generated_documents", ["id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_generated_documents_id"), table_name="generated_documents")
    op.drop_index(
        op.f("ix_generated_documents_status"), table_name="generated_documents"
    )
    op.drop_index(
        op.f("ix_generated_documents_doc_type"), table_name="generated_documents"
    )
    op.drop_index(
        op.f("ix_generated_documents_job_posting_id"), table_name="generated_documents"
    )
    op.drop_index(
        op.f("ix_generated_documents_user_id"), table_name="generated_documents"
    )
    op.drop_table("generated_documents")