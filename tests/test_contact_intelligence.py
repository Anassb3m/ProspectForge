"""Contact-intelligence extraction, honesty, SSRF, and persistence regressions."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from sqlalchemy import func, select

from app.contact_intelligence.confidence import derive_utility
from app.contact_intelligence.crawler import BoundedCrawler, CrawlLimits
from app.contact_intelligence.extractors import (
    extract_emails,
    normalize_person_name,
    normalize_phone,
    normalize_role,
    parse_html_contacts,
    redact_email,
)
from app.contact_intelligence.patterns import (
    generate_pattern_candidates,
    learn_patterns,
)
from app.contact_intelligence.safety import (
    SafeURL,
    UnsafeURLError,
    normalize_http_url,
    validate_peer_address,
    validate_public_url,
)
from app.contact_intelligence.service import (
    DiscoveryNotEligible,
    record_manual_review,
    run_contact_discovery,
)
from app.contact_intelligence.types import (
    ContactDiscoveryContext,
    ContactPointFact,
    ContactSourceResult,
    EvidenceFact,
    PersonFact,
)
from app.models import (
    ContactDiscoveryRun,
    ContactEvidence,
    ContactPerson,
    ContactPoint,
    OutreachEvent,
    Prospect,
    SuppressionEntry,
    Task,
)

FIXTURES = Path(__file__).parent / "fixtures" / "contact_pages"


@pytest.mark.parametrize(
    ("title", "category", "minimum"),
    [
        ("Directrice des opérations", "operations", 90),
        ("Responsable maintenance", "maintenance", 90),
        ("Directeur technique", "technical", 85),
        ("Gérant", "owner", 70),
        ("Représentant légal", "legal_representative", 40),
    ],
)
def test_french_role_normalization(title, category, minimum):
    _normalized, actual, score = normalize_role(title)
    assert actual == category
    assert score >= minimum


def test_name_phone_and_redaction_normalization():
    assert normalize_person_name("Mme. Élodie Martin-Dupont") == "elodie martin-dupont"
    assert normalize_phone("01 44 55 66 77") == "+33144556677"
    assert redact_email("alice@example.fr") == "a***@example.fr"


def test_conservative_obfuscated_email_extraction():
    text = "Écrivez à alice.martin [at] acme-maintenance [dot] fr. Ceci n'est pas une adresse."
    assert extract_emails(text) == ["alice.martin@acme-maintenance.fr"]


@pytest.mark.parametrize(
    "fixture",
    ["team.html", "contact.html", "agency.html", "legal.html", "obfuscated.html", "malformed.html"],
)
def test_sanitized_parser_fixtures_do_not_crash(fixture):
    parsed = parse_html_contacts(
        (FIXTURES / fixture).read_text(),
        "https://acme-maintenance.fr/" + fixture,
    )
    assert isinstance(parsed.text, str)


def test_team_page_extracts_person_and_published_email():
    parsed = parse_html_contacts(
        (FIXTURES / "team.html").read_text(), "https://acme-maintenance.fr/equipe"
    )
    assert any(person.full_name == "Alice Martin" for person in parsed.people)
    email = next(point for point in parsed.contact_points if point.kind == "email")
    assert email.publication_state == "published_personal"
    assert email.source_url.endswith("/equipe")


def test_generic_mailbox_and_contact_form_are_not_personal():
    parsed = parse_html_contacts(
        (FIXTURES / "contact.html").read_text(), "https://acme-maintenance.fr/contact"
    )
    generic = next(point for point in parsed.contact_points if point.kind == "email")
    form = next(point for point in parsed.contact_points if point.kind == "contact_form")
    assert generic.publication_state == "published_generic"
    assert generic.person_match_state == "generic_company_mailbox"
    assert form.metadata["category"] == "sales_quote"
    assert form.metadata["has_captcha"] is True


def test_jsonld_organization_contact_points_are_extracted():
    parsed = parse_html_contacts(
        (FIXTURES / "jsonld_organization.html").read_text(),
        "https://acme-maintenance.fr/",
    )
    kinds = {point.kind for point in parsed.contact_points}
    assert {"email", "phone"} <= kinds
    assert all(point.source_class == "structured_data" for point in parsed.contact_points)


def test_pdf_text_fixture_extracts_without_live_network():
    text = (FIXTURES / "pdf_text.txt").read_text()
    assert extract_emails(text) == ["alice.martin@acme-maintenance.fr"]
    assert normalize_phone("01 44 55 66 77") == "+33144556677"


def test_pattern_learning_requires_multiple_published_people():
    pairs = [
        ("alice.martin@acme.fr", "Alice Martin"),
        ("jean.dupont@acme.fr", "Jean Dupont"),
        ("luc.robert@acme.fr", "Luc Robert"),
        ("contact@acme.fr", "Contact Acme"),
    ]
    patterns = learn_patterns(pairs)
    assert patterns[0].name == "firstname.lastname"
    assert patterns[0].strength == "strong"
    candidates = generate_pattern_candidates("Marie Durand", "acme.fr", patterns)
    assert candidates[0]["email"] == "marie.durand@acme.fr"
    assert candidates[0]["person_match_state"] == "exact_person_pattern_confirmed"


def test_blind_fallback_is_always_name_only_guess_and_bounded():
    candidates = generate_pattern_candidates("Marie Durand", "acme.fr", [], max_candidates=1)
    assert len(candidates) == 1
    assert candidates[0]["person_match_state"] == "name_only_guess"


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        (
            dict(kind="email", publication_state="not_published", deliverability_state="deliverable", person_match_state="name_only_guess"),
            "manual_confirmation_required",
        ),
        (
            dict(kind="email", publication_state="published_personal", deliverability_state="unchecked", person_match_state="exact_person_published"),
            "usable_personal",
        ),
        (
            dict(kind="email", publication_state="published_generic", deliverability_state="unchecked", person_match_state="generic_company_mailbox"),
            "usable_generic",
        ),
        (
            dict(kind="email", publication_state="not_published", deliverability_state="catch_all", person_match_state="exact_person_pattern_confirmed"),
            "manual_confirmation_required",
        ),
        (
            dict(kind="contact_form", publication_state="published_generic", deliverability_state="unchecked", person_match_state="generic_company_mailbox"),
            "usable_generic",
        ),
    ],
)
def test_independent_confidence_dimensions_derive_honest_utility(kwargs, expected):
    assert derive_utility(**kwargs) == expected


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd", "ftp://example.com/a", "gopher://example.com/a",
        "http://user:pass@example.com", "http://example.com:8080", "http://localhost",
        "http://db", "http://service.local",
    ],
)
def test_url_syntax_rejects_unsafe_targets(url):
    with pytest.raises(UnsafeURLError):
        normalize_http_url(url)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1", "http://[::1]", "http://10.0.0.1", "http://172.16.0.1",
        "http://192.168.1.1", "http://169.254.169.254", "http://0.0.0.0",
    ],
)
async def test_private_literal_addresses_are_blocked(url):
    with pytest.raises(UnsafeURLError):
        await validate_public_url(url)


@pytest.mark.asyncio
async def test_dns_with_any_private_answer_is_blocked(monkeypatch):
    async def fake_resolve(_host, _port):
        return {"93.184.216.34", "10.0.0.5"}

    monkeypatch.setattr("app.contact_intelligence.safety._resolve", fake_resolve)
    with pytest.raises(UnsafeURLError, match="non_public_address"):
        await validate_public_url("https://example.com")


def test_dns_rebinding_peer_is_blocked():
    with pytest.raises(UnsafeURLError, match="dns_rebinding"):
        validate_peer_address(("10.0.0.5", 443), frozenset({"93.184.216.34"}))


@pytest.mark.asyncio
async def test_crawler_rejects_oversized_content(monkeypatch):
    async def safe(value, base=None):
        del base
        return SafeURL(value, "example.com", None, frozenset({"93.184.216.34"}))

    def handler(request: httpx.Request):
        if request.url.path in {"/robots.txt", "/sitemap.xml"}:
            return httpx.Response(404, request=request)
        return httpx.Response(
            200, headers={"content-type": "text/html", "content-length": "1000"},
            content=b"small", request=request,
        )

    monkeypatch.setattr("app.contact_intelligence.crawler.validate_public_url", safe)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        crawler = BoundedCrawler(
            CrawlLimits(max_response_bytes=100), client=client, enforce_peer_address=False
        )
        result = await crawler.crawl(ContactDiscoveryContext(1, "Example", "https://example.com"))
    assert result.pages == []
    assert any(item["reason"] == "response_too_large" for item in result.rejected)


async def _mock_safe_url(value, base=None):
    normalized = normalize_http_url(value, base=base)
    host = httpx.URL(normalized).host
    if host in {"127.0.0.1", "169.254.169.254"}:
        raise UnsafeURLError("non_public_address")
    return SafeURL(normalized, host, None, frozenset({"93.184.216.34"}))


@pytest.mark.asyncio
async def test_crawler_honors_robots_disallow(monkeypatch):
    def handler(request: httpx.Request):
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200,
                headers={"content-type": "text/plain"},
                text="User-agent: *\nDisallow: /",
                request=request,
            )
        if request.url.path == "/sitemap.xml":
            return httpx.Response(404, request=request)
        return httpx.Response(500, request=request)

    monkeypatch.setattr("app.contact_intelligence.crawler.validate_public_url", _mock_safe_url)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await BoundedCrawler(client=client, enforce_peer_address=False).crawl(
            ContactDiscoveryContext(1, "Example", "https://example.com")
        )
    assert result.pages == []
    assert result.rejected == [{"url": "https://example.com/", "reason": "robots_disallow"}]


@pytest.mark.asyncio
async def test_crawler_rejects_unsupported_mime(monkeypatch):
    def handler(request: httpx.Request):
        if request.url.path in {"/robots.txt", "/sitemap.xml"}:
            return httpx.Response(404, request=request)
        return httpx.Response(
            200, headers={"content-type": "application/zip"}, content=b"PK", request=request
        )

    monkeypatch.setattr("app.contact_intelligence.crawler.validate_public_url", _mock_safe_url)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await BoundedCrawler(client=client, enforce_peer_address=False).crawl(
            ContactDiscoveryContext(1, "Example", "https://example.com")
        )
    assert result.pages == []
    assert any(item["reason"] == "unsupported_mime" for item in result.rejected)


@pytest.mark.asyncio
async def test_crawler_stops_excessive_redirect_chain(monkeypatch):
    def handler(request: httpx.Request):
        if request.url.path in {"/robots.txt", "/sitemap.xml"}:
            return httpx.Response(404, request=request)
        step = int(request.url.params.get("step", "0"))
        return httpx.Response(
            302, headers={"location": f"/?step={step + 1}"}, request=request
        )

    monkeypatch.setattr("app.contact_intelligence.crawler.validate_public_url", _mock_safe_url)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        crawler = BoundedCrawler(
            CrawlLimits(max_redirects=2), client=client, enforce_peer_address=False
        )
        result = await crawler.crawl(
            ContactDiscoveryContext(1, "Example", "https://example.com")
        )
    assert result.pages == []
    assert any(item["reason"] == "redirect_limit_exceeded" for item in result.rejected)


@pytest.mark.asyncio
async def test_crawler_revalidates_and_blocks_redirect_to_private_ip(monkeypatch):
    def handler(request: httpx.Request):
        if request.url.path in {"/robots.txt", "/sitemap.xml"}:
            return httpx.Response(404, request=request)
        return httpx.Response(
            302, headers={"location": "http://169.254.169.254/latest/meta-data"}, request=request
        )

    monkeypatch.setattr("app.contact_intelligence.crawler.validate_public_url", _mock_safe_url)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await BoundedCrawler(client=client, enforce_peer_address=False).crawl(
            ContactDiscoveryContext(1, "Example", "https://example.com")
        )
    assert result.pages == []
    assert any(item["reason"] == "non_public_address" for item in result.rejected)


class _FakeAdapter:
    name = "official_website"

    async def discover(self, context):
        del context
        return ContactSourceResult(
            people=[
                PersonFact(
                    "Alice Martin", "Directrice des opérations", "operations", 100,
                    "strong", 90, source_url="https://acme-maintenance.fr/equipe",
                )
            ],
            contact_points=[
                ContactPointFact(
                    "email", "alice.martin@acme-maintenance.fr", "published_personal",
                    "strong_person_match", source_url="https://acme-maintenance.fr/equipe",
                    confidence=90,
                )
            ],
            evidence=[
                EvidenceFact(
                    "published_person", "official_website", "https://acme-maintenance.fr/equipe",
                    "Alice Martin — Directrice des opérations", person_name="Alice Martin", confidence=90,
                ),
                EvidenceFact(
                    "published_email", "official_website", "https://acme-maintenance.fr/equipe",
                    "a***@acme-maintenance.fr", contact_value="alice.martin@acme-maintenance.fr",
                    confidence=90,
                ),
            ],
            metrics={
                "pages_accepted": 1, "pages_rejected": 0,
                "domain_match_state": "strong_brand_match",
                "canonical_url": "https://acme-maintenance.fr/",
            },
        )


def _prospect() -> Prospect:
    return Prospect(
        company_name="Acme Maintenance SAS", sector="Facilities / Maintenance",
        company_size="11-50", signal_type="REGISTRY_FIELD", website="https://acme-maintenance.fr",
        data_source="sanitized test fixture", source="Website", market_play_code="FIELD_SERVICE_OPERATIONS_FR",
        opportunity_score=80, acquisition_score=80, urgency_score=80,
    )


@pytest.mark.asyncio
async def test_discovery_persists_provenance_projects_primary_and_never_sends(db_session):
    prospect = _prospect()
    db_session.add(prospect)
    await db_session.flush()
    before_sent = await db_session.scalar(
        select(func.count()).select_from(OutreachEvent).where(OutreachEvent.event_type == "Sent")
    )
    run = await run_contact_discovery(
        db_session, prospect, actor="tester@example.test", force=True,
        adapter=_FakeAdapter(), verify_domains=False,
    )
    assert run.status == "completed"
    assert prospect.email == "alice.martin@acme-maintenance.fr"
    assert prospect.contact_confidence == "published_personal"
    assert await db_session.scalar(select(func.count()).select_from(ContactPerson)) == 1
    assert await db_session.scalar(select(func.count()).select_from(ContactPoint)) == 1
    assert await db_session.scalar(select(func.count()).select_from(ContactEvidence)) == 2
    after_sent = await db_session.scalar(
        select(func.count()).select_from(OutreachEvent).where(OutreachEvent.event_type == "Sent")
    )
    assert after_sent == before_sent == 0


@pytest.mark.asyncio
async def test_discovery_rerun_is_idempotent_for_people_points_evidence_and_tasks(db_session):
    prospect = _prospect()
    db_session.add(prospect)
    await db_session.flush()
    for _ in range(2):
        await run_contact_discovery(
            db_session, prospect, actor="tester@example.test", force=True,
            adapter=_FakeAdapter(), verify_domains=False,
        )
    assert await db_session.scalar(select(func.count()).select_from(ContactPerson)) == 1
    assert await db_session.scalar(select(func.count()).select_from(ContactPoint)) == 1
    assert await db_session.scalar(select(func.count()).select_from(ContactEvidence)) == 2
    task_types = list((await db_session.execute(select(Task.task_type))).scalars().all())
    assert len(task_types) == len(set(task_types))
    assert await db_session.scalar(select(func.count()).select_from(ContactDiscoveryRun)) == 2


@pytest.mark.asyncio
async def test_manual_confirmation_survives_weaker_rerun(db_session):
    prospect = _prospect()
    db_session.add(prospect)
    await db_session.flush()
    await run_contact_discovery(
        db_session, prospect, actor="tester@example.test", force=True,
        adapter=_FakeAdapter(), verify_domains=False,
    )
    point = await db_session.scalar(select(ContactPoint))
    await record_manual_review(
        db_session, prospect, reviewer="operator@example.test", decision="primary",
        contact_point_id=point.id,
    )
    point.publication_state = "published_personal"
    await run_contact_discovery(
        db_session, prospect, actor="tester@example.test", force=True,
        adapter=_FakeAdapter(), verify_domains=False,
    )
    assert point.manually_confirmed is True
    assert point.confidence_score == 100
    assert prospect.contact_confidence == "manual_confirmed"


@pytest.mark.asyncio
async def test_suppression_blocks_discovery(db_session):
    prospect = _prospect()
    prospect.siren = "123456789"
    db_session.add_all(
        [
            prospect,
            SuppressionEntry(kind="siren", value_normalized="123456789", reason="opt_out"),
        ]
    )
    await db_session.flush()
    with pytest.raises(DiscoveryNotEligible, match="suppressed"):
        await run_contact_discovery(
            db_session, prospect, actor="tester@example.test", force=True,
            adapter=_FakeAdapter(), verify_domains=False,
        )
    assert await db_session.scalar(select(func.count()).select_from(ContactDiscoveryRun)) == 0
