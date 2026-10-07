"""Persist canonical structured JD normalization fields.

Revision ID: jdnorm001
Revises: c7d4e1a9f2b8
"""
from alembic import op
import sqlalchemy as sa

revision = "jdnorm001"
down_revision = "c7d4e1a9f2b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("job_postings", sa.Column("normalized_required_skills", sa.JSON(), nullable=True))
    op.add_column("job_postings", sa.Column("normalized_preferred_skills", sa.JSON(), nullable=True))
    op.add_column("job_postings", sa.Column("experience_min_years", sa.Float(), nullable=True))
    op.add_column("job_postings", sa.Column("experience_max_years", sa.Float(), nullable=True))
    op.add_column("job_postings", sa.Column("education_level", sa.String(length=50), nullable=True))
    op.add_column("job_postings", sa.Column("education_fields", sa.JSON(), nullable=True))
    op.add_column("job_postings", sa.Column("jd_normalization_version", sa.String(length=50), nullable=True))
    op.add_column("job_postings", sa.Column("jd_normalization_status", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("job_postings", "jd_normalization_status")
    op.drop_column("job_postings", "jd_normalization_version")
    op.drop_column("job_postings", "education_fields")
    op.drop_column("job_postings", "education_level")
    op.drop_column("job_postings", "experience_max_years")
    op.drop_column("job_postings", "experience_min_years")
    op.drop_column("job_postings", "normalized_preferred_skills")
    op.drop_column("job_postings", "normalized_required_skills")
