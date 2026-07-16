"""
Ideal Customer Profile (ICP) for Elevya-style client acquisition.

Targets French SMEs that:
- Win / deliver IT, cyber, digital, software public contracts (capacity signal)
- Or operate in IT/digital NAF with mid-market headcount
- Need nearshore/external delivery capacity (Morocco corridor narrative)
- Have reachable decision-makers (dirigeant / DSI / commercial)

Every score is explicit and inspectable — no black box.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.discovery.naf import is_it_cyber_naf, normalize_naf

# ── Elevya ICP definition ────────────────────────────────────────────────────

# NAF codes that map tightly to service capacity Elevya can support
CORE_NAF = {
    "6201Z", "6202A", "6202B", "6203Z", "6209Z",
    "6311Z", "6312Z", "5829A", "5829B", "7022Z",
}
ADJACENT_NAF_PREFIXES = ("62", "63", "58", "61", "70", "71")

# Company size sweet spot for mid-market outsourcing deals
SIZE_WEIGHTS = {
    "1-10": 35,
    "11-50": 95,
    "51-200": 100,
    "200+": 45,
}

# Decision-maker quality (from annuaire dirigeants or manual)
DIRIGEANT_TITLE_WEIGHTS = (
    (["président", "president", "pdg", "gérant", "gerant", "fondateur"], 100),
    (["directeur général", "directeur general", "dg"], 95),
    (["dsi", "directeur des systèmes", "directeur systemes", "cio", "cto"], 90),
    (["directeur commercial", "directrice commerciale", "sales"], 85),
    (["directeur", "directrice"], 70),
    (["associé", "associe", "associé gérant"], 75),
)

# Public buyer quality (DECP acheteur) — digital transformation budget proxy
BUYER_KEYWORDS_HIGH = (
    "ministère", "ministere", "état", "etat", "région", "region",
    "département", "departement", "cnrs", "inria", "université",
    "universite", "hôpital", "hopital", "chs", "défense", "defense",
    "armée", "armee", "police", "gendarmerie", "assemblée", "sénat",
)
BUYER_KEYWORDS_MED = (
    "ville de", "commune", "communauté", "communaute", "métropole",
    "metropole", "syndicat", "établissement", "etablissement", "epci",
    "caisse", "urssaf", "pole emploi", "france travail",
)

# Cyber / high-value delivery signals in award object
HOT_KEYWORDS = (
    "cybersécurité", "cybersecurite", "soc ", "siem", "pentest",
    "audit de sécurité", "iso 27001", "secnum",
    "cloud", "migration", "infogérance", "infogerance",
    "tma ", "tierce maintenance", "développement", "developpement",
    "transformation numérique", "transformation numerique",
    "data ", "big data", "ia ", "intelligence artificielle",
)


@dataclass
class ScoreBreakdown:
    fit: int = 0
    timing: int = 0
    contactability: int = 0
    value: int = 0
    acquisition: int = 0
    components: list[dict[str, Any]] = field(default_factory=list)
    badges: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fit": self.fit,
            "timing": self.timing,
            "contactability": self.contactability,
            "value": self.value,
            "acquisition": self.acquisition,
            "components": self.components,
            "badges": self.badges,
            "reasons": self.reasons,
        }


def _clamp(n: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, n))


def score_naf_fit(naf_code: str | None) -> tuple[int, str | None]:
    code = normalize_naf(naf_code)
    if not code:
        return 20, None
    if code in CORE_NAF:
        return 100, "Core IT NAF"
    if is_it_cyber_naf(code) or code[:2] in ADJACENT_NAF_PREFIXES:
        return 75, "Adjacent digital NAF"
    return 25, None


def score_size_fit(company_size: str | None) -> tuple[int, str | None]:
    if not company_size:
        return 40, None
    w = SIZE_WEIGHTS.get(company_size, 40)
    badge = "SME sweet spot" if w >= 90 else ("Micro" if w < 50 else "Large")
    return w, badge if w >= 90 else None


def score_dirigeant_quality(
    title: str | None = None,
    dirigeants: list[dict] | None = None,
) -> tuple[int, str | None, dict | None]:
    """Return (score, badge, best_dirigeant)."""
    best_score = 0
    best_badge = None
    best_d = None

    titles: list[tuple[str, dict | None]] = []
    if title:
        titles.append((title.lower(), None))
    for d in dirigeants or []:
        if d.get("type_dirigeant") == "personne morale":
            continue
        q = (d.get("qualite") or d.get("title") or "").lower()
        if q:
            titles.append((q, d))

    for t, d in titles:
        for keywords, weight in DIRIGEANT_TITLE_WEIGHTS:
            if any(k in t for k in keywords):
                if weight > best_score:
                    best_score = weight
                    best_badge = keywords[0].title()
                    best_d = d
                break

    if best_score == 0 and (title or dirigeants):
        return 40, None, best_d
    if best_score == 0:
        return 15, None, None
    return best_score, best_badge, best_d


def score_timing_from_awards(
    award_history: list[dict] | None,
    last_tender_date: datetime | None,
    signal_type: str | None,
    *,
    signal_details: str | None = None,
    now: datetime | None = None,
) -> tuple[int, list[str], list[str]]:
    """Fresh public wins = high timing (capacity strain / budget in flight)."""
    now = now or datetime.now(timezone.utc)
    badges: list[str] = []
    reasons: list[str] = []
    score = 30
    details_l = (signal_details or "").lower()

    history = award_history or []
    recent_90 = 0
    recent_180 = 0
    hot = 0
    total_montant = 0.0
    high_buyer = 0

    for a in history:
        try:
            total_montant += float(a.get("montant") or 0)
        except (TypeError, ValueError):
            pass
        d = a.get("date")
        age = None
        if d:
            try:
                ad = datetime.fromisoformat(str(d)[:10]).replace(tzinfo=timezone.utc)
                age = (now - ad).days
            except ValueError:
                age = None
        if age is not None:
            if age <= 90:
                recent_90 += 1
            if age <= 180:
                recent_180 += 1
        objet = (a.get("objet") or "").lower()
        if any(k in objet for k in HOT_KEYWORDS):
            hot += 1
        acheteur = (a.get("acheteur") or "").lower()
        if any(k in acheteur for k in BUYER_KEYWORDS_HIGH):
            high_buyer += 1
        elif any(k in acheteur for k in BUYER_KEYWORDS_MED):
            high_buyer += 0  # med tracked later

    if signal_type in ("DECP_WIN", "BOAMP_WIN"):
        score += 25
        reasons.append("Public contract win signal")
    elif signal_type == "REGISTRY_IT":
        score += 8
    if recent_90:
        score += min(30, recent_90 * 15)
        badges.append(f"{recent_90} win(s) ≤90d")
        reasons.append(f"{recent_90} award(s) in last 90 days — capacity timing")
    elif recent_180:
        score += min(18, recent_180 * 9)
        badges.append(f"{recent_180} win(s) ≤180d")
    if len(history) >= 2 or "multiple" in details_l:
        score += 12
        badges.append("Multi-win streak")
        reasons.append("Multiple awards = delivery capacity signal")
    if hot or any(k in details_l for k in HOT_KEYWORDS):
        score += 15
        badges.append("Hot topic (cyber/digital)")
        reasons.append("Award language matches cyber/digital/cloud delivery")
    if high_buyer:
        score += 10
        badges.append("Premium public buyer")
    if total_montant >= 100_000:
        score += 10
        badges.append("≥100k€ awards")
    elif total_montant >= 50_000:
        score += 5

    if last_tender_date:
        ltd = last_tender_date
        if ltd.tzinfo is None:
            ltd = ltd.replace(tzinfo=timezone.utc)
        age = (now - ltd).days
        if age <= 30:
            score += 8
            badges.append("Win this month")

    return _clamp(score), badges, reasons


def score_contactability(
    *,
    email: str | None,
    contact_confidence: str | None,
    website: str | None,
    decision_maker_name: str | None,
    dirigeants: list[dict] | None,
    phone: str | None,
) -> tuple[int, list[str], list[str]]:
    score = 10
    badges: list[str] = []
    reasons: list[str] = []

    conf = (contact_confidence or "").lower()
    if email and conf == "verified":
        score += 50
        badges.append("Verified email")
        reasons.append("SMTP-verified email ready for outreach")
    elif email and conf == "likely":
        score += 35
        badges.append("Likely email")
    elif email:
        score += 25
        badges.append("Email on file")
    elif dirigeants:
        score += 20
        badges.append("Dirigeant known")
        reasons.append("Named dirigeant → high-quality email permutations")
    elif decision_maker_name:
        score += 15
        badges.append("DM named")

    if website:
        score += 15
    if phone:
        score += 10
    if not email and not dirigeants and not decision_maker_name:
        reasons.append("Needs LinkedIn / contact discovery")

    return _clamp(score), badges, reasons


def score_value_potential(
    *,
    award_history: list[dict] | None,
    company_size: str | None,
    naf_code: str | None,
) -> tuple[int, list[str]]:
    score = 40
    badges: list[str] = []
    total = 0.0
    for a in award_history or []:
        try:
            total += float(a.get("montant") or 0)
        except (TypeError, ValueError):
            pass
    if total >= 250_000:
        score += 35
        badges.append("High contract value")
    elif total >= 100_000:
        score += 25
    elif total >= 40_000:
        score += 15
    if company_size in ("11-50", "51-200"):
        score += 20
    if is_it_cyber_naf(naf_code):
        score += 15
    return _clamp(score), badges


def compute_acquisition_score(prospect: Any, *, now: datetime | None = None) -> ScoreBreakdown:
    """
    Composite acquisition score for prioritization.

    acquisition = 0.35*fit + 0.30*timing + 0.20*contactability + 0.15*value
    """
    now = now or datetime.now(timezone.utc)
    bd = ScoreBreakdown()

    naf_s, naf_b = score_naf_fit(getattr(prospect, "naf_code", None))
    size_s, size_b = score_size_fit(getattr(prospect, "company_size", None))
    dir_s, dir_b, _ = score_dirigeant_quality(
        getattr(prospect, "decision_maker_title", None),
        getattr(prospect, "dirigeants", None),
    )
    fit = int(round(0.45 * naf_s + 0.30 * size_s + 0.25 * dir_s))
    bd.fit = _clamp(fit)
    bd.components.append({"axis": "fit", "naf": naf_s, "size": size_s, "dirigeant": dir_s})
    for b in (naf_b, size_b, dir_b):
        if b:
            bd.badges.append(b)
    if naf_s >= 75:
        bd.reasons.append("NAF aligns with IT/digital delivery ICP")
    if size_s >= 90:
        bd.reasons.append("Headcount in mid-market outsourcing sweet spot")

    timing, t_badges, t_reasons = score_timing_from_awards(
        getattr(prospect, "award_history", None),
        getattr(prospect, "last_tender_date", None),
        getattr(prospect, "signal_type", None),
        signal_details=getattr(prospect, "signal_details", None),
        now=now,
    )
    bd.timing = timing
    bd.badges.extend(t_badges)
    bd.reasons.extend(t_reasons)

    contact, c_badges, c_reasons = score_contactability(
        email=getattr(prospect, "email", None),
        contact_confidence=getattr(prospect, "contact_confidence", None),
        website=getattr(prospect, "website", None),
        decision_maker_name=getattr(prospect, "decision_maker_name", None),
        dirigeants=getattr(prospect, "dirigeants", None),
        phone=getattr(prospect, "phone", None),
    )
    bd.contactability = contact
    bd.badges.extend(c_badges)
    bd.reasons.extend(c_reasons)

    value, v_badges = score_value_potential(
        award_history=getattr(prospect, "award_history", None),
        company_size=getattr(prospect, "company_size", None),
        naf_code=getattr(prospect, "naf_code", None),
    )
    bd.value = value
    bd.badges.extend(v_badges)

    acq = int(round(0.35 * bd.fit + 0.30 * bd.timing + 0.20 * bd.contactability + 0.15 * bd.value))
    bd.acquisition = _clamp(acq)

    # Deduplicate badges preserving order
    seen: set[str] = set()
    uniq: list[str] = []
    for b in bd.badges:
        if b not in seen:
            seen.add(b)
            uniq.append(b)
    bd.badges = uniq[:8]
    bd.reasons = bd.reasons[:6]
    return bd


def pick_best_dirigeant(dirigeants: list[dict] | None) -> dict | None:
    """Prefer Président / DG over commissaire aux comptes."""
    if not dirigeants:
        return None
    _, _, best = score_dirigeant_quality(dirigeants=dirigeants)
    if best:
        return best
    for d in dirigeants:
        if d.get("type_dirigeant") == "personne morale":
            continue
        q = (d.get("qualite") or "").lower()
        if "commissaire" in q:
            continue
        return d
    return None


def format_dirigeant_name(d: dict) -> str:
    prenoms = (d.get("prenoms") or d.get("prenom") or "").strip()
    nom = (d.get("nom") or "").strip()
    # Title-case French names carefully
    def tc(s: str) -> str:
        return " ".join(p.capitalize() for p in s.split()) if s else ""

    return f"{tc(prenoms)} {tc(nom)}".strip()
