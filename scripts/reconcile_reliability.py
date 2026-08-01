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
    ContactPoint,
    EvidenceItem,
    EvidenceSignal,
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
        duplicate_evidence = list(
            (
                await session.execute(
                    select(
                        EvidenceItem.opportunity_id,
                        EvidenceItem.fingerprint,
                        func.count(EvidenceItem.id).label("count"),
                    )
                    .where(
                        EvidenceItem.is_active.is_(True),
                        EvidenceItem.fingerprint.is_not(None),
                    )
                    .group_by(
                        EvidenceItem.opportunity_id, EvidenceItem.fingerprint
                    )
                    .having(func.count(EvidenceItem.id) > 1)
                )
            ).all()
        )
        mapped_legacy_evidence = int(
            await session.scalar(
                select(func.count(EvidenceSignal.id)).where(
                    EvidenceSignal.canonical_evidence_id.is_not(None)
                )
            )
            or 0
        )
        mappable_unmapped_evidence = int(
            await session.scalar(
                select(func.count(EvidenceSignal.id))
                .join(Prospect, EvidenceSignal.prospect_id == Prospect.id)
                .where(
                    Prospect.company_id.is_not(None),
                    Prospect.opportunity_id.is_not(None),
                    EvidenceSignal.canonical_evidence_id.is_(None),
                )
            )
            or 0
        )
        orphan_evidence = int(
            await session.scalar(
                select(func.count(EvidenceItem.id))
                .outerjoin(Company, EvidenceItem.company_id == Company.id)
                .where(Company.id.is_(None))
            )
            or 0
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
                "identity_manual_review": int(
                    await session.scalar(
                        select(func.count(Company.id)).where(
                            Company.identity_review_state != "clear"
                        )
                    )
                    or 0
                ),
            },
            "evidence": {
                "legacy_signals": int(
                    await session.scalar(scalar_count(EvidenceSignal)) or 0
                ),
                "legacy_signals_mapped": mapped_legacy_evidence,
                "mappable_legacy_signals_unmapped": mappable_unmapped_evidence,
                "canonical_items": int(
                    await session.scalar(scalar_count(EvidenceItem)) or 0
                ),
                "active_canonical_items": int(
                    await session.scalar(
                        select(func.count(EvidenceItem.id)).where(
                            EvidenceItem.is_active.is_(True)
                        )
                    )
                    or 0
                ),
                "legacy_duplicates_retained_inactive": int(
                    await session.scalar(
                        select(func.count(EvidenceItem.id)).where(
                            EvidenceItem.contradiction_status == "duplicate_legacy"
                        )
                    )
                    or 0
                ),
                "orphan_items": orphan_evidence,
                "duplicate_active_fingerprints": [
                    {
                        "opportunity_id": row.opportunity_id,
                        "fingerprint": row.fingerprint,
                        "count": row.count,
                    }
                    for row in duplicate_evidence
                ],
            },
            "contacts": {
                "legacy_contact_points_retained": int(
                    await session.scalar(scalar_count(ContactPoint)) or 0
                ),
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
        or bool(result["evidence"]["duplicate_active_fingerprints"])
        or result["evidence"]["orphan_items"] > 0
        or result["evidence"]["mappable_legacy_signals_unmapped"] > 0
        or result["runs"]["legacy_runs_backfilled"]
        < result["runs"]["legacy_ingestion_runs"]
    )
    if args.fail_on_anomaly and anomalies:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
