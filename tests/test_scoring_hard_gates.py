"""Tests for Hard-Gated Scoring Engine."""

from app.services.scoring_engine import calculate_opportunity_score, evaluate_hard_gates


def test_hard_gates_pass():
    res = evaluate_hard_gates(
        entity_status="active",
        legal_form="ltd",
        domain_verification_state="verified_primary",
        compliance_decision="allow_send",
    )
    assert res.passed is True
    assert len(res.rejection_reasons) == 0


def test_hard_gates_fail_dissolved():
    res = evaluate_hard_gates(
        entity_status="dissolved",
        legal_form="ltd",
    )
    assert res.passed is False
    assert "dissolved" in res.rejection_reasons[0]


def test_opportunity_score_calculation():
    hard_gate = evaluate_hard_gates(entity_status="active", legal_form="ltd")
    score_snap = calculate_opportunity_score(
        evidence_codes=["OPERATIONS.COMPLEXITY.MULTI_BRANCH", "OPERATIONS.COMPLEXITY.RECURRING_CONTRACTS"],
        has_buyer_identified=True,
        has_contact_path=True,
        hard_gate_result=hard_gate,
    )
    assert score_snap.hard_gates_passed is True
    assert score_snap.total_score == 90.0
    assert score_snap.breakdown["multi_branch_evidence"] == 15.0
