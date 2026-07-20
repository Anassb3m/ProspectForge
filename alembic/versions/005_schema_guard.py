"""Fail deployment if a historical migration left the production schema incomplete.

Revision ID: 005
Revises: 004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


EXPECTED_COLUMNS = {
    "users": {"id", "email", "hashed_password", "created_at"},
    "prospects": {
        "id",
        "company_name",
        "siren",
        "market_play_code",
        "opportunity_score",
        "readiness_state",
        "manual_review_state",
        "qualification_decision",
        "evidence_json",
        "data_source",
        "informed_at",
        "opted_out",
    },
    "outreach_events": {
        "id",
        "prospect_id",
        "event_type",
        "event_kind",
        "personalization_summary",
    },
    "market_plays": {"id", "code", "config_json", "is_active"},
    "evidence_signals": {"id", "prospect_id", "category", "evidence_text"},
    "qualification_reviews": {"id", "prospect_id", "decision", "reviewer_email"},
    "tasks": {"id", "prospect_id", "task_type", "status", "due_date"},
    "suppression_entries": {"id", "kind", "value_normalized"},
    "ingestion_runs": {"id", "adapter", "status", "started_at"},
    "offer_assets": {"id", "market_play_code", "asset_type", "is_active"},
}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    failures: list[str] = []

    for table, expected_columns in EXPECTED_COLUMNS.items():
        if table not in tables:
            failures.append(f"missing table {table}")
            continue
        actual_columns = {column["name"] for column in inspector.get_columns(table)}
        missing = sorted(expected_columns - actual_columns)
        if missing:
            failures.append(f"{table} missing columns: {', '.join(missing)}")

    if failures:
        raise RuntimeError(
            "ProspectForge schema integrity check failed: " + "; ".join(failures)
        )


def downgrade() -> None:
    # This revision only records that schema integrity was verified.
    pass
