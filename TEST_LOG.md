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
