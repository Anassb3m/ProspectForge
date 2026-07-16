"""
V3 opportunity scoring — evidence-aware, play-specific, with hard readiness gates.

Separate from action urgency (follow-ups / replies).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.plays import DEFAULT_PLAY_CODE, get_play


@dataclass
class OpportunityResult:
    fit: int = 0
    pain: int = 0
    trigger: int = 0
    authority: int = 0
    value: int = 0
    data_quality: int = 0
    opportunity_score: int = 0
    penalties: int = 0
    readiness_state: str = "research_required"
    readiness_failures: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    badges: list[str] = field(default_factory=list)
    suspected_pain: str | None = None
    why_now: str | None = None
    recommended_buyer_role: str | None = None
    personalization_brief: str | None = None
    recommended_offer: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "fit": self.fit,
            "pain": self.pain,
            "trigger": self.trigger,
            "authority": self.authority,
            "value": self.value,
            "data_quality": self.data_quality,
            "opportunity_score": self.opportunity_score,
            "penalties": self.penalties,
            "readiness_state": self.readiness_state,
            "readiness_failures": self.readiness_failures,
            "reasons": self.reasons,
            "badges": self.badges,
            "suspected_pain": self.suspected_pain,
            "why_now": self.why_now,
            "recommended_buyer_role": self.recommended_buyer_role,
            "personalization_brief": self.personalization_brief,
            "recommended_offer": self.recommended_offer,
        }


def _clamp(n: float, lo: int = 0, hi: int = 100) -> int:
    return int(max(lo, min(hi, round(n))))


def compute_opportunity_score(
    *,
    fit: int,
    pain: int,
    trigger: int,
    authority: int,
    value: int,
    data_quality: int,
    penalties: int = 0,
    manual_override: int = 0,
    weights: dict | None = None,
) -> int:
    w = weights or {
        "fit": 0.25,
        "pain": 0.25,
        "trigger": 0.20,
        "authority": 0.15,
        "value": 0.10,
        "data_quality": 0.05,
    }
    raw = (
        w["fit"] * fit
        + w["pain"] * pain
        + w["trigger"] * trigger
        + w["authority"] * authority
        + w["value"] * value
        + w["data_quality"] * data_quality
    )
    confidence_multiplier = 0.65 + 0.35 * (data_quality / 100)
    score = raw * confidence_multiplier - penalties + manual_override
    return _clamp(score)


def evaluate_readiness(
    *,
    fit: int,
    pain: int,
    trigger: int,
    authority: int,
    data_quality: int,
    signal_count: int,
    source_type_count: int,
    human_accepted: bool,
    suppressed: bool,
    contact_usable: bool,
    offer_ok: bool,
    config: dict,
) -> tuple[str, list[str]]:
    if suppressed:
        return "suppressed", ["Company or contact is suppressed"]

    failures: list[str] = []
    if fit < config.get("fit_score_min", 55):
        failures.append(f"fit_score < {config.get('fit_score_min')}")
    if pain < config.get("pain_score_min", 35):
        failures.append(f"pain_score < {config.get('pain_score_min')}")
    if trigger < config.get("trigger_score_min", 25):
        failures.append(f"trigger_score < {config.get('trigger_score_min')}")
    if authority < config.get("authority_score_min", 40):
        failures.append(f"authority_score < {config.get('authority_score_min')}")
    if data_quality < config.get("data_quality_min", 45):
        failures.append(f"data_quality < {config.get('data_quality_min')}")
    if signal_count < config.get("active_signals_min", 2):
        failures.append("insufficient_signals")
    if source_type_count < config.get("independent_source_types_min", 1):
        failures.append("insufficient_independent_sources")
    if not contact_usable:
        failures.append("contact_required")
    if config.get("offer_asset_required") and not offer_ok:
        failures.append("proof_required")
    if config.get("human_review_required") and not human_accepted:
        failures.append("human_review_required")

    if not failures:
        return "contact_ready", []
    if "human_review_required" in failures and len(failures) == 1:
        return "human_review_required", failures
    if "contact_required" in failures:
        return "contact_required", failures
    if fit < 40:
        return "insufficient_identity", failures
    return "research_required", failures


def score_prospect_v3(prospect: Any, play_code: str | None = None) -> OpportunityResult:
    """
    Score a Prospect-like object for the active (or given) market play.
    Uses award_history, naf, size, dirigeants, signals list, contact fields.
    """
    play = get_play(play_code or getattr(prospect, "market_play_code", None) or DEFAULT_PLAY_CODE)
    result = OpportunityResult()
    result.recommended_offer = play.get("offer_name")
    reasons: list[str] = []
    badges: list[str] = []
    penalties = 0
    pen_cfg = (play.get("score_config") or {}).get("penalties") or {}

    naf = (getattr(prospect, "naf_code", None) or "").replace(".", "").upper()
    size = getattr(prospect, "company_size", None) or getattr(prospect, "employee_band", None)
    signals = list(getattr(prospect, "signals_cache", None) or getattr(prospect, "evidence_signals", None) or [])
    # Also accept JSON list stored on prospect
    if not signals and getattr(prospect, "evidence_json", None):
        signals = list(prospect.evidence_json or [])

    # ── Fit ────────────────────────────────────────────────────────────────
    fit = 25
    target_prefixes = play.get("target_naf_prefixes") or []
    target_codes = {c.replace(".", "").upper() for c in (play.get("target_naf_codes") or [])}
    excluded_prefixes = play.get("excluded_naf_prefixes") or []
    excluded_codes = {c.replace(".", "").upper() for c in (play.get("excluded_naf_codes") or [])}

    if naf:
        if naf in excluded_codes or (len(naf) >= 2 and naf[:2] in excluded_prefixes):
            fit = 5
            penalties += pen_cfg.get("internal_it_team", 25)
            reasons.append("Excluded NAF (software/digital) — not target buyer")
            badges.append("IT exclusion")
        elif naf in target_codes or (len(naf) >= 2 and naf[:2] in target_prefixes):
            fit = 85
            reasons.append(f"NAF {naf} matches field-service / technical installation play")
            badges.append("Target NAF")
        else:
            fit = 40
            reasons.append(f"NAF {naf} adjacent / unverified for play")

    target_sizes = play.get("target_sizes") or ["11-50", "51-200"]
    if size in ("11-50", "51-200"):
        fit = min(100, fit + 15)
        badges.append("SME fit")
        reasons.append("Headcount in mid-market service sweet spot")
    elif size == "1-10":
        fit = min(100, fit + 5)
        if fit < 50:
            penalties += pen_cfg.get("micro_weak", 10)
    elif size == "200+":
        penalties += pen_cfg.get("oversized", 15)
        badges.append("Large")

    # ── Pain ───────────────────────────────────────────────────────────────
    pain = 15
    pain_hits: list[str] = []
    details = (getattr(prospect, "signal_details", None) or "").lower()
    notes = (getattr(prospect, "notes", None) or "").lower()
    blob = f"{details} {notes}"
    for hyp in play.get("pain_hypotheses") or []:
        # weak automatic match via keywords in details
        key = hyp.lower().split()[0] if hyp else ""
        if key and key in blob:
            pain_hits.append(hyp)

    # Structural complexity proxies from awards / multi-site language
    awards = list(getattr(prospect, "award_history", None) or [])
    if awards:
        pain = max(pain, 35)
        pain_hits.append("Public service/maintenance delivery implies operational coordination")
    if any(k in blob for k in ("multisite", "multi-site", "agences", "techniciens", "maintenance")):
        pain = max(pain, 50)
        pain_hits.append("Multi-site or technician language suggests coordination complexity")
        badges.append("Ops complexity")
    if any(k in blob for k in ("excel", "manuel", "papier", "whatsapp", "pdf")):
        pain = max(pain, 60)
        pain_hits.append("Manual/Excel workflow signal")
        badges.append("Manual workflow")

    # Signals list boost
    for s in signals:
        cat = (s.get("category") if isinstance(s, dict) else getattr(s, "category", "")) or ""
        if cat == "pain":
            pain = max(pain, 55)
            lab = s.get("label") if isinstance(s, dict) else getattr(s, "label", "")
            if lab:
                pain_hits.append(str(lab))

    if not pain_hits:
        pain = max(pain, 20)
    result.suspected_pain = pain_hits[0] if pain_hits else (play.get("pain_hypotheses") or [None])[0]

    # ── Trigger ────────────────────────────────────────────────────────────
    trigger = 10
    why_now_parts: list[str] = []
    now = datetime.now(timezone.utc)
    recent = 0
    for a in awards:
        d = a.get("date") if isinstance(a, dict) else None
        if d:
            try:
                ad = datetime.fromisoformat(str(d)[:10]).replace(tzinfo=timezone.utc)
                age = (now - ad).days
                if age <= 90:
                    recent += 1
            except ValueError:
                recent += 1
        else:
            recent += 1
    if recent:
        trigger = min(100, 40 + recent * 15)
        why_now_parts.append(f"{recent} recent public award(s)")
        badges.append(f"{recent} award(s)")
        reasons.append("Public award timing — capacity / delivery pressure possible")
    if len(awards) >= 2:
        trigger = min(100, trigger + 12)
        badges.append("Multi-award")
        why_now_parts.append("Multiple awards in window")
    signal_type = getattr(prospect, "signal_type", None)
    if signal_type in ("DECP_WIN", "BOAMP_WIN", "PUBLIC_AWARD"):
        trigger = max(trigger, 45)
    if signal_type in ("REGISTRY_IT",):
        # Legacy IT registry — low trigger for field play
        trigger = min(trigger, 20)
        penalties += 10
    if signal_type in ("REGISTRY_FIELD", "STRUCTURAL"):
        trigger = max(trigger, 25)

    for s in signals:
        cat = (s.get("category") if isinstance(s, dict) else getattr(s, "category", "")) or ""
        if cat == "trigger":
            trigger = max(trigger, 55)
            lab = s.get("label") if isinstance(s, dict) else getattr(s, "label", "")
            if lab:
                why_now_parts.append(str(lab))

    result.why_now = "; ".join(why_now_parts) if why_now_parts else "No strong timing trigger yet — research required"

    # ── Authority ──────────────────────────────────────────────────────────
    authority = 15
    title = (getattr(prospect, "decision_maker_title", None) or "").lower()
    name = getattr(prospect, "decision_maker_name", None)
    role_match = None
    for br in play.get("buyer_roles") or []:
        labels = br.get("labels") or []
        if any(l in title for l in labels):
            authority = max(authority, 100 - (br.get("priority", 3) - 1) * 10)
            role_match = br.get("role")
            badges.append("Buyer role match")
            reasons.append(f"Title matches preferred buyer role ({br.get('role')})")
            break
    if name and authority < 40:
        authority = 35  # named person but role unconfirmed
        badges.append("Person named")
    if not name:
        authority = min(authority, 25)

    result.recommended_buyer_role = role_match or "gerant_owner"

    # Contact path (does not make ready alone)
    email = getattr(prospect, "email", None)
    conf = (getattr(prospect, "contact_confidence", None) or "").lower()
    contact_usable = False
    if conf in ("verified", "deliverable_non_catch_all", "published_personal", "confirmed_by_reply"):
        authority = min(100, authority + 15)
        contact_usable = True
        badges.append("Contact OK")
    elif conf in ("likely", "published_generic"):
        authority = min(100, authority + 8)
        contact_usable = True
    elif email and conf in ("domain_and_pattern_only", "unverified", "guessed"):
        # guessed only — not usable for send
        contact_usable = False
        badges.append("Guessed email")
    elif email:
        contact_usable = conf not in ("invalid", "bounced", "risky", "suppressed")

    # ── Value ──────────────────────────────────────────────────────────────
    value = 40
    total_m = 0.0
    for a in awards:
        try:
            total_m += float((a.get("montant") if isinstance(a, dict) else 0) or 0)
        except (TypeError, ValueError):
            pass
    if total_m >= 100_000:
        value = 80
        badges.append("≥100k€ awards")
    elif total_m >= 40_000:
        value = 65
    if size in ("11-50", "51-200"):
        value = min(100, value + 10)

    # ── Data quality ───────────────────────────────────────────────────────
    dq = 30
    sources = set()
    if getattr(prospect, "data_source", None):
        sources.add("declared")
        dq += 15
    if getattr(prospect, "siren", None) or getattr(prospect, "siret", None):
        sources.add("registry")
        dq += 20
    if awards:
        sources.add("decp")
        dq += 15
    if name:
        sources.add("person")
        dq += 10
    if getattr(prospect, "website", None):
        dq += 5
    if len(sources) == 1:
        penalties += pen_cfg.get("single_source", 10)
    dq = _clamp(dq)

    # ── Compose ────────────────────────────────────────────────────────────
    result.fit = _clamp(fit)
    result.pain = _clamp(pain)
    result.trigger = _clamp(trigger)
    result.authority = _clamp(authority)
    result.value = _clamp(value)
    result.data_quality = dq
    result.penalties = penalties
    result.opportunity_score = compute_opportunity_score(
        fit=result.fit,
        pain=result.pain,
        trigger=result.trigger,
        authority=result.authority,
        value=result.value,
        data_quality=result.data_quality,
        penalties=penalties,
        weights=(play.get("score_config") or {}).get("weights"),
    )
    result.reasons = reasons[:8]
    result.badges = list(dict.fromkeys(badges))[:8]

    human_accepted = (
        getattr(prospect, "manual_review_state", None) == "accepted"
        or getattr(prospect, "qualification_decision", None) == "accept"
    )
    suppressed = bool(getattr(prospect, "opted_out", False) or getattr(prospect, "is_suppressed", False))

    state, failures = evaluate_readiness(
        fit=result.fit,
        pain=result.pain,
        trigger=result.trigger,
        authority=result.authority,
        data_quality=result.data_quality,
        signal_count=max(len(signals), (1 if awards else 0) + (1 if naf else 0)),
        source_type_count=len(sources),
        human_accepted=human_accepted,
        suppressed=suppressed,
        contact_usable=contact_usable and bool(name or email),
        offer_ok=True,
        config=play.get("readiness_config") or {},
    )
    result.readiness_state = state
    result.readiness_failures = failures

    # Personalization brief
    company = getattr(prospect, "company_name", "Company")
    result.personalization_brief = (
        f"Observed: {company}"
        + (f" (NAF {naf})" if naf else "")
        + f"\nWhy now: {result.why_now}"
        + f"\nLikely pain: {result.suspected_pain or '—'}"
        + f"\nBuyer role: {result.recommended_buyer_role}"
        + f"\nOffer: {result.recommended_offer}"
        + f"\nSafe first line: reference a real award/object or multi-site ops — do not invent internal tools."
        + f"\nDo not claim: that they lack software, or that an award proves budget for custom software."
        + f"\nCTA: short diagnostic call on intervention/planning flow."
    )
    return result


def apply_v3_score(prospect: Any, play_code: str | None = None) -> Any:
    """Mutate prospect with V3 score fields."""
    r = score_prospect_v3(prospect, play_code)
    prospect.fit_score = r.fit
    prospect.pain_score = r.pain
    prospect.trigger_score = r.trigger
    prospect.authority_score = r.authority
    prospect.value_score = r.value
    prospect.data_quality_score = r.data_quality
    prospect.opportunity_score = r.opportunity_score
    prospect.acquisition_score = r.opportunity_score  # keep legacy sort field aligned
    prospect.readiness_state = r.readiness_state
    prospect.readiness_failures = r.readiness_failures
    prospect.score_breakdown = r.to_dict()
    prospect.suspected_pain = r.suspected_pain
    prospect.why_now = r.why_now
    prospect.recommended_buyer_role = r.recommended_buyer_role
    prospect.personalization_brief = r.personalization_brief
    prospect.recommended_offer = r.recommended_offer
    if play_code or not getattr(prospect, "market_play_code", None):
        prospect.market_play_code = play_code or DEFAULT_PLAY_CODE

    # Priority from opportunity
    if r.opportunity_score >= 70:
        prospect.priority_level = "High"
    elif r.opportunity_score >= 45:
        prospect.priority_level = "Medium"
    else:
        prospect.priority_level = "Low"
    prospect.urgency_score = r.opportunity_score
    return prospect
