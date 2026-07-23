"""add v4 scoring models

Revision ID: 1e81eb7d5107
Revises: ba79da6588fd
Create Date: 2026-07-23 02:25:54.958896

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1e81eb7d5107'
down_revision: Union[str, None] = 'ba79da6588fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # opportunities table updates
    op.add_column('opportunities', sa.Column('outreach_ready', sa.Boolean(), server_default='0', nullable=False))
    
    # score_snapshots table updates
    op.add_column('score_snapshots', sa.Column('version', sa.String(length=20), server_default='4.0', nullable=False))
    op.add_column('score_snapshots', sa.Column('inputs_json', sa.JSON(), nullable=True))
    op.add_column('score_snapshots', sa.Column('dimensions_json', sa.JSON(), nullable=True))
    op.add_column('score_snapshots', sa.Column('weights_json', sa.JSON(), nullable=True))
    op.add_column('score_snapshots', sa.Column('penalties_json', sa.JSON(), nullable=True))
    op.add_column('score_snapshots', sa.Column('hard_gates_json', sa.JSON(), nullable=True))
    op.add_column('score_snapshots', sa.Column('reasons_json', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('score_snapshots', 'reasons_json')
    op.drop_column('score_snapshots', 'hard_gates_json')
    op.drop_column('score_snapshots', 'penalties_json')
    op.drop_column('score_snapshots', 'weights_json')
    op.drop_column('score_snapshots', 'dimensions_json')
    op.drop_column('score_snapshots', 'inputs_json')
    op.drop_column('score_snapshots', 'version')
    
    op.drop_column('opportunities', 'outreach_ready')
