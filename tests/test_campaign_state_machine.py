"""Tests for Campaign Sequence State Machine."""

from app.services.campaign_engine import evaluate_campaign_stop_rules


def test_stop_rules_on_reply():
    should_stop, reason = evaluate_campaign_stop_rules(has_replied=True)
    assert should_stop is True
    assert reason == "prospect_replied"


def test_stop_rules_on_bounce():
    should_stop, reason = evaluate_campaign_stop_rules(is_bounced=True)
    assert should_stop is True
    assert reason == "email_bounced"


def test_stop_rules_no_stop():
    should_stop, reason = evaluate_campaign_stop_rules()
    assert should_stop is False
    assert reason is None
