"""Regression coverage for the deployable reliability hotfix."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from celery.exceptions import Retry
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import services
from app.config import Settings
from app.discovery.annuaire import (
    discover_companies_for_play_checkpointed,
    registry_discovery_plan,
)
from app.jobs import ingestion
from app.models import (
    Company,
    FailedWorkItem,
    MarketPlayVersion,
    Opportunity,
    PipelineRun,
    Prospect,
    SourceCheckpoint,
    SourceRecord,
    WorkItem,
)
from app.services.pipeline_runs import create_pipeline_run
from app.services.recovery import recover_stale_work_items
from app.services.run_lock import acquisition_run_lock, acquisition_run_locks
from app.sources.base import RawSourceRecord
from app.workers.celery_app import build_beat_schedule
from app.workers.tasks import (
    extract_website_evidence,
    ingest_market_play,
    ingest_recover_stale_work,
)


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


def test_ingestion_worker_retries_transient_run_failure(monkeypatch):
    captured = {}

    async def fail_run(**kwargs):
        raise RuntimeError("temporary upstream failure")

    def fake_retry(**kwargs):
        captured.update(kwargs)
        raise Retry("retry scheduled")

    monkeypatch.setattr(ingestion, "run_ingestion", fail_run)
    monkeypatch.setattr(ingest_market_play, "retry", fake_retry)
    with pytest.raises(Retry, match="retry scheduled"):
        ingest_market_play.run(
            play_code="FIELD_OPERATIONS_FR_V2",
            mode="registry",
            discovery_limit=50,
            run_contacts=False,
            pipeline_run_id="run-retry-proof",
        )
    assert isinstance(captured["exc"], RuntimeError)
    assert captured["countdown"] == 5


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
async def test_raw_failure_retry_endpoint_queues_durable_reconciler(
    client, auth_headers, engine, monkeypatch
):
    from app.workers.celery_app import celery_app

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        failure = FailedWorkItem(
            original_work_item_id="raw-endpoint-proof",
            task_name="persist_registry_record",
            source_name="registry",
            source_record_key="12345678900001",
            payload={},
            error_category="UPSTREAM_TIMEOUT",
            retryable=True,
            error_message="temporary upstream failure",
        )
        session.add(failure)
        await session.commit()
        failure_id = failure.id
    sent = {}

    def fake_send_task(task_name, *, args, kwargs):
        sent.update(task_name=task_name, args=args, kwargs=kwargs)

    monkeypatch.setattr(celery_app, "send_task", fake_send_task)
    response = await client.post(
        f"/api/operations/failed-work/{failure_id}/retry", headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert sent == {
        "task_name": "app.workers.tasks.ingest_failed_raw_source",
        "args": [failure_id],
        "kwargs": {},
    }
    async with factory() as session:
        persisted = await session.get(FailedWorkItem, failure_id)
        assert persisted.resolved is False
        assert persisted.retry_count == 1
        assert "success not yet confirmed" in persisted.resolution_note


@pytest.mark.asyncio
async def test_stale_recovery_endpoint_reports_broker_acceptance_only(
    client, auth_headers, monkeypatch
):
    monkeypatch.setattr(
        ingest_recover_stale_work,
        "delay",
        lambda: SimpleNamespace(id="stale-recovery-task"),
    )
    response = await client.post(
        "/api/operations/recover-stale-work", headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "accepted",
        "task_id": "stale-recovery-task",
        "message": "Stale-work recovery accepted; completion is not yet confirmed",
    }


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
    assert checkpoint["version"] == 2
    assert checkpoint["partition"] == 0
    assert checkpoint["page"] == 1
    assert checkpoint["offset"] == 2
    assert len(checkpoint["plan_fingerprint"]) == 16
    assert {row["siren"] for row in first}.isdisjoint(
        {row["siren"] for row in second}
    )
    assert next_checkpoint != checkpoint


def test_registry_plan_uses_v2_classification_codes():
    from app.plays import get_play

    partitions, fingerprint = registry_discovery_plan(
        get_play("FIELD_OPERATIONS_FR_V2"), max_pages_per_partition=1000
    )
    assert partitions == [
        ("naf", "4322B"),
        ("naf", "4321A"),
        ("naf", "3312Z"),
        ("naf", "3313Z"),
        ("naf", "3314Z"),
        ("naf", "8020Z"),
        ("naf", "8110Z"),
    ]
    assert len(fingerprint) == 16


@pytest.mark.asyncio
async def test_registry_progresses_across_thousands_without_replay(monkeypatch):
    async def fake_search(**kwargs):
        page = kwargs["page"]
        return {
            "results": [
                {
                    "siren": f"{page:03d}{index:06d}",
                    "nom_complet": f"Company {page}-{index}",
                    "activite_principale": "43.22B",
                    "siege": {"siret": f"{page:03d}{index:011d}"},
                }
                for index in range(25)
            ],
            "total_pages": 200,
        }

    monkeypatch.setattr("app.discovery.annuaire.search_companies", fake_search)
    first, checkpoint, exhausted = await discover_companies_for_play_checkpointed(
        "FIELD_OPERATIONS_FR_V2",
        max_results=1000,
        pages_per_query=200,
        checkpoint={},
    )
    second, next_checkpoint, next_exhausted = (
        await discover_companies_for_play_checkpointed(
            "FIELD_OPERATIONS_FR_V2",
            max_results=1000,
            pages_per_query=200,
            checkpoint=checkpoint,
        )
    )
    assert len(first) == len(second) == 1000
    assert exhausted is next_exhausted is False
    assert checkpoint["page"] == 41
    assert next_checkpoint["page"] == 81
    assert {row["siren"] for row in first}.isdisjoint(
        {row["siren"] for row in second}
    )


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
    assert await db_session.scalar(select(func.count(SourceRecord.id))) == 3
    statuses = dict(
        (
            await db_session.execute(
                select(SourceRecord.processing_status, func.count(SourceRecord.id))
                .group_by(SourceRecord.processing_status)
            )
        ).all()
    )
    assert statuses == {"failed": 1, "normalized": 2}
    checkpoint = await db_session.scalar(select(SourceCheckpoint))
    assert checkpoint is not None
    assert checkpoint.high_water_mark == '{"offset": 0, "partition": 1}'


@pytest.mark.asyncio
async def test_stale_work_recovery_requeues_or_dead_letters_truthfully(
    db_session: AsyncSession,
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
    now = datetime.now(timezone.utc)
    recoverable = WorkItem(
        pipeline_run_id=run.id,
        idempotency_key="stale:recoverable",
        task_name="extract_website_evidence",
        payload={"prospect_id": 10, "source_name": "registry"},
        status="running",
        retry_count=0,
        max_retries=3,
        lock_lease_until=now - timedelta(minutes=1),
    )
    exhausted = WorkItem(
        pipeline_run_id=run.id,
        idempotency_key="stale:exhausted",
        task_name="extract_website_evidence",
        payload={"prospect_id": 11, "source_name": "registry"},
        status="running",
        retry_count=3,
        max_retries=3,
        lock_lease_until=now - timedelta(minutes=1),
    )
    unsupported = WorkItem(
        pipeline_run_id=run.id,
        idempotency_key="stale:unsupported",
        task_name="unknown_stage",
        payload={"prospect_id": 12, "source_name": "registry"},
        status="running",
        retry_count=0,
        max_retries=3,
        lock_lease_until=now - timedelta(minutes=1),
    )
    db_session.add_all([recoverable, exhausted, unsupported])
    await db_session.commit()

    result = await recover_stale_work_items(db_session, now=now)

    assert result == {
        "scanned": 3,
        "recovered": 1,
        "exhausted": 1,
        "unsupported": 1,
        "pipeline_run_ids": [run.id],
    }
    await db_session.refresh(recoverable)
    await db_session.refresh(exhausted)
    await db_session.refresh(unsupported)
    assert (recoverable.status, recoverable.retry_count) == ("pending", 1)
    assert (exhausted.status, exhausted.retry_count) == ("failed", 4)
    assert (unsupported.status, unsupported.retry_count) == ("failed", 1)
    failures = list(
        (
            await db_session.execute(
                select(FailedWorkItem).where(
                    FailedWorkItem.original_work_item_id.in_(
                        [exhausted.id, unsupported.id]
                    )
                )
            )
        )
        .scalars()
        .all()
    )
    assert {item.error_category for item in failures} == {
        "TASK_RETRIES_EXHAUSTED",
        "STALE_TASK_UNSUPPORTED",
    }


@pytest.mark.asyncio
async def test_raw_failure_reconciliation_uses_persisted_record(
    db_session: AsyncSession, engine, monkeypatch
):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(ingestion, "async_session_factory", factory)
    run = await create_pipeline_run(
        db_session,
        play_code="FIELD_OPERATIONS_FR_V2",
        mode="registry",
        discovery_limit=1,
        run_contacts=False,
        skip_sirene=True,
        requested_by="test",
    )
    record = SourceRecord(
        pipeline_run_id=run.id,
        external_id="12345678900001",
        record_type="registry_company",
        payload_json={
            "normalized": {
                "siren": "123456789",
                "siret": "12345678900001",
                "company_name": "Recovered SARL",
                "naf_code": "4322B",
                "company_size": "11-50",
            }
        },
        payload_hash="a" * 64,
        processing_status="failed",
        error_category="UPSTREAM_TIMEOUT",
    )
    failure = FailedWorkItem(
        original_work_item_id="raw-proof",
        pipeline_run_id=run.id,
        task_name="persist_registry_record",
        source_name="registry",
        source_record_key="12345678900001",
        payload={},
        error_category="UPSTREAM_TIMEOUT",
        retryable=True,
        error_message="temporary failure",
    )
    db_session.add_all([record, failure])
    await db_session.commit()
    failure_id = failure.id
    record_id = record.id

    async def fake_upsert(session, *, base, play_code, **kwargs):
        prospect = Prospect(
            company_name=base["company_name"],
            sector="Field Services",
            company_size=base["company_size"],
            signal_type="REGISTRY_FIELD",
            data_source="test",
            source="Annuaire",
            siren=base["siren"],
            siret=base["siret"],
            market_play_code=play_code,
        )
        session.add(prospect)
        await session.flush()
        return prospect, True, "created"

    async def fake_dispatch(session, *, pipeline_run_id):
        return {"pending": 1, "dispatched": 1, "dispatch_errors": 0}

    monkeypatch.setattr(ingestion, "upsert_prospect", fake_upsert)
    monkeypatch.setattr(ingestion, "_dispatch_enrichment_work", fake_dispatch)

    result = await ingestion.reconcile_failed_raw_item(failure_id)

    assert result["status"] == "resolved"
    assert result["source_records"] == 1
    db_session.expire_all()
    resolved_failure = await db_session.get(FailedWorkItem, failure_id)
    resolved_record = await db_session.get(SourceRecord, record_id)
    assert resolved_failure.resolved is True
    assert resolved_failure.retry_count == 1
    assert resolved_record.processing_status == "normalized"
    assert await db_session.scalar(select(func.count(WorkItem.id))) == 1


@pytest.mark.asyncio
async def test_raw_registry_stage_replay_is_idempotent(db_session: AsyncSession):
    run = await create_pipeline_run(
        db_session,
        play_code="FIELD_OPERATIONS_FR_V2",
        mode="registry",
        discovery_limit=2,
        run_contacts=False,
        skip_sirene=True,
        requested_by="test",
    )
    companies = [
        {
            "siren": "123456789",
            "siret": "12345678900001",
            "company_name": "Raw One",
            "naf_code": "4322B",
            "_source_record": {
                "record": {"siren": "123456789", "nom_complet": "Raw One"},
                "metadata": {"page": 1, "offset": 0},
            },
        },
        {
            "siren": "987654321",
            "siret": "98765432100001",
            "company_name": "Raw Two",
            "naf_code": "4322B",
            "_source_record": {
                "record": {"siren": "987654321", "nom_complet": "Raw Two"},
                "metadata": {"page": 1, "offset": 1},
            },
        },
    ]
    first_count, first_duplicates = await ingestion._persist_registry_raw_records(
        db_session,
        pipeline_run_id=run.id,
        companies=companies,
        batch_size=25,
    )
    replay_count, replay_duplicates = await ingestion._persist_registry_raw_records(
        db_session,
        pipeline_run_id=run.id,
        companies=companies,
        batch_size=25,
    )
    assert (first_count, first_duplicates) == (2, 0)
    assert (replay_count, replay_duplicates) == (2, 2)
    records = list(await db_session.scalars(select(SourceRecord).order_by(SourceRecord.id)))
    assert len(records) == 2
    assert records[0].payload_json["raw"]["nom_complet"] == "Raw One"
    assert records[0].processing_status == "pending"


@pytest.mark.asyncio
async def test_decp_awards_are_raw_persisted_aggregated_and_replay_safe(
    db_session: AsyncSession, monkeypatch
):
    run = await create_pipeline_run(
        db_session,
        play_code="FIELD_OPERATIONS_FR_V2",
        mode="decp",
        discovery_limit=3,
        run_contacts=False,
        skip_sirene=True,
        requested_by="test",
    )
    await db_session.commit()

    raw_awards = [
        RawSourceRecord(
            connector_code="decp",
            external_id=f"decp-award-{index}",
            record_type="award",
            observed_at=datetime(2026, 7, 20 + index, tzinfo=timezone.utc),
            payload={
                "id": f"award-{index}",
                "dateAttribution": f"2026-07-{20 + index:02d}",
                "_date": f"2026-07-{20 + index:02d}",
                "codeCPV": "50710000",
                "objetMarche": f"Maintenance {index}",
                "titulaire_siret": (
                    "12345678900001" if index < 2 else "98765432100001"
                ),
                "titulaire_nom": "Company One" if index < 2 else "Company Two",
                "montant": 1000.0 + index,
                "acheteur_nom": "Buyer",
                "siren": "123456789" if index < 2 else "987654321",
                "montant_quality": "ok",
                "_source_external_id": f"decp-award-{index}",
                "_source_event_date": f"2026-07-{20 + index:02d}",
            },
        )
        for index in range(3)
    ]

    async def fake_discover(self, checkpoint, limit, query_params):
        return (
            raw_awards,
            {
                "version": 1,
                "plan_fingerprint": "decp-test-plan",
                "high_water": {
                    "event_date": "2026-07-22",
                    "external_id": "decp-award-2",
                },
                "backfill_cursor": {
                    "event_date": "2026-07-20",
                    "external_id": "decp-award-0",
                },
                "backfill_exhausted": True,
            },
            True,
        )

    async def fake_upsert(session, *, base, play_code, **kwargs):
        prospect = Prospect(
            company_name=base["company_name"],
            sector="Field Services",
            company_size="11-50",
            signal_type="PUBLIC_AWARD",
            data_source="test",
            source="DECP",
            siren=base["siren"],
            siret=base["siret"],
            market_play_code=play_code,
        )
        session.add(prospect)
        await session.flush()
        return prospect, True, "created"

    monkeypatch.setattr("app.sources.decp_adapter.DecpAdapter.discover", fake_discover)
    monkeypatch.setattr(ingestion, "upsert_prospect", fake_upsert)

    first = await ingestion.ingest_decp(
        db_session,
        days_back=90,
        max_companies=3,
        play_code="FIELD_OPERATIONS_FR_V2",
        skip_sirene=True,
        pipeline_run_id=run.id,
    )
    replay = await ingestion.ingest_decp(
        db_session,
        days_back=90,
        max_companies=3,
        play_code="FIELD_OPERATIONS_FR_V2",
        skip_sirene=True,
        pipeline_run_id=run.id,
    )

    assert first["awards"] == 3
    assert first["raw_persisted"] == 3
    assert first["companies"] == 2
    assert first["created"] == 2
    assert first["errors"] == 0
    assert replay["raw_persisted"] == 3
    assert replay["duplicates"] == 3
    assert replay["created"] == 2
    assert await db_session.scalar(select(func.count(SourceRecord.id))) == 3
    assert await db_session.scalar(select(func.count(Prospect.id))) == 2
    outcomes = dict(
        (
            await db_session.execute(
                select(SourceRecord.processing_result, func.count(SourceRecord.id))
                .group_by(SourceRecord.processing_result)
            )
        ).all()
    )
    assert outcomes == {"aggregated": 1, "created": 2}


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
