"""Acquisition intelligence fields: ICP scores, dirigeants, geo, stage

Revision ID: 003
Revises: 002
Create Date: 2026-07-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("prospects", sa.Column("dirigeants", sa.JSON(), nullable=True))
    op.add_column("prospects", sa.Column("city", sa.String(100), nullable=True))
    op.add_column("prospects", sa.Column("department", sa.String(10), nullable=True))
    op.add_column("prospects", sa.Column("region", sa.String(100), nullable=True))
    op.add_column("prospects", sa.Column("fit_score", sa.Integer(), server_default="0", nullable=False))
    op.add_column("prospects", sa.Column("timing_score", sa.Integer(), server_default="0", nullable=False))
    op.add_column(
        "prospects", sa.Column("contactability_score", sa.Integer(), server_default="0", nullable=False)
    )
    op.add_column(
        "prospects", sa.Column("acquisition_score", sa.Integer(), server_default="50", nullable=False)
    )
    op.add_column("prospects", sa.Column("score_breakdown", sa.JSON(), nullable=True))
    op.add_column(
        "prospects",
        sa.Column("acquisition_stage", sa.String(30), server_default="discovered", nullable=False),
    )
    op.add_column("prospects", sa.Column("last_enriched_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_prospects_department", "prospects", ["department"])
    op.create_index("ix_prospects_acquisition_score", "prospects", ["acquisition_score"])
    op.create_index("ix_prospects_acquisition_stage", "prospects", ["acquisition_stage"])


def downgrade() -> None:
    op.drop_index("ix_prospects_acquisition_stage", table_name="prospects")
    op.drop_index("ix_prospects_acquisition_score", table_name="prospects")
    op.drop_index("ix_prospects_department", table_name="prospects")
    for col in (
        "last_enriched_at",
        "acquisition_stage",
        "score_breakdown",
        "acquisition_score",
        "contactability_score",
        "timing_score",
        "fit_score",
        "region",
        "department",
        "city",
        "dirigeants",
    ):
        op.drop_column("prospects", col)
