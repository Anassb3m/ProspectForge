"""Idempotent discovery orchestration, persistence, projection, and review tasks."""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from sqlalchemy import and_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.commercial import is_suppressed, recompute_commercial_state
from app.config import get_settings
from app.contact_intelligence.confidence import derive_utility, is_usable, primary_sort_key
from app.contact_intelligence.crawler import BoundedCrawler, CrawlLimits, OfficialWebsiteAdapter
from app.contact_intelligence.dns import validate_email_domain
from app.contact_intelligence.extractors import (
    normalize_email,
    normalize_person_name,
    normalize_role,
    normalize_space,
)
from app.contact_intelligence.patterns import generate_pattern_candidates, identify_pattern, learn_patterns
from app.contact_intelligence.types import (
    ContactDiscoveryContext,
    ContactPointFact,
    ContactSourceAdapter,
    EvidenceFact,
    PersonFact,
)
from app.discovery.emails import extract_domain
from app.discovery.reacher import check_email
from app.models import (
    ContactDiscoveryRun,
    ContactEvidence,
    ContactManualReview,
    ContactPerson,
    ContactPoint,
    ContactVerificationEvent,
    Prospect,
    Task,
)

logger = logging.getLogger(__name__)
SOURCE_RANK = {
    "manual_operator": 0,
    "company_website": 1,
    "structured_data": 2,
    "company_pdf": 3,
    "public_registry": 4,
    "domain_pattern": 5,
    "reacher": 6,
    "search_provider": 7,
    "legacy": 8,
}
CONTACT_TASK_TYPES = {
    "confirm_buyer_identity", "confirm_linkedin_profile", "review_catch_all_email",
    "review_pattern_inferred_email", "call_switchboard_for_buyer", "use_contact_form",
    "resolve_domain_ambiguity", "review_conflicting_role", "refresh_stale_contact",
}


class DiscoveryNotEligible(ValueError):
    pass


class DiscoveryAlreadyRunning(RuntimeError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _evidence_fingerprint(prospect_id: int, fact: EvidenceFact) -> str:
    payload = "|".join(
        (
            str(prospect_id), fact.source_adapter, fact.source_url or "", fact.evidence_type,
            fact.contact_value or "", normalize_person_name(fact.person_name or ""),
            fact.content_hash or "",
        )
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _split_name(full_name: str) -> tuple[str | None, str | None]:
    parts = normalize_space(full_name).split()
    if len(parts) < 2:
        return (parts[0] if parts else None, None)
    return parts[0], " ".join(parts[1:])


def _registry_people(prospect: Prospect) -> tuple[list[PersonFact], list[EvidenceFact]]:
    people: list[PersonFact] = []
    evidence: list[EvidenceFact] = []
    for entry in list(prospect.dirigeants or [])[:20]:
        if not isinstance(entry, dict) or entry.get("type_dirigeant") == "personne morale":
            continue
        full_name = normalize_space(f"{entry.get('prenoms') or ''} {entry.get('nom') or ''}")
        if not full_name:
            continue
        title = normalize_space(str(entry.get("qualite") or "")) or None
        normalized_role, category, score = normalize_role(title)
        people.append(
            PersonFact(
                full_name=full_name, job_title=title, role_category=category,
                buyer_role_score=min(score, 78), company_match_state="strong",
                identity_confidence=75, source_adapter="public_registry",
                metadata={"normalized_role": normalized_role},
            )
        )
        evidence.append(
            EvidenceFact(
                evidence_type="registry_person", source_adapter="public_registry",
                source_url=None, excerpt=f"{full_name} — {title or 'legal role'}"[:600],
                confidence=75, person_name=full_name,
                metadata={"record": "annuaire_entreprises"},
            )
        )
    return people, evidence


async def _acquire_lease(db: AsyncSession, prospect_id: int, actor: str) -> ContactDiscoveryRun:
    now = _now()
    dialect = db.bind.dialect.name if db.bind is not None else ""
    if dialect == "postgresql":
        acquired = await db.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": prospect_id})
        if not acquired:
            raise DiscoveryAlreadyRunning("contact discovery already holds the prospect lock")
    active = await db.scalar(
        select(ContactDiscoveryRun.id).where(
            and_(
                ContactDiscoveryRun.prospect_id == prospect_id,
                ContactDiscoveryRun.status == "running",
                ContactDiscoveryRun.lease_expires_at > now,
            )
        ).limit(1)
    )
    if active is not None:
        raise DiscoveryAlreadyRunning("contact discovery already running")
    run = ContactDiscoveryRun(
        prospect_id=prospect_id,
        triggered_by=actor[:150],
        status="running",
        lease_expires_at=now + timedelta(minutes=3),
        adapters_requested=["official_website", "public_registry", "dns", "reacher"],
    )
    db.add(run)
    await db.flush()
    return run


def _eligibility_reason(prospect: Prospect, minimum_score: int) -> str | None:
    if prospect.anonymized:
        return "anonymized"
    if prospect.opted_out:
        return "opted_out"
    if (prospect.opportunity_score or prospect.acquisition_score or 0) < minimum_score:
        return "below_opportunity_threshold"
    if not prospect.website and not extract_domain(None, prospect.email):
        return "no_defensible_domain"
    return None


async def _load_existing(
    db: AsyncSession, prospect_id: int
) -> tuple[list[ContactPerson], list[ContactPoint]]:
    people = list(
        (
            await db.execute(select(ContactPerson).where(ContactPerson.prospect_id == prospect_id))
        ).scalars().all()
    )
    points = list(
        (
            await db.execute(select(ContactPoint).where(ContactPoint.prospect_id == prospect_id))
        ).scalars().all()
    )
    return people, points


async def _merge_people(
    db: AsyncSession, prospect: Prospect, facts: list[PersonFact]
) -> tuple[dict[str, ContactPerson], int]:
    existing, _ = await _load_existing(db, prospect.id)
    by_key = {(person.normalized_name, person.normalized_role): person for person in existing}
    by_name: dict[str, ContactPerson] = {person.normalized_name: person for person in existing}
    added = 0
    for fact in facts:
        normalized_name = normalize_person_name(fact.full_name)
        normalized_role, category, role_score = normalize_role(fact.job_title)
        normalized_role = str(fact.metadata.get("normalized_role") or normalized_role)[:120]
        if not normalized_name:
            continue
        key = (normalized_name, normalized_role)
        person = by_key.get(key)
        if person is None:
            first, last = _split_name(fact.full_name)
            person = ContactPerson(
                prospect_id=prospect.id,
                full_name=fact.full_name[:200], normalized_name=normalized_name[:200],
                first_name=first, last_name=last, job_title=(fact.job_title or None),
                normalized_role=normalized_role, role_category=fact.role_category or category,
                buyer_role_score=max(fact.buyer_role_score, role_score),
                company_match_state=fact.company_match_state,
                identity_confidence=fact.identity_confidence,
                linkedin_url=fact.linkedin_url, source_count=1,
            )
            db.add(person)
            await db.flush()
            by_key[key] = person
            by_name[normalized_name] = person
            added += 1
        else:
            person.last_seen_at = _now()
            # Evidence rows carry distinct source counts; reruns must not inflate this value.
            person.source_count = max(person.source_count, 1)
            if not person.manually_confirmed:
                if fact.buyer_role_score > person.buyer_role_score:
                    person.job_title = fact.job_title or person.job_title
                    person.normalized_role = normalized_role
                    person.role_category = fact.role_category or category
                    person.buyer_role_score = max(fact.buyer_role_score, role_score)
                person.identity_confidence = max(person.identity_confidence, fact.identity_confidence)
                person.linkedin_url = person.linkedin_url or fact.linkedin_url
    return by_name, added


def _associate_people(points: list[ContactPointFact], people: dict[str, ContactPerson]) -> None:
    for point in points:
        if point.person_name:
            continue
        if point.kind != "email" or point.publication_state != "published_personal":
            continue
        for person in people.values():
            if identify_pattern(point.value, person.full_name):
                point.person_name = person.full_name
                point.person_match_state = "exact_person_published"
                break


async def _merge_points(
    db: AsyncSession,
    prospect: Prospect,
    facts: list[ContactPointFact],
    people: dict[str, ContactPerson],
) -> tuple[list[ContactPoint], int]:
    _, existing = await _load_existing(db, prospect.id)
    by_key = {(point.kind, point.value_normalized): point for point in existing}
    added = 0
    for fact in facts:
        value = fact.value.strip()
        if fact.kind == "email":
            normalized = normalize_email(value)
            if not normalized:
                continue
            value = normalized
        else:
            normalized = value.lower() if fact.kind in {"linkedin", "contact_form", "website"} else value
        person = people.get(normalize_person_name(fact.person_name or ""))
        suppressed = await is_suppressed(
            db,
            email=normalized if fact.kind == "email" else None,
            domain=(normalized.rsplit("@", 1)[1] if fact.kind == "email" else None),
            siren=prospect.siren,
        )
        utility = derive_utility(
            kind=fact.kind,
            publication_state=str(fact.publication_state),
            deliverability_state=str(fact.deliverability_state),
            person_match_state=str(fact.person_match_state),
            suppressed=suppressed,
        )
        key = (fact.kind, normalized)
        point = by_key.get(key)
        if point is None:
            point = ContactPoint(
                prospect_id=prospect.id, person_id=person.id if person else None,
                kind=fact.kind, value_normalized=normalized, value_display=value,
                domain=(normalized.rsplit("@", 1)[1] if fact.kind == "email" else urlsplit(value).hostname),
                source_class=fact.source_class,
                publication_state=str(fact.publication_state),
                person_match_state=str(fact.person_match_state),
                deliverability_state=str(fact.deliverability_state),
                verification_state=str(fact.deliverability_state),
                utility_state=str(utility), confidence_score=max(0, min(100, fact.confidence)),
                is_usable=is_usable(str(utility)),
                requires_manual_review=str(utility) in {
                    "manual_confirmation_required", "verification_required", "stale"
                },
                is_suppressed=suppressed,
            )
            db.add(point)
            await db.flush()
            by_key[key] = point
            added += 1
        else:
            point.last_seen_at = _now()
            if not point.manually_confirmed and not point.rejection_reason:
                old_rank = SOURCE_RANK.get(point.source_class, 99)
                new_rank = SOURCE_RANK.get(fact.source_class, 99)
                if new_rank <= old_rank:
                    point.person_id = point.person_id or (person.id if person else None)
                    point.source_class = fact.source_class
                    point.publication_state = str(fact.publication_state)
                    point.person_match_state = str(fact.person_match_state)
                    point.deliverability_state = str(fact.deliverability_state)
                    point.utility_state = str(utility)
                    point.confidence_score = max(point.confidence_score, fact.confidence)
                    point.is_usable = is_usable(str(utility))
                    point.requires_manual_review = str(utility) in {
                        "manual_confirmation_required", "verification_required", "stale"
                    }
                    point.is_suppressed = suppressed
    return list(by_key.values()), added


async def _persist_evidence(
    db: AsyncSession,
    prospect: Prospect,
    facts: list[EvidenceFact],
    people: dict[str, ContactPerson],
    points: list[ContactPoint],
) -> int:
    existing = set(
        (
            await db.execute(
                select(ContactEvidence.fingerprint).where(ContactEvidence.prospect_id == prospect.id)
            )
        ).scalars().all()
    )
    points_by_value = {point.value_normalized: point for point in points}
    added = 0
    for fact in facts:
        fingerprint = _evidence_fingerprint(prospect.id, fact)
        if fingerprint in existing:
            continue
        person = people.get(normalize_person_name(fact.person_name or ""))
        contact_value = fact.contact_value or ""
        point = points_by_value.get(normalize_email(contact_value) or contact_value.lower())
        source_domain = urlsplit(fact.source_url).hostname if fact.source_url else None
        db.add(
            ContactEvidence(
                prospect_id=prospect.id, person_id=person.id if person else None,
                contact_point_id=point.id if point else None, fingerprint=fingerprint,
                source_adapter=fact.source_adapter, source_url=fact.source_url,
                canonical_url=fact.source_url, source_domain=source_domain,
                page_title=fact.page_title, evidence_type=fact.evidence_type,
                excerpt=(fact.excerpt or "")[:600] or None, content_hash=fact.content_hash,
                confidence=max(0, min(100, fact.confidence)), raw_metadata=fact.metadata or None,
            )
        )
        existing.add(fingerprint)
        added += 1
    return added


async def _verify_points(db: AsyncSession, points: list[ContactPoint]) -> dict[str, int]:
    settings = get_settings()
    stats = {"dns_checked": 0, "reacher_checked": 0, "deliverable": 0, "catch_all": 0, "invalid": 0}
    candidates = [
        point for point in points
        if point.kind == "email" and not point.is_suppressed and point.deliverability_state == "unchecked"
    ][: settings.contact_max_email_candidates]
    for point in candidates:
        mx = await validate_email_domain(point.value_normalized)
        stats["dns_checked"] += 1
        if not mx.has_mx:
            point.deliverability_state = "invalid" if mx.state in {"no_mx", "null_mx", "invalid_syntax"} else "indeterminate"
            point.verification_state = mx.state[:30]
            point.utility_state = derive_utility(
                kind=point.kind, publication_state=point.publication_state,
                deliverability_state=point.deliverability_state,
                person_match_state=point.person_match_state,
            )
            point.is_usable = is_usable(point.utility_state)
            continue
        if not settings.reacher_enabled:
            continue
        result = await check_email(point.value_normalized)
        stats["reacher_checked"] += 1
        state = str(result.get("deliverability_state") or result.get("confidence") or "indeterminate")
        if state not in {"deliverable", "catch_all", "risky", "invalid", "indeterminate", "error"}:
            state = "indeterminate"
        point.deliverability_state = state
        point.verification_state = state
        point.last_verified_at = _now()
        point.utility_state = derive_utility(
            kind=point.kind, publication_state=point.publication_state,
            deliverability_state=state, person_match_state=point.person_match_state,
            suppressed=point.is_suppressed, manually_confirmed=point.manually_confirmed,
        )
        point.is_usable = is_usable(point.utility_state)
        point.requires_manual_review = point.utility_state == "manual_confirmation_required"
        summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
        db.add(
            ContactVerificationEvent(
                contact_point_id=point.id, provider="reacher", deliverability_state=state,
                is_catch_all=result.get("is_catch_all"), smtp_state=summary.get("smtp_state"),
                mx_state=mx.state, confidence=float(result.get("score") or 0),
                raw_summary=summary or None, error_code=result.get("error_code"),
            )
        )
        if state in stats:
            stats[state] += 1
        if state == "deliverable" and point.utility_state == "usable_personal":
            break
    return stats


async def _sync_tasks(db: AsyncSession, prospect: Prospect, points: list[ContactPoint], warnings: list[str]) -> int:
    existing = list(
        (
            await db.execute(
                select(Task).where(
                    and_(Task.prospect_id == prospect.id, Task.origin == "contact_intelligence")
                )
            )
        ).scalars().all()
    )
    open_by_type = {task.task_type: task for task in existing if task.status == "open"}
    desired: dict[str, tuple[str, str]] = {}
    if "ambiguous_company_domain" in warnings:
        desired["resolve_domain_ambiguity"] = (
            f"Resolve official domain — {prospect.company_name}", "Company/domain match is ambiguous."
        )
    if not any(point.person_id for point in points):
        desired["confirm_buyer_identity"] = (
            f"Confirm buyer identity — {prospect.company_name}", "No source-backed operational buyer was found."
        )
    for point in points:
        source_note = f"Source: {point.domain or point.source_class}"
        if point.deliverability_state == "catch_all":
            desired["review_catch_all_email"] = (
                f"Review catch-all email — {prospect.company_name}", source_note
            )
        elif point.person_match_state in {"name_only_guess", "pattern_inferred"}:
            desired["review_pattern_inferred_email"] = (
                f"Review inferred email — {prospect.company_name}", source_note
            )
        elif point.kind == "phone" and not any(p.kind == "email" and p.is_usable for p in points):
            desired["call_switchboard_for_buyer"] = (
                f"Call switchboard for buyer — {prospect.company_name}", source_note
            )
        elif point.kind == "contact_form" and not any(p.kind == "email" and p.is_usable for p in points):
            desired["use_contact_form"] = (
                f"Use official contact form — {prospect.company_name}", source_note
            )
    if not any(point.kind == "linkedin" for point in points):
        desired["confirm_linkedin_profile"] = (
            f"Confirm LinkedIn profile manually — {prospect.company_name}",
            "Manual search only; no LinkedIn automation.",
        )
    for task in existing:
        if task.status == "open" and task.task_type not in desired:
            task.status = "completed"
            task.completed_at = _now()
    created = 0
    for task_type, (title, notes) in desired.items():
        if task_type in open_by_type:
            continue
        db.add(
            Task(
                prospect_id=prospect.id, task_type=task_type, title=title,
                due_date=_now(), priority=70, origin="contact_intelligence", notes=notes,
            )
        )
        created += 1
    return created


async def project_primary_contact_to_prospect(
    db: AsyncSession, prospect: Prospect, *, points: list[ContactPoint] | None = None
) -> None:
    people, loaded_points = await _load_existing(db, prospect.id)
    points = points or loaded_points
    active_people = [person for person in people if person.is_active]
    active_people.sort(
        key=lambda person: (
            0 if person.manually_confirmed else 1,
            -person.buyer_role_score,
            -person.identity_confidence,
        )
    )
    primary_person = active_people[0] if active_people else None
    for person in people:
        person.is_primary_candidate = person is primary_person
    available = [point for point in points if not point.rejection_reason and not point.is_suppressed]
    available.sort(key=primary_sort_key)
    primary = available[0] if available else None
    for point in points:
        point.is_primary = point is primary

    if primary_person:
        prospect.decision_maker_name = primary_person.full_name
        prospect.decision_maker_title = primary_person.job_title
    if primary:
        if primary.kind == "email" and primary.utility_state in {
            "usable_personal", "usable_role", "usable_generic"
        }:
            prospect.email = primary.value_normalized
        elif primary.kind == "phone":
            prospect.phone = primary.value_normalized
        elif primary.kind == "linkedin" and (
            primary.manually_confirmed or primary.publication_state == "published_personal"
        ):
            prospect.linkedin_url = primary.value_normalized
        prospect.contact_source = primary.source_class
        if primary.manually_confirmed:
            prospect.contact_confidence = "manual_confirmed"
            prospect.contact_discovery_state = "user_supplied"
        elif primary.publication_state == "published_personal":
            prospect.contact_confidence = "published_personal"
            prospect.contact_discovery_state = "published"
        elif primary.publication_state in {"published_role", "published_generic"}:
            prospect.contact_confidence = "published_generic"
            prospect.contact_discovery_state = "published"
        elif primary.person_match_state == "exact_person_pattern_confirmed" and primary.deliverability_state == "deliverable":
            prospect.contact_confidence = "deliverable"
            prospect.contact_discovery_state = "inferred"
        else:
            prospect.contact_confidence = "needs_review"
            prospect.contact_discovery_state = "guessed"
        prospect.needs_manual_review = primary.requires_manual_review
    else:
        prospect.contact_source = "none"
        prospect.contact_confidence = "none"
        prospect.contact_discovery_state = None
        prospect.needs_manual_review = True
    prospect.contact_candidates = [
        {
            "id": point.id,
            "kind": point.kind,
            "value": point.value_display,
            "publication_state": point.publication_state,
            "deliverability_state": point.deliverability_state,
            "person_match_state": point.person_match_state,
            "utility_state": point.utility_state,
            "requires_manual_review": point.requires_manual_review,
        }
        for point in available[:10]
    ]
    await recompute_commercial_state(db, prospect)


async def run_contact_discovery(
    db: AsyncSession,
    prospect: Prospect,
    *,
    actor: str,
    force: bool = False,
    adapter: ContactSourceAdapter | None = None,
    verify_domains: bool = True,
) -> ContactDiscoveryRun:
    settings = get_settings()
    if await is_suppressed(db, email=prospect.email, siren=prospect.siren):
        raise DiscoveryNotEligible("suppressed")
    reason = _eligibility_reason(prospect, settings.contact_min_opportunity_score)
    if reason and not force:
        raise DiscoveryNotEligible(reason)
    if not force:
        fresh_after = _now() - timedelta(days=settings.contact_refresh_days)
        fresh = await db.scalar(
            select(ContactDiscoveryRun.id).where(
                and_(
                    ContactDiscoveryRun.prospect_id == prospect.id,
                    ContactDiscoveryRun.status.in_({"completed", "completed_with_warnings"}),
                    ContactDiscoveryRun.finished_at >= fresh_after,
                )
            ).limit(1)
        )
        if fresh is not None:
            raise DiscoveryNotEligible("contact dossier is fresh")
    run = await _acquire_lease(db, prospect.id, actor)
    started = time.monotonic()
    try:
        context = ContactDiscoveryContext(
            prospect_id=prospect.id, company_name=prospect.company_name,
            website=prospect.website, siren=prospect.siren, company_size=prospect.company_size,
            market_play_code=prospect.market_play_code, started_at=_now(),
        )
        source = adapter or OfficialWebsiteAdapter(
            BoundedCrawler(
                CrawlLimits(
                    max_pages=settings.contact_crawl_max_pages,
                    max_depth=settings.contact_crawl_max_depth,
                    max_redirects=settings.contact_crawl_max_redirects,
                    max_response_bytes=settings.contact_crawl_max_response_bytes,
                    request_timeout_seconds=settings.contact_crawl_request_timeout_seconds,
                    total_timeout_seconds=settings.contact_crawl_total_timeout_seconds,
                    concurrency=settings.contact_domain_concurrency,
                )
            )
        )
        source_result = await source.discover(context)
        registry_people, registry_evidence = _registry_people(prospect)
        source_result.people.extend(registry_people)
        source_result.evidence.extend(registry_evidence)
        people, people_added = await _merge_people(db, prospect, source_result.people)
        _associate_people(source_result.contact_points, people)

        domain = extract_domain(source_result.metrics.get("canonical_url") or prospect.website)
        paired = [
            (point.value, point.person_name)
            for point in source_result.contact_points
            if point.kind == "email" and point.person_name
        ]
        learned = learn_patterns([(email, name) for email, name in paired if name])
        if domain:
            for person in sorted(people.values(), key=lambda item: item.buyer_role_score, reverse=True)[:3]:
                for candidate in generate_pattern_candidates(
                    person.full_name, domain, learned,
                    max_candidates=settings.contact_max_email_candidates,
                ):
                    source_result.contact_points.append(
                        ContactPointFact(
                            kind="email", value=str(candidate["email"]),
                            publication_state="not_published",
                            person_match_state=str(candidate["person_match_state"]),
                            source_class="domain_pattern", person_name=person.full_name,
                            confidence=78 if candidate["pattern_observations"] >= 2 else 35,
                            metadata={
                                "pattern": candidate["pattern"],
                                "observations": candidate["pattern_observations"],
                            },
                        )
                    )
        points, points_added = await _merge_points(
            db, prospect, source_result.contact_points, people
        )
        evidence_added = await _persist_evidence(
            db, prospect, source_result.evidence, people, points
        )
        verification = await _verify_points(db, points) if verify_domains else {
            "dns_checked": 0, "reacher_checked": 0, "deliverable": 0, "catch_all": 0, "invalid": 0
        }
        tasks_created = await _sync_tasks(db, prospect, points, source_result.warnings)
        await project_primary_contact_to_prospect(db, prospect, points=points)
        run.status = "completed_with_warnings" if source_result.errors else "completed"
        run.finished_at = _now()
        run.lease_expires_at = None
        run.adapters_completed = [source.name, "public_registry", "dns"] + (
            ["reacher"] if settings.reacher_enabled else []
        )
        run.pages_examined = int(source_result.metrics.get("pages_accepted") or 0)
        run.people_found = len(source_result.people)
        run.contact_points_found = len(source_result.contact_points)
        run.published_emails_found = sum(
            1 for point in source_result.contact_points
            if point.kind == "email" and point.publication_state != "not_published"
        )
        run.generated_candidates = sum(
            1 for point in source_result.contact_points if point.source_class == "domain_pattern"
        )
        run.verified_deliverable = verification["deliverable"]
        run.catch_all = verification["catch_all"]
        run.invalid = verification["invalid"]
        run.manual_review_required = sum(1 for point in points if point.requires_manual_review)
        run.errors = len(source_result.errors)
        run.timings = {"total_ms": round((time.monotonic() - started) * 1000)}
        run.result_summary = {
            "domain_match_state": source_result.metrics.get("domain_match_state", "unknown"),
            "pages_rejected": source_result.metrics.get("pages_rejected", 0),
            "people_added": people_added,
            "contact_points_added": points_added,
            "evidence_added": evidence_added,
            "tasks_created": tasks_created,
            "dns_checked": verification["dns_checked"],
            "reacher_checked": verification["reacher_checked"],
            "usable_paths": sum(1 for point in points if point.is_usable and not point.is_suppressed),
            "warnings": source_result.warnings[:20],
        }
        run.error_summary = "; ".join(source_result.errors)[:2000] or None
        await db.flush()
        return run
    except Exception as exc:
        run.status = "failed"
        run.finished_at = _now()
        run.lease_expires_at = None
        run.errors = 1
        run.error_summary = exc.__class__.__name__[:200]
        run.timings = {"total_ms": round((time.monotonic() - started) * 1000)}
        await db.flush()
        raise


async def record_manual_review(
    db: AsyncSession,
    prospect: Prospect,
    *,
    reviewer: str,
    decision: str,
    person_id: int | None = None,
    contact_point_id: int | None = None,
    reason: str | None = None,
    evidence_url: str | None = None,
) -> None:
    if decision not in {"confirm", "reject", "primary", "suppress"}:
        raise ValueError("invalid manual review decision")
    previous = None
    new_state = decision
    if person_id:
        person = await db.get(ContactPerson, person_id)
        if not person or person.prospect_id != prospect.id:
            raise ValueError("person not found")
        previous = "confirmed" if person.manually_confirmed else "unconfirmed"
        if decision in {"confirm", "primary"}:
            person.manually_confirmed = True
            person.is_active = True
            person.company_match_state = "exact"
            person.identity_confidence = 100
            if decision == "primary":
                await db.execute(
                    update(ContactPerson)
                    .where(ContactPerson.prospect_id == prospect.id)
                    .values(is_primary_candidate=False)
                )
                person.is_primary_candidate = True
                person.buyer_role_score = 100
        elif decision == "reject":
            person.is_active = False
    if contact_point_id:
        point = await db.get(ContactPoint, contact_point_id)
        if not point or point.prospect_id != prospect.id:
            raise ValueError("contact point not found")
        previous = point.utility_state
        if decision in {"confirm", "primary"}:
            point.manually_confirmed = True
            point.rejection_reason = None
            point.utility_state = derive_utility(
                kind=point.kind, publication_state=point.publication_state,
                deliverability_state=point.deliverability_state,
                person_match_state=point.person_match_state, manually_confirmed=True,
            )
            point.is_usable = is_usable(point.utility_state)
            point.requires_manual_review = False
            if decision == "primary":
                await db.execute(
                    update(ContactPoint)
                    .where(ContactPoint.prospect_id == prospect.id)
                    .values(is_primary=False)
                )
                point.is_primary = True
                point.confidence_score = 100
        elif decision == "reject":
            point.rejection_reason = (reason or "operator_rejected")[:300]
            point.is_usable = False
            point.requires_manual_review = False
        elif decision == "suppress":
            from app.commercial import add_suppression

            kind = "email" if point.kind == "email" else "person"
            await add_suppression(
                db, kind=kind, value=point.value_normalized,
                reason=reason or "operator_suppressed", source="contact_intelligence",
            )
            point.is_suppressed = True
            point.is_usable = False
            point.utility_state = "suppressed"
            await db.execute(
                update(Task)
                .where(
                    and_(
                        Task.prospect_id == prospect.id,
                        Task.origin == "contact_intelligence",
                        Task.status == "open",
                    )
                )
                .values(status="cancelled", completed_at=_now())
            )
    db.add(
        ContactManualReview(
            contact_point_id=contact_point_id, person_id=person_id, reviewer=reviewer,
            decision=decision, previous_state=previous, new_state=new_state,
            reason=reason, evidence_url=evidence_url,
        )
    )
    await db.flush()
    await project_primary_contact_to_prospect(db, prospect)
