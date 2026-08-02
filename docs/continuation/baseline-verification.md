# Baseline Verification

Baseline date: 2026-07-29
Final verification update: 2026-08-01

## Runtime State
- **Python Version**: Python 3.12.13
- **Dependency Management**: Authoritative dependencies installed in the virtual environment.

## Git Status
The repository contains modifications to core files (routing, models, workers, templates, docker configuration) from the previous reliability phase, as well as untracked markdown prompts, run scripts, and test files introduced during the Codex reliability rebuild. Pre-existing user modifications (e.g. `app/templates/dashboard.html` and `scripts/deploy.sh`) are preserved and have not been overwritten.

## Test Environment
Integration tests rely on PostgreSQL and Redis containers configured via `docker-compose.yml`. The release-gate script uses Podman/Docker Compose to launch the test suite, applying migrations to a clean database and executing all backend logic.

## Verification Run
The baseline `release-gate.sh` run completed successfully:
- Frontend assets compiled (0 vulnerabilities).
- Migration applied cleanly to the test database.
- Reconciliation script (`scripts/reconcile_reliability.py`) executed with zero anomalies.
- All 130 tests passed in 46.35s.
- Caddy TLS/HTTP configurations were successfully validated.

## Phase Matrix

| Feature / Behavior | Status | File / Reference |
|---|---|---|
| Immutable pre-enqueue requests | Complete | `app/jobs/ingestion.py`, `app/models.py` |
| Propagated play/mode/limits | Complete | `app/routers/sourcing.py`, `app/workers/tasks.py` |
| Explicit France play selection | Complete | `FIELD_OPERATIONS_FR_V2` |
| Rejection of unsupported UK ingestion | Complete | `app/jobs/ingestion.py` |
| Canonical `PipelineRun` durability | Complete | `app/services/pipeline_runs.py` |
| Per-record savepoints | Complete | `app/jobs/ingestion.py` |
| Durable failed-work items | Complete | `app/models.py` |
| Bounded enrichment retries | Complete | `app/workers/tasks.py` |
| Progressive registry cursors | Complete | `app/discovery/annuaire.py` |
| Advisory locks | Complete | `app/services/run_lock.py` |
| Explicit `Prospect.company_id` | Complete | `app/models.py` |
| Scheduler feature-flag | Complete | `app/workers/celery_app.py` |
| Operations visibility API | Complete | `app/routers/operations.py` |

The original 130-test result above is retained as historical baseline evidence.
The final rebuild release gate now passes 166 PostgreSQL tests in 133.53s with
zero reconciliation anomalies and zero npm vulnerabilities. The complete suite
also passes in the production Python 3.12.13 image (`166 passed, 1 warning in
108.33s`). See `TEST_LOG.md` and `CODEX_HANDOFF.md` for the exact final commands,
live-source/contact acceptance, and the still-open actual production-copy gate.
