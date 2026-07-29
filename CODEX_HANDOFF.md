# Codex Handoff — Reliability Hotfix

Updated: 2026-07-28

## Delivered patch

The deployable phase covers truthful orchestration, durable run requests,
overlap locking, per-item failure isolation, progressive registry checkpoints,
separate idempotent enrichment work, explicit canonical identity links,
feature-gated schedules, operations visibility, PostgreSQL/Redis tests, and
safe reconciliation.

Alembic head is `pfrel01_20260728`.

## Start here

Read:

1. `CURRENT_STATE.md`
2. `NEXT_ACTIONS.md`
3. `DECISION_LOG.md`
4. `TEST_LOG.md`
5. `docs/reliability/architecture.md`
6. `docs/reliability/runbook.md`
7. `acceptance/baseline-defect-register.md`

Core runtime files are `app/jobs/ingestion.py`,
`app/services/pipeline_runs.py`, `app/services/run_lock.py`,
`app/discovery/annuaire.py`, and `app/workers/tasks.py`.

## Verification

```bash
PYTHON_BIN=.venv/bin/python ./scripts/release-gate.sh
DEBUG=false ENVIRONMENT=production \
  docker compose exec -T app python scripts/reconcile_reliability.py --fail-on-anomaly
./scripts/diagnose_pipeline.sh
```

The final workspace test was `130 passed in 56.90s` on PostgreSQL 16. The full
release gate passed before the final lock regression, and the focused
reliability suite passed afterward (`11 passed in 14.73s`). Migration
rehearsal linked 1/1 identifier-bearing prospect and backfilled 1/1 legacy run
with no duplicates or orphans.

## Deployment state

No production deployment or scheduler activation was performed. Normal
`./scripts/deploy.sh` does not start Celery Beat because it is in the
`scheduler` profile. All automation and outreach flags remain false.

## Controlled activation

After backup, migration, reconciliation, and health checks:

```bash
docker compose exec -T app python -m app.jobs.ingestion \
  --play-code FIELD_OPERATIONS_FR_V2 --mode registry \
  --max-companies 25 --skip-sirene
```

Inspect `/operations`, the authenticated acquisition-health endpoint, and the
reconciliation output. Do not enable the scheduler until live-source quality
is accepted. Do not enable contact automation until scoring reconciliation is
implemented and certified.

## Highest risks for the next engineer

- Finish removing mutable duplicated fields from the legacy `Prospect` row.
- Add raw DECP records and a progressive DECP cursor.
- Replace placeholder V4 scoring with evidence-bound, explainable snapshots
  and hard readiness gates.
- Add persistent worker heartbeats and authenticated recovery controls.
- Certify Python 3.12 and rehearse against an anonymized production copy.

Do not remove compatibility fields or constraints until reconciliation shows
zero unresolved identifier-bearing rows and rollback has been rehearsed.
