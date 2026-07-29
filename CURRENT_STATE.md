# Current State — Reliability Hotfix

Updated: 2026-07-28

## Implemented architecture

- `PipelineRun` is the canonical ingestion-run ledger. The immutable request is
  committed before Celery enqueue and includes play/version, connector mode,
  limit, source partition, contact/Sirene choices, requester, correlation ID,
  timestamp, and application revision.
- PostgreSQL session advisory locks serialize each
  `play/connector/partition`. A competing run exits as `skipped_overlap`.
- Registry discovery advances a durable partition-and-row checkpoint only
  after item outcomes and failed-work records commit.
- Each source record uses a nested transaction. A bad item enters
  `failed_work_items`; it cannot roll back previously committed items.
- Raw ingestion persists identity/evidence input and creates idempotent
  `WorkItem` rows. Deep enrichment runs on the `website-evidence` queue with
  three bounded retries. Contact discovery is never run inside source
  ingestion.
- Normalized `Company`/`Opportunity` records are the canonical identity and
  opportunity records. The legacy `Prospect` compatibility row links through
  explicit `company_id` and `opportunity_id`; company names are not joins.
- Celery Beat schedules are generated only from explicit feature flags. The
  Compose scheduler profile is not started by a normal deploy.
- `/api/operations/acquisition-health` and `/operations` expose committed run,
  checkpoint, work, queue, error, source-capability, and automation state.

## Active source and play

- Active mutation play: `FIELD_OPERATIONS_FR_V2`.
- Enabled manual connectors: France registry and DECP.
- Companies House sourcing: disabled until pagination, checkpoints, canonical
  identity, and production validation exist.
- BODACC and OCDS: planned, not executable and never reported healthy.
- Sirene: `misconfigured` without `INSEE_API_KEY`; otherwise still requires a
  live health check.

## Automation state

All schedules are intentionally disabled by default:

```text
ENABLE_SCHEDULER=false
ENABLE_NIGHTLY_INGESTION=false
ENABLE_NIGHTLY_CONTACT_DISCOVERY=false
ENABLE_SCORE_RECONCILIATION=false
ENABLE_RETENTION_SWEEP=false
OUTREACH_ENABLED=false
```

Automatic cold outreach is unsupported and production validation rejects
`OUTREACH_ENABLED=true`.

## Migration state

- Alembic head: `pfrel01_20260728`.
- PostgreSQL 16 clean upgrade, downgrade/re-upgrade, identifier-only link
  backfill, and legacy run backfill were rehearsed.
- Reconciliation fixture result: 1/1 prospect linked by SIRET, 1/1 legacy run
  backfilled, zero duplicate identifiers, zero orphan opportunities.

## Safe production state

This is a deployable, automation-disabled reliability hotfix after a verified
backup. It is safe for a small controlled registry run and operator review. It
is not approved for unattended scale or cold outreach.

## Known limitations

- The compatibility `Prospect` row still duplicates fields held in canonical
  models. Explicit foreign keys remove ambiguous joins, but the remaining
  projection/write consolidation is not complete.
- DECP remains an idempotent rolling-window replay, not a progressive
  high-water checkpoint connector.
- Raw source payload storage and raw-persisted counts are not activated;
  `raw_persisted` therefore reports zero instead of a synthetic value.
- V4 scoring is still incomplete and is not certified for automated contact
  readiness. Score reconciliation and nightly contact discovery remain off.
- Work-item recovery is durable, but there is no operator retry endpoint yet;
  pending items are redispatched by a controlled run or manual task dispatch.
- Worker heartbeats are not canonical; operations reports worker state as
  `unknown`, never healthy.
- Live-source throughput and quality were not claimed from synthetic tests.
- The current local interpreter is Python 3.14.5; the release target remains
  Python 3.12 and needs a final 3.12 certification run.
