"""DECP discovery — market-play-driven public award filters (V3)."""

from __future__ import annotations

import logging
import re
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import polars as pl

from app.config import get_settings
from app.plays import get_play

logger = logging.getLogger(__name__)
DECP_CHECKPOINT_VERSION = 1

DECP_DATASET_SLUG = (
    "donnees-essentielles-de-la-commande-publique-consolidees-format-tabulaire"
)
DATA_GOUV_DATASET_API = f"https://www.data.gouv.fr/api/1/datasets/{DECP_DATASET_SLUG}/"

COL_ALIASES = {
    "dateAttribution": [
        "dateAttribution", "dateNotification", "dateattribution",
        "datenotification", "date_notification", "date_attribution",
    ],
    "codeCPV": ["codeCPV", "codecpv", "code_cpv", "cpv", "CPV"],
    "objetMarche": [
        "objetMarche", "objet", "objetmarche", "objet_marche", "intitule", "titre",
    ],
    "titulaire_siret": [
        "titulaire_siret", "titulaireSiret", "siretTitulaire",
        "siret_titulaire", "titulaire_id", "idTitulaire",
    ],
    "titulaire_nom": [
        "titulaire_nom", "titulaireNom", "nomTitulaire", "nom_titulaire", "titulaire",
    ],
    "montant": ["montant", "montantHT", "montant_ht", "amount"],
    "acheteur_nom": [
        "acheteur_nom", "acheteurNom", "nomAcheteur", "nom_acheteur", "acheteur",
    ],
    "id": ["id", "idMarche", "id_marche", "uid"],
}


def _resolve_col(df: pl.DataFrame, logical: str) -> str | None:
    cols = {c.lower(): c for c in df.columns}
    for alias in COL_ALIASES.get(logical, [logical]):
        if alias in df.columns:
            return alias
        if alias.lower() in cols:
            return cols[alias.lower()]
    return None


def _normalize_columns(df: pl.DataFrame) -> pl.DataFrame:
    rename: dict[str, str] = {}
    for logical in COL_ALIASES:
        actual = _resolve_col(df, logical)
        if actual and actual != logical:
            rename[actual] = logical
    if rename:
        df = df.rename(rename)
    return df


async def discover_decp_parquet_url() -> str:
    settings = get_settings()
    if settings.decp_parquet_url:
        return settings.decp_parquet_url
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        r = await client.get(DATA_GOUV_DATASET_API)
        r.raise_for_status()
        data = r.json()
    resources = data.get("resources") or []
    parquet_resources = [
        res for res in resources
        if ((res.get("format") or "").lower() == "parquet"
        or (res.get("url") or "").endswith(".parquet")
        or "parquet" in (res.get("title") or "").lower())
        and "statistiques" not in (res.get("url") or "").lower()
    ]
    if not parquet_resources:
        parquet_resources = [res for res in resources if "parquet" in (res.get("url") or "").lower()]
    if not parquet_resources:
        raise RuntimeError(f"No Parquet resource on {DECP_DATASET_SLUG}; set DECP_PARQUET_URL")
    parquet_resources.sort(
        key=lambda res: (res.get("last_modified") or res.get("created_at") or "", res.get("filesize") or 0),
        reverse=True,
    )
    url = parquet_resources[0]["url"]
    logger.info("DECP Parquet URL: %s", url)
    return url


def download_decp_parquet(url: str, cache_path: Path | None = None) -> pl.DataFrame:
    settings = get_settings()
    cache_path = cache_path or Path(settings.decp_cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists():
        age = datetime.now(timezone.utc) - datetime.fromtimestamp(
            cache_path.stat().st_mtime, tz=timezone.utc
        )
        if age < timedelta(hours=settings.decp_cache_hours):
            logger.info("Loading DECP from cache %s", cache_path)
            return pl.read_parquet(cache_path)
    logger.info("Downloading DECP Parquet from %s", url)
    with httpx.stream("GET", url, follow_redirects=True, timeout=300.0) as resp:
        resp.raise_for_status()
        with open(cache_path, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=1024 * 1024):
                f.write(chunk)
    df = pl.read_parquet(cache_path)
    logger.info("DECP loaded: %d rows", df.height)
    return df


async def load_decp() -> pl.DataFrame:
    url = await discover_decp_parquet_url()
    return download_decp_parquet(url)


def filter_relevant(
    df: pl.DataFrame,
    *,
    days_back: int = 120,
    min_montant: float | None = None,
    max_rows: int | None = None,
    play_code: str | None = None,
    cpv_prefixes: list[str] | tuple[str, ...] | None = None,
    keywords: list[str] | tuple[str, ...] | None = None,
    negative_keywords: list[str] | tuple[str, ...] | None = None,
) -> pl.DataFrame:
    """
    Filter awards using market-play CPV/keywords (not universal IT defaults).
    """
    play_code = play_code or "FIELD_SERVICE_OPERATIONS_FR"
    play = get_play(play_code)
    cpv_prefixes = tuple(cpv_prefixes or play.get("cpv_prefixes") or ("45", "50", "507", "453", "397", "425", "4533", "4531", "9091", "713", "7999"))
    keywords = tuple(keywords or play.get("positive_keywords") or ("maintenance", "entretien", "froid", "réfrigération", "clim", "climatisation", "chauffage", "hvac", "électrique", "intervention", "technicien"))
    negative_keywords = tuple(negative_keywords or play.get("negative_keywords") or ())

    df = _normalize_columns(df)
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days_back)

    for col, dtype in (
        ("dateAttribution", pl.Utf8),
        ("codeCPV", pl.Utf8),
        ("objetMarche", pl.Utf8),
        ("titulaire_siret", pl.Utf8),
        ("titulaire_nom", pl.Utf8),
        ("montant", pl.Float64),
        ("acheteur_nom", pl.Utf8),
        ("id", pl.Utf8),
    ):
        if col not in df.columns:
            df = df.with_columns(pl.lit(None).cast(dtype).alias(col))

    df = df.with_columns(
        [
            pl.col("titulaire_siret").cast(pl.Utf8, strict=False),
            pl.col("codeCPV").cast(pl.Utf8, strict=False),
            pl.col("objetMarche").cast(pl.Utf8, strict=False),
            pl.col("titulaire_nom").cast(pl.Utf8, strict=False),
            pl.col("acheteur_nom").cast(pl.Utf8, strict=False),
            pl.col("montant").cast(pl.Float64, strict=False),
            pl.col("id").cast(pl.Utf8, strict=False),
            pl.col("dateAttribution").cast(pl.Utf8, strict=False),
        ]
    )

    date_col = pl.col("dateAttribution")
    parsed_date = (
        date_col.str.to_datetime(strict=False, time_unit="us")
        .fill_null(date_col.str.strptime(pl.Datetime, format="%Y-%m-%d", strict=False))
        .fill_null(date_col.str.strptime(pl.Datetime, format="%Y-%m-%dT%H:%M:%S", strict=False))
        .fill_null(date_col.str.strptime(pl.Date, format="%Y-%m-%d", strict=False).cast(pl.Datetime))
    )
    df = df.with_columns(parsed_date.alias("_date"))

    cpv_expr = pl.lit(False)
    for prefix in cpv_prefixes:
        cpv_expr = cpv_expr | pl.col("codeCPV").fill_null("").str.starts_with(str(prefix))

    objet_lower = pl.col("objetMarche").fill_null("").str.to_lowercase()
    if keywords:
        kw_pattern = "|".join(re.escape(k.lower()) for k in keywords)
        kw_expr = objet_lower.str.contains(kw_pattern)
    else:
        kw_expr = pl.lit(False)

    filtered = df.filter(
        (pl.col("_date").is_not_null())
        & (pl.col("_date") >= pl.lit(cutoff))
        & (cpv_expr | kw_expr)
        & (pl.col("titulaire_siret").is_not_null())
        & (pl.col("titulaire_siret").str.replace_all(r"\D", "").str.len_chars() >= 9)
    )

    if negative_keywords:
        neg_pattern = "|".join(re.escape(k.lower()) for k in negative_keywords)
        filtered = filtered.filter(~objet_lower.str.contains(neg_pattern))

    if min_montant is not None:
        filtered = filtered.filter(
            pl.col("montant").is_null() | (pl.col("montant") >= min_montant)
        )

    filtered = filtered.with_columns(
        [
            pl.col("titulaire_siret").str.replace_all(r"\D", "").alias("titulaire_siret"),
            pl.col("titulaire_siret").str.replace_all(r"\D", "").str.slice(0, 9).alias("siren"),
            # Amount quality flag
            pl.when(pl.col("montant").is_null())
            .then(pl.lit("missing"))
            .when(pl.col("montant") <= 0)
            .then(pl.lit("invalid"))
            .otherwise(pl.lit("ok"))
            .alias("montant_quality"),
        ]
    )

    keep = [
        c for c in (
            "id", "dateAttribution", "_date", "codeCPV", "objetMarche",
            "titulaire_siret", "titulaire_nom", "montant", "acheteur_nom",
            "siren", "montant_quality",
        ) if c in filtered.columns
    ]
    filtered = filtered.select(keep).sort("_date", descending=True)
    if max_rows:
        filtered = filtered.head(max_rows)
    logger.info(
        "DECP filter (play=%s): %d awards (days=%d)",
        play.get("code"), filtered.height, days_back,
    )
    return filtered


def aggregate_by_siret(df: pl.DataFrame) -> list[dict[str, Any]]:
    if df.is_empty():
        return []
    rows = df.to_dicts()
    by_siret: dict[str, dict[str, Any]] = {}
    for row in rows:
        siret = re.sub(r"\D", "", str(row.get("titulaire_siret") or ""))
        if len(siret) == 9:
            key = siret
        elif len(siret) >= 14:
            siret = siret[:14]
            key = siret
        else:
            continue
        award = {
            "id": row.get("id"),
            "date": _date_iso(row.get("_date") or row.get("dateAttribution")),
            "objet": (row.get("objetMarche") or "")[:500],
            "cpv": row.get("codeCPV"),
            "montant": row.get("montant"),
            "montant_quality": row.get("montant_quality") or "ok",
            "acheteur": row.get("acheteur_nom"),
        }
        if key not in by_siret:
            by_siret[key] = {
                "siret": siret if len(siret) == 14 else None,
                "siren": siret[:9],
                "company_name": row.get("titulaire_nom") or f"SIRET {siret}",
                "award_history": [award],
                "last_tender_date": award["date"],
                "total_montant": float(award["montant"] or 0) if award.get("montant") else 0.0,
            }
        else:
            entry = by_siret[key]
            entry["award_history"].append(award)
            if award.get("montant"):
                entry["total_montant"] += float(award["montant"] or 0)
            if award["date"] and (
                not entry["last_tender_date"] or award["date"] > entry["last_tender_date"]
            ):
                entry["last_tender_date"] = award["date"]
            if not entry.get("siret") and len(siret) == 14:
                entry["siret"] = siret

    results = []
    for entry in by_siret.values():
        entry["award_history"].sort(key=lambda a: a.get("date") or "", reverse=True)
        entry["award_count"] = len(entry["award_history"])
        entry["has_multiple"] = entry["award_count"] >= 2
        objets = [a.get("objet") or "" for a in entry["award_history"][:3]]
        details_parts = [
            f"{entry['award_count']} award(s)",
            f"total≈{entry['total_montant']:.0f}€" if entry["total_montant"] else None,
            "multiple wins" if entry["has_multiple"] else None,
        ]
        entry["signal_details"] = " · ".join(p for p in details_parts if p)
        entry["objets_joined"] = " | ".join(objets)
        # Evidence signals for V3
        entry["evidence"] = [
            {
                "category": "trigger",
                "signal_type": "PUBLIC_AWARD_RECENT",
                "label": "Recent public award",
                "evidence_text": entry["signal_details"] + " — " + entry["objets_joined"][:300],
                "source_type": "decp",
                "confidence": 70,
                "strength": 65 if entry["has_multiple"] else 50,
            }
        ]
        if entry["has_multiple"]:
            entry["evidence"].append({
                "category": "trigger",
                "signal_type": "PUBLIC_AWARD_MULTI",
                "label": "Multiple awards",
                "evidence_text": f"{entry['award_count']} awards in discovery window",
                "source_type": "decp",
                "confidence": 75,
                "strength": 70,
            })
        # Award alone is NOT pain — only structural hint
        entry["evidence"].append({
            "category": "structural_fit",
            "signal_type": "PUBLIC_SERVICE_DELIVERY",
            "label": "Delivers public technical/service contracts",
            "evidence_text": "Supplier on public awards matching field-service play filters",
            "source_type": "decp",
            "confidence": 60,
            "strength": 40,
        })
        results.append(entry)
    results.sort(key=lambda e: (e["award_count"], e["total_montant"]), reverse=True)
    return results


def prepare_decp_award_records(df: pl.DataFrame) -> list[dict[str, Any]]:
    """Return deterministic, award-level raw records in newest-first order."""
    if df.is_empty():
        return []
    records: dict[str, dict[str, Any]] = {}
    for raw in df.to_dicts():
        event_date = _date_iso(raw.get("_date") or raw.get("dateAttribution"))
        if not event_date:
            continue
        stable_fields = {
            "source_id": raw.get("id"),
            "event_date": event_date,
            "siret": re.sub(r"\D", "", str(raw.get("titulaire_siret") or "")),
            "cpv": raw.get("codeCPV"),
            "object": raw.get("objetMarche"),
            "amount": raw.get("montant"),
            "buyer": raw.get("acheteur_nom"),
        }
        digest = hashlib.sha256(
            json.dumps(stable_fields, default=str, sort_keys=True).encode()
        ).hexdigest()
        external_id = f"decp:{digest}"
        record = dict(raw)
        record["_source_external_id"] = external_id
        record["_source_event_date"] = event_date
        records[external_id] = record
    return sorted(
        records.values(),
        key=lambda row: (
            row["_source_event_date"],
            row["_source_external_id"],
        ),
        reverse=True,
    )


def decp_plan_fingerprint(
    *,
    play_code: str,
    days_back: int,
    min_montant: float | None,
    max_rows: int | None,
    adapter_version: str,
) -> str:
    play = get_play(play_code)
    payload = {
        "checkpoint_version": DECP_CHECKPOINT_VERSION,
        "adapter_version": adapter_version,
        "play_code": play_code,
        "play_version": play.get("version"),
        "days_back": days_back,
        "min_montant": min_montant,
        "max_rows": max_rows,
        "cpv_prefixes": play.get("cpv_prefixes") or [],
        "positive_keywords": play.get("positive_keywords") or [],
        "negative_keywords": play.get("negative_keywords") or [],
    }
    return hashlib.sha256(
        json.dumps(payload, default=str, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]


def slice_decp_awards_checkpointed(
    records: list[dict[str, Any]],
    *,
    checkpoint: dict[str, Any] | None,
    limit: int,
    plan_fingerprint: str,
) -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
    """Select unseen incremental awards and progressive historical backfill.

    Incremental rows are consumed oldest-first above the committed high-water
    mark so a bounded run cannot skip an unseen row. Historical rows are
    consumed newest-first below the backfill cursor.
    """
    if limit < 1:
        raise ValueError("DECP discovery limit must be positive")
    checkpoint = checkpoint or {}
    compatible = (
        int(checkpoint.get("version") or 0) == DECP_CHECKPOINT_VERSION
        and checkpoint.get("plan_fingerprint") == plan_fingerprint
    )
    state = checkpoint if compatible else {}

    def key(row: dict[str, Any]) -> tuple[str, str]:
        return row["_source_event_date"], row["_source_external_id"]

    if not records:
        next_checkpoint = {
            "version": DECP_CHECKPOINT_VERSION,
            "plan_fingerprint": plan_fingerprint,
            "high_water": state.get("high_water"),
            "backfill_cursor": state.get("backfill_cursor"),
            "backfill_exhausted": True,
        }
        return [], next_checkpoint, True

    high_water = state.get("high_water")
    backfill_cursor = state.get("backfill_cursor")
    backfill_exhausted = bool(state.get("backfill_exhausted", False))
    if not high_water:
        selected = records[:limit]
        newest = key(records[0])
        oldest_selected = key(selected[-1]) if selected else newest
        exhausted = len(selected) >= len(records)
        next_checkpoint = {
            "version": DECP_CHECKPOINT_VERSION,
            "plan_fingerprint": plan_fingerprint,
            "high_water": {"event_date": newest[0], "external_id": newest[1]},
            "backfill_cursor": {
                "event_date": oldest_selected[0],
                "external_id": oldest_selected[1],
            },
            "backfill_exhausted": exhausted,
        }
        return selected, next_checkpoint, exhausted

    high_key = (str(high_water["event_date"]), str(high_water["external_id"]))
    incremental = sorted(
        (row for row in records if key(row) > high_key), key=key
    )
    selected = incremental[:limit]
    if selected:
        newest_committed = key(selected[-1])
        high_water = {
            "event_date": newest_committed[0],
            "external_id": newest_committed[1],
        }

    remaining = limit - len(selected)
    incremental_remaining = len(incremental) > len(selected)
    if remaining and not incremental_remaining and not backfill_exhausted:
        cursor_key = (
            (str(backfill_cursor["event_date"]), str(backfill_cursor["external_id"]))
            if backfill_cursor
            else high_key
        )
        historical = [row for row in records if key(row) < cursor_key]
        historical_page = historical[:remaining]
        selected.extend(historical_page)
        if historical_page:
            oldest_committed = key(historical_page[-1])
            backfill_cursor = {
                "event_date": oldest_committed[0],
                "external_id": oldest_committed[1],
            }
        if len(historical_page) >= len(historical):
            backfill_exhausted = True

    exhausted = not incremental_remaining and backfill_exhausted
    next_checkpoint = {
        "version": DECP_CHECKPOINT_VERSION,
        "plan_fingerprint": plan_fingerprint,
        "high_water": high_water,
        "backfill_cursor": backfill_cursor,
        "backfill_exhausted": backfill_exhausted,
    }
    return selected, next_checkpoint, exhausted


def _date_iso(val: Any) -> str | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date().isoformat()
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)[:10]
