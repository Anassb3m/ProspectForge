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


# ── P0 Regression: Readiness Never Bypasses Pain Gate ────────────────────────


def test_high_score_without_pain_cannot_be_contact_ready():
    """Even with very high fit/trigger/authority/awards, if pain is not confirmed
    by human review or explicit evidence, contact_ready is blocked."""
    p = _base(
        naf_code="4322B",
        company_size="51-200",
        contact_confidence="deliverable",
        contact_discovery_state="inferred",
        latest_qualification=None,  # No human review yet
        manual_review_state="unreviewed",
        award_history=[
            {"date": datetime.now(timezone.utc).date().isoformat(), "montant": 200000, "objet": "Gros chantier"},
            {"date": datetime.now(timezone.utc).date().isoformat(), "montant": 150000, "objet": "Second lot"},
        ],
        evidence_json=[
            {
                "category": "trigger",
                "signal_type": "PUBLIC_AWARD_RECENT",
                "label": "Recent award",
                "evidence_text": "2 awards, total 350k",
                "source_type": "decp",
                "confidence": 80,
                "strength": 75,
            }
        ],
        notes="",  # No pain language
        signal_details="2 awards · 350k€",
    )
    r = score_prospect_v3(p)
    # Trigger should be high from multi-award
    assert r.trigger >= 40
    # Pain should be low — awards are timing, not pain, and no human confirmed it
    assert r.pain < 40
    # Must NOT be contact_ready (multiple reasons: no human review, no pain)
    assert r.readiness_state != "contact_ready"


def test_opted_out_prospect_is_suppressed():
    """opted_out should always force suppressed readiness state."""
    r = score_prospect_v3(_base(opted_out=True, notes="excel double saisie"))
    assert r.readiness_state == "suppressed"


def test_guessed_email_blocks_contact_usable():
    """Guessed/pattern-only email should not satisfy contact_usable gate."""
    review = SimpleNamespace(
        decision="accept",
        fit_confirmed=True,
        pain_confirmed=True,
        trigger_confirmed=True,
        buyer_confirmed=True,
        contact_confirmed=True,
        offer_match_confirmed=True,
    )
    r = score_prospect_v3(
        _base(
            contact_confidence="domain_and_pattern_only",
            contact_discovery_state="guessed",
            notes="excel et planning manuel",
            latest_qualification=review,
            evidence_json=[
                {
                    "category": "pain",
                    "signal_type": "EXCEL_OR_MANUAL_REPORTING_MENTION",
                    "label": "Manual processes",
                    "evidence_text": "excel et planning manuel",
                    "source_type": "manual",
                    "strength": 70,
                    "manually_confirmed": True,
                }
            ],
        )
    )
    assert r.readiness_state != "contact_ready"
    assert "contact_required" in r.readiness_failures


def test_catch_all_email_requires_review():
    """catch_all confidence should not satisfy contact_usable."""
    r = score_prospect_v3(
        _base(
            contact_confidence="catch_all",
            contact_discovery_state="guessed",
        )
    )
    # Contact should not be considered usable
    assert "contact_required" in r.readiness_failures or r.readiness_state != "contact_ready"


def test_single_source_blocks_readiness():
    """Only one source type should trigger insufficient_independent_sources failure."""
    r = score_prospect_v3(
        _base(
            evidence_json=[],
            award_history=[],
            notes="",
            signal_details="",
            data_source="manual",
        )
    )
    assert "insufficient_independent_sources" in r.readiness_failures or r.readiness_state != "contact_ready"


def test_multiple_pain_keywords_compound():
    """Multiple pain signals should push pain score higher."""
    r = score_prospect_v3(
        _base(
            award_history=[],
            signal_details="",
            notes="planning techniciens via excel et double saisie devis manuels whatsapp rapport",
            evidence_json=[
                {
                    "category": "pain",
                    "signal_type": "EXCEL_OR_MANUAL_REPORTING_MENTION",
                    "label": "Excel/manual reporting",
                    "evidence_text": "excel et double saisie devis manuels",
                    "source_type": "manual",
                    "strength": 70,
                },
                {
                    "category": "pain",
                    "signal_type": "DISJOINTED_TOOLS_MENTION",
                    "label": "WhatsApp usage",
                    "evidence_text": "whatsapp rapport",
                    "source_type": "manual",
                    "strength": 60,
                },
            ],
        )
    )
    assert r.pain >= 40


def test_it_naf_penalized_in_field_service_play():
    """IT/software NAF codes should receive fit penalties in field-service play."""
    r = score_prospect_v3(
        _base(
            naf_code="6201Z",  # IT consultancy
            company_size="51-200",
        )
    )
    # Field service play excludes 62xx NAF
    assert r.fit < 55


def test_readiness_evaluate_suppressed_overrides_all():
    """Suppressed flag should override all other readiness logic."""
    from app.scoring_v3 import evaluate_readiness

    state, failures = evaluate_readiness(
        fit=100, pain=100, trigger=100, authority=100,
        data_quality=100, signal_count=10, source_type_count=5,
        human_accepted=True, suppressed=True,
        contact_usable=True, offer_ok=True,
        config={},
    )
    assert state == "suppressed"


def test_readiness_human_required_blocks_contact_ready():
    """Even with all scores passing, missing human review blocks contact_ready."""
    from app.scoring_v3 import evaluate_readiness

    state, failures = evaluate_readiness(
        fit=80, pain=60, trigger=50, authority=60,
        data_quality=70, signal_count=5, source_type_count=3,
        human_accepted=False, suppressed=False,
        contact_usable=True, offer_ok=True,
        config={"human_review_required": True},
    )
    assert state == "human_review_required"
    assert "human_review_required" in failures


@pytest.mark.asyncio
async def test_upsert_evidence_idempotency():
    from app.commercial import upsert_evidence
    from app.models import EvidenceSignal, Prospect
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.database import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 1. Setup prospect
        p = Prospect(
            company_name="Test Corp",
            sector="Test Sector",
            company_size="11-50",
            signal_type="PUBLIC_AWARD",
            email="test@corp.fr",
            data_source="DECP",
            source="manual",
            market_play_code="FIELD_SERVICE_OPERATIONS_FR",
            manual_review_state="unreviewed",
            readiness_state="research_required"
        )
        session.add(p)
        await session.commit()
        await session.refresh(p)

        evidence_items = [
            {
                "category": "trigger",
                "signal_type": "PUBLIC_AWARD_RECENT",
                "evidence_text": "Won a contract",
                "source_type": "decp",
                "confidence": 80,
                "strength": 75,
            }
        ]

        # 2. First ingestion -> should add 1
        added1 = await upsert_evidence(session, p.id, evidence_items)
        assert added1 == 1

        # 3. Second ingestion of the same data -> should add 0
        added2 = await upsert_evidence(session, p.id, evidence_items)
        assert added2 == 0

    await engine.dispose()
