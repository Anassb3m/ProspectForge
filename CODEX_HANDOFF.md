# Codex Handoff — Reliability and Scale Rebuild

Updated: 2026-08-01

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

The operator-facing zero-output/502 paths are also repaired. Website evidence
and contact discovery no longer crawl, resolve DNS, harvest, or call Reacher in
an HTTP request. Evidence commits a canonical `PipelineRun` plus idempotent
`WorkItem`; contact discovery commits a deduplicated `ContactDiscoveryRun` and
runs on `buyer-contact`. Enqueue, retry, terminal failure, and completion states
are persisted. All primary authenticated pages render in regression coverage;
broken destinations, canonical-ID links, Kanban, inbox, campaigns, drafts, and
native-form CSRF are backed by real routes/state changes or explicitly disabled.

## Verification state

- Live registry source population: 7,108 across the seven active NAF segments.
- Live connector sample: 250 records, 250 unique SIRENs, 250 raw envelopes,
  checkpoint advanced to page 11.
- Persisted live-source acceptance: registry and DECP each committed 25 raw
  rows through canonical company/opportunity/evidence and downstream work with
  zero duplicate, invalid, failed, or reconciliation-anomaly counts. A clean
  2+2 rerun reconfirmed both checkpoint transitions.
- Deterministic scale proof: two disjoint 1,000-record registry batches.
- DECP proof: six historical awards in three batches, then two incremental
  awards without skip; raw replay remained idempotent.
- Canonical backfill rehearsal: one legacy signal mapped; three canonical rows
  retained; one deliberate duplicate inactive; zero orphans, unmapped mappable
  evidence, or duplicate active fingerprints.
- Production-shaped migration rehearsal: 1,001 linked companies,
  opportunities, and prospects reached `pfscale03_20260731` with zero identity,
  orphan, projection, or duplicate-active-fingerprint anomalies. No actual
  production dump was available, so the data-specific production-copy gate is
  still open.
- Live public-contact proof: one official site produced four published generic
  contacts and eight evidence items; a second produced one person, five contact
  points including two strong published-personal matches, and six evidence
  items. The diagnostic redacts values and persists nothing. A blocking site
  was reported as HTTP 403, not healthy.
- Operator reliability proof: 62 focused PostgreSQL tests cover committed-before-
  dispatch contact/evidence work, replay/deduplication, broker failure truth,
  12 primary pages, cookie-session CSRF, and non-empty UI mutations.
- Final host release gate: clean `pfscale03_20260731` migration, zero
  reconciliation anomalies, zero npm vulnerabilities, all
  static/Compose/Caddy checks, and `166 passed in 133.53s`; exit code `0`.
- Production runtime certification: Python 3.12.13 container completed the
  entire suite with `166 passed, 1 warning in 108.33s`; the disposable
  production HTTPS/migration/backup-integrity smoke passed.

## Files in the 2026-08-01 patch

- Durable execution: `app/contact_intelligence/crawler.py`,
  `app/contact_intelligence/service.py`,
  `app/services/evidence_queue.py`, `app/workers/tasks.py`,
  `app/routers/contact_intelligence.py`, `app/routers/sourcing.py`.
- Routes/state/metrics: `app/routers/dashboard.py`, `app/routers/prospects.py`,
  `app/routers/inbox.py`, `app/routers/campaigns.py`,
  `app/routers/operations.py`, `app/services/__init__.py`, `app/schemas.py`.
- Model/runtime security: `app/models.py`, `app/security.py`,
  `app/routers/auth.py`, `app/static/js/app.js`, `docker-compose.yml`.
- UI: `app/templates/prospect_detail.html`, `sourcing.html`, `queue.html`,
  `follow_ups.html`, `dashboard.html`, `inbox.html`,
  `campaigns/detail.html`, `campaigns/drafts.html`, `operations/index.html`,
  `partials/sourcing_row.html`, and `partials/kanban_board.html`.
- Regression tests: `tests/test_ui_reliability.py`,
  `tests/test_contact_intelligence.py`, `tests/test_reliability_hotfix.py`.
- Acceptance/rehearsal tooling: `scripts/rehearse-production-migration.sh`,
  `scripts/verify-production-shaped-migration.py`,
  `scripts/seed_production_shape.py`,
  `scripts/seed_canonical_backfill_rehearsal.py`,
  `scripts/live-source-acceptance.sh`, and
  `scripts/live_contact_yield_smoke.py`.
- Operational truth: `CURRENT_STATE.md`, `NEXT_ACTIONS.md`, `TEST_LOG.md`,
  `DECISION_LOG.md`, `acceptance/baseline-defect-register.md`, `DEPLOY.md`,
  and the reliability architecture/runbook/metrics documents.

No schema revision was required for this patch. The ORM relationship is over
existing foreign keys and the durable ledgers already exist.

## Required pre-deploy commands

```bash
PYTHON_BIN=.venv/bin/python ./scripts/release-gate.sh
./scripts/backup-host.sh
PYTHON_BIN=.venv/bin/python bash scripts/rehearse-production-migration.sh \
  /path/to/anonymized-production.sql.gz
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
docker compose ps worker-ingestion worker-evidence worker-contact redis
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

After evidence enrichment and readiness review, queue contact discovery from a
prospect page. Confirm the durable contact run on the page/operations screen and
inspect `worker-contact`; do not combine it with raw ingestion. Optional
Reacher verification requires approved credentials and remains technical
deliverability evidence only.

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
- The deterministic production-shaped migration passes, but an actual
  production backup/copy was not available. Deployment remains gated on the
  supplied-dump rehearsal command above.
- Public website contact yield is live-validated. Optional INSEE/Hunter/Reacher/
  harvester behavior and provider latency are not validated because approved
  credentials/services are not configured; nightly contact discovery remains
  off.
- Optional Companies House, BODACC, and OCDS connectors remain intentionally
  disabled until each has real pagination, raw persistence, checkpoints, rate
  budgets, health checks, and tests.

## Start here

Read `CURRENT_STATE.md`, `NEXT_ACTIONS.md`, `DECISION_LOG.md`, `TEST_LOG.md`,
`docs/reliability/runbook.md`, `docs/reliability/data_migration.md`, and
`acceptance/baseline-defect-register.md` before activation.
