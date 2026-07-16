"""Urgency scoring engine — explicit, inspectable weighted function."""

from datetime import datetime, timezone

from app.discovery.naf import is_it_cyber_naf
from app.models import OutreachEvent, Prospect


def priority_from_score(score: int) -> str:
    """Derive priority label from urgency score."""
    if score >= 75:
        return "High"
    if score >= 45:
        return "Medium"
    return "Low"


def _award_count_recent(prospect: Prospect, *, days: int = 180, now: datetime) -> int:
    history = prospect.award_history or []
    if not history:
        return 0
    count = 0
    for a in history:
        d = a.get("date")
        if not d:
            count += 1  # undated still counts as signal of multi-win list
            continue
        try:
            ad = datetime.fromisoformat(str(d)[:10]).replace(tzinfo=timezone.utc)
            if (now - ad).days <= days:
                count += 1
        except ValueError:
            count += 1
    return count


def _montant_high(prospect: Prospect, threshold: float = 50_000) -> bool:
    history = prospect.award_history or []
    for a in history:
        try:
            if float(a.get("montant") or 0) >= threshold:
                return True
        except (TypeError, ValueError):
            continue
    return False


def calculate_urgency_score(
    prospect: Prospect,
    events: list[OutreachEvent] | None = None,
    *,
    now: datetime | None = None,
) -> int:
    """
    Weighted urgency score in [0, 100].

    Factors (v2.1):
    - DECP/BOAMP public win (+ multi-award, cyber/montant boosts)
    - Morocco ops / pain post signals
    - IT/cyber NAF code
    - Decision-maker title seniority
    - Sweet-spot company size
    - Decay when last outreach is stale (21+ days)
    """
    score = 50
    events = events if events is not None else list(prospect.outreach_events or [])
    now = now or datetime.now(timezone.utc)

    signal = prospect.signal_type
    details = (prospect.signal_details or "").lower()

    if signal in ("DECP_WIN", "BOAMP_WIN"):
        score += 30
        award_count = _award_count_recent(prospect, now=now)
        if award_count >= 2 or "multiple" in details:
            score += 15
        if _montant_high(prospect) or "cybersécurité" in details or "cyber" in details:
            score += 10
    elif signal == "REGISTRY_IT":
        score += 18  # strong ICP but weaker timing than a fresh award
    elif signal == "MOROCCO_OPS":
        score += 15
    elif signal == "PAIN_POST":
        score += 20

    # V3: IT/cyber NAF is no longer a general urgency bonus (wrong ICP).
    # Field-service fit is handled by scoring_v3 opportunity model.

    title = (prospect.decision_maker_title or "").lower()
    if title and any(
        t in title for t in ("fondateur", "dirigeant", "directeur commercial", "dsi", "cto")
    ):
        score += 10

    if prospect.company_size in ("11-50", "51-200"):
        score += 8

    # Verified contact slightly boosts actionability
    if getattr(prospect, "contact_confidence", None) == "verified":
        score += 3

    # Decay: no activity in 21+ days since last outreach event
    if events:
        last = events[-1].event_date
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        last_event_age_days = (now - last).days
        if last_event_age_days > 21:
            score -= 10

    return max(0, min(100, score))


def apply_score(prospect: Prospect, events: list[OutreachEvent] | None = None) -> Prospect:
    """Mutate prospect with recalculated score and priority."""
    score = calculate_urgency_score(prospect, events)
    prospect.urgency_score = score
    prospect.priority_level = priority_from_score(score)
    return prospect


def explain_score(prospect: Prospect, events: list[OutreachEvent] | None = None) -> list[dict]:
    """Return score components for UI transparency / tuning."""
    components: list[dict] = [{"label": "Base", "delta": 50}]
    details = (prospect.signal_details or "").lower()
    now = datetime.now(timezone.utc)

    if prospect.signal_type in ("DECP_WIN", "BOAMP_WIN"):
        components.append({"label": "Public award (DECP/BOAMP)", "delta": 30})
        if _award_count_recent(prospect, now=now) >= 2 or "multiple" in details:
            components.append({"label": "Multiple recent awards", "delta": 15})
        if _montant_high(prospect) or "cyber" in details:
            components.append({"label": "High value or cyber signal", "delta": 10})
    elif prospect.signal_type == "MOROCCO_OPS":
        components.append({"label": "Morocco ops signal", "delta": 15})
    elif prospect.signal_type == "PAIN_POST":
        components.append({"label": "Pain post signal", "delta": 20})

    if is_it_cyber_naf(getattr(prospect, "naf_code", None)):
        components.append({"label": "IT/cyber NAF", "delta": 12})

    title = (prospect.decision_maker_title or "").lower()
    if title and any(
        t in title for t in ("fondateur", "dirigeant", "directeur commercial", "dsi", "cto")
    ):
        components.append({"label": "Senior decision-maker title", "delta": 10})

    if prospect.company_size in ("11-50", "51-200"):
        components.append({"label": "SME size fit", "delta": 8})

    if getattr(prospect, "contact_confidence", None) == "verified":
        components.append({"label": "Verified email", "delta": 3})

    events = events if events is not None else list(prospect.outreach_events or [])
    if events:
        last = events[-1].event_date
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if (now - last).days > 21:
            components.append({"label": "Stale outreach decay", "delta": -10})

    total = max(0, min(100, sum(c["delta"] for c in components)))
    components.append({"label": "Total (clamped)", "delta": total})
    return components
