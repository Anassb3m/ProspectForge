"""Regression tests for formerly dead UI controls and queued contact discovery."""

from unittest.mock import Mock

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.models import (
    Campaign,
    Company,
    ContactDiscoveryRun,
    MarketPlayVersion,
    Opportunity,
    OutreachEvent,
    PipelineRun,
    Touch,
    WorkItem,
)


@pytest.mark.asyncio
async def test_dashboard_control_aliases_resolve(
    client: AsyncClient, auth_headers: dict
):
    expected = {
        "/contacts/queue": "/sourcing?contact_filter=needs_review",
        "/campaigns/drafts": "/drafts",
        "/jobs": "/operations",
        "/settings": "/operations#automation",
    }
    for path, destination in expected.items():
        response = await client.get(path, headers=auth_headers, follow_redirects=False)
        assert response.status_code == 307, (path, response.text)
        assert response.headers["location"] == destination


@pytest.mark.asyncio
async def test_all_primary_authenticated_pages_render_without_gateway_errors(
    client: AsyncClient, auth_headers: dict
):
    pages = (
        "/",
        "/market-plays",
        "/sourcing",
        "/prospects",
        "/kanban",
        "/queue",
        "/follow-ups",
        "/import",
        "/operations",
        "/campaigns",
        "/drafts",
        "/inbox",
    )
    for path in pages:
        response = await client.get(path, headers=auth_headers)
        assert response.status_code == 200, (path, response.status_code, response.text[:500])


@pytest.mark.asyncio
async def test_contact_button_persists_one_run_and_never_crawls_in_request(
    client: AsyncClient,
    auth_headers: dict,
    sample_prospect_payload: dict,
    db_session,
    monkeypatch,
):
    created = (
        await client.post(
            "/api/prospects", json=sample_prospect_payload, headers=auth_headers
        )
    ).json()
    delay = Mock()
    monkeypatch.setattr("app.workers.tasks.contact_discovery_run.delay", delay)

    first = await client.post(
        f"/prospects/{created['id']}/contact-intelligence/run",
        data={"force": "on"},
        headers=auth_headers,
        follow_redirects=False,
    )
    assert first.status_code == 303
    assert "contact_status=queued" in first.headers["location"]
    assert delay.call_count == 1
    assert await db_session.scalar(
        select(func.count()).select_from(ContactDiscoveryRun)
    ) == 1
    run = await db_session.scalar(select(ContactDiscoveryRun))
    assert run.status == "queued"
    assert delay.call_args.kwargs["contact_run_id"] == run.id

    second = await client.post(
        f"/prospects/{created['id']}/contact-intelligence/run",
        data={"force": "on"},
        headers=auth_headers,
        follow_redirects=False,
    )
    assert second.status_code == 303
    assert "contact_status=already_queued" in second.headers["location"]
    assert delay.call_count == 1
    assert await db_session.scalar(
        select(func.count()).select_from(ContactDiscoveryRun)
    ) == 1

    detail = await client.get(f"/prospects/{created['id']}", headers=auth_headers)
    assert detail.status_code == 200
    assert "Contact run queued" in detail.text


@pytest.mark.asyncio
async def test_native_browser_form_accepts_cookie_bound_csrf_field(
    client: AsyncClient,
    auth_headers: dict,
    sample_prospect_payload: dict,
    monkeypatch,
):
    created = (
        await client.post(
            "/api/prospects", json=sample_prospect_payload, headers=auth_headers
        )
    ).json()
    login = await client.post(
        "/auth/login/form",
        data={"email": "admin@test.local", "password": "testpass123"},
        follow_redirects=False,
    )
    assert login.status_code == 303
    detail = await client.get(f"/prospects/{created['id']}")
    assert detail.status_code == 200
    csrf = client.cookies.get("pf_csrf")
    assert csrf

    delay = Mock()
    monkeypatch.setattr("app.workers.tasks.contact_discovery_run.delay", delay)
    response = await client.post(
        f"/prospects/{created['id']}/contact-intelligence/run",
        data={"force": "on", "_csrf": csrf},
        follow_redirects=False,
    )
    assert response.status_code == 303
    delay.assert_called_once()

    rejected = await client.post(
        f"/prospects/{created['id']}/contact-intelligence/run",
        data={"force": "on", "_csrf": "wrong-token"},
        headers={"Accept": "text/html"},
        follow_redirects=False,
    )
    assert rejected.status_code == 403


@pytest.mark.asyncio
async def test_cookie_authenticated_api_mutation_requires_csrf_header(
    client: AsyncClient,
    monkeypatch,
):
    login = await client.post(
        "/auth/login/form",
        data={"email": "admin@test.local", "password": "testpass123"},
        follow_redirects=False,
    )
    assert login.status_code == 303
    operations = await client.get("/operations")
    assert operations.status_code == 200
    csrf = client.cookies.get("pf_csrf")
    assert csrf

    rejected = await client.post("/api/operations/recover-stale-work")
    assert rejected.status_code == 403

    queued = Mock(id="recovery-task")
    delay = Mock(return_value=queued)
    monkeypatch.setattr("app.workers.tasks.ingest_recover_stale_work.delay", delay)
    accepted = await client.post(
        "/api/operations/recover-stale-work",
        headers={"X-CSRF-Token": csrf},
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"
    delay.assert_called_once()


@pytest.mark.asyncio
async def test_contact_enqueue_failure_is_recorded_truthfully(
    client: AsyncClient,
    auth_headers: dict,
    sample_prospect_payload: dict,
    db_session,
    monkeypatch,
):
    created = (
        await client.post(
            "/api/prospects", json=sample_prospect_payload, headers=auth_headers
        )
    ).json()
    delay = Mock(side_effect=ConnectionError("broker unavailable"))
    monkeypatch.setattr("app.workers.tasks.contact_discovery_run.delay", delay)
    response = await client.post(
        f"/prospects/{created['id']}/contact-intelligence/run",
        data={"force": "on"},
        headers=auth_headers,
        follow_redirects=False,
    )
    assert response.status_code == 503
    run = await db_session.scalar(select(ContactDiscoveryRun))
    await db_session.refresh(run)
    assert run.status == "enqueue_failed"
    assert run.finished_at is not None
    assert "queue_unavailable" in run.error_summary


@pytest.mark.asyncio
async def test_kanban_move_endpoint_updates_canonical_opportunity(
    client: AsyncClient,
    auth_headers: dict,
    sample_prospect_payload: dict,
    db_session,
):
    created = (
        await client.post(
            "/api/prospects", json=sample_prospect_payload, headers=auth_headers
        )
    ).json()
    response = await client.post(
        "/kanban/move",
        data={
            "opportunity_id": created["id"],
            "column": "Qualified",
            "channel": "Email",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    opportunity = await db_session.get(Opportunity, created["id"])
    await db_session.refresh(opportunity)
    assert opportunity.status == "qualified"


@pytest.mark.asyncio
async def test_sourcing_links_use_canonical_identity_and_enrichment_is_queued(
    client: AsyncClient,
    auth_headers: dict,
    sample_prospect_payload: dict,
    db_session,
    monkeypatch,
):
    created = (
        await client.post(
            "/api/prospects", json=sample_prospect_payload, headers=auth_headers
        )
    ).json()
    page = await client.get("/sourcing", headers=auth_headers)
    assert page.status_code == 200
    assert f'/prospects/{created["id"]}' in page.text
    assert "/sourcing/enrich-modal/" not in page.text

    queued_task = Mock(id="evidence-task-1")
    delay = Mock(return_value=queued_task)
    monkeypatch.setattr("app.workers.tasks.extract_website_evidence.delay", delay)
    response = await client.post(
        f"/prospects/{created['id']}/deep-enrich",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert "Evidence enrichment queued" in response.text
    assert "Contact discovery remains a separate" in response.text
    delay.assert_called_once()
    work = await db_session.scalar(select(WorkItem))
    run = await db_session.scalar(select(PipelineRun))
    assert work.status == "enqueued"
    assert work.task_name == "extract_website_evidence"
    assert run.id == work.pipeline_run_id
    assert run.connector_code == "operator-evidence"
    assert run.status == "running"


@pytest.mark.asyncio
async def test_inbox_controls_use_real_reply_and_classify_it(
    client: AsyncClient,
    auth_headers: dict,
    sample_prospect_payload: dict,
    db_session,
):
    created = (
        await client.post(
            "/api/prospects", json=sample_prospect_payload, headers=auth_headers
        )
    ).json()
    event = (
        await client.post(
            f"/api/prospects/{created['id']}/events",
            json={
                "channel": "Email",
                "event_type": "Replied",
                "notes": "Please call next Tuesday.",
            },
            headers=auth_headers,
        )
    ).json()
    page = await client.get("/inbox", headers=auth_headers)
    assert page.status_code == 200
    assert sample_prospect_payload["company_name"] in page.text
    assert "Please call next Tuesday." in page.text
    assert "John Doe" not in page.text
    assert f'/inbox/{event["id"]}/classify' in page.text
    assert "Reply sending is intentionally disabled" in page.text

    classified = await client.post(
        f'/inbox/{event["id"]}/classify',
        data={"classification": "positive_interest"},
        headers=auth_headers,
        follow_redirects=False,
    )
    assert classified.status_code == 303
    persisted = await db_session.get(OutreachEvent, event["id"])
    await db_session.refresh(persisted)
    assert persisted.event_kind == "reply_classified"
    assert persisted.objection_code == "positive_interest"

    metrics = await client.get("/api/dashboard/metrics", headers=auth_headers)
    assert metrics.status_code == 200
    assert metrics.json()["replies_needing_classification"] == 0


@pytest.mark.asyncio
async def test_campaign_and_draft_controls_are_backed_by_real_mutations(
    client: AsyncClient,
    auth_headers: dict,
    db_session,
):
    play = MarketPlayVersion(play_code="FIELD_OPERATIONS_FR_V2")
    company = Company(canonical_name="Real Draft Company", country_code="FR")
    db_session.add_all([play, company])
    await db_session.flush()
    opportunity = Opportunity(company_id=company.id, play_version_id=play.id)
    campaign = Campaign(
        name="Manual Review Campaign",
        play_version_id=play.id,
        status="draft",
    )
    db_session.add_all([opportunity, campaign])
    await db_session.flush()
    touch = Touch(
        campaign_id=campaign.id,
        opportunity_id=opportunity.id,
        status="draft",
        subject="Evidence-backed subject",
        body="Draft body",
    )
    db_session.add(touch)
    await db_session.commit()

    detail = await client.get(f"/campaigns/{campaign.id}", headers=auth_headers)
    assert detail.status_code == 200
    assert "Prepare manual review" in detail.text
    assert f'/campaigns/{campaign.id}/status' in detail.text

    drafts = await client.get("/drafts", headers=auth_headers)
    assert drafts.status_code == 200
    assert "Real Draft Company" in drafts.text
    assert f'/drafts/{touch.id}/reject' in drafts.text

    rejected = await client.post(
        f"/drafts/{touch.id}/reject",
        headers=auth_headers,
        follow_redirects=False,
    )
    assert rejected.status_code == 303
    await db_session.refresh(touch)
    assert touch.status == "rejected"

    prepared = await client.post(
        f"/campaigns/{campaign.id}/status",
        data={"action": "prepare_manual_review"},
        headers=auth_headers,
        follow_redirects=False,
    )
    assert prepared.status_code == 303
    await db_session.refresh(campaign)
    assert campaign.status == "manual_review"
