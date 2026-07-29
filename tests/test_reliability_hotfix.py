"""Regression coverage for the deployable reliability hotfix."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import services
from app.config import Settings
from app.discovery.annuaire import discover_companies_for_play_checkpointed
from app.jobs import ingestion
from app.models import (
    Company,
    FailedWorkItem,
    MarketPlayVersion,
    Opportunity,
    PipelineRun,
    Prospect,
    SourceCheckpoint,
    WorkItem,
)
from app.services.pipeline_runs import create_pipeline_run
from app.services.run_lock import acquisition_run_lock, acquisition_run_locks
from app.workers.celery_app import build_beat_schedule
from app.workers.tasks import extract_website_evidence, ingest_market_play


def _settings(**overrides) -> Settings:
    values = {
        "environment": "test",
        "enable_scheduler": False,
        "enable_nightly_ingestion": False,
        "enable_nightly_contact_discovery": False,
        "enable_score_reconciliation": False,
        "enable_retention_sweep": False,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_scheduler_is_empty_until_each_automation_is_enabled():
    assert build_beat_schedule(_settings()) == {}
    schedule = build_beat_schedule(
        _settings(
            enable_scheduler=True,
            enable_nightly_ingestion=True,
            active_market_play="FIELD_OPERATIONS_FR_V2",
            nightly_ingestion_limit=137,
        )
    )
    assert set(schedule) == {"nightly-ingestion"}
    assert schedule["nightly-ingestion"]["kwargs"] == {
        "play_code": "FIELD_OPERATIONS_FR_V2",
        "mode": "registry",
        "discovery_limit": 137,
        "run_contacts": False,
        "skip_sirene": False,
        "requested_by": "celery-beat",
    }


def test_worker_preserves_every_ingestion_option(monkeypatch):
    captured = {}

    async def fake_run_ingestion(**kwargs):
        captured.update(kwargs)
        return {"status": "completed", "run_id": kwargs["pipeline_run_id"]}

    monkeypatch.setattr(ingestion, "run_ingestion", fake_run_ingestion)
    result = ingest_market_play.run(
        play_code="FIELD_OPERATIONS_FR_V2",
        mode="registry",
        discovery_limit=73,
        run_contacts=False,
        skip_sirene=True,
        requested_by="operator@example.com",
        correlation_id="correlation-proof",
        pipeline_run_id="run-proof",
    )
    assert result == {"status": "completed", "run_id": "run-proof"}
    assert captured == {
        "play_code": "FIELD_OPERATIONS_FR_V2",
        "mode": "registry",
        "max_companies": 73,
        "run_contact_discovery": False,
        "skip_sirene": True,
        "requested_by": "operator@example.com",
        "correlation_id": "correlation-proof",
        "pipeline_run_id": "run-proof",
    }
    assert extract_website_evidence.max_retries == 3


@pytest.mark.asyncio
async def test_ingestion_rejects_inline_contact_discovery():
    with pytest.raises(ValueError, match="separate"):
        await ingestion.run_ingestion(
            play_code="FIELD_OPERATIONS_FR_V2",
            mode="registry",
            max_companies=1,
            run_contact_discovery=True,
        )


@pytest.mark.asyncio
async def test_authenticated_acquisition_health_is_truthful(
    client, auth_headers
):
    response = await client.get(
        "/api/operations/acquisition-health", headers=auth_headers
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["database"] == "healthy"
    assert payload["redis"] in {"healthy", "unavailable"}
    assert payload["workers"]["state"] == "unknown"
    assert payload["automation"]["scheduler"] is False
    assert payload["automation"]["automatic_outreach"] is False
    assert payload["sources"]["bodacc"] == "planned"
    assert payload["sources"]["companies_house"] == "misconfigured"


@pytest.mark.asyncio
async def test_registry_checkpoint_resumes_inside_page(monkeypatch):
    async def fake_search(**kwargs):
        page = kwargs["page"]
        return {
            "results": [
                {
                    "siren": f"{page:01d}{index:08d}",
                    "nom_complet": f"Company {page}-{index}",
                    "activite_principale": "43.21A",
                    "siege": {"siret": f"{page:01d}{index:013d}"},
                }
                for index in range(1, 4)
            ],
            "total_pages": 4,
        }

    monkeypatch.setattr("app.discovery.annuaire.search_companies", fake_search)
    first, checkpoint, exhausted = await discover_companies_for_play_checkpointed(
        "FIELD_OPERATIONS_FR_V2",
        max_results=2,
        pages_per_query=4,
        checkpoint={"partition": 0, "offset": 0},
    )
    second, next_checkpoint, _ = await discover_companies_for_play_checkpointed(
        "FIELD_OPERATIONS_FR_V2",
        max_results=2,
        pages_per_query=4,
        checkpoint=checkpoint,
    )
    assert exhausted is False
    assert checkpoint == {"partition": 0, "offset": 2}
    assert {row["siren"] for row in first}.isdisjoint(
        {row["siren"] for row in second}
    )
    assert next_checkpoint != checkpoint


@pytest.mark.asyncio
async def test_registry_item_failure_isolated_and_checkpoint_committed(
    db_session: AsyncSession, monkeypatch
):
    run = await create_pipeline_run(
        db_session,
        play_code="FIELD_OPERATIONS_FR_V2",
        mode="registry",
        discovery_limit=3,
        run_contacts=False,
        skip_sirene=True,
        requested_by="test",
    )
    await db_session.commit()
    companies = [
        {
            "siren": "111111111",
            "siret": "11111111100001",
            "company_name": "Good One",
            "naf_code": "4321A",
            "company_size": "11-50",
        },
        {
            "siren": "222222222",
            "siret": "22222222200002",
            "company_name": "Bad",
            "naf_code": "4321A",
            "company_size": "11-50",
        },
        {
            "siren": "333333333",
            "siret": "33333333300003",
            "company_name": "Good Two",
            "naf_code": "4321A",
            "company_size": "11-50",
        },
    ]

    async def fake_discovery(*args, **kwargs):
        return companies, {"partition": 1, "offset": 0}, False

    async def fake_upsert(session, *, base, play_code, **kwargs):
        if base["company_name"] == "Bad":
            raise ValueError("invalid test record")
        prospect = Prospect(
            company_name=base["company_name"],
            sector="Field Services",
            company_size="11-50",
            signal_type="REGISTRY_FIELD",
            data_source="test",
            source="test",
            siren=base["siren"],
            siret=base["siret"],
            market_play_code=play_code,
        )
        session.add(prospect)
        await session.flush()
        return prospect, True, "created"

    monkeypatch.setattr(
        ingestion, "discover_companies_for_play_checkpointed", fake_discovery
    )
    monkeypatch.setattr(ingestion, "upsert_prospect", fake_upsert)
    stats = await ingestion.ingest_registry(
        db_session,
        max_companies=3,
        play_code="FIELD_OPERATIONS_FR_V2",
        skip_sirene=True,
        pipeline_run_id=run.id,
    )

    assert stats["created"] == 2
    assert stats["errors"] == 1
    assert await db_session.scalar(select(func.count(Prospect.id))) == 2
    assert await db_session.scalar(select(func.count(FailedWorkItem.id))) == 1
    checkpoint = await db_session.scalar(select(SourceCheckpoint))
    assert checkpoint is not None
    assert checkpoint.high_water_mark == '{"offset": 0, "partition": 1}'


@pytest.mark.asyncio
async def test_partition_lock_prevents_overlap(engine):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as first_session, factory() as second_session:
        async with acquisition_run_lock(first_session, "same-partition") as first:
            assert first is True
            async with acquisition_run_lock(
                second_session, "same-partition"
            ) as second:
                assert second is False


@pytest.mark.asyncio
async def test_full_run_lock_set_conflicts_and_releases_partial_lock(engine):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    registry_key = "ingestion:FIELD_OPERATIONS_FR_V2:registry:all"
    decp_key = "ingestion:FIELD_OPERATIONS_FR_V2:decp:all"
    async with (
        factory() as registry_session,
        factory() as full_session,
        factory() as proof_session,
    ):
        async with acquisition_run_lock(
            registry_session, registry_key
        ) as registry_acquired:
            assert registry_acquired is True
            async with acquisition_run_locks(
                full_session, [decp_key, registry_key]
            ) as (full_acquired, blocked_key):
                assert full_acquired is False
                assert blocked_key == registry_key
            async with acquisition_run_lock(
                proof_session, decp_key
            ) as decp_released:
                assert decp_released is True


@pytest.mark.asyncio
async def test_queued_request_mismatch_fails_run_truthfully(
    engine, monkeypatch
):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        run = await create_pipeline_run(
            session,
            play_code="FIELD_OPERATIONS_FR_V2",
            mode="registry",
            discovery_limit=5,
            run_contacts=False,
            skip_sirene=False,
            requested_by="test",
        )
        await session.commit()
        run_id = run.id

    monkeypatch.setattr(ingestion, "async_session_factory", factory)
    with pytest.raises(ValueError, match="configuration mismatch"):
        await ingestion.run_ingestion(
            play_code="FIELD_OPERATIONS_FR_V2",
            mode="registry",
            max_companies=6,
            run_contact_discovery=False,
            pipeline_run_id=run_id,
        )
    async with factory() as session:
        refreshed = await session.get(PipelineRun, run_id)
        assert refreshed is not None
        assert refreshed.status == "failed"
        assert refreshed.error_categories_json == {"RUN_FAILED": 1}


@pytest.mark.asyncio
async def test_explicit_opportunity_bridge_never_joins_same_company_names(
    db_session: AsyncSession,
):
    play = MarketPlayVersion(
        play_code="FIELD_OPERATIONS_FR_V2",
        version="test",
        status="active",
    )
    first_company = Company(canonical_name="Same Display Name", country_code="FR")
    second_company = Company(canonical_name="Same Display Name", country_code="FR")
    db_session.add_all([play, first_company, second_company])
    await db_session.flush()
    first_opportunity = Opportunity(
        company_id=first_company.id,
        play_version_id=play.id,
        status="discovered",
    )
    second_opportunity = Opportunity(
        company_id=second_company.id,
        play_version_id=play.id,
        status="discovered",
    )
    db_session.add_all([first_opportunity, second_opportunity])
    await db_session.flush()
    first_legacy = Prospect(
        company_id=first_company.id,
        opportunity_id=first_opportunity.id,
        company_name="Same Display Name",
        sector="Field Services",
        company_size="11-50",
        signal_type="OTHER",
        data_source="test-one",
        source="Manual",
    )
    second_legacy = Prospect(
        company_id=second_company.id,
        opportunity_id=second_opportunity.id,
        company_name="Same Display Name",
        sector="Field Services",
        company_size="11-50",
        signal_type="OTHER",
        data_source="test-two",
        source="Manual",
    )
    db_session.add_all([first_legacy, second_legacy])
    await db_session.flush()

    projected = await services.get_prospect(db_session, first_opportunity.id)
    assert projected is not None
    assert projected.legacy_id == first_legacy.id
    assert projected.data_source == "test-one"


@pytest.mark.asyncio
async def test_enrichment_work_item_replay_is_idempotent(
    db_session: AsyncSession,
):
    run = await create_pipeline_run(
        db_session,
        play_code="FIELD_OPERATIONS_FR_V2",
        mode="registry",
        discovery_limit=1,
        run_contacts=False,
        skip_sirene=False,
        requested_by="test",
    )
    prospect = Prospect(
        company_name="Replay Test",
        sector="Field Services",
        company_size="11-50",
        signal_type="OTHER",
        data_source="test",
        source="Manual",
    )
    db_session.add(prospect)
    await db_session.flush()
    payload = {"siren": "123456789", "company_name": "Replay Test"}
    first, first_created = await ingestion._ensure_enrichment_work_item(
        db_session,
        pipeline_run_id=run.id,
        prospect_id=prospect.id,
        play_code="FIELD_OPERATIONS_FR_V2",
        source_name="registry",
        source_payload=payload,
        skip_sirene=False,
    )
    second, second_created = await ingestion._ensure_enrichment_work_item(
        db_session,
        pipeline_run_id=run.id,
        prospect_id=prospect.id,
        play_code="FIELD_OPERATIONS_FR_V2",
        source_name="registry",
        source_payload=payload,
        skip_sirene=False,
    )
    assert first.id == second.id
    assert first_created is True
    assert second_created is False
    assert await db_session.scalar(select(func.count(WorkItem.id))) == 1
