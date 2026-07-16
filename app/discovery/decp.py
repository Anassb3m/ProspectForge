"""DECP discovery — market-play-driven public award filters (V3)."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import polars as pl

from app.config import get_settings
from app.plays import DEFAULT_PLAY_CODE, get_play

logger = logging.getLogger(__name__)

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
        if (res.get("format") or "").lower() == "parquet"
        or (res.get("url") or "").endswith(".parquet")
        or "parquet" in (res.get("title") or "").lower()
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
    play = get_play(play_code or DEFAULT_PLAY_CODE)
    cpv_prefixes = tuple(cpv_prefixes or play.get("cpv_prefixes") or ())
    keywords = tuple(keywords or play.get("positive_keywords") or ())
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


def _date_iso(val: Any) -> str | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date().isoformat()
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)[:10]
