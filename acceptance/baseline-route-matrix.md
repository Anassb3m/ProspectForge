# Baseline Route Matrix

This document captures the routing topology of the legacy implementation before the Level-300 architectural cutover.

## HTML Routes (Jinja2 Templates)
- `GET /` (Dashboard)
- `GET /login` (Auth)
- `GET /market-plays`
- `GET /prospects`
- `GET /prospects/new`
- `POST /prospects/new`
- `GET /prospects/{prospect_id}`
- `GET /prospects/{prospect_id}/edit`
- `POST /prospects/{prospect_id}/edit`
- `GET /prospects/{prospect_id}/enrich`
- `POST /prospects/{prospect_id}/enrich`
- `POST /prospects/{prospect_id}/deep-enrich`
- `POST /prospects/{prospect_id}/use-email`
- `POST /prospects/{prospect_id}/mark-reviewed`
- `GET /sourcing`
- `POST /sourcing/run-ingestion`
- `POST /sourcing/bulk-enrich`
- `GET /queue`
- `GET /queue/{prospect_id}/qualify`
- `POST /queue/{prospect_id}/qualify`
- `GET /follow-ups`
- `GET /kanban`
- `GET /import`
- `POST /import`

## API Routes (JSON)
- `GET /health`
- `GET /ready`
- `GET /api/v1/market-plays`
- `GET /api/v1/market-plays/{play_code}`
- `GET /api/prospects`
- `POST /api/prospects`
- `GET /api/prospects/{prospect_id}`
- `PATCH /api/prospects/{prospect_id}`
- `POST /api/prospects/import`
- `GET /api/prospects/export/csv`
- `POST /api/prospects/bulk-status`
- `GET /api/queue`
- `POST /api/queue/bulk-qualify`
- `GET /api/sourcing/queue`
- `POST /api/sourcing/ingest`
- `POST /api/sourcing/bulk-enrich`
- `POST /api/prospects/{prospect_id}/deep-enrich`
- `POST /api/prospects/{prospect_id}/enrich`
- `POST /api/prospects/{prospect_id}/use-email`
- `POST /api/prospects/{prospect_id}/mark-reviewed`
- `POST /prospects/{prospect_id}/contact-intelligence/run`
- `POST /prospects/{prospect_id}/contact-intelligence/review`
- `POST /prospects/{prospect_id}/contact-intelligence/add`
- `GET /api/dashboard/metrics`
- `GET /api/dashboard/follow-ups-due`
- `POST /api/events`

## Observations
- Many endpoints are duplicating the same logic (e.g., HTML vs API JSON endpoints for `/prospects/{id}/enrich`).
- Many background actions are currently executed within FastAPI `BackgroundTasks` instead of durable queues.
