# Baseline Defect Register

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
