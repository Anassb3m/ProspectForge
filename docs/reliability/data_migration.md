# Data Migration and Reconciliation

The current single head is `pfscale03_20260731`. It follows the reliability,
canonical-nullability, and worker-heartbeat revisions in one linear chain.

It adds:

- explicit `prospects.company_id` and `prospects.opportunity_id` links;
- immutable request, checkpoint, counter, correlation, heartbeat, revision,
  and error fields on `pipeline_runs`;
- work-item idempotency keys;
- failed-work source, record, category, and retryability fields.
- pipeline-owned hashed raw records with processing outcome fields;
- failed-work resolution/retry audit fields.
- canonical evidence fingerprints/provenance and explicit legacy projection links;
- company identity-review and opportunity readiness states;
- score input revisions, profile/calculator versions, evidence references, and
  readiness snapshots.

## Backfill rules

1. Link by unique `FR_SIRET`.
2. If still unlinked, link by unique `FR_SIREN`.
3. Link an opportunity only when exactly one opportunity belongs to the
   resolved company and matching market play.
4. Never link by company name or inferred domain.
5. Copy every legacy `ingestion_runs` row into `pipeline_runs`; retain the
   legacy row.
6. Map legacy evidence only through an explicit prospect opportunity/company
   link. Insert a canonical item when absent and link the legacy projection.
7. Retain duplicate legacy canonical evidence, mark all but one inactive, and
   enforce uniqueness only for active semantic fingerprints going forward.

Unresolved rows are preserved for review. No prospect, company, evidence,
contact, source, or run data is deleted.

## Rehearsal result

The PostgreSQL 16 canonical backfill rehearsal produced:

```text
companies/opportunities/prospects: 1/1/1
legacy evidence signals mapped: 1/1
canonical evidence items retained: 3
active canonical evidence items: 2
legacy duplicates retained inactive: 1
mappable legacy signals unmapped: 0
duplicate active fingerprints: 0
orphan opportunities/evidence: 0/0
```

Run the same read-only reconciliation on a production copy before deploy.

## Rollback

Application rollback keeps the additive schema. The canonical metadata
revision has downgrade operations for empty/rehearsal use; production
application rollback should not downgrade the database. Once pipeline-owned
raw rows exist, the preceding raw-stage downgrade refuses rather than deleting them.
Restore the verified pre-deploy backup only when a schema rollback is truly
required; never reset production data to force a downgrade.
