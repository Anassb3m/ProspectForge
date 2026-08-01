"""Make canonical evidence and score explainability explicit.

Revision ID: pfscale03_20260731
Revises: pfscale02_20260731
Create Date: 2026-07-31
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "pfscale03_20260731"
down_revision: str | None = "pfscale02_20260731"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _fingerprint(*parts: object) -> str:
    value = "|".join(str(part or "").strip().lower() for part in parts)
    return hashlib.sha256(value.encode()).hexdigest()


def upgrade() -> None:
    op.alter_column(
        "company_identifiers",
        "verified_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
        postgresql_using="verified_at AT TIME ZONE 'UTC'",
    )
    op.add_column(
        "companies",
        sa.Column(
            "identity_review_state",
            sa.String(30),
            nullable=False,
            server_default="clear",
        ),
    )
    op.create_index(
        "ix_companies_identity_review_state",
        "companies",
        ["identity_review_state"],
    )
    op.execute(
        "UPDATE companies SET jurisdiction_code = 'FR' "
        "WHERE country_code = 'FR' AND jurisdiction_code <> 'FR'"
    )

    op.add_column(
        "opportunities",
        sa.Column(
            "readiness_state",
            sa.String(40),
            nullable=False,
            server_default="RAW",
        ),
    )
    op.create_index(
        "ix_opportunities_readiness_state", "opportunities", ["readiness_state"]
    )
    op.execute(
        "UPDATE opportunities SET readiness_state = CASE "
        "WHEN outreach_ready THEN 'CONTACT_READY' ELSE 'NORMALIZED' END"
    )

    op.add_column(
        "evidence_items", sa.Column("fingerprint", sa.String(64), nullable=True)
    )
    op.add_column(
        "evidence_items", sa.Column("source_type", sa.String(50), nullable=True)
    )
    op.add_column(
        "evidence_items", sa.Column("source_record_id", sa.String(200), nullable=True)
    )
    op.add_column(
        "evidence_items", sa.Column("extractor_version", sa.String(50), nullable=True)
    )
    op.add_column(
        "evidence_items",
        sa.Column("strength", sa.Float(), nullable=False, server_default="0.5"),
    )
    op.add_column(
        "evidence_items",
        sa.Column(
            "contradiction_status",
            sa.String(30),
            nullable=False,
            server_default="none",
        ),
    )
    op.add_column(
        "evidence_items",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    bind = op.get_bind()
    evidence_rows = bind.execute(
        sa.text(
            "SELECT id, opportunity_id, code, category, evidence_text, source_url "
            "FROM evidence_items ORDER BY observed_at, id"
        )
    ).mappings()
    claimed: set[tuple[str, str]] = set()
    for row in evidence_rows:
        fingerprint = _fingerprint(
            row["code"], None, row["evidence_text"], row["source_url"]
        )
        key = (str(row["opportunity_id"] or ""), fingerprint)
        if row["opportunity_id"] and key in claimed:
            bind.execute(
                sa.text(
                    "UPDATE evidence_items SET is_active = false, "
                    "contradiction_status = 'duplicate_legacy' WHERE id = :id"
                ),
                {"id": row["id"]},
            )
            continue
        if row["opportunity_id"]:
            claimed.add(key)
        bind.execute(
            sa.text("UPDATE evidence_items SET fingerprint = :fp WHERE id = :id"),
            {"fp": fingerprint, "id": row["id"]},
        )

    op.create_index(
        "ix_evidence_items_fingerprint", "evidence_items", ["fingerprint"]
    )
    op.create_index(
        "ix_evidence_items_contradiction_status",
        "evidence_items",
        ["contradiction_status"],
    )
    op.create_unique_constraint(
        "uq_evidence_opportunity_fingerprint",
        "evidence_items",
        ["opportunity_id", "fingerprint"],
    )

    op.add_column(
        "evidence_signals",
        sa.Column("canonical_evidence_id", sa.String(36), nullable=True),
    )
    op.create_foreign_key(
        "fk_evidence_signals_canonical_evidence_id",
        "evidence_signals",
        "evidence_items",
        ["canonical_evidence_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_evidence_signals_canonical_evidence_id",
        "evidence_signals",
        ["canonical_evidence_id"],
        unique=True,
    )

    legacy_rows = bind.execute(
        sa.text(
            "SELECT es.id, es.signal_type, es.category, es.evidence_text, "
            "es.evidence_url, es.source_type, es.confidence, es.strength, "
            "es.manually_confirmed, es.observed_at, p.company_id, p.opportunity_id "
            "FROM evidence_signals es JOIN prospects p ON p.id = es.prospect_id "
            "WHERE p.company_id IS NOT NULL AND p.opportunity_id IS NOT NULL "
            "ORDER BY es.id"
        )
    ).mappings()
    mapped_canonical: set[str] = set()
    for row in legacy_rows:
        fingerprint = _fingerprint(
            row["signal_type"],
            row["source_type"],
            row["evidence_text"],
            row["evidence_url"],
        )
        canonical_id = bind.scalar(
            sa.text(
                "SELECT id FROM evidence_items WHERE opportunity_id = :opp "
                "AND fingerprint = :fp AND is_active = true LIMIT 1"
            ),
            {"opp": row["opportunity_id"], "fp": fingerprint},
        )
        if canonical_id is None:
            canonical_id = str(uuid.uuid4())
            bind.execute(
                sa.text(
                    "INSERT INTO evidence_items "
                    "(id, company_id, opportunity_id, code, fingerprint, category, "
                    "evidence_text, source_url, source_type, confidence, strength, "
                    "verification_state, contradiction_status, is_active, observed_at) "
                    "VALUES (:id, :company, :opp, :code, :fp, :category, :text, "
                    ":url, :source_type, :confidence, :strength, :verification, "
                    "'none', true, COALESCE(:observed_at, CURRENT_TIMESTAMP))"
                ),
                {
                    "id": canonical_id,
                    "company": row["company_id"],
                    "opp": row["opportunity_id"],
                    "code": str(row["signal_type"] or "UNKNOWN")[:100],
                    "fp": fingerprint,
                    "category": str(row["category"] or "structural_fit")[:50],
                    "text": str(row["evidence_text"] or ""),
                    "url": row["evidence_url"],
                    "source_type": row["source_type"],
                    "confidence": float(row["confidence"] or 50) / 100.0,
                    "strength": float(row["strength"] or 50) / 100.0,
                    "verification": (
                        "manually_confirmed"
                        if row["manually_confirmed"]
                        else "source_observed"
                    ),
                    "observed_at": row["observed_at"],
                },
            )
        if str(canonical_id) not in mapped_canonical:
            bind.execute(
                sa.text(
                    "UPDATE evidence_signals SET canonical_evidence_id = :canonical "
                    "WHERE id = :legacy"
                ),
                {"canonical": canonical_id, "legacy": row["id"]},
            )
            mapped_canonical.add(str(canonical_id))

    op.add_column(
        "score_snapshots",
        sa.Column(
            "profile_code",
            sa.String(80),
            nullable=False,
            server_default="field_ops_fr_v2",
        ),
    )
    op.add_column(
        "score_snapshots", sa.Column("input_revision", sa.String(64), nullable=True)
    )
    op.add_column(
        "score_snapshots",
        sa.Column(
            "calculator_version", sa.String(30), nullable=False, server_default="5.0.0"
        ),
    )
    op.add_column(
        "score_snapshots",
        sa.Column(
            "readiness_state", sa.String(40), nullable=False, server_default="RAW"
        ),
    )
    op.add_column(
        "score_snapshots", sa.Column("evidence_refs_json", sa.JSON(), nullable=True)
    )
    op.create_index(
        "ix_score_snapshots_input_revision", "score_snapshots", ["input_revision"]
    )
    op.create_index(
        "ix_score_snapshots_readiness_state", "score_snapshots", ["readiness_state"]
    )
    op.create_unique_constraint(
        "uq_score_snapshot_input_revision",
        "score_snapshots",
        ["opportunity_id", "profile_code", "input_revision"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_score_snapshot_input_revision", "score_snapshots", type_="unique"
    )
    op.drop_index("ix_score_snapshots_readiness_state", table_name="score_snapshots")
    op.drop_index("ix_score_snapshots_input_revision", table_name="score_snapshots")
    op.drop_column("score_snapshots", "evidence_refs_json")
    op.drop_column("score_snapshots", "readiness_state")
    op.drop_column("score_snapshots", "calculator_version")
    op.drop_column("score_snapshots", "input_revision")
    op.drop_column("score_snapshots", "profile_code")
    op.drop_index(
        "ix_evidence_signals_canonical_evidence_id", table_name="evidence_signals"
    )
    op.drop_constraint(
        "fk_evidence_signals_canonical_evidence_id",
        "evidence_signals",
        type_="foreignkey",
    )
    op.drop_column("evidence_signals", "canonical_evidence_id")
    op.drop_constraint(
        "uq_evidence_opportunity_fingerprint", "evidence_items", type_="unique"
    )
    op.drop_index(
        "ix_evidence_items_contradiction_status", table_name="evidence_items"
    )
    op.drop_index("ix_evidence_items_fingerprint", table_name="evidence_items")
    op.drop_column("evidence_items", "is_active")
    op.drop_column("evidence_items", "contradiction_status")
    op.drop_column("evidence_items", "strength")
    op.drop_column("evidence_items", "extractor_version")
    op.drop_column("evidence_items", "source_record_id")
    op.drop_column("evidence_items", "source_type")
    op.drop_column("evidence_items", "fingerprint")
    op.drop_index("ix_opportunities_readiness_state", table_name="opportunities")
    op.drop_column("opportunities", "readiness_state")
    op.drop_index("ix_companies_identity_review_state", table_name="companies")
    op.drop_column("companies", "identity_review_state")
    op.alter_column(
        "company_identifiers",
        "verified_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=True,
        postgresql_using="verified_at AT TIME ZONE 'UTC'",
    )
