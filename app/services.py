"""Domain services: prospect queries, metrics, CSV import/export, compliance."""

from __future__ import annotations

import io
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

import pandas as pd
from pydantic import ValidationError
from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    CHANNELS,
    CONTACTED_EVENT_TYPES,
    EVENT_TYPES,
    MEETING_EVENT_TYPES,
    REPLY_EVENT_TYPES,
    OutreachEvent,
    Prospect,
)
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
from app.scoring import apply_score


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
) -> Select[tuple[Prospect]]:
    q = select(Prospect).options(selectinload(Prospect.outreach_events))

    if not include_anonymized:
        q = q.where(Prospect.anonymized.is_(False))
    if not include_opted_out:
        q = q.where(Prospect.opted_out.is_(False))
    if sector:
        q = q.where(Prospect.sector == sector)
    if signal_type:
        q = q.where(Prospect.signal_type == signal_type)
    if priority_level:
        q = q.where(Prospect.priority_level == priority_level)
    if source:
        q = q.where(Prospect.source == source)
    if min_score is not None:
        q = q.where(Prospect.urgency_score >= min_score)
    if max_score is not None:
        q = q.where(Prospect.urgency_score <= max_score)
    if search:
        like = f"%{search}%"
        q = q.where(
            or_(
                Prospect.company_name.ilike(like),
                Prospect.decision_maker_name.ilike(like),
                Prospect.email.ilike(like),
            )
        )
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

    result = await db.execute(q)
    prospects = list(result.scalars().unique().all())

    # Status is derived — filter in Python after load (fine at pilot scale)
    if status:
        prospects = [p for p in prospects if p.current_status == status]

    # Sort
    reverse = sort_dir.lower() != "asc"
    if sort_by == "company_name":
        prospects.sort(key=lambda p: p.company_name.lower(), reverse=reverse)
    elif sort_by == "created_at":
        prospects.sort(key=lambda p: p.created_at or _utcnow(), reverse=reverse)
    elif sort_by == "priority_level":
        order = {"High": 0, "Medium": 1, "Low": 2}
        prospects.sort(key=lambda p: order.get(p.priority_level, 9), reverse=reverse)
    else:
        prospects.sort(key=lambda p: p.urgency_score, reverse=reverse)

    total = len(prospects)
    start = max(0, (page - 1) * page_size)
    end = start + page_size
    return prospects[start:end], total


async def get_prospect(db: AsyncSession, prospect_id: int) -> Prospect | None:
    result = await db.execute(
        select(Prospect)
        .options(selectinload(Prospect.outreach_events))
        .where(Prospect.id == prospect_id)
    )
    return result.scalar_one_or_none()


async def create_prospect(db: AsyncSession, data: ProspectCreate) -> Prospect:
    prospect = Prospect(**data.model_dump())
    apply_score(prospect, [])
    db.add(prospect)
    await db.flush()

    # Seed a "New" event so status derivation always has a root
    initial = OutreachEvent(
        prospect_id=prospect.id,
        channel="Email",
        event_type="New",
        notes="Prospect created",
    )
    db.add(initial)
    await db.flush()

    try:
        from app.discovery.enrich import apply_enrichment_to_prospect

        # Score without lazy-loading relationships
        apply_enrichment_to_prospect(prospect, {})
        await db.flush()
    except Exception:
        pass

    pid = prospect.id
    loaded = await get_prospect(db, pid)
    return loaded  # type: ignore[return-value]


async def update_prospect(db: AsyncSession, prospect: Prospect, updates: dict[str, Any]) -> Prospect:
    for key, value in updates.items():
        if value is not None or key in updates:
            setattr(prospect, key, value)
    apply_score(prospect, list(prospect.outreach_events or []))
    await db.flush()
    await db.refresh(prospect)
    return prospect


# ── Events & compliance ──────────────────────────────────────────────────────


class ComplianceError(Exception):
    """Raised when a Sent (or similar) event lacks required compliance fields."""


async def log_event(
    db: AsyncSession,
    prospect: Prospect,
    data: EventCreate,
    *,
    skip_opt_out_check: bool = False,
) -> OutreachEvent:
    if prospect.opted_out and data.event_type != "OptOut" and not skip_opt_out_check:
        raise ComplianceError("Prospect has opted out — no further outreach events allowed")

    # Cannot log Sent without data_source + informed_at (GDPR trail)
    if data.event_type == "Sent":
        if not prospect.data_source or not str(prospect.data_source).strip():
            raise ComplianceError("Cannot log Sent without data_source populated")
        if prospect.informed_at is None:
            # First contact disclosure: set informed_at now if missing is blocked —
            # spec says required before Sent
            raise ComplianceError(
                "Cannot log Sent without informed_at — record first-contact disclosure timestamp"
            )

    event = OutreachEvent(
        prospect_id=prospect.id,
        channel=data.channel,
        event_type=data.event_type,
        notes=data.notes,
        next_action=data.next_action,
        next_action_date=data.next_action_date,
        event_date=data.event_date or _utcnow(),
    )
    db.add(event)

    if data.event_type == "OptOut":
        prospect.opted_out = True
        prospect.opted_out_at = _utcnow()

    await db.flush()

    # Re-score after new activity
    await db.refresh(prospect)
    apply_score(prospect, list(prospect.outreach_events or []))
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


async def get_kanban_columns(db: AsyncSession) -> dict[str, list[Prospect]]:
    from app.models import KANBAN_COLUMNS

    result = await db.execute(
        select(Prospect)
        .options(selectinload(Prospect.outreach_events))
        .where(and_(Prospect.opted_out.is_(False), Prospect.anonymized.is_(False)))
    )
    prospects = list(result.scalars().unique().all())

    columns: dict[str, list[Prospect]] = {name: [] for name in KANBAN_COLUMNS}
    type_to_col = {
        et: col for col, types in KANBAN_COLUMNS.items() for et in types
    }

    for p in prospects:
        col = type_to_col.get(p.current_status, "New")
        columns[col].append(p)

    for col in columns:
        columns[col].sort(key=lambda p: p.urgency_score, reverse=True)
    return columns
