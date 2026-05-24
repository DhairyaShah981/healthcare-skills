"""add_patient_consent

Revision adds the patient_consent table. ID is hash-style; description in comment.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers — keep ≤ 32 chars
revision = "a4f2b9c1d7e3"           # add_patient_consent
down_revision = "ab12cd34ef56"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patient_consent",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("patient_id", sa.Text, nullable=False, index=True),
        sa.Column("recipient", sa.Text, nullable=False),
        sa.Column("scopes", sa.dialects.postgresql.ARRAY(sa.Text)),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("period_start", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("period_end", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("patient_consent")
