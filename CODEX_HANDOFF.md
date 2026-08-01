# Codex Handoff — Reliability and Scale Rebuild

Updated: 2026-07-31

## Delivered state

The zero-output acquisition path is repaired. Registry discovery follows the
active V2 NAF plan and upstream pagination; DECP persists awards before
aggregation. Both connectors use progressive committed checkpoints, immutable
raw rows, replay-safe identity upserts, isolated item failures, durable
downstream work, bounded retries, and queue-specific worker health.

Recovery is operational: authenticated raw retries rebuild from committed
source rows, stale leases are reclaimed under row locks, and exhausted work is
dead-lettered. Broker acceptance is never presented as completed work.

Canonical `Company`/`Opportunity` identity uses SIREN/SIRET only. Canonical
`EvidenceItem` rows own evidence truth and legacy signals link as compatibility
projections. The French field-operations scoring profile and 13 readiness gates
are implemented with input revisions, evidence references, reason codes,
penalties, and explicit readiness states.

Alembic has one head: `pfscale03_20260731`.

## Verification state

- Live registry source population: 7,108 across the seven active NAF segments.
- Live connector sample: 250 records, 250 unique SIRENs, 250 raw envelopes,
  checkpoint advanced to page 11.
- Deterministic scale proof: two disjoint 1,000-record registry batches.
- DECP proof: six historical awards in three batches, then two incremental
  awards without skip; raw replay remained idempotent.
- Canonical backfill rehearsal: one legacy signal mapped; three canonical rows
  retained; one deliberate duplicate inactive; zero orphans, unmapped mappable
  evidence, or duplicate active fingerprints.
- Final release gate: clean `pfscale03_20260731` migration, zero reconciliation
  anomalies, zero npm vulnerabilities, all static/Compose/Caddy checks, and
  `154 passed in 85.25s`; exit code `0`.

## Required pre-deploy commands

```bash
PYTHON_BIN=.venv/bin/python ./scripts/release-gate.sh
./scripts/backup-host.sh
docker compose run --rm --no-deps app alembic upgrade head
docker compose exec -T app python scripts/reconcile_reliability.py --fail-on-anomaly
./scripts/diagnose_pipeline.sh
```

Production deployment remains:

```bash
./scripts/deploy.sh
curl -fsS http://127.0.0.1:18081/ready
docker compose exec -T app alembic current
docker compose exec -T app python scripts/reconcile_reliability.py --fail-on-anomaly
```

## Controlled manual activation

Start with automation still off and run one bounded source stage:

```bash
docker compose exec -T app python -m app.jobs.ingestion \
  --play-code FIELD_OPERATIONS_FR_V2 --mode registry \
  --max-companies 500 --skip-sirene
```

Inspect `/operations`, acquisition health, raw outcomes, checkpoint movement,
duplicate/error rates, and canonical reconciliation. Repeat 500–2,000 record
runs to build thousands; do not raise the cap or reset the checkpoint.

## Automation state

Intentionally disabled until explicit production acceptance:

```text
ENABLE_SCHEDULER=false
ENABLE_NIGHTLY_INGESTION=false
ENABLE_NIGHTLY_CONTACT_DISCOVERY=false
ENABLE_SCORE_RECONCILIATION=false
ENABLE_RETENTION_SWEEP=false
OUTREACH_ENABLED=false
```

Reacher may be enabled only as technical verification after review; it does
not prove identity. Automatic cold outreach remains unsupported and production
validation rejects it.

## Rollback

```bash
./scripts/rollback.sh
```

This restores the preserved application image after taking another backup.
Keep the additive database schema. If an incompatible schema rollback is truly
required, restore the verified pre-deploy backup; never delete pipeline raw
rows, checkpoints, or production data to force a downgrade.

## Remaining risks

- The legacy `Prospect` and contact tables still project mutable fields for old
  screens. Identity, opportunity, evidence, and score ownership are canonical,
  but final compatibility-write retirement still requires UI/contact migration.
- The scoring profile needs calibration on reviewed production examples before
  scheduled contact research is enabled.
- Persisted live validation has not been run against a production-copy database.
- Optional Companies House, BODACC, and OCDS connectors remain intentionally
  disabled until each has real pagination, raw persistence, checkpoints, rate
  budgets, health checks, and tests.
- The final release gate ran on Python 3.14.5. Production targets Python 3.12
  and still needs that runtime certification.

## Start here

Read `CURRENT_STATE.md`, `NEXT_ACTIONS.md`, `DECISION_LOG.md`, `TEST_LOG.md`,
`docs/reliability/runbook.md`, `docs/reliability/data_migration.md`, and
`acceptance/baseline-defect-register.md` before activation.
