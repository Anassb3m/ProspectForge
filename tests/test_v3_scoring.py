"""V3 opportunity scoring + field-service play."""

from datetime import datetime, timezone
from types import SimpleNamespace

from app.discovery.naf import is_field_service_naf, is_it_cyber_naf, map_naf_to_sector
from app.scoring_v3 import compute_opportunity_score, evaluate_readiness, score_prospect_v3


def test_field_naf_not_it():
    assert is_field_service_naf("4322A")
    assert is_field_service_naf("33.12Z")
    assert is_it_cyber_naf("6201Z")
    assert not is_field_service_naf("6201Z")
    assert map_naf_to_sector("4322B") == "Field Services"


def test_opportunity_formula():
    s = compute_opportunity_score(
        fit=80, pain=70, trigger=60, authority=50, value=50, data_quality=70, penalties=0
    )
    assert 40 <= s <= 100


def test_readiness_requires_human():
    state, fails = evaluate_readiness(
        fit=70,
        pain=50,
        trigger=40,
        authority=50,
        data_quality=60,
        signal_count=3,
        source_type_count=2,
        human_accepted=False,
        suppressed=False,
        contact_usable=True,
        offer_ok=True,
        config={
            "fit_score_min": 55,
            "pain_score_min": 35,
            "trigger_score_min": 25,
            "authority_score_min": 40,
            "data_quality_min": 45,
            "active_signals_min": 2,
            "independent_source_types_min": 1,
            "human_review_required": True,
            "offer_asset_required": False,
        },
    )
    assert state == "human_review_required"
    assert "human_review_required" in fails


def test_score_field_service_winner():
    p = SimpleNamespace(
        company_name="Froid Pro Services",
        naf_code="4322B",
        company_size="11-50",
        signal_type="PUBLIC_AWARD",
        signal_details="2 award(s) · maintenance froid multisite",
        decision_maker_name="Jean Martin",
        decision_maker_title="Gérant",
        email=None,
        contact_confidence="none",
        contact_discovery_state=None,
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
        opted_out=False,
        market_play_code="FIELD_SERVICE_OPERATIONS_FR",
    )
    r = score_prospect_v3(p)
    assert r.fit >= 60
    assert r.trigger >= 40
    assert r.opportunity_score >= 40
    assert r.recommended_offer
    assert r.personalization_brief
    assert r.readiness_state in (
        "human_review_required",
        "contact_required",
        "research_required",
        "contact_ready",
    )


def test_it_company_penalized():
    p = SimpleNamespace(
        company_name="SoftDev SAS",
        naf_code="6201Z",
        company_size="51-200",
        signal_type="REGISTRY_IT",
        signal_details="software",
        decision_maker_name="Alice",
        decision_maker_title="CTO",
        email="a@x.fr",
        contact_confidence="likely",
        award_history=[],
        data_source="Annuaire",
        siren="111",
        website=None,
        notes="",
        evidence_json=[],
        dirigeants=[],
        manual_review_state="unreviewed",
        qualification_decision=None,
        opted_out=False,
        market_play_code=None,
    )
    r = score_prospect_v3(p)
    assert r.fit < 40 or r.penalties > 0
    assert "IT exclusion" in " ".join(r.badges) or r.opportunity_score < 55
