# Baseline Runtime Topology

This document captures the runtime topology defined in `docker-compose.yml` before Phase 2 durability work.

## Containers
1. `db`: PostgreSQL 16 Alpine
2. `redis`: Redis 7 Alpine
3. `caddy`: Reverse proxy (Caddy 2)
4. `app`: The main FastAPI container using the `prospectforge:latest` image.
5. `celery-beat`: The Celery Beat scheduler container.
6. `worker-ingestion`: Celery worker for the `source-ingestion` queue.
7. `worker-domain`: Celery worker for the `identity-domain` queue.
8. `worker-evidence`: Celery worker for the `website-evidence` queue.
9. `worker-contact`: Celery worker for the `buyer-contact` queue.
10. `worker-campaign`: Celery worker for the `campaigns-notifications` queue.

## Observations
- The topology actually *does* contain the foundational Celery workers and Redis described in Phase 2, but the web application's routes (e.g. `sourcing.py`) are still mostly ignoring these Celery queues and executing heavy background ingestion tasks using FastAPI's `BackgroundTasks` instead.
- `app` process runs as an API server, while `worker-*` instances manage async loads.
- This is a good baseline, meaning Phase 2 involves routing the actual code through Celery, rather than spinning up entirely new infrastructure components from scratch.
