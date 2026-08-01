"""Canonical identity and evidence write-path regression tests."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.commercial import upsert_evidence
from app.models import (
    Company,
    CompanyClassification,
    CompanyDomain,
    CompanyIdentifier,
    EvidenceItem,
    EvidenceSignal,
    Prospect,
    Opportunity,
    ScoreSnapshot,
)
from app.services import scoring_v4
from app.services.normalized import upsert_normalized_company


@pytest.mark.asyncio
async def test_normalized_identity_uses_official_ids_and_adds_missing_establishment(
    db_session: AsyncSession,
):
    first = await upsert_normalized_company(
        db_session,
        company_name="Canonical Maintenance",
        siren="123 456 789",
        siret="12345678900001",
        website="https://www.canonical.example/contact",
        payload={
            "naf_code": "43.22B",
            "website_source": "search_inference",
        },
        play_code="FIELD_OPERATIONS_FR_V2",
    )
    second = await upsert_normalized_company(
        db_session,
        company_name="Different Trade Name",
        siren="123456789",
        siret="12345678900019",
        payload={"naf_code": "4322B"},
        play_code="FIELD_OPERATIONS_FR_V2",
    )
    await db_session.flush()

    assert first.company_id == second.company_id
    assert await db_session.scalar(select(func.count(Company.id))) == 1
    company = await db_session.get(Company, first.company_id)
    assert (company.country_code, company.jurisdiction_code) == ("FR", "FR")
    identifiers = set(
        (
            await db_session.execute(
                select(
                    CompanyIdentifier.scheme,
                    CompanyIdentifier.value_normalized,
                )
            )
        ).all()
    )
    assert identifiers == {
        ("FR_SIREN", "123456789"),
        ("FR_SIRET", "12345678900001"),
        ("FR_SIRET", "12345678900019"),
    }
    classification = await db_session.scalar(select(CompanyClassification))
    assert (classification.scheme, classification.code) == ("FR_NAF_REV2", "4322B")
    domain = await db_session.scalar(select(CompanyDomain))
    assert domain.domain_normalized == "canonical.example"
    assert domain.verification_state == "candidate"
    assert first.latest_score == 0
    assert first.outreach_ready is False


@pytest.mark.asyncio
async def test_siren_siret_contradiction_never_name_joins(db_session: AsyncSession):
    with pytest.raises(ValueError, match="identity contradiction"):
        await upsert_normalized_company(
            db_session,
            company_name="Collision Name",
            siren="123456789",
            siret="98765432100001",
            play_code="FIELD_OPERATIONS_FR_V2",
        )
    assert await db_session.scalar(select(func.count(Company.id))) == 0


@pytest.mark.asyncio
async def test_evidence_is_canonical_first_and_replay_safe(db_session: AsyncSession):
    opportunity = await upsert_normalized_company(
        db_session,
        company_name="Evidence Maintenance",
        siren="111222333",
        siret="11122233300001",
        payload={"naf_code": "4322B"},
        play_code="FIELD_OPERATIONS_FR_V2",
    )
    prospect = Prospect(
        company_name="Evidence Maintenance",
        sector="Field Services",
        company_size="11-50",
        signal_type="REGISTRY_FIELD",
        data_source="test",
        source="test",
        siren="111222333",
        siret="11122233300001",
        company_id=opportunity.company_id,
        opportunity_id=opportunity.id,
        market_play_code="FIELD_OPERATIONS_FR_V2",
    )
    db_session.add(prospect)
    await db_session.flush()
    item = {
        "category": "operations",
        "signal_type": "OPERATIONS.COMPLEXITY.MULTI_BRANCH",
        "label": "Multiple branches",
        "evidence_text": "Official registry shows multiple establishments",
        "source_type": "official_registry",
        "source_record_id": "registry:111222333",
        "confidence": 90,
        "strength": 80,
    }

    assert await upsert_evidence(db_session, prospect.id, [item]) == 1
    assert await upsert_evidence(db_session, prospect.id, [item]) == 0
    await db_session.flush()

    canonical = await db_session.scalar(select(EvidenceItem))
    projection = await db_session.scalar(select(EvidenceSignal))
    assert await db_session.scalar(select(func.count(EvidenceItem.id))) == 1
    assert await db_session.scalar(select(func.count(EvidenceSignal.id))) == 1
    assert canonical.fingerprint
    assert canonical.source_record_id == "registry:111222333"
    assert projection.canonical_evidence_id == canonical.id


@pytest.mark.asyncio
async def test_score_snapshot_is_idempotent_until_profile_revision_changes(
    db_session: AsyncSession, monkeypatch
):
    opportunity = await upsert_normalized_company(
        db_session,
        company_name="Score Maintenance",
        siren="444555666",
        siret="44455566600001",
        payload={"naf_code": "4322B"},
        play_code="FIELD_OPERATIONS_FR_V2",
    )
    prospect = Prospect(
        company_name="Score Maintenance",
        sector="Field Services",
        company_size="11-50",
        signal_type="REGISTRY_FIELD",
        data_source="test",
        source="test",
        siren="444555666",
        siret="44455566600001",
        company_id=opportunity.company_id,
        opportunity_id=opportunity.id,
        market_play_code="FIELD_OPERATIONS_FR_V2",
    )
    db_session.add(prospect)
    await db_session.flush()
    await upsert_evidence(
        db_session,
        prospect.id,
        [
            {
                "category": "operations",
                "signal_type": "OPERATIONS.COMPLEXITY.MULTI_BRANCH",
                "evidence_text": "Two official establishments",
                "source_type": "official_registry",
                "confidence": 90,
                "strength": 90,
            }
        ],
    )
    await db_session.flush()
    loaded = await db_session.scalar(
        select(Opportunity)
        .options(selectinload(Opportunity.company))
        .where(Opportunity.id == opportunity.id)
    )

    first = await scoring_v4.calculate_opportunity_score_v4(db_session, loaded)
    await db_session.flush()
    second = await scoring_v4.calculate_opportunity_score_v4(db_session, loaded)
    assert first.id == second.id
    assert await db_session.scalar(select(func.count(ScoreSnapshot.id))) == 1

    monkeypatch.setattr(scoring_v4, "PROFILE_VERSION", "2.0.1-test")
    changed = await scoring_v4.calculate_opportunity_score_v4(db_session, loaded)
    await db_session.flush()
    assert changed.id != first.id
    assert await db_session.scalar(select(func.count(ScoreSnapshot.id))) == 2
