# Baseline Defect Register

Last verified: 2026-07-28

## Reliability rebuild disposition

| Defect | Verification | Current disposition |
|---|---|---|
| Missing `app` import | Not present | Repository-root test collection succeeds; final PostgreSQL suite collected and passed 130 tests. |
| Play/mode/limit/options dropped | Confirmed | Fixed. Immutable request is persisted before enqueue and worker propagation has a regression test. |
| UK default executing France sources | Confirmed | Fixed for mutation paths. `FIELD_OPERATIONS_FR_V2` is explicit; UK sourcing is rejected. |
| Placeholder adapter reported healthy | Confirmed | Fixed. Planned/misconfigured/degraded states are explicit; optional placeholders are not executable. |
| Background ingestion not durable | Changed since original audit | Celery existed, but enqueue/run truth was broken. Fixed with pre-enqueue `PipelineRun`, advisory lock, and durable work. |
| In-process scheduler | Not present in current code | Celery Beat existed but registered jobs unconditionally. Fixed with flags and a non-default Compose profile. |
| Whole-session rollback per bad item | Confirmed | Fixed with nested transactions and durable failed-work items. |
| Registry page-one replay | Confirmed | Fixed with partition+row checkpoints and replay tests. |
| Two run ledgers | Confirmed | New ingestion writes only canonical `PipelineRun`; legacy runs are retained and backfilled for history. |
| Company-name compatibility join | Confirmed by PostgreSQL tests | Fixed with explicit company/opportunity foreign keys and identifier-only backfill. |
| Canonical UUID passed to integer contact/review tables | Confirmed by PostgreSQL tests | Fixed by resolving the explicit compatibility link before legacy-table mutation. |
| Inline contact discovery during ingestion | Confirmed | Fixed. Request is rejected and contact work remains a separate gated stage. |
| Hardcoded dashboard success metrics | Confirmed | Fixed for implemented metrics; values now derive from persisted runs/prospects/opportunities/work. |
| Placeholder V4 scoring | Confirmed | Open. Automation depending on it remains disabled. |
| DECP progressive checkpoint/raw storage | Confirmed missing | Open. DECP remains a bounded idempotent rolling-window replay. |
| Mutable legacy/canonical field duplication | Confirmed | Partially mitigated with explicit links; full projection/write consolidation remains open. |

This document tracks known defects and architectural violations found before the V4 rebuild.

## 1. 500 Internal Server Error & Missing Application Module
During baseline tests (`pytest -q`), an `ImportError` was encountered: `ModuleNotFoundError: No module named 'app'`. This indicates that the `PYTHONPATH` or test configuration does not correctly include the application root, causing CI/CD or local test executions to fail immediately.

## 2. Execution-Path Contradictions
- The system globally defaults to `FIELD_OPERATIONS_UK_V1` but executes French DECP/Annuaire flows in `ingestion.py`.
- Form routes silently force `mode=full`, ignoring user input for `companies_house`.
- Fixture behavior is heavily relied upon (e.g., `companies_house.py` uses mock data when API keys are missing).

## 3. Disconnected Architecture
- The application executes off a flat `Prospect` table, ignoring the newly migrated normalized V4 tables (`Company`, `Opportunity`, etc.).

## 4. Scale and Reliability
- Ingestion processes operate within FastAPI `BackgroundTasks`, which lacks durability. Process restarts lose data.
- APScheduler is run in-process within the web container instead of a distributed Celery Beat cluster.

## 5. Intelligence and Frontend Claims
- The frontend includes static visual claims like "LEVEL 300" or "PECR/CNIL Pass" without corresponding verified backend validation.
- Message generation lacks evidence-bound checks, instead using raw heuristic data.

## 6. Raw 500 Internal Server Error (Identified & Fixed)
- **Exact Route**: `GET /queue`
- **Exception**: `NameError: name 'func' is not defined`
- **Query**: `count_q = select(func.count()).select_from(q.subquery())`
- **Data Condition**: Any authenticated user hitting the `/queue` page triggers the `_daily_queue` execution which attempts to use `func` without importing it from `sqlalchemy`.

## Phase 0 Continuation Verification

| Defect / Check | Verification | Current disposition |
|---|---|---|
| Release Gate passing | Confirmed | 130 tests pass cleanly, reconciliation shows zero anomalies. |
| Python Runtime | Confirmed | Running on Python 3.12.13 successfully. |
