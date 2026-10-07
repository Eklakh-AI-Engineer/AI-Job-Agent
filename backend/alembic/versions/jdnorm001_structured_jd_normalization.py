"""Record the structured JD normalization contract.

Revision ID: jdnorm001
Revises: c7d4e1a9f2b8
"""
revision = "jdnorm001"
down_revision = "c7d4e1a9f2b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # v1 stores normalization metadata inside JobPosting.raw_source_reference.
    # The migration exists to version the persistence contract without adding
    # duplicate columns for data that is already JSON-backed.
    pass


def downgrade() -> None:
    pass
