"""Phase 3: Retire mutable fields from Prospect

Revision ID: d87cfdcfae2c
Revises: pfrel01_20260728
Create Date: 2026-07-29 02:16:11.273889

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd87cfdcfae2c'
down_revision: Union[str, None] = 'pfrel01_20260728'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Phase 3: Canonical Data Model Consolidation
    # Make mutable fields nullable on Prospect as they are now managed in canonical models.
    op.alter_column('prospects', 'sector', existing_type=sa.String(length=100), nullable=True)
    op.alter_column('prospects', 'company_size', existing_type=sa.String(length=20), nullable=True)
    op.alter_column('prospects', 'data_source', existing_type=sa.String(length=200), nullable=True)


def downgrade() -> None:
    # Revert mutability nullability
    op.alter_column('prospects', 'data_source', existing_type=sa.String(length=200), nullable=False)
    op.alter_column('prospects', 'company_size', existing_type=sa.String(length=20), nullable=False)
    op.alter_column('prospects', 'sector', existing_type=sa.String(length=100), nullable=False)
