#!/usr/bin/env python3
"""Seed legacy evidence into a disposable pfscale02 migration rehearsal DB."""

from __future__ import annotations

import asyncio
from urllib.parse import urlparse

from sqlalchemy import text

from app.config import get_settings
from app.database import async_session_factory


async def main() -> None:
    database_url = get_settings().database_url
    database_name = urlparse(database_url.replace("+asyncpg", "")).path.lstrip("/")
    allowed_prefixes = (
        "prospectforge_canonical_gate_",
        "prospectforge_production_rehearsal_",
    )
    if not database_name.startswith(allowed_prefixes):
        raise RuntimeError("Refusing to seed a non-rehearsal database")
    async with async_session_factory() as session:
        revision = await session.scalar(text("SELECT version_num FROM alembic_version"))
        if revision != "pfscale02_20260731":
            raise RuntimeError(f"Expected pfscale02_20260731, found {revision}")
        await session.execute(
            text(
                "INSERT INTO market_play_versions "
                "(id, play_code, version, status, jurisdiction, locale) VALUES "
                "('rehearsal-play', 'FIELD_OPERATIONS_FR_V2', '2.0.0', "
                "'active', 'FR', 'fr-FR')"
            )
        )
        await session.execute(
            text(
                "INSERT INTO companies "
                "(id, canonical_name, country_code, jurisdiction_code, entity_status) "
                "VALUES ('rehearsal-company', 'Rehearsal Maintenance', 'FR', "
                "'GB-EW', 'active')"
            )
        )
        await session.execute(
            text(
                "INSERT INTO opportunities "
                "(id, company_id, play_version_id, status, priority, latest_score) "
                "VALUES ('rehearsal-opportunity', 'rehearsal-company', "
                "'rehearsal-play', 'discovered', 'Medium', 0)"
            )
        )
        await session.execute(
            text(
                "INSERT INTO prospects "
                "(company_name, sector, company_size, signal_type, data_source, source, "
                "company_id, opportunity_id) VALUES "
                "('Rehearsal Maintenance', 'Field Services', '11-50', "
                "'REGISTRY_FIELD', 'rehearsal', 'rehearsal', "
                "'rehearsal-company', 'rehearsal-opportunity')"
            )
        )
        prospect_id = await session.scalar(
            text("SELECT id FROM prospects WHERE company_name = 'Rehearsal Maintenance'")
        )
        await session.execute(
            text(
                "INSERT INTO evidence_signals "
                "(prospect_id, category, signal_type, label, evidence_text, "
                "source_type, confidence, strength, is_active, manually_confirmed) "
                "VALUES (:prospect, 'operations', 'OPERATIONS.MULTI_SITE', "
                "'Multi-site', 'Operates three service sites', 'official_registry', "
                "90, 80, true, false)"
            ),
            {"prospect": prospect_id},
        )
        for evidence_id in ("legacy-evidence-a", "legacy-evidence-b"):
            await session.execute(
                text(
                    "INSERT INTO evidence_items "
                    "(id, company_id, opportunity_id, code, category, evidence_text, "
                    "confidence, verification_state) VALUES "
                    "(:id, 'rehearsal-company', 'rehearsal-opportunity', "
                    "'LEGACY.DUPLICATE', 'operations', 'Duplicated legacy fact', "
                    "0.8, 'source_observed')"
                ),
                {"id": evidence_id},
            )
        await session.commit()
        print({"seeded_prospect_id": prospect_id, "revision": revision})


if __name__ == "__main__":
    asyncio.run(main())
