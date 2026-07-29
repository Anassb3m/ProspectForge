# Reliability Architecture

## Acquisition sequence

```text
authenticated request / scheduler
  -> validate explicit play + connector + limit
  -> commit immutable PipelineRun(status=queued)
  -> enqueue source-ingestion task
  -> acquire PostgreSQL advisory lock(play/connector/partition)
  -> read committed SourceCheckpoint
  -> retrieve bounded source slice
  -> per item SAVEPOINT
       -> statutory identity upsert
       -> canonical Company/Opportunity link
       -> evidence projection
       -> idempotent enrichment WorkItem
     on failure -> FailedWorkItem
  -> commit next checkpoint
  -> dispatch pending work to website-evidence queue
  -> commit truthful run totals/status
```

The source task never performs contact discovery or outreach. Enrichment work
has its own status, lease, retry count, idempotency key, and dead-letter
record. Contact research has separate score, suppression, domain, freshness,
and concurrency gates.

## Canonical ownership

- `CompanyIdentifier` owns statutory identity.
- `Company` owns canonical organization identity.
- `Opportunity` owns play-specific commercial state.
- `PipelineRun`, `SourceCheckpoint`, `WorkItem`, and `FailedWorkItem` own
  operational history.
- `Prospect` is a temporary compatibility projection linked by foreign keys.

Display names and inferred domains are never identity joins.

## Recovery properties

- Advisory locks are connection-scoped and cannot leave an expired lease.
- Checkpoints move after committed outcomes; a crash replays the prior slice.
- Prospect identity and work idempotency turn replay into update/no-op.
- A failed record rolls back its savepoint only.
- Broker failure leaves work pending and visible.
- Run failure is persisted in a separate session and re-raised.
