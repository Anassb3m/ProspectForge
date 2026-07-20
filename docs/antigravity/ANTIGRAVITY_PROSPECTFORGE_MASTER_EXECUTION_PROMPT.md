# Antigravity Master Execution Prompt — ProspectForge Production Pilot and Client-Acquisition OS

> Paste this entire prompt into Google Antigravity after adding the latest `ProspectForge-main` repository as the project workspace. Give the agent terminal and browser access for this workspace. Replace only the values in the **Operator Inputs** section that are known. Do not shorten this prompt.

---

## Operator Inputs

Use these values when available. Never invent a credential or reveal secrets in logs, chat, screenshots, commits, or generated documentation.

```text
REPOSITORY_PATH=<ABSOLUTE_PATH_TO_THE_LATEST_PROSPECTFORGE_REPOSITORY>
TARGET_BRANCH=antigravity/prospectforge-production-pilot
PRODUCTION_DOMAIN=prospects.elevya.tech
VPS_SSH_TARGET=<SSH_ALIAS_OR_USER_AT_IP>
VPS_DEPLOY_PATH=/opt/prospectforge
ADMIN_EMAIL=<ADMIN_EMAIL>
EXISTING_REVERSE_PROXY=<caddy|nginx|unknown>
DEPLOY_NOW=<yes|no>
```

If a value is unknown, discover it safely from the repository or environment when possible. Ask me only when a missing value is a genuine blocker, such as an SSH target, DNS access, external API key, or production administrator email. Do not interrupt for routine engineering choices that can be resolved from the code, specifications, or standard production practice.

---

# 1. Your Role

Act as the principal software engineer, data-product architect, security reviewer, DevOps engineer, QA lead, and commercial-operations designer responsible for taking ProspectForge from its current repository state to a reliable, protected, production-pilot client-acquisition operating system.

This is not a superficial code review. You must:

1. Understand the business and commercial objective deeply.
2. Understand the existing architecture and every important data flow.
3. Compare the implementation against the repository’s V3 master specification.
4. Find contradictions, dead infrastructure, false assumptions, unsafe defaults, and partially implemented features.
5. Implement the missing or defective work in priority order.
6. Test the system at unit, integration, migration, browser, Docker, and live-source levels where access permits.
7. Deploy it safely to the VPS when `DEPLOY_NOW=yes` and credentials are available.
8. Leave an exact operator workflow for using it to find, qualify, contact, and track prospective clients.
9. Produce evidence for every important claim.

Do not treat passing tests as proof that the product is commercially correct. Do not treat documentation as proof that code enforces the documented behavior. Inspect and verify both.

---

# 2. Product Mission

ProspectForge is an internal client-acquisition operating system for finding and converting French non-technical or lightly technical SMEs that may buy custom operational software.

The initial market play is:

```text
FIELD_SERVICE_OPERATIONS_FR
```

It should target businesses such as:

- HVAC and refrigeration service companies;
- maintenance and technical-service firms;
- electrical-installation companies;
- field-service and facilities operators;
- industrial maintenance businesses;
- companies with technicians, recurring interventions, quotes, reports, parts, dispatching, and management coordination.

The system must not default back to software companies, ESNs, IT consultancies, cybersecurity vendors, cloud firms, or companies that are likely to build the same software internally.

The default commercial offer is not “Laravel development” or “digital transformation.” It is:

> A focused operations-control system for quotes, interventions, technician planning, reports, parts, customer follow-up, and management visibility, configured around the company’s real workflow.

The product’s job is not to create a giant lead database. Its job is to create a small, defensible, meeting-ready work queue.

A meeting-ready prospect must have sufficient evidence for all of the following:

1. **ICP fit:** the company structurally resembles the target customer.
2. **Pain evidence:** there is credible evidence of operational friction or a carefully verified pain hypothesis.
3. **Buying trigger:** there is a plausible reason the company may act now.
4. **Authority:** the likely buyer or relevant role is identified.
5. **Contactability:** there is a legitimate, accurately classified contact path.
6. **Offer match:** the packaged offer and proof assets are relevant.
7. **Human qualification:** the operator explicitly confirms the six dimensions.
8. **Compliance:** source provenance, first-contact disclosure, opt-out, and suppression rules are satisfied.

No numeric score may bypass these gates.

---

# 3. Ground Truth and Repository Documents

Before editing code, read these files completely:

```text
README.md
DEPLOY.md
GUIDE.md
docs/archive/PROSPECTFORGE_V3_CLIENT_ACQUISITION_REBUILD_MASTER_SPEC.md
docs/archive/prospectforge_spec_python.md
docs/archive/logic_specification.txt
pyproject.toml
docker-compose.yml
Dockerfile
.env.example
.env.production.example
alembic.ini
all Alembic revisions
```

Then inspect all code under:

```text
app/
tests/
scripts/
alembic/
```

Do not skim only filenames. Trace the important execution paths through routers, services, scoring, discovery, ingestion, models, templates, security, background jobs, migrations, Docker startup, and deployment scripts.

Treat `docs/archive/PROSPECTFORGE_V3_CLIENT_ACQUISITION_REBUILD_MASTER_SPEC.md`
as historical product direction, not current ground truth. When the archived
specification conflicts with safer, simpler, or more commercially correct
behavior in the active code and current docs, preserve the active behavior and
document the decision.

---

# 4. Required Working Method

## 4.1 Preserve a safe baseline

Before modifying anything:

1. Run `git status --short`.
2. Record the current branch and commit hash.
3. Create or switch to `TARGET_BRANCH` without discarding user changes.
4. Save a patch of any pre-existing uncommitted changes.
5. Never overwrite `.env`, credentials, user data, or production volumes.
6. Never commit secrets, database dumps, API keys, or generated personal data.

Use small, intentional commits grouped by coherent changes. Do not create one enormous unreviewable commit.

## 4.2 Use evidence artifacts

Create and continuously update these documents under `docs/antigravity/`:

```text
PROJECT_UNDERSTANDING.md
BASELINE_REPORT.md
GAP_MATRIX.md
IMPLEMENTATION_PLAN.md
DATA_FLOW_AND_TRUST_MODEL.md
SECURITY_REVIEW.md
TEST_AND_VALIDATION_REPORT.md
LIVE_SOURCE_VALIDATION.md
DEPLOYMENT_RECORD.md
OPERATOR_LAUNCH_PLAYBOOK.md
CHANGELOG_ANTIGRAVITY.md
KNOWN_LIMITATIONS.md
```

These are operational artifacts, not marketing copy. Include commands, actual results, file references, decisions, risks, and remaining limitations.

## 4.3 Do not stop at analysis

After producing the initial gap matrix, implement the work. Do not return only recommendations unless blocked by missing access or credentials.

For routine, reversible repository edits, proceed without asking me for permission. Ask only before:

- deleting or rewriting production data;
- changing DNS or external accounts;
- opening public ports;
- sending real outreach;
- purchasing paid services;
- pushing to a remote repository when authorization is unclear;
- performing an irreversible production action.

## 4.4 Use parallel agents carefully

If Antigravity supports parallel subagents, divide work by bounded workstreams:

- architecture and commercial correctness;
- data model and migrations;
- discovery and evidence ingestion;
- scoring and qualification gates;
- queue and operator UX;
- security and compliance;
- testing and deployment.

The lead agent must reconcile all work, resolve conflicts, rerun the complete test suite, and verify the integrated result. Do not allow parallel agents to make incompatible migrations or duplicate architectural changes.

---

# 5. Phase 0 — Deep Project Comprehension

Produce `PROJECT_UNDERSTANDING.md` before implementing fixes. It must explain, in your own words:

1. What ProspectForge does commercially.
2. Who the first buyer profile is.
3. What the packaged offer is.
4. Which data sources exist now.
5. How a candidate moves from discovery to contact-ready.
6. How evidence is stored and scored.
7. How contacts and people are represented.
8. How human qualification works.
9. How outreach history, tasks, follow-ups, and pipeline status work.
10. How suppression and opt-out work.
11. How local and production deployment work.
12. Which features are implemented, partial, dead, legacy, or only documented.

Create a route map and a code map. Identify the source-of-truth object for:

- company/prospect identity;
- evidence;
- score dimensions;
- readiness;
- human qualification;
- contact confidence;
- current outreach status;
- next action;
- suppression;
- market play;
- ingestion run.

Where multiple sources of truth exist, mark them as defects to resolve.

---

# 6. Phase 1 — Establish the Baseline

Run and record the exact results of:

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
```

Inspect `pyproject.toml` and use the project’s configured commands. If virtual-environment setup is needed, create it without modifying global Python.

Validate migrations in at least these scenarios:

1. Fresh empty database to `head`.
2. Existing schema at each realistically supported previous revision to `head`.
3. Application startup after migration.
4. Migration failure behavior: production startup must fail hard.

Validate Docker configuration:

```bash
docker compose config
```

When Docker is available:

```bash
docker compose build --pull app
docker compose up -d db app
docker compose ps
docker compose logs --tail=200 app
curl -fsS http://127.0.0.1:${APP_PORT:-18081}/health
curl -fsS http://127.0.0.1:${APP_PORT:-18081}/ready
```

Do not claim Docker deployment works if Docker was unavailable or a real build was not completed. State the precise boundary of validation.

Use a browser smoke test to verify:

- login;
- logout;
- dashboard;
- prospects list;
- sourcing;
- queue;
- qualification form;
- prospect detail;
- follow-ups;
- Kanban;
- CSV import when safe;
- CSRF failure behavior;
- login throttling behavior.

Capture screenshots or browser artifacts without exposing personal data or credentials.

---

# 7. Phase 2 — Build the Gap Matrix

Create `GAP_MATRIX.md` with one row per requirement and these columns:

```text
Requirement
Commercial importance
Current implementation
Evidence inspected
Status: complete / partial / missing / defective / legacy
Risk
Required change
Files involved
Test required
Priority: P0 / P1 / P2 / deferred
```

At minimum, audit every item in Sections 8–20 below.

---

# 8. Commercial Correctness — Non-Negotiable Rules

Implement and test all of the following.

## 8.1 Awards are timing signals, never automatic pain

A DECP or public-procurement award may increase:

- trigger score;
- potential value;
- structural complexity confidence.

It must not directly satisfy the pain gate.

Generic words such as these must not be treated as pain evidence by themselves:

```text
maintenance
technicien
installation
service
intervention
contrat
```

These often describe the company’s business, not a broken workflow.

Pain requires credible evidence, such as:

- explicit spreadsheet or Excel workflow;
- paper intervention reports;
- WhatsApp coordination;
- manual dispatching or planning;
- repeated double entry;
- disconnected portals or systems;
- administrative or planning recruitment caused by workload;
- reporting bottlenecks;
- recurring customer complaints about delays or visibility;
- multisite and technician complexity combined with supporting evidence;
- human-confirmed pain after manual research.

Create tests proving that:

1. Award-only prospects fail the pain gate.
2. Target NAF + award + director + contact still does not become contact-ready without pain.
3. Generic business-language keywords do not fabricate pain.
4. Verified pain evidence can satisfy the pain floor.

## 8.2 Split score from readiness

Keep a useful opportunity score, but readiness must be gate-driven.

The dimensions should remain explicit and inspectable:

- fit;
- pain;
- trigger;
- authority;
- value;
- data quality;
- penalties;
- confidence multiplier.

Every displayed score must include explanations and source-backed evidence.

A high score must never bypass:

- minimum fit;
- minimum pain;
- minimum trigger;
- buyer confirmation;
- contact confirmation;
- offer/proof match;
- human acceptance;
- suppression/compliance checks.

## 8.3 Human qualification must be enforced server-side

The qualification form’s six confirmations are mandatory for `Accept`:

```text
fit_confirmed
pain_confirmed
trigger_confirmed
buyer_confirmed
contact_confirmed
offer_match_confirmed
```

Do not trust browser checkboxes alone. Validate on the server.

The latest accepted `QualificationReview` must be the source of truth. A cached `manual_review_state` may exist for query performance, but it must be derived consistently.

Create tests for:

- accept with zero confirmations;
- accept with one missing confirmation;
- successful accept with all confirmations;
- research/park/reject paths;
- a later review superseding an earlier review;
- readiness changing after review state changes.

## 8.4 Contact confidence must be honest

Separate:

### Mailbox deliverability

```text
deliverable
catch_all
risky
invalid
unknown
```

### Person matching

```text
exact_person_confirmed
published_personal
pattern_inferred
generic_role_address
unknown
```

A generic published address is not equivalent to a confirmed decision-maker address. A guessed pattern is not verified.

Email contact-ready should require an acceptable combination of deliverability and person match. LinkedIn-ready may use a confirmed LinkedIn identity instead.

Server-side enums must reject arbitrary confidence values.

Every manual confidence override must create an audit record with:

- operator;
- previous state;
- new state;
- reason;
- evidence source;
- timestamp.

Create tests for invalid enum values, pattern-inferred contacts, generic mailboxes, catch-all addresses, verified personal contacts, bounces, and suppression.

## 8.5 Proof and offer match must be real

Do not hard-code `offer_ok=True` or an equivalent unconditional pass.

Connect `offer_assets` or the current proof-asset model to readiness. An accepted prospect must have:

- a selected offer;
- at least one relevant proof asset or an explicit approved no-proof exception;
- a defined first-call objective;
- a safe claim set that does not invent outcomes.

Never fabricate client results, usage metrics, time savings, revenue, or testimonials.

---

# 9. Data Model and Sources of Truth

Audit for duplicated or disconnected representations.

The normalized database should be authoritative for:

- evidence signals;
- qualification reviews;
- contacts and confidence;
- tasks;
- suppression;
- ingestion runs;
- offer assets;
- market plays.

Legacy JSON fields may remain temporarily for compatibility but must not silently diverge from normalized tables.

## 9.1 Evidence deduplication

Create a stable evidence fingerprint using appropriate components, such as:

```text
prospect/company ID
source type
source record ID
signal type
canonical URL
observed date or source publication date
normalized content hash
```

Use a unique constraint or idempotent upsert.

Repeated ingestion must not:

- duplicate evidence;
- inflate source counts;
- inflate scores;
- create duplicate tasks;
- create duplicate contacts;
- create duplicate prospects for the same company/SIREN.

Create idempotency tests for registry and DECP ingestion.

## 9.2 Evidence expiration and provenance

Every evidence item should support:

- source type;
- source record ID;
- source URL when available;
- observed/published date;
- confidence;
- category: structural, pain, trigger, authority, contact, value;
- active/expired status;
- human-confirmed flag;
- raw excerpt or structured metadata within legal and copyright limits.

Scoring must use active, deduplicated evidence only.

## 9.3 Independent sources

Do not count multiple fields from one API response as independent sources.

Examples:

- NAF, address, and legal representative from one registry response = one source origin.
- DECP award + company website = two origins.
- A person extracted from the registry is not a separate origin from the registry.

Implement source-origin counting clearly and test it.

---

# 10. Remove Legacy V2/IT Behavior

Search the entire repository for stale concepts, including:

```text
REGISTRY_IT
IT registry
cyber
cybersécurité
cloud
ESN
SSII
TMA
CTO
DSI
software house
IT SME
```

Classify every occurrence as:

- valid historical documentation;
- migration compatibility;
- test fixture;
- active defect.

Remove active V2 commercial behavior from:

- discovery filters;
- NAF/CPV selection;
- source labels;
- scoring;
- UI filters;
- dashboards;
- documentation;
- command help;
- templates;
- CSS badges;
- tests.

If legacy values must remain for existing records, isolate them explicitly as legacy and ensure they never influence the active V3 queue.

---

# 11. Consolidate Scoring and State Recalculation

Audit `app/scoring.py`, `app/scoring_v3.py`, services, routers, ingestion, and event logging.

There must be one clear commercial projection service, for example:

```python
recompute_commercial_state(prospect_id)
```

Every mutation that can affect commercial state must trigger it:

- evidence added, removed, expired, or confirmed;
- person or buyer updated;
- contact added or confidence changed;
- qualification submitted;
- offer/proof asset selected;
- suppression or opt-out changed;
- outreach event logged;
- source data refreshed.

Separate:

### Opportunity score

How commercially attractive is the prospect based on evidence?

### Action urgency

What should the operator do next and when, based on replies, meetings, overdue follow-ups, pending first contact, proposal age, and expiring triggers?

Do not use a legacy acquisition score as action urgency.

Retire or clearly isolate unused scoring code. Add regression tests preventing V2 paths from overwriting V3 state.

---

# 12. Build a Real Today Queue

The main daily operating screen must merge actions, not merely sort prospects.

Prioritize in this order:

1. New replies requiring action.
2. Meetings today or tomorrow.
3. Overdue follow-ups.
4. Proposal follow-ups.
5. Accepted prospects awaiting first contact.
6. Contact-verification tasks.
7. Research tasks.
8. High-scoring unreviewed prospects.
9. Parked/backlog items only when due.

Each action should show:

- company;
- exact action;
- reason and evidence;
- due date;
- opportunity score;
- readiness failures;
- buyer;
- contact channel and confidence;
- previous outreach context;
- recommended next action;
- offer/proof asset;
- one-click complete/reschedule/open.

Connect the `tasks` table to this screen. Ensure qualification-created research and first-outreach tasks become visible. Avoid creating tasks that disappear into dead infrastructure.

Keep specialized screens such as prospects, follow-ups, sourcing, and Kanban, but make `/queue` the true daily command center.

Add tests for ordering, overdue tasks, replies, meetings, first-touch tasks, completion, rescheduling, and suppression.

---

# 13. Discovery and Research Improvements

Do not maximize volume. Maximize the precision of the top 10–20 weekly prospects.

## 13.1 Existing sources

Audit and harden:

- DECP/public-award ingestion;
- Recherche Entreprises/Annuaire ingestion;
- Sirene enrichment;
- website/domain discovery;
- contact candidates;
- optional Reacher/Harvester integrations.

For each adapter, implement:

- timeouts;
- retries with bounded backoff;
- rate limiting;
- clear user-agent when appropriate;
- caching;
- source timestamps;
- partial failure handling;
- structured error reporting;
- run metrics;
- idempotency;
- legal/terms awareness.

Never bypass access controls, CAPTCHAs, robots restrictions, or platform terms.

## 13.2 Website intelligence — highest-priority new evidence source

Implement a bounded, respectful company-website research adapter if it is missing or incomplete.

It should inspect only public company pages and extract source-backed signals such as:

- service locations and agencies;
- emergency or 24/7 service;
- technician/workforce language;
- maintenance contracts;
- customer portal availability;
- technician portal availability;
- service territories;
- downloadable forms;
- PDF-heavy workflows;
- recruitment links;
- certifications;
- recurring-service structure;
- published personal or generic emails;
- named operational roles;
- explicit mentions of planning, reporting, interventions, parts, contracts, dispatch, or customer visibility.

It must not claim pain merely because these words exist. Classify them as:

- structural complexity;
- possible pain hypothesis;
- trigger;
- contact evidence.

Require human confirmation for ambiguous pain.

Use strict crawl limits, same-domain rules, page-count limits, content-size limits, timeouts, and caching. Store provenance for every extracted signal.

## 13.3 Job-posting signals

Implement a compliant, public job-signal workflow when feasible. Prefer company career pages or APIs whose terms permit use.

Useful evidence includes recruitment for:

- planning/dispatch;
- ADV/administrative coordination;
- intervention reporting;
- service operations;
- GMAO/ERP migration;
- technician management;
- quote or contract administration.

A job post is usually a trigger or pain hypothesis, not automatic proof. Preserve the source and date.

## 13.4 BOAMP/BODACC

Implement only when the core queue, website intelligence, and evidence model are correct.

- BOAMP may improve award detail and source traceability.
- BODACC may identify expansion, acquisition, establishment changes, or management transitions.

Do not add sources merely to increase feature count.

## 13.5 LinkedIn boundary

Do not implement unauthorized LinkedIn scraping, automated login, browser evasion, or automated mass messaging.

The correct last-mile workflow is:

- system proposes a likely buyer role;
- operator manually confirms the person on LinkedIn or another public source;
- operator records the confirmed identity and URL;
- operator sends the first LinkedIn message manually.

---

# 14. Ingestion Run Management

Make ingestion observable and controllable.

Each run must record:

- source and mode;
- market play;
- parameters;
- start/end time;
- status;
- records examined;
- records rejected and reason distribution;
- prospects created;
- prospects updated;
- duplicate evidence skipped;
- contacts produced by confidence class;
- errors and retries;
- run duration;
- operator or scheduler identity.

Build an ingestion-run screen with drill-down and safe retry.

The production defaults must remain:

```text
ENABLE_SCHEDULER=false
ENABLE_NIGHTLY_INGESTION=false
INGESTION_RUN_CONTACTS=false
REACHER_ENABLED=false
HARVESTER_ENABLED=false
```

Do not enable scheduled discovery until live-source precision has been measured and accepted.

---

# 15. Compliance, Suppression, and Data Hygiene

Implement global suppression checks at every relevant boundary:

- before prospect insertion;
- after contact discovery;
- before qualification acceptance;
- before contact-ready status;
- before CSV export;
- before logging `Sent`;
- before any future mail integration.

Suppression should cover, where appropriate:

- email;
- domain;
- company/SIREN;
- person;
- phone;
- source-specific identifiers.

An opt-out event must immediately suppress future outreach and remove inappropriate due tasks.

Preserve:

- exact data source;
- first-contact disclosure timestamp;
- opt-out timestamp and reason;
- retention/anonymization state;
- audit history.

Do not provide legal conclusions. Implement clear operational controls and document that the operator remains responsible for applicable GDPR/CNIL B2B-prospecting practice.

---

# 16. Security Hardening

Audit and implement:

1. CSRF protection on all state-changing browser forms.
2. Login throttling and safe error messages.
3. Strong password hashing.
4. Strong `SECRET_KEY` validation.
5. Secure, HttpOnly, appropriate SameSite cookies.
6. `FORCE_HTTPS_COOKIES=true` behind production HTTPS.
7. Strict production trusted hosts.
8. Restricted proxy trust; never trust arbitrary forwarding sources unnecessarily.
9. Production docs/OpenAPI disabled or protected.
10. Security headers at application or reverse-proxy layer.
11. No public database port.
12. App bound to loopback when behind the existing reverse proxy.
13. No plaintext public access in the final domain deployment.
14. Secrets excluded from logs and source control.
15. Fail-hard database migrations.
16. Safe upload size and CSV validation.
17. Input validation and output escaping.
18. Dependency and container vulnerability review using available tools.
19. Backup and restore validation.
20. Minimal container privileges where practical.

Add automated security regressions for CSRF, throttling, trusted hosts, production docs, cookie flags, invalid contact states, and suppression.

---

# 17. Deployment Architecture

Preferred production architecture:

```text
https://prospects.elevya.tech
        ↓
existing VPS Caddy or nginx on 80/443
        ↓
127.0.0.1:18081
        ↓
ProspectForge app container
        ↓
PostgreSQL container, loopback/private network only
```

Do not expose PostgreSQL publicly.

Do not open application high ports publicly when the existing reverse proxy can serve the domain.

Use a real TLS certificate through the existing proxy. Do not use self-signed high-port HTTPS as the final production path.

Before modifying the VPS:

1. Confirm the SSH target and hostname.
2. Inspect running services and Docker stacks.
3. Inspect occupied ports.
4. Identify the existing reverse proxy.
5. Back up the current application database if it exists.
6. Back up any proxy configuration before editing it.
7. Confirm DNS resolves to the intended VPS.
8. Avoid changing unrelated services.

Production `.env` requirements:

```text
ENVIRONMENT=production
DEBUG=false
DOMAIN=prospects.elevya.tech
TRUSTED_HOSTS=prospects.elevya.tech,localhost,127.0.0.1
FORCE_HTTPS_COOKIES=true
RUN_MIGRATIONS=true
ENABLE_SCHEDULER=false
ENABLE_NIGHTLY_INGESTION=false
INGESTION_RUN_CONTACTS=false
REACHER_ENABLED=false
HARVESTER_ENABLED=false
TLS_MODE=off
```

Generate strong secrets locally or on the VPS. Never display them after initial secure delivery.

Use:

```text
APP_PORT=18081
POSTGRES_PORT=15432
```

or choose other loopback-only ports after checking conflicts.

The app entrypoint must:

1. wait for the database with a bounded timeout;
2. run `alembic upgrade head`;
3. fail immediately if migration fails;
4. create the initial admin only when appropriate;
5. seed required market plays idempotently;
6. start the application.

Do not use `create_all()` as a production migration fallback.

---

# 18. Deployment Execution and Proof

When `DEPLOY_NOW=yes` and access is available:

1. Create a pre-deployment database backup.
2. Sync or clone code to `/opt/prospectforge` without deleting `.env`, backups, or volumes.
3. Build the app image with `--pull`.
4. Run migrations.
5. Start only the required services.
6. Configure the existing reverse proxy for `prospects.elevya.tech`.
7. Validate and reload the proxy safely.
8. Verify firewall rules expose only intended ports.
9. Verify application and database binds.
10. Run health, readiness, login, browser, and core-workflow smoke tests.
11. Verify HTTPS and cookie behavior.
12. Verify backup creation and a restore rehearsal in an isolated database/container.
13. Record exact deployed commit, image, migration revision, timestamp, and commands.
14. Provide rollback instructions.

Do not say “deployed” unless the public HTTPS endpoint was actually reached and the core smoke tests passed.

Do not include passwords or tokens in `DEPLOYMENT_RECORD.md`.

---

# 19. Production Pilot and Live-Source Validation

After deployment, do not immediately generate hundreds of records.

Run a controlled pilot:

```text
Registry: maximum 20 companies
DECP: maximum 15 companies, approximately 90 days
Contact automation: disabled
Nightly scheduling: disabled
```

For every generated prospect, capture:

- source;
- company identity;
- sector/NAF;
- size;
- trigger;
- pain evidence or missing pain;
- likely buyer role;
- contact path and confidence;
- score breakdown;
- readiness failures;
- manual review outcome.

Create `LIVE_SOURCE_VALIDATION.md` and a CSV export with no unnecessary personal data.

Measure:

```text
structural relevance rate
worth-researching rate
genuine pain-evidence rate
buyer-identification rate
usable-contact rate
human-acceptance rate
false contact-ready rate
duplicate rate
source failure rate
```

Initial acceptance targets:

```text
At least 60% structurally relevant
At least 30% worth deeper research
Approximately 20–35% genuinely qualified after human review
Zero award-only prospects marked contact-ready
Zero guessed-only emails treated as verified
Zero suppressed records entering a send-ready state
No duplicate score inflation after rerunning ingestion
```

If these targets fail, tune the market play, source filters, and gates before increasing volume.

---

# 20. Operator and Client-Acquisition Workflow

Create `OPERATOR_LAUNCH_PLAYBOOK.md` and ensure the UI supports it.

The daily workflow should be:

1. Process replies and meetings first.
2. Process overdue follow-ups.
3. Review accepted prospects awaiting first touch.
4. Complete contact-verification tasks.
5. Research the highest-quality unreviewed prospects.
6. Generate new prospects only after due actions are complete.

For each prospect, the operator must verify:

- company fit;
- real pain or defensible pain hypothesis;
- current trigger;
- correct buyer role/person;
- valid contact path;
- matching offer and proof.

The product should help prepare a safe outreach brief containing:

```text
specific source-backed observation
plausible operational consequence, labeled as hypothesis when unconfirmed
relevant proof asset
narrow offer
low-friction CTA
claims that are safe to make
claims that must not be made
```

The system must not automatically send outreach during this production pilot.

Provide reusable but editable message drafts for:

- email;
- LinkedIn connection note;
- LinkedIn first message;
- follow-up one;
- follow-up two;
- reply to “not now”;
- meeting confirmation.

These drafts must be generated from actual prospect evidence. Do not invent specific pain or claim the prospect uses Excel, WhatsApp, paper, or a broken process unless the evidence supports it.

Before logging `Sent`, enforce:

- exact data source;
- first-contact disclosure/informed timestamp;
- no suppression;
- human acceptance;
- valid contact path;
- selected offer/proof;
- message reviewed by the operator.

The default pilot cadence should be conservative:

```text
Week 1: review 20–30, accept 8–15, contact 5–10
Week 2: review another 20–30, contact 8–15, complete every due follow-up
```

The system should measure:

- accepted prospects by source;
- messages sent;
- reply rate;
- positive reply rate;
- meeting rate;
- proposal rate;
- close rate;
- opt-out rate;
- bounce rate;
- performance by market play, pain signal, trigger, buyer role, channel, message variant, and proof asset.

Do not optimize scoring from tiny datasets. Show sample size and confidence warnings.

---

# 21. UX and Product Quality

Keep the interface minimalist, fast, and operational.

Requirements:

- clear visual hierarchy;
- no misleading precision;
- explicit evidence and missing-gate explanations;
- fast keyboard-friendly qualification;
- safe destructive-action confirmation;
- responsive layouts;
- accessible labels and focus states;
- useful empty and error states;
- loading indicators for ingestion and enrichment;
- no stale IT/cyber copy;
- no decorative dashboards that do not affect action.

Every “contact-ready” label must show why it is ready. Every blocked prospect must show the exact missing gates.

The queue should reduce operator decisions, not hide uncertainty.

---

# 22. Testing Requirements

All existing tests must pass, and new tests must cover the changed behavior.

Minimum validation:

## Unit tests

- score dimensions;
- pain/trigger separation;
- evidence expiration;
- source-origin counting;
- contact confidence combinations;
- readiness gates;
- action urgency;
- suppression;
- evidence fingerprints.

## API/router tests

- qualification enforcement;
- CSRF;
- login throttling;
- invalid enums;
- event logging prerequisites;
- task completion/rescheduling;
- suppression boundaries;
- ingestion run states.

## Migration tests

- fresh database;
- supported upgrade path;
- indexes and constraints;
- uniqueness and idempotency;
- failure behavior.

## Integration tests

- ingestion rerun does not duplicate;
- evidence changes recompute readiness;
- contact changes recompute readiness;
- qualification creates visible tasks;
- opt-out removes send-ready actions;
- first outreach creates follow-up state;
- task queue ordering.

## Browser smoke tests

- login/logout;
- queue;
- qualify;
- sourcing;
- prospect detail;
- follow-up;
- Kanban;
- common failure messages;
- mobile-width sanity.

## Quality gates

The final repository must satisfy:

```bash
pytest -q
ruff check .
python -m compileall app tests
docker compose config
```

When Docker is available:

```bash
docker compose build --pull app
docker compose up -d db app
health and readiness checks
browser smoke checks
```

Do not suppress meaningful lint or test failures simply to make the commands green.

---

# 23. Performance and Reliability

The pilot target is hundreds to low thousands of prospects, not internet scale.

Optimize for reliability and maintainability:

- appropriate database indexes;
- bounded list queries;
- pagination;
- no accidental N+1 behavior in queue pages;
- bounded ingestion memory;
- streaming or chunked processing for large datasets when practical;
- cache large public datasets;
- clear ingestion progress;
- safe job retries;
- app responsiveness while ingestion runs.

The current DECP data flow may involve a large dataset. Measure memory and runtime on the VPS during the first supervised run. Do not schedule it blindly.

Separate long-running ingestion from the web request lifecycle. For the pilot, a CLI-run ingestion job is acceptable. If a worker service is added, keep it simple and operationally observable.

---

# 24. Documentation Cleanup

Update all repository documentation to match the final implementation.

At minimum:

- `README.md`: accurate product, architecture, local start, current limitations.
- `DEPLOY.md`: preferred real-domain reverse-proxy deployment first; high-port self-signed mode only as an explicitly non-preferred fallback.
- `GUIDE.md`: remove obsolete IT/cyber content and describe the real Today queue.
- `.env.production.example`: safe defaults with all automation off.
- command help: field-service terminology.
- master specification: append implementation status or link to the gap matrix.

Do not leave documentation claiming a feature is active when it is only planned.

---

# 25. Commit and Delivery Discipline

Create coherent commits, for example:

```text
chore: establish verified project baseline
fix: enforce evidence-based readiness gates
refactor: consolidate commercial state projection
fix: make evidence ingestion idempotent
feat: connect tasks to the daily action queue
feat: add bounded website intelligence
fix: enforce suppression and contact audit rules
security: harden production session and proxy settings
test: add commercial and deployment regressions
docs: align V3 operator and deployment guides
```

Do not push unless authorized or the connected repository workflow clearly permits it.

At completion, provide:

1. Executive outcome.
2. Exact branch and commit range.
3. Files changed.
4. Tests and commands with results.
5. Migration status.
6. Docker status.
7. Deployment status.
8. Public URL and smoke-test result when deployed.
9. Live-source pilot results.
10. Remaining limitations.
11. Exact next operator actions for the first client-acquisition week.

---

# 26. Definition of Done

The task is not complete until all applicable items below are true or explicitly documented as blocked.

## Product and commercial correctness

- [ ] The active ICP is field-service/technical-operations SMEs, not IT vendors.
- [ ] Awards never create automatic pain.
- [ ] Pain, trigger, fit, authority, value, and data quality are separate.
- [ ] Human acceptance requires all six confirmations.
- [ ] Proof/offer match is real, not hard-coded.
- [ ] Guessed emails are never represented as verified.
- [ ] Contact-ready status is defensible and explainable.
- [ ] V2 scoring cannot overwrite V3 state.

## Data integrity

- [ ] Normalized evidence is authoritative.
- [ ] Evidence ingestion is idempotent.
- [ ] Independent sources are counted correctly.
- [ ] Suppression is global and enforced.
- [ ] Reingestion cannot duplicate prospects, contacts, tasks, or evidence.
- [ ] Every claim has source provenance.

## Operator workflow

- [ ] `/queue` is a real Today queue combining replies, meetings, follow-ups, first touches, research, and qualification.
- [ ] Qualification-created tasks are visible.
- [ ] Missing gates are explicit.
- [ ] First-message briefs use actual evidence and safe claims.
- [ ] Sent, reply, meeting, proposal, close, refusal, and opt-out are traceable.

## Security and deployment

- [ ] Tests and lint pass.
- [ ] Migrations pass from fresh and supported previous states.
- [ ] Migration failures stop startup.
- [ ] Docker build and startup pass when Docker is available.
- [ ] Production uses real HTTPS on `prospects.elevya.tech`.
- [ ] App and database are not unnecessarily public.
- [ ] CSRF, login throttling, secure cookies, trusted hosts, proxy trust, and security headers are verified.
- [ ] Backups work and an isolated restore rehearsal succeeds.
- [ ] Nightly ingestion and contact automation remain disabled.

## Commercial pilot

- [ ] A supervised 20-company registry run is completed.
- [ ] A supervised 15-company DECP run is completed when access allows.
- [ ] Results are manually audited.
- [ ] No award-only false contact-ready prospects exist.
- [ ] Precision metrics are recorded.
- [ ] Operator playbook is complete.
- [ ] The system is ready for 5–10 careful first contacts, not mass outreach.

---

# 27. Final Behavior Instructions

Be rigorous and skeptical.

Do not:

- invent credentials;
- invent client proof;
- claim a deployment succeeded without testing it;
- hide failed tests;
- create fake contacts or prospects;
- treat numeric score as proof of buyer intent;
- automate unauthorized LinkedIn activity;
- enable nightly ingestion prematurely;
- expose the database;
- weaken security to make deployment easier;
- rewrite unrelated VPS services;
- stop after writing an audit.

Do:

- inspect deeply;
- trace behavior end to end;
- make reversible changes;
- preserve backups;
- implement the highest-value missing work;
- test adversarial edge cases;
- use browser verification;
- show evidence artifacts;
- distinguish verified facts from hypotheses;
- optimize for a small number of genuinely qualified prospects;
- leave the system deployable, understandable, and operable by one person.

Begin now with Phase 0 and Phase 1. Continue through implementation and validation without waiting for approval on routine reversible changes. Pause only when an external credential, irreversible production action, or explicit business fact is genuinely required.
