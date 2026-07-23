# Gap Matrix

This document maps the differences between the Current State (Baseline) and the Target State (V4 Level-300).

| Feature / Domain | Current Baseline | Target State (V4 Level-300) |
| --- | --- | --- |
| **Data Architecture** | Single, flat `Prospect` table serves as operational truth. V4 models exist but are largely unused in write paths. | Fully normalized tables (`Company`, `Opportunity`, `EvidenceItem`, `Person`, `CampaignMembership`). |
| **Task Orchestration** | FastAPI `BackgroundTasks` executing within the web context. Unsafe for scaling. | Durable job system using Celery, Redis, and Checkpoints with Leases and Retries. |
| **Data Sourcing** | Serial API calls to providers. Fake/fixture data generated when API keys are missing. | Robust streaming ingestion of bulk files (Companies House, Sirene). Hard separation of test fixtures from production. |
| **Scoring & Logic** | Heuristics and regex rules on raw text. Static UI badges showing "LEVEL 300" or "Passed". | Multi-dimensional scoring framework. Explicit evidence linking for every claim. Hard gates. |
| **Scale & UI** | Python-based filtering. Potential OOM issues for 10K+ records. External CDNs in production. | Server-side cursor pagination. Local assets built deterministically. Responsive UI designed for high-volume tabular review. |
| **Security** | Password resets on startup. Global defaults ignoring play-specific selections. | First-time-only password bootstrap. Role-based authorization. Precise tracking of data lineage and compliance policies. |
