# Baseline Data Model

The current `app/models.py` defines a mix of legacy and newer, disconnected tables.

## Core Legacy Tables
- `User`: Handles authentication.
- `Prospect`: The legacy monolith table handling company data, contact info, domains, and scoring in a single row. This represents a flat structure rather than normalized entities.
- `OutreachEvent`: Tracks interactions but tied to the flat `Prospect` model.

## Newly Migrated (but disconnected) V4 Tables
There are tables that exist in the schema but are not fully integrated into the write path for bulk discovery (as observed in `app/jobs/ingestion.py` which still queries the flat structure):
- `Company`, `CompanyIdentifier`, `CompanyClassification`, `CompanyLocation`, `CompanyDomain`
- `Person`, `PersonRole`, `ContactPoint`, `ContactVerificationEvent`
- `MarketPlay`, `MarketPlayVersion`, `Opportunity`
- `EvidenceItem`, `ComplianceDecision`, `ScoreSnapshot`
- `Campaign`, `SequenceVersion`, `SequenceStep`, `MessageDraft`, `CampaignMembership`
- `Touch`, `ProviderEvent`, `ConversationEvent`
- `Task`, `SuppressionEntry`

## Assessment
The `Prospect` model is still fundamentally the operational source of truth. The V4 models exist in the database schema but are largely treated as parallel structures or are partially populated without full lineage from `SourceRecord` to `Company` to `Opportunity`.
