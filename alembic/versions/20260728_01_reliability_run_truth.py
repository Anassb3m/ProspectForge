"""Make pipeline runs the canonical, truthful ingestion ledger.

Revision ID: pfrel01_20260728
Revises: 1e81eb7d5107
Create Date: 2026-07-28
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "pfrel01_20260728"
down_revision: str | None = "1e81eb7d5107"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "prospects", sa.Column("company_id", sa.String(36), nullable=True)
    )
    op.add_column(
        "prospects", sa.Column("opportunity_id", sa.String(36), nullable=True)
    )
    op.create_foreign_key(
        "fk_prospects_company_id_companies",
        "prospects",
        "companies",
        ["company_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_prospects_opportunity_id_opportunities",
        "prospects",
        "opportunities",
        ["opportunity_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_prospects_company_id", "prospects", ["company_id"])
    op.create_index(
        "ix_prospects_opportunity_id",
        "prospects",
        ["opportunity_id"],
        unique=True,
    )

    # Identity-only reconciliation. Names and guessed domains are never used.
    op.execute(
        """
        UPDATE prospects AS p
        SET company_id = ci.company_id
        FROM company_identifiers AS ci
        WHERE p.company_id IS NULL
          AND p.siret IS NOT NULL
          AND ci.scheme = 'FR_SIRET'
          AND ci.value_normalized = p.siret
        """
    )
    op.execute(
        """
        UPDATE prospects AS p
        SET company_id = ci.company_id
        FROM company_identifiers AS ci
        WHERE p.company_id IS NULL
          AND p.siren IS NOT NULL
          AND ci.scheme = 'FR_SIREN'
          AND ci.value_normalized = p.siren
        """
    )
    op.execute(
        """
        UPDATE prospects AS p
        SET opportunity_id = (
            SELECT MIN(o.id)
            FROM opportunities AS o
            JOIN market_play_versions AS mpv
              ON mpv.id = o.play_version_id
            WHERE o.company_id = p.company_id
              AND mpv.play_code = p.market_play_code
            HAVING COUNT(*) = 1
        )
        WHERE p.company_id IS NOT NULL
          AND p.market_play_code IS NOT NULL
          AND p.opportunity_id IS NULL
        """
    )

    columns = (
        sa.Column("play_version", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("connector_code", sa.String(80), nullable=False, server_default="unknown"),
        sa.Column("partition_key", sa.String(160), nullable=False, server_default="all"),
        sa.Column("mode", sa.String(40), nullable=False, server_default="full"),
        sa.Column("request_config_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("requested_by", sa.String(150), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=False, server_default="legacy"),
        sa.Column("application_revision", sa.String(80), nullable=True),
        sa.Column(
            "heartbeat_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("checkpoint_before_json", sa.JSON(), nullable=True),
        sa.Column("checkpoint_after_json", sa.JSON(), nullable=True),
        sa.Column("raw_discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_persisted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invalid_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("companies_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("companies_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("icp_accepted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("icp_rejected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enrichment_queued", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enrichment_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enrichment_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contact_queued", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contact_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contact_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_categories_json", sa.JSON(), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
    )
    for column in columns:
        op.add_column("pipeline_runs", column)

    op.create_index(
        "ix_pipeline_runs_connector_code", "pipeline_runs", ["connector_code"]
    )
    op.create_index(
        "ix_pipeline_runs_correlation_id", "pipeline_runs", ["correlation_id"]
    )
    op.create_index(
        "ix_pipeline_runs_status_heartbeat",
        "pipeline_runs",
        ["status", "heartbeat_at"],
    )
    op.add_column(
        "failed_work_items", sa.Column("source_name", sa.String(80), nullable=True)
    )
    op.add_column(
        "failed_work_items",
        sa.Column("source_record_key", sa.String(200), nullable=True),
    )
    op.add_column(
        "failed_work_items",
        sa.Column(
            "error_category",
            sa.String(80),
            nullable=False,
            server_default="UNCLASSIFIED",
        ),
    )
    op.add_column(
        "failed_work_items",
        sa.Column("retryable", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        "ix_failed_work_items_source_name",
        "failed_work_items",
        ["source_name"],
    )
    op.create_index(
        "ix_failed_work_items_error_category",
        "failed_work_items",
        ["error_category"],
    )
    op.add_column(
        "work_items",
        sa.Column("idempotency_key", sa.String(128), nullable=True),
    )
    bind = op.get_bind()
    work_items = sa.table(
        "work_items",
        sa.column("id", sa.String),
        sa.column("idempotency_key", sa.String),
    )
    for row in bind.execute(sa.select(work_items.c.id)).mappings():
        bind.execute(
            work_items.update()
            .where(work_items.c.id == row["id"])
            .values(idempotency_key=f"legacy-work-item:{row['id']}")
        )
    op.alter_column("work_items", "idempotency_key", nullable=False)
    op.create_index(
        "ix_work_items_idempotency_key",
        "work_items",
        ["idempotency_key"],
        unique=True,
    )

    # Compatibility backfill: retain every legacy run as a read-only historical
    # pipeline record. No company/evidence data is altered or inferred.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "ingestion_runs" not in inspector.get_table_names():
        return

    legacy = sa.table(
        "ingestion_runs",
        sa.column("id", sa.Integer),
        sa.column("adapter", sa.String),
        sa.column("market_play_code", sa.String),
        sa.column("status", sa.String),
        sa.column("started_at", sa.DateTime(timezone=True)),
        sa.column("finished_at", sa.DateTime(timezone=True)),
        sa.column("stats_json", sa.JSON),
        sa.column("error_summary", sa.Text),
    )
    pipeline = sa.table(
        "pipeline_runs",
        sa.column("id", sa.String),
        sa.column("play_code", sa.String),
        sa.column("play_version", sa.String),
        sa.column("connector_code", sa.String),
        sa.column("partition_key", sa.String),
        sa.column("mode", sa.String),
        sa.column("status", sa.String),
        sa.column("request_config_json", sa.JSON),
        sa.column("correlation_id", sa.String),
        sa.column("started_at", sa.DateTime(timezone=True)),
        sa.column("heartbeat_at", sa.DateTime(timezone=True)),
        sa.column("finished_at", sa.DateTime(timezone=True)),
        sa.column("companies_created", sa.Integer),
        sa.column("companies_updated", sa.Integer),
        sa.column("error_count", sa.Integer),
        sa.column("stats_json", sa.JSON),
        sa.column("error_categories_json", sa.JSON),
    )
    for row in bind.execute(sa.select(legacy)).mappings():
        stats = row["stats_json"] or {}
        bind.execute(
            pipeline.insert().values(
                id=str(uuid.uuid4()),
                play_code=row["market_play_code"] or "UNKNOWN_LEGACY_PLAY",
                play_version="legacy",
                connector_code=row["adapter"] or "unknown",
                partition_key="legacy",
                mode=row["adapter"] or "unknown",
                status=row["status"] or "unknown",
                request_config_json={
                    "legacy_ingestion_run_id": row["id"],
                    "backfilled": True,
                },
                correlation_id=f"legacy-ingestion-{row['id']}",
                started_at=row["started_at"],
                heartbeat_at=row["finished_at"] or row["started_at"],
                finished_at=row["finished_at"],
                companies_created=int(stats.get("created") or 0),
                companies_updated=int(stats.get("updated") or 0),
                error_count=int(stats.get("errors") or 0),
                stats_json=stats,
                error_categories_json=(
                    {"LEGACY_ERROR": 1} if row["error_summary"] else None
                ),
            )
        )


def downgrade() -> None:
    # Historical backfill rows are intentionally retained in pipeline_runs. A
    # downgrade removes only the new columns; no legacy/source/company rows.
    op.drop_index("ix_pipeline_runs_status_heartbeat", table_name="pipeline_runs")
    op.drop_index("ix_pipeline_runs_correlation_id", table_name="pipeline_runs")
    op.drop_index("ix_pipeline_runs_connector_code", table_name="pipeline_runs")
    op.drop_index(
        "ix_failed_work_items_error_category", table_name="failed_work_items"
    )
    op.drop_index("ix_failed_work_items_source_name", table_name="failed_work_items")
    op.drop_column("failed_work_items", "retryable")
    op.drop_column("failed_work_items", "error_category")
    op.drop_column("failed_work_items", "source_record_key")
    op.drop_column("failed_work_items", "source_name")
    op.drop_index("ix_work_items_idempotency_key", table_name="work_items")
    op.drop_column("work_items", "idempotency_key")
    for name in (
        "error_summary",
        "error_categories_json",
        "error_count",
        "retry_count",
        "contact_failed",
        "contact_completed",
        "contact_queued",
        "enrichment_failed",
        "enrichment_completed",
        "enrichment_queued",
        "icp_rejected",
        "icp_accepted",
        "companies_updated",
        "companies_created",
        "invalid_count",
        "duplicate_count",
        "raw_persisted",
        "raw_discovered",
        "checkpoint_after_json",
        "checkpoint_before_json",
        "heartbeat_at",
        "application_revision",
        "correlation_id",
        "requested_by",
        "request_config_json",
        "mode",
        "partition_key",
        "connector_code",
        "play_version",
    ):
        op.drop_column("pipeline_runs", name)
    op.drop_index("ix_prospects_opportunity_id", table_name="prospects")
    op.drop_index("ix_prospects_company_id", table_name="prospects")
    op.drop_constraint(
        "fk_prospects_opportunity_id_opportunities",
        "prospects",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_prospects_company_id_companies", "prospects", type_="foreignkey"
    )
    op.drop_column("prospects", "opportunity_id")
    op.drop_column("prospects", "company_id")
