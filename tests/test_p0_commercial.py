"""P0 commercial-correctness tests — pain, gates, evidence, contacts."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.scoring_v3 import (
    evidence_fingerprint,
    score_prospect_v3,
)
from app.commercial import merge_evidence_json, validate_contact_confidence


def _base(**kwargs):
    d = dict(
        company_name="Froid Pro",
        naf_code="4322B",
        company_size="11-50",
        signal_type="PUBLIC_AWARD",
        signal_details="1 award · contrat maintenance froid",
        decision_maker_name="Jean Martin",
        decision_maker_title="Gérant",
        email="j.martin@froidpro.fr",
        contact_confidence="likely",
        contact_discovery_state="guessed",
        award_history=[
            {
                "date": datetime.now(timezone.utc).date().isoformat(),
                "montant": 80000,
                "objet": "Contrat maintenance froid commercial",
                "acheteur": "Région",
            }
        ],
        data_source="DECP",
        siren="123456789",
        website="https://froidpro.fr",
        notes="",
        evidence_json=[],
        dirigeants=[],
        manual_review_state="unreviewed",
        qualification_decision=None,
        latest_qualification=None,
        opted_out=False,
        market_play_code="FIELD_SERVICE_OPERATIONS_FR",
    )
    d.update(kwargs)
    return SimpleNamespace(**d)


def test_award_alone_does_not_create_pain_points():
    r = score_prospect_v3(_base())
    assert r.pain < 40, f"pain should not pass gate from award alone, got {r.pain}"
    assert r.trigger >= 40
    assert r.readiness_state != "contact_ready"


def test_maintenance_word_is_not_pain():
    r = score_prospect_v3(_base(signal_details="maintenance techniciens agences", award_history=[]))
    assert r.pain < 40


def test_excel_language_is_pain():
    r = score_prospect_v3(
        _base(
            award_history=[],
            signal_details="",
            notes="planning via excel et double saisie admin",
        )
    )
    assert r.pain >= 40


def test_incomplete_accept_not_human_gate():
    r = score_prospect_v3(_base(manual_review_state="accepted", qualification_decision="accept"))
    # Without full QualificationReview flags, incomplete accept is NOT enough
    assert "human_review_required" in r.readiness_failures or r.readiness_state != "contact_ready"


def test_full_qualification_accept_gate():
    review = SimpleNamespace(
        decision="accept",
        fit_confirmed=True,
        pain_confirmed=True,
        trigger_confirmed=True,
        buyer_confirmed=True,
        contact_confirmed=True,
        offer_match_confirmed=True,
    )
    p = _base(
        contact_confidence="deliverable",
        contact_discovery_state="inferred",
        notes="excel double saisie",
        latest_qualification=review,
        evidence_json=[
            {
                "category": "pain",
                "signal_type": "EXCEL_OR_MANUAL_REPORTING_MENTION",
                "label": "Excel reporting",
                "evidence_text": "notes: excel double saisie",
                "source_type": "manual",
                "strength": 70,
                "manually_confirmed": True,
            }
        ],
    )
    r = score_prospect_v3(p)
    assert r.pain >= 40
    from app.scoring_v3 import _is_full_human_accept

    assert _is_full_human_accept(p) is True


def test_generic_email_not_email_ready():
    r = score_prospect_v3(
        _base(
            contact_confidence="published_generic",
            contact_discovery_state="published",
            email="contact@froidpro.fr",
            notes="excel",
        )
    )
    assert "contact_required" in r.readiness_failures or r.readiness_state != "contact_ready"


def test_evidence_dedupe():
    items = [
        {"source_type": "decp", "signal_type": "PUBLIC_AWARD_RECENT", "evidence_text": "award A"},
        {"source_type": "decp", "signal_type": "PUBLIC_AWARD_RECENT", "evidence_text": "award A"},
    ]
    merged = merge_evidence_json([], items)
    assert len(merged) == 1


def test_fingerprint_stable():
    a = evidence_fingerprint(source_type="decp", signal_type="PUBLIC_AWARD_RECENT", evidence_text="x")
    b = evidence_fingerprint(source_type="decp", signal_type="PUBLIC_AWARD_RECENT", evidence_text="x")
    assert a == b


def test_contact_confidence_enum():
    assert validate_contact_confidence("deliverable") == "deliverable"
    with pytest.raises(ValueError):
        validate_contact_confidence("totally_verified_trust_me")
