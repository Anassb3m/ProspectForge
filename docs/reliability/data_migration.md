# Data Migration and Reconciliation

Revision `pfrel01_20260728` is additive.

It adds:

- explicit `prospects.company_id` and `prospects.opportunity_id` links;
- immutable request, checkpoint, counter, correlation, heartbeat, revision,
  and error fields on `pipeline_runs`;
- work-item idempotency keys;
- failed-work source, record, category, and retryability fields.

## Backfill rules

1. Link by unique `FR_SIRET`.
2. If still unlinked, link by unique `FR_SIREN`.
3. Link an opportunity only when exactly one opportunity belongs to the
   resolved company and matching market play.
4. Never link by company name or inferred domain.
5. Copy every legacy `ingestion_runs` row into `pipeline_runs`; retain the
   legacy row.

Unresolved rows are preserved for review. No prospect, company, evidence,
contact, source, or run data is deleted.

## Rehearsal result

The PostgreSQL 16 fixture downgrade/upgrade produced:

```text
prospects total: 1
linked by explicit IDs: 1
identifier-bearing unlinked: 0
legacy runs: 1
legacy runs backfilled: 1
duplicate identifiers: 0
orphan opportunities: 0
```

Run the same read-only reconciliation on a production copy before deploy.

## Rollback

`alembic downgrade 1e81eb7d5107` removes additive columns and indexes. It does
not delete historical `pipeline_runs` rows. Because those rows lose their new
fields during downgrade, the preferred production recovery is the pre-deploy
backup when rolling back the application image and schema together.
