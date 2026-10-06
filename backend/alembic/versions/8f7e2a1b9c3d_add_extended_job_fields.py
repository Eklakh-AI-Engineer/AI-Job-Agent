"""Add extended fields to job_postings for discovery pipeline

Revision ID: 8f7e2a1b9c3d
Revises: 3cebe9a2cfbf
Create Date: 2026-10-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8f7e2a1b9c3d"
down_revision: Union[str, None] = "3cebe9a2cfbf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to job_postings table
    op.add_column(
        "job_postings",
        sa.Column("source_job_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "job_postings",
        sa.Column("application_url", sa.String(length=1024), nullable=True),
    )
    op.add_column(
        "job_postings",
        sa.Column("work_mode", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "job_postings",
        sa.Column("posted_date", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "job_postings",
        sa.Column("closing_date", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "job_postings",
        sa.Column("experience_requirement", sa.Text(), nullable=True),
    )
    op.add_column(
        "job_postings",
        sa.Column("education_requirement", sa.Text(), nullable=True),
    )
    op.add_column(
        "job_postings",
        sa.Column("required_skills", sa.JSON(), nullable=True),
    )
    op.add_column(
        "job_postings",
        sa.Column("preferred_skills", sa.JSON(), nullable=True),
    )
    op.add_column(
        "job_postings",
        sa.Column("eligibility", sa.Text(), nullable=True),
    )
    op.add_column(
        "job_postings",
        sa.Column("compensation", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "job_postings",
        sa.Column("internship_information", sa.Text(), nullable=True),
    )
    op.add_column(
        "job_postings",
        sa.Column("raw_source_reference", sa.JSON(), nullable=True),
    )
    
    # Add index on source_job_id for faster lookups
    op.create_index(
        op.f("ix_job_postings_source_job_id"), "job_postings", ["source_job_id"], unique=False
    )
    
    # Add composite unique constraint on source + source_job_id
    op.create_unique_constraint(
        "uq_job_postings_source_source_job_id",
        "job_postings",
        ["source", "source_job_id"],
    )


def downgrade() -> None:
    # Drop constraints and indexes
    op.drop_constraint("uq_job_postings_source_source_job_id", "job_postings", type_="unique")
    op.drop_index(op.f("ix_job_postings_source_job_id"), table_name="job_postings")
    
    # Drop columns
    op.drop_column("job_postings", "raw_source_reference")
    op.drop_column("job_postings", "internship_information")
    op.drop_column("job_postings", "compensation")
    op.drop_column("job_postings", "eligibility")
    op.drop_column("job_postings", "preferred_skills")
    op.drop_column("job_postings", "required_skills")
    op.drop_column("job_postings", "education_requirement")
    op.drop_column("job_postings", "experience_requirement")
    op.drop_column("job_postings", "closing_date")
    op.drop_column("job_postings", "posted_date")
    op.drop_column("job_postings", "work_mode")
    op.drop_column("job_postings", "application_url")
    op.drop_column("job_postings", "source_job_id")