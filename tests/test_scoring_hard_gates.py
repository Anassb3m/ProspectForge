"""Focused hard-gate checks against the single canonical scoring engine."""

from datetime import datetime, timezone

from app.models import EvidenceItem
from app.services.scoring_v4 import evaluate_field_ops_profile


def _operational_evidence() -> list[EvidenceItem]:
    return [
        EvidenceItem(
            id="operations-proof",
            company_id="company-proof",
            opportunity_id="opportunity-proof",
            code="OPERATIONS.COMPLEXITY.MULTI_BRANCH",
            category="operations",
            evidence_text="Official source shows three establishments",
            source_type="official_registry",
            confidence=0.9,
            strength=0.9,
            verification_state="source_observed",
            contradiction_status="none",
            is_active=True,
        )
    ]


def _evaluate(**overrides):
    values = {
        "company_status": "active",
        "jurisdiction": "FR",
        "identity_state": "clear",
        "identifier_verified": True,
        "relevant_classification": True,
        "classification_override": False,
        "verified_domain": True,
        "evidence": _operational_evidence(),
        "buyer_role": True,
        "usable_contact": True,
        "contact_provenance": True,
        "suppressed": False,
        "compliance_allowed": True,
        "human_approved": True,
        "location_count": 3,
        "now": datetime(2026, 8, 1, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return evaluate_field_ops_profile(**values)


def test_hard_gates_pass_only_with_complete_inputs():
    result = _evaluate()
    assert result["hard_gates_passed"] is True
    assert result["readiness_state"] == "CONTACT_READY"


def test_hard_gates_fail_inactive_entity_without_zeroing_rank_explanation():
    result = _evaluate(company_status="dissolved")
    assert result["hard_gates_passed"] is False
    assert result["hard_gates"]["active_legal_entity"] is False
    assert result["readiness_state"] == "ICP_REJECTED"
    assert result["total_score"] > 0


def test_opportunity_dimensions_are_bounded_and_evidence_derived():
    result = _evaluate()
    assert 0 < result["dimensions"]["operational_complexity"] <= 20
    assert 0 <= result["dimensions"]["icp_fit"] <= 25
    assert result["evidence_refs"] == ["operations-proof"]
