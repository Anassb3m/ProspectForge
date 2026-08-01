"""
Recherche Entreprises — market-play driven company discovery (V3).

No longer defaults to Section J / IT SMEs.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any
from urllib.parse import quote

import httpx

from app.discovery.icp import format_dirigeant_name, pick_best_dirigeant
from app.discovery.naf import is_it_cyber_naf, map_naf_to_sector, map_tranche_effectifs, normalize_naf
from app.plays import DEFAULT_PLAY_CODE, get_play

logger = logging.getLogger(__name__)
BASE = "https://recherche-entreprises.api.gouv.fr"
SME_TRANCHES = "11,12,21,22,31,32"
REGISTRY_CHECKPOINT_VERSION = 2


async def search_companies(
    *,
    q: str = "",
    activite_principale: str | None = None,
    section_activite_principale: str | None = None,
    tranche_effectif_salarie: str = SME_TRANCHES,
    page: int = 1,
    per_page: int = 25,
    etat_administratif: str = "A",
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "page": page,
        "per_page": min(per_page, 25),
        "etat_administratif": etat_administratif,
    }
    if q:
        params["q"] = q
    if activite_principale:
        params["activite_principale"] = activite_principale
    if section_activite_principale:
        params["section_activite_principale"] = section_activite_principale
    if tranche_effectif_salarie:
        params["tranche_effectif_salarie"] = tranche_effectif_salarie
    if client is not None:
        response = await client.get(f"{BASE}/search", params=params)
        response.raise_for_status()
        return response.json()
    async with httpx.AsyncClient(timeout=30.0) as owned_client:
        response = await owned_client.get(f"{BASE}/search", params=params)
        response.raise_for_status()
        return response.json()


async def get_by_siren(siren: str) -> dict[str, Any] | None:
    siren = "".join(c for c in siren if c.isdigit())
    if len(siren) != 9:
        return None
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(f"{BASE}/search", params={"q": siren, "per_page": 1})
        if r.status_code != 200:
            return None
        results = r.json().get("results") or []
        for item in results:
            if item.get("siren") == siren:
                return item
        return results[0] if results else None


def normalize_company(item: dict[str, Any], *, signal_hint: str = "REGISTRY_FIELD") -> dict[str, Any]:
    siege = item.get("siege") or {}
    naf = normalize_naf(item.get("activite_principale") or siege.get("activite_principale"))
    tranche = item.get("tranche_effectif_salarie") or siege.get("tranche_effectif_salarie")
    dirigeants_raw = item.get("dirigeants") or []
    dirigeants = []
    for d in dirigeants_raw:
        if not isinstance(d, dict):
            continue
        dirigeants.append({
            "nom": d.get("nom"),
            "prenoms": d.get("prenoms"),
            "qualite": d.get("qualite"),
            "type_dirigeant": d.get("type_dirigeant"),
            "denomination": d.get("denomination"),
        })
    best = pick_best_dirigeant(dirigeants)
    dm_name = format_dirigeant_name(best) if best else None
    dm_title = (best.get("qualite") if best else None) or None
    siret = siege.get("siret")
    return {
        "siren": item.get("siren"),
        "siret": siret,
        "company_name": item.get("nom_complet") or item.get("nom_raison_sociale") or item.get("sigle"),
        "naf_code": naf,
        "sector": map_naf_to_sector(naf),
        "company_size": map_tranche_effectifs(tranche),
        "tranche_effectifs": tranche,
        "dirigeants": dirigeants,
        "decision_maker_name": dm_name,
        "decision_maker_title": dm_title,
        "city": siege.get("libelle_commune") or siege.get("commune"),
        "department": (siege.get("departement") or "")[:3] or None,
        "region": siege.get("region"),
        "address": siege.get("adresse") or siege.get("geo_adresse"),
        "website": None,
        "phone": None,
        "diffusion_status": "diffusible",
        "signal_hint": signal_hint,
        "nombre_etablissements": item.get("nombre_etablissements_ouverts"),
    }


def _passes_play_filter(n: dict[str, Any], play: dict) -> bool:
    naf = normalize_naf(n.get("naf_code"))
    if not naf:
        return False
    if is_it_cyber_naf(naf):
        return False
    classifications = play.get("classifications") or {}
    classified_exclusions = classifications.get("exclude_codes") or []
    excluded = {
        str(c).replace(".", "").upper()
        for c in [*(play.get("excluded_naf_codes") or []), *classified_exclusions]
    }
    excl_pref = play.get("excluded_naf_prefixes") or []
    if naf in excluded or naf[:2] in excl_pref:
        return False
    classified_targets = [
        entry.get("code") if isinstance(entry, dict) else entry
        for entry in (classifications.get("include_codes") or [])
    ]
    targets = {
        str(c).replace(".", "").upper()
        for c in [*(play.get("target_naf_codes") or []), *classified_targets]
        if c
    }
    prefs = play.get("target_naf_prefixes") or []
    if targets or prefs:
        if naf in targets or naf[:2] in prefs:
            return True
        return False
    return True


def registry_discovery_plan(
    play: dict[str, Any], *, max_pages_per_partition: int
) -> tuple[list[tuple[str, str]], str]:
    """Build a stable plan from both supported market-play schemas.

    The V2 play stores NAF codes in ``classifications.include_codes`` while
    the older play stores them in ``target_naf_codes``. Treating either as
    absent silently collapses discovery to a few keyword pages, so this
    adapter is deliberately explicit and fingerprinted.
    """
    classifications = play.get("classifications") or {}
    classified_codes = [
        entry.get("code") if isinstance(entry, dict) else entry
        for entry in (classifications.get("include_codes") or [])
    ]
    naf_codes: list[str] = []
    for value in [*(play.get("target_naf_codes") or []), *classified_codes]:
        normalized = str(value or "").replace(".", "").upper()
        if normalized and normalized not in naf_codes:
            naf_codes.append(normalized)

    # Keyword partitions are exploratory and may be noisy. They are only used
    # when explicitly configured, or as a compatibility fallback for a play
    # with no classification targets at all.
    configured_queries = play.get("registry_queries")
    queries = list(configured_queries or [])
    if not naf_codes and not queries:
        queries = ["maintenance", "installation technique"]

    partitions = [*(('naf', code) for code in naf_codes)]
    partitions.extend(("query", str(query)) for query in queries if query)
    if not partitions:
        raise ValueError(f"Market play {play.get('code')} has no registry discovery plan")

    plan_payload = {
        "checkpoint_version": REGISTRY_CHECKPOINT_VERSION,
        "play_code": play.get("code"),
        "play_version": play.get("version"),
        "tranches": SME_TRANCHES,
        "max_pages_per_partition": max_pages_per_partition,
        "partitions": partitions,
    }
    fingerprint = hashlib.sha256(
        json.dumps(plan_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]
    return partitions, fingerprint


async def discover_companies_for_play(
    play_code: str | None = None,
    *,
    max_results: int = 80,
    pages_per_query: int = 3,
) -> list[dict[str, Any]]:
    """Compatibility wrapper for a bounded replay from the first partition."""
    results, _, _ = await discover_companies_for_play_checkpointed(
        play_code,
        max_results=max_results,
        pages_per_query=pages_per_query,
        checkpoint={"partition": 0, "offset": 0},
    )
    return results


async def discover_companies_for_play_checkpointed(
    play_code: str | None = None,
    *,
    max_results: int = 80,
    pages_per_query: int = 3,
    checkpoint: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
    """Discover from a durable page cursor.

    ``checkpoint`` identifies the next deterministic partition and row offset.
    The returned cursor may be persisted only after the caller commits every
    record from this batch. Replays with the same cursor are idempotent.
    """
    play = get_play(play_code or DEFAULT_PLAY_CODE)
    if max_results < 1:
        raise ValueError("max_results must be positive")
    if pages_per_query < 1:
        raise ValueError("pages_per_query must be positive")
    partitions, plan_fingerprint = registry_discovery_plan(
        play, max_pages_per_partition=pages_per_query
    )
    by_siren: dict[str, dict] = {}

    def _ingest(
        item: dict,
        *,
        force: bool = False,
        source_meta: dict[str, Any],
    ) -> None:
        n = normalize_company(item, signal_hint="REGISTRY_FIELD")
        if not n.get("siren"):
            return
        if not force and not _passes_play_filter(n, play):
            return
        if is_it_cyber_naf(n.get("naf_code")):
            return
        if n["siren"] not in by_siren:
            # Structural evidence only — no automatic pain
            n["evidence"] = [
                {
                    "category": "structural_fit",
                    "signal_type": "REGISTRY_ACTIVITY",
                    "label": f"Registry NAF {n.get('naf_code')}",
                    "evidence_text": f"{n.get('company_name')} — {n.get('sector')} — size {n.get('company_size')}",
                    "source_type": "annuaire",
                    "confidence": 70,
                    "strength": 45,
                }
            ]
            if n.get("nombre_etablissements") and int(n["nombre_etablissements"] or 0) >= 2:
                n["evidence"].append({
                    "category": "structural_fit",
                    "signal_type": "MULTI_SITE_OPERATIONS",
                    "label": "Multiple establishments",
                    "evidence_text": f"{n['nombre_etablissements']} establishments ouverts",
                    "source_type": "annuaire",
                    "confidence": 65,
                    "strength": 55,
                })
            # The exact upstream record is carried to the raw persistence
            # stage. It is removed before canonical prospect enrichment work
            # is fingerprinted or queued.
            n["_source_record"] = {"record": item, "metadata": source_meta}
            by_siren[n["siren"]] = n

    checkpoint = checkpoint or {}
    compatible = (
        int(checkpoint.get("version") or 0) == REGISTRY_CHECKPOINT_VERSION
        and checkpoint.get("plan_fingerprint") == plan_fingerprint
    )
    cursor = (
        max(0, min(int(checkpoint.get("partition", 0)), len(partitions)))
        if compatible
        else 0
    )
    page = max(1, int(checkpoint.get("page", 1))) if compatible else 1
    offset = max(0, int(checkpoint.get("offset", 0))) if compatible else 0
    start_checkpoint = {
        "version": REGISTRY_CHECKPOINT_VERSION,
        "plan_fingerprint": plan_fingerprint,
        "partition": cursor,
        "page": page,
        "offset": offset,
    }
    if checkpoint and not compatible:
        logger.warning(
            "Registry checkpoint rebased because its discovery plan changed: old=%s new=%s",
            checkpoint,
            start_checkpoint,
        )

    async with httpx.AsyncClient(timeout=30.0) as client:
        while cursor < len(partitions) and len(by_siren) < max_results:
            kind, value = partitions[cursor]
            try:
                if kind == "naf":
                    naf_q = (
                        value
                        if "." in value
                        else f"{value[:2]}.{value[2:]}"
                        if len(value) >= 4
                        else value
                    )
                    data = await search_companies(
                        q="",
                        activite_principale=naf_q,
                        section_activite_principale=None,
                        page=page,
                        per_page=25,
                        client=client,
                    )
                else:
                    data = await search_companies(
                        q=value,
                        section_activite_principale=None,
                        page=page,
                        per_page=25,
                        client=client,
                    )
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    logger.warning(
                        "Annuaire rate limit (429) reached at %s %r page=%d, returning partial results.",
                        kind, value, page
                    )
                    break
                logger.warning(
                    "Annuaire %s %r page=%d failed: %s", kind, value, page, exc
                )
                raise
            except httpx.HTTPError as exc:
                logger.warning(
                    "Annuaire %s %r page=%d failed: %s", kind, value, page, exc
                )
                raise

            page_results = list(data.get("results") or [])
            total_pages = max(1, int(data.get("total_pages") or page))
            index = min(offset, len(page_results))
            while index < len(page_results) and len(by_siren) < max_results:
                item = page_results[index]
                _ingest(
                    item,
                    force=kind == "naf",
                    source_meta={
                        "kind": kind,
                        "value": value,
                        "page": page,
                        "offset": index,
                        "plan_fingerprint": plan_fingerprint,
                    },
                )
                index += 1
            if index < len(page_results):
                offset = index
                break

            offset = 0
            if not page_results or page >= total_pages or page >= pages_per_query:
                cursor += 1
                page = 1
            else:
                page += 1

    results = list(by_siren.values())

    def rank_key(c: dict) -> tuple:
        naf = normalize_naf(c.get("naf_code")) or ""
        core = 0 if naf[:2] in (play.get("target_naf_prefixes") or []) else 1
        size = 0 if c.get("company_size") in ("11-50", "51-200") else 1
        dm = 0 if c.get("decision_maker_name") else 1
        return (core, size, dm)

    results.sort(key=rank_key)
    results = results[:max_results]
    exhausted = cursor >= len(partitions)
    next_checkpoint = {
        "version": REGISTRY_CHECKPOINT_VERSION,
        "plan_fingerprint": plan_fingerprint,
        "partition": cursor,
        "page": page,
        "offset": offset,
    }
    logger.info(
        "Annuaire play=%s checkpoint=%s->%s exhausted=%s companies=%d",
        play.get("code"),
        start_checkpoint,
        next_checkpoint,
        exhausted,
        len(results),
    )
    return results, next_checkpoint, exhausted


# Back-compat alias — redirects to field play discovery
async def discover_it_smes(**kwargs) -> list[dict[str, Any]]:
    logger.warning("discover_it_smes is deprecated; using discover_companies_for_play")
    return await discover_companies_for_play(**kwargs)


async def enrich_from_annuaire(siren: str) -> dict[str, Any] | None:
    item = await get_by_siren(siren)
    if not item:
        return None
    return normalize_company(item)


def linkedin_people_url(company: str, person: str | None = None, title: str | None = None) -> str:
    parts = [f'"{company}"']
    if person:
        parts.append(f'"{person}"')
    if title:
        parts.append(title)
    q = "site:linkedin.com/in " + " ".join(parts)
    return f"https://www.google.com/search?q={quote(q)}"
