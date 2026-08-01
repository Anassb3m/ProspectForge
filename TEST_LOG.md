# Test Log

Date: 2026-07-28

## Baseline

- `.venv/bin/python --version` → `Python 3.14.5`.
- `.venv/bin/python -m compileall -q app tests` → pass.
- `.venv/bin/python -m ruff check app tests` → pass.
- `.venv/bin/python -m pytest -q` with the original in-memory SQLite fixture
  hung during the first async fixture. A direct `aiosqlite` schema creation
  reproduced the hang on Python 3.14.5.
- `.venv/bin/python -m pytest -q tests/test_config.py tests/test_scoring_hard_gates.py tests/test_companies_house.py`
  → `8 passed in 0.09s`.

## Reliability patch

- `docker compose --profile test up -d test-db test-redis` → PostgreSQL 16 and
  Redis 7 started on loopback.
- Clean migration:

  ```bash
  DEBUG=false ENVIRONMENT=development \
  DATABASE_URL=postgresql+asyncpg://prospectforge_test:test-only-password@127.0.0.1:55439/prospectforge_test \
  .venv/bin/alembic upgrade head
  ```

  Result: all revisions applied; `pfrel01_20260728 (head)`.

- Migration rollback/backfill rehearsal:

  ```bash
  .venv/bin/alembic downgrade 1e81eb7d5107
  # inserted one SIRET-linked compatibility/canonical fixture and one legacy run
  .venv/bin/alembic upgrade head
  .venv/bin/python scripts/reconcile_reliability.py --fail-on-anomaly
  ```

  Result: explicit company/opportunity link matched expected UUIDs; legacy run
  projected `created=2`, `updated=1`; 1/1 prospect linked, 1/1 legacy run
  backfilled, 0 duplicate identifiers, 0 orphan opportunities.

- New reliability tests initially found two defects: contact-stage error text
  mismatch and an expired ORM run ID after rollback. Both were fixed.
- First full PostgreSQL suite found four existing UUID/integer failures hidden
  by SQLite. Root cause was a company-name compatibility join and canonical
  opportunity UUIDs being sent to legacy integer tables. Explicit identity
  links fixed all four.
- Final commands:

  ```bash
  .venv/bin/python -m ruff check app tests scripts/reconcile_reliability.py
  .venv/bin/python -m compileall -q app tests alembic scripts/reconcile_reliability.py
  TEST_DATABASE_URL=postgresql+asyncpg://prospectforge_test:test-only-password@127.0.0.1:55439/prospectforge_test \
  TEST_REDIS_URL=redis://127.0.0.1:56380/0 \
  .venv/bin/python -m pytest -q
  ```

  Results before the final option-integrity test: Ruff pass; compile pass;
  `127 passed in 63.73s`.

- Final complete suite after adding worker argument propagation:

  ```bash
  TEST_DATABASE_URL=postgresql+asyncpg://prospectforge_test:test-only-password@127.0.0.1:55439/prospectforge_test \
  TEST_REDIS_URL=redis://127.0.0.1:56380/0 \
  .venv/bin/python -m pytest -q
  ```

  Result: `128 passed in 68.25s`.

- Complete release gate:

  ```bash
  PYTHON_BIN=.venv/bin/python bash scripts/release-gate.sh
  ```

  Result: npm audit `0 vulnerabilities`; assets built; Ruff passed; clean
  unique PostgreSQL database migrated to `pfrel01_20260728`; reconciliation
  passed; `128 passed in 58.52s`; shell, Compose, and all three Caddy
  configurations passed; final output `Release gate passed`.

- After adding the full-versus-single-connector lock-set regression:

  ```bash
  TEST_DATABASE_URL=postgresql+asyncpg://prospectforge_test:test-only-password@127.0.0.1:55439/prospectforge_test \
  TEST_REDIS_URL=redis://127.0.0.1:56380/0 \
  .venv/bin/python -m pytest -q
  ```

  Result: `129 passed in 43.85s`. The focused reliability file reported
  `10 passed in 11.28s`.

- Final suite with authenticated acquisition-health coverage:

  ```bash
  TEST_DATABASE_URL=postgresql+asyncpg://prospectforge_test:test-only-password@127.0.0.1:55439/prospectforge_test \
  TEST_REDIS_URL=redis://127.0.0.1:56380/0 \
  .venv/bin/python -m pytest -q
  ```

  Result: `130 passed in 56.90s`; focused reliability tests:
  `11 passed in 14.73s`.

## Environmental limitation

Python 3.12 was not installed in this workspace. PostgreSQL 16 is the certified
test database for this patch; Python 3.12 release certification remains
required before production activation.
## Baseline Continuation Verification (Phase 0)

- **Date:** 2026-07-29
- **Python Version:** 3.12.13
- **Command:** `PYTHON_BIN=.venv/bin/python bash scripts/release-gate.sh`
- **Result:** `130 passed in 46.35s`.
- **Status:** Release gate passed. All tests, migrations, reconciliation queries, and Docker compose configurations execute cleanly on the current baseline without any regression from the previous reliability handoff.

## Progressive registry scale patch — 2026-07-31

- Confirmed source availability with the public registry using the exact active
  NAF codes and employee tranches:

  ```text
  43.22B=2357, 43.21A=3336, 33.12Z=678, 33.13Z=96,
  33.14Z=185, 80.20Z=333, 81.10Z=123; total=7108
  ```

- Live application connector smoke:

  ```text
  count=250
  unique_sirens=250
  raw_carried=250
  checkpoint={version: 2, plan_fingerprint: 463bb0819cffa468,
              partition: 0, page: 11, offset: 0}
  exhausted=false
  ```

- Focused progressive/replay proof:

  ```bash
  .venv/bin/python -m pytest -q \
    tests/test_reliability_hotfix.py::test_registry_checkpoint_resumes_inside_page \
    tests/test_reliability_hotfix.py::test_registry_plan_uses_v2_classification_codes \
    tests/test_reliability_hotfix.py::test_registry_progresses_across_thousands_without_replay
  ```

  Result: `3 passed in 1.14s`. The scale fixture produced two disjoint
  1,000-record batches and advanced page 1 → 41 → 81.

- PostgreSQL failure isolation/locking groups: `7 passed in 3.22s`, `3 passed
  in 7.70s`, and `3 passed in 5.38s`. Raw replay persisted two rows once and
  classified both second attempts as duplicates; a bad normalization row did
  not roll back two good rows.

- Complete release gate:

  ```bash
  PYTHON_BIN=.venv/bin/python bash scripts/release-gate.sh
  ```

  Result: clean unique PostgreSQL upgrade to `pfscale02_20260731`, zero
  reconciliation anomalies, npm audit zero vulnerabilities, Ruff/compile/
  shell/Compose/Caddy checks passed, `133 passed in 64.27s`, final output
  `Release gate passed`.

- Dedicated migration rehearsal on PostgreSQL 16:

  ```text
  clean upgrade -> pfscale02_20260731: pass
  downgrade -1 -> 76aae9630f93: pass (empty raw stage)
  re-upgrade -> pfscale02_20260731: pass
  reconcile --fail-on-anomaly: pass, zero anomalies
  ```

- After adding the bounded ingestion-retry regression and queue-specific
  worker-health check:

  ```bash
  TEST_DATABASE_URL=postgresql+asyncpg://prospectforge_test:test-only-password@127.0.0.1:55439/prospectforge_test \
  TEST_REDIS_URL=redis://127.0.0.1:56380/0 \
  .venv/bin/python -m pytest -q
  ```

  Result: `134 passed in 96.36s`.

- Final static checks: `.venv/bin/python -m ruff check .`, compileall for app,
  Alembic, tests, and scripts, `git diff --check`, shell syntax for the updated
  diagnostic script, and `alembic heads` all passed. Alembic reports exactly
  one head: `pfscale02_20260731`.

## DECP durable raw/checkpoint patch — 2026-07-31

- `tests/test_discovery.py` → `13 passed in 0.53s`. The new checkpoint test
  consumed six historical awards in three disjoint two-record batches, then
  consumed two newly arrived awards oldest-unseen-first without skipping.
- PostgreSQL integration
  `test_decp_awards_are_raw_persisted_aggregated_and_replay_safe` →
  `1 passed in 3.32s`. Three raw awards produced exactly three raw rows, two
  canonical company processing outcomes, one aggregate member, and two
  prospects. Same-run replay retained three raw rows and reported three
  duplicates.
- Ruff and `py_compile` for the DECP adapter, discovery, ingestion, model, and
  migration files passed.
- Clean PostgreSQL migration rehearsal reached `pfscale02_20260731`; the
  `source_checkpoints.high_water_mark` column is `text`, allowing the complete
  versioned DECP high-water/backfill cursor. The disposable rehearsal database
  was removed afterward.

## Recovery, canonical evidence, and hard-gated scoring — 2026-07-31/2026-08-01

- Static verification during implementation:

  ```bash
  .venv/bin/ruff check .
  .venv/bin/python -m compileall -q app alembic scripts
  git diff --check
  ```

  Result: passed.

- Durable recovery integration:

  ```bash
  TEST_DATABASE_URL=postgresql+asyncpg://prospectforge_test:test-only-password@127.0.0.1:55439/prospectforge_test \
  TEST_REDIS_URL=redis://127.0.0.1:56380/0 \
  .venv/bin/python -m pytest -q \
    tests/test_reliability_hotfix.py::test_stale_work_recovery_requeues_or_dead_letters_truthfully \
    tests/test_reliability_hotfix.py::test_raw_failure_reconciliation_uses_persisted_record
  ```

  First run: one test passed and one test assertion failed because the test
  expired its own ORM identifier before reading it. The test retained the IDs
  before expiration; corrected result: `2 passed in 3.35s`.

- Scoring gate table:

  ```bash
  .venv/bin/python -m pytest -q tests/test_scoring_v4.py
  ```

  Result: `11 passed in 0.21s`. Cases include ideal fit, irrelevant
  classification, inactive entity, missing verified domain, suppression,
  severe identity contradiction, role routing, guessed-only contact, stale
  evidence, human approval, and numeric-score/gate separation.

- Canonical identity/evidence/scoring PostgreSQL tests initially exposed that
  `company_identifiers.verified_at` was timezone-naive while the writer supplied
  UTC-aware values. The model and additive migration now use timezone-aware
  timestamps. Corrected canonical suite result:

  ```bash
  TEST_DATABASE_URL=postgresql+asyncpg://prospectforge_test:test-only-password@127.0.0.1:55439/prospectforge_test \
  TEST_REDIS_URL=redis://127.0.0.1:56380/0 \
  .venv/bin/python -m pytest -q tests/test_canonical_model.py tests/test_scoring_v4.py
  ```

  Result: `15 passed in 8.57s`.

- Authenticated operations retry/recovery endpoints:

  ```bash
  TEST_DATABASE_URL=postgresql+asyncpg://prospectforge_test:test-only-password@127.0.0.1:55439/prospectforge_test \
  TEST_REDIS_URL=redis://127.0.0.1:56380/0 \
  .venv/bin/python -m pytest -q \
    tests/test_reliability_hotfix.py::test_raw_failure_retry_endpoint_queues_durable_reconciler \
    tests/test_reliability_hotfix.py::test_stale_recovery_endpoint_reports_broker_acceptance_only
  ```

  Result: `2 passed in 5.86s`.

- Clean migration rehearsal reached `pfscale03_20260731`. A seeded
  production-shaped upgrade from `pfscale02_20260731` reconciled:

  ```text
  companies/opportunities/prospects: 1/1/1
  legacy evidence signals mapped: 1/1
  canonical evidence retained/active: 3/2
  deliberate duplicate retained inactive: 1
  mappable legacy signals unmapped: 0
  duplicate active fingerprints: 0
  orphan opportunities/evidence: 0/0
  ```

  `scripts/reconcile_reliability.py --fail-on-anomaly` exited zero.

- One isolated complete PostgreSQL suite (before the final two endpoint tests):

  ```bash
  TEST_DATABASE_URL=postgresql+asyncpg://prospectforge_test:test-only-password@127.0.0.1:55439/prospectforge_test \
  TEST_REDIS_URL=redis://127.0.0.1:56380/0 \
  .venv/bin/python -m pytest -q
  ```

  Result: `152 passed in 83.94s (0:01:23)`.

- Final complete release gate on the final tree:

  ```bash
  PYTHON_BIN=.venv/bin/python bash scripts/release-gate.sh
  ```

  Result: npm installed/audited 80 packages with `0 vulnerabilities`; assets
  rebuilt; Ruff, compileall, `git diff --check`, shell syntax, Compose, and all
  three Caddy configurations passed; a unique PostgreSQL database upgraded
  cleanly through `pfscale03_20260731`; reconciliation reported zero anomalies;
  `154 passed in 84.44s (0:01:24)`; final output `Release gate passed` and exit
  code `0`.

  Runtime: `.venv/bin/python --version` reports `Python 3.14.5`; this is not a
  substitute for the required Python 3.12 production certification.

- After deleting the unused fixed-bonus `services/scoring_engine.py` and
  moving its three tests onto the canonical evidence-bound scorer, focused
  scoring tests reported `14 passed in 0.25s`. The complete release gate was
  rerun on the final tree: `154 passed in 85.25s (0:01:25)`, zero
  reconciliation anomalies, zero npm vulnerabilities, all remaining checks
  passed, final output `Release gate passed`, exit code `0`.
