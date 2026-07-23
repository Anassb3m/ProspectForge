
# ANTIGRAVITY MASTER EXECUTION PROMPT — REPOSITORY-AWARE V4 EDITION

## Repository fingerprint and authority

This prompt is grounded in the exact archive:

```text
ProspectForge-main(4).zip
SHA-256: 977802d8cdebad1ee9cfad9d602bb1d79e0d37ba9d01597d3dec7c3f91644a0b
```

The archive is byte-for-byte identical to `ProspectForge-main(3).zip`. Therefore, do not treat the filename `(4)` as evidence of a newer implementation. Treat the code contents, migrations, tests, and runtime behavior as the only source of truth.

This repository-aware edition adds exact file-level orders to the broader master rebuild specification included later in this document. Where a generic instruction and a repository-specific instruction overlap, the repository-specific instruction wins.

Do not merely read the broad design sections and then improvise. Begin with the exact defects and file changes in this repository-aware section.

---

# PART A — VERIFIED REPOSITORY AUDIT AND EXACT IMPLEMENTATION ORDER

# A0. Mandatory opening procedure

Before touching code:

1. Extract the archive and record the archive hash.
2. Create a Git branch:

```text
feat/prospectforge-v4-repository-aware-rebuild
```

3. Create the following artifacts:

```text
acceptance/repository-fingerprint.txt
acceptance/current-route-inventory.md
acceptance/current-template-action-inventory.md
acceptance/current-model-map.md
acceptance/current-migration-head.txt
acceptance/current-source-adapter-matrix.md
acceptance/current-job-topology.md
acceptance/current-security-defects.md
acceptance/current-ui-defects.md
acceptance/current-performance-risks.md
acceptance/current-test-baseline.txt
acceptance/current-production-topology.md
```

4. Record the current migration head:

```text
pfmm70_20260721
```

5. Run the test suite in a reproducible Python 3.12 environment. The repository declares Python `>=3.12`, but acceptance must use Python 3.12 unless the release explicitly certifies a newer version.
6. Use PostgreSQL 16 for integration and acceptance tests. SQLite may remain for fast unit tests only.
7. Build frontend assets with the repository’s own npm lockfile.
8. Launch the current app and capture every authenticated route before changes.
9. Reproduce the raw `Internal Server Error` shown in the supplied screenshots and identify:
   - route;
   - request method;
   - exact exception;
   - stack trace;
   - database row/data condition;
   - why no friendly error page rendered;
   - regression test that fails before the fix and passes after it.
10. Do not start visual redesign work until the baseline defect register is complete.

---

# A1. Exact verified contradictions that are release blockers

The application currently claims multi-market acquisition behavior that the execution path does not actually provide.

## A1.1 The sourcing form advertises a market-play selector that the backend ignores

Verified files:

```text
app/templates/sourcing.html
app/routers/sourcing.py
app/jobs/ingestion.py
```

The template submits:

```text
play_code=FIELD_OPERATIONS_UK_V1
or
play_code=FIELD_OPERATIONS_FR_V2
```

But `form_run_ingestion()` in `app/routers/sourcing.py` does not accept a `play_code` form field at all.

It accepts only:

```text
max_companies
mode
contacts
skip_sirene
```

Then `run_ingestion()` in `app/jobs/ingestion.py` hard-codes `DEFAULT_PLAY_CODE`, which is currently:

```text
FIELD_OPERATIONS_UK_V1
```

Yet the same ingestion function runs only the legacy DECP and French registry routines:

```text
ingest_decp()
ingest_registry()
```

This means the UI can present “UK + Companies House,” while the backend launches French DECP/Sirene-oriented ingestion.

Mandatory fix:

1. Remove `mode` as an overloaded concept.
2. Introduce explicit identifiers:
   - `play_version_id`;
   - `connector_code`;
   - `dataset_snapshot_id` when applicable;
   - `run_profile_code`;
   - `requested_limit`;
   - `requested_by_user_id`.
3. The POST route must validate that the selected connector is allowed for the selected market-play version.
4. Persist the requested configuration before queueing work.
5. The worker must load the persisted run configuration from the database. It must not rely on `DEFAULT_PLAY_CODE`.
6. Reject invalid combinations with a useful 422 response and UI explanation.
7. Add integration tests proving:
   - UK + Companies House creates a UK source run;
   - France + DECP creates a French source run;
   - UK + DECP is rejected unless a future play explicitly allows it;
   - changing the UI play changes the backend run;
   - persisted run configuration survives restart.

## A1.2 The Companies House adapter fabricates a company when credentials are missing

Verified file:

```text
app/sources/companies_house.py
```

Current behavior:

```python
if not self.api_key:
    return [RawSourceRecord(... fabricated Apex Commercial Refrigeration & HVAC Ltd ...)]
```

The health check also returns:

```text
is_healthy=True
Running in fixture mode (no API key set)
```

This is prohibited in every non-test environment.

Mandatory fix:

1. Delete production fixture fallback.
2. Move fixture data to:

```text
tests/fixtures/sources/companies_house/
```

3. Introduce a connector runtime state enum:

```text
unconfigured
credential_blocked
ready
running
degraded
rate_limited
stale
failed
disabled
```

4. If credentials are absent:
   - `discover()` must raise a typed `ConnectorConfigurationError`;
   - health must return `credential_blocked`;
   - no `RawSourceRecord` may be emitted;
   - no company, opportunity, or success count may be created.
5. Add a separate explicit test adapter or dependency-injected fake for tests.
6. Add tests proving fixture code cannot be reached when `ENVIRONMENT=production`.

## A1.3 The DECP adapter is entirely fabricated

Verified file:

```text
app/sources/decp_adapter.py
```

Current behavior returns one synthetic contract record with:

```text
Société France Maintenance SAS
SIREN 808123456
montant 150000
date_notification 2026-05-10
```

The health check always returns healthy without performing a fetch.

Mandatory fix:

1. Remove the fabricated output.
2. Wrap the actual DECP acquisition logic already present in `app/discovery/decp.py`, or replace it with a new production adapter that:
   - retrieves or loads a real dataset snapshot;
   - records dataset version and retrieval time;
   - validates required columns;
   - filters by play classifications/CPV/keywords;
   - stores immutable source records;
   - normalizes holder entities;
   - records rejected-row reasons.
3. Health must distinguish:
   - endpoint reachable;
   - dataset downloaded;
   - dataset parsed;
   - latest successful data timestamp;
   - schema compatible;
   - current query executable.
4. A source is not healthy merely because a method exists.
5. Add tests with captured real-format fixtures, not invented business entities in production code.

## A1.4 Sirene adapter health is not truthful enough

Verified file:

```text
app/sources/sirene_adapter.py
```

Current health is unconditional. `validate_config()` is empty.

Mandatory fix:

1. Define the exact source mode:
   - bulk stock dataset;
   - Annuaire API;
   - Sirene API;
   - cached local snapshot.
2. Validate credentials or snapshot availability.
3. Persist snapshot metadata.
4. Test an actual lightweight query or validate the local snapshot.
5. Return typed failure states.
6. Never return `ready` when the source has not been queried successfully within the configured freshness window.

## A1.5 Source adapters are mostly disconnected from the real ingestion pipeline

The normalized source package exists:

```text
app/sources/
```

The legacy production ingestion path uses:

```text
app/discovery/decp.py
app/discovery/annuaire.py
app/discovery/sirene.py
app/jobs/ingestion.py
```

The interface allows connector selection, but the selected adapter is not the actual orchestration source of truth.

Mandatory fix:

1. Define one adapter registry.
2. Every connector must implement one contract.
3. All source runs must execute through that registry.
4. Legacy discovery modules may become adapter internals but cannot remain separate parallel pipelines.
5. Remove duplicate code paths after backfill and cutover.
6. Tests must prove that every visible connector maps to one real executable adapter.

## A1.6 Normalized multi-market models exist but are largely unused

Verified models in `app/models.py`:

```text
Company
CompanyIdentifier
CompanyName
CompanyClassification
CompanyLocation
CompanyDomain
CompanyEstimate
SourceConnector
SourceRun
SourceRecord
MarketPlayVersion
Opportunity
EvidenceItem
Person
PersonRole
CompliancePolicy
ComplianceDecision
ScoreSnapshot
Campaign
Touch
```

Verified operational routes and services still depend mainly on:

```text
Prospect
OutreachEvent
Task
QualificationReview
```

This creates a decorative normalized schema while the product still behaves as a France-shaped flat prospect tracker.

Mandatory fix:

1. `Company` becomes authoritative for company identity.
2. `Opportunity` becomes authoritative for market-play qualification.
3. `EvidenceItem` becomes authoritative for evidence.
4. `Person` and `PersonRole` become authoritative for buyers.
5. Introduce or normalize contact routes so they are linked to `Person` and/or `Company`, not only legacy `Prospect`.
6. `Campaign` and sequence membership become authoritative for outreach.
7. `Prospect` becomes:
   - a temporary compatibility projection;
   - read-only after cutover;
   - eventually removable.
8. Add a `legacy_prospect_id` bridge on normalized records during migration.
9. Every new UI route must read normalized models.
10. Legacy routes must either redirect to new routes or use a projection service.
11. Prove that a new UK company can pass through the full normalized pipeline without creating a France-specific `Prospect` first.

## A1.7 Long-running work is non-durable

Verified files:

```text
app/routers/sourcing.py
app/jobs/scheduler.py
app/main.py
scripts/entrypoint.sh
docker-compose.yml
```

Current behavior uses:

```text
FastAPI BackgroundTasks
AsyncIOScheduler inside the web process
single web worker to avoid duplicate scheduler execution
```

This means work can disappear on:

- app restart;
- deploy;
- container crash;
- worker timeout;
- process kill;
- multiple web replicas.

Mandatory fix:

1. Add Redis.
2. Add Celery workers.
3. Add Celery Beat.
4. Remove APScheduler from production.
5. Remove FastAPI `BackgroundTasks` for durable acquisition/enrichment.
6. Persist a `JobRun` before enqueue.
7. Add:
   - job attempts;
   - stage checkpoints;
   - heartbeats;
   - worker leases;
   - retries;
   - retry classification;
   - dead-letter state;
   - cancellation;
   - pause/resume;
   - idempotency key;
   - progress counters;
   - error samples;
   - logs correlation.
8. Web routes return a run ID immediately.
9. UI polls or receives HTMX/SSE progress from persisted state.
10. Restart tests must prove an interrupted job resumes without duplicate source records.

## A1.8 Admin passwords are overwritten at every app start

Verified file:

```text
app/main.py
```

Current behavior:

```python
else:
    admin.hashed_password = hash_password(settings.admin_password)
```

Mandatory fix:

1. Startup may create an initial admin only when no user exists.
2. Startup must never change an existing password.
3. Add a separate explicit CLI command:

```text
python -m app.cli.users reset-password --email ...
```

4. Audit password changes.
5. Add tests proving restart does not change credentials.

## A1.9 Login rate limiting is process-local

Verified file:

```text
app/security.py
```

The rate limiter uses an in-memory dictionary.

Mandatory fix:

1. Move production login throttling to Redis.
2. Key by normalized email + IP/device risk.
3. Add expiry and lockout state.
4. Keep a lightweight in-memory fallback only for development.
5. Record security events without logging passwords or tokens.

## A1.10 The CSRF middleware permits mutation when the cookie is missing

Verified logic in `app/security.py` allows a first mutation when no CSRF cookie exists.

Mandatory fix:

1. Do not permit mutating browser requests merely because the cookie is absent.
2. Ensure a token is issued on safe GET.
3. Require cookie/header equality for every browser mutation.
4. Use Bearer exemption only for authenticated JSON API clients.
5. Add CSRF regression tests for normal forms, HTMX, fetch, login, logout, and expired sessions.

## A1.11 The global form handler rewrites the entire document

Verified file:

```text
app/static/js/app.js
```

Current code intercepts almost every POST and uses:

```javascript
document.open();
document.write(html);
document.close();
```

Mandatory fix:

1. Delete this global interception strategy.
2. Use normal browser form submission for full-page forms.
3. Use HTMX only on forms intentionally designed for partial updates.
4. Build a shared mutation helper only for JSON/fetch actions.
5. Add:
   - CSRF header;
   - timeout;
   - loading state;
   - error body parsing;
   - toast;
   - retry where safe;
   - request ID display.
6. Never replace a full document with `document.write`.

## A1.12 Kanban mutation is not production-grade

Verified file:

```text
app/static/js/kanban.js
```

Current code uses a browser alert and inconsistent CSRF handling.

Mandatory fix:

1. Stop using `alert()`.
2. Add CSRF.
3. Use optimistic UI only after validating transition permissions.
4. Revert the card on failure.
5. Display a structured error toast.
6. Record stage transition history.
7. Enforce transitions server-side.
8. The commercial pipeline must contain only real commercial opportunities, not the entire company universe.

## A1.13 Queue template posts to nonexistent routes

Verified template:

```text
app/templates/queue.html
```

It posts to:

```text
/queue/review/{{ p.id }}
```

No such router endpoint exists.

The actual qualification endpoint is:

```text
POST /queue/{prospect_id}/qualify
```

Mandatory fix:

1. Remove nonexistent actions.
2. The queue must open a qualification drawer or route with the required checklist.
3. A one-click “accept” button must not bypass six mandatory confirmations.
4. Add route/template contract tests that crawl every internal form action and verify a matching route exists.

## A1.14 Market-play page is a static code view, not an operational control surface

Verified files:

```text
app/routers/market_plays.py
app/templates/market_plays.html
app/plays/__init__.py
```

The page reads in-memory dictionaries and does not show real run or yield data.

Mandatory fix:

1. Persist market-play versions.
2. Show:
   - active version;
   - jurisdiction;
   - allowed connectors;
   - last source run;
   - next scheduled run;
   - universe size;
   - eligible count;
   - evidence-ready count;
   - contact-ready count;
   - review acceptance rate;
   - outreach rate;
   - reply/meeting outcomes;
   - current policy version;
   - source health;
   - configuration diff from prior version.
3. Launching sourcing creates a source run tied to the displayed version.

## A1.15 Dashboard contains unsupported and misplaced claims

Verified file:

```text
app/templates/dashboard.html
```

Examples:

```text
Benchmark ≥ 15%
PECR/CNIL Pass
Companies House: Active
DECP Wins under Meeting Conversion
```

Mandatory fix:

1. Remove all unsupported benchmarks.
2. Replace `0.0%` with `—` when denominator is zero.
3. Never claim compliance “pass” globally. Show counts of current decisions by policy state.
4. Connector status must come from runtime records.
5. Dashboard metrics must answer:
   - what work is due;
   - where the funnel is blocked;
   - which source produced usable opportunities;
   - which cohort produced replies/meetings;
   - whether workers and sources are healthy.
6. Add metric definitions and denominator tooltips.

## A1.16 Sourcing and dashboard load entire tables into memory

Verified examples:

```text
app/routers/sourcing.py -> all_p = list(all_q.scalars().all())
app/services/__init__.py -> repeated scalars().all()
app/jobs/ingestion.py -> rescore all loads all prospects
app/routers/queue.py -> q.limit(500), then Python sorting
```

Mandatory fix:

1. Use SQL aggregation for counts.
2. Use keyset pagination for large lists.
3. Compute dashboard metrics through grouped SQL queries or materialized summaries.
4. Stream or batch large rescoring jobs.
5. Do not load 10,000+ companies into Python memory for routine pages.
6. Add query-count and p95 latency tests.

## A1.17 The database page is still legacy-prospect-centric

Verified files:

```text
app/routers/prospects.py
app/templates/prospects.html
app/templates/partials/prospect_table.html
```

Mandatory fix:

1. Replace “Prospect Database” with:
   - Company Universe;
   - Opportunity Explorer;
   - Buyer & Contact Review.
2. Do not mix legal entity, opportunity score, outreach state, and contact fields in one flat record.
3. Add server-side:
   - pagination;
   - sorting;
   - filter facets;
   - saved views;
   - selectable columns;
   - export job;
   - bulk actions;
   - data lineage.
4. CSV export of large sets must run as a job and generate a downloadable artifact.
5. Sensitive contact columns must respect permissions.

## A1.18 CSV import schema is stale and contradictory

Verified file:

```text
app/templates/import.html
```

It advertises stale values such as:

```text
BOAMP_WIN
MOROCCO_OPS
PAIN_POST
LinkedIn
```

Mandatory fix:

1. Remove stale schema text.
2. Build staged import:
   - upload;
   - detect encoding/delimiter;
   - map columns;
   - choose target entity type;
   - preview rows;
   - validate;
   - deduplicate;
   - compliance/provenance mapping;
   - confirm;
   - execute as durable job;
   - download error file.
3. Never treat an imported email as verified without its source and evidence.
4. Store provider/export provenance.

## A1.19 CSS has two conflicting systems

Verified files:

```text
app/static/css/input.css
app/static/css/app.css
app/templates/base.html
```

Current state:
- old light component layer in `input.css`;
- dark `!important` override layer in generated `app.css`;
- additional inline CSS in `base.html`;
- Tailwind CDN loaded on top.

Mandatory fix:

1. Delete CDN Tailwind.
2. Delete inline Tailwind config.
3. Move all tokens to `tailwind.config.js` and source CSS.
4. Remove blanket `!important`.
5. Build one component layer.
6. Bundle fonts locally or use a robust system-font stack.
7. Bundle Alpine only if it is still needed; otherwise remove it.
8. Keep HTMX local.
9. Add content hashing and cache headers for static assets.

## A1.20 Production frontend depends on third-party CDNs

Verified in `app/templates/base.html`:
- Google Fonts;
- Tailwind CDN;
- jsDelivr Alpine.

Mandatory fix:
- no external CDN is required for application rendering or operation;
- CSP can block third-party scripts;
- all assets are built and served locally.

---

# A2. Exact new target architecture

Implement this topology:

```text
Browser
  ↓ HTTPS
Caddy
  ↓
FastAPI web application (stateless)
  ↓
PostgreSQL 16
  ↓
Redis
  ↓
Celery workers
  ↓
Celery Beat
  ↓
Source adapters / email provider / controlled external services
```

Docker Compose must contain at least:

```text
app
worker-acquisition
worker-enrichment
worker-outreach
beat
redis
db
caddy
optional-reacher
```

Production web may scale horizontally because scheduling is no longer in-process.

Each worker queue must have explicit routing:

```text
acquisition
normalization
identity
domain
evidence
buyer
contact
scoring
campaign
delivery
reply
maintenance
exports
```

Set concurrency and source budgets independently.

---

# A3. Exact package and file structure to create

Create or refactor toward this structure:

```text
app/
  api/
    dependencies.py
    errors.py
    pagination.py
    responses.py
    request_id.py
  domain/
    companies/
      models.py
      schemas.py
      repository.py
      service.py
      identity.py
      dedupe.py
    opportunities/
      models.py
      schemas.py
      repository.py
      service.py
      state_machine.py
    evidence/
      models.py
      schemas.py
      repository.py
      service.py
      taxonomy.py
    people/
      models.py
      schemas.py
      repository.py
      service.py
      roles.py
    contacts/
      models.py
      schemas.py
      repository.py
      service.py
      verification.py
    compliance/
      models.py
      schemas.py
      repository.py
      engine.py
      policies/
        uk_b2b_corporate_v1.py
        fr_b2b_professional_v1.py
    scoring/
      models.py
      schemas.py
      engine.py
      profiles/
        field_ops_uk_v1.py
        field_ops_fr_v2.py
    campaigns/
      models.py
      schemas.py
      repository.py
      service.py
      state_machine.py
    tasks/
      models.py
      repository.py
      service.py
  connectors/
    registry.py
    base.py
    errors.py
    companies_house/
      adapter.py
      bulk.py
      api.py
      normalize.py
      fixtures/
    sirene/
      adapter.py
      bulk.py
      api.py
      normalize.py
    decp/
      adapter.py
      dataset.py
      normalize.py
    website/
      adapter.py
      crawl.py
      extract.py
    csv/
      adapter.py
      validate.py
      mapping.py
  jobs/
    celery_app.py
    routing.py
    models.py
    repository.py
    orchestration.py
    tasks/
      acquisition.py
      normalization.py
      identity.py
      domain.py
      evidence.py
      buyers.py
      contacts.py
      scoring.py
      campaigns.py
      delivery.py
      replies.py
      exports.py
      maintenance.py
  web/
    routers/
      command_center.py
      my_work.py
      market_plays.py
      source_runs.py
      companies.py
      opportunities.py
      qualification.py
      contacts.py
      evidence.py
      campaigns.py
      drafts.py
      replies.py
      followups.py
      pipeline.py
      connectors.py
      data_quality.py
      workers.py
      suppression.py
      audit.py
      settings.py
    templates/
      layouts/
      components/
      command/
      acquire/
      qualify/
      outreach/
      operations/
    static/
      css/
      js/
      icons/
  cli/
    users.py
    sources.py
    jobs.py
    maintenance.py
```

This is a target organization. Antigravity may stage the move, but it must not preserve one 1,000-line `models.py`, one 700-line router, and one 500-line generic service module as the final architecture.

---

# A4. Exact migration sequence

Current migration head is:

```text
pfmm70_20260721
```

Create staged revisions. Names may differ, but responsibilities must remain separated.

## Migration 008 — durable job foundation

Create:

```text
job_runs
job_attempts
job_checkpoints
job_events
dead_letter_items
worker_heartbeats
```

Required fields include:
- UUID;
- job type;
- queue;
- state;
- idempotency key;
- requested by;
- payload hash;
- progress total/completed/rejected;
- current stage;
- lease owner;
- lease expiry;
- heartbeat;
- attempt count;
- retry classification;
- error code;
- error summary;
- created/started/finished timestamps;
- cancellation and pause flags.

## Migration 009 — connector runtime truth

Extend/create:

```text
source_connectors
source_connector_credentials
source_connector_health
dataset_snapshots
source_runs
source_run_partitions
source_records
source_record_rejections
```

Add:
- credential state;
- runtime state;
- last checked;
- last successful fetch;
- freshness SLA;
- rate-limit state;
- current dataset snapshot;
- query fingerprint;
- partition cursor;
- payload hash;
- immutable raw storage reference.

## Migration 010 — company universe cutover

Add:
- legacy bridge;
- canonical identity key;
- official registration status;
- legal form;
- official website state;
- merge/split audit;
- identity confidence;
- indexes for country, identifier, classification, domain, status.

Create:
- `company_merge_events`;
- `company_identity_decisions`;
- `company_snapshots`.

## Migration 011 — opportunity and qualification lifecycle

Add:
- opportunity state history;
- hard-gate status;
- rejection codes;
- active score version;
- human review status;
- assigned reviewer;
- next required action.

Create:
- `opportunity_state_events`;
- `qualification_reviews_v2`;
- `opportunity_tasks`.

## Migration 012 — people and contact routes

Normalize:
- person;
- role;
- company relation;
- contact route;
- contact evidence;
- verification event;
- publication state;
- deliverability state;
- utility state;
- suppression relation.

Create:
```text
contact_routes
contact_route_evidence
contact_verification_events_v2
contact_role_decisions
```

Backfill from legacy `ContactPerson` and `ContactPoint`.

## Migration 013 — evidence governance

Extend evidence with:
- claim type;
- source record;
- quoted/extracted text;
- observed date;
- freshness;
- contradiction group;
- confidence;
- verifier;
- message-eligibility flag.

Create:
```text
evidence_contradictions
evidence_reviews
```

## Migration 014 — scoring and gold-set calibration

Create:
```text
scoring_profiles
score_snapshots_v2
score_components
gold_sets
gold_set_items
calibration_runs
```

## Migration 015 — campaign and sequence engine

Create:
```text
campaigns_v2
campaign_memberships
sequences
sequence_steps
message_drafts
message_draft_evidence
touches_v2
delivery_attempts
```

## Migration 016 — replies, bounces, suppression, outcomes

Create:
```text
inbound_messages
reply_classifications
bounce_events
unsubscribe_events
suppression_entries_v2
commercial_deals
commercial_stage_events
```

## Migration 017 — saved views, audit, UI preferences

Create:
```text
saved_views
saved_view_filters
user_preferences
audit_events
notifications
```

## Migration 018 — legacy projection and cutover

Create:
- normalized-to-legacy projection where needed;
- cutover flags;
- data-parity checks.

Stop new writes to `prospects` after acceptance.

Every migration must include:
- upgrade;
- downgrade or explicit irreversible rationale;
- data backfill;
- row-count validation;
- constraint validation;
- index validation;
- production timing estimate;
- rollback plan.

---

# A5. Acquisition orchestration contract

A source run must execute as a persisted state machine:

```text
created
→ validated
→ queued
→ acquiring
→ raw_persisted
→ normalizing
→ identity_resolving
→ deduplicating
→ play_evaluating
→ opportunity_creating
→ domain_verifying
→ evidence_collecting
→ scoring
→ completed
```

Alternative terminal states:

```text
blocked_credentials
blocked_policy
paused
cancelled
failed_retryable
failed_terminal
completed_with_rejections
```

Rules:
1. Each stage writes a checkpoint.
2. Stage transitions are append-only audited.
3. Retry begins from the latest valid checkpoint.
4. Raw source records are immutable.
5. Normalized observations can be recomputed from raw data.
6. Deduplication is idempotent.
7. A source record cannot create duplicate companies on replay.
8. A company can create at most one opportunity per play version.
9. Run progress is queryable without reading worker logs.
10. UI uses persisted progress only.

---

# A6. 10,000-company data strategy

Do not attempt to discover 10,000 companies using repeated REST search calls.

## UK

Use:
- Companies House bulk company data snapshot for universe creation;
- selective Companies House API calls for refresh/detail;
- classification and legal-form filters;
- official website/domain resolution after initial ICP filtering.

## France

Use:
- Sirene bulk stock files for universe creation;
- selective Annuaire/Sirene refresh;
- DECP as a trigger/evidence source, not the company universe;
- BODACC or future sources as events.

Store:
- dataset snapshot ID;
- download checksum;
- source date;
- schema version;
- record count;
- processed partitions;
- import errors.

Target performance:
- import 10,000 company rows without browser timeout;
- list p95 under 500 ms for normal filters;
- detail p95 under 800 ms excluding live enrichment;
- source-run launch under 300 ms;
- progress view under 500 ms;
- no routine query scans all raw JSON payloads.

---

# A7. Unified scoring V4

Remove operational dependence on:
- `app/scoring.py`;
- `app/scoring_v3.py`;
- fragmented scoring inside services.

Build one versioned engine with dimensions:

```text
ICP fit
operational complexity
pain evidence
timing/trigger
technology opportunity
buyer authority
budget capacity
data quality
contactability
compliance eligibility
```

Hard gates:
- official identity;
- allowed legal entity;
- eligible classification or manually accepted fit;
- official domain or approved alternate;
- at least one current pain/trigger/technology evidence item;
- buyer role;
- contact route state;
- policy pass;
- suppression pass;
- human acceptance before outreach.

Persist:
- profile version;
- component values;
- evidence IDs;
- hard-gate results;
- failure reasons;
- computation timestamp.

A score never overrides a failed gate.

---

# A8. Exact UI rebuild order

Do not redesign page by page in the old navigation. Replace the information architecture first.

## Navigation

```text
COMMAND
  Command Center
  My Work

ACQUIRE
  Market Plays
  Source Runs
  Company Universe
  Imports

QUALIFY
  Opportunity Review
  Buyer & Contact Review
  Evidence Review

OUTREACH
  Campaigns
  Draft Approval
  Replies
  Follow-ups
  Commercial Pipeline

OPERATIONS
  Connectors
  Data Quality
  Jobs & Workers
  Suppression
  Audit Log
  Settings
```

## Command Center

Show:
- due work;
- blocked jobs;
- worker/source health;
- funnel stage counts;
- review throughput;
- source yield;
- campaign outcomes;
- recent failures;
- quick actions.

No giant icon cards.

## My Work

One queue of operator tasks:
- reply;
- follow-up;
- qualification;
- contact review;
- evidence review;
- failed-run intervention;
- draft approval.

Support keyboard navigation and bulk actions where safe.

## Market Plays

Compact rows/cards with real runtime data and version history.

## Source Runs

Table:
- run ID;
- play;
- connector;
- state;
- progress;
- created;
- duration;
- discovered;
- normalized;
- rejected;
- companies created/updated;
- opportunities created;
- error count;
- operator;
- actions.

Run detail:
- stage timeline;
- partitions;
- logs;
- rejection samples;
- retry/resume/cancel;
- configuration;
- dataset snapshot;
- source health.

## Company Universe

Server-side table:
- company;
- country;
- legal identifier;
- legal status;
- classification;
- estimated field size;
- official domain;
- identity confidence;
- opportunity count;
- last updated;
- data-quality flags.

## Opportunity Review

High-speed triage:
- company summary;
- play;
- score;
- hard-gate failures;
- top evidence;
- buyer/contact state;
- accept/research/park/reject;
- reason codes;
- keyboard shortcuts.

## Company Intelligence Workspace

Tabs:
- Overview;
- Identity;
- Operations;
- Evidence;
- People;
- Contacts;
- Opportunities;
- Outreach;
- Activity;
- Source records.

## Campaigns

Separate campaign membership from commercial pipeline.
Campaign builder must preview:
- cohort size;
- policy exclusions;
- suppression exclusions;
- missing contacts;
- missing evidence;
- approved drafts;
- send caps.

## Replies

Inbound messages with classification and stop-rule enforcement.

## Commercial Pipeline

Only opportunities with a real commercial state:
- engaged;
- discovery;
- mapping sprint;
- proposal;
- negotiation;
- won;
- lost;
- nurture.

Raw companies must never appear.

---

# A9. Design system exact requirements

Use a restrained professional dark interface.

## Foundations

- system or locally bundled sans-serif;
- locally bundled monospace only where needed;
- compact 14–16 px body typography;
- 24–30 px page headings, not giant headings;
- 8 px spacing system;
- 4–8 px radius for controls;
- 8–12 px radius for panels;
- subtle 1 px borders;
- minimal shadows;
- one accent color;
- semantic success/warning/error/info colors.

## Prohibited

- emoji as icons;
- huge decorative SVGs;
- constant glow;
- glassmorphism everywhere;
- gradients on every button;
- white Kanban columns;
- full-screen border frame;
- static “Level 300” badges;
- animated pulse implying fake live status;
- unreadable low-contrast text.

## Required components

```text
AppShell
Sidebar
Topbar
Breadcrumbs
PageHeader
Metric
StatusBadge
DataTable
FilterBar
SavedViewPicker
Pagination
Drawer
Modal
Tabs
Timeline
RunProgress
EmptyState
ErrorState
Toast
ConfirmationDialog
CommandPalette
Skeleton
InlineValidation
AuditMetadata
EvidenceChip
GateChecklist
```

Every component must have:
- default;
- hover;
- focus;
- disabled;
- loading;
- error;
- empty;
- responsive behavior;
- accessible label.

---

# A10. Error handling

Add:
- request ID middleware;
- structured exception hierarchy;
- HTML 404/403/422/500 pages;
- JSON problem responses;
- error logging with correlation ID;
- safe operator detail;
- no stack trace in production;
- retry action only for retry-safe operations.

The raw `Internal Server Error` page must be impossible for normal browser routes.

---

# A11. Tests that must be added

## Contract tests

- every template form action has a route;
- every HTMX target exists;
- every mutation includes CSRF;
- every visible connector maps to a registered adapter;
- every market-play connector combination validates.

## Source tests

- no production fixture fallback;
- credential-blocked state;
- real-format fixture parse;
- pagination;
- rate-limit handling;
- schema drift;
- partial failure;
- idempotent replay;
- snapshot checksum.

## Job tests

- persist before enqueue;
- restart/resume;
- worker lease expiry;
- retry;
- dead letter;
- pause/resume;
- cancellation;
- idempotency;
- no duplicate company/opportunity.

## Migration tests

- upgrade empty database;
- upgrade populated legacy database;
- parity counts;
- rollback or restore path;
- constraints and indexes.

## UI tests

- all routes load authenticated;
- no raw 500;
- no external CDN dependency;
- keyboard operation;
- responsive screenshots;
- empty/error/loading states;
- color contrast;
- no missing icons;
- no unsupported static status claims.

## Performance tests

Use at least:
- 10,000 companies;
- 2,500 opportunities;
- 5,000 evidence items;
- 1,000 people;
- 1,000 contact routes;
- 500 campaign memberships.

Measure:
- page p50/p95;
- API p50/p95;
- query count;
- memory;
- batch throughput;
- worker restart behavior.

---

# A12. Exact file-by-file disposition

## `app/main.py`

Must:
- stop password overwrite;
- remove scheduler startup;
- add request ID and global errors;
- keep app stateless;
- seed only immutable/reference data safely;
- not mutate operator credentials.

## `app/config.py`

Must add:
- Redis URL;
- Celery broker/backend;
- queue settings;
- source budgets;
- connector credential state;
- environment validation;
- frontend asset manifest;
- outbound disabled-by-default flag;
- sender caps;
- health freshness thresholds.

## `docker-compose.yml`

Must add:
- Redis;
- workers;
- Beat;
- health checks;
- queue-specific commands;
- resource limits;
- persistent volumes where necessary;
- no public database/Redis exposure.

## `pyproject.toml`

Must:
- add Celery and Redis dependencies;
- pin compatible ranges;
- add structured logging/metrics dependencies if selected;
- preserve Python 3.12 support;
- add test tools for browser/integration if used.

## `app/models.py`

Must be decomposed or reduced to imports from domain modules.
Do not keep adding more classes to the 1,092-line file.

## `app/routers/sourcing.py`

Must be replaced by:
- source-run creation endpoint;
- run list/detail;
- run controls;
- no nested background job functions;
- no legacy all-table stats.

## `app/jobs/ingestion.py`

Must become orchestration tasks using persisted runs.
No `DEFAULT_PLAY_CODE`.
No synchronous monolithic full run.
No mixed source logic.

## `app/jobs/scheduler.py`

Remove from production.
Replace with Celery Beat schedules.

## `app/sources/*.py`

Refactor into truthful adapters.
Fixtures live under tests only.

## `app/services/__init__.py`

Split the 562-line mixed service module into domain services/repositories.
Do not retain it as a dumping ground.

## `app/scoring.py` and `app/scoring_v3.py`

Deprecate and remove after parity tests.
One Scoring V4 engine only.

## `app/templates/base.html`

Must contain:
- semantic shell;
- local CSS/JS only;
- no inline Tailwind config;
- no external fonts/scripts;
- no emoji navigation;
- truthful runtime indicator.

## `app/static/js/app.js`

Replace with small modules.
No `document.write`.

## `app/static/js/kanban.js`

Replace or rebuild with safe transitions and toasts.

## `app/static/css/input.css` and `app/static/css/app.css`

One source stylesheet and generated artifact.
No blanket `!important`.

## `app/templates/queue.html`

Replace broken `/queue/review/` actions.
Convert to normalized opportunity review.

## `app/templates/kanban.html`

Use only commercial deals/opportunities.
Never render all raw companies.

## `app/templates/import.html`

Replace with staged import.

## `tests/`

Keep existing useful tests, but add normalized pipeline and production-like integration coverage.
Tests that expect fabricated source output must be rewritten.

## `scripts/`

Update deploy/release/smoke/backup/restore/rollback for Redis and workers.
Release gate must verify:
- web;
- DB;
- Redis;
- workers;
- Beat;
- migrations;
- queues;
- no fixture-backed active connectors;
- outbound disabled unless explicitly enabled.

---

# A13. Phased implementation order

## Phase 0 — baseline truth

- fingerprint;
- current tests;
- route matrix;
- screenshots;
- reproduce 500;
- data backup;
- production topology;
- defect register.

## Phase 1 — security and truth hotfixes

- stop admin overwrite;
- remove source fabrication;
- fix broken template routes;
- add global error pages;
- remove static connector claims;
- no production fixtures.

## Phase 2 — durable runtime

- Redis;
- Celery;
- Beat;
- job tables;
- worker health;
- persisted run state;
- replace BackgroundTasks/APScheduler.

## Phase 3 — source architecture

- connector registry;
- Companies House bulk/API;
- Sirene bulk/API;
- DECP real adapter;
- dataset snapshots;
- immutable raw records;
- source-run UI.

## Phase 4 — normalized cutover

- company universe;
- opportunity;
- evidence;
- people;
- contact routes;
- compliance;
- score;
- legacy bridge;
- backfill and parity.

## Phase 5 — qualification intelligence

- scoring V4;
- hard gates;
- gold set;
- operator review;
- data-quality queues.

## Phase 6 — frontend system

- assets;
- shell;
- component library;
- Command Center;
- Acquire;
- Qualify;
- Operations.

## Phase 7 — outreach operations

- campaigns;
- sequences;
- drafts;
- approvals;
- suppression;
- provider dry run;
- replies;
- follow-ups;
- commercial pipeline.

## Phase 8 — performance and launch

- 10,000-company benchmark;
- browser acceptance;
- accessibility;
- backup/restore;
- restart/resume;
- deployment;
- rollback;
- controlled pilot.

Do not invert this order by doing a cosmetic redesign while backend semantics remain false.

---

# A14. Acceptance evidence required from Antigravity

The final response must contain:

1. archive hash;
2. branch and commit;
3. complete file change list;
4. migration revisions;
5. current route matrix;
6. screenshot matrix;
7. test commands and outputs;
8. PostgreSQL integration results;
9. source connector states and proof;
10. evidence that fixtures cannot run in production;
11. worker topology;
12. restart/resume evidence;
13. 10,000-company benchmark;
14. dashboard metric definitions;
15. route/template contract test;
16. accessibility results;
17. backup/restore rehearsal;
18. deploy and rollback evidence;
19. known limitations;
20. credentials still required;
21. exact commands to launch the controlled pilot.

Do not claim completion if:
- any source is fixture-backed;
- any status is static;
- any long job uses FastAPI BackgroundTasks;
- APScheduler remains the production scheduler;
- new workflows still write primarily to `Prospect`;
- raw companies still populate the commercial Kanban;
- external CDNs remain required;
- the raw 500 is not reproduced and regression-tested;
- the test suite cannot run;
- 10,000-company performance is unmeasured;
- backup/restore is untested.

---

# PART B — FULL ELITE OPERATIONAL REBUILD SPECIFICATION

The following full master specification remains mandatory and supplies the deeper product, UX, data, campaign, compliance, testing, and deployment detail. Apply it after and together with Part A.



# ANTIGRAVITY MASTER EXECUTION PROMPT — PROSPECTFORGE ELITE OPERATIONAL REBUILD

**Authority:** This document is the authoritative implementation order for the next ProspectForge release. It supersedes visual styling, route behavior, status claims, page structures, and frontend assumptions in older prompts wherever they conflict. The backend acquisition-engine baseline embedded in Part II remains mandatory and is subordinate to the more specific operating and interface requirements in Part I.

**Primary objective:** Transform the current ProspectForge deployment from a visually inconsistent collection of pages and partially connected acquisition functions into a truthful, durable, high-density B2B acquisition operating system that can build a large company universe, enrich and rank opportunities, help one operator make fast decisions, and execute controlled outreach without losing provenance, compliance, or reliability.

**Do not return a design concept, static mockup, generic audit, or partial restyle. Implement the full system.**

---

# PART I — PRODUCT, UX, FRONTEND, OPERATIONS, AND INTEGRATION ORDER

# 0. Required inputs, branch, and execution behavior

Before modifying code:

1. Open the latest ProspectForge repository attached with this prompt.
2. Read this entire file before editing anything.
3. Inspect every existing route, router, template, model, migration, test, static asset, deployment script, source adapter, service, and job.
4. Run the current application locally using a production-like PostgreSQL database. Do not use SQLite as evidence of production readiness.
5. Capture baseline screenshots of every authenticated route at:
   - 1920 × 1080;
   - 1440 × 900;
   - 1280 × 800;
   - 1024 × 768.
6. Reproduce the raw `Internal Server Error` shown in the supplied screenshots. Identify the exact route, exception, query, and data condition. Fix the root cause and add a regression test.
7. Create a branch named similar to:

```text
feat/elite-operational-rebuild-v4
```

8. Create these living artifacts before implementation:

```text
acceptance/baseline-route-matrix.md
acceptance/baseline-screenshots/
acceptance/baseline-data-model.md
acceptance/baseline-runtime-topology.md
acceptance/baseline-defect-register.md
acceptance/implementation-plan.md
```

9. Do not claim that a connector, market play, worker, campaign, compliance policy, or engine is active unless the application can prove that state from current runtime data.
10. Do not fabricate records, connector health, success metrics, benchmark labels, or source output to make the interface look complete.
11. Preserve data. Use forward-compatible Alembic migrations, backfills, dual-read/dual-write where necessary, verified backups, and reversible release steps.
12. Work phase by phase, running the relevant tests after each phase. Do not postpone all testing to the end.

The final response must include exact changed files, actual command outputs, migration revisions, screenshots, benchmarks, known limitations, and remaining external credential blockers.

---

# 1. Current-state diagnosis that must be treated as release-blocking

The supplied screenshots and repository reveal a product that uses dramatic labels and oversized visual elements but does not yet provide a coherent operational workflow. Treat every issue below as a defect, not a subjective preference.

## 1.1 Visual and information-architecture defects

The current interface has these problems:

- A thick border encloses the entire viewport, making the application feel like a prototype frame instead of a professional operating system.
- The left navigation consumes significant width but provides no collapsible state, no grouped workflow hierarchy, no queue badges, and no useful environment or data-health context.
- Page titles are oversized relative to the actual information density.
- Emoji are used as primary interface icons. They are visually inconsistent across operating systems, render at unpredictable sizes, and make the application look amateur rather than operational.
- Large decorative icons dominate entire cards, including the giant map pin and giant circular arrows. They communicate less information than a compact status panel would.
- Cards and panels use excessive empty space, excessive borders, and inconsistent padding.
- The UI mixes dark surfaces with stark white table headers and white Kanban columns, causing severe contrast inconsistency and unreadable washed-out text.
- The `Pipeline Kanban` puts the whole raw database into a `New` column instead of showing only active commercial opportunities. This is conceptually wrong and operationally unusable at scale.
- The Database page claims “high-density” behavior but lacks saved views, bulk selection, column control, proper pagination, row actions, drill-down drawers, data lineage, and separate company/opportunity/contact semantics.
- Market-play cards are huge and decorative. They do not show the operational facts that matter: last run, next schedule, source health, universe size, qualified yield, contact-ready yield, errors, version change, or policy state.
- The sourcing page wastes most of the screen on an empty launch form and a giant enrichment icon. It has no durable run history, no stage progress, no partition status, no cost or volume preview, no resumability, and no connector diagnostics.
- Dashboard metrics are not decision-oriented. Labels such as `DECP Wins` under meeting conversion, `Verified Email 0.0%` under contacted, and a static `Benchmark ≥ 15%` are either misplaced, unsupported, or misleading.
- Empty states merely say “All caught up” or show blank panels. They do not explain why the queue is empty, whether the pipeline is healthy, or what action should be taken next.
- The raw `Internal Server Error` screen exposes a broken failure experience with no request ID, recovery path, navigation, or operator guidance.
- The Import page contains stale schema vocabulary and presents a simplistic upload box instead of a staged, auditable import process.
- There is no global command palette, keyboard navigation, contextual help, notification center, run status indicator, or clear definition of system scope.
- The interface repeats aspirational phrases such as `Level 300`, `UK/FR ENGINE LIVE`, and `Companies House: Active` rather than proving capability through real status data.

## 1.2 Frontend implementation defects

The current code also contains technical problems that must be corrected:

- `app/templates/base.html` loads Tailwind from a CDN while the repository also contains a compiled Tailwind asset. Production must have one deterministic asset pipeline, not two competing systems.
- Google Fonts and Alpine are loaded from external CDNs. Production must not depend on third-party frontend CDNs for core rendering or behavior.
- Tailwind configuration and a large set of visual rules are embedded inline in the base template. Move design tokens and components into versioned source files.
- `app/static/css/input.css` still contains an older light component system while `app/static/css/app.css` uses broad `!important` overrides. This is why pages become visually inconsistent. Replace the conflict with a single token-based component layer.
- `app.js` intercepts nearly every POST form and rewrites the whole document with `document.write`. This is fragile, damages progressive enhancement, weakens error handling, and makes redirect behavior difficult to reason about.
- `kanban.js` performs a mutation through `fetch` without consistently attaching the shared CSRF token and uses `alert()` as its failure UI.
- Page-specific scripts are embedded directly inside templates. Replace them with small, tested modules and shared interaction primitives.
- There is no global error boundary for HTMX or fetch requests, no standardized toast system, no retry action, and no correlation/request ID display.
- Static claims in templates are not connected to connector-health or worker-health records.
- The UI is still primarily bound to the legacy flat `Prospect` record instead of the normalized company, opportunity, evidence, person, contact, source-run, and campaign models.

## 1.3 Backend and operational defects visible through the UI

The interface exposes deeper backend problems:

- Long ingestion and enrichment work is launched with FastAPI `BackgroundTasks` and an in-process APScheduler. This is not durable. Work can disappear during restart, deployment, process crash, or timeout.
- Source-run progress is not a first-class durable model with stage checkpoints, leases, partition progress, retry history, dead-letter state, and cancellation.
- The normalized multi-market schema exists but is not the authoritative operational read/write path.
- Several adapters still contain `pass`, fixture modes, fabricated example behavior, or health checks that do not prove real data retrieval.
- The Companies House connector can report fixture operation when credentials are absent. Production must show `credential_blocked`, never fabricated success.
- Bootstrap logic updates the admin password on every application start. Startup must never silently overwrite an existing operator credential.
- Dashboard counts and list queries are built around the legacy prospect table rather than intentional universe, opportunity, qualification, contact, and outreach stages.
- The application lacks truthful system-health, queue-health, source-freshness, and data-quality reporting.
- There is no proper campaign execution lifecycle, reply ingestion, bounce processing, suppression enforcement, or provider reconciliation.
- Large-data behavior is not proven. A 10,000-company universe must not be loaded into memory or rendered as an unpaginated list.

All of these are mandatory correction targets.

---

# 2. Product mission and exact business use case

ProspectForge is not a generic CRM and not a visual dashboard for vanity counts. It is an internal acquisition operating system for a founder selling field-operations software, integration, automation, and rescue work to UK and French service businesses.

The system must turn broad official and commercial company data into a small, defensible set of companies worth contacting.

The target funnel is:

```text
Official company universe
    → ICP-eligible companies
    → company identity resolved
    → official domain verified
    → operational evidence collected
    → opportunity created for a market play
    → buyer role identified
    → contact route verified
    → compliance and suppression passed
    → human qualification accepted
    → evidence-bound message approved
    → controlled outreach executed
    → reply classified
    → meeting, proposal, win, loss, or nurture outcome
```

The platform must support two operating modes:

1. **Acquisition factory mode** — scheduled, durable creation and enrichment of the company universe.
2. **Operator decision mode** — a high-speed daily workspace where one human can review, approve, contact, and progress the best opportunities.

The system succeeds only if it improves these commercial outputs:

- verified companies in the target market;
- qualified opportunities with defensible evidence;
- current buyers and usable contact routes;
- review throughput per operator hour;
- approved messages with no unsupported claims;
- positive replies;
- meetings;
- paid mapping sprints or projects;
- learning about which cohorts and messages work.

Do not optimize the product around decorative dashboards or total record count alone.

---

# 3. Operating doctrine and non-negotiable product rules

## 3.1 Truth before spectacle

- Remove the phrase `Level 300` from visible production UI.
- Remove static `ENGINE LIVE`, `ACTIVE`, `COMPLIANT`, `HEALTHY`, and similar claims.
- Status must be computed from real records and include a timestamp.
- When a connector has no credentials, display `Credential required`.
- When the last successful fetch is stale, display `Stale`.
- When a worker is unavailable, display `Worker offline`.
- When a source returns zero records, distinguish `valid empty result` from `failed query`.
- When a metric has no denominator, display `—`, not `0.0%`.
- Never show a benchmark unless its source, cohort definition, and minimum sample size are configured.

## 3.2 Dense, calm, operational interface

The design must feel like a premium internal control system: calm, precise, fast, and information-rich. Avoid cyberpunk styling, constant glow, excessive gradients, glassmorphism everywhere, giant icons, and visual noise.

The operator must be able to answer, within ten seconds:

- What should I do next?
- Which acquisition run is active or blocked?
- How much usable data did each source produce?
- Which opportunities are ready for review?
- Which contacts are safe and useful?
- Which messages need approval?
- What requires follow-up today?
- Are workers, sources, sending, and data freshness healthy?
- Which cohort is producing meetings?

## 3.3 Human control at commercial boundaries

Automation may discover, normalize, enrich, score, draft, and queue. It must not:

- auto-send guessed contacts;
- auto-contact suppressed recipients;
- auto-approve unsupported claims;
- silently override a human rejection;
- bypass jurisdiction policy;
- fabricate buyer identities;
- scrape or automate LinkedIn;
- retry dangerous sending actions without idempotency.

## 3.4 One source of truth

- `Company` is the legal/operational entity.
- `Opportunity` is a company evaluated against one versioned market play.
- `Person` and `PersonRole` represent current professional identities.
- `ContactPoint` represents a source-backed route.
- `EvidenceItem` represents one claim with provenance.
- `QualificationReview` represents a human decision.
- `CampaignMembership` represents outreach participation.
- `Task` represents a required operator action.

Do not continue using one flat `Prospect` row to represent all of these concepts. The legacy table may temporarily serve as a compatibility projection during migration only.

---

# 4. Target information architecture

Replace the current flat navigation with workflow groups. Use a persistent left sidebar on desktop, collapsible to icon rail, and a drawer on small screens.

## 4.1 Primary navigation

```text
COMMAND
  Command Center
  My Work

ACQUIRE
  Market Plays
  Source Runs
  Company Universe
  Imports

QUALIFY
  Opportunity Review
  Buyer & Contact Review
  Evidence Review

OUTREACH
  Campaigns
  Draft Approval
  Replies
  Follow-ups
  Commercial Pipeline

OPERATIONS
  Connectors
  Data Quality
  Jobs & Workers
  Suppression
  Audit Log
  Settings
```

Do not show every page as an equally important top-level link. Group by operator workflow.

## 4.2 Global top bar

Every authenticated page must include:

- breadcrumbs;
- current page title, compact rather than oversized;
- active market-play scope selector;
- date-range selector where metrics are shown;
- global search;
- command palette trigger with `⌘/Ctrl + K`;
- notification and blocker count;
- system-health indicator derived from runtime state;
- operator menu.

## 4.3 Global command palette

Implement a keyboard-driven command palette that can:

- search companies, opportunities, people, contacts, campaigns, and runs;
- navigate to any page;
- start a safe source-run wizard;
- open today’s review queue;
- create a manual company or task;
- pause all sending;
- open worker health;
- export the current saved view.

The command palette must respect permissions and hide dangerous actions when prerequisites are not met.

## 4.4 Global status model

Display status with one shared component and vocabulary:

- `Healthy`
- `Running`
- `Degraded`
- `Blocked`
- `Stale`
- `Paused`
- `Disabled`
- `Unknown`

Every status badge must provide a tooltip or detail popover containing:

- reason;
- last checked time;
- relevant run or connector;
- remediation action.

---

# 5. Visual design system

## 5.1 Design direction

Use a restrained premium dark theme suitable for long operational sessions. The platform must look closer to Linear, modern cloud operations tools, and high-quality B2B data products than to a gaming dashboard.

The design must not copy any product directly. Use the following characteristics:

- near-black neutral canvas;
- slightly elevated neutral surfaces;
- one primary violet accent;
- cyan only for information and source activity;
- green only for verified success;
- amber only for warnings or review;
- red only for failure, suppression, or destructive action;
- minimal gradients;
- minimal glow;
- crisp 1px borders;
- compact typography;
- consistent 8px spacing grid;
- restrained rounded corners;
- precise icons from one icon family;
- high-density tables and forms;
- generous whitespace only where it improves comprehension.

## 5.2 Required color tokens

Implement CSS variables and Tailwind aliases. Exact values may be adjusted slightly after contrast testing, but use this hierarchy:

```css
--pf-bg-canvas: #0a0d12;
--pf-bg-sidebar: #0d1118;
--pf-bg-surface: #111720;
--pf-bg-elevated: #171e29;
--pf-bg-subtle: #1c2431;
--pf-border-subtle: #263142;
--pf-border-strong: #354258;
--pf-text-primary: #f5f7fb;
--pf-text-secondary: #a8b1c2;
--pf-text-muted: #707b8f;
--pf-accent: #7c5cff;
--pf-accent-hover: #8c70ff;
--pf-accent-soft: rgba(124, 92, 255, 0.14);
--pf-info: #3fbfd1;
--pf-success: #2fc28b;
--pf-warning: #e6ad45;
--pf-danger: #ed6571;
--pf-focus: #9d88ff;
```

Do not use pure white panels on dark pages. Do not use orange progress bars for neutral scores. Color must communicate semantics.

## 5.3 Typography

- Use a locally bundled variable sans font or a robust system stack. Do not fetch Google Fonts at runtime.
- Use one sans family for all interface text and one mono family only for identifiers, timestamps, codes, and logs.
- Page title: 24–28px desktop, 22–24px tablet.
- Section title: 16–18px.
- Card title: 14–15px.
- Body: 13–14px.
- Table: 12.5–13px.
- Label: 11–12px.
- Avoid all-caps except short metadata labels.
- Use consistent line heights and no oversized decorative headlines.

## 5.4 Iconography

- Remove all emoji from navigation, buttons, headings, cards, empty states, and company rows.
- Use one locally bundled icon system, preferably Lucide, with 16px and 18px defaults.
- Large empty-state icons may be 32–40px maximum.
- Flags may appear as small country indicators, not giant illustrations.
- Icons must have accessible labels where meaning is not obvious.

## 5.5 Layout metrics

Desktop:

```text
Expanded sidebar: 248px
Collapsed sidebar: 72px
Top bar: 56–64px
Content gutter: 24px at 1280, 32px at 1440+
Default card radius: 10px
Modal radius: 12px
Table row: 44–48px
Control height: 34–38px
Primary button height: 36–40px
```

- Remove the full-viewport frame border.
- Allow data pages to use the full remaining width.
- Constrain text-heavy settings pages to a readable content width.
- Use sticky headers and sticky filter bars where useful.

## 5.6 Surface and elevation rules

- Base panels use flat surfaces and a subtle border.
- Use shadows only for overlays, menus, drawers, and modals.
- Do not apply glass blur to every panel.
- Do not animate every status indicator.
- Use an animated pulse only for genuinely live running work and respect reduced-motion preferences.

## 5.7 Component library

Create reusable Jinja macros/partials and style primitives for:

- app shell;
- nav group and nav item;
- breadcrumb;
- page header;
- button variants;
- icon button;
- status badge;
- score badge;
- country badge;
- source badge;
- metric card;
- mini trend;
- progress bar;
- data table;
- filter chip;
- saved-view selector;
- tabs;
- side drawer;
- modal;
- command palette;
- toast;
- inline alert;
- empty state;
- skeleton;
- error state;
- form field;
- select/combobox;
- date range;
- pagination;
- activity timeline;
- evidence card;
- contact confidence indicator;
- job-stage timeline;
- log viewer;
- confirmation dialog.

No page may invent its own unrelated button, badge, or card design.

---

# 6. Application shell and responsive behavior

## 6.1 Sidebar

The sidebar must:

- support expanded and collapsed states persisted per user;
- group navigation by workflow;
- show queue counts only when nonzero;
- show active route and parent group;
- include a compact product mark, not a large logo block;
- place operator/account controls at the bottom;
- show environment (`Production`, `Staging`, `Local`) and release version;
- never claim engine health from static text;
- become a drawer under 1024px;
- remain keyboard navigable.

## 6.2 Top bar

The top bar must remain visible during long table scrolling. It must not duplicate the sidebar. Keep global search, play scope, notifications, health, and account actions there.

## 6.3 Content state

Every page must implement:

- initial loading state;
- successful data state;
- valid empty state;
- partial/degraded state;
- permission-denied state;
- recoverable error state;
- fatal error state with request ID.

Never render a blank large panel when data is missing.

## 6.4 Responsive priorities

ProspectForge is desktop-first but must remain usable on a laptop and tablet:

- 1920 and 1440: full navigation and multi-column workspaces;
- 1280: compact sidebar and reduced secondary columns;
- 1024: collapsible navigation and drawers;
- below 768: read/review functions remain usable, complex table configuration may switch to cards.

No horizontal viewport overflow is allowed. Wide data tables may scroll within their own container with sticky key columns.

---

# 7. Exact page-by-page product specification

# 7.1 Command Center

Replace the current dashboard with a decision-oriented command center.

## Header

Show:

- title: `Command Center`;
- active play or `All active plays`;
- selected period;
- last refreshed time;
- one primary action: `Start acquisition run`;
- secondary actions inside a menu, not three oversized hero buttons.

The primary action must open a scoped wizard, not launch work immediately.

## Section A — Today’s priorities

Use compact actionable cards:

- opportunities awaiting qualification;
- contacts awaiting review;
- drafts awaiting approval;
- overdue follow-ups;
- failed or blocked jobs;
- replies needing classification.

Each card must include:

- count;
- oldest age;
- priority breakdown;
- one direct action;
- reason when zero.

## Section B — Acquisition funnel

Show the real period and cohort funnel:

```text
Universe → ICP eligible → Domain verified → Evidence enriched → Human accepted → Contact ready → In outreach → Positive reply → Meeting → Proposal → Won
```

Requirements:

- absolute count;
- conversion from previous step;
- conversion from universe;
- delta versus previous comparable period;
- tooltip defining each stage;
- no percentage when denominator is zero;
- filter by play, country, source, cohort, and period.

## Section C — Pipeline throughput and quality

Show:

- companies imported per day;
- opportunities created per day;
- qualification acceptance rate;
- contact-ready yield;
- duplicate rate;
- domain verification rate;
- evidence coverage;
- stale-data count.

Do not mix outreach conversion with source quality.

## Section D — Active and recent runs

Compact table:

- run ID;
- market play;
- connector;
- stage;
- progress;
- discovered/normalized/rejected;
- started duration;
- status;
- operator action.

Clicking a run opens the Run Inspector drawer or page.

## Section E — Outreach outcomes

Show only when there is a meaningful sample:

- sent;
- delivered;
- bounced;
- replies;
- positive replies;
- meetings;
- proposals;
- won value;
- cohort and template variant.

Do not show a static `15% benchmark` without configured evidence. If sample size is below the configured threshold, display `Insufficient sample`.

## Section F — System health

Display truthful summaries of:

- web application;
- database;
- Redis;
- worker pool;
- scheduler;
- source freshness;
- mail provider;
- backups;
- last deployment.

A click opens Operations.

## Empty state

A fresh installation must show a guided checklist:

1. configure a market play;
2. enable a real connector;
3. validate credentials;
4. run a dry-run acquisition;
5. review the first cohort;
6. configure controlled outreach.

Never fill the page with zeros and giant blank cards.

---

# 7.2 My Work

Replace disconnected `Daily Queue` and `Follow-ups` behavior with a coherent operator task workspace.

Tabs:

- Today;
- Overdue;
- Upcoming;
- Waiting;
- Completed.

Task categories:

- qualification;
- evidence review;
- buyer review;
- contact review;
- draft approval;
- reply classification;
- follow-up;
- source/run remediation;
- manual research.

Each row shows:

- task;
- company/opportunity;
- play;
- priority;
- due time;
- age;
- reason;
- next action.

Support keyboard shortcuts:

- `j/k` next/previous;
- `enter` open;
- `a` accept where appropriate;
- `r` reject or research;
- `p` park;
- `c` complete;
- `s` snooze.

The raw `Internal Server Error` route must be fixed and covered by an authenticated route smoke test.

---

# 7.3 Market Plays

The current giant market-play cards must be replaced with a compact operational index and a detailed configuration workspace.

## Index view

Columns/cards must show:

- name and version;
- jurisdiction and locale;
- lifecycle state: draft, pilot, active, paused, retired;
- target sectors and size range;
- enabled connectors;
- schedule;
- last successful run;
- next scheduled run;
- company universe count;
- opportunity count;
- accepted count;
- contact-ready count;
- current blockers;
- owner/operator.

Actions:

- open;
- run discovery;
- clone to draft;
- pause;
- compare version;
- retire.

Do not place a giant location pin or flags as the dominant visual element.

## Detail workspace tabs

### Overview

- commercial objective;
- offer mapping;
- current health;
- funnel;
- recent runs;
- active experiments.

### ICP

- legal forms;
- classifications;
- geography;
- size bands;
- field-team estimates;
- inclusion keywords;
- exclusion conditions;
- target buyer roles.

### Sources

- enabled source adapters;
- query strategy;
- source priority;
- rate/cost budget;
- freshness SLA;
- last run and yield.

### Evidence and scoring

- evidence taxonomy;
- hard gates;
- score weights;
- thresholds;
- versioned calibration notes.

### Compliance

- jurisdiction policy;
- entity-type eligibility;
- required disclosure;
- retention;
- suppression behavior;
- policy version.

### Messaging

- offer;
- approved claims;
- disallowed claims;
- templates;
- language;
- sequence.

### Schedule

- discovery cadence;
- refresh cadence;
- enrichment cadence;
- contact reverification cadence.

### Change history

- immutable versions;
- author;
- diff;
- activation time;
- rollback action.

## Launch sourcing wizard

The `Run discovery` action must open a wizard with:

1. play and exact version;
2. connector selection;
3. scope/partition;
4. dry-run or commit mode;
5. estimated volume, API calls, time, and cost;
6. duplicate and refresh policy;
7. contact waterfall toggle with warning;
8. maximum caps;
9. validation summary;
10. explicit confirmation.

Never launch a source run from one unqualified button click.

---

# 7.4 Source Runs and Acquisition Cockpit

Replace the current sourcing screen with a true run-management workspace.

## Tabs

- Runs;
- Connectors;
- Schedules;
- Queue;
- Dead letters.

## Runs table

Columns:

- run ID;
- play version;
- source connector;
- mode;
- partition;
- requested by;
- started;
- duration;
- current stage;
- progress;
- discovered;
- normalized;
- matched;
- rejected;
- errors;
- cost/API calls;
- state.

Filters:

- status;
- play;
- connector;
- date;
- operator;
- has errors;
- dry run/commit.

## Run Inspector

Show a stage timeline:

```text
Queued → Fetching → Raw capture → Normalization → Identity resolution → Deduplication → Play filtering → Opportunity creation → Domain discovery → Evidence enrichment → Buyer/contact → Scoring → Complete
```

For each stage show:

- state;
- start/end;
- duration;
- processed/total;
- throughput;
- retry count;
- errors;
- checkpoint;
- worker;
- logs.

Actions based on state:

- cancel safely;
- pause;
- resume from checkpoint;
- retry failed partition;
- download errors;
- inspect raw source records;
- clone run configuration;
- archive.

## Connector cards

Compact status, no giant icon:

- connector name and version;
- countries;
- enabled state;
- credential state;
- current rate budget;
- last health check;
- last successful fetch;
- last yield;
- failure rate;
- freshness;
- documentation/action.

A connector is `Healthy` only when a real authenticated or public request has succeeded within the configured freshness window and returned a valid schema.

## Bulk enrichment

Do not provide a generic `Enrich 25` box. Implement a scoped bulk action:

- current saved view or explicit IDs;
- enrichment stages to run;
- budget and cap;
- skip fresh data;
- dry-run preview;
- queue as a durable job;
- live progress;
- result summary.

---

# 7.5 Company Universe

Rename `Prospect Database` to `Company Universe`. A company in the universe is not automatically a prospect or outreach candidate.

## Table requirements

Use server-side filtering, sorting, and cursor pagination. The table must remain fast with at least 10,000 companies and 100,000 source records.

Default columns:

- selection;
- company;
- country;
- legal identifier;
- legal status;
- primary classification;
- size/field-team estimate;
- location;
- verified domain;
- active opportunities;
- data quality;
- freshness;
- last source;
- updated.

Optional columns:

- employee band;
- field-team range;
- public-award count;
- website technology;
- buyer count;
- contact count;
- suppression;
- source count;
- duplicate confidence.

Features:

- saved views;
- column chooser;
- reorder and resize columns;
- compact/comfortable density;
- sticky header;
- sticky company column;
- keyboard row navigation;
- multi-select;
- bulk actions;
- export current view;
- share/copy filtered URL;
- query token/chip filter builder;
- clear active filter summary.

## Bulk actions

- evaluate against market play;
- queue domain verification;
- queue evidence enrichment;
- refresh official record;
- merge duplicates;
- suppress;
- export;
- add to manual research list.

Every bulk action must show scope, count, side effects, and confirmation.

## Company quick drawer

Clicking a row opens a right-side drawer without losing the table state. Show:

- legal identity;
- verified domain;
- classifications;
- locations;
- field-team estimate;
- source freshness;
- active opportunities;
- top evidence;
- people/contact summary;
- open full workspace.

---

# 7.6 Opportunity Explorer

Create a separate opportunity list. Do not overload the company universe with commercial readiness.

Default columns:

- company;
- play;
- opportunity score;
- hard-gate state;
- ICP fit;
- pain/evidence;
- trigger;
- buyer;
- contact route;
- compliance;
- review state;
- next action;
- age.

Saved views:

- high-fit, missing evidence;
- evidence-ready, missing buyer;
- buyer-ready, missing contact;
- contact-ready, awaiting human approval;
- approved, awaiting draft;
- stale and needs refresh;
- blocked by compliance;
- rejected this week.

Scores must be explainable. Hovering or opening a score shows components, evidence, gates, version, and timestamp.

---

# 7.7 Opportunity and Company Intelligence Workspace

Replace the current generic prospect detail page with an integrated workspace.

## Header

Show:

- company legal/trading name;
- country and identifiers;
- verified domain;
- play and version;
- readiness state;
- score and confidence;
- owner;
- last refresh;
- suppression/compliance warning;
- primary next action.

Actions:

- accept/reject/park/research;
- run scoped enrichment;
- approve contact;
- generate draft;
- add to campaign;
- create task;
- suppress;
- merge duplicate.

Dangerous actions must be in an overflow menu and require confirmation.

## Workspace layout

Use a responsive two-column layout:

- main content 65–72%;
- action/context rail 28–35%;

Avoid three narrow unreadable columns.

## Main tabs

### Summary

- why this company fits;
- why now;
- operational complexity;
- recommended offer;
- top verified evidence;
- missing requirements;
- decision history.

### Evidence

Each evidence item shows:

- category and code;
- concise claim;
- quoted/extracted text where legally and technically appropriate;
- source URL and source type;
- observed time;
- freshness/expiry;
- confidence;
- verification state;
- contradiction links;
- use in scoring;
- use in draft claims.

Support confirm, reject, mark stale, and request refresh.

### People and contacts

Separate people from contact routes. Show:

- full name;
- current title;
- normalized buyer category;
- company-match confidence;
- source count;
- current-role validation;
- contacts linked to that person;
- publication/deliverability/utility states;
- manual confirmation.

Never present a guessed pattern as a verified personal email.

### Company data

- identifiers;
- classifications;
- locations;
- domains;
- official records;
- estimates;
- source records;
- duplicates/merge history.

### Activity

Unified timeline:

- source updates;
- evidence changes;
- review decisions;
- contact verification;
- tasks;
- drafts;
- outreach;
- replies;
- meetings;
- stage changes;
- audit actions.

### Raw and audit

For advanced use:

- source payload links;
- transformation lineage;
- model versions;
- policy decision trace;
- score snapshots;
- request/run IDs.

## Context rail

Show:

- hard gates with pass/fail reasons;
- buyer recommendation;
- primary contact state;
- compliance decision;
- open tasks;
- current campaign membership;
- next best action.

---

# 7.8 Qualification Review

Create a fast, keyboard-driven review queue rather than forcing the operator to open random detail pages.

## Queue construction

The backend must rank review items using:

- opportunity score;
- hard-gate proximity;
- evidence completeness;
- freshness;
- expected value;
- age;
- operator SLA;
- active campaign demand.

## Review workspace

Show one opportunity at a time with:

- company summary;
- verified identity;
- top evidence;
- suspected pain and why-now hypothesis;
- missing or contradictory evidence;
- recommended buyer;
- contact state;
- policy state;
- score explanation;
- source links.

Actions:

- Accept;
- Reject;
- Research more;
- Park;
- Suppress.

Require structured reason codes and optional notes. Record reviewer, time, play version, score version, and evidence snapshot.

Support undo for a short safe window, but preserve audit history.

---

# 7.9 Buyer and Contact Review

This queue handles identities and routes independently of opportunity fit.

Show:

- company and play;
- recommended buyer role;
- candidate people;
- company-match evidence;
- current-role evidence;
- contact candidates;
- publication state;
- deliverability state;
- policy utility;
- suppression result.

Actions:

- select primary person;
- confirm current role;
- approve role mailbox;
- approve generic contact route;
- reject conflicting identity;
- request refresh;
- manually add source-backed contact;
- mark no safe contact.

Do not allow a `contact_ready` state until required human and policy gates pass.

---

# 7.10 Evidence Review

Provide a queue for low-confidence, contradictory, stale, or message-critical evidence.

Capabilities:

- compare extracted claim with source context;
- open the source safely;
- confirm/reject/edit normalized label without altering raw evidence;
- mark stale;
- link contradiction;
- prevent rejected evidence from returning without a new source version;
- show which scores and drafts would change.

---

# 7.11 Campaigns

Build a real campaign workspace. A campaign is not a Kanban column.

## Campaign index

Show:

- name;
- market play/cohort;
- state;
- owner;
- members;
- approved;
- active;
- paused;
- delivered;
- bounced;
- replies;
- positive replies;
- meetings;
- next send window;
- health blockers.

## Campaign builder

Steps:

1. objective and owner;
2. market play and saved audience view;
3. eligibility preview;
4. sequence version;
5. sender identity;
6. daily and domain caps;
7. send windows/time zones;
8. suppression and compliance validation;
9. draft-generation policy;
10. approval mode;
11. dry-run preview;
12. activation confirmation.

Show exactly how many records are excluded and why.

## Campaign detail tabs

- Overview;
- Audience;
- Drafts;
- Sequence;
- Sending;
- Replies;
- Experiments;
- Audit.

## Safety

- default state is draft;
- sending remains paused until sender checks pass;
- one global emergency pause;
- stop on reply, bounce, opt-out, meeting, manual pause, suppression, or policy invalidation;
- no automatic LinkedIn activity;
- no guessed contact send;
- idempotent provider calls.

---

# 7.12 Draft Approval

Create a queue of evidence-bound messages.

For each draft show:

- recipient and contact utility state;
- company;
- play;
- sequence step;
- subject and body;
- claims highlighted;
- evidence linked to each claim;
- prohibited/unsupported claim warnings;
- personalization quality;
- policy disclosure;
- sender preview;
- previous touch context.

Actions:

- approve;
- edit and approve;
- reject;
- regenerate from selected evidence;
- park;
- open opportunity.

Approved drafts must become immutable versions. Later edits create a new version and invalidate prior approval.

---

# 7.13 Replies

Build a reply inbox connected to provider events.

Classifications:

- positive interest;
- referral;
- question;
- not now;
- not relevant;
- already solved;
- wrong person;
- objection;
- unsubscribe/opt-out;
- automated reply;
- bounce;
- spam complaint;
- ambiguous.

The system may suggest classification but a human confirms material outcomes. Opt-outs and complaints must apply suppression immediately.

Show:

- conversation thread;
- company and opportunity context;
- sequence history;
- suggested classification;
- next-action recommendation;
- reply SLA;
- create task or meeting outcome.

---

# 7.14 Follow-ups

Follow-ups are tasks generated from conversations, sequences, and operator decisions. The page must show overdue/today/upcoming and support snooze, completion, reassignment, and context.

Do not show an empty large screen with only `All caught up`. When empty, show:

- why no follow-ups exist;
- active campaign state;
- next scheduled send or task;
- action to review replies or opportunity queue.

---

# 7.15 Commercial Pipeline

The current Kanban is conceptually incorrect because it puts hundreds of raw records into `New`.

Only show commercially active opportunities. Recommended stages:

```text
Qualified
Draft ready
In outreach
Positive reply
Meeting scheduled
Diagnostic/Mapping Sprint
Proposal
Negotiation
Won
Lost
Nurture
```

Requirements:

- maximum card density appropriate for active deals;
- dark readable columns, not white panels;
- compact cards with company, value band, buyer, next action, age, owner, and blocker;
- drag-and-drop only for valid transitions;
- server validates state-machine rules;
- keyboard-accessible alternative to drag-and-drop;
- WIP counts and aging indicators;
- lost/nurture not always visible as full-width columns;
- list view alternative;
- no raw source or unqualified company appears here.

---

# 7.16 Imports

Replace the simple CSV box with a staged import workspace.

## Five-step flow

1. **Upload** — file, provider/source, jurisdiction, play, purpose.
2. **Map** — map columns to normalized fields using saved provider profiles.
3. **Validate** — schema, type, identifiers, domains, emails, legal forms, required source/provenance.
4. **Preview and resolve** — duplicates, conflicts, invalid rows, suppression, policy risks.
5. **Commit as durable job** — progress, result summary, quarantine and downloadable error report.

Requirements:

- streaming upload, not loading whole large file into memory;
- file-size and row limits configurable;
- CSV injection protection on export/import;
- encoding detection and explicit override;
- delimiter detection;
- provider profile support;
- source and collection date mandatory;
- no stale `BOAMP/MOROCCO_OPS` schema as default;
- import creates source records and lineage, not direct opaque prospect rows;
- bad rows go to quarantine;
- import can be resumed safely;
- full audit history.

---

# 7.17 Connectors

Provide an operations page for every source and delivery connector.

Show:

- type;
- version;
- countries;
- credential state;
- enabled state;
- health;
- rate limit;
- current budget usage;
- last run;
- last successful data;
- schema version;
- recent errors;
- owner;
- documentation.

Actions:

- validate credentials;
- test request;
- enable/disable;
- rotate secret through secure settings;
- edit budget;
- inspect runs;
- view raw response in a redacted manner.

No production fixture mode is allowed.

---

# 7.18 Data Quality

Build a first-class data quality center.

Metrics and queues:

- unresolved identities;
- duplicate candidates;
- conflicting identifiers;
- unverified domains;
- stale domains;
- missing classifications;
- missing locations;
- stale evidence;
- contradictions;
- people without current-role confirmation;
- contacts requiring review;
- invalid or bounced contacts;
- opportunities with score/evidence mismatch;
- legacy records not migrated.

Every metric opens a repair queue or run action.

---

# 7.19 Jobs and Workers

Show:

- worker instances;
- heartbeat;
- active jobs;
- queue depth;
- oldest queued age;
- throughput;
- retries;
- dead letters;
- scheduled jobs;
- Redis state;
- database connection health.

Support safe actions:

- pause queue;
- resume;
- retry dead-letter item;
- cancel job;
- drain worker;
- inspect logs.

Do not expose secret values.

---

# 7.20 Suppression

Support email, domain, company identifier, person, and campaign-level suppression.

Show:

- normalized value;
- scope;
- reason;
- source;
- created by;
- created time;
- related reply/event;
- expiration where applicable.

Opt-out suppression cannot be removed casually. Require a privileged explicit action and audit note for any permitted override.

---

# 7.21 Audit Log

Immutable operator and system events:

- authentication;
- configuration changes;
- market-play activation;
- source run creation/cancellation;
- identity merges;
- review decisions;
- contact approvals;
- campaign activation/pause;
- draft approval;
- send/provider event;
- suppression;
- export;
- setting change;
- deployment/release.

Filters and export must be available to the administrator.

---

# 7.22 Settings

Sections:

- operator account;
- environment and release;
- market defaults;
- source credentials;
- sending provider;
- sender domains;
- compliance policies;
- retention;
- notification rules;
- task SLAs;
- feature flags;
- backups;
- advanced diagnostics.

Do not let application startup overwrite an existing password. Implement explicit password change and bootstrap-only first-user creation.

---

# 8. Interaction and state behavior

## 8.1 Safe actions

Use three levels:

- immediate reversible action;
- confirmation-required action;
- typed-confirmation destructive action.

Launching a run, activating a campaign, bulk suppressing, merging companies, deleting data, and changing active play versions require confirmation appropriate to risk.

## 8.2 Loading

- Use skeletons for first load.
- Use inline progress for local mutations.
- Use durable job progress for long work.
- Disable only the affected control, not the whole page.
- Show queueing explicitly.
- Never leave a button appearing clickable while a duplicate job is already active.

## 8.3 Toasts and errors

Implement a shared toast and alert system:

- success;
- info;
- warning;
- error.

Errors must include:

- human-readable summary;
- request/job ID;
- retry when safe;
- link to details or logs;
- no raw stack trace to the browser.

## 8.4 Empty states

Every empty state must distinguish:

- no data has ever been created;
- filters exclude all data;
- data is still processing;
- source is blocked;
- system is unhealthy;
- genuine completion.

Provide the single most appropriate next action.

## 8.5 Forms

- Validate client- and server-side.
- Preserve entered data on validation errors.
- Use inline field errors and a summary.
- Display units, allowed values, and consequences.
- Use comboboxes for large reference lists.
- Do not use native number spinners for important volume controls without bounds and context.

## 8.6 Accessibility

Meet WCAG 2.2 AA for core flows:

- visible focus;
- keyboard navigation;
- semantic headings;
- labels;
- error association;
- sufficient contrast;
- reduced-motion support;
- screen-reader descriptions for status and charts;
- non-drag alternative for Kanban transitions.

---

# 9. Frontend implementation architecture

Keep the existing FastAPI + Jinja2 + HTMX architecture unless a measured requirement proves it cannot meet the use case. Do not perform a risky React rewrite merely for appearance.

## 9.1 Asset pipeline

- Remove Tailwind CDN from production.
- Remove Google Fonts runtime dependency.
- Add Alpine as a pinned local package if it remains necessary.
- Add a pinned local Lucide icon package or vendor a deterministic icon sprite.
- Add any chart library as a pinned local asset; prefer a lightweight library or server-generated SVG for simple charts.
- Build and minify assets during CI/release.
- Add content hashes or version query strings for cache invalidation.
- Set a restrictive Content Security Policy compatible with local assets.
- Remove inline Tailwind configuration and inline style blocks from base template.

## 9.2 Template structure

Create:

```text
app/templates/layouts/app.html
app/templates/layouts/auth.html
app/templates/components/
app/templates/pages/command/
app/templates/pages/acquire/
app/templates/pages/qualify/
app/templates/pages/outreach/
app/templates/pages/operations/
app/templates/partials/
```

Use Jinja macros for shared components. Keep route templates small and declarative.

## 9.3 JavaScript structure

Replace global ad hoc scripts with modules:

```text
app/static/js/core/csrf.js
app/static/js/core/http.js
app/static/js/core/toast.js
app/static/js/core/dialog.js
app/static/js/core/command-palette.js
app/static/js/core/shortcuts.js
app/static/js/features/data-table.js
app/static/js/features/run-progress.js
app/static/js/features/review-queue.js
app/static/js/features/pipeline.js
app/static/js/features/import-wizard.js
app/static/js/features/draft-review.js
```

Rules:

- No `document.write`.
- No browser `alert()` or `confirm()` for primary flows.
- All mutation requests include CSRF.
- Fetch/HTMX errors use shared handling.
- Long-running progress uses polling with backoff or server-sent events; it must survive page reload.
- Browser state such as filters and table view must be encoded in URL or persisted intentionally.

## 9.4 HTMX contracts

- Return partials only when `HX-Request` is present.
- Return full pages for normal navigation.
- Use `HX-Trigger` for toasts and count refreshes.
- Use proper HTTP status codes.
- Preserve focus after partial updates.
- Add `hx-disabled-elt` and request indicators.
- Do not replace the full document for routine mutations.

## 9.5 Charts

Charts must support decisions, not decoration. Provide accessible tables or summaries. Use consistent semantic colors. Avoid 3D charts, gauges, or large doughnut charts for simple counts.

---

# 10. Backend architecture and authoritative data cutover

## 10.1 Runtime topology

Production target:

```text
Caddy/reverse proxy
    → FastAPI web service
    → PostgreSQL
    → Redis
    → Celery worker pool
    → Celery Beat scheduler
    → durable file/object storage for raw bulk data and exports
```

Separate web request handling from long-running acquisition work.

## 10.2 Remove non-durable execution

- Do not use FastAPI `BackgroundTasks` for ingestion, bulk enrichment, imports, contact discovery, exports, or campaign sends.
- Do not use in-process APScheduler as the production scheduler.
- Convert long work into durable jobs with idempotency, checkpoints, retries, cancellation, and progress events.
- A deployment or web-process restart must not lose queued work.

## 10.3 Normalized source of truth

The existing normalized schema is incomplete in execution. Complete and use it.

Required authoritative objects:

```text
companies
company_identifiers
company_names
company_classifications
company_locations
company_domains
company_estimates
source_connectors
source_runs
source_records
market_plays
market_play_versions
opportunities
evidence_items
evidence_relations
people
person_roles
contact_points
contact_verification_events
contact_manual_reviews
compliance_policies
compliance_decisions
qualification_reviews
score_snapshots
campaigns
sequence_versions
sequence_steps
campaign_memberships
message_drafts
touches
provider_events
conversation_events
tasks
suppression_entries
job_runs
job_steps
job_events
dead_letters
audit_events
```

Use the legacy `prospects` table only as a temporary compatibility projection. New UI and APIs must read normalized models.

## 10.4 Dashboard rollups

Do not execute many expensive counts against raw tables on every dashboard request. Add intentionally maintained rollups or efficient aggregate queries for:

- stage funnel by play/day;
- source-run yield;
- contact readiness;
- campaign outcomes;
- task counts;
- worker health;
- data quality.

Refresh rollups transactionally after relevant jobs/events or on a short durable schedule. Show rollup freshness.

## 10.5 Search

Implement PostgreSQL-backed search:

- normalized company name;
- trading names;
- legal identifiers;
- domain;
- person name;
- email/domain where policy allows display;
- campaign/run IDs.

Use appropriate indexes, potentially `pg_trgm` and full-text search. Do not scan all rows in Python.

## 10.6 Pagination

Use cursor pagination for large company, opportunity, evidence, contact, audit, and run lists. Offset pagination may be used only for small stable administrative lists.

## 10.7 Query budgets

Set and test query-count budgets for key pages. Eliminate N+1 loads. Use explicit selectin/joined loading only where appropriate. Add indexes for all common filters and sort keys.

---

# 11. Durable jobs and automation model

Add explicit models and services.

## 11.1 JobRun

Fields:

- UUID;
- type;
- status;
- requested_by;
- play_version;
- connector;
- scope JSON;
- idempotency key;
- priority;
- created/queued/started/finished timestamps;
- progress current/total;
- current stage;
- heartbeat;
- cancel requested;
- retry count;
- error summary;
- result summary;
- parent job;
- correlation ID.

Statuses:

```text
created
queued
running
pausing
paused
succeeded
partially_succeeded
failed
cancelled
dead_lettered
```

## 11.2 JobStep

Track each pipeline stage and partition:

- job;
- stage code;
- partition key;
- status;
- attempt;
- worker;
- checkpoint;
- counts;
- start/end;
- error;
- metrics.

## 11.3 Idempotency

Use deterministic keys based on job type, play version, connector, partition, source snapshot, and configuration hash. Duplicate launch requests must return the existing active job rather than creating duplicate work.

## 11.4 Leases and heartbeats

- Workers claim steps using a lease.
- Extend lease through heartbeat.
- Requeue abandoned work only after safe timeout.
- Ensure side effects are idempotent before retry.

## 11.5 Source budgets and circuit breakers

Per connector configure:

- requests/minute;
- concurrent requests;
- daily request budget;
- monetary budget;
- maximum error rate;
- cooldown;
- freshness SLA.

Open the circuit on repeated upstream failure and show it in the UI.

## 11.6 Scheduling

Celery Beat must schedule:

- official bulk snapshot checks;
- incremental refresh;
- domain reverification;
- evidence refresh;
- contact reverification;
- score recalculation only when dependencies changed;
- task generation;
- campaign windows;
- retention;
- backup checks;
- data-quality scans.

Schedules belong to versioned configuration and are visible in the UI.

---

# 12. Acquisition and intelligence logic

## 12.1 Pipeline stages

Implement this as a durable DAG, not one monolithic function:

```text
1. acquire raw source data
2. validate source schema
3. persist immutable source record
4. normalize entity fields
5. resolve legal identity
6. deduplicate/merge
7. evaluate play eligibility
8. create/update opportunity
9. resolve official domain
10. crawl bounded official pages
11. extract evidence and triggers
12. estimate operational complexity/field team
13. identify current buyer candidates
14. discover source-backed contact routes
15. verify contact technical state
16. apply suppression and compliance policy
17. calculate score snapshot
18. calculate hard gates/readiness
19. create human-review task
20. draft only after acceptance and sufficient evidence
```

Each stage must be repeatable and independently observable.

## 12.2 Recompute dependency graph

Do not recalculate everything after every edit. Define dependencies:

- company identity change → domain, opportunity eligibility, person-company match, compliance, score;
- evidence change → score, readiness, draft validity;
- person role change → buyer choice, authority score, draft recipient;
- contact verification change → contact gate, compliance, campaign eligibility;
- policy version change → all affected decisions and memberships;
- play version change → new opportunity evaluation, not silent mutation of historical decisions.

## 12.3 Evidence-bound claims

Every generated message claim must reference one or more evidence IDs. If evidence expires, is rejected, or contradicts another item, invalidate the draft and require regeneration/reapproval.

## 12.4 No fake inference

The system may create hypotheses such as `possible fragmented workflow`, but must label them as hypotheses. It may not present them as facts in messages unless source evidence supports them.

## 12.5 Learning loop

Record:

- cohort;
- score version;
- play version;
- evidence profile;
- contact type;
- message variant;
- outcome.

Use this to report which combinations produce positive replies and meetings. Do not automatically retrain or alter production scoring without a reviewed version change.

---

# 13. Outreach and commercial logic

## 13.1 Eligibility gate

A campaign membership can become `ready_for_draft` only when:

- active company;
- active eligible legal form;
- current play version;
- identity resolved;
- official domain sufficiently verified;
- required evidence exists and is fresh;
- buyer selected or an approved role mailbox strategy exists;
- contact route utility is allowed;
- compliance decision is allowed;
- suppression passes;
- human qualification accepted;
- no conflicting active campaign.

## 13.2 Draft lifecycle

```text
generated → needs_review → approved → scheduled → locked → sent
                      ↘ rejected
                      ↘ invalidated
```

Any material input change invalidates approval.

## 13.3 Touch lifecycle

```text
planned → queued → provider_accepted → delivered
                       ↘ bounced
                       ↘ failed
                       ↘ cancelled
```

Provider webhooks/events must reconcile touch state idempotently.

## 13.4 Stop rules

Stop future sequence steps immediately for:

- any human reply other than a recognized automated response;
- opt-out;
- complaint;
- hard bounce;
- meeting booked;
- opportunity won/lost;
- manual pause;
- policy no longer allowed;
- contact invalidated;
- company/person suppression.

## 13.5 Pipeline outcome semantics

Do not infer `Replied`, `Meeting`, `Proposal`, or `Won` from manually dragging a card alone. Stage changes must be backed by events and validated transitions. Manual override requires a reason and audit record.

---

# 14. Security, privacy, and reliability

- Keep CSRF protection for all browser mutations.
- Add CSRF to all fetch/HTMX requests consistently.
- Secure cookies with appropriate flags.
- Implement explicit session expiration and logout.
- Add rate limiting for login and sensitive routes.
- Never log passwords, tokens, full secret values, or unredacted provider payloads containing sensitive data.
- Encrypt secrets at rest or load from environment/secret store; do not store plaintext in general settings tables.
- Retain SSRF defenses for website crawling and strengthen redirect/IP revalidation.
- Validate uploaded files and prevent path traversal.
- Add CSV formula-injection protection.
- Add global exception handling with request/correlation ID.
- Create branded 403, 404, 409, 422, 429, and 500 pages.
- Add structured JSON logs in production.
- Add Prometheus-compatible metrics or equivalent.
- Add backup freshness and restore-test visibility.
- Separate production, staging, and test data.
- Disable fixture behavior in production through hard configuration validation.
- Do not overwrite admin credentials at startup.

---

# 15. API and service contracts

Create a versioned `/api/v1` surface for the normalized system. HTML routes may call the same application services.

Required resource groups:

```text
/api/v1/command-center
/api/v1/tasks
/api/v1/market-plays
/api/v1/market-play-versions
/api/v1/connectors
/api/v1/source-runs
/api/v1/jobs
/api/v1/companies
/api/v1/opportunities
/api/v1/evidence
/api/v1/people
/api/v1/contact-points
/api/v1/qualification-reviews
/api/v1/compliance-decisions
/api/v1/campaigns
/api/v1/drafts
/api/v1/touches
/api/v1/conversations
/api/v1/suppressions
/api/v1/audit-events
/api/v1/imports
/api/v1/health/*
```

Rules:

- Pydantic schemas must be separate from ORM models.
- List endpoints support cursor pagination and filter validation.
- Mutations use idempotency keys where relevant.
- Conflict states return 409.
- Long operations return 202 with job resource URL.
- Validation errors return structured field errors.
- Every response that drives status includes freshness and source where appropriate.
- Permission checks happen in service/API layer, not only templates.

---

# 16. Exact repository change map

At minimum inspect and replace/refactor these current files:

```text
app/templates/base.html
app/templates/dashboard.html
app/templates/market_plays.html
app/templates/sourcing.html
app/templates/prospects.html
app/templates/prospect_detail.html
app/templates/queue.html
app/templates/follow_ups.html
app/templates/kanban.html
app/templates/import.html
app/templates/partials/*
app/static/css/input.css
app/static/css/app.css
app/static/js/app.js
app/static/js/kanban.js
app/main.py
app/models.py
app/schemas.py
app/routers/dashboard.py
app/routers/market_plays.py
app/routers/sourcing.py
app/routers/prospects.py
app/routers/queue.py
app/routers/events.py
app/routers/contact_intelligence.py
app/jobs/scheduler.py
app/jobs/ingestion.py
app/jobs/enrichment.py
app/services/*
app/sources/*
docker-compose.yml
Dockerfile
package.json
pyproject.toml
scripts/release-gate.sh
scripts/smoke-production.sh
```

Create coherent packages such as:

```text
app/domain/
app/repositories/
app/use_cases/
app/jobs/tasks/
app/jobs/pipelines/
app/metrics/
app/observability/
app/templates/layouts/
app/templates/components/
app/templates/pages/
app/static/js/core/
app/static/js/features/
```

Do not create a parallel unused architecture. Move real routes and jobs onto it through a tested cutover.

---

# 17. Migration plan

Continue after the existing latest migration with ordered revisions. Exact IDs may follow repository convention, but include at least:

1. job/run/step/event/dead-letter tables;
2. audit and request-correlation support;
3. missing normalized person-role and contact verification structures;
4. complete campaign/sequence/draft/touch/provider/conversation structures;
5. dashboard rollups and indexes;
6. task and queue normalization;
7. source connector health/budget/freshness fields;
8. import staging/quarantine tables;
9. legacy backfill and compatibility projection;
10. final constraints and indexes after data cleanup.

For every migration:

- test upgrade from a realistic copy of current data;
- test downgrade where safe;
- avoid table rewrites that create unacceptable downtime;
- backfill in batches;
- verify row counts and checksums;
- provide rollback notes.

---

# 18. Performance requirements

Test with at least:

```text
10,000 companies
20,000 opportunities across versions
100,000 source records
50,000 evidence items
20,000 people
30,000 contact points
5,000 tasks
2,000 campaign memberships
100,000 audit events
```

Acceptance targets on production-like hardware:

- Command Center p95 server response under 700ms using fresh rollups.
- Company Universe first page p95 under 500ms.
- Opportunity list p95 under 500ms.
- Full text search p95 under 700ms.
- Detail workspace p95 under 800ms excluding queued external enrichment.
- Pagination does not degrade linearly with deep pages.
- No request loads all 10,000 companies into application memory.
- Bulk import uses streaming/chunking.
- Long jobs expose progress and survive restart.

Record actual benchmark hardware, dataset, commands, and results.

---

# 19. Testing and acceptance strategy

## 19.1 Backend tests

- unit tests for normalization, scoring, policies, transitions, idempotency;
- repository tests against PostgreSQL;
- source adapter contract tests using recorded fixtures only in tests;
- integration tests for job pipelines;
- migration tests from current schema/data;
- campaign state-machine tests;
- provider webhook idempotency tests;
- suppression and opt-out tests;
- SSRF/security tests;
- data-quality tests;
- load and concurrency tests.

## 19.2 Frontend tests

Use Playwright or equivalent for:

- login/logout;
- every navigation route returns a designed page, never raw 500;
- sidebar collapse;
- command palette;
- start run wizard and dry run;
- run inspector progress;
- company filters/saved views/pagination;
- opportunity review actions;
- contact approval;
- draft approval/invalidation;
- campaign activation/pause;
- reply classification;
- task completion;
- pipeline valid/invalid transitions;
- import mapping/validation/quarantine;
- error pages;
- keyboard operation.

## 19.3 Visual regression

Capture and compare all major pages at four viewport sizes. Acceptance must reject:

- clipped content;
- unreadable contrast;
- white panels in dark workspace;
- giant emoji/icons;
- unbounded empty space;
- horizontal viewport overflow;
- inconsistent button or badge variants;
- misaligned tables;
- missing focus state;
- raw browser error pages.

## 19.4 Accessibility

Run automated axe checks plus manual keyboard review for core flows. No critical accessibility violations may remain.

## 19.5 Route matrix

Create an authenticated route smoke test that visits every HTML route with seeded realistic data and valid empty data. Every route must return expected status and contain the correct application shell.

---

# 20. Implementation phases and release gates

## Phase 0 — Truthful baseline and failure reproduction

Deliver:

- full route matrix;
- current screenshots;
- exact 500 reproduction and fix test;
- data model/runtime map;
- static-claim inventory;
- fixture/placeholder inventory;
- current performance sample.

Gate: no implementation begins without a written baseline.

## Phase 1 — Safety and frontend foundation

- stop password overwrite;
- add global error handling and request IDs;
- remove production CDNs;
- establish deterministic asset build;
- create tokens/components/app shell;
- add local icons;
- fix CSRF handling;
- remove `document.write` and alerts;
- create designed error/empty/loading states.

Gate: every old route renders within the new shell without visual breakage or raw error.

## Phase 2 — Durable job foundation

- Redis/Celery/Beat;
- job tables;
- job services;
- leases/checkpoints/retry/dead letter;
- web-to-job 202 behavior;
- worker health;
- operations UI.

Gate: a long test job survives web restart and worker restart without duplication or data loss.

## Phase 3 — Normalized read/write cutover

- complete schema;
- backfill;
- normalized repositories/services;
- legacy compatibility projection;
- company universe and opportunity explorer use normalized data.

Gate: new acquisition writes and UI reads no longer depend on flat `Prospect` as authority.

## Phase 4 — Command Center and workflow pages

- Command Center;
- My Work;
- Market Plays;
- Source Runs;
- Company Universe;
- Opportunity Explorer;
- Intelligence workspace.

Gate: the operator can go from run to reviewed opportunity without legacy pages.

## Phase 5 — Review and data quality

- qualification;
- buyer/contact review;
- evidence review;
- data-quality center;
- saved views and tasks.

Gate: gold-set workflow works end-to-end with audit history.

## Phase 6 — Campaign and outreach operations

- campaign builder;
- eligibility;
- drafts;
- approval;
- provider abstraction;
- touch state;
- replies;
- follow-ups;
- commercial pipeline;
- emergency pause.

Gate: full dry-run works; real send remains disabled until sender readiness gate.

## Phase 7 — Import, operations, and administration

- staged imports;
- connectors;
- jobs/workers;
- suppression;
- audit;
- settings;
- backup and release visibility.

Gate: all administrative workflows are operational and audited.

## Phase 8 — Scale, quality, and deployment

- 10K+ benchmark dataset;
- load tests;
- query optimization;
- visual regression;
- accessibility;
- backup/restore rehearsal;
- migration rehearsal;
- deployment/rollback rehearsal.

Gate: all acceptance thresholds pass with evidence.

## Phase 9 — Controlled production activation

- deploy with sending paused;
- verify all health states;
- ingest real official data;
- run a bounded cohort;
- inspect quality;
- enable only approved connector and campaign functions.

Gate: no production capability is labeled active before observed success.

---

# 21. Exact visual acceptance criteria

The final product must visibly satisfy all of these:

- no emoji anywhere in the core interface;
- no giant decorative icons;
- no pure white Kanban columns or table headers in dark mode;
- no full-screen border frame;
- no static `Level 300` language;
- no static source-health or engine-live claims;
- compact page headers;
- consistent 8px spacing system;
- consistent component library;
- readable contrast at all supported widths;
- tables use full available width and remain controllable;
- key pages contain actionable information above the fold;
- empty states explain cause and next action;
- long-running actions show durable progress;
- all errors show a designed recovery state and request ID;
- active commercial pipeline contains only qualified/outreach opportunities;
- the source-run interface makes progress, failures, and resume state obvious;
- the platform looks credible in a client, investor, or senior-engineer review without relying on visual exaggeration.

---

# 22. Business acceptance criteria

The release is not complete merely because the pages look better. It must prove that the product supports the intended business workflow.

Using a realistic seeded or real controlled dataset, demonstrate:

1. Create or activate a versioned market play.
2. Validate a real source connector.
3. Start a dry-run with scope and budget preview.
4. Run a durable acquisition job.
5. Inspect raw, normalized, rejected, and duplicate counts.
6. Open the resulting company universe.
7. Evaluate companies into opportunities.
8. Enrich one opportunity with official domain and evidence.
9. Identify and review a buyer and contact route.
10. Apply policy and suppression gates.
11. Review and accept the opportunity.
12. Generate an evidence-bound message.
13. Edit and approve a versioned draft.
14. Add it to a paused campaign.
15. Execute provider dry-run or sandbox send.
16. Ingest a simulated provider delivery and reply event through the real event path.
17. Stop the sequence and create a follow-up task.
18. Move the commercial opportunity through a valid pipeline transition.
19. See the funnel and outcome metrics update truthfully.
20. Reproduce the full audit trail.

The operator must complete daily qualification and approval work without copying data between disconnected pages.

---

# 23. Required documentation

Create/update:

```text
README.md
GUIDE.md
DEPLOY.md
ARCHITECTURE.md
OPERATIONS.md
DATA_MODEL.md
SOURCE_CONNECTORS.md
MARKET_PLAYS.md
SCORING_AND_GATES.md
CAMPAIGNS_AND_SENDING.md
SECURITY_AND_PRIVACY.md
BACKUP_AND_RESTORE.md
RUNBOOK.md
acceptance/route-matrix.md
acceptance/visual-review.md
acceptance/performance-report.md
acceptance/migration-rehearsal.md
acceptance/backup-restore-rehearsal.md
acceptance/production-activation.md
```

Documentation must describe actual implemented behavior and known limitations, not aspirational capability.

---

# 24. Required final response from Antigravity

Return a structured completion report containing:

1. executive summary;
2. branch and final commit;
3. exact files created/modified/deleted;
4. architecture changes;
5. database migrations and backfill counts;
6. legacy cutover state;
7. frontend pages and components completed;
8. screenshots at required widths;
9. route smoke results;
10. unit/integration/E2E/accessibility results;
11. performance dataset and benchmarks;
12. source connector states with real evidence;
13. durable job restart/resume evidence;
14. campaign dry-run evidence;
15. security checks;
16. backup/restore and rollback evidence;
17. deployment commands;
18. remaining credentials or upstream blockers;
19. known limitations;
20. exact next operator actions.

Do not write `completed` beside a requirement that is mocked, fixture-backed, untested, credential-blocked, or only visually represented.

---

# 25. Absolute prohibitions

Antigravity must not:

- perform only a CSS restyle;
- return mockups instead of working pages;
- introduce React or another SPA framework without a proven need and approved migration plan;
- keep the Tailwind CDN in production;
- use emoji as icons;
- use giant icons to fill empty space;
- preserve the white Kanban columns;
- display static engine/source/compliance health claims;
- launch ingestion directly in a web request or non-durable background task;
- use in-process scheduling as production authority;
- fabricate source records or fixture health;
- silently continue using the flat `Prospect` model as the source of truth;
- load all records into memory for filtering or export;
- auto-send guessed contacts;
- bypass suppression or policy gates;
- automate LinkedIn scraping or messaging;
- overwrite an existing admin password on startup;
- expose raw stack traces or raw `Internal Server Error` pages;
- use browser alerts as product UI;
- use `document.write` for form responses;
- claim 10K-scale readiness without benchmark evidence;
- claim production readiness without migration, backup, restore, and rollback evidence.

---

# PART II — MANDATORY LEVEL-300 BACKEND AND ACQUISITION-ENGINE BASELINE

The following technical baseline is incorporated from the previous acquisition-engine order. It remains mandatory. When any wording conflicts with Part I, Part I controls because it is more specific to the final operating product and interface.

# 2. Business mission

ProspectForge is an internal acquisition operating system for Anass/Elevya. Its mission is to continuously build a large, trustworthy company universe, reduce it into evidence-backed opportunities, identify the correct buyers and defensible contact paths, and help convert the best opportunities into conversations for custom field-operations systems, integrations, workflow automation, rescue work, and operational software.

The first market plays are:

```text
FIELD_OPERATIONS_UK_V1
FIELD_OPERATIONS_FR_V2
```

The system must support at least 10,000 distinct raw company entities without degrading, but “10,000 leads” means a company-intelligence universe—not 10,000 guessed personal emails and not 10,000 automatic cold messages.

The intended funnel is:

```text
10,000+ raw official company entities
    ↓ identity, status, sector, legal-form and location normalization
2,000–5,000 plausible ICP companies
    ↓ official-domain discovery and verification
1,000–3,000 domain-resolved companies
    ↓ bounded website/trigger/technology evidence extraction
500–1,500 evidence-enriched opportunities
    ↓ buyer and contact waterfall
200–800 buyer-identified opportunities
    ↓ policy, hard gates, verification and human review
50–250 review-ready opportunities per active cycle
    ↓ operator approval and campaign capacity
20–50 outreach-ready opportunities per week
```

These are capacity and quality targets, not fabricated promises. The engine does not guarantee clients. It must create a repeatable, measurable path to qualified conversations and expose exactly where conversion fails.

---

# 3. Current repository truth that must be treated as defects

The latest supplied repository already contains valuable work, but it is not the system represented by its “Level 300” UI. Verify every item below and either correct it or document evidence that it has already been corrected.

## 3.1 Execution-path contradictions

1. `app/plays/__init__.py` sets `DEFAULT_PLAY_CODE = "FIELD_OPERATIONS_UK_V1"`.
2. `app/jobs/ingestion.py` still imports that global default but executes France-specific DECP and Annuaire/Sirene flows.
3. The sourcing page presents a `play_code` selector, but `/sourcing/run-ingestion` does not accept or pass `play_code`.
4. The sourcing page presents `mode=companies_house`, but the form route rejects every mode except `full`, `decp`, and `registry`, silently replacing the UK selection with `full`.
5. Therefore selecting the UK play can launch the French acquisition path while the UI claims Companies House sourcing.
6. `app/sources/companies_house.py` falls back to a realistic-looking fixture when no API key exists.
7. `app/sources/decp_adapter.py` returns a fabricated contract/company record rather than a real source result.
8. Some source `healthcheck()` methods report healthy without making a real check.
9. Fixture behavior is not sufficiently isolated from production behavior.
10. These are P0 truth violations. Production must never create or display fabricated candidates as sourced leads.

## 3.2 Dead or disconnected architecture

1. Migration `007_multi_market_schema.py` adds normalized company, identifier, classification, domain, source-run, opportunity, evidence, person, compliance, score, campaign, and touch tables.
2. Most operational routes and jobs still use the legacy `Prospect` aggregate.
3. The application contains roughly 181 Python references to `Prospect`, while the normalized models are referenced only sparsely outside model definitions.
4. `SourceRun` and `SourceRecord` are not the real ingestion audit path.
5. `Company`, `Opportunity`, `EvidenceItem`, `PersonRole`, `ComplianceDecision`, `ScoreSnapshot`, `Campaign`, and `Touch` are not end-to-end sources of truth.
6. Existing normalized contact-intelligence tables and the newer company/person/contact design are not reconciled.
7. A migration existing is not evidence that the architecture is implemented.

## 3.3 Scale and reliability defects

1. Ingestion runs inside FastAPI `BackgroundTasks`; work can disappear on process restart.
2. APScheduler runs inside the web process and is unsafe as the durable orchestration layer.
3. There is no durable task lease, retry policy, dead-letter queue, run checkpoint, per-source quota ledger, or resumable batch cursor.
4. `max_companies` is capped at 500 through the API and defaults near 200.
5. Contact refresh defaults to eight records per night.
6. Ingestion performs serial per-company enrichment and small commits; it is not designed to populate 10,000 companies efficiently.
7. Full list filtering and status derivation are partly done in Python, which will become slow and memory-heavy as volume grows.
8. There is no genuine bulk Companies House ingestor or bulk Sirene stock ingestor.
9. There is no source freshness matrix, source cost budget, data lineage browser, replay control, or failed-record workbench.

## 3.4 Intelligence defects

1. The Companies House adapter searches by company name/number; that cannot enumerate a market by SIC at scale.
2. The current evidence engine is a small regex list and cannot reliably classify operational complexity, system fragmentation, triggers, or contradictory evidence at scale.
3. Technician estimates use broad workforce-band assumptions and can present false precision.
4. Buyer resolution is a small title regex dictionary without source freshness, current-role reconciliation, or multi-person ranking.
5. Message generation inserts evidence text directly into generic templates and does not prove that each claim is safe, current, or relevant.
6. Scoring has multiple implementations (`scoring.py`, `scoring_v3.py`, `services/scoring_engine.py`) and risks conflicting sources of truth.
7. Current campaign code is largely a model/dataclass skeleton rather than an operational sequence engine.

## 3.5 Frontend truth and usability defects

1. UI labels such as “LEVEL 300,” “Companies House: Active,” and “PECR/CNIL Pass” can appear without verified runtime evidence.
2. `market_plays.html` expects fields that `list_active_plays()` does not return and hard-codes “2 Active Plays” while the registry contains three entries.
3. The UI is styled as an advanced system but lacks a genuine 10K universe explorer, run monitor, source health center, data-quality queues, merge review, durable job status, campaign control, and cost/coverage analytics.
4. Static visual claims must be replaced by live status derived from persisted facts.
5. Do not “improve” the system by adding more gradients, badges, or glassmorphism while the pipeline remains false or disconnected.

## 3.6 Security and operations defects to re-check

1. Admin password bootstrap currently updates the password during every startup; this is dangerous and must become create-once plus explicit rotation.
2. Production and development fixture modes need hard separation.
3. Source secrets need validated configuration and redacted diagnostics.
4. Background task duplication must be prevented across multiple app instances.
5. Production must use Alembic only and must fail hard on migration errors.
6. Every export and send boundary must re-check suppression and policy.

---

# 4. Definition of the real Level 300 system

The system is Level 300 only when all of the following are true:

1. It can ingest at least 10,000 distinct official company records into PostgreSQL through resumable bulk pipelines.
2. It can process a 10,000-company universe without loading the full dataset into application memory.
3. Every record has provenance, source run, observed time, and normalized identity.
4. It uses exact identifiers before fuzzy matching and provides operator merge/split controls.
5. It has real UK and France acquisition implementations selected by play and source—not a global default pretending to be multi-market.
6. It distinguishes raw companies, ICP candidates, opportunities, people, contact points, campaigns, and touches.
7. It automatically discovers and verifies official domains using a bounded, auditable waterfall.
8. It automatically crawls allowed public website pages with SSRF protection, per-domain politeness, content hashing, and refresh rules.
9. It extracts evidence and contradictory evidence with exact source snippets.
10. It ranks companies by explainable dimensions and hard gates, calibrated against a labeled set.
11. It automatically attempts buyer and contact enrichment while clearly distinguishing published, provider-supplied, inferred, guessed, verified, catch-all, invalid, and unknown states.
12. It never converts a guessed email into an outreach-ready contact without policy-compliant human approval and sufficient evidence.
13. It has a durable worker system with retries, leases, idempotency, checkpoints, rate budgets, dead-letter handling, and operational visibility.
14. It has a high-density but usable frontend for 10K records, including saved views, cursor/server-side pagination, bulk actions, and drill-down evidence.
15. It supports approval-gated email sequences, reply/bounce/opt-out stop rules, and a global kill switch.
16. It never automates LinkedIn scraping, connection requests, or messaging.
17. It tracks the complete funnel from source record to reply, meeting, proposal, and revenue outcome.
18. It can be deployed, backed up, restored, monitored, and rolled back without data loss.
19. Unit tests, integration tests, source-contract tests, migration tests, browser tests, and 10K load tests pass.
20. The deployed UI reports only live, persisted truth.

---

# 5. Required architecture

Do not rewrite the entire product into a fashionable stack. Preserve FastAPI, PostgreSQL, SQLAlchemy, Alembic, Jinja, HTMX, and Tailwind where they remain suitable. Replace only the parts that block reliability, scale, or maintainability.

## 5.1 Runtime topology

Implement this production topology:

```text
Caddy / existing reverse proxy
        ↓
FastAPI web container (no long-running acquisition work)
        ↓
PostgreSQL 16 — source of truth
Redis 7 — task broker, short-lived locks and cache only
Celery worker: source-ingestion queue
Celery worker: identity/domain queue
Celery worker: website/evidence queue
Celery worker: buyer/contact queue
Celery worker: campaigns/notifications queue
Celery Beat — one durable scheduler instance
Optional internal Flower or custom worker monitor — never public without auth
Backup job + raw-data volume
```

If a mature async-first alternative is already present and demonstrably better integrated, document the decision. Do not keep FastAPI `BackgroundTasks` or in-process APScheduler for important work.

## 5.2 Data zones

Implement three explicit logical data zones:

### Bronze — immutable source capture

- source connector;
- source run;
- external record ID;
- raw payload or raw file manifest;
- payload hash;
- retrieval timestamp;
- source URL/license metadata;
- parser version;
- rejection/error state.

### Silver — normalized company intelligence

- company identity;
- identifiers;
- aliases;
- status and legal form;
- classifications;
- locations;
- official-domain candidates;
- website pages;
- people and roles;
- contact points;
- estimates;
- source-backed facts.

### Gold — commercial opportunities

- market play/version;
- opportunity;
- evidence and contradictions;
- score snapshots;
- compliance decisions;
- readiness state;
- human reviews;
- message drafts;
- campaign membership;
- touches and outcomes.

Do not collapse these zones back into a single `Prospect` row.

## 5.3 Raw file storage

For large official snapshots, store downloaded ZIP/CSV/Parquet assets under a mounted data volume with:

- atomic `.partial` download and rename;
- SHA-256 checksum;
- ETag/Last-Modified where available;
- file size;
- source version/date;
- parser version;
- import manifest;
- retention policy;
- resumable parsing checkpoint.

PostgreSQL remains the record source of truth. Raw large files do not need to be stored as giant JSONB rows.

---

# 6. Exact source strategy for 10,000+ companies

Implement source connectors as independent, versioned adapters. Each connector must expose config validation, health, discovery/snapshot, normalization, checkpointing, rate/cost budget, and fixtures used only in tests.

## 6.1 UK foundation

### A. Companies House bulk company snapshot

This is the primary high-volume UK discovery source. Implement a connector that:

1. discovers the current official monthly bulk file manifest;
2. downloads split files or the single file safely;
3. validates content length and checksum when available;
4. streams CSV rows rather than reading the entire archive into memory;
5. filters active corporate entities by configured SIC codes and legal forms;
6. normalizes company number, name, status, incorporation date, registered address, SIC codes, accounts dates, previous names and URI;
7. persists every accepted/rejected row with counters and reason codes;
8. supports reruns without duplicates;
9. records the snapshot date;
10. creates/updates opportunities only after market-play eligibility evaluation.

### B. Companies House REST enrichment

Use the API for current profile refresh and selected enrichment, not market-wide enumeration. Implement rate limiting compatible with the official limit, backoff for `429`, request caching, ETag support when available, and per-company endpoints for:

- profile;
- officers;
- persons with significant control where appropriate;
- filing history metadata;
- registered office changes or other relevant updates.

Never bypass official limits. Never treat missing API credentials as permission to generate fixtures.

### C. UK public-contract triggers

Implement official OCDS connectors for Find a Tender and Contracts Finder. Use award/supplier data as a trigger or capacity signal, never proof of software pain. Normalize OCID, notice/release ID, buyer, supplier, award date, value, CPV/category, title, and source URL.

## 6.2 France foundation

### A. Sirene stock files

This is the primary high-volume French discovery source. Implement streaming/batch ingestion of `StockUniteLegale` and `StockEtablissement` official files, including current NAF Rev.2 fields and the parallel NAF 2025 fields already appearing ahead of the 2027 cutover.

Requirements:

- parse only required columns efficiently;
- retain SIREN/SIRET relationships;
- determine active legal units and establishments;
- support legal form, employee band, activity, location and diffusion fields;
- filter by play-specific classifications after normalization;
- checkpoint by file and row group/chunk;
- maintain source snapshot dates;
- be ready for the NAF 2025 transition without schema breakage.

### B. Sirene/Annuaire current refresh

Use APIs for selected refresh and current details. Do not issue one API request per entire raw universe when a bulk stock file provides the data.

### C. DECP trigger ingestion

Continue using real official/consolidated DECP datasets, but make the adapter real, incremental, checkpointed, and play-aware. Remove the fabricated adapter response. Store award data separately and link supplier identity through SIREN/SIRET.

### D. BODACC and optional RNE/INPI

Implement BODACC as a trigger source for creations, modifications, acquisitions, relocations, insolvency/risk, and other company-life events. Add an optional RNE/INPI connector behind credential validation for richer legal/current-role information. Respect source terms, access requirements, and update notices.

## 6.3 Website/domain discovery sources

Implement a provider interface rather than scraping consumer search-result pages directly. Support:

1. imported domains from commercial/provider CSVs;
2. domains published in official or partner data;
3. approved search API provider;
4. deterministic company-name candidate generation as low-confidence hypotheses;
5. manual operator candidates.

A domain is never official solely because its name resembles the company.

## 6.4 Optional commercial connectors

Create adapters for commercial company/contact exports or APIs, but do not hard-code a vendor. Required generic contracts:

- `commercial_company_provider`;
- `commercial_people_provider`;
- `email_verification_provider`;
- `search_provider`;
- `outbound_provider`.

Every imported field must retain provider, plan/run ID, retrieval date, license/usage note, and confidence. Provider data must be resolved against official identity before it can reach Gold.

---

# 7. Durable orchestration and automation

## 7.1 Job model

Create durable persisted models for:

```text
pipeline_runs
pipeline_run_stages
work_items
work_item_attempts
source_rate_budgets
source_checkpoints
failed_work_items
scheduler_leases
```

Each work item requires:

- UUID;
- run and stage;
- entity/source reference;
- idempotency key;
- status (`queued`, `leased`, `running`, `retry_wait`, `succeeded`, `failed`, `dead`, `cancelled`);
- priority;
- queue name;
- attempts/max attempts;
- scheduled time;
- lease owner and expiry;
- input hash;
- output summary;
- error class/message/trace reference;
- created/started/finished timestamps.

## 7.2 Pipeline DAG

Implement this resumable DAG:

```text
snapshot/discover
  → normalize
  → exact identity resolve
  → fuzzy duplicate review when needed
  → market-play eligibility
  → opportunity create/update
  → domain candidate discovery
  → domain verification
  → bounded website crawl
  → evidence extraction
  → trigger extraction
  → complexity/field-team estimation
  → buyer discovery and role resolution
  → contact waterfall
  → compliance evaluation
  → score snapshot
  → readiness decision
  → review queue
  → optional approved campaign
```

A failed downstream stage must not erase upstream work. Stages must be replayable independently by version.

## 7.3 Required queue behavior

- exponential backoff with jitter;
- source-specific rate limits;
- per-domain crawl limits;
- idempotency across retries;
- explicit cancellation;
- pause/resume by play, source, run and global kill switch;
- dead-letter review and replay;
- task-heartbeat and stale-lease recovery;
- concurrency limits per queue;
- cost budgets for paid providers/LLM calls;
- no duplicate schedule execution;
- structured logging with run/work-item IDs.

## 7.4 Scheduling

Implement schedules through Celery Beat or equivalent single scheduler:

- monthly bulk snapshot discovery and import;
- daily official trigger delta imports;
- daily domain/evidence processing budget;
- daily contact refresh budget;
- daily score/readiness recalculation for changed entities only;
- weekly stale-domain/contact refresh;
- weekly retention/suppression integrity sweep;
- scheduled backup and restore verification;
- source-health checks.

Do not rescore or recrawl all 10,000 companies every night. Use change events, freshness and priority budgets.

---

# 8. Normalized source-of-truth cutover

The current migration `007` is a starting point, not the final design. Implement a controlled cutover.

## 8.1 Required source-of-truth rules

- `Company` is the legal/operating entity source of truth.
- `CompanyIdentifier` holds official identifiers.
- `CompanyClassification` holds SIC/NAF/NACE classifications.
- `CompanyLocation` holds registered and operating locations.
- `CompanyDomain` holds domain candidates and verification state.
- `Opportunity` is company × market-play-version.
- `EvidenceItem` holds exact evidence, not a narrative blob.
- `Person` and `PersonRole` hold people/current roles.
- normalized contact-point models hold email/phone/form information.
- `ComplianceDecision` is immutable/versioned per evaluation.
- `ScoreSnapshot` is immutable/versioned.
- `Campaign`, sequence, message draft, touch and provider event models hold outreach.
- `Prospect` becomes a compatibility projection during migration and is removed from business logic after parity.

## 8.2 Required additional/changed models

Add or complete:

```text
company_facts
company_relationships
website_pages
website_fetches
technology_observations
trigger_events
negative_evidence_items
person_sources
contact_points_v2 or reconciled existing contact_points
contact_verification_events_v2 or reconciled existing events
human_reviews_v2
message_drafts
message_claims
sequences
sequence_steps
campaign_memberships
provider_events
inbound_messages
unsubscribe_tokens
saved_views
bulk_actions
audit_events
pipeline_runs and work-item tables
```

Do not create redundant V2 tables if the existing normalized contact-intelligence schema can be migrated cleanly. Document the canonical table and remove duplicate logic.

## 8.3 Migration requirements

1. Create a full database backup.
2. Add new tables/columns/indexes safely.
3. Backfill Companies from legacy Prospects using SIREN/SIRET, company number, country and domain.
4. Create market-play versions from active configs.
5. Backfill Opportunities.
6. Backfill evidence with provenance and mark weak legacy narratives appropriately.
7. Backfill people/contact points with their original confidence/source.
8. Backfill suppression and outreach history.
9. Establish deterministic legacy-to-new mapping IDs.
10. Run dual-read comparison reports.
11. Switch writes to normalized services.
12. Remove legacy writes.
13. Keep a read-only compatibility view if necessary.
14. Do not drop legacy columns/tables until production parity and rollback window pass.

Add indexes for exact identifiers, normalized domains, country/classification/status, opportunity play/status/score, evidence codes/freshness, role/company/current, contact state, work-item status/schedule, and text search. Enable `pg_trgm` and `unaccent` where supported for company-name/domain matching.

---

# 9. Identity resolution and deduplication

Implement deterministic exact resolution first:

1. official identifier exact match;
2. verified official domain exact match;
3. source URI exact match;
4. exact normalized legal name + country + postcode/address;
5. only then fuzzy candidate generation.

Fuzzy resolution must compute and persist explainable features:

- normalized-name similarity;
- alias similarity;
- postcode/address match;
- country/jurisdiction match;
- classification compatibility;
- domain legal-name evidence;
- officer/phone/address overlap;
- conflicting identifier penalty.

Never auto-merge when official identifiers conflict. Create a merge-review queue with side-by-side source records, scores, reasons, and operator actions: merge, keep separate, mark branch/establishment, defer.

Support reversible merges and maintain an entity-merge audit trail.

---

# 10. Domain and website intelligence

## 10.1 Domain verification waterfall

For every candidate domain:

1. normalize registrable domain with public-suffix handling;
2. reject free-hosting/social/directory domains as primary corporate domains;
3. DNS resolution and TLS/HTTP check;
4. fetch root page safely;
5. extract legal name, trading names, company number/SIREN/SIRET/VAT, address, phone, email, schema.org data and legal footer;
6. compare with Company facts;
7. score and record reasons;
8. choose primary domain only above threshold with no hard contradiction;
9. otherwise queue domain review.

Verification states:

```text
candidate
resolves
reachable
probable
verified_primary
verified_secondary
ambiguous
rejected
parked
```

## 10.2 Crawler requirements

- SSRF-safe URL validation at every redirect;
- DNS rebinding defense;
- prohibit private/link-local/metadata networks;
- per-domain concurrency of one by default;
- clear user agent and contact identity;
- robots/politeness handling;
- bounded page count, depth, bytes and time;
- content-type allowlist;
- PDF extraction bounds;
- HTML-to-text normalization;
- canonical URL and duplicate-content hashing;
- cache and freshness;
- no login/captcha bypass;
- optional Playwright worker only for verified high-value JavaScript-only sites;
- screenshot only when operationally useful and storage-bounded.

Prioritize paths containing localized equivalents of:

```text
about, company, services, maintenance, service, support, industries,
careers, jobs, team, contact, legal, privacy, locations, branches,
interventions, sav, dépannage, maintenance, recrutement, agences
```

---

# 11. Evidence, trigger and technology intelligence

## 11.1 Evidence object contract

Every evidence item must include:

- taxonomy code;
- category;
- exact factual claim;
- exact supporting snippet;
- source URL;
- source record/page ID;
- observed time;
- confidence;
- extraction method/version;
- verification state;
- freshness/expiry;
- contradiction group;
- market-play relevance;
- allowed downstream uses.

Never use a source-free summary as personalization.

## 11.2 Taxonomy

Implement at least these categories:

```text
IDENTITY
VERTICAL
OPERATING_SCALE
FIELD_WORKFORCE
MULTI_BRANCH
GEOGRAPHIC_COVERAGE
RECURRING_MAINTENANCE
EMERGENCY_ON_CALL
CERTIFICATION_OR_REGULATION
CUSTOMER_PORTAL
ONLINE_BOOKING
FSM_OR_ERP_STACK
ACCOUNTING_STACK
MANUAL_DOCUMENT_WORKFLOW
DISCONNECTED_SYSTEM_HINT
HIRING_TRIGGER
EXPANSION_TRIGGER
PUBLIC_CONTRACT_TRIGGER
ACQUISITION_OR_RESTRUCTURE_TRIGGER
TECHNOLOGY_CHANGE_TRIGGER
RISK_OR_NEGATIVE_SIGNAL
BUYER_ROLE
CONTACT_PUBLICATION
```

Model negative evidence explicitly, for example:

- company is too small;
- pure retailer/no service;
- enterprise platform already deeply deployed;
- inactive/dissolved;
- no target geography;
- sole trader or excluded legal form;
- residential-only low-budget profile;
- IT/software vendor;
- duplicate/holding entity;
- insolvency or severe risk.

## 11.3 Extraction pipeline

Use a tiered extraction strategy:

1. deterministic metadata and structured-data extraction;
2. localized keyword/regex classifiers;
3. lightweight statistical/embedding relevance classifier when justified;
4. optional LLM structured extraction only for ambiguous/high-value pages.

LLM rules:

- provider abstraction;
- disabled without credential;
- strict JSON schema;
- prompt includes only retrieved source text;
- output must cite snippet spans/page IDs;
- no autonomous web access from the LLM;
- no direct score or send decision;
- cache by input hash/model/prompt version;
- token/cost budgets;
- human review for low-confidence claims.

## 11.4 Technology-stack detection

Detect only observable technology signals, such as script domains, login/customer-portal links, public integration pages, job requirements, cookies/headers and explicit product mentions. Store observation, evidence and confidence. Do not claim a company has a fragmented stack merely because multiple technologies appear.

---

# 12. Field-team and operational-complexity estimates

Replace the current broad heuristic with an evidence aggregation model.

Inputs may include:

- official employee band;
- number of branches/establishments;
- team-page technician counts;
- job-posting quantities and role types;
- service coverage and on-call claims;
- fleet/vehicle claims;
- certification registers if licensed and appropriate;
- public contract scale;
- explicit “X engineers/technicians” statements.

Return a range, method, confidence and assumptions. Do not present a point estimate as fact unless an exact source states it.

Use estimates as soft scoring inputs. Unknown field-team size may pass only when strong operational-complexity evidence exists.

---

# 13. Buyer and contact intelligence

## 13.1 Buyer selection

Support multiple likely buyers, ranked by company size and offer type:

- owner/managing director/president;
- operations director/head of operations;
- service/SAV director or manager;
- field-service/maintenance manager;
- technical director;
- transformation/IT systems owner when relevant;
- branch/general manager for localized opportunities.

Every role must have source, observed date, current/former state, normalization, confidence, and priority. Do not treat an old registry officer as the current operational buyer without evidence.

## 13.2 Contact waterfall

Use this order:

1. published personal business email on official site/document;
2. published role/generic business mailbox relevant to the request;
3. licensed provider contact tied to the same company/person;
4. published switchboard/business phone;
5. official contact form;
6. generated email pattern as hypothesis only;
7. manual research task.

Verification dimensions must remain separate:

```text
syntax
DNS/MX
publication
provider source
mailbox deliverability
catch-all state
person identity match
current role match
practical outreach utility
policy decision
```

Do not collapse these into a single deceptive `verified` boolean.

## 13.3 No LinkedIn automation

The application may store a manually found public profile URL or generate a search link. It must not scrape LinkedIn, bypass access controls, auto-connect, auto-message, or simulate user activity.

---

# 14. Scoring V4 and hard gates

Consolidate all scoring into one versioned service. Deprecate conflicting scoring implementations.

Required independent dimensions, each 0–100:

```text
icp_fit
operational_complexity
pain_or_integration_opportunity
trigger_strength
commercial_value
buyer_confidence
contact_quality
data_quality
freshness
risk_penalty
```

Persist every snapshot with:

- profile/version;
- inputs/evidence IDs;
- dimension values;
- weights;
- penalties;
- hard-gate results;
- final score;
- reasons;
- computed time.

Required hard gates before `outreach_ready`:

- active eligible legal entity;
- allowed jurisdiction/legal form;
- target vertical or manually approved exception;
- official identity resolved;
- domain resolved or explicit alternate defensible contact path;
- at least one real opportunity/complexity/trigger evidence item;
- buyer role identified or accepted generic role path;
- usable contact path;
- policy decision `allow`;
- not suppressed;
- no unresolved high-severity contradiction;
- human approval;
- evidence-backed message draft.

A high score cannot bypass a failed gate.

## 14.1 Gold set and calibration

Create a labeled dataset of at least 100 companies across UK and France before declaring the scoring system calibrated. Include positives, borderline cases, excluded entities, duplicates, wrong domains, wrong buyers and weak contacts.

Calculate and display:

- company identity precision;
- domain precision;
- ICP precision/recall on the labeled set;
- buyer-role precision;
- contact publication/identity accuracy;
- outreach-ready precision;
- false-positive reasons;
- coverage by source and play.

Mandatory thresholds before larger campaign use:

```text
exact legal-entity resolution ≥ 98%
official-domain precision ≥ 95%
ICP eligibility precision ≥ 90%
buyer-role precision ≥ 85%
outreach-ready unsupported-claim rate = 0%
auto-approved guessed personal email rate = 0%
suppression leakage = 0
```

---

# 15. Campaign and outbound automation

Research and qualification automation should be aggressive. Sending automation must be approval-gated and reversible.

## 15.1 Required campaign entities

```text
Campaign
CampaignMembership
Sequence
SequenceStep
MessageDraft
MessageClaim
Touch
ProviderEvent
InboundMessage
ReplyClassification
UnsubscribeToken
MailboxHealthSnapshot
ExperimentVariant
```

## 15.2 Approval model

Support:

- manual send/export mode;
- approve-first-touch-only mode;
- approve-entire-sequence mode;
- dry-run mode;
- global send kill switch;
- per-campaign pause;
- per-mailbox daily cap;
- per-domain recipient cap;
- working-hours/time-zone window;
- policy re-check immediately before send.

Do not activate real sending without explicit operator configuration and a test mailbox flow.

## 15.3 Stop rules

Immediately stop all scheduled touches for a company/person/contact when any of these occur:

- reply;
- positive/negative manual response;
- hard or repeated soft bounce;
- opt-out/unsubscribe;
- suppression match;
- meeting booked;
- campaign paused;
- mailbox health failure;
- policy state changes;
- contact/role invalidated.

## 15.4 Sending provider interface

Implement an adapter contract that supports:

- send;
- provider message ID;
- delivery/bounce/complaint webhook or polling;
- reply correlation;
- unsubscribe headers/link where appropriate;
- rate limits;
- test mode;
- redacted logs.

Do not force one vendor. Implement at least a safe generic SMTP or selected provider adapter plus a CSV/manual-export fallback. Document setup for the operator’s chosen mailbox.

## 15.5 Deliverability controls

- verify SPF, DKIM and DMARC configuration status through DNS checks;
- do not display “healthy” without real checks;
- maintain consistent low initial volume;
- disable tracking pixels by default;
- plain-text-first messages;
- no fake `Re:` threads;
- no attachments in first touch;
- bounce and complaint thresholds with automatic pause;
- separate sending identity/subdomain decision documented;
- Postmaster/provider monitoring links in operator docs;
- never attempt to send 10,000 cold emails merely because 10,000 companies exist.

---

# 16. Frontend rebuild requirements

Retain the current dark visual identity only where it improves readability. Remove decorative “Level 300” claims. The product should feel like a serious intelligence and operations console.

## 16.1 Navigation

Implement:

```text
Command Center
Company Universe
Opportunities
Review Queues
Campaigns
Pipeline
Runs
Sources
Data Quality
Operations
Settings
```

## 16.2 Command Center

Show live persisted metrics only:

- raw companies by country/play/source;
- eligible opportunities by stage;
- domain coverage;
- website evidence coverage;
- buyer coverage;
- contact-ready coverage;
- review-ready and outreach-ready counts;
- source freshness;
- pipeline throughput for 24h/7d/30d;
- worker queue depth and failures;
- provider cost/budget;
- sends, deliveries, bounces, replies, meetings, proposals, wins;
- conversion by cohort/play/source/message variant;
- alerts and paused systems.

Every metric links to the filtered underlying records.

## 16.3 Company Universe

Build a server-side/cursor-paginated explorer for 10K+ records:

- 50/100 row page sizes;
- fast full-text search;
- country/play/source/status/classification/legal-form/location filters;
- employee/technician/score ranges;
- domain/evidence/buyer/contact coverage filters;
- freshness and failure filters;
- saved views;
- column chooser;
- bulk select across current filtered set through a server-side selection token;
- bulk enqueue/re-evaluate/export/suppress/archive actions;
- no loading all rows into Python then sorting.

## 16.4 Opportunity detail workspace

Tabs/panels:

```text
Overview
Identity
Locations
Domains & Website
Evidence
Triggers & Technology
People & Buyers
Contacts
Compliance
Scores
Messages
Campaigns & Touches
Tasks
Audit & Source Lineage
```

For every claim, provide “why,” evidence source, observed date, confidence, and contradiction.

## 16.5 Review Queues

Separate queues for:

- identity/duplicate review;
- domain ambiguity;
- ICP eligibility;
- evidence verification;
- buyer confirmation;
- contact/catch-all review;
- compliance review;
- message approval;
- dead-letter/retry review.

Each queue needs keyboard-friendly next/previous actions, batch decisions where safe, notes, reasons, SLA/age, and audit events.

## 16.6 Runs and Sources

Create an operational run center with:

- play/source/run status;
- stage progress;
- accepted/rejected/error counts;
- throughput;
- checkpoint;
- retries;
- rate-limit state;
- last success;
- next schedule;
- cost;
- pause/resume/cancel/replay controls;
- sample rejected records and reason distribution.

Source pages must show real health checks, configuration readiness, credentials present/missing without exposing them, data license/use notes, freshness, last snapshot, and quality/coverage contribution.

## 16.7 Campaign UI

- cohort builder from saved views;
- campaign capacity preview;
- policy/suppression preflight;
- message variant preview;
- claim/evidence inspection;
- approval workflow;
- send calendar;
- touch state;
- reply/bounce/opt-out processing;
- performance by play/cohort/variant;
- pause and kill controls.

## 16.8 Design quality

- consistent spacing/type/contrast;
- WCAG-conscious keyboard/focus behavior;
- responsive desktop/tablet layouts;
- no fabricated static badges;
- clear loading, empty, partial, stale, blocked and error states;
- progressive HTMX updates with accessible fallbacks;
- charts only when they improve decisions;
- dense data tables with sticky headers and preserved filters;
- no full React rewrite unless a measured blocker is proven.

---

# 17. API requirements

Create versioned JSON APIs under `/api/v1` and keep HTML routes thin. Include OpenAPI in non-production or protected internal mode.

Required groups:

```text
/api/v1/plays
/api/v1/sources
/api/v1/source-runs
/api/v1/pipeline-runs
/api/v1/work-items
/api/v1/companies
/api/v1/opportunities
/api/v1/evidence
/api/v1/people
/api/v1/contacts
/api/v1/reviews
/api/v1/scores
/api/v1/campaigns
/api/v1/sequences
/api/v1/touches
/api/v1/inbound
/api/v1/suppressions
/api/v1/analytics
/api/v1/settings/status
```

Use validated filter schemas, cursor pagination, stable sort keys, consistent error envelopes, idempotency keys for mutations, optimistic locking/version fields for human edits, and audit events.

Do not expose secrets or full personal contact data in list endpoints. Reveal sensitive values only to authorized users in detail workflows.

---

# 18. Exact repository change map

The names below are directional. Reuse suitable existing modules, but do not leave business logic split between legacy and new paths.

## 18.1 Replace/refactor

```text
app/jobs/ingestion.py                  → orchestrator only; no France-only global default
app/jobs/scheduler.py                  → Celery Beat schedules / durable orchestration
app/routers/sourcing.py                → play-aware run creation; no BackgroundTasks
app/services/__init__.py               → split monolith into domain services
app/scoring.py                          → remove/deprecate after V4 parity
app/scoring_v3.py                       → migrate to versioned scoring service
app/services/scoring_engine.py          → complete canonical V4 engine
app/sources/companies_house.py          → real API enrichment adapter; no runtime fixture fallback
app/sources/decp_adapter.py             → real incremental adapter; remove fabricated record
app/sources/sirene_adapter.py           → real config/health/checkpoint behavior
app/templates/sourcing.html             → real source/play controls and run state
app/templates/market_plays.html         → match actual schema and live state
app/templates/dashboard.html            → live funnel/ops metrics
app/main.py                              → no password reset every startup; no durable scheduler in web
```

## 18.2 Add packages/modules

```text
app/domain/companies/
app/domain/opportunities/
app/domain/evidence/
app/domain/people/
app/domain/contacts/
app/domain/compliance/
app/domain/scoring/
app/domain/campaigns/
app/pipelines/
app/workers/
app/sources/companies_house_bulk.py
app/sources/companies_house_api.py
app/sources/sirene_stock.py
app/sources/sirene_api.py
app/sources/find_tender_ocds.py
app/sources/contracts_finder_ocds.py
app/sources/bodacc.py
app/sources/decp.py
app/sources/search_provider.py
app/sources/website.py
app/sources/commercial_provider.py
app/services/company_resolution.py
app/services/domain_discovery.py
app/services/website_crawl.py
app/services/evidence_extraction.py
app/services/technology_detection.py
app/services/trigger_intelligence.py
app/services/buyer_intelligence.py
app/services/contact_waterfall.py
app/services/readiness.py
app/services/message_claims.py
app/services/source_health.py
app/services/analytics_v2.py
app/routers/api_v1/
app/templates/universe/
app/templates/opportunities/
app/templates/reviews/
app/templates/runs/
app/templates/sources/
app/templates/campaigns/
app/templates/operations/
```

## 18.3 Infrastructure additions

```text
redis service
dedicated worker services
beat service
health/readiness probes
worker startup scripts
raw-data mounted volume
backup inclusion for raw manifests and database
structured log configuration
optional prometheus metrics endpoint/internal monitor
```

## 18.4 Alembic plan

Continue after current head with small reversible revisions, for example:

```text
008_pipeline_jobs_and_source_manifests
009_company_fact_and_website_models
010_people_contact_reconciliation
011_scoring_v4_and_readiness
012_campaign_sequences_and_provider_events
013_saved_views_audit_and_bulk_actions
014_legacy_backfill_and_mapping
015_indexes_extensions_and_constraints
016_normalized_write_cutover
017_legacy_read_only_compatibility
```

Do not create one giant migration. Test upgrades from the actual production head and a full restore.

---

# 19. Performance and capacity requirements

At minimum, prove the following on a production-like PostgreSQL environment:

- import/normalize 10,000 company rows without process memory growth proportional to full dataset;
- rerun same snapshot with zero duplicate companies/opportunities;
- server-side filtered list p95 under 500 ms for common indexed filters at 10K records;
- company detail p95 under 800 ms excluding live external calls;
- enqueue 10K work items idempotently;
- workers recover stale leases and continue after restart;
- no source exceeds configured rate budget;
- batch can pause and resume from checkpoint;
- source failure does not take down web UI;
- exports stream rather than building entire files in memory;
- no N+1 query explosion on list/detail pages;
- background processing has bounded concurrency and connection pools.

Use actual load/integration tests and record hardware/context. Do not invent benchmark results.

---

# 20. Security, privacy and compliance requirements

- Preserve CSRF, trusted hosts, secure cookies and production docs restrictions.
- Add role-based authorization (`admin`, `researcher`, `outreach_operator`, `viewer/auditor`).
- Create admin only when absent; password rotation is an explicit command/workflow.
- Add session invalidation/password-change handling.
- Add login throttling and audit.
- Keep secrets in environment/Docker secrets; redact diagnostics.
- Validate file uploads, CSV size, type and formula-injection risks.
- Enforce SSRF protections in every fetcher including Playwright.
- Maintain suppression at email, domain, person, company identifier and campaign levels.
- Re-evaluate policy immediately before sending.
- Store source and collection notice/information state where required.
- Implement export/delete/anonymize workflows and retention schedules.
- Disable tracking pixels by default; do not assume B2B email permission covers tracking.
- Keep legal rules in versioned configurable policies with documented human review; code must not claim to provide legal advice.
- UK corporate and French professional-relevance logic must be conservative and source-backed.
- Germany/Netherlands and other jurisdictions remain disabled until explicit policy implementation and review.

---

# 21. Testing requirements

## 21.1 Baseline first

Before edits, record:

```bash
git status --short
git branch --show-current
git rev-parse HEAD
python --version
pytest -q
ruff check .
python -m compileall app tests
alembic heads
alembic history
docker compose config
```

The current audit environment could compile the latest source, but could not install all declared packages from its restricted package mirror. Antigravity must establish the project’s declared environment and rerun the suite. Do not copy an old “140 tests passed” claim.

## 21.2 Required test layers

- pure unit tests;
- SQL/PostgreSQL integration tests;
- Alembic fresh and upgrade-path tests;
- source adapter contract tests;
- recorded official-source fixtures with capture date and sanitization;
- no network in unit tests;
- live-source smoke tests behind explicit flag;
- job idempotency/retry/stale-lease tests;
- identity/dedupe/merge tests;
- domain/SSRF/DNS-rebinding tests;
- evidence claim/provenance tests;
- score/gate/calibration tests;
- compliance/suppression tests;
- campaign stop and provider-event tests;
- browser E2E tests using Playwright;
- accessibility smoke checks;
- 10K load test;
- backup/restore test;
- deployment smoke and rollback test.

## 21.3 Invariants

Add tests that make these impossible:

- production fixture lead creation;
- UK selection invoking France ingestion;
- run without persisted source run/checkpoint;
- duplicate company for same official identifier;
- score bypass of hard gate;
- guessed/catch-all personal email auto-approved;
- send after opt-out/reply/bounce/suppression;
- message claim without evidence;
- public UI claiming source healthy when no real health result exists;
- background task loss represented as success;
- startup resetting admin password;
- list endpoint loading all 10K records into memory.

---

# 22. Required implementation phases and release gates

Do not jump directly to more scrapers. Execute in this order.

## Phase 0 — preserve and understand

Deliver:

- branch and baseline;
- repository map;
- current data-flow diagram;
- current production topology;
- gap matrix against this prompt;
- production database revision and data counts if access exists.

Gate: no implementation begins without a recorded baseline and backup strategy.

## Phase 1 — remove falsehoods and production hazards

- remove/disable fabricated source records outside tests;
- make source health truthful;
- fix play/mode routing;
- fix broken market-play page contract;
- remove static health/compliance claims;
- stop startup password reset;
- disable durable work through BackgroundTasks/APScheduler once replacement is ready;
- correct docs that claim features not implemented.

Gate: UI cannot claim UK sourcing unless a real UK run succeeds.

## Phase 2 — durable job/runtime foundation

- Redis/Celery topology;
- persisted pipeline/work-item state;
- retries/checkpoints/leases/DLQ;
- run monitor;
- source budgets;
- worker health.

Gate: kill and restart workers during a test run; processing resumes without duplicate side effects.

## Phase 3 — normalized write path

- complete schema;
- migrations/backfill;
- canonical repositories/services;
- dual-read comparison;
- normalized API endpoints.

Gate: new discovery records flow from SourceRecord to Company to Opportunity without writing the legacy Prospect aggregate as the primary source.

## Phase 4 — bulk official discovery

- Companies House monthly bulk;
- Sirene stock;
- real DECP;
- UK OCDS contracts;
- BODACC;
- current-profile refresh adapters.

Gate: ingest a controlled 10K candidate dataset, rerun idempotently, and show source/run statistics.

## Phase 5 — domain and website engine

- domain candidates/provider abstraction;
- verification waterfall;
- safe crawler;
- content store/freshness;
- domain review queue.

Gate: ≥95% official-domain precision on labeled test set.

## Phase 6 — evidence, trigger and technology intelligence

- taxonomy;
- structured extraction;
- negative evidence;
- optional LLM tier;
- source-linked claims;
- operator evidence review.

Gate: zero unsupported personalized claims in test cohort.

## Phase 7 — buyer/contact waterfall

- people/roles;
- current-role reconciliation;
- contact points and verification dimensions;
- provider adapters;
- manual tasks;
- review UI.

Gate: no guessed or catch-all personal address reaches outreach-ready automatically.

## Phase 8 — scoring V4 and calibration

- single scoring engine;
- hard gates;
- immutable snapshots;
- 100-company gold set;
- quality metrics and thresholds.

Gate: required precision thresholds pass or system remains pilot/paused.

## Phase 9 — 10K frontend and operator workflows

- command center;
- universe explorer;
- opportunity workspace;
- reviews;
- runs/sources/data quality/operations;
- saved views and bulk actions.

Gate: browser E2E and 10K UI performance pass.

## Phase 10 — campaigns and controlled automation

- sequences/drafts/claims;
- approval workflow;
- outbound provider;
- inbound/bounce/opt-out;
- stop rules;
- deliverability status;
- kill switch.

Gate: full test mailbox flow passes; no real campaign is activated automatically.

## Phase 11 — production hardening and deployment

- security review;
- backup/restore;
- observability;
- release gate;
- migration rehearsal;
- deploy/canary/smoke/rollback.

Gate: production deployment record and rollback evidence exist.

## Phase 12 — controlled real-data bootstrap

- load official raw universe;
- select market cohorts;
- validate 100-company gold set;
- run top-priority enrichment budgets;
- create first 20-message approved pilot;
- review results before scaling.

Gate: operator explicitly approves real sending.

---

# 23. Operator-facing success workflow

At completion, the operator must be able to:

1. Open Sources and see which connectors are configured, healthy, blocked or stale.
2. Create a pipeline run for a market play and source set.
3. Watch 10K companies ingest, normalize and deduplicate with truthful progress.
4. Open Company Universe and save a cohort view.
5. Enqueue domain/evidence/buyer/contact enrichment for the filtered cohort.
6. Review ambiguous identities/domains/contacts through dedicated queues.
7. Inspect one opportunity and trace every score and message claim to a source.
8. Approve or reject outreach readiness.
9. Add approved records to a campaign with capacity/policy preflight.
10. Approve drafts and run a controlled sequence.
11. See replies, bounces, opt-outs, meetings and proposals stop/update the sequence automatically.
12. Review weekly funnel metrics and identify whether failures come from sources, fit, domains, contacts, messaging, deliverability, calls, proposals or offer.

Create `docs/operator/LEVEL_300_OPERATOR_PLAYBOOK.md` with exact screenshots or route descriptions and commands.

---

# 24. Required documentation and evidence artifacts

Create/update:

```text
docs/level300/PROJECT_UNDERSTANDING.md
docs/level300/CURRENT_STATE_AUDIT.md
docs/level300/GAP_MATRIX.md
docs/level300/TARGET_ARCHITECTURE.md
docs/level300/DATA_MODEL.md
docs/level300/SOURCE_CATALOG.md
docs/level300/PIPELINE_DAG.md
docs/level300/IDENTITY_AND_DEDUPE.md
docs/level300/EVIDENCE_TAXONOMY.md
docs/level300/SCORING_AND_GATES.md
docs/level300/COMPLIANCE_AND_SUPPRESSION.md
docs/level300/CAMPAIGN_AND_DELIVERABILITY.md
docs/level300/FRONTEND_WORKFLOWS.md
docs/level300/SECURITY_REVIEW.md
docs/level300/TEST_REPORT.md
docs/level300/LOAD_TEST_REPORT.md
docs/level300/LIVE_SOURCE_VALIDATION.md
docs/level300/MIGRATION_AND_BACKFILL_REPORT.md
docs/level300/DEPLOYMENT_RECORD.md
docs/level300/ROLLBACK_RUNBOOK.md
docs/operator/LEVEL_300_OPERATOR_PLAYBOOK.md
docs/level300/KNOWN_LIMITATIONS.md
docs/level300/CHANGELOG.md
```

Reports must contain actual commands/results. Do not write aspirational checkmarks.

---

# 25. Required final response from Antigravity

At the end, return:

1. concise commercial/product understanding;
2. exact branch and commits;
3. implemented phases;
4. files/migrations/services added and changed;
5. real test/lint/migration/load/browser results;
6. live-source results and counts;
7. deployment state and domain smoke results;
8. production data counts by funnel stage;
9. credentials/connectors still blocked;
10. known limitations and risks;
11. exact operator next commands/actions;
12. explicit statement whether real outbound sending remains disabled;
13. links/paths to all evidence artifacts.

Do not claim “fully operational,” “10K ready,” “production ready,” “compliant,” “healthy,” or “Level 300” unless the corresponding gates and evidence are complete.

---

# 26. Absolute prohibitions

Do not:

- fabricate prospects, companies, contracts, people, emails, source health or conversion metrics;
- leave runtime fixture fallback enabled in production;
- scrape or automate LinkedIn;
- bypass robots, authentication, CAPTCHA, rate limits or access controls;
- scrape consumer search pages when an authorized API/provider is required;
- treat public availability as automatic outreach permission;
- auto-send to sole traders/individual subscribers under a corporate-only policy;
- auto-send guessed/catch-all personal emails;
- personalize with unsupported statements;
- use static UI copy as operational status;
- create a giant unreviewable migration or commit;
- rewrite the stack without evidence;
- add Kafka, Elasticsearch, Kubernetes or microservices merely to sound advanced;
- expose Flower, Redis, PostgreSQL, internal metrics or admin tools publicly;
- send real messages without explicit approval;
- declare completion after only tests or documentation.

---


---

# END OF AUTHORITATIVE IMPLEMENTATION ORDER
