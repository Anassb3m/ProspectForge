#!/usr/bin/env python3
"""Read-only reconciliation for the reliability hotfix.

This script never creates identity links. The migration backfills links only
from unique statutory identifiers; unresolved rows remain visible for manual
review.
"""

from __future__ import annotations

import argparse
import asyncio
import json

from sqlalchemy import func, or_, select

from app.database import async_session_factory
from app.models import (
    Company,
    CompanyIdentifier,
    FailedWorkItem,
    IngestionRun,
    Opportunity,
    PipelineRun,
    Prospect,
    SourceCheckpoint,
    WorkItem,
)


async def reconcile() -> dict:
    async with async_session_factory() as session:
        def scalar_count(model):
            return select(func.count()).select_from(model)

        total_prospects = int(await session.scalar(scalar_count(Prospect)) or 0)
        linked_prospects = int(
            await session.scalar(
                select(func.count(Prospect.id)).where(
                    Prospect.company_id.isnot(None),
                    Prospect.opportunity_id.isnot(None),
                )
            )
            or 0
        )
        identifier_bearing_unlinked = int(
            await session.scalar(
                select(func.count(Prospect.id)).where(
                    Prospect.company_id.is_(None),
                    or_(Prospect.siren.isnot(None), Prospect.siret.isnot(None)),
                )
            )
            or 0
        )
        name_only_unlinked = int(
            await session.scalar(
                select(func.count(Prospect.id)).where(
                    Prospect.company_id.is_(None),
                    Prospect.siren.is_(None),
                    Prospect.siret.is_(None),
                )
            )
            or 0
        )
        orphan_opportunities = int(
            await session.scalar(
                select(func.count(Opportunity.id))
                .outerjoin(Company, Opportunity.company_id == Company.id)
                .where(Company.id.is_(None))
            )
            or 0
        )
        duplicate_identifiers = list(
            (
                await session.execute(
                    select(
                        CompanyIdentifier.scheme,
                        CompanyIdentifier.value_normalized,
                        func.count(CompanyIdentifier.id).label("count"),
                    )
                    .group_by(
                        CompanyIdentifier.scheme,
                        CompanyIdentifier.value_normalized,
                    )
                    .having(func.count(CompanyIdentifier.id) > 1)
                )
            ).all()
        )
        work_states = dict(
            (
                await session.execute(
                    select(WorkItem.status, func.count(WorkItem.id)).group_by(
                        WorkItem.status
                    )
                )
            ).all()
        )
        legacy_runs = int(await session.scalar(scalar_count(IngestionRun)) or 0)
        backfilled_runs = int(
            await session.scalar(
                select(func.count(PipelineRun.id)).where(
                    PipelineRun.correlation_id.like("legacy-ingestion-%")
                )
            )
            or 0
        )
        return {
            "prospects": {
                "total": total_prospects,
                "linked_by_explicit_ids": linked_prospects,
                "identifier_bearing_unlinked": identifier_bearing_unlinked,
                "name_only_unlinked_not_auto_joined": name_only_unlinked,
            },
            "canonical": {
                "companies": int(await session.scalar(scalar_count(Company)) or 0),
                "opportunities": int(
                    await session.scalar(scalar_count(Opportunity)) or 0
                ),
                "orphan_opportunities": orphan_opportunities,
                "duplicate_identifiers": [
                    {"scheme": row.scheme, "value": row.value_normalized, "count": row.count}
                    for row in duplicate_identifiers
                ],
            },
            "runs": {
                "legacy_ingestion_runs": legacy_runs,
                "legacy_runs_backfilled": backfilled_runs,
                "pipeline_runs": int(
                    await session.scalar(scalar_count(PipelineRun)) or 0
                ),
            },
            "work": {
                "states": {str(key): int(value) for key, value in work_states.items()},
                "failed_work_items": int(
                    await session.scalar(scalar_count(FailedWorkItem)) or 0
                ),
                "source_checkpoints": int(
                    await session.scalar(scalar_count(SourceCheckpoint)) or 0
                ),
            },
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fail-on-anomaly",
        action="store_true",
        help="exit non-zero for duplicate identifiers, orphan opportunities, or incomplete run backfill",
    )
    args = parser.parse_args()
    result = asyncio.run(reconcile())
    print(json.dumps(result, indent=2, sort_keys=True))
    anomalies = (
        bool(result["canonical"]["duplicate_identifiers"])
        or result["canonical"]["orphan_opportunities"] > 0
        or result["runs"]["legacy_runs_backfilled"]
        < result["runs"]["legacy_ingestion_runs"]
    )
    if args.fail_on_anomaly and anomalies:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
