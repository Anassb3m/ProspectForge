# Canonical Model Cutover Map

## Overview
This document inventories the remaining usage of the `Prospect` model in the codebase, detailing the cutover paths to the canonical data model (`Company`, `Opportunity`, `EvidenceItem`, `Person`, `ContactPoint`, etc.).

## Write Paths (To Migrate)

### 1. Ingestion (`app/jobs/ingestion.py`)
- **Current Source of Truth**: Creates/Updates `Prospect` row with fields like `company_name`, `sector`, `company_size`, `email`, `website`, `source`.
- **Target Source of Truth**: Writes should go entirely to `Company`, `CompanyIdentifier`, `Opportunity`, and `ContactPoint`.
- **Compatibility Requirement**: The `Prospect` table should be maintained as a read-only projection or populated transparently via triggers/services for legacy dashboards.
- **Migration Order**: 1 (Must be fixed to enforce immutable ingestion and prevent dual-write).

### 2. Enrichment (`app/discovery/enrich.py`)
- **Current Source of Truth**: `apply_enrichment_to_prospect` updates `Prospect` with location (`city`, `department`, `region`), and scores.
- **Target Source of Truth**: `CompanyLocation`, `ScoreSnapshot`, `Opportunity` (for stages).
- **Migration Order**: 2.

### 3. Commercial Logic (`app/commercial.py`)
- **Current Source of Truth**: Modifies `Prospect` score fields, pipeline stages, and readiness states.
- **Target Source of Truth**: `Opportunity` (readiness state, scores) and `ScoreSnapshot` (immutable ledger of scores).
- **Migration Order**: 3.

### 4. Contact Intelligence (`app/contact_intelligence/service.py` & `app/jobs/contact_discovery.py`)
- **Current Source of Truth**: Creates/updates `Prospect.contact_candidates`, `Prospect.contact_confidence`, `Prospect.email`.
- **Target Source of Truth**: `Person`, `ContactPoint`, `ContactEvidence`.
- **Migration Order**: 4.

## Read Paths (To Project)

### 1. Dashboards and Views (`app/routers/prospects.py`, `app/templates/*.html`)
- **Current Source of Truth**: Queries `Prospect` for list views, detailed prospect pages, and kanban boards.
- **Target Source of Truth**: Read from `Prospect` as a projection or dynamically map from `Opportunity` joined with `Company`.
- **Migration Order**: 5 (Keep reading from `Prospect` but ensure it reflects canonical reality).

### 2. Campaigns and Outbound (`app/jobs/campaigns.py`, `app/services/outbound.py`)
- **Current Source of Truth**: Reads `Prospect.email`, `Prospect.decision_maker_name`, etc.
- **Target Source of Truth**: Read from `Person` and primary `ContactPoint`.
- **Migration Order**: 6.
