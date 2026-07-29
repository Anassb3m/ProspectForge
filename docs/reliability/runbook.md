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

## Run one controlled source partition

```bash
docker compose exec -T app python -m app.jobs.ingestion \
  --play-code FIELD_OPERATIONS_FR_V2 \
  --mode registry --max-companies 25 --skip-sirene
```

Remove `--skip-sirene` only after `INSEE_API_KEY` is configured and health is
verified. `full` splits the requested limit across DECP and registry.

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

## Reset a registry checkpoint

Checkpoint reset causes replay. Back up first and record the old value:

```bash
./scripts/backup-host.sh
docker compose exec -T db psql -U prospectforge -d prospectforge \
  -c "SELECT * FROM source_checkpoints WHERE source_name='registry:FIELD_OPERATIONS_FR_V2:all';"
```

Do not delete the row. In a maintenance window, update
`high_water_mark` to `{"partition": 0, "offset": 0}` only after confirming
identifier and work-item uniqueness and recording the operator decision.

## Retry and recovery

- `pending`: durable, not accepted by the broker; redispatch manually after
  Redis is healthy.
- `enqueued`: accepted by the broker.
- `running`: check `lock_lease_until` and worker logs.
- `failed`: retries exhausted; inspect the matching `failed_work_items` row.

There is no authenticated retry endpoint in this phase. Do not edit status
blindly. Re-run the exact task only after classifying the failure and retaining
the failed-work record.

## Reconcile

```bash
docker compose exec -T app python scripts/reconcile_reliability.py
docker compose exec -T app python scripts/reconcile_reliability.py --fail-on-anomaly
```

The gate fails for duplicate statutory identifiers, orphan opportunities, or
an incomplete legacy-run backfill. Name-only unlinked rows are reported but
are intentionally not auto-joined.

## Enable scheduler

Prerequisites: controlled live-source acceptance, zero reconciliation
anomalies, current backup, Redis and workers healthy.

```bash
# .env
ENABLE_SCHEDULER=true
ENABLE_NIGHTLY_INGESTION=true
ACTIVE_MARKET_PLAY=FIELD_OPERATIONS_FR_V2
NIGHTLY_INGESTION_LIMIT=100

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

The migration downgrade preserves historical pipeline rows but removes new
columns. For an incompatible rollback, restore the pre-deploy database backup
instead of deleting or resetting production data.

## Alert meanings

- `enqueue_failed` / `QUEUE_UNAVAILABLE`: run request persisted, broker did not
  accept it.
- `skipped_overlap`: another run owns the exact source partition.
- `completed_with_errors`: source run completed; one or more items are in the
  failed-work queue.
- stale active run: heartbeat older than the configured lock timeout.
- worker `unknown`: no canonical heartbeat exists; never interpret as healthy.
