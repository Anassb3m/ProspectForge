"""
V3 opportunity scoring — evidence-aware, play-specific, hard readiness gates.

Rules (commercial correctness):
- Public awards contribute trigger/value/structural fit only — NEVER pain.
- Generic activity words (maintenance, techniciens) are NOT pain.
- Pain requires explicit workflow/pain evidence or human confirmation.
- human_accepted requires a full QualificationReview accept with required flags.
- contact_usable requires deliverability + person match (not generic alone).
- Independent sources are real origins (decp, annuaire, sirene, website…), not “person”.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.plays import DEFAULT_PLAY_CODE, get_play

# Explicit pain language — not the company's business description
PAIN_KEYWORDS = (
    "excel",
    "tableur",
    "spreadsheet",
    "papier",
    "whatsapp",
    "double saisie",
    "double-saisie",
    "saisie manuelle",
    "manuellement",
    "manuelle",
    "dispatch",
    "planification manuelle",
    "planning manuel",
    "reporting manuel",
    "pdf déconnect",
    "pdf deconnect",
    "formulaires papier",
    "coordination difficile",
    "goulot",
    "goulot d'étranglement",
    "re-saisie",
    "resaise",
    "portails multiples",
    "sans gmao",
    "pas de gmao",
    "pas de crm",
)

# Structural complexity — NOT pain, modest fit/value only
STRUCTURAL_COMPLEXITY_KEYWORDS = (
    "multisite",
    "multi-site",
    "multi sites",
    "plusieurs agences",
    "agences",
    "techniciens",
    "flotte",
    "astreinte",
    "24/7",
    "24h/24",
)

# Real independent source origins (not derived fields)
INDEPENDENT_SOURCES = frozenset({
    "decp",
    "boamp",
    "sirene",
    "annuaire",
    "registry",
    "website",
    "bodacc",
    "jobs",
    "job",
    "linkedin",
    "manual",
    "call",
})

# Email-send ready: deliverability + person-level match
EMAIL_READY_CONFIDENCE = frozenset({
    "deliverable",
    "verified",  # legacy alias of deliverable
    "published_personal",
    "confirmed_by_reply",
})

# Allowed confidence values server-side (never free-text)
ALLOWED_CONTACT_CONFIDENCE = frozenset({
    "untested",
    "syntax_valid",
    "domain_valid",
    "deliverable",
    "catch_all",
    "risky",
    "indeterminate",
    "invalid",
    "bounced",
    "confirmed_by_reply",
    "published_personal",
    "published_generic",
    "domain_and_pattern_only",
    "verified",
    "likely",
    "unverified",
    "needs_review",
    "none",
    "manual_confirmed",
})

ALLOWED_DISCOVERY_STATES = frozenset({
    "published",
    "inferred",
    "guessed",
    "user_supplied",
    "none",
})


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


def evidence_fingerprint(
    *,
    source_type: str | None,
    signal_type: str | None,
    evidence_text: str | None = None,
    evidence_url: str | None = None,
    observed_at: str | None = None,
) -> str:
    raw = "|".join(
        [
            (source_type or "").lower().strip(),
            (signal_type or "").upper().strip(),
            (evidence_url or "").strip().lower()[:200],
            re.sub(r"\s+", " ", (evidence_text or "").strip().lower())[:120],
            (observed_at or "")[:10],
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def normalize_signals(signals: list[Any]) -> list[dict]:
    """Normalize signal dicts or ORM rows; drop inactive."""
    out: list[dict] = []
    seen: set[str] = set()
    for s in signals or []:
        if isinstance(s, dict):
            d = dict(s)
        else:
            d = {
                "category": getattr(s, "category", None),
                "signal_type": getattr(s, "signal_type", None),
                "label": getattr(s, "label", None),
                "evidence_text": getattr(s, "evidence_text", None),
                "evidence_url": getattr(s, "evidence_url", None),
                "source_type": getattr(s, "source_type", None),
                "confidence": getattr(s, "confidence", 50),
                "strength": getattr(s, "strength", 50),
                "is_active": getattr(s, "is_active", True),
                "manually_confirmed": getattr(s, "manually_confirmed", False),
            }
        if d.get("is_active") is False:
            continue
        fp = d.get("fingerprint") or evidence_fingerprint(
            source_type=d.get("source_type"),
            signal_type=d.get("signal_type"),
            evidence_text=d.get("evidence_text"),
            evidence_url=d.get("evidence_url"),
        )
        if fp in seen:
            continue
        seen.add(fp)
        d["fingerprint"] = fp
        out.append(d)
    return out


def independent_source_types(signals: list[dict], *, awards: bool, has_registry_id: bool) -> set[str]:
    sources: set[str] = set()
    for s in signals:
        st = (s.get("source_type") or "").lower().strip()
        if st in INDEPENDENT_SOURCES:
            sources.add(st)
        elif st in ("recherche", "annuaire entreprises"):
            sources.add("annuaire")
    if awards:
        sources.add("decp")
    if has_registry_id and "annuaire" not in sources and "sirene" not in sources:
        # Identity only counts as registry if no richer annuaire signal
        sources.add("sirene")
    return sources


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
    if pain < config.get("pain_score_min", 40):
        failures.append(f"pain_score < {config.get('pain_score_min')} (need real workflow pain, not award alone)")
    if trigger < config.get("trigger_score_min", 25):
        failures.append(f"trigger_score < {config.get('trigger_score_min')}")
    if authority < config.get("authority_score_min", 40):
        failures.append(f"authority_score < {config.get('authority_score_min')}")
    if data_quality < config.get("data_quality_min", 45):
        failures.append(f"data_quality < {config.get('data_quality_min')}")
    if signal_count < config.get("active_signals_min", 2):
        failures.append("insufficient_signals")
    if source_type_count < config.get("independent_source_types_min", 2):
        failures.append("insufficient_independent_sources")
    if not contact_usable:
        failures.append("contact_required")
    if config.get("offer_asset_required") and not offer_ok:
        failures.append("proof_required")
    if config.get("human_review_required", True) and not human_accepted:
        failures.append("human_review_required")

    if not failures:
        return "contact_ready", []
    if "human_review_required" in failures and len([f for f in failures if f != "human_review_required"]) == 0:
        return "human_review_required", failures
    if "contact_required" in failures and fit >= 55 and pain >= 40:
        return "contact_required", failures
    if fit < 40:
        return "insufficient_identity", failures
    return "research_required", failures


def _signal_dicts(prospect: Any) -> list[dict]:
    """Prefer ORM evidence rows (signals_cache), then evidence_json."""
    raw: list[Any] = []
    cache = getattr(prospect, "signals_cache", None)
    if cache:
        raw = list(cache)
    elif getattr(prospect, "evidence_json", None):
        raw = list(prospect.evidence_json or [])
    return normalize_signals(raw)


def _is_full_human_accept(prospect: Any) -> bool:
    """
    Source of truth: latest qualification accept with required confirmations.
    Falls back to flags cached on prospect only if full review was stored.
    """
    review = getattr(prospect, "latest_qualification", None)
    if review is not None:
        if getattr(review, "decision", None) != "accept":
            return False
        return all(
            [
                getattr(review, "fit_confirmed", False),
                getattr(review, "pain_confirmed", False),
                getattr(review, "trigger_confirmed", False),
                getattr(review, "buyer_confirmed", False),
                getattr(review, "contact_confirmed", False),
                getattr(review, "offer_match_confirmed", False),
            ]
        )
    # Cached projection — only if accept AND all six stored on prospect
    if getattr(prospect, "manual_review_state", None) != "accepted":
        return False
    # Without full review flags on prospect, require explicit all-true cache
    flags = getattr(prospect, "qualification_flags", None) or {}
    if flags:
        return all(flags.get(k) for k in (
            "fit_confirmed", "pain_confirmed", "trigger_confirmed",
            "buyer_confirmed", "contact_confirmed", "offer_match_confirmed",
        ))
    # Incomplete accept is NOT enough
    return False


def score_prospect_v3(prospect: Any, play_code: str | None = None) -> OpportunityResult:
    play = get_play(play_code or getattr(prospect, "market_play_code", None) or DEFAULT_PLAY_CODE)
    result = OpportunityResult()
    result.recommended_offer = play.get("offer_name")
    reasons: list[str] = []
    badges: list[str] = []
    penalties = 0
    pen_cfg = (play.get("score_config") or {}).get("penalties") or {}

    naf = (getattr(prospect, "naf_code", None) or "").replace(".", "").upper()
    size = getattr(prospect, "company_size", None) or getattr(prospect, "employee_band", None)
    signals = _signal_dicts(prospect)
    awards = list(getattr(prospect, "award_history", None) or [])
    details = (getattr(prospect, "signal_details", None) or "").lower()
    notes = (getattr(prospect, "notes", None) or "").lower()
    blob = f"{details} {notes}"

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
            reasons.append(f"NAF {naf} matches field-service play")
            badges.append("Target NAF")
        else:
            fit = 40
            reasons.append(f"NAF {naf} adjacent / unverified for play")

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

    # Structural complexity from multi-site language → modest fit, NOT pain
    if any(k in blob for k in STRUCTURAL_COMPLEXITY_KEYWORDS):
        fit = min(100, fit + 5)
        badges.append("Structural complexity")
    for s in signals:
        if s.get("category") == "structural_fit":
            fit = min(100, fit + 3)

    # ── Pain — NO contribution from awards or generic "maintenance" ────────
    pain = 0
    pain_hits: list[str] = []
    suspected_only: list[str] = []

    # Awards may only set *suspected* pain hypothesis text — zero points
    if awards:
        suspected_only.append(
            "Hypothesis only: public service delivery may imply coordination load — not verified pain"
        )

    # Explicit workflow/pain keywords only
    if any(k in blob for k in PAIN_KEYWORDS):
        pain = max(pain, 40)
        pain_hits.append("Explicit manual/workflow language in notes or details")
        badges.append("Manual workflow")
        reasons.append("Pain from explicit workflow evidence (Excel/paper/WhatsApp/double entry…)")

    for s in signals:
        cat = (s.get("category") or "").lower()
        stype = (s.get("signal_type") or "").upper()
        if cat == "pain" or stype.startswith("PAIN_") or stype in (
            "MANUAL_PDF_WORKFLOW",
            "EXCEL_OR_MANUAL_REPORTING_MENTION",
            "NO_CUSTOMER_PORTAL",
            "HIRING_PLANNING_COORDINATOR",
            "HIRING_ADMIN_OPERATIONS",
        ):
            strength = int(s.get("strength") or 50)
            pain = max(pain, min(80, 40 + strength // 5))
            lab = s.get("label") or stype
            pain_hits.append(str(lab))
            if s.get("manually_confirmed"):
                pain = max(pain, 55)
                badges.append("Pain confirmed")

    # Human pain confirmation from qualification
    review = getattr(prospect, "latest_qualification", None)
    if review is not None and getattr(review, "pain_confirmed", False):
        pain = max(pain, 55)
        pain_hits.append("Human confirmed operational pain")
        badges.append("Pain confirmed")

    if not pain_hits:
        # Keep suspected hypothesis for brief, but pain score stays 0–15 max
        pain = 0
        result.suspected_pain = (
            suspected_only[0]
            if suspected_only
            else (play.get("pain_hypotheses") or [None])[0]
        )
        if result.suspected_pain:
            reasons.append("Suspected pain is hypothesis only — does not satisfy pain gate")
    else:
        result.suspected_pain = pain_hits[0]

    # ── Trigger (awards belong here) ───────────────────────────────────────
    trigger = 10
    why_now_parts: list[str] = []
    now = datetime.now(timezone.utc)
    recent = 0
    for a in awards:
        d = a.get("date") if isinstance(a, dict) else None
        if d:
            try:
                ad = datetime.fromisoformat(str(d)[:10]).replace(tzinfo=timezone.utc)
                if (now - ad).days <= 90:
                    recent += 1
            except ValueError:
                recent += 1
        else:
            recent += 1
    if recent:
        trigger = min(100, 40 + recent * 15)
        why_now_parts.append(f"{recent} recent public award(s)")
        badges.append(f"{recent} award(s)")
        reasons.append("Public award = timing/capacity signal, not proof of software need")
    if len(awards) >= 2:
        trigger = min(100, trigger + 12)
        badges.append("Multi-award")
        why_now_parts.append("Multiple awards in window")

    signal_type = getattr(prospect, "signal_type", None)
    if signal_type in ("DECP_WIN", "BOAMP_WIN", "PUBLIC_AWARD"):
        trigger = max(trigger, 45)
    if signal_type == "REGISTRY_IT":
        trigger = min(trigger, 20)
        penalties += 10
    if signal_type in ("REGISTRY_FIELD", "STRUCTURAL"):
        trigger = max(trigger, 20)  # structural discovery only — weak timing

    for s in signals:
        if (s.get("category") or "") == "trigger":
            trigger = max(trigger, 55)
            if s.get("label"):
                why_now_parts.append(str(s["label"]))

    result.why_now = (
        "; ".join(why_now_parts)
        if why_now_parts
        else "No strong timing trigger yet — research required"
    )

    # ── Authority ──────────────────────────────────────────────────────────
    authority = 15
    title = (getattr(prospect, "decision_maker_title", None) or "").lower()
    name = getattr(prospect, "decision_maker_name", None)
    role_match = None
    for br in play.get("buyer_roles") or []:
        labels = br.get("labels") or []
        if any(lab in title for lab in labels):
            authority = max(authority, 100 - (br.get("priority", 3) - 1) * 10)
            role_match = br.get("role")
            badges.append("Buyer role match")
            reasons.append(f"Title matches preferred buyer role ({br.get('role')})")
            break
    if name and authority < 40:
        authority = 35
        badges.append("Person named")
    if not name:
        authority = min(authority, 25)
    result.recommended_buyer_role = role_match or "gerant_owner"

    # Contact: deliverability AND person match — not generic alone
    conf = (getattr(prospect, "contact_confidence", None) or "").lower()
    disc = (getattr(prospect, "contact_discovery_state", None) or "").lower()
    contact_usable = False
    if conf in EMAIL_READY_CONFIDENCE and disc != "guessed":
        authority = min(100, authority + 15)
        contact_usable = True
        badges.append("Contact OK")
    elif conf == "manual_confirmed":
        authority = min(100, authority + 12)
        contact_usable = True
        badges.append("Contact manually confirmed")
    elif conf == "published_generic":
        authority = min(100, authority + 5)
        contact_usable = False  # generic mailbox ≠ decision-maker path for email-ready
        badges.append("Generic mailbox only")
        reasons.append("Generic role email is not person-matched — LinkedIn-first or research")
    elif conf in ("likely", "domain_and_pattern_only", "unverified") or disc == "guessed":
        contact_usable = False
        badges.append("Guessed email")
        reasons.append("Guessed/pattern email is not email-contact-ready")
    elif conf in ("catch_all", "indeterminate", "risky"):
        contact_usable = False
        badges.append("Risky/catch-all contact")
    elif conf in ("invalid", "bounced", "suppressed"):
        contact_usable = False
        penalties += 5

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

    # ── Data quality & independent sources ─────────────────────────────────
    indep = independent_source_types(
        signals,
        awards=bool(awards),
        has_registry_id=bool(getattr(prospect, "siren", None) or getattr(prospect, "siret", None)),
    )
    dq = 25 + min(50, len(indep) * 15)
    if getattr(prospect, "data_source", None):
        dq += 10
    if getattr(prospect, "website", None):
        dq += 5
    if len(indep) <= 1:
        penalties += pen_cfg.get("single_source", 10)
    dq = _clamp(dq)

    # Active signal count — real evidence rows only, not invent from awards+naf
    signal_count = len(signals)
    if awards and not any((s.get("source_type") or "").lower() == "decp" for s in signals):
        signal_count += 1  # award history counts as one trigger source signal

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

    human_accepted = _is_full_human_accept(prospect)
    suppressed = bool(
        getattr(prospect, "opted_out", False)
        or getattr(prospect, "is_suppressed", False)
    )

    # offer_ok: true if assets exist OR play doesn't require (pilot)
    offer_ok = bool(getattr(prospect, "offer_assets_ok", False))
    readiness_cfg = dict(play.get("readiness_config") or {})
    # Stricter pain floor: awards must not pass alone
    readiness_cfg.setdefault("pain_score_min", 40)
    readiness_cfg.setdefault("independent_source_types_min", 2)
    readiness_cfg.setdefault("human_review_required", True)

    state, failures = evaluate_readiness(
        fit=result.fit,
        pain=result.pain,
        trigger=result.trigger,
        authority=result.authority,
        data_quality=result.data_quality,
        signal_count=signal_count,
        source_type_count=len(indep),
        human_accepted=human_accepted,
        suppressed=suppressed,
        contact_usable=contact_usable and bool(name or getattr(prospect, "email", None)),
        offer_ok=offer_ok or not readiness_cfg.get("offer_asset_required"),
        config=readiness_cfg,
    )
    # Extra hard rule: no contact_ready without real pain evidence
    if state == "contact_ready" and result.pain < 40:
        state = "research_required"
        failures = list(failures) + ["pain_score insufficient (award alone is not pain)"]
    if state == "contact_ready" and not human_accepted:
        state = "human_review_required"
        failures = list(failures) + ["human_review_required"]

    result.readiness_state = state
    result.readiness_failures = failures

    company = getattr(prospect, "company_name", "Company")
    result.personalization_brief = (
        f"Observed: {company}"
        + (f" (NAF {naf})" if naf else "")
        + f"\nWhy now: {result.why_now}"
        + f"\nPain status: {result.suspected_pain or 'none verified'} "
        + f"(score={result.pain}; hypothesis≠evidence)"
        + f"\nBuyer role: {result.recommended_buyer_role}"
        + f"\nOffer: {result.recommended_offer}"
        + "\nSafe first line: reference a real award/object or multi-site ops — do not invent internal tools."
        + "\nDo not claim: that they lack software, or that an award proves budget for custom software."
        + "\nCTA: short diagnostic call on intervention/planning flow."
    )
    return result


def apply_v3_score(prospect: Any, play_code: str | None = None) -> Any:
    r = score_prospect_v3(prospect, play_code)
    prospect.fit_score = r.fit
    prospect.pain_score = r.pain
    prospect.trigger_score = r.trigger
    prospect.authority_score = r.authority
    prospect.value_score = r.value
    prospect.data_quality_score = r.data_quality
    prospect.opportunity_score = r.opportunity_score
    prospect.acquisition_score = r.opportunity_score
    prospect.urgency_score = r.opportunity_score
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

    if r.opportunity_score >= 70:
        prospect.priority_level = "High"
    elif r.opportunity_score >= 45:
        prospect.priority_level = "Medium"
    else:
        prospect.priority_level = "Low"

    # Stage from readiness
    rs = r.readiness_state
    if rs == "contact_ready":
        prospect.acquisition_stage = "contact_ready"
        prospect.needs_manual_review = False
    elif rs == "human_review_required":
        prospect.acquisition_stage = "human_review_required"
        prospect.needs_manual_review = True
    elif rs == "suppressed":
        prospect.acquisition_stage = "suppressed"
    elif rs == "contact_required":
        prospect.acquisition_stage = "enriched"
        prospect.needs_manual_review = True
    else:
        prospect.acquisition_stage = "researching"
        prospect.needs_manual_review = True

    prospect.timing_score = r.trigger
    prospect.contactability_score = r.authority
    return prospect
