"""Multi-market evidence and contact acquisition operating system schema.

Revision ID: pfmm70_20260721
Revises: pfci60_20260720
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "pfmm70_20260721"
down_revision: str | None = "pfci60_20260720"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. companies
    op.create_table(
        "companies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("canonical_name", sa.String(255), nullable=False, index=True),
        sa.Column("legal_name", sa.String(255), nullable=True),
        sa.Column("country_code", sa.String(2), nullable=False, server_default="GB", index=True),
        sa.Column("jurisdiction_code", sa.String(10), nullable=False, server_default="GB-EW"),
        sa.Column("legal_form_code", sa.String(50), nullable=True),
        sa.Column("entity_status", sa.String(50), nullable=False, server_default="active", index=True),
        sa.Column("incorporated_at", sa.DateTime(), nullable=True),
        sa.Column("dissolved_at", sa.DateTime(), nullable=True),
        sa.Column("primary_domain_id", sa.String(36), nullable=True),
        sa.Column("merged_into_company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("record_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 2. company_identifiers
    op.create_table(
        "company_identifiers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("scheme", sa.String(50), nullable=False, index=True),
        sa.Column("value_normalized", sa.String(100), nullable=False, index=True),
        sa.Column("value_display", sa.String(100), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("source_record_id", sa.Integer(), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("scheme", "value_normalized", name="uq_identifier_scheme_value"),
    )

    # 3. company_names
    op.create_table(
        "company_names",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("name_type", sa.String(50), nullable=False, server_default="legal"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 4. company_classifications
    op.create_table(
        "company_classifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("scheme", sa.String(50), nullable=False, index=True),
        sa.Column("code", sa.String(50), nullable=False, index=True),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 5. company_locations
    op.create_table(
        "company_locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("location_type", sa.String(50), nullable=False, server_default="registered"),
        sa.Column("street", sa.String(255), nullable=True),
        sa.Column("locality", sa.String(100), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("postal_code", sa.String(20), nullable=True, index=True),
        sa.Column("country_code", sa.String(2), nullable=False, server_default="GB"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 6. company_domains
    op.create_table(
        "company_domains",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("domain_normalized", sa.String(255), nullable=False, index=True),
        sa.Column("domain_role", sa.String(50), nullable=False, server_default="primary"),
        sa.Column("verification_state", sa.String(50), nullable=False, server_default="candidate"),
        sa.Column("match_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("match_reasons_json", sa.JSON(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 7. company_estimates
    op.create_table(
        "company_estimates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("estimate_type", sa.String(50), nullable=False, server_default="field_technicians"),
        sa.Column("lower_bound", sa.Integer(), nullable=True),
        sa.Column("upper_bound", sa.Integer(), nullable=True),
        sa.Column("point_estimate", sa.Integer(), nullable=True),
        sa.Column("method_code", sa.String(50), nullable=False, server_default="composite"),
        sa.Column("confidence", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("assumptions_json", sa.JSON(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 8. source_connectors
    op.create_table(
        "source_connectors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("version", sa.String(20), nullable=False, server_default="1.0.0"),
        sa.Column("country_coverage", sa.JSON(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 9. source_runs
    op.create_table(
        "source_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("connector_code", sa.String(50), nullable=False, index=True),
        sa.Column("play_version_code", sa.String(100), nullable=False, index=True),
        sa.Column("query_config_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="running"),
        sa.Column("items_discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_normalized", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_rejected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
    )

    # 10. source_records
    op.create_table(
        "source_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_run_id", sa.String(36), sa.ForeignKey("source_runs.id"), nullable=False, index=True),
        sa.Column("external_id", sa.String(255), nullable=True, index=True),
        sa.Column("record_type", sa.String(50), nullable=False, server_default="company"),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("payload_hash", sa.String(64), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 11. market_play_versions
    op.create_table(
        "market_play_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("play_code", sa.String(100), nullable=False, index=True),
        sa.Column("version", sa.String(20), nullable=False, server_default="1.0.0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pilot"),
        sa.Column("jurisdiction", sa.String(10), nullable=False, server_default="GB"),
        sa.Column("locale", sa.String(10), nullable=False, server_default="en-GB"),
        sa.Column("icp_config_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 12. opportunities
    op.create_table(
        "opportunities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("play_version_id", sa.String(36), sa.ForeignKey("market_play_versions.id"), nullable=False, index=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="discovered", index=True),
        sa.Column("status_reason_code", sa.String(50), nullable=True),
        sa.Column("priority", sa.String(20), nullable=False, server_default="Medium"),
        sa.Column("latest_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("company_id", "play_version_id", name="uq_company_play_version"),
    )

    # 13. evidence_items
    op.create_table(
        "evidence_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("opportunity_id", sa.String(36), sa.ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("code", sa.String(100), nullable=False, index=True),
        sa.Column("category", sa.String(50), nullable=False, index=True),
        sa.Column("evidence_text", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("verification_state", sa.String(50), nullable=False, server_default="verified"),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 14. people
    op.create_table(
        "people",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("first_name", sa.String(100), nullable=True),
        sa.Column("last_name", sa.String(100), nullable=True),
        sa.Column("full_name", sa.String(200), nullable=False, index=True),
        sa.Column("linkedin_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 15. person_roles
    op.create_table(
        "person_roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("person_id", sa.String(36), sa.ForeignKey("people.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("raw_title", sa.String(200), nullable=False),
        sa.Column("normalized_role", sa.String(100), nullable=False, index=True),
        sa.Column("seniority", sa.String(50), nullable=False, server_default="executive"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("source_evidence_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 16. compliance_policies
    op.create_table(
        "compliance_policies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False, index=True),
        sa.Column("jurisdiction", sa.String(10), nullable=False),
        sa.Column("rules_config_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 17. compliance_decisions
    op.create_table(
        "compliance_decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("opportunity_id", sa.String(36), sa.ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("policy_code", sa.String(50), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("reasons_json", sa.JSON(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 18. score_snapshots
    op.create_table(
        "score_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("opportunity_id", sa.String(36), sa.ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("total_score", sa.Float(), nullable=False),
        sa.Column("hard_gates_passed", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("breakdown_json", sa.JSON(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 19. campaigns
    op.create_table(
        "campaigns",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("play_version_id", sa.String(36), sa.ForeignKey("market_play_versions.id"), nullable=False, index=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("daily_send_cap", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 20. touches
    op.create_table(
        "touches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id"), nullable=False, index=True),
        sa.Column("opportunity_id", sa.String(36), sa.ForeignKey("opportunities.id"), nullable=False, index=True),
        sa.Column("step_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("channel", sa.String(50), nullable=False, server_default="Email"),
        sa.Column("status", sa.String(50), nullable=False, server_default="scheduled"),
        sa.Column("subject", sa.String(255), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("evidence_citations_json", sa.JSON(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("touches")
    op.drop_table("campaigns")
    op.drop_table("score_snapshots")
    op.drop_table("compliance_decisions")
    op.drop_table("compliance_policies")
    op.drop_table("person_roles")
    op.drop_table("people")
    op.drop_table("evidence_items")
    op.drop_table("opportunities")
    op.drop_table("market_play_versions")
    op.drop_table("source_records")
    op.drop_table("source_runs")
    op.drop_table("source_connectors")
    op.drop_table("company_estimates")
    op.drop_table("company_domains")
    op.drop_table("company_locations")
    op.drop_table("company_classifications")
    op.drop_table("company_names")
    op.drop_table("company_identifiers")
    op.drop_table("companies")
