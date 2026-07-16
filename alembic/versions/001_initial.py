"""Initial schema: users, prospects, outreach_events

Revision ID: 001
Revises:
Create Date: 2026-07-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(150), nullable=False),
        sa.Column("hashed_password", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "prospects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_name", sa.String(200), nullable=False),
        sa.Column("sector", sa.String(100), nullable=False),
        sa.Column("company_size", sa.String(20), nullable=False),
        sa.Column("signal_type", sa.String(50), nullable=False),
        sa.Column("signal_details", sa.Text(), nullable=True),
        sa.Column("decision_maker_name", sa.String(150), nullable=True),
        sa.Column("decision_maker_title", sa.String(150), nullable=True),
        sa.Column("linkedin_url", sa.String(300), nullable=True),
        sa.Column("email", sa.String(150), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("website", sa.String(300), nullable=True),
        sa.Column("data_source", sa.String(200), nullable=False),
        sa.Column("informed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opted_out", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("opted_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("urgency_score", sa.Integer(), server_default="50", nullable=False),
        sa.Column("priority_level", sa.String(10), server_default="Medium", nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("anonymized", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_prospects_company_name", "prospects", ["company_name"])
    op.create_index("ix_prospects_signal_type", "prospects", ["signal_type"])
    op.create_index("ix_prospects_urgency_score", "prospects", ["urgency_score"])

    op.create_table(
        "outreach_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prospect_id", sa.Integer(), sa.ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("event_date", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("next_action", sa.String(300), nullable=True),
        sa.Column("next_action_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_outreach_events_prospect_id", "outreach_events", ["prospect_id"])
    op.create_index("ix_outreach_events_event_type", "outreach_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("outreach_events")
    op.drop_table("prospects")
    op.drop_table("users")
