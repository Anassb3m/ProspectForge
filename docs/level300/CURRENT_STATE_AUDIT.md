# Current State Audit

## Architecture & Topology
- **Current State**: The system operates as a FastAPI monolith. `docker-compose.yml` includes Celery and Redis containers, but many long-running tasks (e.g., ingestion and enrichment) are inappropriately executed within the FastAPI event loop using `BackgroundTasks`. 
- **Data Model**: The database contains newly migrated V4 tables (`Company`, `Opportunity`, `EvidenceItem`, etc.) per migration `007`, but the application logic still heavily relies on the legacy, flat `Prospect` model.

## Stability & Testing
- **Test Suite**: Fails out of the box due to `ModuleNotFoundError` (`app` not found in `PYTHONPATH` during `pytest` execution).
- **Security**: The application resets the admin password on startup instead of treating it as an immutable bootstrap step.

## Sourcing & Intelligence
- **Fixtures**: Adapters (like `companies_house.py`) resort to fixture behaviors rather than true external API integrations or bulk file processing when tokens are missing.
- **Scoring & Workflow**: The UI displays hard-coded status indicators (e.g., "LEVEL 300") without verified backing logic. Message generation combines templates without strict, sourced evidence checks.

## User Interface
- **Dependencies**: Relies on external CDNs (Tailwind) in production.
- **Workflow**: Lacks dedicated, performant pagination and caching for processing datasets at the 10,000+ scale. UI elements often misrepresent the backend execution state (e.g., `play_code` dropdowns that don't match the backend processing).
