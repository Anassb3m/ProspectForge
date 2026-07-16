"""Add DECP discovery / enrichment fields on prospects

Revision ID: 002
Revises: 001
Create Date: 2026-07-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("prospects", sa.Column("siren", sa.String(9), nullable=True))
    op.add_column("prospects", sa.Column("siret", sa.String(14), nullable=True))
    op.add_column("prospects", sa.Column("naf_code", sa.String(10), nullable=True))
    op.add_column("prospects", sa.Column("award_history", sa.JSON(), nullable=True))
    op.add_column("prospects", sa.Column("last_tender_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("prospects", sa.Column("contact_source", sa.String(50), nullable=True))
    op.add_column("prospects", sa.Column("contact_confidence", sa.String(20), nullable=True))
    op.add_column("prospects", sa.Column("diffusion_status", sa.String(50), nullable=True))
    op.add_column("prospects", sa.Column("contact_candidates", sa.JSON(), nullable=True))
    op.add_column(
        "prospects",
        sa.Column("needs_manual_review", sa.Boolean(), server_default="0", nullable=False),
    )
    op.add_column("prospects", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))

    op.create_index("ix_prospects_siren", "prospects", ["siren"])
    op.create_index("ix_prospects_siret", "prospects", ["siret"], unique=True)
    op.create_index("ix_prospects_naf_code", "prospects", ["naf_code"])
    op.create_index("ix_prospects_contact_confidence", "prospects", ["contact_confidence"])
    op.create_index("ix_prospects_needs_manual_review", "prospects", ["needs_manual_review"])


def downgrade() -> None:
    op.drop_index("ix_prospects_needs_manual_review", table_name="prospects")
    op.drop_index("ix_prospects_contact_confidence", table_name="prospects")
    op.drop_index("ix_prospects_naf_code", table_name="prospects")
    op.drop_index("ix_prospects_siret", table_name="prospects")
    op.drop_index("ix_prospects_siren", table_name="prospects")
    for col in (
        "reviewed_at",
        "needs_manual_review",
        "contact_candidates",
        "diffusion_status",
        "contact_confidence",
        "contact_source",
        "last_tender_date",
        "award_history",
        "naf_code",
        "siret",
        "siren",
    ):
        op.drop_column("prospects", col)
