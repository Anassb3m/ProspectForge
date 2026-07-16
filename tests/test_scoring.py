"""Unit tests for the urgency scoring engine."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.scoring import apply_score, calculate_urgency_score, priority_from_score


def _prospect(**kwargs):
    defaults = dict(
        signal_type="OTHER",
        signal_details=None,
        decision_maker_title=None,
        company_size="1-10",
        naf_code=None,
        award_history=None,
        contact_confidence=None,
        outreach_events=[],
        urgency_score=50,
        priority_level="Medium",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _event(days_ago: int = 0):
    return SimpleNamespace(
        event_date=datetime.now(timezone.utc) - timedelta(days=days_ago)
    )


class TestPriorityFromScore:
    def test_high(self):
        assert priority_from_score(75) == "High"
        assert priority_from_score(100) == "High"

    def test_medium(self):
        assert priority_from_score(45) == "Medium"
        assert priority_from_score(74) == "Medium"

    def test_low(self):
        assert priority_from_score(0) == "Low"
        assert priority_from_score(44) == "Low"


class TestCalculateUrgencyScore:
    def test_base_score(self):
        p = _prospect()
        assert calculate_urgency_score(p, []) == 50

    def test_boamp_win(self):
        p = _prospect(signal_type="BOAMP_WIN")
        assert calculate_urgency_score(p, []) == 80  # 50+30

    def test_boamp_win_multiple(self):
        p = _prospect(signal_type="BOAMP_WIN", signal_details="Won multiple tenders")
        assert calculate_urgency_score(p, []) == 95  # 50+30+15

    def test_morocco_ops(self):
        p = _prospect(signal_type="MOROCCO_OPS")
        assert calculate_urgency_score(p, []) == 65

    def test_pain_post(self):
        p = _prospect(signal_type="PAIN_POST")
        assert calculate_urgency_score(p, []) == 70

    def test_senior_title(self):
        p = _prospect(decision_maker_title="Directeur commercial France")
        assert calculate_urgency_score(p, []) == 60

    def test_fondateur_title(self):
        p = _prospect(decision_maker_title="Fondateur & CEO")
        assert calculate_urgency_score(p, []) == 60

    def test_company_size_sweet_spot(self):
        p = _prospect(company_size="11-50")
        assert calculate_urgency_score(p, []) == 58  # 50+8
        p2 = _prospect(company_size="51-200")
        assert calculate_urgency_score(p2, []) == 58

    def test_decay_after_21_days(self):
        p = _prospect()
        events = [_event(days_ago=22)]
        assert calculate_urgency_score(p, events) == 40  # 50-10

    def test_no_decay_within_21_days(self):
        p = _prospect()
        events = [_event(days_ago=10)]
        assert calculate_urgency_score(p, events) == 50

    def test_clamp_max(self):
        p = _prospect(
            signal_type="BOAMP_WIN",
            signal_details="multiple awards cybersécurité",
            decision_maker_title="Fondateur",
            company_size="11-50",
            naf_code="6201Z",
            award_history=[{"montant": 100000, "date": "2026-06-01"}],
        )
        assert calculate_urgency_score(p, []) == 100

    def test_clamp_min(self):
        p = _prospect()
        score = calculate_urgency_score(p, [_event(30)])
        assert score == 40
        assert score >= 0

    def test_full_stack_high_priority(self):
        p = _prospect(
            signal_type="BOAMP_WIN",
            signal_details="multiple lots",
            decision_maker_title="Dirigeant",
            company_size="51-200",
        )
        score = calculate_urgency_score(p, [])
        assert score >= 75
        assert priority_from_score(score) == "High"

    def test_apply_score_mutates(self):
        p = _prospect(signal_type="PAIN_POST", company_size="11-50")
        apply_score(p, [])
        assert p.urgency_score == 78  # 50+20+8
        assert p.priority_level == "High"
