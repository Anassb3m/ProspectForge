"""Normalized, source-backed contact intelligence.

Revision ID: pfci60_20260720
Revises: 005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "pfci60_20260720"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "prospects",
        "contact_confidence",
        existing_type=sa.String(20),
        type_=sa.String(50),
        existing_nullable=True,
    )

    op.create_table(
        "contact_people",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "prospect_id", sa.Integer(), sa.ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("normalized_name", sa.String(200), nullable=False),
        sa.Column("first_name", sa.String(100)),
        sa.Column("last_name", sa.String(100)),
        sa.Column("job_title", sa.String(200)),
        sa.Column("normalized_role", sa.String(120), server_default="unknown", nullable=False),
        sa.Column("role_category", sa.String(40), server_default="unknown", nullable=False),
        sa.Column("buyer_role_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("company_match_state", sa.String(20), server_default="unknown", nullable=False),
        sa.Column("identity_confidence", sa.Integer(), server_default="0", nullable=False),
        sa.Column("linkedin_url", sa.Text()),
        sa.Column("source_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_primary_candidate", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("manually_confirmed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "role_category IN ('owner','executive','operations','service','maintenance','technical',"
            "'exploitation','administration_finance','commercial','planning_methods',"
            "'legal_representative','other','unknown')",
            name="ck_contact_people_role_category",
        ),
        sa.CheckConstraint(
            "company_match_state IN ('exact','strong','probable','ambiguous','conflicting','unknown')",
            name="ck_contact_people_company_match",
        ),
        sa.UniqueConstraint(
            "prospect_id", "normalized_name", "normalized_role", name="uq_contact_person_identity"
        ),
    )
    op.create_index("ix_contact_people_prospect_id", "contact_people", ["prospect_id"])
    op.create_index("ix_contact_people_normalized_name", "contact_people", ["normalized_name"])

    op.create_table(
        "contact_points",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "prospect_id", sa.Integer(), sa.ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "person_id", sa.Integer(), sa.ForeignKey("contact_people.id", ondelete="SET NULL")
        ),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("value_normalized", sa.String(500), nullable=False),
        sa.Column("value_display", sa.String(500), nullable=False),
        sa.Column("domain", sa.String(253)),
        sa.Column("source_class", sa.String(50), server_default="legacy", nullable=False),
        sa.Column("publication_state", sa.String(30), server_default="unknown", nullable=False),
        sa.Column("person_match_state", sa.String(40), server_default="unknown", nullable=False),
        sa.Column("deliverability_state", sa.String(30), server_default="unchecked", nullable=False),
        sa.Column("verification_state", sa.String(30), server_default="unchecked", nullable=False),
        sa.Column("utility_state", sa.String(40), server_default="no_contact", nullable=False),
        sa.Column("confidence_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_usable", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("requires_manual_review", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("is_suppressed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("manually_confirmed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("rejection_reason", sa.String(300)),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('email','phone','contact_form','linkedin','website','generic_contact_page','other')",
            name="ck_contact_points_kind",
        ),
        sa.CheckConstraint(
            "publication_state IN ('published_personal','published_role','published_generic',"
            "'not_published','unknown')",
            name="ck_contact_points_publication",
        ),
        sa.CheckConstraint(
            "deliverability_state IN ('deliverable','catch_all','risky','invalid','indeterminate',"
            "'unchecked','error')",
            name="ck_contact_points_deliverability",
        ),
        sa.CheckConstraint(
            "person_match_state IN ('exact_person_published','exact_person_pattern_confirmed',"
            "'strong_person_match','role_mailbox','generic_company_mailbox','pattern_inferred',"
            "'name_only_guess','conflicting','unknown')",
            name="ck_contact_points_person_match",
        ),
        sa.CheckConstraint(
            "utility_state IN ('usable_personal','usable_role','usable_generic',"
            "'manual_confirmation_required','verification_required','invalid','suppressed',"
            "'stale','no_contact')",
            name="ck_contact_points_utility",
        ),
        sa.UniqueConstraint("prospect_id", "kind", "value_normalized", name="uq_contact_point_value"),
    )
    op.create_index("ix_contact_points_prospect_id", "contact_points", ["prospect_id"])
    op.create_index("ix_contact_points_person_id", "contact_points", ["person_id"])
    op.create_index("ix_contact_points_kind", "contact_points", ["kind"])
    op.create_index("ix_contact_points_domain", "contact_points", ["domain"])
    op.create_index("ix_contact_points_utility_state", "contact_points", ["utility_state"])
    op.create_index("ix_contact_points_is_usable", "contact_points", ["is_usable"])

    op.create_table(
        "contact_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "prospect_id", sa.Integer(), sa.ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("person_id", sa.Integer(), sa.ForeignKey("contact_people.id", ondelete="SET NULL")),
        sa.Column(
            "contact_point_id", sa.Integer(), sa.ForeignKey("contact_points.id", ondelete="SET NULL")
        ),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("source_adapter", sa.String(60), nullable=False),
        sa.Column("source_url", sa.Text()),
        sa.Column("canonical_url", sa.Text()),
        sa.Column("source_domain", sa.String(253)),
        sa.Column("source_record_id", sa.String(200)),
        sa.Column("page_title", sa.String(300)),
        sa.Column("evidence_type", sa.String(60), nullable=False),
        sa.Column("excerpt", sa.String(600)),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("confidence", sa.Integer(), server_default="50", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("raw_metadata", sa.JSON()),
        sa.UniqueConstraint("fingerprint", name="uq_contact_evidence_fingerprint"),
    )
    for column in ("prospect_id", "person_id", "contact_point_id", "fingerprint", "source_adapter", "evidence_type"):
        op.create_index(f"ix_contact_evidence_{column}", "contact_evidence", [column])

    op.create_table(
        "contact_discovery_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "prospect_id", sa.Integer(), sa.ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("run_type", sa.String(30), server_default="full", nullable=False),
        sa.Column("triggered_by", sa.String(150), nullable=False),
        sa.Column("status", sa.String(30), server_default="running", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("adapters_requested", sa.JSON()),
        sa.Column("adapters_completed", sa.JSON()),
        sa.Column("pages_examined", sa.Integer(), server_default="0", nullable=False),
        sa.Column("people_found", sa.Integer(), server_default="0", nullable=False),
        sa.Column("contact_points_found", sa.Integer(), server_default="0", nullable=False),
        sa.Column("published_emails_found", sa.Integer(), server_default="0", nullable=False),
        sa.Column("generated_candidates", sa.Integer(), server_default="0", nullable=False),
        sa.Column("verified_deliverable", sa.Integer(), server_default="0", nullable=False),
        sa.Column("catch_all", sa.Integer(), server_default="0", nullable=False),
        sa.Column("invalid", sa.Integer(), server_default="0", nullable=False),
        sa.Column("manual_review_required", sa.Integer(), server_default="0", nullable=False),
        sa.Column("errors", sa.Integer(), server_default="0", nullable=False),
        sa.Column("timings", sa.JSON()),
        sa.Column("result_summary", sa.JSON()),
        sa.Column("error_summary", sa.Text()),
    )
    op.create_index("ix_contact_discovery_runs_prospect_id", "contact_discovery_runs", ["prospect_id"])
    op.create_index("ix_contact_discovery_runs_status", "contact_discovery_runs", ["status"])

    op.create_table(
        "contact_verification_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "contact_point_id", sa.Integer(), sa.ForeignKey("contact_points.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("provider", sa.String(60), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deliverability_state", sa.String(30), nullable=False),
        sa.Column("is_catch_all", sa.Boolean()),
        sa.Column("smtp_state", sa.String(40)),
        sa.Column("mx_state", sa.String(40)),
        sa.Column("confidence", sa.Float(), server_default="0", nullable=False),
        sa.Column("raw_summary", sa.JSON()),
        sa.Column("error_code", sa.String(80)),
    )
    op.create_index(
        "ix_contact_verification_events_contact_point_id",
        "contact_verification_events",
        ["contact_point_id"],
    )

    op.create_table(
        "contact_manual_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("contact_point_id", sa.Integer(), sa.ForeignKey("contact_points.id", ondelete="SET NULL")),
        sa.Column("person_id", sa.Integer(), sa.ForeignKey("contact_people.id", ondelete="SET NULL")),
        sa.Column("reviewer", sa.String(150), nullable=False),
        sa.Column("decision", sa.String(40), nullable=False),
        sa.Column("previous_state", sa.String(60)),
        sa.Column("new_state", sa.String(60)),
        sa.Column("reason", sa.Text()),
        sa.Column("evidence_url", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_contact_manual_reviews_contact_point_id", "contact_manual_reviews", ["contact_point_id"])
    op.create_index("ix_contact_manual_reviews_person_id", "contact_manual_reviews", ["person_id"])


def downgrade() -> None:
    op.drop_table("contact_manual_reviews")
    op.drop_table("contact_verification_events")
    op.drop_table("contact_discovery_runs")
    op.drop_table("contact_evidence")
    op.drop_table("contact_points")
    op.drop_table("contact_people")
    op.alter_column(
        "prospects",
        "contact_confidence",
        existing_type=sa.String(50),
        type_=sa.String(20),
        existing_nullable=True,
    )
