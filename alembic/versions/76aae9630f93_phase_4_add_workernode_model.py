"""Phase 4: Add WorkerNode model

Revision ID: 76aae9630f93
Revises: d87cfdcfae2c
Create Date: 2026-07-29 02:25:59.018086

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '76aae9630f93'
down_revision: Union[str, None] = 'd87cfdcfae2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Phase 4: Add WorkerNode model
    op.create_table(
        'worker_nodes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('hostname', sa.String(length=200), nullable=False),
        sa.Column('worker_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='active', nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_heartbeat_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_worker_nodes_hostname'), 'worker_nodes', ['hostname'], unique=False)
    op.create_index(op.f('ix_worker_nodes_status'), 'worker_nodes', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_worker_nodes_status'), table_name='worker_nodes')
    op.drop_index(op.f('ix_worker_nodes_hostname'), table_name='worker_nodes')
    op.drop_table('worker_nodes')
