"""V3 market play, evidence, qualification, tasks, suppression

Revision ID: 004
Revises: 003
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Prospect V3 columns
    cols = [
        ("market_play_code", sa.String(80)),
        ("pain_score", sa.Integer(), "0"),
        ("trigger_score", sa.Integer(), "0"),
        ("authority_score", sa.Integer(), "0"),
        ("value_score", sa.Integer(), "0"),
        ("data_quality_score", sa.Integer(), "0"),
        ("opportunity_score", sa.Integer(), "0"),
        ("readiness_state", sa.String(40), "research_required"),
        ("readiness_failures", sa.JSON()),
        ("suspected_pain", sa.Text()),
        ("why_now", sa.Text()),
        ("recommended_buyer_role", sa.String(80)),
        ("personalization_brief", sa.Text()),
        ("recommended_offer", sa.String(300)),
        ("evidence_json", sa.JSON()),
        ("manual_review_state", sa.String(30), "unreviewed"),
        ("qualification_decision", sa.String(30)),
        ("qualification_notes", sa.Text()),
        ("contact_discovery_state", sa.String(40)),
    ]
    for name, coltype, *default in cols:
        kwargs = {}
        if default:
            kwargs["server_default"] = default[0]
            if isinstance(coltype, sa.Integer) or name.endswith("_score"):
                kwargs["nullable"] = False
            elif name in ("readiness_state", "manual_review_state"):
                kwargs["nullable"] = False
            else:
                kwargs["nullable"] = True
        else:
            kwargs["nullable"] = True
        try:
            op.add_column("prospects", sa.Column(name, coltype, **kwargs))
        except Exception:
            pass

    op.create_index("ix_prospects_market_play_code", "prospects", ["market_play_code"])
    op.create_index("ix_prospects_opportunity_score", "prospects", ["opportunity_score"])
    op.create_index("ix_prospects_readiness_state", "prospects", ["readiness_state"])
    op.create_index("ix_prospects_manual_review_state", "prospects", ["manual_review_state"])

    for col in ("event_kind", "pipeline_stage_after", "personalization_summary", "objection_code"):
        try:
            op.add_column("outreach_events", sa.Column(col, sa.String(80) if col != "personalization_summary" else sa.Text(), nullable=True))
        except Exception:
            pass

    op.create_table(
        "market_plays",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("is_active", sa.Boolean(), server_default="0"),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("offer_name", sa.String(200)),
        sa.Column("offer_summary", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_market_plays_code", "market_plays", ["code"], unique=True)

    op.create_table(
        "evidence_signals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prospect_id", sa.Integer(), sa.ForeignKey("prospects.id", ondelete="CASCADE")),
        sa.Column("category", sa.String(30)),
        sa.Column("signal_type", sa.String(80)),
        sa.Column("label", sa.String(200)),
        sa.Column("evidence_text", sa.Text()),
        sa.Column("evidence_url", sa.Text()),
        sa.Column("source_type", sa.String(50)),
        sa.Column("confidence", sa.Integer(), server_default="50"),
        sa.Column("strength", sa.Integer(), server_default="50"),
        sa.Column("is_active", sa.Boolean(), server_default="1"),
        sa.Column("manually_confirmed", sa.Boolean(), server_default="0"),
        sa.Column("observed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_evidence_signals_prospect_id", "evidence_signals", ["prospect_id"])

    op.create_table(
        "qualification_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prospect_id", sa.Integer(), sa.ForeignKey("prospects.id", ondelete="CASCADE")),
        sa.Column("reviewer_email", sa.String(150)),
        sa.Column("decision", sa.String(30)),
        sa.Column("fit_confirmed", sa.Boolean(), server_default="0"),
        sa.Column("pain_confirmed", sa.Boolean(), server_default="0"),
        sa.Column("trigger_confirmed", sa.Boolean(), server_default="0"),
        sa.Column("buyer_confirmed", sa.Boolean(), server_default="0"),
        sa.Column("contact_confirmed", sa.Boolean(), server_default="0"),
        sa.Column("offer_match_confirmed", sa.Boolean(), server_default="0"),
        sa.Column("reason_codes", sa.JSON()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prospect_id", sa.Integer(), sa.ForeignKey("prospects.id", ondelete="CASCADE")),
        sa.Column("task_type", sa.String(40)),
        sa.Column("title", sa.String(300)),
        sa.Column("due_date", sa.DateTime(timezone=True)),
        sa.Column("priority", sa.Integer(), server_default="50"),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("origin", sa.String(20), server_default="manual"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "suppression_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(30)),
        sa.Column("value_normalized", sa.String(320)),
        sa.Column("reason", sa.String(200)),
        sa.Column("source", sa.String(80)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("adapter", sa.String(40)),
        sa.Column("market_play_code", sa.String(80)),
        sa.Column("status", sa.String(30), server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("stats_json", sa.JSON()),
        sa.Column("error_summary", sa.Text()),
        sa.Column("log_summary", sa.Text()),
    )

    op.create_table(
        "offer_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("market_play_code", sa.String(80)),
        sa.Column("asset_type", sa.String(40)),
        sa.Column("name", sa.String(200)),
        sa.Column("url_or_path", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("proof_tags", sa.JSON()),
        sa.Column("is_active", sa.Boolean(), server_default="1"),
    )


def downgrade() -> None:
    for t in (
        "offer_assets", "ingestion_runs", "suppression_entries", "tasks",
        "qualification_reviews", "evidence_signals", "market_plays",
    ):
        op.drop_table(t)
