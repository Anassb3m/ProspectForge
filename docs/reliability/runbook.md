# Reliability Runbook

## Inspect health

```bash
./scripts/diagnose_pipeline.sh
curl -fsS http://127.0.0.1:18081/ready
docker compose ps
docker compose logs --tail=200 app worker-ingestion worker-evidence redis db
```

Sign in and inspect `/operations`. The JSON endpoint
`/api/operations/acquisition-health` is authenticated.

Verify every execution queue, especially for operator actions:

```bash
docker compose ps app worker-ingestion worker-evidence worker-contact redis db
docker compose logs --tail=200 worker-evidence worker-contact
```

`worker-evidence` handles website evidence. `worker-contact` handles eligible
contact research. The health endpoint reports all five execution queues
individually. A healthy web process without these workers can render pages but
cannot complete those stages; the durable queued/pending state is the source
of truth.

## Operator evidence and contact actions

- **Deep enrich** commits a canonical evidence `PipelineRun` and idempotent
  `WorkItem`, then publishes to `website-evidence`.
- **Queue contact discovery** is available from prospect detail only after
  the readiness checks pass. It commits a `ContactDiscoveryRun` and publishes
  to `buyer-contact`.
- Repeated clicks reuse active contact work. Evidence duplicate requests are
  recorded as skipped duplicates.
- `enqueue_failed` means the request is durable but the broker did not accept
  it. Restore Redis/worker health and retry; do not mark it completed manually.
- Reacher being reachable only adds deliverability evidence. It never proves
  the person's or company's identity.

## Run one controlled source partition

```bash
docker compose exec -T app python -m app.jobs.ingestion \
  --play-code FIELD_OPERATIONS_FR_V2 \
  --mode registry --max-companies 500 --skip-sirene
```

Remove `--skip-sirene` only after `INSEE_API_KEY` is configured and health is
verified. `full` splits the requested limit across DECP and registry.

For a disposable persisted acceptance of both enabled public sources:

```bash
LIVE_REGISTRY_LIMIT=25 LIVE_DECP_LIMIT=25 \
  PYTHON_BIN=.venv/bin/python bash scripts/live-source-acceptance.sh
```

The script creates an isolated database, applies migrations, executes both
sources, reports checkpoint/raw/canonical/work and anomaly counts, and removes
the database. It does not enable schedules.

For a redacted live public-contact diagnostic:

```bash
.venv/bin/python scripts/live_contact_yield_smoke.py \
  --company "Example Company" --website https://example.org/
```

Only aggregate contact/evidence counts and rejection categories are printed;
contact values are not logged or persisted by this diagnostic. A 403, missing
peer address, or blocked destination is a truthful failed/rejected page, not a
healthy result.

## Pause and resume

To pause scheduling:

```bash
# set in .env
ENABLE_SCHEDULER=false
ENABLE_NIGHTLY_INGESTION=false
docker compose --profile scheduler stop celery-beat
```

Running work is not killed. Wait for it or inspect the advisory lock and run
heartbeat. Resume only after setting reviewed flags and starting the scheduler
profile.

## Registry checkpoint handling

Inspect the cursor without changing it:

```bash
./scripts/backup-host.sh
docker compose exec -T db psql -U prospectforge -d prospectforge \
  -c "SELECT * FROM source_checkpoints WHERE source_name='registry:FIELD_OPERATIONS_FR_V2:all';"
```

Do not delete or manually rewrite the row during normal operation. The cursor
includes a discovery-plan fingerprint, partition, page, and row offset. A
legacy/incompatible cursor is automatically rebased and its replay is safe by
statutory identity, payload hash, and work idempotency.

## Retry and recovery

- `pending`: durable, not accepted by the broker; redispatch manually after
  Redis is healthy.
- `enqueued`: accepted by the broker.
- `running`: check `lock_lease_until` and worker logs.
- `failed`: retries exhausted; inspect the matching `failed_work_items` row.

The authenticated retry endpoint accepts retryable Celery failures and
registry/DECP raw normalization failures. Raw retries read the persisted
`SourceRecord`; they do not rediscover the source. Broker acceptance increments
the retry audit but does not resolve the failed row. Resolution occurs only
after normalization commits.

Use **Recover stale work** in `/operations` to enqueue locked recovery. It
reclaims expired supported work within its retry budget and dead-letters
exhausted/unsupported work. The API response is `accepted`, not `completed`.
Do not edit statuses or leases blindly.

## Reconcile

```bash
docker compose exec -T app python scripts/reconcile_reliability.py
docker compose exec -T app python scripts/reconcile_reliability.py --fail-on-anomaly
```

The gate fails for duplicate statutory identifiers, orphan opportunities or
evidence, duplicate active evidence fingerprints, mappable unmapped legacy
evidence, or incomplete legacy-run backfill. Name-only unlinked rows are
reported but intentionally not auto-joined.

## Rehearse a production-copy migration

Create and verify a backup, anonymize the copy under the approved operating
procedure, then run:

```bash
PYTHON_BIN=.venv/bin/python bash scripts/rehearse-production-migration.sh \
  /path/to/anonymized-production.sql.gz
```

The rehearsal uses and removes only a uniquely named disposable database. The
no-argument deterministic fixture is useful for CI/mechanics, but does not
satisfy the production-copy gate. Never point the script or Alembic directly
at the live production database for rehearsal.

## Enable scheduler

Prerequisites: controlled live-source acceptance, zero reconciliation
anomalies, current backup, Redis and workers healthy.

```bash
# .env
ENABLE_SCHEDULER=true
ENABLE_NIGHTLY_INGESTION=true
ACTIVE_MARKET_PLAY=FIELD_OPERATIONS_FR_V2
NIGHTLY_INGESTION_LIMIT=500

docker compose --profile scheduler up -d celery-beat
```

Keep nightly contact discovery, score reconciliation, retention, and outreach
off unless each prerequisite is separately accepted.

## Enable Reacher

Reacher is technical verification, not identity proof:

```bash
# .env
REACHER_ENABLED=true
docker compose --profile reacher up -d reacher
```

Do not enable contact automation merely because Reacher is reachable.

## Rollback

```bash
./scripts/backup-host.sh
./scripts/rollback.sh
```

Application rollback preserves the additive raw-stage schema. A schema
downgrade refuses once new raw rows exist. For an incompatible rollback,
restore the pre-deploy database backup instead of deleting or resetting data.

## Alert meanings

- `enqueue_failed` / `QUEUE_UNAVAILABLE`: run request persisted, broker did not
  accept it.
- `skipped_overlap`: another run owns the exact source partition.
- `completed_with_errors`: source run completed; one or more items are in the
  failed-work queue.
- stale active run: heartbeat older than the configured lock timeout.
- stale work item: running lease expired or broker-accepted work exceeded
  `WORK_STALE_AFTER_SECONDS` without starting.
- worker `unknown`: no canonical heartbeat exists; never interpret as healthy.
- worker `degraded`: no fresh `source-ingestion` queue heartbeat exists.
- repeated HTML 403 on valid controls: verify the `pf_csrf` cookie and current
  `/static/js/app.js`; do not disable CSRF. A 502 should be traced through Caddy
  and app logs, but enrichment/contact network work must never run in the web
  request.
