"""Domain services: prospect queries, metrics, CSV import/export, compliance."""

from __future__ import annotations

import io
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

import pandas as pd
from pydantic import ValidationError
from sqlalchemy.orm import selectinload
from sqlalchemy import Select, and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CHANNELS,
    CONTACTED_EVENT_TYPES,
    MEETING_EVENT_TYPES,
    REPLY_EVENT_TYPES,
    OutreachEvent,
    Prospect,
    Task,
    Company,
    Opportunity,
    CompanyIdentifier as CompanyIdentifier,
    CompanyDomain as CompanyDomain,
    CompanyLocation as CompanyLocation,
    CompanyClassification as CompanyClassification
)
from app.services.legacy_projection import LegacyProspectProxy
from app.schemas import (
    ChannelMetrics,
    DashboardMetrics,
    EventCreate,
    FollowUpItem,
    ImportResult,
    ImportRowError,
    ObjectionNote,
    ProspectCreate,
    SignalTypeMetrics,
)
from app.commercial import add_suppression, is_suppressed, recompute_commercial_state
from app.plays import DEFAULT_PLAY_CODE


class ComplianceError(Exception):
    """Raised when a compliance or suppression rule blocks an action."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Queries ──────────────────────────────────────────────────────────────────


def prospect_query(
    *,
    sector: str | None = None,
    signal_type: str | None = None,
    priority_level: str | None = None,
    status: str | None = None,
    source: str | None = None,
    search: str | None = None,
    min_score: int | None = None,
    max_score: int | None = None,
    include_opted_out: bool = False,
    include_anonymized: bool = False,
) -> Select:
    q = select(Company, Opportunity).join(Opportunity).options(
        selectinload(Company.identifiers),
        selectinload(Company.domains),
        selectinload(Company.locations),
        selectinload(Company.classifications),
    )

    if priority_level:
        q = q.where(Opportunity.priority == priority_level)
    if min_score is not None:
        q = q.where(Opportunity.latest_score >= min_score)
    if max_score is not None:
        q = q.where(Opportunity.latest_score <= max_score)
    if search:
        like = f"%{search}%"
        q = q.where(
            or_(
                Company.canonical_name.ilike(like),
                Company.legal_name.ilike(like),
            )
        )
    if status:
        q = q.where(Opportunity.pipeline_stage == status)
    return q


async def list_prospects(
    db: AsyncSession,
    *,
    sector: str | None = None,
    signal_type: str | None = None,
    priority_level: str | None = None,
    status: str | None = None,
    source: str | None = None,
    search: str | None = None,
    min_score: int | None = None,
    max_score: int | None = None,
    include_opted_out: bool = False,
    sort_by: str = "urgency_score",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Prospect], int]:
    q = prospect_query(
        sector=sector,
        signal_type=signal_type,
        priority_level=priority_level,
        source=source,
        search=search,
        min_score=min_score,
        max_score=max_score,
        include_opted_out=include_opted_out,
    )

    from sqlalchemy import func

    # Calculate total count
    count_q = select(func.count()).select_from(q.subquery())
    total = await db.scalar(count_q) or 0

    # Apply sorting
    reverse = sort_dir.lower() != "asc"
    if sort_by == "company_name":
        q = q.order_by(Company.legal_name.desc() if reverse else Company.legal_name.asc())
    elif sort_by == "created_at":
        q = q.order_by(Company.created_at.desc() if reverse else Company.created_at.asc())
    elif sort_by == "priority_level":
        # Simplified sort by priority text
        q = q.order_by(Opportunity.priority.desc() if reverse else Opportunity.priority.asc())
    else:
        q = q.order_by(Opportunity.latest_score.desc() if reverse else Opportunity.latest_score.asc())

    start = max(0, (page - 1) * page_size)
    q = q.offset(start).limit(page_size)

    result = await db.execute(q)
    rows = result.all()
    prospects = [LegacyProspectProxy.from_models(company, opp) for company, opp in rows]

    return prospects, total


async def get_prospect(db: AsyncSession, prospect_id: str) -> LegacyProspectProxy | None:
    result = await db.execute(
        select(Company, Opportunity)
        .join(Opportunity)
        .options(
            selectinload(Company.identifiers),
            selectinload(Company.domains),
            selectinload(Company.locations),
            selectinload(Company.classifications),
        )
        .where(Opportunity.id == prospect_id)
    )
    row = result.first()
    if not row:
        return None
    proxy = LegacyProspectProxy.from_models(row[0], row[1])

    # Try to load events from the legacy prospect
    legacy_prospect_query = await db.execute(
        select(Prospect)
        .options(selectinload(Prospect.outreach_events))
        .where(Prospect.company_name == proxy.company_name)
    )
    legacy = legacy_prospect_query.scalars().first()
    if legacy:
        proxy.outreach_events = list(legacy.outreach_events or [])
        proxy.legacy_id = legacy.id
        proxy.current_status = legacy.current_status
        proxy.manual_review_state = legacy.manual_review_state
        setattr(proxy, "qualification_decision", legacy.qualification_decision)
        setattr(proxy, "opted_out", getattr(legacy, "opted_out", False))
        setattr(proxy, "anonymized", getattr(legacy, "anonymized", False))
        setattr(proxy, "is_suppressed", getattr(legacy, "is_suppressed", False))

    return proxy


async def create_prospect(db: AsyncSession, data: ProspectCreate) -> Prospect:
    # Suppression gate
    if await is_suppressed(db, email=data.email, siren=getattr(data, "siren", None)):
        raise ComplianceError("Contact/company is on the suppression list")

    payload = data.model_dump()
    prospect = Prospect(**payload)
    prospect.market_play_code = DEFAULT_PLAY_CODE
    prospect.manual_review_state = "unreviewed"
    prospect.readiness_state = "research_required"
    prospect.readiness_state = "research_required"
    db.add(prospect)
    await db.flush()

    initial = OutreachEvent(
        prospect_id=prospect.id,
        channel="Email",
        event_type="New",
        notes="Prospect created",
        event_kind="research",
    )
    db.add(initial)
    await db.flush()
    await recompute_commercial_state(db, prospect)
    await db.flush()

    from app.services.normalized import upsert_normalized_company
    opp = await upsert_normalized_company(
        session=db,
        company_name=prospect.company_name,
        siren=prospect.siren,
        siret=prospect.siret,
        website=prospect.website,
        city=prospect.city,
        department=prospect.department,
        payload=payload
    )
    loaded = await get_prospect(db, str(opp.id))
    return loaded  # type: ignore[return-value]


async def update_prospect(db: AsyncSession, prospect: Any, updates: dict[str, Any]) -> Prospect:
    prospect = await _resolve_prospect(db, prospect)
    for key, value in updates.items():
        if value is not None or key in updates:
            setattr(prospect, key, value)
    await recompute_commercial_state(db, prospect)
    await db.flush()
    await db.refresh(prospect)
    return prospect


# ── Events & compliance ──────────────────────────────────────────────────────


async def _resolve_prospect(db: AsyncSession, p: Any) -> Prospect:
    if isinstance(p, Prospect):
        return p
    # Resolve from proxy
    result = await db.execute(
        select(Prospect).where(Prospect.company_name == p.company_name)
    )
    res = result.scalars().first()
    if not res:
        raise ComplianceError("Could not resolve legacy prospect for mutation")
    return res

async def log_event(
    db: AsyncSession,
    prospect: Any,
    data: EventCreate,
    *,
    skip_opt_out_check: bool = False,
) -> OutreachEvent:
    prospect = await _resolve_prospect(db, prospect)
    if prospect.opted_out and data.event_type != "OptOut" and not skip_opt_out_check:
        raise ComplianceError("Prospect has opted out — no further outreach events allowed")

    if await is_suppressed(db, email=prospect.email, siren=prospect.siren):
        if data.event_type not in ("OptOut", "ClosedLost", "Refused"):
            raise ComplianceError("Suppressed contact/company — no outreach events allowed")

    # Cannot log Sent without data_source + informed_at (GDPR trail)
    if data.event_type == "Sent":
        if not prospect.data_source or not str(prospect.data_source).strip():
            raise ComplianceError("Cannot log Sent without data_source populated")
        if prospect.informed_at is None:
            raise ComplianceError(
                "Cannot log Sent without informed_at — record first-contact disclosure timestamp"
            )
        conf = (prospect.contact_confidence or "").lower()
        if conf in ("domain_and_pattern_only", "catch_all", "guessed", "invalid", "bounced", "risky"):
            raise ComplianceError(
                f"Cannot log Sent with contact_confidence={conf} — confirm contact first"
            )

    event = OutreachEvent(
        prospect_id=prospect.id,
        channel=data.channel,
        event_type=data.event_type,
        notes=data.notes,
        next_action=data.next_action,
        next_action_date=data.next_action_date,
        event_date=data.event_date or _utcnow(),
        event_kind="message" if data.event_type == "Sent" else "decision",
        pipeline_stage_after=data.event_type if data.event_type != "New" else None,
    )
    db.add(event)

    if data.event_type == "OptOut":
        prospect.opted_out = True
        prospect.opted_out_at = _utcnow()
        if prospect.email:
            await add_suppression(
                db, kind="email", value=prospect.email, reason="opt_out", source="outreach"
            )
        if prospect.siren:
            await add_suppression(
                db, kind="siren", value=prospect.siren, reason="opt_out", source="outreach"
            )

        # P1: Cancel open tasks on opt-out
        await db.execute(
            update(Task)
            .where(
                and_(
                    Task.prospect_id == prospect.id,
                    Task.status == "open",
                )
            )
            .values(status="cancelled", completed_at=_utcnow())
        )

    await db.flush()
    await recompute_commercial_state(db, prospect)
    await db.flush()
    await db.refresh(event)
    return event


# ── CSV import / export ──────────────────────────────────────────────────────

CSV_COLUMNS = [
    "company_name",
    "sector",
    "company_size",
    "signal_type",
    "signal_details",
    "decision_maker_name",
    "decision_maker_title",
    "linkedin_url",
    "email",
    "phone",
    "website",
    "data_source",
    "source",
    "notes",
]


async def import_csv(db: AsyncSession, content: bytes) -> ImportResult:
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        return ImportResult(
            created=0,
            failed=0,
            errors=[ImportRowError(row=0, errors=[f"Invalid CSV: {exc}"])],
        )

    # Normalize column names
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    created = 0
    errors: list[ImportRowError] = []

    for idx, row in df.iterrows():
        row_num = int(idx) + 2  # 1-indexed + header
        raw = {col: (None if pd.isna(row.get(col)) else str(row.get(col)).strip()) for col in CSV_COLUMNS}
        # Drop empty optionals
        payload = {k: v for k, v in raw.items() if v not in (None, "")}

        try:
            data = ProspectCreate(**payload)
        except ValidationError as ve:
            messages = [f"{e['loc'][0]}: {e['msg']}" for e in ve.errors()]
            errors.append(ImportRowError(row=row_num, errors=messages))
            continue
        except Exception as exc:
            errors.append(ImportRowError(row=row_num, errors=[str(exc)]))
            continue

        try:
            await create_prospect(db, data)
            created += 1
        except Exception as exc:
            errors.append(ImportRowError(row=row_num, errors=[str(exc)]))

    return ImportResult(created=created, failed=len(errors), errors=errors)


def export_csv(prospects: Sequence[Prospect]) -> str:
    rows = []
    for p in prospects:
        # P1: Check before CSV export (filter suppressed)
        if p.opted_out or getattr(p, "is_suppressed", False):
            continue
        rows.append(
            {
                "id": p.id,
                "company_name": p.company_name,
                "sector": p.sector,
                "company_size": p.company_size,
                "signal_type": p.signal_type,
                "signal_details": p.signal_details or "",
                "decision_maker_name": p.decision_maker_name or "",
                "decision_maker_title": p.decision_maker_title or "",
                "linkedin_url": p.linkedin_url or "",
                "email": p.email or "",
                "phone": p.phone or "",
                "website": p.website or "",
                "data_source": p.data_source,
                "source": p.source,
                "urgency_score": p.urgency_score,
                "priority_level": p.priority_level,
                "current_status": p.current_status,
                "opted_out": p.opted_out,
                "notes": p.notes or "",
                "created_at": p.created_at.isoformat() if p.created_at else "",
            }
        )
    df = pd.DataFrame(rows)
    return df.to_csv(index=False)


# ── Dashboard metrics ────────────────────────────────────────────────────────


async def compute_metrics(db: AsyncSession) -> DashboardMetrics:
    result = await db.execute(
        select(Prospect)
        .options(selectinload(Prospect.outreach_events))
        .where(Prospect.anonymized.is_(False))
    )
    prospects = list(result.scalars().unique().all())

    total = len(prospects)
    week_ago = _utcnow() - timedelta(days=7)

    contacted_this_week = 0
    total_contacted = 0
    total_replied = 0
    total_meetings = 0

    by_signal: dict[str, dict[str, int]] = {}
    by_channel: dict[str, dict[str, int]] = {c: {"sent": 0, "replied": 0} for c in CHANNELS}
    objections: list[str] = []

    for p in prospects:
        st = p.signal_type
        if st not in by_signal:
            by_signal[st] = {"total": 0, "contacted": 0, "replied": 0}
        by_signal[st]["total"] += 1

        events = list(p.outreach_events or [])
        types = {e.event_type for e in events}

        contacted = bool(types & set(CONTACTED_EVENT_TYPES))
        replied = bool(types & set(REPLY_EVENT_TYPES))
        meeting = bool(types & set(MEETING_EVENT_TYPES))

        if contacted:
            total_contacted += 1
            by_signal[st]["contacted"] += 1
        if replied:
            total_replied += 1
            by_signal[st]["replied"] += 1
        if meeting:
            total_meetings += 1

        for e in events:
            if e.event_type in CONTACTED_EVENT_TYPES and e.event_date:
                ed = e.event_date if e.event_date.tzinfo else e.event_date.replace(tzinfo=timezone.utc)
                if ed >= week_ago:
                    contacted_this_week += 1
                    break

        for e in events:
            if e.event_type == "Sent":
                by_channel.setdefault(e.channel, {"sent": 0, "replied": 0})
                by_channel[e.channel]["sent"] += 1
            if e.event_type in REPLY_EVENT_TYPES:
                by_channel.setdefault(e.channel, {"sent": 0, "replied": 0})
                by_channel[e.channel]["replied"] += 1
            if e.event_type in ("Refused", "ClosedLost") and e.notes:
                objections.append(e.notes.strip().lower()[:120])

    def rate(num: int, den: int) -> float:
        return round((num / den) * 100, 1) if den else 0.0

    signal_metrics = [
        SignalTypeMetrics(
            signal_type=k,
            total=v["total"],
            contacted=v["contacted"],
            replied=v["replied"],
            reply_rate=rate(v["replied"], v["contacted"]),
        )
        for k, v in sorted(by_signal.items())
    ]
    channel_metrics = [
        ChannelMetrics(
            channel=k,
            sent=v["sent"],
            replied=v["replied"],
            reply_rate=rate(v["replied"], v["sent"]),
        )
        for k, v in sorted(by_channel.items())
        if v["sent"] > 0 or v["replied"] > 0
    ]

    common = [
        ObjectionNote(note=note, count=count)
        for note, count in Counter(objections).most_common(10)
    ]

    high_priority = sum(1 for p in prospects if p.priority_level == "High" and not p.opted_out)

    new_decp = sum(
        1
        for p in prospects
        if p.signal_type == "DECP_WIN"
        and p.created_at
        and (
            (p.created_at if p.created_at.tzinfo else p.created_at.replace(tzinfo=timezone.utc))
            >= week_ago
        )
    )
    with_email = [p for p in prospects if p.email]
    verified = sum(1 for p in prospects if p.contact_confidence == "verified")
    needs_review = sum(
        1 for p in prospects if p.needs_manual_review and not p.opted_out and not p.anonymized
    )

    follow_ups = await get_follow_ups_due(db)
    today = _utcnow().date()
    overdue_follow_ups = len([f for f in follow_ups if f.next_action_date and f.next_action_date.date() < today])

    return DashboardMetrics(
        total_prospects=total,
        contacted_this_week=contacted_this_week,
        reply_rate=rate(total_replied, total_contacted),
        meeting_rate=rate(total_meetings, total_contacted),
        by_signal_type=signal_metrics,
        by_channel=channel_metrics,
        common_objections=common,
        high_priority_count=high_priority,
        follow_ups_due_count=len(follow_ups),
        new_decp_this_week=new_decp,
        verified_email_pct=rate(verified, len(with_email) if with_email else total),
        needs_review_count=needs_review,
        opportunities_awaiting_qualification=sum(1 for p in prospects if p.needs_manual_review),
        contacts_awaiting_review=sum(1 for p in prospects if getattr(p, "contact_discovery_state", "") == "review_required"),
        drafts_awaiting_approval=0,
        overdue_follow_ups=overdue_follow_ups,
        failed_or_blocked_jobs=0,
        replies_needing_classification=0,
        funnel_universe=total,
        funnel_icp_eligible=sum(1 for p in prospects if getattr(p, "fit_score", 0) > 0),
        funnel_domain_verified=0,
        funnel_evidence_enriched=sum(1 for p in prospects if getattr(p, "evidence_json", None)),
        funnel_human_accepted=sum(1 for p in prospects if p.manual_review_state == "accepted"),
        funnel_contact_ready=sum(1 for p in prospects if p.readiness_state == "contact_ready"),
        funnel_in_outreach=sum(1 for p in prospects if p.acquisition_stage in ("in_sequence", "replied", "meeting", "proposal", "won")),
        funnel_positive_reply=sum(1 for p in prospects if p.acquisition_stage in ("replied", "meeting", "proposal", "won")),
        funnel_meeting=sum(1 for p in prospects if p.acquisition_stage in ("meeting", "proposal", "won")),
        funnel_proposal=sum(1 for p in prospects if p.acquisition_stage in ("proposal", "won")),
        funnel_won=sum(1 for p in prospects if p.acquisition_stage == "won"),
        companies_imported_per_day=0.0,
        opportunities_created_per_day=0.0,
        qualification_acceptance_rate=0.0,
        contact_ready_yield=0.0,
        duplicate_rate=0.0,
        domain_verification_rate=0.0,
        evidence_coverage=0.0,
        stale_data_count=0
    )


async def get_follow_ups_due(db: AsyncSession) -> list[FollowUpItem]:
    result = await db.execute(
        select(Prospect)
        .options(selectinload(Prospect.outreach_events))
        .where(and_(Prospect.opted_out.is_(False), Prospect.anonymized.is_(False)))
    )
    prospects = list(result.scalars().unique().all())
    today = _utcnow().date()
    items: list[FollowUpItem] = []

    for p in prospects:
        events = list(p.outreach_events or [])
        if not events:
            continue
        last = events[-1]
        if last.next_action_date is None:
            continue
        nad = last.next_action_date
        if nad.tzinfo is None:
            nad = nad.replace(tzinfo=timezone.utc)
        if nad.date() > today:
            continue
        days_overdue = (today - nad.date()).days
        items.append(
            FollowUpItem(
                prospect_id=p.id,
                company_name=p.company_name,
                current_status=p.current_status,
                priority_level=p.priority_level,
                urgency_score=p.urgency_score,
                next_action=last.next_action,
                next_action_date=last.next_action_date,
                decision_maker_name=p.decision_maker_name,
                channel=last.channel,
                days_overdue=days_overdue,
            )
        )

    items.sort(key=lambda x: (-x.days_overdue, -x.urgency_score))
    return items


async def get_kanban_columns(db: AsyncSession) -> dict[str, list[Any]]:
    from app.models import KANBAN_COLUMNS, Opportunity

    columns: dict[str, list[Opportunity]] = {name: [] for name in KANBAN_COLUMNS}

    # We query top 50 per column in the database to avoid memory exhaustion
    for col_name, statuses in KANBAN_COLUMNS.items():
        if not statuses:
            continue

        result = await db.execute(
            select(Opportunity)
            .options(selectinload(Opportunity.company))
            .where(Opportunity.status.in_(statuses))
            .order_by(Opportunity.latest_score.desc())
            .limit(50)
        )
        columns[col_name] = list(result.scalars().unique().all())

    return columns
