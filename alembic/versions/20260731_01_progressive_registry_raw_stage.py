"""Add pipeline-owned raw source records for recoverable discovery.

Revision ID: pfscale02_20260731
Revises: 76aae9630f93
Create Date: 2026-07-31
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "pfscale02_20260731"
down_revision: str | None = "76aae9630f93"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "source_checkpoints",
        "high_water_mark",
        existing_type=sa.String(200),
        type_=sa.Text(),
        existing_nullable=False,
    )
    op.add_column(
        "failed_work_items",
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "failed_work_items",
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "failed_work_items",
        sa.Column("resolution_note", sa.Text(), nullable=True),
    )
    op.add_column(
        "failed_work_items",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("source_records", "source_run_id", nullable=True)
    op.add_column(
        "source_records",
        sa.Column("pipeline_run_id", sa.String(36), nullable=True),
    )
    op.add_column(
        "source_records",
        sa.Column(
            "processing_status",
            sa.String(30),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "source_records",
        sa.Column("processing_result", sa.String(30), nullable=True),
    )
    op.add_column(
        "source_records",
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "source_records",
        sa.Column("error_category", sa.String(80), nullable=True),
    )
    # Existing source-run records remain immutable legacy raw history. They
    # are not pending work for the new pipeline-owned normalizer.
    op.execute(
        "UPDATE source_records SET processing_status = 'legacy' "
        "WHERE pipeline_run_id IS NULL"
    )
    op.create_foreign_key(
        "fk_source_records_pipeline_run_id",
        "source_records",
        "pipeline_runs",
        ["pipeline_run_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_source_records_pipeline_run_id",
        "source_records",
        ["pipeline_run_id"],
    )
    op.create_index(
        "ix_source_records_processing_status",
        "source_records",
        ["processing_status"],
    )
    op.create_index(
        "ix_source_records_pipeline_status",
        "source_records",
        ["pipeline_run_id", "processing_status"],
    )
    op.create_unique_constraint(
        "uq_source_record_pipeline_external_hash",
        "source_records",
        ["pipeline_run_id", "external_id", "payload_hash"],
    )
    op.create_check_constraint(
        "ck_source_record_has_run",
        "source_records",
        "source_run_id IS NOT NULL OR pipeline_run_id IS NOT NULL",
    )


def downgrade() -> None:
    bind = op.get_bind()
    pipeline_owned = bind.scalar(
        sa.text(
            "SELECT count(*) FROM source_records WHERE pipeline_run_id IS NOT NULL"
        )
    )
    if pipeline_owned:
        raise RuntimeError(
            "Refusing to downgrade: pipeline-owned raw source records exist. "
            "Keep the additive schema during an application rollback."
        )
    oversized_checkpoint = bind.scalar(
        sa.text(
            "SELECT count(*) FROM source_checkpoints "
            "WHERE length(high_water_mark) > 200"
        )
    )
    if oversized_checkpoint:
        raise RuntimeError(
            "Refusing to downgrade: a source checkpoint exceeds the legacy "
            "200-character limit. Keep the additive schema."
        )
    op.drop_constraint(
        "ck_source_record_has_run", "source_records", type_="check"
    )
    op.drop_constraint(
        "uq_source_record_pipeline_external_hash",
        "source_records",
        type_="unique",
    )
    op.drop_index("ix_source_records_pipeline_status", table_name="source_records")
    op.drop_index(
        "ix_source_records_processing_status", table_name="source_records"
    )
    op.drop_index(
        "ix_source_records_pipeline_run_id", table_name="source_records"
    )
    op.drop_constraint(
        "fk_source_records_pipeline_run_id", "source_records", type_="foreignkey"
    )
    op.drop_column("source_records", "error_category")
    op.drop_column("source_records", "processed_at")
    op.drop_column("source_records", "processing_result")
    op.drop_column("source_records", "processing_status")
    op.drop_column("source_records", "pipeline_run_id")
    op.alter_column("source_records", "source_run_id", nullable=False)
    op.alter_column(
        "source_checkpoints",
        "high_water_mark",
        existing_type=sa.Text(),
        type_=sa.String(200),
        existing_nullable=False,
    )
    op.drop_column("failed_work_items", "retry_count")
    op.drop_column("failed_work_items", "resolution_note")
    op.drop_column("failed_work_items", "resolved_at")
    op.drop_column("failed_work_items", "resolved")
