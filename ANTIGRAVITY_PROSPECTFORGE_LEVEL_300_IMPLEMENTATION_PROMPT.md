# ANTIGRAVITY MASTER EXECUTION PROMPT — PROSPECTFORGE LEVEL 300

**Purpose:** Paste this entire document into Antigravity with the latest `ProspectForge-main(3)` repository opened as the workspace. Do not shorten it. This prompt supersedes the older prompt currently under `docs/antigravity/` whenever the two conflict.

**Execution standard:** This is an implementation order, not a request for recommendations, mockups, a report, or a partial prototype. Antigravity must inspect, design, implement, migrate, test, document, deploy when access exists, and leave the application operational.

---

# 0. Operator inputs

Use existing repository and environment values when safely discoverable. Never invent credentials, silently use test data in production, or expose secrets in output, screenshots, commits, logs, fixtures, or documentation.

```text
REPOSITORY_PATH=<ABSOLUTE_PATH_TO_LATEST_PROSPECTFORGE_REPOSITORY>
TARGET_BRANCH=antigravity/prospectforge-level-300
PRODUCTION_DOMAIN=prospect.elevya.tech
VPS_SSH_TARGET=<DISCOVER_OR_ASK_ONLY_IF_DEPLOYMENT_IS_BLOCKED>
VPS_DEPLOY_PATH=<DISCOVER_FROM_CURRENT_DEPLOYMENT; DEFAULT /opt/prospectforge>
DEPLOY_NOW=<yes|no; infer yes only when explicitly authorized>
ADMIN_EMAIL=<EXISTING PRODUCTION ADMIN>
PRIMARY_MARKETS=GB,FR
TARGET_RAW_COMPANY_UNIVERSE=10000
TARGET_WEEKLY_REVIEW_READY=100
TARGET_WEEKLY_OUTREACH_READY=20-50
OUTBOUND_AUTOMATION_MODE=approval_gated
```

If an external API key, paid provider account, DNS change, email mailbox, or SSH credential is absent, implement the adapter, settings, validation, UI, tests, dry-run behavior, and operator setup documentation. Do not substitute fabricated data. Mark the connector `blocked_credentials` and continue with all work that does not require the secret.

---

# 1. Role and authority

Act as all of the following simultaneously:

- principal product engineer;
- data-platform architect;
- acquisition-operations architect;
- backend engineer;
- frontend/UI engineer;
- data-quality engineer;
- security and privacy reviewer;
- DevOps and reliability engineer;
- QA and release lead;
- commercial systems designer.

You have authority to make routine, reversible repository changes without asking for permission. Ask only before an irreversible production-data operation, real email transmission, external purchase, DNS change, public network exposure, or destructive infrastructure action.

Do not stop after analysis. Do not say “this is too large.” Implement the phases in priority order and leave truthful evidence of what is complete, blocked, deferred, or failed.

---

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

# 27. Embedded architecture and implementation specification

The specification below was prepared for the prior multi-market rebuild. Treat it as mandatory detailed architecture where it does not conflict with the current Level 300 directives above. The directives above win on current repository facts, bulk-volume architecture, durable workers, source truth, and release order.

# ProspectForge — UK/France Field-Operations Acquisition Engine Master Rebuild Specification

**Document status:** Implementation master specification  
**Prepared:** 21 July 2026  
**Repository reference:** Earlier architecture specification; the live implementation target is the latest repository supplied with this prompt.  
**Historical baseline note:** An earlier archive reported 140 passing tests. Do not reuse that claim for the latest repository; rerun and record the complete current baseline.  
**Primary objective:** Convert the current France-specific prospecting application into a controlled, multi-market evidence and contact-acquisition operating system for high-quality UK and French field-operations opportunities.  
**Commercial standard:** Correct company → genuine operational opportunity → correct buyer → defensible contact → policy-approved message → human approval → controlled touch → measurable result.  
**Safety standard:** Bulk official-company discovery is required; indiscriminate personal-data scraping, guessed-address auto-send, LinkedIn automation, unsupported personalization, and score-based bypass of legal or human gates are prohibited. Volume may scale only by stage-specific quality thresholds.

---

# Table of contents

1. Executive decision
2. Baseline audit and repository truth
3. Commercial mission, non-goals, and operating doctrine
4. Initial market plays and cohort strategy
5. Target system architecture
6. Domain model redesign
7. Legacy migration and compatibility strategy
8. Market-play configuration system
9. Source-adapter framework
10. UK company-source implementation
11. France source implementation
12. Commercial import and manual-source implementation
13. Company identity and deduplication engine
14. Domain resolution and official-site verification
15. Website evidence and technology intelligence
16. Field-team and operational-complexity estimation
17. Evidence taxonomy, provenance, and lifecycle
18. Trigger intelligence
19. Buyer-role and person-resolution engine
20. Contact-intelligence localization and verification
21. Compliance policy engine
22. Scoring, hard gates, and qualification
23. Gold-set labeling and calibration
24. Messaging and personalization engine
25. Campaign, sequence, and touch state machines
26. Deliverability and sending infrastructure
27. Operator interface and workflow
28. API contracts
29. Jobs, queues, scheduling, and resilience
30. Analytics, funnel integrity, and experimentation
31. Security, privacy, audit, and retention
32. Testing strategy
33. Exact repository change map
34. Alembic migration plan
35. Deployment, production reconciliation, and rollback
36. Controlled live-pilot protocol
37. 30/60/90-day implementation plan
38. Prioritized implementation backlog
39. Codex/Antigravity execution protocol
40. Release gates and definition of done
41. Source and reference appendix

---

# 1. Executive decision

ProspectForge must become a **high-volume company-intelligence and qualification engine**, but it must not become an indiscriminate personal-contact scraper. Its strongest existing design choice is the opposite: normalized contact evidence, bounded official-site discovery, confidence states, human qualification, suppression, and cautious treatment of guessed addresses. The rebuild must preserve those controls while replacing the France-only assumptions with explicit market, jurisdiction, source, language, and campaign abstractions.

The repository is internally consistent, but “tests pass” does not establish commercial readiness. The current baseline proves that the existing declared behavior is stable. It does not prove:

- correct UK company resolution;
- acceptable precision on the new ICP;
- official-domain accuracy;
- field-team-size estimation;
- buyer-role localization;
- contact coverage in UK and France;
- country-specific policy decisions;
- deliverability;
- reply quality;
- campaign stop behavior against real providers;
- production parity with the revision referenced on the VPS;
- conversion into qualified calls or paid work.

The target product is an **evidence-driven acquisition operating system** with six bounded layers:

1. **Market definition:** versioned UK and France plays.
2. **Company intelligence:** official identity, legal form, classification, locations, domain, operational evidence, and estimates.
3. **Buyer/contact intelligence:** current relevant people and source-backed contact points.
4. **Policy and qualification:** jurisdiction decision, suppression, hard gates, human approval, and evidence-backed scoring.
5. **Campaign execution:** localized drafts, approval, sequence state, stop rules, provider events, and controlled sending.
6. **Learning:** gold-set quality metrics, cohort funnel, message experiments, loss reasons, and commercial outcomes.

## 1.1 Primary implementation principle

No field should exist merely because a source happened to provide it. Every stored fact must have:

- a normalized business meaning;
- source and retrieval time;
- confidence or verification state;
- jurisdiction and play context where relevant;
- expiry/refresh behavior;
- downstream-use rules.

## 1.2 Primary commercial principle

ProspectForge must find companies that have evidence of a **custom/integration opportunity**, not merely companies in a field-service industry. A list of HVAC companies is not a qualified market. The engine must identify operational complexity, system fragmentation, trigger, buyer, and contactability.

---

# 2. Baseline audit and repository truth

## 2.1 Verified strengths

The audited archive contains a valuable foundation:

- FastAPI application structure;
- SQLAlchemy/Alembic persistence;
- authenticated operator UI;
- market-play and evidence concepts;
- prospect records and qualification review;
- append-oriented outreach event history;
- suppression entries;
- ingestion-run records;
- normalized `ContactPerson`, `ContactPoint`, `ContactEvidence`, discovery run, verification event, and manual-review models;
- official-domain bounded crawling;
- SSRF and network-safety controls;
- HTML/PDF extraction;
- JSON-LD and page-content extraction;
- phone, email, form, and person discovery;
- DNS/MX and optional deliverability verification integration;
- safe separation between discovered, guessed, verified, approved, and usable contact states;
- human qualification gates;
- backups, restore, rollback, deployment, and smoke-test scaffolding;
- deterministic test baseline.

The clean test result is a useful starting release baseline:

```text
pytest: 140 passed
ruff check .: All checks passed
```

Record the exact commit/archive checksum before modifications.

## 2.2 Structural blockers

### France-only market play

`app/plays/field_service.py` and `app/plays/__init__.py` assume one French field-service play. Configuration includes French NAF/CPV codes, French registry queries, French role vocabulary, French evidence keywords, and French offers.

### Global default leakage

`app/jobs/ingestion.py` imports and uses `DEFAULT_PLAY_CODE`. This allows new ingestion to silently inherit the wrong market. A market play must be explicit in every run and persisted in every resulting record.

### French-specific company identity

`Prospect` contains `siren`, `siret`, `naf_code`, `department`, and other source-shaped fields. UK Companies House numbers, legal forms, SIC classifications, and locations do not fit cleanly. Identity and classifications need normalized child tables.

### Flat prospect duplication

Company facts, person/contact facts, workflow/evidence, and outreach state coexist in ways that create ambiguity and future conflicts. The normalized contact subsystem is stronger than the flat legacy fields; the company subsystem needs the same treatment.

### Messaging localization gap

`app/messaging.py` is French-specific and insufficiently tied to evidence provenance. It should generate message drafts from approved evidence, not infer broad pain claims from industry alone.

### Outreach model gap

`OutreachEvent` records history but does not provide a robust campaign/sequence state machine. Missing concepts include campaign, cohort, sequence version, step, approved draft, scheduled touch, provider delivery state, stop reason, experiment assignment, and outcome reason.

### UI coupling

Current templates and sourcing screens expose French source concepts directly. The target UI must operate on play, market, evidence, and source-adapter status without hardcoded DECP/Sirene language outside source-specific detail views.

### Unproven live quality

Repository documentation acknowledges that a live 20-prospect pilot has not validated precision and coverage. The rebuild must add a gold-set calibration framework before volume.

### Production revision uncertainty

The archive and the production state referenced elsewhere are not proven identical. A production revision such as `pfcc50_20260720` cannot be assumed to exist in the uploaded archive. Production must be inventoried and reconciled before any migration or deployment.

## 2.3 Documentation truth defects

- README still identifies French operational SMEs as the only market.
- GUIDE contains stale IT/cyber and legacy registry material.
- archived V3 and contact-intelligence specifications contain useful concepts but may not reflect current runtime.
- deployment claims must be tied to actual scripts, commit, schema revision, environment, and smoke evidence.

## 2.4 Required baseline artifact

Before coding, generate:

```text
runtime/baseline/
  archive_sha256.txt
  git_status.txt
  git_commit.txt
  python_version.txt
  dependency_lock_hash.txt
  pytest.txt
  ruff.txt
  route_inventory.json
  model_inventory.json
  migration_inventory.json
  production_reconciliation_status.json
```

---

# 3. Commercial mission, non-goals, and operating doctrine

## 3.1 Mission

Generate a small number of high-confidence, explainable, compliant, and contact-ready opportunities for Anass’s field-operations offer in the UK and France, then learn which cohorts, evidence patterns, buyers, and messages create qualified commercial conversations.

## 3.2 The unit of value

The unit is not a lead, email, or contact. It is a **qualified opportunity packet** containing:

- resolved legal company;
- official domain;
- active and eligible entity status;
- market-play match;
- vertical evidence;
- operational-complexity evidence;
- pain, trigger, or technology opportunity;
- current relevant buyer;
- source-backed contact point or safe contact route;
- jurisdiction policy decision;
- suppression result;
- message draft with evidence citations;
- human approval record;
- next-step state.

## 3.3 Non-goals

The first release will not:

- scrape LinkedIn or automate LinkedIn actions;
- crawl the open web without domain and request bounds;
- buy or infer massive email lists and send automatically;
- target sole traders in the first UK pilot;
- enable Germany or Netherlands cold email by default;
- treat employee count as technician count;
- guess operational pain from industry alone;
- guarantee email deliverability;
- use LLM-generated facts without source evidence;
- optimize for vanity contact volume or indiscriminate sending;
- become a general-purpose sales engagement platform;
- replace a CRM/accounting system;
- auto-approve prospects because a score is high;
- allow an operator to bypass suppression or legal policy without an audited override.

## 3.4 Bounded automation doctrine

Automation is allowed for:

- source retrieval through permitted interfaces;
- normalization;
- identity/domain candidate generation;
- evidence extraction;
- classification and estimates with confidence;
- contact discovery on official sites;
- DNS/MX and configured verification;
- message drafting from approved evidence;
- scheduled processing;
- provider event ingestion;
- metrics and reports.

Human approval is required for:

- final company/ICP acceptance in the pilot;
- final buyer choice when evidence is ambiguous;
- guessed or pattern-derived addresses;
- first-touch message;
- compliance exceptions;
- campaign activation;
- material personalization claims;
- scale increases;
- any new jurisdiction.

---

# 4. Initial market plays and cohort strategy

## 4.1 Active play 1 — UK field-operations integration

**Code:** `FIELD_OPERATIONS_UK_V1`  
**Jurisdiction:** `GB`  
**Language:** `en-GB`  
**Status:** pilot  
**Entity policy:** Ltd/LLP and other reviewed corporate entities; exclude sole traders and ambiguous partnerships in pilot.

### Initial sectors

- commercial HVAC and refrigeration;
- fire and security systems installation/maintenance;
- electrical maintenance and technical services;
- industrial maintenance;
- technical building services/facilities maintenance;
- specialist inspection/service companies with mobile technicians.

### UK SIC candidate families

Store exact codes and labels in configuration after validating current official definitions. Candidate families may include plumbing/heating/air-conditioning installation, electrical installation, repair of machinery/equipment, facilities support, security systems service, and related technical service classes. Do not rely on SIC alone; website evidence must confirm the actual operating model.

### Entity-size target

- estimated 10–75 field technicians;
- company headcount is a prior only;
- include companies with visible multi-team/branch/service-contract complexity even when technician count is unknown;
- exclude microbusinesses with no coordination layer.

### Priority buyers

1. Managing Director / Founder / Owner-Director.
2. Operations Director / Head of Operations.
3. Service Director / Service Manager.
4. Field Service Manager.
5. Technical Director.
6. General Manager.

### Opportunity patterns

- disconnected FSM/CRM/accounting/stock/document tools;
- coordinator/dispatcher hiring;
- new branch or service region;
- acquisition or rebrand;
- customer portal/digital transformation initiative;
- recurring maintenance growth;
- compliance documents and job evidence handled separately;
- invoice or reporting handoff friction;
- failed or partial software implementation.

## 4.2 Active play 2 — France field-operations integration

**Code:** `FIELD_OPERATIONS_FR_V2`  
**Jurisdiction:** `FR`  
**Language:** `fr-FR`  
**Status:** pilot  
**Migration:** replaces but does not silently mutate `FIELD_SERVICE_OPERATIONS_FR`.

### Initial sectors

- froid commercial / réfrigération;
- CVC et maintenance technique;
- maintenance électrique;
- sécurité/incendie;
- maintenance industrielle;
- services techniques du bâtiment;
- SAV technique multi-intervenants.

### Priority buyers

1. Gérant / Président / Directeur général.
2. Directeur des opérations.
3. Responsable d’exploitation.
4. Responsable SAV / Responsable service.
5. Directeur technique.
6. Responsable maintenance.

### Opportunity patterns

- planning, comptes rendus, pièces, documents, devis/factures split across tools;
- recrutement planificateur/coordinateur/SAV;
- marché or contract win relevant to service delivery;
- agency/branch expansion;
- migration ERP/CRM/logiciel métier;
- portail client or digitalisation initiative;
- recurring contracts and compliance evidence.

## 4.3 Disabled future plays

Create placeholders but keep inactive:

- `FIELD_OPERATIONS_DE_V0` — disabled pending legal/channel review and source design.
- `FIELD_OPERATIONS_NL_V0` — disabled pending legal/channel review and source design.

The application must prevent campaign activation for disabled plays.

## 4.4 Cohort order

### Cohort UK-A

15 commercial HVAC/refrigeration companies.

### Cohort UK-B

15 electrical, fire/security, industrial, or technical maintenance companies.

### Cohort FR-A

10 refrigeration/CVC/service companies with strong official-site evidence.

### Cohort FR-B

10 industrial/electrical/security maintenance companies.

Start with a 50-company gold set, then 20 initial sends, then 30 additional sends only after review.

---

# 5. Target system architecture

## 5.1 Logical architecture

```mermaid
flowchart LR
    A[Market Play Registry] --> B[Source Runs]
    B --> C[Raw Source Records]
    C --> D[Company Identity Resolution]
    D --> E[Official Domain Resolution]
    E --> F[Website and Trigger Evidence]
    F --> G[Operational Fit and Estimates]
    G --> H[Buyer and Contact Intelligence]
    H --> I[Compliance Policy Decision]
    I --> J[Scoring and Hard Gates]
    J --> K[Human Qualification]
    K --> L[Message Draft]
    L --> M[Human Approval]
    M --> N[Campaign Touch]
    N --> O[Provider Events and Replies]
    O --> P[Funnel, Quality, and Gold-Set Learning]
```

## 5.2 Layer boundaries

### Configuration layer

Versioned market plays, policy versions, scoring profiles, source plans, role dictionaries, message templates, and campaign defaults.

### Acquisition layer

Source adapters create immutable or append-oriented source records. They do not directly overwrite canonical company truth.

### Resolution layer

Resolves company identity, domain, people, and contacts using explainable evidence.

### Evidence layer

Stores observations with provenance, confidence, timestamps, and expiry.

### Decision layer

Computes fit, policy, qualification gates, scores, and human decisions.

### Execution layer

Campaigns, sequences, drafts, approvals, touches, provider events, replies, and stop rules.

### Learning layer

Gold labels, quality metrics, funnel cohorts, experiments, and loss reasons.

## 5.3 Architectural constraints

- PostgreSQL is the system of record in production.
- Alembic migrations are forward and downgrade tested.
- External source responses are never treated as canonical without normalization/resolution.
- Provider-specific identifiers remain in source/provider tables.
- Jobs are idempotent and resumable.
- Every automated decision stores rule/model version and input evidence IDs.
- Every operator override is audited.
- Every campaign touch is immutable after provider submission; corrections create new events.
- PII is minimized and retained according to policy.
- No contact is sendable merely because a string resembles an email address.

---

# 6. Domain model redesign

The exact ORM implementation may be split across modules, but the following business entities must exist.

## 6.1 `companies`

Canonical legal/operating entity.

| Field | Type | Rules |
|---|---|---|
| `id` | UUID | Primary key |
| `canonical_name` | text | Normalized display name |
| `legal_name` | text nullable | Official name |
| `country_code` | char(2) | ISO 3166-1 alpha-2 |
| `jurisdiction_code` | text | e.g. GB-EW, GB-SCT, FR |
| `legal_form_code` | text nullable | normalized controlled vocabulary |
| `entity_status` | enum | active, inactive, dissolved, unknown |
| `incorporated_at` | date nullable | sourced |
| `dissolved_at` | date nullable | sourced |
| `primary_domain_id` | UUID nullable | points to approved company domain |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |
| `merged_into_company_id` | UUID nullable | dedup tombstone |
| `record_version` | integer | optimistic/audit use |

Constraints:

- country required;
- merged records cannot be campaign eligible;
- canonical name is not globally unique;
- legal status must have source evidence.

## 6.2 `company_identifiers`

| Field | Notes |
|---|---|
| `company_id` | canonical company |
| `scheme` | `companies_house_number`, `siren`, `siret`, `vat`, `internal`, future `kvk` etc. |
| `value_normalized` | normalized value |
| `value_display` | original formatting |
| `is_primary` | one primary per scheme/company |
| `source_record_id` | evidence source |
| `verified_at` | verification timestamp |

Unique constraint: `(scheme, value_normalized)` for schemes globally unique in their jurisdiction.

## 6.3 `company_names`

Store legal, trading, previous, and source-observed names with validity dates and source.

## 6.4 `company_classifications`

| Field | Notes |
|---|---|
| `scheme` | `UK_SIC_2007`, `FR_NAF_REV2`, `NACE_REV2` |
| `code` | normalized |
| `label` | snapshot label |
| `is_primary` | source-specific |
| `valid_from/valid_to` | optional |
| `source_record_id` | provenance |

Do not map classifications silently. Crosswalks need a separate versioned mapping table.

## 6.5 `company_locations`

- registered office;
- operating branch;
- service area;
- source-observed location;
- country, region, locality, postal code;
- geocode only where necessary and permitted;
- confidence and source.

## 6.6 `company_domains`

| Field | Notes |
|---|---|
| `company_id` | |
| `domain_normalized` | punycode/lowercase, no path |
| `domain_role` | primary, alternate, redirect, parent, brand, rejected |
| `verification_state` | candidate, verified, rejected, stale |
| `match_score` | explainable score |
| `match_reasons_json` | name, identifier, address, footer, source link etc. |
| `first_seen_at/last_verified_at` | |
| `source_record_id` | |

One verified primary domain per company per active period, with audited changes.

## 6.7 `company_estimates`

Do not put estimated employee/technician counts directly on `companies` without provenance.

| Field | Notes |
|---|---|
| `estimate_type` | employees, field_technicians, branches, vehicles, service_regions |
| `lower_bound` / `upper_bound` | numeric nullable |
| `point_estimate` | nullable |
| `method_code` | registry_band, jobs_count, team_page, fleet_text, manual, composite |
| `confidence` | 0–1 or controlled enum |
| `evidence_ids` | relationship table preferred |
| `observed_at` | |
| `expires_at` | |
| `play_version_id` | when play-dependent |

## 6.8 `source_connectors`

Configuration/registry of adapters:

- code;
- version;
- source type;
- country coverage;
- terms/reference URL;
- authentication mode;
- rate limit;
- enabled state;
- data classes allowed;
- retention policy;
- health status.

## 6.9 `source_runs`

Generalize `IngestionRun`:

- connector/version;
- play version;
- query/config hash;
- requested scope;
- cursor/checkpoint;
- counts discovered/normalized/rejected/errored;
- started/finished;
- status;
- error summary;
- idempotency key;
- operator/automation initiator.

## 6.10 `source_records`

Append-oriented normalized envelope around raw records:

| Field | Notes |
|---|---|
| `source_run_id` | |
| `external_id` | provider ID |
| `record_type` | company, officer, contract, job, page, contact etc. |
| `payload_json` | raw/filtered payload subject to retention |
| `payload_hash` | dedup/change detection |
| `observed_at` | source observation |
| `retrieved_at` | collection time |
| `source_url` | where appropriate |
| `http_metadata_json` | status/etag/last-modified |
| `normalization_status` | |
| `retention_class` | |

Avoid storing unnecessary full payloads containing excess personal data.

## 6.11 `market_plays` and `market_play_versions`

Separate stable identity from immutable versions.

### `market_plays`

- `id`;
- stable `code`;
- name;
- status: draft/pilot/active/paused/retired;
- owner;
- created/updated.

### `market_play_versions`

- `market_play_id`;
- semantic version;
- country/jurisdiction;
- language;
- ICP config;
- source plan;
- evidence taxonomy version;
- scoring profile;
- buyer-role profile;
- compliance policy version;
- message policy version;
- effective dates;
- immutable after activation.

Every resulting prospect/opportunity stores the exact play version, not only the stable play code.

## 6.12 `opportunities`

Replace the overloaded commercial meaning of `Prospect` over time.

| Field | Notes |
|---|---|
| `company_id` | canonical company |
| `play_version_id` | exact market hypothesis |
| `status` | discovered, enriching, review, accepted, rejected, contact_ready, campaign, replied, qualified, won, lost, suppressed, archived |
| `status_reason_code` | controlled |
| `owner_user_id` | |
| `priority` | calculated/manual |
| `latest_score_snapshot_id` | |
| `latest_policy_decision_id` | |
| `accepted_at/rejected_at` | |
| `dedupe_key` | company+play version |

Unique active opportunity per company/play version, with explicit reopen/version behavior.

## 6.13 Evidence tables

### `evidence_items`

- subject type and ID;
- evidence type code;
- normalized value/text;
- source record/page;
- source URL;
- observed/retrieved/valid dates;
- extractor/rule version;
- confidence;
- verification state;
- locale;
- sensitivity/retention class;
- content hash.

### `evidence_relations`

Link evidence to company, opportunity, person, contact, estimate, trigger, score component, message claim, or policy decision.

## 6.14 Person and employment model

Retain and evolve `ContactPerson` into normalized:

### `people`

- normalized name components;
- country/locale hints;
- privacy/retention state;
- merge support.

### `person_roles`

- person;
- company;
- raw title;
- normalized role code;
- seniority;
- department/function;
- current state;
- start/end dates where known;
- source evidence;
- confidence.

A person can have multiple source observations and historical roles.

## 6.15 Contact model

Retain the strong normalized concepts but clarify states:

### `contact_points`

- person or company association;
- type: email, phone, contact_form, general_email, other;
- normalized/display value;
- discovery method;
- publication state;
- identity-match state;
- deliverability state;
- policy-use state;
- utility state;
- source evidence;
- first/last seen;
- last verified;
- expires;
- suppression link.

### `contact_verification_events`

Immutable provider/manual checks with result, reason, provider version, timestamp, and raw-response retention class.

### `contact_manual_reviews`

Reviewer, decision, reason, evidence inspected, timestamp, prior/new state.

## 6.16 Compliance model

### `compliance_policies`

Versioned jurisdiction/channel policies.

### `compliance_decisions`

- subject opportunity/contact;
- channel;
- policy version;
- decision: allow_review, allow_send, deny, needs_review;
- legal-form classification;
- professional relevance;
- source-disclosure requirement;
- opt-out requirement;
- retention deadline;
- reasons and rule trace;
- reviewer override and justification.

## 6.17 Qualification model

Evolve `QualificationReview` into:

- gate definitions version;
- automated gate outputs;
- human answers;
- evidence references;
- decision/reason;
- reviewer;
- timestamp;
- re-review due date.

## 6.18 Scoring model

### `score_snapshots`

- opportunity;
- scoring profile/version;
- total;
- component scores;
- hard-gate state;
- evidence IDs per component;
- computed timestamp;
- stale state.

Scores are snapshots, never silently overwritten.

## 6.19 Campaign execution model

### `campaigns`

- play version;
- country/cohort;
- objective;
- status;
- owner;
- sending identity;
- start/end;
- daily caps;
- policy version;
- experiment plan;
- activation approval.

### `sequences` / `sequence_versions`

Stable sequence plus immutable activated version.

### `sequence_steps`

- ordinal;
- channel;
- delay policy;
- template version;
- required evidence classes;
- approval policy;
- stop checks.

### `campaign_memberships`

Opportunity/person/contact assigned to campaign with eligibility snapshot and cohort.

### `message_drafts`

- membership/step;
- locale;
- subject/body;
- rendered template version;
- claim/evidence mapping;
- generation method;
- approval state;
- approver;
- content hash.

### `touches`

- scheduled/due/submitted/sent/delivered/bounced/failed/cancelled;
- provider ID;
- immutable content snapshot;
- send identity;
- timestamps;
- policy/eligibility snapshot;
- stop state.

### `provider_events`

Webhook/poll events with dedup key and raw event retention.

### `conversation_events`

Replies, manual notes, calls, meetings, proposals, outcomes.

### `experiment_assignments`

Deterministic cohort/variant assignment, immutable after first send.

## 6.20 Suppression model

Retain suppression and add scopes:

- exact contact point;
- person;
- company;
- domain;
- campaign;
- global;
- reason: opt_out, complaint, hard_bounce, legal, duplicate, client, conflict, manual;
- source and timestamp;
- expires only where policy permits;
- immutable audit.

---

# 7. Legacy migration and compatibility strategy

A big-bang replacement is too risky. Use expand → backfill → dual-read/dual-write → verify → cut over → contract.

## 7.1 Phase A — Freeze and inventory

- capture production schema and migration revision;
- dump model/table counts;
- identify nullable/duplicate legacy fields;
- identify API/template dependencies on `Prospect` flat columns;
- snapshot all active records;
- create mapping document from legacy fields to normalized targets.

## 7.2 Phase B — Expand schema

Add new normalized tables without removing legacy columns. No user-facing behavior changes.

## 7.3 Phase C — Backfill

Backfill in resumable batches:

- `Prospect.siren` → `company_identifiers` scheme `siren`;
- `Prospect.siret` → scheme `siret`;
- `Prospect.naf_code` → `company_classifications` scheme `FR_NAF_REV2`;
- company/address/domain fields → canonical company/location/domain candidates;
- existing `MarketPlay` → stable play + immutable version;
- existing evidence → normalized evidence items;
- contact subsystem associations → people/company/opportunity relationships;
- current outreach events → legacy conversation/touch events where meaning is known.

Every batch writes:

- processed count;
- created/updated/skipped/conflict counts;
- checkpoint;
- conflict report;
- checksum/validation sample.

## 7.4 Phase D — Dual-write

All new writes update normalized tables and legacy projections where required. Implement one service boundary; do not scatter dual-write logic through routers.

## 7.5 Phase E — Read switch

Switch read paths page by page/API by API using feature flags:

- company identity;
- evidence;
- qualification;
- contact intelligence;
- sourcing;
- campaigns.

Compare old and new outputs in shadow reports before operator cutover.

## 7.6 Phase F — Projection-only legacy fields

Mark legacy columns read-only/deprecated. Generate projections from normalized data if old templates still require them.

## 7.7 Phase G — Contract schema

Remove legacy fields only after:

- two successful production releases;
- no reads in telemetry/static search;
- rollback path no longer requires old application version;
- data export verified;
- migration downgrade/restore strategy approved.

## 7.8 Migration conflict policy

Never choose silently when:

- one SIREN maps to multiple companies unexpectedly;
- domain is shared across parent/subsidiary;
- person association conflicts;
- legal status differs across fresh official sources;
- current play cannot be determined;
- legacy score has no evidence equivalent.

Create a review task with evidence and reason.

---

# 8. Market-play configuration system

## 8.1 Configuration requirements

A play version must fully specify:

```yaml
code: FIELD_OPERATIONS_UK_V1
version: 1.0.0
status: pilot
jurisdiction: GB
locale: en-GB
entity_policy:
  allowed_legal_forms: [ltd, llp, plc_review]
  excluded_legal_forms: [sole_trader, unincorporated_partnership]
verticals:
  include: [...]
  exclude: [...]
classifications:
  schemes: [UK_SIC_2007]
  include_codes: [...]
  exclude_codes: [...]
operational_size:
  field_technicians: {min: 10, max: 75, allow_unknown_with_complexity: true}
evidence:
  required_any: [operational_complexity, pain, trigger, technology_opportunity]
buyer_role_profile: buyer_roles_uk_field_ops_v1
source_plan: source_plan_uk_v1
compliance_policy: uk_b2b_email_corporate_v1
scoring_profile: field_ops_uk_v1
message_policy: evidence_first_en_gb_v1
```

## 8.2 Validation

Reject activation if:

- jurisdiction or locale missing;
- compliance policy inactive;
- no source plan;
- score profile references unknown evidence codes;
- buyer roles missing;
- campaign channel not allowed;
- classification codes invalid;
- no human owner;
- version not immutable/frozen.

## 8.3 Play activation lifecycle

```text
draft → validated → pilot → active → paused → retired
```

- `pilot` enforces low caps and full manual approval.
- `active` still respects campaign caps and policy.
- `paused` prevents new source/campaign activation but preserves history.
- `retired` cannot be reactivated; create a new version.

## 8.4 No default play

Remove runtime dependence on `DEFAULT_PLAY_CODE`. CLI, API, jobs, imports, and UI must require explicit play version. UI may remember the operator’s last selection, but it must display it visibly and persist it with every run.

---

# 9. Source-adapter framework

## 9.1 Interface

```python
from typing import Protocol, AsyncIterator

class SourceAdapter(Protocol):
    code: str
    version: str

    async def validate_config(self, config: dict) -> None: ...
    async def discover(self, run_context: "SourceRunContext") -> AsyncIterator["RawSourceRecord"]: ...
    def normalize(self, raw: "RawSourceRecord") -> list["NormalizedObservation"]: ...
    async def checkpoint(self, run_context: "SourceRunContext") -> dict: ...
    async def healthcheck(self) -> "SourceHealth": ...
```

Adapters discover and normalize observations. They do not directly approve companies or contacts.

## 9.2 Adapter requirements

- explicit source code/version;
- jurisdiction coverage;
- terms/reference metadata;
- authenticated configuration validation;
- timeouts and retries with jitter;
- rate-limit handling;
- cursor/checkpoint support;
- idempotency;
- payload minimization;
- source URL/external ID;
- observed/retrieved timestamps;
- health and error classification;
- test fixtures from permitted examples;
- redaction of secrets and unnecessary PII.

## 9.3 Source classes

- official registry;
- official procurement/contract;
- official company website;
- company job/careers page;
- authorized commercial import;
- manual research;
- contact verification provider;
- sending provider;
- CRM/calendar outcome source.

## 9.4 Source authority hierarchy

For legal identity/status, prefer official registry.  
For current operating activity, prefer official company website and recent sources.  
For current role, prefer official team/contact page or direct manual confirmation.  
For contact publication, prefer official company-controlled page.  
For deliverability, use configured verification but do not confuse it with identity or legal permission.

---

# 10. UK company-source implementation

## 10.1 Companies House adapter

Create `app/sources/companies_house.py` and supporting schemas/client.

### Responsibilities

- company search/discovery where appropriate;
- company profile retrieval;
- status and incorporation date;
- registered office;
- SIC codes;
- previous names;
- officers only where justified for buyer resolution;
- filing metadata only when used as a trigger and within source terms;
- API/bulk mode behind the same normalized contract.

### Do not infer

- operating address from registered office;
- field technician count from total employees;
- current operational buyer from any officer name;
- official domain from company name alone;
- relevance from SIC alone.

### Normalized outputs

- company identifier;
- legal name;
- status;
- legal form/jurisdiction;
- incorporation date;
- classifications;
- registered location;
- officer observations with role source;
- source URLs and timestamps.

### Query plan

Prefer a controlled seed strategy:

1. classification/location candidate universe;
2. active incorporated entities;
3. official website/domain resolution;
4. actual service/field-operation evidence;
5. complexity/trigger assessment;
6. buyer/contact discovery.

Do not make broad name searches the main acquisition method.

## 10.2 Companies House bulk data

If using bulk products:

- record snapshot date;
- checksum downloaded artifact;
- stage import separately;
- stream/process rather than load unbounded data into memory;
- preserve source IDs;
- filter only after retaining enough source context for audit;
- test restart and partial import;
- document licensing/terms and update cadence.

## 10.3 UK classification validation

Create a controlled list of candidate SIC codes with:

- official label;
- include/exclude reason;
- known false-positive patterns;
- required website evidence;
- effective play version.

Example false positives:

- construction installer with no ongoing service operation;
- dormant/holding company;
- equipment retailer without field technicians;
- one-person residential contractor;
- parent company whose operating subsidiary has another identity.

## 10.4 UK legal-form gate

Classify entity using official data. In pilot:

- allow reviewed corporate entities;
- deny sole traders;
- deny ambiguous unincorporated partnerships;
- review LLP/corporate form behavior against policy;
- record policy decision and reason.

---

# 11. France source implementation

## 11.1 Preserve and isolate existing adapters

Existing `app/discovery/sirene.py`, `annuaire.py`, `decp.py`, `naf.py`, and related code should be wrapped behind the new adapter interface rather than copied into UK logic.

## 11.2 Sirene adapter

Responsibilities:

- legal identity;
- SIREN/SIRET;
- active establishment/company status;
- NAF classification;
- address/location observations;
- workforce band only as a source estimate, with date and interpretation limits.

## 11.3 Annuaire des Entreprises adapter

Use for entity resolution and official-company information according to the available interface. Store source and retrieval time.

## 11.4 DECP adapter

Use public contract data as a **trigger or operating-evidence source**, not a universal indicator of software need. Required fields:

- buyer;
- supplier/company identifier;
- award/publication dates;
- contract category/description;
- amount only when reliable and contextually appropriate;
- relevance classification;
- source record.

A contract match can raise trigger/complexity confidence but cannot prove pain.

## 11.5 France play migration

Keep `FIELD_SERVICE_OPERATIONS_FR` for historical records. Create `FIELD_OPERATIONS_FR_V2` with:

- refined sectors;
- current buyer roles;
- evidence-first messaging;
- policy version;
- new score profile;
- normalized identity model;
- source plan.

Historical opportunities remain tied to their original play version.

---

# 12. Commercial import and manual-source implementation

## 12.1 CSV import

Commercial providers such as Apollo or Snov can be used only through authorized export/import or supported APIs consistent with their terms.

Create an import mapping flow:

1. upload to quarantine;
2. detect encoding/header;
3. map provider fields to staging schema;
4. preview and validate;
5. retain provider/export metadata;
6. resolve official company identity;
7. verify official domain;
8. deduplicate people/contact points;
9. apply policy and suppression;
10. require review before contact readiness.

## 12.2 Import staging schema

- import batch ID;
- provider;
- export date;
- source terms note;
- original row number;
- raw row JSON with retention rules;
- normalized name/company/domain/email/title;
- validation errors;
- identity resolution result;
- merge result;
- final disposition.

## 12.3 Manual research

Provide an operator action to add evidence manually with:

- exact source URL;
- observed text/fact;
- evidence type;
- observation date;
- confidence;
- notes;
- screenshot/file reference if permitted;
- reviewer identity.

Manual data must not become “source unknown.”

## 12.4 LinkedIn boundary

Allowed:

- operator manually views LinkedIn;
- operator records a professional role observation and URL;
- operator manually sends a connection request/message outside ProspectForge;
- operator records the touch and outcome.

Not allowed in this specification:

- scraping profiles;
- automated browsing;
- automated connection requests/messages;
- session-cookie reuse;
- evasion of rate limits or access controls.

---

# 13. Company identity and deduplication engine

## 13.1 Resolution stages

1. Identifier exact match.
2. Official registry candidate search.
3. Name/legal suffix normalization.
4. Location comparison.
5. domain/footer identifier match.
6. brand/subsidiary/parent analysis.
7. operator review when ambiguous.

## 13.2 Name normalization

- Unicode normalization;
- case folding;
- punctuation/whitespace normalization;
- legal suffix separation rather than destructive deletion;
- trading-name preservation;
- accent-insensitive comparison for matching only;
- no aggressive token removal that merges distinct companies.

## 13.3 Match score dimensions

- exact official identifier: decisive;
- legal-name match;
- trading-name match;
- address/postcode match;
- domain footer identifier;
- source-linked official website;
- phone match;
- parent/subsidiary relationship;
- conflicting active entities.

Store match reasons, not only a number.

## 13.4 Resolution outcomes

- `resolved_exact`;
- `resolved_high_confidence`;
- `candidate_review`;
- `unresolved`;
- `conflict`;
- `non_eligible_entity`.

Only exact/high-confidence resolution can proceed automatically to domain/evidence enrichment. Pilot still requires human company acceptance.

## 13.5 Merge behavior

- never hard-delete merged companies;
- redirect relationships to survivor in a transaction;
- preserve merge event and source IDs;
- prevent split-brain campaign memberships;
- re-run suppression and policy after merge;
- support manual unmerge only through audited administrative procedure.

---

# 14. Domain resolution and official-site verification

## 14.1 Candidate sources

- official registry-linked URL where available;
- official company contact material;
- commercial import candidate;
- search-provider result if later approved;
- email-domain candidate;
- manual entry;
- redirect from previous brand domain.

## 14.2 Verification evidence

Strong signals:

- legal name and company identifier in footer/legal page;
- address/phone matching official records;
- official source links to domain;
- privacy/terms identify company;
- consistent branding and service content;
- email domain used on official contact page.

Weak signals:

- name similarity only;
- directory listing;
- social profile link without legal identity;
- parked domain;
- generic marketplace page.

## 14.3 Domain states

- candidate;
- fetching;
- verified_primary;
- verified_alternate;
- rejected_wrong_entity;
- rejected_directory;
- rejected_inactive;
- inaccessible_review;
- stale.

## 14.4 Network safety

Preserve and expand current SSRF controls:

- allow HTTP/HTTPS only;
- resolve DNS and reject private, loopback, link-local, multicast, reserved, metadata, and prohibited ranges;
- revalidate every redirect target;
- bound redirects;
- timeout connect/read/overall;
- cap response bytes;
- restrict content types;
- safe decompression limits;
- no JavaScript execution in first release;
- identify crawler with transparent user agent;
- respect configured robots/terms policy;
- per-domain rate limit and concurrency cap.

## 14.5 Domain-resolution acceptance gate

Before official-site evidence/contact discovery:

- company is resolved;
- domain has at least two strong signals or one authoritative official link;
- no unresolved company conflict;
- TLS/redirect chain is safe;
- domain is not a directory/provider/parent unless explicitly classified.

---

# 15. Website evidence and technology intelligence

## 15.1 Crawl scope

Use exact-domain bounded crawling with prioritized paths:

- home;
- about/company/legal;
- services;
- sectors;
- locations;
- team/contact;
- careers/jobs;
- customer portal/login;
- privacy/terms;
- news/press where recent;
- PDFs linked from these pages within limits.

## 15.2 Evidence categories

### Operational complexity

- emergency/24-hour service;
- multiple service regions or branches;
- recurring maintenance contracts;
- large fleets/team descriptions;
- industrial/commercial customers;
- compliance documents;
- inspection/service reports;
- parts/spares/warehouse;
- multi-disciplinary technicians;
- customer portal;
- SLAs/callout contracts.

### Technology opportunity

- named FSM/CRM/accounting software;
- customer login/portal technology;
- downloadable paper/PDF process;
- separate booking/contact/forms;
- job advertisements mentioning manual tools or multiple systems;
- migration/digitalization initiative;
- integration/API references;
- legacy login/subdomain;
- duplicate forms and disconnected service areas.

### Trigger

- branch opening;
- acquisition;
- major contract;
- rapid hiring;
- new service line;
- management hire;
- system implementation/migration;
- portal launch;
- expansion geography.

### Pain evidence

Pain requires explicit evidence. Examples:

- job advert says coordinator reconciles multiple systems;
- company announcement discusses replacing manual process;
- case study/review identifies reporting or adoption problem;
- prospect directly confirms issue;
- public documentation shows repeated forms and handoffs.

Do not treat “has WhatsApp” or “has PDF form” alone as proven pain.

## 15.3 Technology detection

Technology signals are hypotheses unless supported. Record:

- signal type;
- detector version;
- exact URL/header/script/domain evidence;
- confidence;
- first/last seen;
- likely product/category;
- whether it is relevant to the opportunity.

Do not use technology detection to criticize the company in messaging.

## 15.4 Content extraction

- preserve text snippets with context and source URL;
- store content hash;
- deduplicate repeated template/footer text;
- detect language;
- distinguish current versus old news pages;
- limit verbatim personal data;
- retain only necessary page fragments.

---

# 16. Field-team and operational-complexity estimation

## 16.1 Principle

The engine cannot reliably know technician count from company employee count. It must store an estimate range, method, evidence, and confidence.

## 16.2 Evidence sources

- official workforce band;
- team/engineer count stated on site;
- branch count;
- job vacancies;
- fleet size statements/images with caution;
- service-area and 24/7 claims;
- named technical roles;
- manual research;
- commercial provider headcount;
- direct confirmation.

## 16.3 Estimation methods

### Direct stated

Company explicitly states number of engineers/technicians. Highest potential confidence after freshness check.

### Registry-band prior

Use workforce band to set broad bounds, never exact field-team count.

### Role-page estimate

Count only clearly current people and adjust for incomplete listings; usually low/medium confidence.

### Hiring/fleet composite

Infer only a broad range. Explain assumptions.

### Manual confirmed

Operator records direct company confirmation and date.

## 16.4 Output

Example:

```json
{
  "estimate_type": "field_technicians",
  "lower_bound": 15,
  "upper_bound": 35,
  "method_code": "composite_registry_site_jobs_v1",
  "confidence": "medium",
  "evidence_ids": ["..."],
  "assumptions": [
    "registry employee band includes office staff",
    "site states multiple regional engineering teams",
    "three current engineer vacancies"
  ],
  "expires_at": "2027-01-21"
}
```

## 16.5 Complexity score inputs

- technician estimate;
- branch count;
- service region count;
- planned + reactive service;
- recurring contracts;
- on-call/24h;
- parts/stock;
- compliance documents;
- multiple customer types;
- portal/reporting requirements;
- visible system count.

Complexity can compensate for unknown size, but cannot compensate for wrong vertical/entity.

---

# 17. Evidence taxonomy, provenance, and lifecycle

## 17.1 Evidence code format

```text
DOMAIN.CATEGORY.SPECIFIC_SIGNAL
```

Examples:

- `COMPANY.IDENTITY.ACTIVE_STATUS`
- `OPERATIONS.COMPLEXITY.MULTI_BRANCH`
- `OPERATIONS.COMPLEXITY.RECURRING_CONTRACTS`
- `TECH.STACK.NAMED_FSM`
- `TECH.OPPORTUNITY.MULTI_SYSTEM_HANDOFF`
- `TRIGGER.GROWTH.BRANCH_OPENING`
- `TRIGGER.HIRING.SERVICE_COORDINATOR`
- `PAIN.EXPLICIT.MANUAL_RECONCILIATION`
- `BUYER.ROLE.OPERATIONS_DIRECTOR`
- `CONTACT.PUBLICATION.OFFICIAL_PAGE`

## 17.2 Evidence fields

Every item:

- subject;
- code;
- normalized value;
- source connector/record;
- exact URL or official identifier;
- observed time;
- retrieved time;
- extractor/rule/manual reviewer;
- confidence;
- verification state;
- content/snippet hash;
- locale;
- sensitivity class;
- expiry/refresh rule;
- supersession link.

## 17.3 Evidence freshness

Suggested initial defaults:

| Evidence | Refresh/expiry |
|---|---|
| Entity status | 30–90 days in active campaign |
| Official domain | 90 days or on failure |
| Buyer role | 60–90 days |
| Public contact point | 60 days before first send; recheck after bounce |
| Job vacancy trigger | 30–60 days |
| News/contract trigger | relevance window by type, often 90–180 days |
| Technology signal | 90–180 days |
| Direct confirmation | review after 180 days or known change |

Policy can require fresher checks immediately before send.

## 17.4 Contradictions

Store contradictory evidence rather than deleting it. Resolution states:

- unresolved conflict;
- source priority resolution;
- superseded by newer official evidence;
- manual decision;
- not actually contradictory due to time/subsidiary/context.

Contradictions affecting identity, buyer, contact, or policy block send.

## 17.5 Message evidence link

Every personalized message claim must map to evidence IDs and a transformation rule. Example:

```json
{
  "claim_text": "I noticed you are recruiting a Service Coordinator in Manchester.",
  "evidence_id": "EV-...",
  "rule": "HIRING_TRIGGER_DIRECT_V1",
  "source_date": "2026-07-18",
  "reviewed": true
}
```

---

# 18. Trigger intelligence

## 18.1 Trigger definition

A trigger is a time-bounded event that plausibly changes priority or creates operational strain. It is not a generic company characteristic.

## 18.2 Trigger types

- branch/service-region expansion;
- acquisition/merger;
- major contract award;
- rapid technician or coordinator hiring;
- new operations/service leader;
- customer portal/digital initiative;
- software implementation/migration;
- recurring-service launch;
- compliance/regulatory process change relevant to workflow;
- explicit modernization project.

## 18.3 Trigger scoring dimensions

- recency;
- source authority;
- relevance to field operations;
- magnitude;
- directness;
- ambiguity;
- evidence confidence.

## 18.4 Trigger-to-message rule

A trigger can be mentioned only if:

- current and correctly associated with the company;
- professional and non-sensitive;
- directly relevant to the message;
- source is public/authorized;
- wording does not overstate consequence;
- human reviewer confirms it does not feel invasive.

Example safe:

> “I saw that you are recruiting a Service Coordinator while expanding the maintenance team.”

Unsafe:

> “Your growth must be causing scheduling chaos.”

---

# 19. Buyer-role and person-resolution engine

## 19.1 Role taxonomy

Create normalized role codes:

- `EXECUTIVE_OWNER`;
- `MANAGING_DIRECTOR`;
- `OPERATIONS_DIRECTOR`;
- `OPERATIONS_MANAGER`;
- `SERVICE_DIRECTOR`;
- `SERVICE_MANAGER`;
- `FIELD_SERVICE_MANAGER`;
- `TECHNICAL_DIRECTOR`;
- `MAINTENANCE_MANAGER`;
- `GENERAL_MANAGER`;
- `IT_DIGITAL_LEAD`;
- `FINANCE_LEAD`;
- `UNKNOWN_RELEVANT`.

## 19.2 Role dictionaries

### English examples

- managing director, MD;
- operations director, head of operations;
- operations manager;
- service director, head of service;
- service manager;
- field service manager;
- technical director;
- maintenance manager;
- general manager.

### French examples

- gérant, président, directeur général;
- directeur des opérations;
- responsable d’exploitation;
- directeur/ responsable SAV;
- responsable service;
- directeur technique;
- responsable maintenance.

Include negative/low-priority titles such as office administrator, receptionist, generic sales contact, apprentice, former employee, and external accountant.

## 19.3 Buyer selection by company context

- Smaller owner-led company: Managing Director/owner may own budget and operations.
- Larger multi-team company: Operations or Service Director usually first.
- Technical integration/rescue: Technical Director or digital/IT stakeholder may be co-buyer.
- Billing/invoice workflow: finance may be stakeholder, not always first contact.

Store primary buyer, alternate buyer, and rationale.

## 19.4 Current-role validation

A role is current only when evidence supports it and no stronger contradictory evidence exists. Source freshness and official-company control matter.

## 19.5 Person confidence

Calculate separately:

- name parsing confidence;
- company association confidence;
- current-role confidence;
- role relevance;
- contact-point identity match.

Do not collapse these into one opaque confidence number.

---

# 20. Contact-intelligence localization and verification

## 20.1 Preserve existing safety model

Retain concepts from the current contact-intelligence subsystem:

- bounded official-domain discovery;
- publication evidence;
- person/contact association;
- DNS/MX check;
- optional provider verification;
- manual review;
- safe projection to prospect/contact-ready state;
- guessed-address separation.

## 20.2 Discovery order

1. Official team/contact/legal pages.
2. Official PDFs/documents within crawl bounds.
3. JSON-LD and structured data.
4. Official general contact route.
5. Authorized commercial import.
6. Pattern candidate generated from verified domain and person name.
7. Manual research.

## 20.3 Contact-point classes

### Person-specific published email

Strongest identity publication evidence.

### Role/general mailbox

Examples: operations@, service@, contact@. May be useful when buyer-specific contact is unavailable; message and policy differ.

### Contact form

Store URL and fields; no automated submission in first release.

### Pattern-derived candidate

Never equivalent to published. Requires:

- verified official domain;
- high-confidence current person;
- pattern learned from multiple published addresses or reliable source;
- deliverability check where configured;
- manual approval;
- policy allow;
- explicit `guessed` state.

### Phone

Useful for manual follow-up only under separate policy; do not auto-dial.

## 20.4 State dimensions

Keep separate state machines:

- publication: published, inferred, imported, unknown;
- person match: exact, likely, role mailbox, general, unknown;
- deliverability: deliverable, risky, unknown, undeliverable;
- policy: allowed, review, denied;
- utility: preferred, alternate, unusable, stale;
- suppression: clear, suppressed.

A contact-ready decision is a rule over these dimensions, not one boolean.

## 20.5 Email normalization and privacy

- lowercase domain;
- preserve original display;
- avoid unnecessary hashing as a substitute for security;
- encrypt sensitive fields at rest if threat model requires it;
- restrict UI exposure;
- never log full addresses in ordinary application logs;
- redact provider payloads;
- honor retention and suppression.

## 20.6 Reverification before send

Immediately before first touch:

- company still active;
- domain still verified;
- role still current within freshness window;
- contact not stale/suppressed;
- deliverability not hard-failed;
- policy still allows;
- no reply/relationship/conflict exists;
- message evidence still current.

---

# 21. Compliance policy engine

This section describes engineering controls, not legal advice. Policies must be reviewed for the actual business, channels, sources, and jurisdictions before activation.

## 21.1 Policy inputs

- jurisdiction/country;
- legal form/entity type;
- channel;
- business versus individual subscriber classification where relevant;
- professional role and message relevance;
- data source;
- contact publication/inference state;
- prior relationship/consent where available;
- suppression/objection;
- first-contact disclosure status;
- retention state;
- campaign purpose;
- operator override eligibility.

## 21.2 UK pilot policy

Initial engineering policy:

- B2B corporate entities only;
- exclude sole traders and ambiguous partnerships;
- message must relate to recipient’s professional role;
- sender identity and business contact details clear;
- simple opt-out included;
- data source and collection date retained;
- objection immediately suppresses;
- named-contact data-protection obligations recorded;
- no deceptive subject/threading;
- no automated LinkedIn actions.

Policy output should be `allow_review`, not unconditional `allow_send`, until human review.

## 21.3 France pilot policy

Initial engineering policy:

- professional B2B relevance required;
- recipient informed appropriately about data/source and rights;
- simple/free opposition mechanism;
- objection immediately suppresses;
- current professional role and contact evidence;
- source and collection date retained;
- message purpose directly related to profession;
- human review before first send.

## 21.4 Germany and Netherlands

Default policy state: `deny_new_campaign` / disabled play until qualified legal and channel review. The system must fail closed.

## 21.5 First-contact disclosure

Message/footer or linked notice should provide the required transparent identity, reason for contact, and opt-out appropriate to the policy. Store disclosure template version used.

## 21.6 Legitimate-interest/assessment record

Where applicable, create a structured internal assessment record:

- purpose;
- necessity;
- balancing factors;
- reasonable expectations;
- data minimization;
- safeguards;
- objection process;
- review date;
- approver.

Do not generate legal conclusions automatically from a score.

## 21.7 Policy decision trace

Example:

```json
{
  "decision": "allow_review",
  "policy": "uk_b2b_email_corporate_v1",
  "rules": [
    {"rule": "entity_is_corporate", "result": "pass", "evidence": "..."},
    {"rule": "professional_relevance", "result": "pass", "evidence": "..."},
    {"rule": "contact_not_suppressed", "result": "pass"},
    {"rule": "contact_publication", "result": "published"},
    {"rule": "human_first_touch_review", "result": "required"}
  ]
}
```

## 21.8 Overrides

Overrides require:

- authorized role;
- written reason;
- evidence;
- limited scope/time;
- audit event;
- no override of opt-out, complaint, legal prohibition, or hard suppression.

---

# 22. Scoring, hard gates, and qualification

## 22.1 Principle

Score ranks opportunities that already pass basic eligibility. It cannot make an ineligible record eligible.

## 22.2 Score dimensions

Recommended 100-point profile:

| Dimension | UK weight | France weight | Notes |
|---|---:|---:|---|
| ICP/vertical fit | 15 | 15 | classification + website evidence |
| Operational complexity | 15 | 15 | team/branches/contracts/docs/stock |
| Pain evidence | 15 | 15 | explicit evidence; industry alone gives 0 |
| Trigger | 10 | 12 | time-bounded relevance |
| Technology/integration opportunity | 15 | 13 | fragmented stack, migration, portal, rescue |
| Buyer authority/relevance | 10 | 10 | current role |
| Budget/capacity proxies | 5 | 5 | cautious proxy |
| Data quality | 10 | 10 | identity/domain/evidence confidence |
| Contactability | 5 | 5 | usable route, not legal permission |

Adjust only after gold-set analysis.

## 22.3 Example component rules

### ICP fit

- verified eligible vertical on official site: +8;
- classification supports vertical: +3;
- commercial/industrial service evidence: +4;
- residential-only/micro indication: exclusion or negative.

### Pain evidence

- explicit manual reconciliation/multi-system issue: +15;
- direct prospect confirmation: +15;
- strong job description indicating repeated coordination/data entry: +8–12;
- generic “we use spreadsheets” inference: 0 unless evidenced.

### Technology opportunity

- named disconnected systems/handoff: +10–15;
- failed/partial implementation evidence: +12–15;
- customer portal/API initiative: +6–10;
- technology detected without opportunity evidence: +0–3.

## 22.4 Hard gates

Before `contact_ready`:

1. company identity resolved;
2. entity active and permitted legal form;
3. play/vertical match evidenced;
4. official domain verified;
5. operational complexity or target-size evidence sufficient;
6. at least one pain, trigger, or technology opportunity evidenced;
7. current relevant buyer identified or approved general route;
8. contact point/route meets configured evidence state;
9. compliance decision permits review/send;
10. suppression clear;
11. evidence freshness passes;
12. human qualification accepted;
13. message draft contains no unsupported claim;
14. first touch approved.

## 22.5 Human qualification form

Upgrade six booleans into evidence-linked questions:

- Is the legal entity and domain correct?
- Does the company actually operate field-service/technical-service teams?
- Is scale/complexity sufficient?
- What exact opportunity is evidenced?
- Why now?
- Who owns the problem and budget?
- Is this person current?
- Is the contact route defensible?
- What policy allows or blocks the channel?
- What should the first message reference?
- What could make this a poor fit?

Decision: accept, reject, needs research, defer. Require controlled reason codes plus notes.

## 22.6 Score thresholds

Do not hard-code commercial truth before calibration. Initial operating bands:

- 80–100: priority review, not auto-send;
- 65–79: normal review;
- 50–64: research/defer;
- below 50: reject/archive unless specific override.

Hard-gate failure blocks regardless of total.

---

# 23. Gold-set labeling and calibration

## 23.1 Gold set

Create 50 manually researched companies across four cohorts. Each receives independent labels for:

- entity match;
- domain match;
- vertical eligibility;
- operational complexity;
- field-team range;
- pain evidence;
- trigger;
- technology opportunity;
- buyer correctness;
- contact correctness;
- policy decision;
- final outreach suitability.

## 23.2 Label schema

```yaml
company_id: ...
cohort: UK_HVAC_A
labels:
  entity_resolution: correct
  domain_resolution: correct
  vertical_fit: strong
  operational_complexity: strong
  field_team_range: [20, 40]
  pain_evidence: insufficient
  trigger: coordinator_hiring
  buyer_primary: person_id
  buyer_correctness: correct
  contact_point: contact_id
  contact_correctness: correct
  outreach_decision: accept
reviewer: ...
reviewed_at: ...
evidence_notes: ...
```

## 23.3 Quality metrics

- entity precision;
- domain precision;
- vertical precision/recall against labeled set;
- buyer top-1 accuracy;
- buyer top-3 coverage;
- contact precision by state;
- evidence extraction precision;
- field-team range coverage;
- policy agreement with legal/manual review;
- final accept/reject agreement;
- false-positive reason distribution.

## 23.4 Pre-send thresholds

Minimum:

- ≥95% correct legal-company resolution;
- ≥90% correct primary-domain resolution;
- ≥85% correct vertical eligibility;
- ≥80% correct primary buyer-role classification;
- 100% of message claims trace to evidence;
- 0 guessed-only contacts automatically approved;
- 0 suppression/policy bypasses;
- 100% first touches human reviewed.

If thresholds fail, fix the relevant stage rather than lowering standards.

## 23.5 Regression suite

Convert representative gold-set cases into fixtures, including:

- parent/subsidiary domain;
- same-name companies;
- dormant company;
- wrong-directory domain;
- residential microbusiness false positive;
- current versus former director;
- general mailbox only;
- guessed address;
- conflicting registry/site data;
- French establishment versus legal unit;
- UK sole-trader exclusion;
- stale trigger.

---

# 24. Messaging and personalization engine

## 24.1 Message objective

Start a relevant diagnostic conversation. Do not pretend the engine has diagnosed private operations from public data.

## 24.2 Message inputs

Only:

- approved company/buyer fields;
- approved evidence items;
- play/version;
- locale;
- offer category;
- campaign/sequence step;
- disclosure/opt-out block;
- prior conversation context.

## 24.3 Message claim policy

Allowed claim classes:

- direct public observation;
- client-approved Anass proof;
- cautious question/hypothesis;
- transparent explanation of service.

Forbidden:

- invented time/cost loss;
- “companies your size lose…” without source and appropriateness;
- diagnosis stated as fact;
- unsupported Fractal Tech metrics;
- invasive personal detail;
- hidden tracking claims;
- false reply-thread subject;
- fake familiarity;
- aggressive scarcity.

## 24.4 Template model

Templates are versioned and have required evidence slots.

```yaml
code: UK_FIELD_OPS_EVIDENCE_FIRST_01
locale: en-GB
step: first_touch
required_slots:
  - company_name
  - buyer_first_name
  - opportunity_observation
  - relevant_proof
constraints:
  max_words: 110
  no_links: true
  no_attachment: true
  require_opt_out: true
```

## 24.5 Example UK first touch

**Subject:** Field-to-office workflow at {{company_name}}

> Hi {{first_name}},
>
> I noticed {{approved_observation}}. I work with service companies where planning, technician updates, parts, documents and invoicing are split across several tools. I recently delivered a refrigeration operations system that connected those records in one workflow.
>
> How does {{company_name}} currently handle the handoff from completed field work to office processing—mainly one system, or several?
>
> Anass
> {{transparent_identity_and_opt_out}}

The observation must be specific and evidence-backed. If there is no safe observation, use a cohort-level question without pretending to have inspected private operations.

## 24.6 Example French first touch

**Objet :** Processus intervention → facturation chez {{company_name}}

> Bonjour {{first_name}},
>
> J’ai relevé {{approved_observation_fr}}. J’accompagne des entreprises de service lorsque le planning, les retours techniciens, les pièces, les documents et la préparation de la facturation sont répartis entre plusieurs outils. J’ai récemment livré un système d’exploitation pour une entreprise de froid qui relie ces dossiers dans un même processus.
>
> Aujourd’hui, le passage d’une intervention terminée au dossier prêt à facturer se fait-il principalement dans un seul outil chez {{company_name}}, ou dans plusieurs ?
>
> Anass
> {{transparent_identity_and_opt_out_fr}}

Review native phrasing before activation.

## 24.7 Sequence policy

Initial three-email sequence over roughly ten business days:

1. Evidence-first question.
2. Short proof/clarification; no manufactured urgency.
3. Close-the-loop note.

LinkedIn touches are manually executed and recorded, not automatically scheduled for sending.

## 24.8 Draft review UI

Reviewer must see side by side:

- subject/body;
- company identity;
- buyer/role evidence;
- every personalization claim and source;
- contact state;
- compliance decision;
- suppression state;
- prior touches;
- edit diff;
- approve/reject reason.

## 24.9 LLM use

If an LLM is added later:

- it may summarize approved evidence or propose wording;
- it cannot create facts;
- output must conform to schema;
- evidence IDs required per claim;
- deterministic safety checks run after generation;
- first-touch human approval remains;
- prompts/model/version and output hash stored;
- sensitive data minimized;
- provider/data-processing review required.

---

# 25. Campaign, sequence, and touch state machines

## 25.1 Campaign state

```text
draft → review → approved → active → paused → completed
                         ↘ cancelled
```

Activation requires owner, play version, policy version, sending identity, cap, sequence version, cohort, and approval.

## 25.2 Membership state

```text
candidate → eligibility_review → eligible → draft_ready → approved
→ active_sequence → replied/meeting/qualified/won/lost
→ stopped_opt_out/stopped_bounce/stopped_policy/stopped_manual
```

## 25.3 Draft state

```text
generated → validation_failed | review_required → approved → locked
```

Any edit after approval creates a new revision and reapproval.

## 25.4 Touch state

```text
planned → due → eligibility_recheck → approved_to_submit → submitted
→ accepted_by_provider → delivered
→ soft_bounce/hard_bounce/failed
→ cancelled/stopped
```

Provider “accepted” is not delivery. Store exact provider semantics.

## 25.5 Stop rules

Stop all future steps immediately on:

- any reply, including out-of-office until reviewed according to policy;
- opt-out/objection;
- hard bounce;
- spam complaint;
- meeting booked;
- qualified conversation;
- manual stop;
- company/contact suppression;
- identity/buyer/policy invalidation;
- provider or domain health incident;
- campaign pause/cancel.

## 25.6 Reply classification

Controlled categories:

- positive_interest;
- referral_to_colleague;
- ask_for_information;
- timing_later;
- already_solved;
- no_problem;
- not_relevant;
- no_budget;
- opt_out;
- complaint;
- out_of_office;
- bounce;
- unknown_manual_review.

Classification can be suggested automatically but requires review in pilot.

## 25.7 Idempotency

- one provider submission per touch idempotency key;
- webhook/event dedup by provider event ID/hash;
- scheduler uses locked/claimed rows;
- retries never create duplicate email;
- ambiguous timeout after submission is reconciled with provider before retry.

---

# 26. Deliverability and sending infrastructure

## 26.1 Sending identity

Use a transparent, professional mailbox and domain strategy. Protect the primary portfolio domain reputation. Do not create deceptive lookalike domains.

## 26.2 Authentication

Before pilot:

- SPF aligned with actual sender;
- DKIM enabled and verified;
- DMARC policy deployed and reports monitored;
- reverse DNS/provider configuration where applicable;
- From/Return-Path alignment understood;
- TLS supported;
- mailbox can receive replies;
- unsubscribe/opt-out process works.

## 26.3 Pilot sending controls

- 5–10 first touches per business day initially;
- per-domain caps;
- country/business-hour scheduling;
- no open-tracking pixel in initial pilot unless justified and disclosed;
- no attachments in first touch;
- limited links;
- plain, relevant content;
- bounce and complaint monitoring;
- automatic pause on thresholds.

## 26.4 Health thresholds

Configure conservative defaults and human review, for example:

- any complaint: immediate campaign pause and investigation;
- hard bounce above a low threshold: pause affected source/contact method;
- provider authentication failure: global pause;
- sudden delivery-rate collapse: pause and inspect;
- domain blocklist/security incident: stop sending.

Do not optimize only for open rate; privacy features make it unreliable.

## 26.5 Provider abstraction

```python
class SendingProvider(Protocol):
    async def submit(self, message: OutboundMessage, idempotency_key: str) -> SubmissionResult: ...
    async def get_status(self, provider_message_id: str) -> DeliveryStatus: ...
    def verify_webhook(self, headers: dict, body: bytes) -> bool: ...
    def parse_event(self, body: bytes) -> list[ProviderEvent]: ...
```

Provider adapters cannot decide policy or eligibility.

## 26.6 Reply ingestion

Options:

- Gmail API/IMAP/provider webhook with explicit authorization;
- thread mapping by provider message ID and headers;
- safe HTML/text parsing;
- attachment handling disabled or quarantined;
- no automated reply in first release;
- human alert and sequence stop.

---

# 27. Operator interface and workflow

## 27.1 Global navigation

- Dashboard
- Market Plays
- Source Runs
- Companies
- Opportunities
- Review Queue
- Contact Intelligence
- Campaigns
- Conversations
- Gold Set / Quality
- Suppression
- System Health
- Settings / Audit

Display active play and jurisdiction prominently in every relevant screen.

## 27.2 Dashboard

Show separate panels:

- source health;
- records awaiting identity/domain review;
- qualification queue;
- contact review queue;
- drafts awaiting approval;
- touches due today;
- replies needing classification;
- campaign health;
- funnel by cohort;
- quality thresholds;
- policy/suppression incidents;
- production/job health.

Avoid a single vanity “lead score” leaderboard.

## 27.3 Market-play screen

- stable play and versions;
- status;
- country/language;
- source plan;
- ICP rules;
- score profile;
- policy version;
- buyer dictionary;
- active campaigns;
- quality metrics;
- immutable version diff;
- activation/pause with approval.

## 27.4 Source-run screen

- connector/version;
- play version;
- query/config;
- checkpoint;
- progress and rates;
- discovered/normalized/rejected/conflict counts;
- errors by class;
- sample records;
- retry/resume/cancel;
- health and rate-limit information.

## 27.5 Company detail

Tabs:

1. Identity.
2. Names/identifiers/classifications.
3. Locations/domains.
4. Evidence and triggers.
5. Estimates.
6. People/roles.
7. Contacts.
8. Opportunities by play.
9. Audit/source records.

## 27.6 Opportunity detail

Above the fold:

- company and play;
- status and owner;
- hard-gate summary;
- score breakdown;
- exact opportunity hypothesis;
- source-backed evidence;
- buyer/contact/policy state;
- next action.

Tabs:

- qualification;
- evidence;
- buyer/contact;
- message drafts;
- campaign/touches;
- conversation/outcomes;
- audit.

## 27.7 Review queue

Filters:

- play/cohort/country;
- review type;
- score band;
- hard-gate failure;
- evidence freshness;
- guessed contact;
- policy needs review;
- age/SLA.

Review cards must support keyboard operation and fast evidence inspection without hiding ambiguity.

## 27.8 Campaign screen

- activation gate;
- membership count by state;
- daily caps;
- due/sent/delivered/bounced/replied;
- stop reasons;
- variant allocation;
- policy version;
- sending identity health;
- pause control;
- sample approved messages;
- audit log.

## 27.9 Gold-set screen

- labeled records;
- reviewer agreement;
- confusion/error categories;
- current metrics versus thresholds;
- regressions by release;
- drill-down to false positives/negatives;
- freeze version for release gate.

## 27.10 UI safety

- destructive/override actions require reason and confirmation;
- policy/suppression state cannot be hidden;
- guessed contacts visually distinct;
- stale evidence warning;
- no bulk send without campaign activation approval;
- no send action from generic prospect table;
- PII masked for users without need-to-know role;
- export actions audited.

---

# 28. API contracts

Use versioned routes and authorization. Illustrative target:

## 28.1 Market plays

```text
GET    /api/v1/market-plays
POST   /api/v1/market-plays
POST   /api/v1/market-plays/{id}/versions
POST   /api/v1/market-play-versions/{id}/validate
POST   /api/v1/market-play-versions/{id}/activate
POST   /api/v1/market-plays/{id}/pause
```

## 28.2 Source runs

```text
POST   /api/v1/source-runs
GET    /api/v1/source-runs/{id}
POST   /api/v1/source-runs/{id}/resume
POST   /api/v1/source-runs/{id}/cancel
GET    /api/v1/source-runs/{id}/records
```

## 28.3 Companies and resolution

```text
GET    /api/v1/companies
GET    /api/v1/companies/{id}
POST   /api/v1/companies/{id}/resolve-domain
POST   /api/v1/companies/{id}/merge
POST   /api/v1/identity-candidates/{id}/decide
```

## 28.4 Opportunities

```text
GET    /api/v1/opportunities
GET    /api/v1/opportunities/{id}
POST   /api/v1/opportunities/{id}/recalculate
POST   /api/v1/opportunities/{id}/qualification-reviews
POST   /api/v1/opportunities/{id}/defer
POST   /api/v1/opportunities/{id}/reject
```

## 28.5 Contacts

```text
POST   /api/v1/companies/{id}/contact-discovery-runs
GET    /api/v1/contact-points/{id}
POST   /api/v1/contact-points/{id}/verify
POST   /api/v1/contact-points/{id}/manual-reviews
```

## 28.6 Compliance

```text
POST   /api/v1/opportunities/{id}/compliance-decisions/evaluate
GET    /api/v1/compliance-decisions/{id}
POST   /api/v1/compliance-decisions/{id}/override
```

## 28.7 Campaigns

```text
POST   /api/v1/campaigns
POST   /api/v1/campaigns/{id}/memberships
POST   /api/v1/campaigns/{id}/validate
POST   /api/v1/campaigns/{id}/activate
POST   /api/v1/campaigns/{id}/pause
GET    /api/v1/campaigns/{id}/metrics
POST   /api/v1/message-drafts/{id}/approve
POST   /api/v1/message-drafts/{id}/reject
```

## 28.8 Provider webhooks

```text
POST   /api/v1/webhooks/sending/{provider}
POST   /api/v1/webhooks/replies/{provider}
```

Requirements: signature verification, raw-body preservation per retention, idempotency, replay protection, safe failure response.

## 28.9 Error model

Use stable codes:

```json
{
  "error": {
    "code": "POLICY_BLOCKED",
    "message": "The contact is not eligible for this campaign channel.",
    "details": {"decision_id": "...", "rule": "entity_type"},
    "request_id": "..."
  }
}
```

Do not leak secrets or full personal data in errors.

---

# 29. Jobs, queues, scheduling, and resilience

## 29.1 Job classes

- source discovery/import;
- source normalization;
- company identity resolution;
- domain resolution;
- website crawl/extraction;
- evidence classification;
- estimate calculation;
- buyer/contact discovery;
- verification;
- compliance evaluation;
- score recalculation;
- qualification task creation;
- draft generation;
- due-touch eligibility recheck;
- provider submission;
- provider event reconciliation;
- reply ingestion/classification;
- freshness/retention;
- metrics aggregation;
- backup/health.

## 29.2 Job record

Store:

- job type/version;
- subject;
- play version;
- idempotency key;
- priority;
- status;
- attempts/max;
- scheduled/started/finished;
- checkpoint;
- lease/worker;
- error class/message;
- input/output hashes;
- parent/child run;
- trace/request ID.

## 29.3 Reliability

- jobs claim rows atomically;
- leases expire and can be recovered;
- retries use exponential backoff and jitter;
- permanent errors do not retry indefinitely;
- rate-limit errors reschedule appropriately;
- partial progress checkpointed;
- poison records quarantined;
- operators can inspect and retry safely;
- no duplicate tasks on repeated qualification acceptance;
- scheduler timezone explicit.

## 29.4 Scheduler controls

- per-connector concurrency;
- per-domain crawl concurrency;
- per-provider send caps;
- business-day/calendar rules;
- global emergency pause;
- campaign pause;
- source health circuit breaker;
- maintenance windows;
- dry-run mode.

## 29.5 Observability

Metrics:

- job latency and failure by type;
- queue depth;
- source rate-limit responses;
- crawl safety rejections;
- identity/domain resolution outcomes;
- contact verification outcomes;
- policy blocks;
- draft validation failures;
- provider submissions/delivery events;
- duplicate prevention events;
- stale evidence counts.

Structured logs must use IDs, not unnecessary full PII.

---

# 30. Analytics, funnel integrity, and experimentation

## 30.1 Funnel stages

```text
source_record
→ resolved_company
→ verified_domain
→ play_eligible
→ opportunity_evidenced
→ buyer_identified
→ contact_candidate
→ contact_approved
→ policy_allowed
→ human_qualified
→ draft_approved
→ first_touch_sent
→ delivered
→ replied
→ positive_reply
→ call_booked
→ call_completed
→ mapping_sprint_proposed
→ mapping_sprint_won
→ project_proposed
→ project_won
```

## 30.2 Denominators

Every rate must state its denominator and cohort. Examples:

- domain precision among manually labeled resolved domains;
- reply rate among delivered first touches;
- positive reply rate among delivered first touches;
- call booking among delivered or positive replies;
- qualified call among completed calls;
- Mapping Sprint wins among proposals.

Do not report replies divided by “leads found.”

## 30.3 Cohort dimensions

- play version;
- country;
- vertical;
- source connector;
- evidence pattern;
- buyer role;
- contact publication state;
- message template/variant;
- campaign;
- send week;
- result reason.

## 30.4 Experiments

Pilot experiments may test:

- direct operational question versus trigger-led observation;
- buyer role;
- proof sentence;
- subject line;
- UK HVAC versus UK maintenance cohort.

Rules:

- one primary variable per experiment;
- immutable assignment before first send;
- minimum sample acknowledged;
- do not optimize on opens alone;
- safety/compliance wording not experimental unless legally reviewed;
- negative outcomes and complaints override conversion gains.

## 30.5 Weekly decision report

```text
1. Gold-set quality and regressions
2. Source health and coverage
3. Accepted/rejected opportunities and reasons
4. Contact coverage by evidence state
5. Sending health
6. Replies and classifications
7. Calls/proposals/revenue outcomes
8. False-positive examples
9. Message examples that worked/failed
10. One or two changes for next cohort
```

---

# 31. Security, privacy, audit, and retention

## 31.1 Threat model

Protect against:

- unauthorized operator access;
- credential theft;
- mass export/exfiltration;
- SSRF and unsafe crawling;
- malicious source content;
- webhook spoofing;
- duplicate/unauthorized sends;
- policy/suppression bypass;
- secrets in logs/backups;
- SQL/injection/XSS/CSRF;
- excessive PII retention;
- broken tenant/user authorization if multi-user expands;
- compromised dependency/container;
- destructive migration/restore failure.

## 31.2 Authentication and authorization

- strong password hashing or external identity provider;
- MFA for production operators where possible;
- secure session cookies;
- CSRF protection;
- role-based authorization: admin, operator, reviewer, campaign approver, read-only;
- least privilege;
- reauthentication for export, override, and campaign activation;
- session expiry and revocation;
- audit all sensitive actions.

## 31.3 Audit events

Immutable append events for:

- play activation/change;
- source run launch/cancel;
- identity/domain manual decision;
- merge/unmerge;
- qualification decision;
- contact review;
- compliance decision/override;
- suppression change;
- message approval/edit;
- campaign activation/pause;
- provider submission;
- export;
- user/role change;
- retention/deletion;
- backup/restore/deployment.

## 31.4 Retention

Create explicit retention classes:

- official company data;
- public professional role/contact;
- raw source payload;
- website content snippet;
- provider verification payload;
- message/touch history;
- reply content;
- suppression proof;
- audit log;
- backup.

Retention jobs must preserve suppression/objection evidence while deleting unnecessary contact/source data as policy requires.

## 31.5 Exports

- permission-controlled;
- scope/fields shown before export;
- PII warning;
- export encrypted or protected as appropriate;
- expiration/deletion guidance;
- audit event;
- no unrestricted “dump everything” for ordinary operators.

## 31.6 Backups

- encrypted in transit and at rest;
- access restricted;
- retention documented;
- restore tested;
- secrets separated;
- backup does not defeat deletion policy indefinitely;
- schema/application version recorded.

---

# 32. Testing strategy

## 32.1 Maintain current baseline

The existing 140-test baseline becomes a regression floor. New changes must not reduce coverage merely to pass.

## 32.2 Test layers

### Unit

- normalization;
- role mapping;
- evidence extraction;
- score components;
- policy rules;
- state transitions;
- message claim validation;
- suppression;
- idempotency keys.

### Contract

- Companies House fixtures;
- Sirene/Annuaire/DECP fixtures;
- import schemas;
- sending provider;
- verification provider;
- webhook signatures/events.

### Integration

- source record → company resolution;
- domain verification → crawl;
- evidence → score/gates;
- contact discovery → policy;
- qualification → draft;
- campaign activation → due touch;
- provider event → sequence stop;
- reply → stop and task;
- suppression → all future touch cancellation.

### Migration

- upgrade from every supported revision;
- downgrade where supported;
- backfill resume;
- conflict handling;
- row-count/checksum validation;
- old/new projection comparison;
- production-like dataset rehearsal.

### Security

- SSRF redirect/DNS rebinding patterns;
- unsafe schemes/ports/IPs;
- oversized/compressed responses;
- malicious HTML/PDF content;
- authorization/IDOR;
- CSRF;
- webhook spoof/replay;
- secret/log redaction;
- export permission;
- campaign activation permission.

### Browser/UI

- login/session;
- market-play selection;
- source run;
- company/opportunity detail;
- qualification;
- contact review;
- message approval;
- campaign pause;
- reply classification;
- keyboard/accessibility smoke.

### Live acceptance

- one low-volume official-source query;
- safe crawl of controlled domains;
- test mailbox send/reply/bounce;
- provider event reconciliation;
- backup/restore on staging;
- production smoke without real campaign activation.

## 32.3 State-machine property tests

Assert invariants:

- suppressed contact never becomes due/submitted;
- reply cancels future touches;
- hard bounce suppresses exact contact per policy;
- unapproved draft cannot send;
- inactive play cannot activate campaign;
- failed compliance cannot be overridden by score;
- provider retry cannot duplicate touch;
- merged company cannot retain active duplicate opportunity;
- guessed contact cannot auto-approve;
- stale critical evidence blocks send.

## 32.4 Performance tests

- bulk-source import throughput;
- website crawl concurrency under caps;
- score recalculation batches;
- campaign scheduler due-touch query;
- dashboard aggregate queries;
- migration/backfill on production-sized copy;
- database indexes and query plans.

## 32.5 Test evidence

Release bundle:

```text
runtime/release/<version>/
  pytest.txt
  ruff.txt
  typecheck.txt
  migration-upgrade.txt
  migration-downgrade.txt
  security-tests.txt
  browser-tests.txt
  gold-set-metrics.json
  pilot-gate.json
  schema-diff.sql
  backup-restore.txt
  smoke.txt
```

---

# 33. Exact repository change map

The names below are recommended. Adapt only where a cleaner architecture is demonstrably better.

## 33.1 Existing files to modify

### `app/models.py`

- gradually split into domain modules or re-export models;
- add normalized company/opportunity/evidence/compliance/campaign models;
- mark legacy Prospect fields deprecated;
- add constraints and indexes;
- preserve contact models while adapting relationships.

### `app/schemas.py`

- versioned API schemas;
- play/source/company/opportunity/policy/campaign schemas;
- avoid exposing raw provider payloads by default.

### `app/config.py`

Add:

- connector credentials/settings;
- source/sending caps;
- feature flags;
- policy fail-closed defaults;
- active environment identity;
- encryption/redaction options;
- production revision checks.

### `app/main.py`

- register new routers;
- startup config/schema guards;
- request IDs;
- health/readiness dimensions;
- no automatic play default.

### `app/plays/__init__.py`

- remove `DEFAULT_PLAY_CODE` usage;
- expose registry/service;
- validate versions.

### `app/plays/field_service.py`

- split old French configuration into versioned France play;
- remove mixed code/data where possible;
- preserve historical compatibility.

### `app/jobs/ingestion.py`

- require explicit play version and source plan;
- use generic source-run service;
- idempotency/checkpoints;
- remove global default.

### `app/messaging.py`

- convert to evidence-constrained renderer;
- locale/template versions;
- claim mapping;
- deterministic validation;
- no unsupported pain assumptions.

### `app/scoring_v3.py` / `app/scoring.py`

- introduce profile/version abstraction;
- component evidence mapping;
- hard gates separate from score;
- snapshots rather than overwrite.

### `app/services.py` / `app/commercial.py`

- move business workflows into explicit domain services;
- one transaction boundary for qualification/contact-ready/campaign state;
- prevent duplicate tasks and state divergence.

### Existing routers

- adapt `prospects.py`, `sourcing.py`, `queue.py`, `contact_intelligence.py`, `dashboard.py`, `events.py` to normalized entities and versioned contracts;
- retain compatibility routes only temporarily.

### Existing templates

- remove France-specific assumptions from generic pages;
- add play/country context;
- rebuild review and campaign screens;
- show evidence/policy states.

## 33.2 Recommended new packages/files

```text
app/domain/
  companies/models.py
  companies/service.py
  companies/resolution.py
  opportunities/models.py
  opportunities/service.py
  evidence/models.py
  evidence/service.py
  plays/models.py
  plays/registry.py
  compliance/models.py
  compliance/engine.py
  qualification/service.py
  campaigns/models.py
  campaigns/service.py
  campaigns/state.py
  messaging/models.py
  messaging/renderer.py
  messaging/validators.py
  audit/models.py
  audit/service.py

app/sources/
  base.py
  registry.py
  companies_house.py
  companies_house_schemas.py
  sirene_adapter.py
  annuaire_adapter.py
  decp_adapter.py
  website_adapter.py
  commercial_csv.py
  manual.py

app/identity/
  company_names.py
  company_resolver.py
  domain_resolver.py
  crosswalks.py

app/intelligence/
  evidence_taxonomy.py
  website_signals.py
  technology.py
  triggers.py
  estimates.py
  buyer_roles.py

app/policies/
  registry.py
  uk_b2b_email_v1.py
  fr_b2b_email_v1.py
  disabled_jurisdictions.py

app/providers/
  sending/base.py
  sending/<provider>.py
  verification/base.py
  replies/<provider>.py

app/jobs/
  source_runs.py
  identity_resolution.py
  domain_resolution.py
  evidence_enrichment.py
  estimates.py
  compliance.py
  campaigns.py
  provider_events.py
  replies.py
  gold_metrics.py

app/routers/
  market_plays.py
  source_runs.py
  companies.py
  opportunities_v1.py
  compliance.py
  campaigns.py
  conversations.py
  quality.py
  audit.py

app/templates/
  market_plays/
  source_runs/
  companies/
  opportunities/
  campaigns/
  quality/
  audit/

tests/
  unit/
  contract/
  integration/
  migration/
  security/
  browser/
  fixtures/gold_set/
```

## 33.3 Documentation changes

### `README.md`

- new mission;
- supported plays;
- safety boundaries;
- local setup;
- test baseline;
- explicit non-production/pilot status until gates pass.

### `GUIDE.md`

Rewrite operator workflow. Remove stale IT/cyber language.

### `DEPLOY.md`

- production reconciliation;
- migration rehearsal;
- release evidence;
- backup/restore;
- feature flags;
- campaign emergency pause.

### New docs

```text
docs/architecture/MULTI_MARKET_ARCHITECTURE.md
docs/data/DOMAIN_MODEL.md
docs/data/EVIDENCE_TAXONOMY.md
docs/markets/FIELD_OPERATIONS_UK_V1.md
docs/markets/FIELD_OPERATIONS_FR_V2.md
docs/compliance/POLICY_ENGINE.md
docs/campaigns/STATE_MACHINES.md
docs/quality/GOLD_SET_PROTOCOL.md
docs/operations/PILOT_RUNBOOK.md
docs/operations/INCIDENT_RUNBOOK.md
docs/releases/RELEASE_GATE.md
```

---

# 34. Alembic migration plan

The current archive includes revisions through `006_contact_intelligence.py`. Confirm production head before assigning actual IDs.

## Proposed sequence

### `007_market_play_versions`

- stable market plays;
- immutable versions;
- country/jurisdiction/language/policy/profile references;
- migrate existing play.

### `008_companies_identity`

- companies;
- names;
- identifiers;
- classifications;
- locations;
- domains;
- merge audit.

### `009_source_framework`

- connectors;
- source runs;
- source records;
- checkpoints/health.

### `010_opportunities_evidence`

- opportunities;
- evidence items/relations;
- triggers;
- estimates;
- initial backfill from Prospect/EvidenceSignal.

### `011_people_roles_contact_links`

- people/person roles;
- adapt existing contact people/points/evidence to company/opportunity model;
- preserve IDs where practical.

### `012_compliance_and_qualification`

- policy versions;
- decisions;
- gate definitions/reviews;
- suppression scopes.

### `013_score_snapshots`

- scoring profiles;
- snapshots/components/evidence links;
- backfill current score as legacy snapshot.

### `014_campaigns_sequences`

- campaigns;
- sequence/version/steps;
- memberships;
- drafts;
- touches;
- experiments.

### `015_provider_conversations`

- provider events;
- reply/conversation events;
- stop reasons;
- delivery statuses.

### `016_audit_retention_quality`

- audit events;
- retention metadata;
- gold labels/runs/metrics;
- release records.

### `017_legacy_projection_guards`

- deprecated/read-only markers;
- triggers/constraints only if safe;
- cutover support.

### Later contraction migration

Remove legacy fields only after cutover criteria.

## 34.1 Migration requirements

Each migration must include:

- upgrade;
- downgrade or documented restore-only exception;
- online/locking assessment;
- indexes created safely;
- batch backfill outside transaction where necessary;
- invariant checks;
- production-size rehearsal timing;
- rollback point;
- compatibility matrix with application versions.

## 34.2 Schema guard

Extend existing schema guard to verify:

- expected Alembic head;
- required tables/indexes/constraints;
- no partially completed backfill flag;
- application release compatible with schema range;
- campaign system disabled during incompatible migrations.

---

# 35. Deployment, production reconciliation, and rollback

## 35.1 Production reconciliation is P0

Before modifying production:

1. record host/container/service topology;
2. locate actual repository/application path;
3. record running image/commit/build hash;
4. record database URL host/name without exposing secret;
5. record Alembic revision;
6. count critical tables;
7. checksum deployment scripts/config templates;
8. run read-only health/smoke;
9. compare archive to production;
10. classify production-only changes and decide merge source of truth.

Do not deploy the uploaded archive over production until reconciliation is complete.

## 35.2 Reconciliation artifact

```json
{
  "production_commit": "...",
  "archive_commit": "...",
  "production_schema": "...",
  "archive_schema": "006_contact_intelligence",
  "differences": [],
  "decision": "production_is_source|archive_is_source|manual_merge_required",
  "approved_by": "..."
}
```

## 35.3 Environment strategy

- local;
- CI;
- isolated staging with production-like PostgreSQL;
- production.

No live contacts or sending credentials in local fixtures.

## 35.4 Feature flags

- new company model reads;
- UK source adapter;
- France V2 play;
- policy engine enforcement;
- campaign UI;
- provider sending;
- reply ingestion;
- gold-set gate;
- global emergency send disable.

Defaults fail closed in production.

## 35.5 Deployment sequence

1. backup database and configuration;
2. verify restore target;
3. deploy backward-compatible application if needed;
4. run expand migrations;
5. run/resume backfills;
6. validate invariants;
7. enable shadow reads;
8. compare outputs;
9. enable operator screens for internal use;
10. run gold-set tests;
11. activate pilot play only;
12. activate provider sending only after separate approval.

## 35.6 Rollback

Application rollback must remain compatible with expanded schema. For destructive contraction, restore from tested backup rather than relying on unsafe downgrade.

## 35.7 Release gate

Production release fails if:

- baseline tests/lint fail;
- migration rehearsal absent;
- backup or restore check fails;
- schema guard fails;
- gold-set metrics regress below threshold;
- policy engine unavailable;
- emergency send stop unavailable;
- unresolved P0 security issue;
- production reconciliation incomplete;
- smoke test fails.

---

# 36. Controlled live-pilot protocol

## 36.1 Pre-pilot checklist

- portfolio targeted landing page live;
- verified case-study claims only;
- mailbox authentication complete;
- sending/reply provider tested;
- UK/France policies reviewed;
- 50-company gold set labeled;
- quality thresholds pass;
- every first-touch draft reviewed;
- suppression/stop tests pass;
- dashboard and incident pause ready.

## 36.2 Pilot stages

### Stage 1 — Internal dry run

- generate 20 packets;
- no external sending;
- manually inspect identity, evidence, buyer, contact, policy, draft;
- reject and classify errors;
- fix system.

### Stage 2 — Test mailboxes

- send through real provider to controlled addresses;
- verify threading, rendering, reply ingestion, bounce handling, stop rules, and audit.

### Stage 3 — First 20 external sends

- 5 per business day initially;
- UK and France cohorts separated;
- full first-touch approval;
- no guessed-only contacts;
- inspect every provider event and reply daily.

### Stage 4 — Review gate

Review:

- bounces;
- complaints/opt-outs;
- wrong-company/person feedback;
- reply relevance;
- message awkwardness;
- evidence errors;
- policy issues;
- qualified conversations.

### Stage 5 — Next 30

Only if no critical issue and quality remains above thresholds. Increase to no more than 10 first touches/day initially.

## 36.3 Pilot success criteria

Engineering success:

- no duplicate sends;
- no suppressed/policy-blocked send;
- no unsupported message claims;
- stop on reply/opt-out/bounce works;
- provider state reconciles;
- all actions audited.

Data success:

- threshold metrics hold;
- low wrong-company and wrong-buyer feedback;
- contact states predict outcomes reasonably.

Commercial success:

- replies include relevant operational discussion;
- at least some positive/referral responses;
- fit calls can be booked;
- learning identifies a stronger cohort/message/evidence pattern.

Do not set a guaranteed deal target from 50 sends.

## 36.4 Immediate stop conditions

- complaint;
- accidental prohibited entity/channel;
- duplicate send;
- policy/suppression bypass;
- wrong-company data leak;
- provider compromise;
- high hard-bounce pattern;
- unsupported claim found in sent copy;
- reply-stop failure;
- legal concern.

Pause, preserve evidence, investigate, correct, and document before resuming.

---

# 37. 30/60/90-day implementation plan

## Days 1–5 — Truth, production, and architecture

- reconcile production/archive;
- freeze baseline artifact;
- map legacy dependencies;
- finalize UK/France play specs;
- finalize domain model and migration plan;
- establish P0 feature flags and emergency stop;
- rewrite README status truth.

## Days 6–12 — Expand schema and play system

- migrations 007–010 equivalents;
- play/version registry;
- company/source/opportunity/evidence models;
- explicit play context everywhere;
- backfill framework;
- tests and shadow reports.

## Days 13–20 — UK source and identity/domain

- Companies House adapter;
- UK classification config;
- identity resolution;
- domain verification;
- website evidence localization;
- UK entity policy classification;
- source-run UI.

## Days 21–30 — Evidence, buyer, contact, policy

- evidence taxonomy;
- trigger and complexity extraction;
- estimates;
- English/French buyer roles;
- contact model adaptation;
- compliance engine;
- score snapshots/hard gates;
- qualification UI.

## Days 31–40 — Campaign execution

- campaigns/sequences/drafts/touches;
- evidence-constrained messages;
- approvals;
- provider abstraction;
- reply ingestion;
- stop rules;
- deliverability setup;
- UI and audit.

## Days 41–50 — Gold set and QA

- label 50 companies;
- tune rules;
- meet thresholds;
- migration/security/browser/performance tests;
- documentation and runbooks;
- staging backup/restore/deployment rehearsal.

## Days 51–60 — Controlled pilot

- dry run;
- test mailboxes;
- first 20 sends;
- review;
- next 30 if safe;
- weekly commercial/quality report;
- refine one cohort at a time.

## Days 61–90 — Calibration and selective scale

- improve source/contact coverage;
- refine accepted evidence patterns;
- automate only proven manual steps;
- integrate portfolio conversions and commercial outcomes;
- add second message experiment;
- evaluate whether one country/vertical deserves focus;
- do not enable new jurisdictions without separate gate.

---

# 38. Prioritized implementation backlog

## 38.1 P0 — Required before any new-market outreach

| ID | Task | Acceptance criteria |
|---|---|---|
| PF-P0-001 | Reconcile production and archive | Commit/schema/config differences documented and approved |
| PF-P0-002 | Remove runtime default play | Every source/import/opportunity/campaign has explicit play version |
| PF-P0-003 | Version market plays | UK V1 and FR V2 validated; historical France play preserved |
| PF-P0-004 | Normalize company identity | UK/FR identifiers, classifications, locations, domains supported |
| PF-P0-005 | Generic source-run framework | Idempotent, checkpointed, adapter-versioned, auditable |
| PF-P0-006 | Companies House adapter | Official identity/status/SIC/location normalized with fixtures |
| PF-P0-007 | Wrap French adapters | Existing Sirene/Annuaire/DECP work through generic interface |
| PF-P0-008 | Identity resolution | Explainable outcomes and conflict review |
| PF-P0-009 | Domain verification | Official-domain evidence and SSRF-safe crawl gate |
| PF-P0-010 | Evidence taxonomy | Versioned codes, provenance, freshness, contradictions |
| PF-P0-011 | Operational complexity/estimate | Technician range never equated to employee count |
| PF-P0-012 | UK/FR buyer roles | Current-role confidence and primary/alternate buyer |
| PF-P0-013 | Compliance engine | UK/FR policies, Germany/NL fail closed, trace stored |
| PF-P0-014 | Hard gates + score snapshots | Score cannot bypass identity, policy, suppression, human review |
| PF-P0-015 | Contact localization | Published/imported/guessed states preserved; no guessed auto-approval |
| PF-P0-016 | Qualification UI | Evidence-linked decision and controlled reasons |
| PF-P0-017 | Gold-set framework | 50 labels and metrics with release comparison |
| PF-P0-018 | Campaign/sequence model | Immutable versions, memberships, drafts, touches, stop states |
| PF-P0-019 | Evidence-constrained messaging | Every personalized claim maps to evidence |
| PF-P0-020 | Sending/reply controls | Authentication tested; idempotency; reply/opt-out/bounce stop |
| PF-P0-021 | Emergency pause | Global and campaign-level send disable tested |
| PF-P0-022 | Migration rehearsal | Production-like upgrade/backfill/restore evidence |
| PF-P0-023 | Release gate | Tests, lint, security, gold metrics, backup, smoke pass |

## 38.2 P1 — Required before scaling beyond 50 sends

- provider health dashboard;
- source freshness scheduler;
- role/contact reverification before send;
- reply classification UI;
- campaign cohort/variant analytics;
- operator RBAC/MFA;
- structured audit explorer;
- safe export controls;
- website trigger and job-page source improvements;
- commercial CSV import UI;
- contact-source precision reports;
- dashboard query optimization;
- incident runbook exercise;
- portfolio form/conversion outcome integration.

## 38.3 P2 — After commercial signal

- additional official/authorized source adapters;
- assisted LLM evidence summarization with strict citations;
- agency-partner play;
- workflow-specific evidence models;
- CRM integration;
- calendar/call outcome sync;
- proposal/revenue outcome tracking;
- semi-automated recurring cohort creation;
- deeper technology/integration detection;
- parent/subsidiary graph.

## 38.4 P3 — Later

- Netherlands/Germany plays after legal/channel design;
- multiple operators/tenant architecture if genuinely needed;
- advanced experiment engine;
- partner/referral channels;
- inbound intent enrichment;
- controlled content/SEO intelligence;
- broader vertical play registry.

---

# 39. Codex/Antigravity execution protocol

This section defines how an implementation agent must work. It is not permission to make uncontrolled changes.

## 39.1 Mandatory behavior

The agent must:

1. read the repository, migrations, docs, tests, deployment scripts, and existing contact-intelligence architecture before editing;
2. generate a baseline artifact;
3. reconcile requirements against actual code;
4. maintain a decision log;
5. work in gated phases;
6. add tests before or with behavior changes;
7. preserve safe existing capabilities;
8. avoid broad rewrites without migration plan;
9. never weaken security/policy/human gates to make tests pass;
10. stop at a gate failure and report exact evidence;
11. produce a release artifact and operator documentation.

## 39.2 Required pre-implementation outputs

```text
IMPLEMENTATION_CONTEXT.md
CURRENT_ARCHITECTURE.md
GAP_MATRIX.md
DATA_MIGRATION_MAP.md
FILE_CHANGE_PLAN.md
RISK_REGISTER.md
TEST_PLAN.md
PRODUCTION_RECONCILIATION.md
```

## 39.3 Gate sequence

### Gate 0 — Baseline

- existing tests and Ruff pass;
- production/archive status known;
- no uncommitted accidental changes;
- architecture map accepted.

### Gate 1 — Data foundation

- play versions;
- companies/source/opportunities/evidence schema;
- migrations/backfill tests;
- no UI/send activation.

### Gate 2 — Sources and resolution

- Companies House + wrapped France adapters;
- identity/domain accuracy measured against fixtures/gold subset;
- SSRF/security tests pass.

### Gate 3 — Evidence, buyer, contact, policy

- taxonomy, estimates, roles, contact states, policy trace;
- qualification and score gates;
- no campaigns yet.

### Gate 4 — Campaign engine

- sequence/draft/touch/provider models;
- evidence validator;
- stop/idempotency tests;
- test mailboxes only.

### Gate 5 — Gold-set acceptance

- 50 labels;
- thresholds pass;
- false-positive report accepted.

### Gate 6 — Production pilot readiness

- backup/restore;
- migration rehearsal;
- authenticated sending;
- emergency pause;
- operator runbook;
- portfolio ready.

### Gate 7 — First 20

- human-approved sends;
- daily review;
- no automatic scaling.

## 39.4 Required final report per gate

- files changed;
- migrations;
- behavior added/removed;
- tests run and exact outputs;
- security/policy impact;
- data migration result;
- known limitations;
- rollback procedure;
- screenshots/sample records where useful;
- next gate prerequisites.

## 39.5 Forbidden shortcuts

- changing tests to accept unsafe behavior;
- replacing normalized evidence with an opaque LLM score;
- using unofficial scraped personal data without source/policy review;
- activating Germany/Netherlands;
- enabling LinkedIn automation;
- auto-sending guessed addresses;
- hiding production mismatch;
- deleting legacy data before verified backfill;
- setting all conflicts to “high confidence”;
- using one generic message across countries;
- treating provider “accepted” as delivered;
- reporting vanity metrics without denominators.

---

# 40. Release gates and definition of done

## 40.1 Data gate

- [ ] Legal identities resolve correctly above threshold.
- [ ] Domains resolve correctly above threshold.
- [ ] Classifications and source dates are preserved.
- [ ] Field-team estimates are ranges with evidence.
- [ ] Contradictions block critical actions.
- [ ] Backfill is resumable and validated.

## 40.2 Policy and contact gate

- [ ] UK and France policy versions reviewed and active.
- [ ] Germany/Netherlands fail closed.
- [ ] No guessed-only contact can auto-approve.
- [ ] Suppression blocks every downstream send path.
- [ ] First-contact disclosure and opt-out are versioned.
- [ ] Contact freshness is checked before send.

## 40.3 Messaging gate

- [ ] Every personalized claim links to evidence.
- [ ] Unsupported Fractal Tech metrics absent.
- [ ] Locale and buyer role are correct.
- [ ] Human approves first touch.
- [ ] Approved draft locks exact content.
- [ ] No false `Re:` thread.

## 40.4 Campaign gate

- [ ] Campaign has explicit play/policy/sequence/sender/cap.
- [ ] State-machine tests pass.
- [ ] Provider submission is idempotent.
- [ ] Reply, opt-out, hard bounce, complaint, meeting, and manual stop cancel future steps.
- [ ] Emergency pause tested.
- [ ] Delivery/reply events reconcile.

## 40.5 Quality gate

- [ ] 50-company gold set complete.
- [ ] Entity precision ≥95%.
- [ ] Domain precision ≥90%.
- [ ] Vertical eligibility accuracy ≥85%.
- [ ] Primary buyer-role accuracy ≥80%.
- [ ] 100% message claim traceability.
- [ ] Zero policy/suppression bypass in tests.
- [ ] Regression report passes.

## 40.6 Production gate

- [ ] Archive/production reconciled.
- [ ] Exact release commit and schema recorded.
- [ ] Backup created and restore tested.
- [ ] Migrations rehearsed.
- [ ] Health/readiness/smoke pass.
- [ ] Logs/metrics/alerts operational.
- [ ] Rollback executable.
- [ ] Sending disabled by default until pilot activation approval.

## 40.7 Commercial readiness gate

- [ ] Target portfolio path is live.
- [ ] Case-study claims are verified.
- [ ] Mapping Sprint and proposal assets are ready.
- [ ] Mailbox can receive/respond.
- [ ] Reply ownership and response SLA defined.
- [ ] Daily pilot review routine exists.
- [ ] Outcomes can be recorded through call/proposal/win/loss.

## 40.8 Definition of done

ProspectForge is ready for the requested launch only when it can take an explicit UK or France market play, ingest permitted sources, resolve the correct incorporated company and official domain, assemble source-backed operational evidence, estimate fit without inventing technician counts, identify a current relevant buyer, discover or import a defensible contact route, evaluate jurisdiction policy and suppression, calculate an explainable score behind hard gates, support human qualification, generate a localized message whose claims all cite evidence, require approval, submit one idempotent touch through an authenticated sender, stop correctly on any response or prohibition, and report both data quality and commercial outcomes by cohort—while remaining recoverable, auditable, and fail-closed.

---

# 41. Source and reference appendix

Verify current terms, interfaces, and legal guidance at implementation time.

## Official company sources

- [Companies House API documentation](https://developer.company-information.service.gov.uk/)
- [Companies House data products](https://www.gov.uk/government/organisations/companies-house/about/personal-information-charter)
- [INSEE Sirene API catalogue](https://portail-api.insee.fr/)
- [Annuaire des Entreprises](https://annuaire-entreprises.data.gouv.fr/)
- [French public procurement open data](https://www.data.gouv.fr/fr/datasets/donnees-essentielles-de-la-commande-publique/)

## Direct-marketing and data-protection guidance

- [UK ICO — Business-to-business marketing](https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/business-to-business-marketing/)
- [UK ICO — Electronic mail marketing](https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/guide-to-pecr/electronic-and-telephone-marketing/electronic-mail-marketing/)
- [CNIL — communication électronique : quelles règles ?](https://www.cnil.fr/fr/communication-electronique-quelles-regles)
- [Germany Act Against Unfair Competition, English translation](https://www.gesetze-im-internet.de/englisch_uwg/englisch_uwg.html)
- [LinkedIn User Agreement](https://www.linkedin.com/legal/user-agreement)

## Sender authentication

- [Google email sender guidelines](https://support.google.com/mail/answer/81126)
- [Microsoft email sender guidance](https://learn.microsoft.com/en-us/defender-office-365/email-authentication-about)
- [DMARC overview](https://dmarc.org/overview/)

---

# Appendix A — Opportunity packet example

```yaml
opportunity_id: OPP-...
play_version: FIELD_OPERATIONS_UK_V1@1.0.0
company:
  id: CMP-...
  legal_name: Example Technical Services Ltd
  identifier:
    scheme: companies_house_number
    value: "01234567"
  status: active
  official_domain: example.co.uk
  domain_confidence: high
fit:
  vertical: commercial_hvac
  vertical_evidence: [EV-001, EV-002]
  field_team_estimate:
    lower: 15
    upper: 35
    confidence: medium
    evidence: [EV-003, EV-004]
  complexity:
    signals: [recurring_contracts, multiple_regions, parts_stock]
opportunity:
  type: integration_control_layer
  hypothesis: "Field completion evidence and invoice preparation may cross multiple systems."
  evidence: [EV-005, EV-006]
  trigger:
    type: service_coordinator_hiring
    observed_at: 2026-07-18
buyer:
  person_id: PER-...
  role: OPERATIONS_DIRECTOR
  confidence: high
  evidence: [EV-007]
contact:
  contact_point_id: CP-...
  publication: published
  identity_match: exact
  deliverability: deliverable
  suppression: clear
policy:
  decision: allow_review
  policy_version: uk_b2b_email_corporate_v1
qualification:
  decision: accepted
  reviewer: user-...
message:
  draft_id: MSG-...
  template: UK_FIELD_OPS_EVIDENCE_FIRST_01@1
  claims:
    - text: "..."
      evidence: EV-005
  approval: approved
```

# Appendix B — Error and rejection reason taxonomy

## Company/identity

- `IDENTITY_NOT_RESOLVED`
- `IDENTITY_CONFLICT`
- `ENTITY_INACTIVE`
- `ENTITY_LEGAL_FORM_EXCLUDED`
- `WRONG_SUBSIDIARY`
- `DUPLICATE_COMPANY`

## Domain

- `DOMAIN_NOT_FOUND`
- `DOMAIN_WRONG_ENTITY`
- `DOMAIN_DIRECTORY`
- `DOMAIN_SHARED_PARENT_REVIEW`
- `DOMAIN_UNSAFE_OR_INACCESSIBLE`

## ICP/evidence

- `VERTICAL_NOT_ELIGIBLE`
- `SIZE_TOO_SMALL`
- `COMPLEXITY_INSUFFICIENT`
- `NO_OPPORTUNITY_EVIDENCE`
- `TRIGGER_STALE`
- `ALREADY_WELL_SOLVED`

## Buyer/contact

- `BUYER_NOT_FOUND`
- `BUYER_ROLE_UNCERTAIN`
- `CONTACT_NOT_FOUND`
- `CONTACT_GUESSED_REVIEW_REQUIRED`
- `CONTACT_UNDELIVERABLE`
- `CONTACT_STALE`

## Policy/suppression

- `JURISDICTION_DISABLED`
- `POLICY_ENTITY_TYPE_BLOCK`
- `PROFESSIONAL_RELEVANCE_INSUFFICIENT`
- `SUPPRESSED_OPT_OUT`
- `SUPPRESSED_COMPLAINT`
- `SUPPRESSED_BOUNCE`
- `SUPPRESSED_MANUAL`

## Campaign

- `DRAFT_UNAPPROVED`
- `MESSAGE_CLAIM_UNSUPPORTED`
- `CAMPAIGN_CAP_REACHED`
- `CAMPAIGN_PAUSED`
- `SENDER_HEALTH_BLOCK`
- `PRIOR_REPLY_STOP`
- `MEETING_BOOKED_STOP`

# Appendix C — Pilot daily operator checklist

## Before sending

- [ ] Sender health green.
- [ ] No complaints/security alerts.
- [ ] Campaign/play/policy versions correct.
- [ ] Daily and per-domain caps correct.
- [ ] Each due touch revalidated.
- [ ] Every draft approved and locked.
- [ ] Evidence current.
- [ ] Suppression clear.

## After sending

- [ ] Provider acceptance reconciled.
- [ ] Delivery/bounce events processed.
- [ ] Replies triaged and future steps stopped.
- [ ] Opt-outs suppressed globally as required.
- [ ] Wrong-person/company feedback recorded.
- [ ] Positive replies answered manually.
- [ ] Quality/commercial outcomes updated.
- [ ] Incident pause used if any critical anomaly.

# Appendix D — Release sign-off record

```yaml
release: prospectforge-vX.Y.Z
commit: "..."
schema_revision: "..."
production_reconciliation: pass
market_plays:
  - FIELD_OPERATIONS_UK_V1@1.0.0
  - FIELD_OPERATIONS_FR_V2@2.0.0
checks:
  pytest: pass
  ruff: pass
  migrations: pass
  security: pass
  browser: pass
  gold_set:
    entity_precision: 0.96
    domain_precision: 0.92
    vertical_accuracy: 0.88
    buyer_top1_accuracy: 0.82
    claim_traceability: 1.00
  backup_restore: pass
  smoke: pass
sending_enabled: false
pilot_activation_approved_by: null
known_limitations: []
rollback_release: "..."
```
