"""Tests for Multi-Jurisdiction B2B Compliance Engine."""

from app.services.compliance_engine import evaluate_compliance_policy


def test_uk_compliance_corporate_allowed():
    res = evaluate_compliance_policy(jurisdiction="GB", legal_form="ltd")
    assert res.decision == "allow_send"
    assert res.policy_code == "uk_b2b_email_corporate_v1"
    assert res.opt_out_required is True


def test_uk_compliance_sole_trader_denied():
    res = evaluate_compliance_policy(jurisdiction="GB", legal_form="sole_trader")
    assert res.decision == "deny"
    assert "Sole trader" in res.reasons[0]


def test_fr_compliance_corporate_allowed():
    res = evaluate_compliance_policy(jurisdiction="FR", legal_form="sas")
    assert res.decision == "allow_send"
    assert res.policy_code == "fr_b2b_email_optout_v1"


def test_fr_compliance_auto_entrepreneur_denied():
    res = evaluate_compliance_policy(jurisdiction="FR", legal_form="auto_entrepreneur")
    assert res.decision == "deny"


def test_suppressed_target_denied():
    res = evaluate_compliance_policy(jurisdiction="GB", legal_form="ltd", is_suppressed=True)
    assert res.decision == "deny"
    assert "suppression list" in res.reasons[0]
