"""
Legacy commercial compatibility projection.

Canonical opportunity scoring lives only in ``services.scoring_v4``. This
module keeps old Prospect screens synchronized while they are migrated.
"""

from __future__ import annotations

import logging
import hashlib
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    EvidenceSignal,
    EvidenceItem,
    OfferAsset,
    Prospect,
    QualificationReview,
    SuppressionEntry,
)
ALLOWED_CONTACT_CONFIDENCE = frozenset({
    "untested", "syntax_valid", "domain_valid", "deliverable", "catch_all",
    "risky", "indeterminate", "invalid", "bounced", "confirmed_by_reply",
    "published_personal", "published_generic", "domain_and_pattern_only",
    "verified", "likely", "unverified", "needs_review", "none", "manual_confirmed"
})

ALLOWED_DISCOVERY_STATES = frozenset({
    "published", "inferred", "guessed", "user_supplied", "none"
})

logger = logging.getLogger(__name__)


async def load_evidence_for_prospect(db: AsyncSession, prospect_id: int) -> list[EvidenceSignal]:
    result = await db.execute(
        select(EvidenceSignal).where(
            and_(
                EvidenceSignal.prospect_id == prospect_id,
                EvidenceSignal.is_active.is_(True),
            )
        )
    )
    return list(result.scalars().all())


async def load_latest_qualification(
    db: AsyncSession, prospect_id: int
) -> QualificationReview | None:
    result = await db.execute(
        select(QualificationReview)
        .where(QualificationReview.prospect_id == prospect_id)
        .order_by(QualificationReview.created_at.desc(), QualificationReview.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def is_suppressed(
    db: AsyncSession,
    *,
    email: str | None = None,
    domain: str | None = None,
    siren: str | None = None,
) -> bool:
    checks: list[tuple[str, str]] = []
    if email:
        checks.append(("email", email.strip().lower()))
        if "@" in email:
            checks.append(("domain", email.split("@", 1)[1].strip().lower()))
    if domain:
        checks.append(("domain", domain.strip().lower().removeprefix("www.")))
    if siren:
        checks.append(("siren", "".join(c for c in siren if c.isdigit())))

    for kind, value in checks:
        if not value:
            continue
        r = await db.execute(
            select(SuppressionEntry.id).where(
                and_(
                    SuppressionEntry.kind == kind,
                    SuppressionEntry.value_normalized == value,
                )
            ).limit(1)
        )
        if r.scalar_one_or_none() is not None:
            return True
    return False


async def add_suppression(
    db: AsyncSession,
    *,
    kind: str,
    value: str,
    reason: str | None = None,
    source: str | None = None,
) -> None:
    value_n = value.strip().lower()
    if kind == "siren":
        value_n = "".join(c for c in value if c.isdigit())
    if kind == "domain":
        value_n = value_n.removeprefix("www.")
    existing = await db.execute(
        select(SuppressionEntry).where(
            and_(
                SuppressionEntry.kind == kind,
                SuppressionEntry.value_normalized == value_n,
            )
        ).limit(1)
    )
    if existing.scalar_one_or_none():
        return
    db.add(
        SuppressionEntry(
            kind=kind,
            value_normalized=value_n,
            reason=reason,
            source=source,
        )
    )


def evidence_fingerprint(source_type: str | None, signal_type: str | None, evidence_text: str | None, evidence_url: str | None) -> str:
    """Helper to dedupe evidence signals."""
    parts = [
        str(x or "").strip().lower()
        for x in (signal_type, source_type, evidence_text, evidence_url)
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


async def upsert_evidence(
    db: AsyncSession,
    prospect_id: int,
    evidence_items: list[dict[str, Any]],
) -> int:
    """Write canonical evidence first, then its read-only legacy projection."""
    if not evidence_items:
        return 0
    prospect = await db.get(Prospect, prospect_id)
    if prospect is None:
        raise ValueError("Evidence prospect does not exist")
    if not prospect.company_id or not prospect.opportunity_id:
        raise ValueError("Evidence requires an explicit canonical opportunity mapping")

    added = 0
    for ev in evidence_items:
        if not isinstance(ev, dict):
            continue
        fp = evidence_fingerprint(
            source_type=ev.get("source_type"),
            signal_type=ev.get("signal_type"),
            evidence_text=ev.get("evidence_text"),
            evidence_url=ev.get("evidence_url"),
        )
        canonical = await db.scalar(
            select(EvidenceItem).where(
                EvidenceItem.opportunity_id == prospect.opportunity_id,
                EvidenceItem.fingerprint == fp,
            )
        )
        if canonical is None:
            canonical = EvidenceItem(
                company_id=prospect.company_id,
                opportunity_id=prospect.opportunity_id,
                code=(ev.get("signal_type") or "UNKNOWN")[:100],
                fingerprint=fp,
                category=(ev.get("category") or "structural_fit")[:50],
                evidence_text=(ev.get("evidence_text") or "")[:4000],
                source_url=ev.get("evidence_url"),
                source_type=ev.get("source_type"),
                source_record_id=(
                    str(ev.get("source_record_id"))[:200]
                    if ev.get("source_record_id") is not None
                    else None
                ),
                extractor_version=str(ev.get("extractor_version") or "legacy-v1")[:50],
                confidence=max(0.0, min(1.0, float(ev.get("confidence") or 50) / 100.0)),
                strength=max(0.0, min(1.0, float(ev.get("strength") or 50) / 100.0)),
                verification_state=(
                    "manually_confirmed"
                    if ev.get("manually_confirmed")
                    else "source_observed"
                ),
                contradiction_status=str(
                    ev.get("contradiction_status") or "none"
                )[:30],
                is_active=True,
            )
            db.add(canonical)
            await db.flush()
            added += 1
        projection = await db.scalar(
            select(EvidenceSignal.id).where(
                EvidenceSignal.canonical_evidence_id == canonical.id
            )
        )
        if projection is None:
            db.add(
                EvidenceSignal(
                    canonical_evidence_id=canonical.id,
                    prospect_id=prospect_id,
                    category=canonical.category,
                    signal_type=canonical.code[:80],
                    label=(ev.get("label") or "")[:200],
                    evidence_text=canonical.evidence_text,
                    evidence_url=canonical.source_url,
                    source_type=canonical.source_type,
                    confidence=round(canonical.confidence * 100),
                    strength=round(canonical.strength * 100),
                    is_active=canonical.is_active,
                    manually_confirmed=(
                        canonical.verification_state == "manually_confirmed"
                    ),
                )
            )

    return added


def merge_evidence_json(existing: list | None, new_items: list[dict]) -> list[dict]:
    """Dedupe compatibility cache on prospect.evidence_json."""
    from app.discovery.enrich import normalize_signals
    merged = normalize_signals(list(existing or []) + list(new_items or []))
    return merged[:40]


async def has_active_offer_assets(db: AsyncSession, play_code: str | None) -> bool:
    q = select(OfferAsset.id).where(OfferAsset.is_active.is_(True)).limit(1)
    if play_code:
        q = select(OfferAsset.id).where(
            and_(
                OfferAsset.is_active.is_(True),
                (OfferAsset.market_play_code == play_code) | (OfferAsset.market_play_code.is_(None)),
            )
        ).limit(1)
    r = await db.execute(q)
    return r.scalar_one_or_none() is not None


def validate_contact_confidence(value: str | None) -> str:
    v = (value or "none").lower().strip()
    if v not in ALLOWED_CONTACT_CONFIDENCE:
        raise ValueError(
            f"Invalid contact_confidence '{value}'. "
            f"Allowed: {sorted(ALLOWED_CONTACT_CONFIDENCE)}"
        )
    return v


def validate_discovery_state(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    v = value.lower().strip()
    if v not in ALLOWED_DISCOVERY_STATES:
        raise ValueError(f"Invalid contact_discovery_state '{value}'")
    return v


async def recompute_commercial_state(
    db: AsyncSession,
    prospect: Prospect,
    *,
    play_code: str | None = None,
) -> Prospect:
    """Load evidence + qualification + suppression; apply V3 projection."""
    # Ensure relationships / caches
    signals = await load_evidence_for_prospect(db, prospect.id)
    prospect.signals_cache = signals  # type: ignore[attr-defined]

    review = await load_latest_qualification(db, prospect.id)
    prospect.latest_qualification = review  # type: ignore[attr-defined]

    suppressed = await is_suppressed(
        db,
        email=prospect.email,
        siren=prospect.siren,
    )
    if prospect.opted_out:
        suppressed = True
    prospect.is_suppressed = suppressed  # type: ignore[attr-defined]

    play = play_code or prospect.market_play_code
    prospect.offer_assets_ok = await has_active_offer_assets(db, play)  # type: ignore[attr-defined]

    # Sync evidence_json cache from normalized rows (deduped)
    prospect.evidence_json = [
        {
            "category": s.category,
            "signal_type": s.signal_type,
            "label": s.label,
            "evidence_text": s.evidence_text,
            "source_type": s.source_type,
            "confidence": s.confidence,
            "strength": s.strength,
            "manually_confirmed": s.manually_confirmed,
        }
        for s in signals
    ]

    # Hard Gates & Readiness Evaluation
    has_identity = bool(prospect.siren or prospect.siret)
    has_domain = bool(prospect.website)
    has_evidence = len(signals) > 0
    has_contact = prospect.contact_confidence in ("verified", "manual_confirmed", "deliverable")
    
    if suppressed:
        prospect.readiness_state = "suppressed"
        prospect.acquisition_stage = "parked"
    elif not has_identity:
        prospect.readiness_state = "insufficient_identity"
    elif not has_domain and not has_evidence:
        prospect.readiness_state = "research_required"
    elif not has_evidence:
        prospect.readiness_state = "research_required"
    elif not has_contact:
        prospect.readiness_state = "contact_required"
    elif prospect.needs_manual_review or not review or review.decision != "accept":
        prospect.readiness_state = "human_review_required"
    else:
        prospect.readiness_state = "contact_ready"
        prospect.acquisition_stage = "contacting"

    return prospect
