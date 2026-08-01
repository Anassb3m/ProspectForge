"""Table-driven proof for score/ranking separation and hard readiness gates."""

from datetime import datetime, timedelta, timezone

import pytest

from app.models import EvidenceItem
from app.services.scoring_v4 import evaluate_field_ops_profile


NOW = datetime(2026, 7, 31, tzinfo=timezone.utc)


def evidence(
    category: str = "operations",
    *,
    expires_at: datetime | None = None,
    contradiction: str = "none",
) -> EvidenceItem:
    return EvidenceItem(
        id=f"evidence-{category}-{expires_at}-{contradiction}",
        company_id="company-1",
        opportunity_id="opportunity-1",
        code=f"TEST.{category.upper()}",
        category=category,
        evidence_text=f"Source-backed {category} evidence",
        source_type="official_registry",
        confidence=0.9,
        strength=0.9,
        verification_state="source_observed",
        contradiction_status=contradiction,
        is_active=True,
        expires_at=expires_at,
    )


BASE = {
    "company_status": "active",
    "jurisdiction": "FR",
    "identity_state": "clear",
    "identifier_verified": True,
    "relevant_classification": True,
    "classification_override": False,
    "verified_domain": True,
    "evidence": [evidence("operations"), evidence("trigger")],
    "buyer_role": True,
    "usable_contact": True,
    "contact_provenance": True,
    "suppressed": False,
    "compliance_allowed": True,
    "human_approved": True,
    "location_count": 2,
    "now": NOW,
}


@pytest.mark.parametrize(
    ("overrides", "readiness", "failed_gate"),
    [
        ({}, "CONTACT_READY", None),
        (
            {"relevant_classification": False},
            "ICP_REJECTED",
            "relevant_classification",
        ),
        ({"company_status": "inactive"}, "ICP_REJECTED", "active_legal_entity"),
        (
            {"verified_domain": False},
            "CONTACT_RESEARCH_ELIGIBLE",
            "verified_official_domain",
        ),
        ({"suppressed": True}, "SUPPRESSED", "suppression_check_passed"),
        (
            {"identity_state": "severe_contradiction"},
            "IDENTITY_REVIEW",
            "no_severe_identity_contradiction",
        ),
        (
            {"buyer_role": True, "usable_contact": True, "contact_provenance": True},
            "CONTACT_READY",
            None,
        ),
        (
            {"buyer_role": False, "usable_contact": False, "contact_provenance": False},
            "CONTACT_RESEARCH_ELIGIBLE",
            "contact_path_usable",
        ),
        (
            {
                "evidence": [
                    evidence("operations", expires_at=NOW - timedelta(days=1))
                ]
            },
            "EVIDENCE_INSUFFICIENT",
            "minimum_operational_evidence",
        ),
        (
            {"human_approved": False},
            "HUMAN_REVIEW_REQUIRED",
            "human_approval",
        ),
    ],
    ids=[
        "ideal-field-service-company",
        "irrelevant-software-company",
        "inactive-entity",
        "strong-fit-no-domain",
        "high-score-suppressed",
        "conflicting-identifiers",
        "role-based-contact-path",
        "guessed-email-only",
        "stale-evidence",
        "human-approval-transition",
    ],
)
def test_field_ops_readiness_table(overrides, readiness, failed_gate):
    inputs = {**BASE, **overrides}
    result = evaluate_field_ops_profile(**inputs)

    assert result["readiness_state"] == readiness
    assert result["hard_gates_passed"] is (readiness == "CONTACT_READY")
    if failed_gate:
        assert result["hard_gates"][failed_gate] is False


def test_numeric_score_cannot_override_suppression_or_human_gate():
    suppressed = evaluate_field_ops_profile(**{**BASE, "suppressed": True})
    unapproved = evaluate_field_ops_profile(**{**BASE, "human_approved": False})

    assert suppressed["total_score"] > 0
    assert suppressed["readiness_state"] == "SUPPRESSED"
    assert unapproved["total_score"] > 0
    assert unapproved["readiness_state"] == "HUMAN_REVIEW_REQUIRED"
