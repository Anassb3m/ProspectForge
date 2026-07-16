"""Buyer-role helpers (play-aware). Legacy IT ICP replaced by scoring_v3 + plays."""

from __future__ import annotations

from app.plays import get_play, DEFAULT_PLAY_CODE


def pick_best_dirigeant(dirigeants: list[dict] | None, play_code: str | None = None) -> dict | None:
    """Prefer operational buyers for the active play; fall back to legal rep."""
    if not dirigeants:
        return None
    play = get_play(play_code or DEFAULT_PLAY_CODE)
    roles = play.get("buyer_roles") or []

    best = None
    best_prio = 999
    for d in dirigeants:
        if d.get("type_dirigeant") == "personne morale":
            continue
        q = (d.get("qualite") or "").lower()
        if "commissaire" in q:
            continue
        for br in roles:
            labels = br.get("labels") or []
            if any(lab in q for lab in labels):
                prio = br.get("priority", 9)
                if prio < best_prio:
                    best_prio = prio
                    best = d
                break
    if best:
        return best
    # Fallback: first physical person who is not auditor
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

    def tc(s: str) -> str:
        return " ".join(p.capitalize() for p in s.split()) if s else ""

    return f"{tc(prenoms)} {tc(nom)}".strip()


# Compatibility shims for older imports
def compute_acquisition_score(prospect, **kwargs):
    from app.scoring_v3 import score_prospect_v3
    from types import SimpleNamespace

    r = score_prospect_v3(prospect)
    return SimpleNamespace(
        fit=r.fit,
        timing=r.trigger,
        contactability=r.authority,
        value=r.value,
        acquisition=r.opportunity_score,
        badges=r.badges,
        reasons=r.reasons,
        to_dict=r.to_dict,
    )


def score_naf_fit(naf_code):
    from app.discovery.naf import is_field_service_naf, is_it_cyber_naf, normalize_naf

    code = normalize_naf(naf_code)
    if not code:
        return 20, None
    if is_it_cyber_naf(code):
        return 5, "IT exclusion"
    if is_field_service_naf(code):
        return 100, "Field-service NAF"
    return 40, None


def score_timing_from_awards(*args, **kwargs):
    return 30, [], []
