"""add_patient_consent_revocation_table_v2_with_signed_hash

This migration trips multiple alembic-guard rules. See check_revision.py output.
"""
from alembic import op

# ALG-001: revision is 54 chars — varchar(32) blows up
revision = "add_patient_consent_revocation_table_v2_with_signed_hash"
down_revision = "abc123"

# ALG-004: PHI in a comment. Backfilling for patient Mr. John Smith,
# MRN8829340, account 998812 per support ticket #4421.


def upgrade() -> None:
    # ALG-005: bare UPDATE will lock the patients table for the duration
    op.execute("UPDATE patient SET consent_required = TRUE WHERE consent_required IS NULL")

# ALG-003: no downgrade() function.
