"""Add structured JD normalization metadata.

Revision ID: jdnorm001
Revises: None
"""
from alembic import op
import sqlalchemy as sa

revision = "jdnorm001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Normalization metadata is stored inside the existing JSON provenance
    # envelope, so no schema column is required for v1.
    pass


def downgrade() -> None:
    pass
