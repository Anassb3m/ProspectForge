# ANTIGRAVITY MASTER CONTINUATION PROMPT
## Complete ProspectForge after the Codex reliability phase

You are operating directly inside the existing **ProspectForge** repository.

This is a continuation of a completed Codex reliability phase. You are **not** starting from an old version, a blank architecture, or the original broken system. The repository already contains substantial reliability repairs. Your job is to inspect that exact implemented state, preserve the correct work, complete the remaining architecture, verify it under realistic conditions, and leave ProspectForge as a dependable acquisition intelligence engine for a real solo software business.

Assume that you will misunderstand, omit, or accidentally weaken anything that is not stated explicitly. Therefore:

- read this document completely before editing;
- inspect the repository and handoff files before forming conclusions;
- do not infer that a component is complete merely because a class, route, model, button, or feature flag exists;
- do not produce only a plan;
- do not stop after analysis;
- do not claim completion from mocked counts, synthetic fixtures, screenshots, or a green landing page;
- do not replace working reliability controls with simpler but weaker code;
- do not perform an unbounded rewrite;
- do not delete production data;
- do not activate automatic outreach.

The required result is an operational system that can continuously discover a large raw company universe, normalize it safely, enrich records in durable stages, score and gate companies for the actual market, research appropriate professional contacts, expose truthful operational controls, and produce a smaller human-reviewed queue that can support client acquisition.

---

# 1. Files you must read before changing code

Read these files in full, in this order:

1. `CURRENT_STATE.md`
2. `NEXT_ACTIONS.md`
3. `TEST_LOG.md`
4. `DECISION_LOG.md`
5. `CODEX_HANDOFF.md`
6. `README.md`
7. `DEPLOY.md`
8. `GUIDE.md`
9. `acceptance/baseline-defect-register.md`
10. Every file under `docs/reliability/`
11. `CODEX_PROSPECTFORGE_ELITE_RELIABILITY_REBUILD_PROMPT.md`
12. `PROSPECTFORGE_RELIABILITY_AND_SCALE_AUDIT.md`
13. `ELEVYA_SOLO_SOFTWARE_BUSINESS_OPERATING_MANUAL.md`
14. All Alembic revisions, especially `20260728_01_reliability_run_truth.py`
15. The current models, services, workers, sources, routers, templates, scripts, Docker configuration, and tests.

Also inspect:

```bash
git status --short
git diff --stat
git log --oneline --decorate -20
find . -maxdepth 3 -type f | sort
docker compose config
```

Do not overwrite unrelated uncommitted work. The previous phase explicitly preserved pre-existing user changes in:

- `app/templates/dashboard.html`
- `scripts/deploy.sh`

Confirm their current state before editing them.

---

# 2. Business context that must control technical decisions

ProspectForge supports a one-person software business operated by Anass Benameur.

The initial direct market is:

```text
Country: France
Primary vertical: commercial HVAC, refrigeration, maintenance, and adjacent field-service companies
Approximate company size: 20–150 employees
Core operational wedge:
intervention completion
→ technician report
→ parts/documents
→ administrative validation
→ invoice-ready information
```

The engine is not intended to send indiscriminate mass outreach. It should produce a controlled funnel:

```text
large raw source universe
→ normalized legal companies
→ ICP-eligible companies
→ identity/domain evidence
→ operational evidence and timing triggers
→ explainable score
→ hard readiness gates
→ buyer/contact dossier
→ human review
→ small approved outreach queue
```

The business needs volume at the top of the funnel and precision at the bottom.

A sensible initial operating shape is:

| Stage | Initial daily operating range |
|---|---:|
| Raw source records | 500–2,000 |
| Unique normalized companies | 200–800 |
| ICP-eligible companies | 75–300 |
| Identity/evidence enrichment attempts | 100–300 |
| Contact-dossier attempts | 20–75 |
| Human-approved contact-ready prospects | 5–25 |

These numbers are goals for capacity planning, not permission to fabricate benchmark results. Measure real live-source performance and report source-imposed limitations honestly.

---

# 3. What the Codex phase already completed

Treat the following as implemented but verify it against code and tests.

## 3.1 Runtime truth and request integrity

The current system reportedly has:

- immutable pre-enqueue ingestion requests;
- propagated play, mode, limits, and source flags;
- explicit France play selection;
- rejection of unsupported UK ingestion;
- durable canonical `PipelineRun` records;
- correlation IDs, revisions, heartbeat/checkpoint fields, committed stage counters, and categorized errors;
- truthful failed runs that re-raise exceptions rather than returning success-shaped errors.

Do not regress these behaviors.

## 3.2 Transaction and failure isolation

The current system reportedly has:

- per-record savepoints;
- a durable failed-work record;
- successful rows preserved when another record fails;
- bounded enrichment retries with exponential backoff;
- pending work retained when broker dispatch fails;
- unique idempotency keys for work items.

Do not return to one transaction around a network-heavy batch.

## 3.3 Progressive registry discovery and run locks

The current system reportedly has:

- durable partition-and-row registry cursors;
- no-overlap checkpoint resume;
- PostgreSQL advisory locks;
- conflict handling between full and registry runs;
- safe release of partially acquired locks.

Preserve ordered lock acquisition and checkpoint semantics.

## 3.4 Identity and run-ledger repair

The current system reportedly has:

- explicit `Prospect.company_id`;
- explicit `Prospect.opportunity_id`;
- identifier-first backfill using SIRET, then SIREN;
- no company-name backfill joins;
- legacy ingestion runs backfilled into `PipelineRun`;
- handling for the UUID/integer compatibility problem.

This is an intermediate compatibility state, not the final canonical model.

## 3.5 Scheduler and operations truth

The current system reportedly has:

- feature-flag-generated Beat schedules;
- scheduler and nightly tasks disabled by default;
- source health states that distinguish planned, unavailable, misconfigured, degraded, and healthy;
- authenticated operations visibility;
- metrics based on persisted data instead of fixed zeros;
- diagnostic, release-gate, reconciliation, backup, deployment, rollback, and restoration scripts.

Do not activate schedules merely because tests pass.

## 3.6 Verification already reported

The previous phase reported:

- 130 PostgreSQL/Redis tests passing;
- a complete release gate passing;
- migration upgrade/downgrade/re-upgrade rehearsal;
- failure isolation with 2 successful rows and 1 durable failure;
- checkpoint resume without overlap;
- enrichment replay retaining one idempotent item;
- run-overlap rejection.

Re-run relevant checks before extending the system. Do not assume those results still hold after your changes.

---

# 4. Current automation state

The system must begin this continuation with:

```text
Manual bounded ingestion: enabled
Durable enrichment dispatch after manual ingestion: enabled
Scheduler: disabled
Nightly ingestion: disabled
Nightly scoring: disabled
Automatic contact discovery: disabled
Retention automation: disabled
Automatic cold outreach: unsupported and disabled
```

You may activate a stage only after the stage-specific exit gate in this document passes.

Automatic sending of cold email or LinkedIn messages remains outside scope and must stay disabled.

---

# 5. Confirmed remaining gaps

The previous implementation report left these known gaps:

## P0

1. Python 3.12 release certification is unfinished.
2. Migration and reconciliation against an anonymized production copy are unfinished.
3. `Prospect` still duplicates mutable canonical fields.
4. The compatibility model is not yet a read-only projection.
5. DECP lacks immutable raw-source records.
6. DECP lacks a durable progressive high-water checkpoint.

## P1

7. V4 scoring is incomplete.
8. Automated scoring and contact readiness remain disabled.
9. There is no canonical worker heartbeat model and stale-worker control.
10. There is no authenticated failed-work retry endpoint.
11. Live-source quality, latency, freshness, and sustained throughput have not been measured.
12. Buyer/contact readiness is not proven end to end.
13. Domain and evidence quality still require production-grade resolution rules.
14. The full human review experience is not yet demonstrated.

## P2

15. BODACC is intentionally disabled or planned.
16. OCDS is intentionally disabled or planned.
17. Companies House is intentionally disabled for the France play.
18. Additional sources have not passed source-contract and live acceptance gates.

There may be additional gaps. Find them, but do not ignore these listed gaps.

---

# 6. Non-negotiable invariants

The following rules are binding.

## Data identity

- A company name is not a stable identity key.
- A guessed domain is not a stable identity key.
- An email address is not proof of legal-company identity.
- Prefer official SIRET/SIREN identifiers for France.
- Preserve source provenance for every identifier.
- Never merge companies solely because normalized names look similar.
- Never split one legal company into multiple canonical companies solely because source formatting differs.
- Ambiguous identity must remain unresolved and visible.

## Raw evidence

- A raw source response must be persisted immutably before downstream transformation when the source supports durable retrieval.
- Raw payloads require source, external record ID, retrieval time, payload hash, source-run reference, schema/version, and provenance.
- Transformation may create new versions; it must not mutate historical raw evidence.
- Duplicate retrieval must be idempotent.

## Checkpoints

- A checkpoint represents only durably committed progress.
- Never advance a checkpoint before raw records and required run counters commit.
- Checkpoints must be partition-specific.
- Checkpoint comparison must be deterministic.
- Recovery must not skip unseen records.
- Controlled overlap/lookback is allowed when source ordering can change, provided deduplication is durable.

## Work execution

- Every durable stage requires an idempotency key.
- A retry may repeat work but must not create duplicate business entities or duplicate evidence.
- Retryable and terminal failures must be distinguished.
- One failed record must not invalidate unrelated committed records.
- No infinite retry loops.
- No unbounded network calls.
- No network operation inside a long database transaction.

## Scoring and readiness

- Score ranks records; hard gates decide eligibility.
- A high score must never bypass missing identity, missing evidence, suppression, contradiction, or human approval.
- Every score must be explainable.
- Score versions and input versions must be persisted.
- Readiness state changes require an audit record.
- Outreach-ready is not equivalent to “has an email.”

## Human control and compliance

- No automatic cold outreach.
- No automatic LinkedIn actions.
- Suppression must always win.
- Professional relevance must be documented.
- Contact provenance must be visible.
- Reacher/SMTP results may describe mailbox behavior but must not be treated as identity proof.
- A human must approve a dossier before it enters the final contact-ready queue.

## Truthful operations

- No fixed or fabricated counts.
- No “healthy” state for a placeholder.
- No “completed” run with hidden record failures unless the run state and counters explain partial completion.
- Every loss between funnel stages must be explainable by a decision, gate, duplicate, error, or pending state.
- Every operator action must be auditable.

---

# 7. Priority order

Whenever tradeoffs occur, use this order:

```text
production data safety
→ preservation of completed reliability work
→ truthful observability
→ immutable raw evidence and checkpoints
→ canonical identity
→ idempotent stage recovery
→ real scoring and gates
→ contact-dossier quality
→ measured live throughput
→ controlled automation
→ UI polish
→ optional source expansion
```

Do not prioritize visual redesign over missing data integrity or pipeline correctness.

---

# 8. Mandatory execution program

Complete the following phases in order unless repository evidence proves that a phase is already fully implemented. If you believe a phase is complete, prove it using code references, tests, and actual command results.

---

## PHASE 0 — Baseline and continuation verification

### Objective

Establish the exact current repository, runtime, migration, and test state before modifying it.

### Required work

1. Read all handoff and reliability documents.
2. Inspect Git status and preserve unrelated edits.
3. Identify the current Python runtime.
4. Inspect dependency declarations and lock files.
5. Inspect PostgreSQL and Redis test setup.
6. Inspect current Alembic head and migration graph.
7. Trace:
   - manual ingestion request;
   - immutable run request creation;
   - worker dispatch;
   - registry discovery;
   - checkpoint commit;
   - enrichment work creation;
   - retry handling;
   - source health;
   - operations API and UI.
8. Build a matrix mapping each reported completed behavior to:
   - implementation file;
   - model/table;
   - test;
   - diagnostic output.
9. Re-run the existing release gate without changing code.
10. Record any divergence between the handoff report and the current repository.

### Commands

Use the repository-supported commands. At minimum run equivalents of:

```bash
python3.12 --version
git status --short
git diff --check
docker compose config
PYTHON_BIN=.venv/bin/python bash scripts/release-gate.sh
```

If `.venv` is not Python 3.12, do not silently reuse it for certification. Create or configure a 3.12 environment according to project conventions.

### Deliverables

- `docs/continuation/baseline-verification.md`
- updated `TEST_LOG.md`
- updated defect register
- a phase matrix identifying complete, partial, absent, and contradictory features.

### Exit gate

- current repository state is documented;
- previous reliability tests still pass;
- no unrelated user edits were overwritten;
- Python 3.12 certification path is explicit.

---

## PHASE 1 — Python 3.12 release certification and anonymized production-copy rehearsal

### Objective

Prove that the repaired foundation can be migrated, reconciled, tested, and rolled back against data shaped like production.

### Required work

#### 1. Python 3.12 certification

- Create or rebuild a deterministic Python 3.12 environment.
- Install dependencies from the repository’s authoritative dependency definition.
- Do not rely on undeclared globally installed packages.
- Run:
  - Ruff or the configured linter;
  - compile checks;
  - complete PostgreSQL/Redis test suite;
  - migration tests;
  - release gate;
  - shell validation;
  - Compose validation;
  - frontend asset verification.
- Update documentation to state the supported production Python version.
- Add a release-gate failure if production uses a materially unsupported Python version.

#### 2. Anonymized production-copy process

Create a safe documented procedure and script where appropriate to:

1. take a verified production database backup;
2. restore it into an isolated rehearsal database;
3. remove or irreversibly anonymize:
   - personal names where not required for structure tests;
   - emails;
   - phone numbers;
   - free-text notes;
   - message content;
   - tokens/secrets;
   - client-specific confidential values;
4. preserve:
   - row counts;
   - key distributions;
   - source/run relationships;
   - identifier collision patterns;
   - checkpoint structure;
   - failure-state structure;
   - realistic data volume;
5. run Alembic upgrade;
6. run `scripts/reconcile_reliability.py --fail-on-anomaly`;
7. run integrity queries;
8. run application smoke tests;
9. test downgrade only in an isolated copy;
10. re-upgrade;
11. test backup restoration.

Do not copy live secrets into the rehearsal environment.

#### 3. Required reconciliation assertions

At minimum report:

- duplicate SIREN/SIRET identifiers;
- identifiers attached to multiple canonical companies;
- unresolved identifier-bearing `Prospect` rows;
- orphan opportunities;
- orphan evidence;
- legacy runs not represented in `PipelineRun`;
- counter mismatches;
- work items without runs;
- failures without source/work references;
- checkpoints without matching source partitions;
- compatibility rows with conflicting mutable values.

### Deliverables

- `scripts/create-anonymized-rehearsal-db.sh` or a documented equivalent;
- `scripts/verify-production-shaped-migration.py`;
- `docs/continuation/production-copy-rehearsal.md`;
- exact rehearsal results in `TEST_LOG.md`;
- an activation decision: approved or blocked.

### Exit gate

Do not continue to scheduler activation. This phase passes only when:

- Python 3.12 complete suite passes;
- production-shaped migration passes;
- reconciliation finds no unexplained P0 anomalies;
- backup restoration is demonstrated;
- rollback limitations are documented.

---

## PHASE 2 — Immutable raw-source ledger and progressive DECP ingestion

### Objective

Make DECP discovery durable, replayable, progressive, and independent from downstream enrichment.

The prior report truthfully stated that `raw_persisted` remained zero. Fix that.

### 2.1 Canonical source contract

Inspect the existing source abstraction and define one canonical contract. It should expose concepts equivalent to:

```python
class SourceAdapter(Protocol):
    source_code: str
    schema_version: str

    async def validate_configuration(self) -> SourceHealth: ...
    async def iter_records(
        self,
        *,
        play_code: str,
        partition: SourcePartition,
        checkpoint: SourceCheckpoint | None,
        budget: SourceBudget,
    ) -> AsyncIterator[SourceEnvelope]: ...
```

A `SourceEnvelope` must include:

- source code;
- source external record ID;
- stable ordering key;
- partition key;
- retrieved timestamp;
- source-updated timestamp when available;
- raw payload;
- payload hash;
- request metadata;
- next checkpoint candidate;
- source schema version.

Do not force every source into a field it cannot truthfully provide. Represent optional values explicitly.

### 2.2 Immutable raw record model

Implement or complete a canonical immutable raw-record table.

Required fields should include equivalents of:

```text
id
source_code
external_record_id
partition_key
source_run_id
retrieved_at
source_updated_at
schema_version
payload_json or protected raw payload reference
payload_hash
request_fingerprint
ordering_key
is_tombstone when applicable
created_at
```

Required uniqueness/idempotency rule:

```text
source_code
+ external_record_id
+ payload_hash
```

or an equally safe source-specific immutable key.

If the source returns the same record unchanged, do not create unnecessary duplicate raw rows. If the source record changes, preserve a new immutable version.

### 2.3 DECP high-water checkpoint

Implement a progressive checkpoint based on the most stable source ordering available after inspecting the actual DECP response and current adapter.

Use a compound high-water mark, such as:

```text
source_updated_at/event_date
+ stable external record ID tie-breaker
```

Do not use timestamp alone when multiple records can share a timestamp.

Required behavior:

1. Read the committed checkpoint for the DECP partition.
2. Query records after the high-water mark.
3. Use a small configurable lookback window when source updates can arrive late.
4. Persist raw records idempotently.
5. Commit run counters and raw records.
6. Advance the checkpoint only after the durable commit.
7. On retry, re-read and deduplicate overlap.
8. Never skip records because one item failed normalization.

### 2.4 DECP partitioning

Partition by a stable market-relevant dimension where necessary, such as:

- date window;
- CPV/category set;
- geographic market;
- buyer/award update window.

Do not create hundreds of uncontrolled partitions. Persist partition configuration and rotate fairly.

### 2.5 Source budget and resilience

Add source-specific configuration for:

- records per request;
- requests per minute;
- maximum records per run;
- connect timeout;
- read timeout;
- overall task timeout;
- retryable HTTP statuses;
- maximum retries;
- backoff;
- circuit-breaker/degraded threshold;
- lookback window.

Respect explicit source limits and provider terms.

### 2.6 Stage separation

DECP discovery must do only:

```text
fetch
→ persist immutable raw record
→ update source-run counters
→ enqueue normalization work
→ commit checkpoint
```

It must not perform:

- website crawling;
- deep enrichment;
- contact discovery;
- email verification;
- score calculation;
- outreach.

### 2.7 Replay and recovery

Provide operator actions or scripts to:

- replay normalization from raw records;
- rebuild canonical entities from a selected raw-source window;
- inspect checkpoint history;
- pause a source;
- resume a source;
- rewind a checkpoint safely with explicit confirmation and audit;
- reprocess terminal failures after code repair.

### Tests

Add:

- DECP source-contract test with recorded sanitized fixtures;
- same-page replay test;
- same-timestamp tie-breaker test;
- changed-payload version test;
- late-arrival lookback test;
- failure-before-commit checkpoint test;
- failure-after-raw-commit normalization test;
- retry without duplicate raw rows;
- partition fairness test;
- source-budget test;
- source-health degradation test.

### Deliverables

- model/migration changes;
- completed DECP adapter;
- checkpoint implementation;
- replay commands;
- source-specific runbook;
- operations visibility for raw records and checkpoints.

### Exit gate

- controlled DECP run persists immutable raw rows;
- rerunning the same window creates no duplicate unchanged rows;
- changed source payload creates a traceable version;
- checkpoint resumes without gaps;
- normalization failure does not block checkpoint-safe raw persistence;
- source metrics are visible;
- `raw_persisted` is based on actual committed raw rows.

---

## PHASE 3 — Canonical data model consolidation

### Objective

End the remaining mutable dual truth.

The target canonical model is:

```text
Company
CompanyIdentifier
CompanyDomain
Opportunity
EvidenceItem
Person
ContactPoint
ScoreSnapshot
SourceRecord
PipelineRun
WorkItem
FailedWorkItem
SuppressionEntry
ReviewDecision
```

`Prospect` may temporarily remain for compatibility, but it must become a read-only projection or be removed from active business logic.

### 3.1 Inventory every read and write

Use repository search to map every location that:

- creates `Prospect`;
- updates `Prospect`;
- queries `Prospect`;
- copies fields between `Prospect` and `Company`;
- joins by name;
- joins by inferred domain;
- reconstructs opportunity links;
- writes duplicate score/contact/readiness fields.

Create:

`docs/continuation/canonical-model-cutover-map.md`

For each path, identify:

- current source of truth;
- target source of truth;
- compatibility requirement;
- migration order;
- test coverage.

### 3.2 Canonical ownership rules

Define one owner for every mutable field.

Example:

| Data | Canonical owner |
|---|---|
| Legal identity | `Company` + `CompanyIdentifier` |
| Official domain | `CompanyDomain` |
| Market-play candidacy | `Opportunity` |
| Evidence | `EvidenceItem` |
| Score | immutable `ScoreSnapshot` |
| Current readiness | `Opportunity` or dedicated state record |
| Contact identity | `Person` |
| Contact channel | `ContactPoint` |
| Suppression | `SuppressionEntry` |
| Human decision | `ReviewDecision` |

Do not let `Prospect` independently own mutable copies.

### 3.3 Compatibility projection

Choose one controlled compatibility method:

1. database view;
2. query/service projection;
3. generated read model refreshed transactionally.

The projection must be read-only from application code.

Any old route that still renders a `Prospect`-shaped object must read from the canonical model through the projection.

### 3.4 Migration sequence

Use expand-and-contract migration:

#### Expand

- add canonical fields/constraints/indexes;
- add missing relationships;
- create projection;
- add reconciliation tooling;
- keep old readers functional.

#### Backfill

- resolve by official identifiers;
- link only unambiguous records;
- create anomaly records for ambiguous cases;
- never use name-only matching;
- preserve all historical rows.

#### Cut over writes

- update every writer to canonical models;
- prohibit legacy mutable writes;
- add tests or database protections.

#### Cut over reads

- update API, UI, workers, scoring, queue, and exports;
- compare old/new output during a verification window.

#### Contract

Only after verified production operation:

- remove duplicate mutable columns or make them generated/read-only;
- remove unused write paths;
- keep migration rollback strategy explicit.

### 3.5 Canonical identity conflict handling

Implement visible states such as:

```text
RESOLVED
AMBIGUOUS
CONFLICTING_IDENTIFIERS
MISSING_OFFICIAL_IDENTIFIER
MERGE_REVIEW_REQUIRED
SPLIT_REVIEW_REQUIRED
```

Do not silently choose one company when evidence conflicts.

### Tests

- same display name, different SIREN;
- same SIREN, formatting variants;
- SIRET establishment linked to SIREN legal entity;
- duplicate source records;
- conflicting domains;
- opportunity for multiple market plays;
- projection equivalence;
- legacy write rejection;
- migration/backfill idempotency;
- downgrade/restore rehearsal;
- no name-only join detection test.

### Exit gate

- no active business workflow writes mutable legacy fields;
- canonical entities serve all API/UI/worker reads;
- compatibility projection is read-only;
- reconciliation reports zero unexplained duplicate ownership;
- same-name collision tests pass;
- production-shaped backfill passes.

---

## PHASE 4 — Worker heartbeat, queue health, and failure recovery control

### Objective

Make worker availability and failed-work recovery operable from the authenticated control center.

### 4.1 Canonical worker heartbeat

Implement a durable heartbeat model or an equally reliable mechanism.

Required dimensions:

```text
worker identity
worker type/queue
software version or build ID
started_at
last_seen_at
current task ID when safe
current run ID
host/container identity
concurrency
status
last error summary
```

Do not store secrets or unbounded stack traces.

Define states such as:

```text
ONLINE
DEGRADED
STALE
OFFLINE
UNKNOWN
```

Staleness thresholds must be configuration-driven and queue-specific.

### 4.2 Queue-health metrics

Expose:

- queued;
- claimed;
- running;
- retry scheduled;
- succeeded;
- terminal failed;
- oldest queued age;
- oldest running age;
- stale claims;
- per-stage throughput;
- per-stage p50/p95 duration;
- worker availability;
- retry counts;
- dead-letter counts.

Metrics must derive from persisted state and broker inspection where reliable.

### 4.3 Failed-work retry API

Create authenticated operator controls.

Requirements:

- authentication required;
- authorization role required;
- CSRF protection for browser actions;
- retry only failed items marked retryable unless an explicit privileged override exists;
- require a reason for privileged override;
- preserve original failure;
- create an audit event;
- create or reuse an idempotent retry work item;
- prevent double-click duplicate retry;
- show retry chain;
- support single-item retry;
- support filtered bounded bulk retry;
- enforce maximum bulk size;
- allow terminal close/acknowledge with reason;
- never delete failure history.

### 4.4 Lease and stale-task recovery

If the work model uses claims/leases:

- define lease expiry;
- renew while executing;
- detect abandoned tasks;
- return safe retryable tasks to pending;
- avoid concurrent duplicate execution;
- audit recovery.

### 4.5 Operations UI

Add:

- worker status panel;
- queue status panel;
- failed-work filters;
- error category;
- source/stage/run links;
- retry eligibility;
- retry history;
- bounded bulk action;
- stale-task recovery visibility.

### Tests

- heartbeat update;
- stale worker detection;
- multiple worker identities;
- retryable retry;
- terminal failure blocked;
- privileged override audited;
- duplicate retry prevented;
- stale lease recovery;
- unauthorized access rejected;
- CSRF protection;
- bounded bulk retry;
- broker outage does not create false success.

### Exit gate

An authenticated operator can see whether every required worker is alive, identify blocked queues, inspect a failure, retry it safely, and trace the complete retry chain.

---

## PHASE 5 — Real V4 scoring and hard readiness gates

### Objective

Replace placeholder scoring with a real, versioned, explainable market-play model for `FIELD_OPERATIONS_FR_V2`.

Do not activate automated contact discovery until this phase and its quality validation pass.

### 5.1 Separate ranking from eligibility

Implement:

```text
score: 0–100
gates: pass/fail/unknown
readiness state: explicit state machine
```

A score does not override a failed or unknown hard gate.

### 5.2 Initial score model

Implement a configuration-driven scoring specification. Use the business manual as the starting model.

#### A. ICP fit — 25 points

Possible factors:

- correct France market;
- relevant NAF/APE or verified service activity;
- approximate employee/company-size fit;
- recurring field-service activity;
- maintenance, installation, repair, inspection, or intervention workflow;
- evidence that the company is an operating company rather than an irrelevant holding entity.

#### B. Operational complexity — 20 points

Possible factors:

- multiple establishments or service territories;
- technician or field-role recruitment;
- multiple service categories;
- recurring contracts;
- parts/equipment/document requirements;
- customer portal, job form, PDF workflow, or several systems;
- branch or coordination complexity.

#### C. Trigger and timing — 15 points

Possible factors:

- current hiring;
- new branch;
- acquisition;
- public contract award;
- management change;
- explicit digital/system initiative;
- recent growth or service expansion.

#### D. Buyer and contact quality — 20 points

Possible factors:

- correct buyer role identified;
- named person relationship verified;
- public professional contact path;
- secondary route;
- source provenance;
- freshness;
- no contradiction.

Do not award these points before contact evidence actually exists.

#### E. Evidence quality — 20 points

Possible factors:

- legal identity verified;
- official domain verified;
- Grade A evidence;
- at least two facts supporting the operational hypothesis;
- current evidence;
- no unresolved contradiction.

### 5.3 Evidence grades

Support grades equivalent to:

```text
A — primary and current
B — reliable secondary
C — weak lead
D — unsupported
```

Persist grade and rationale for each evidence item.

### 5.4 Hard gates

Required gates before `CONTACT_REVIEW_READY` should include:

1. active legal entity;
2. official identifier verified;
3. France market play;
4. field-service relevance supported;
5. company size not clearly outside the configured target;
6. official or strongly evidenced domain;
7. no unresolved identity contradiction;
8. operational hypothesis supported by at least two relevant facts;
9. buyer role appropriate to the workflow;
10. named person verified when a named contact is proposed;
11. professional contact source recorded;
12. contact freshness within policy;
13. suppression check passed;
14. legal/professional relevance check passed;
15. no source or compliance block;
16. score based on current scoring version;
17. human review not yet rejected.

Required gates before `CONTACT_READY`:

- all applicable previous gates pass;
- human reviewer explicitly approves;
- message angle and evidence are visible;
- no unresolved stale information;
- no company/person suppression;
- no duplicate active outreach record.

### 5.5 Readiness state machine

Implement explicit transitions such as:

```text
DISCOVERED
NORMALIZED
ICP_REJECTED
ICP_ELIGIBLE
IDENTITY_PENDING
IDENTITY_BLOCKED
EVIDENCE_PENDING
SCORED
CONTACT_RESEARCH_ELIGIBLE
CONTACT_RESEARCH_PENDING
CONTACT_REVIEW_READY
CONTACT_READY
REJECTED
SUPPRESSED
STALE
ERROR
```

Define allowed transitions in one service. Do not scatter state assignment across routers and workers.

Persist:

- previous state;
- new state;
- reason code;
- actor/system;
- run/work item;
- timestamp;
- scoring/gate version.

### 5.6 Score snapshots

Every calculation must persist an immutable snapshot with:

- score version;
- play version;
- total;
- dimension totals;
- factor values;
- source evidence IDs;
- gate results;
- missing inputs;
- contradictions;
- calculation timestamp;
- triggering event.

Do not overwrite historical score explanations.

### 5.7 Recalculation triggers

Recalculate when:

- relevant company data changes;
- identifier/domain resolution changes;
- evidence is added/expired/retracted;
- person/contact data changes;
- suppression changes;
- play/scoring version changes;
- manual review corrects evidence;
- source freshness policy marks data stale.

Use idempotent work items.

### 5.8 Calibration interface

Add an operator-readable scoring specification page or documentation showing:

- current version;
- factors and weights;
- hard gates;
- sample calculations;
- distribution;
- recent changes;
- activation status.

### Tests

- exact factor calculations;
- missing evidence;
- contradictory evidence;
- high score with failed gate remains blocked;
- suppression overrides all;
- stale contact blocks readiness;
- scoring version change creates new snapshot;
- repeated recalculation is idempotent;
- state transitions enforce allowed paths;
- manual approval required;
- contact discovery remains disabled until gate activation.

### Exit gate

- placeholder constants are gone;
- every score is explainable;
- gates are independent;
- 50–100 manually reviewed companies are used to assess precision;
- false-positive and false-negative examples are documented;
- automatic contact research may be activated only after explicit operator approval;
- automatic outreach remains disabled.

---

## PHASE 6 — Identity, domain, and evidence quality engine

### Objective

Ensure that enrichment produces defensible evidence rather than confident guesses.

### 6.1 Official company identity

For France, prioritize:

1. SIRET/SIREN and official registry evidence;
2. official company-controlled legal notices;
3. consistent official domain/legal-entity association;
4. reliable secondary corroboration.

Persist source, retrieval date, and confidence.

### 6.2 Domain resolution hierarchy

Use a hierarchy equivalent to:

1. official registry-provided website when available and current;
2. company legal notice or official public document;
3. company-controlled social/profile link pointing to the domain;
4. verified official website with matching legal identity;
5. strong corroborated secondary evidence;
6. guessed domain candidate requiring review.

A guessed domain must not be marked official merely because:

- DNS resolves;
- TLS works;
- the homepage contains a similar name;
- an email pattern exists;
- SMTP accepts an address.

### 6.3 Domain states

Implement states such as:

```text
OFFICIAL_VERIFIED
STRONGLY_EVIDENCED
CANDIDATE
CONFLICTING
PARKED
UNREACHABLE
REDIRECTED_UNRESOLVED
REJECTED
```

Persist verification evidence and history.

### 6.4 Safe website evidence extraction

The website-fetching subsystem must have:

- SSRF protections;
- block private, loopback, link-local, metadata, and reserved networks;
- DNS rebinding protection where feasible;
- redirect limit;
- response-size limit;
- content-type validation;
- connect/read timeout;
- user-agent identification;
- rate budgets;
- robots/provider-policy consideration;
- HTML parsing safeguards;
- no script execution;
- no credential submission;
- no storage of unnecessary personal content;
- sanitized evidence extraction.

### 6.5 Evidence schema

Every evidence item should record:

```text
company/opportunity
evidence type
claim supported
source URL or source record
source category
grade
observed fact
retrieved_at
published/source_updated_at when known
expires_at or freshness policy
payload/text hash
extractor version
confidence
contradiction status
human review status
```

Separate:

- observed fact;
- inferred implication;
- unresolved question.

Do not store an inference as if it were a source fact.

### 6.6 Freshness and contradiction

Implement:

- evidence expiry policies by type;
- stale-state transitions;
- replacement/supersession;
- contradiction detection;
- operator review for conflicting identifiers/domains/roles;
- score recalculation when evidence changes.

### Tests

- SSRF cases;
- redirects;
- oversized response;
- invalid content type;
- official-domain evidence;
- conflicting legal notices;
- stale evidence;
- changed page content;
- observed fact vs inference separation;
- domain candidate does not pass official-domain gate.

### Exit gate

A reviewer can explain exactly why a domain, identity, service activity, branch, hiring trigger, or operational hypothesis is accepted, stale, weak, or blocked.

---

## PHASE 7 — Buyer and contact dossier engine

### Objective

Create accurate, provenance-rich professional contact dossiers only for eligible companies.

### 7.1 Eligibility

Contact research starts only when:

- identity is resolved;
- company is ICP-eligible;
- evidence gate passes;
- opportunity is not suppressed;
- score/gate version is current;
- contact research budget permits it.

### 7.2 Buyer-role mapping

For the initial operational wedge, use configurable role priorities.

Examples:

| Workflow | Likely primary role |
|---|---|
| Planning/dispatch | Operations or Service Director |
| Technician reports/documents | Service, Technical, Quality, or Operations Director |
| Invoice-preparation delay | Finance/Administration lead plus Operations |
| Integration/system ownership | IT/Digital lead plus operational owner |
| Small company-wide decision | Managing Director |

Do not treat a legal representative as the operational buyer without evidence.

### 7.3 Contact source preference

Use this preference order:

1. published named professional email;
2. published role-based email;
3. official contact form with relevant routing;
4. company switchboard/professional phone;
5. manually verified professional profile;
6. generic company email;
7. guessed email candidate requiring explicit review.

A guessed personal email is never automatically contact-ready.

### 7.4 Canonical person/contact model

`Person` should hold identity and company-role evidence.

`ContactPoint` should hold:

- channel type;
- normalized value;
- source/provenance;
- publication context;
- discovered_at;
- last_verified_at;
- verification type;
- confidence;
- status;
- professional relevance;
- suppression state;
- risk/contradiction;
- expiry.

Do not place multiple comma-separated contacts in one field.

### 7.5 Reacher constraints

If Reacher is used:

- it can record SMTP/network behavior;
- it cannot establish person identity;
- catch-all results must remain ambiguous;
- temporary errors must be retryable;
- negative SMTP results must not delete source evidence;
- results must have timestamps and expiry;
- it must not trigger outreach.

### 7.6 Suppression

Implement suppression at:

- exact contact point;
- person;
- company;
- domain when appropriate.

Suppression must:

- be checked before contact research approval;
- be checked before export;
- be checked before any outreach record;
- preserve the minimum data needed to respect the objection;
- be auditable;
- never be bypassed by a high score.

### 7.7 Human-review dossier

The review screen must show:

- legal company identity;
- official identifiers;
- official domain evidence;
- field-service fit;
- complexity facts;
- trigger facts;
- operational hypothesis;
- score and factor explanation;
- every hard gate;
- proposed buyer role;
- person-role evidence;
- contact provenance;
- verification and freshness;
- contradictions;
- suppression result;
- duplicate-contact warning;
- recommended message angle;
- approve, reject, request research, suppress, and mark stale actions.

Require a reviewer reason for rejection, override, or suppression.

### 7.8 Export control

Exports must:

- contain only explicitly approved records;
- record who exported;
- record when and which filter/version;
- re-check suppression;
- include provenance fields needed for responsible manual contact;
- never contain hidden unapproved guessed contacts.

### Tests

- legal representative not automatically buyer;
- published email preference;
- guessed candidate blocked;
- catch-all ambiguity;
- stale contact;
- person left company;
- duplicate person across sources;
- suppression propagation;
- export rechecks suppression;
- manual approval audit;
- no automatic outreach side effect.

### Exit gate

A controlled batch produces accurate reviewable dossiers, and the operator can distinguish verified, candidate, stale, contradictory, and suppressed contacts.

---

## PHASE 8 — Elite operations control center

### Objective

Turn the existing truthful operations page into a complete operator console after backend truth exists.

Do not rebuild the UI merely for appearance. Every screen must correspond to real persisted state and an operator decision.

### 8.1 Required views

#### Funnel overview

Show counts and conversion/loss reasons for:

```text
raw fetched
raw persisted
normalized
new companies
updated companies
duplicates
ICP eligible
ICP rejected
identity pending/blocked
evidence pending
scored
contact research eligible
contact review ready
contact ready
suppressed
failed
```

Allow date, source, play, run, and stage filters.

#### Source health

Per source show:

- activation state;
- configuration;
- credentials status without revealing secrets;
- last successful run;
- last failure;
- checkpoint;
- lag;
- records fetched/persisted;
- duplicate ratio;
- rate-limit events;
- error categories;
- circuit state;
- next scheduled run.

#### Run detail

Show:

- immutable request;
- source partitions;
- lock acquisition;
- checkpoints before/after;
- stage counters;
- duration;
- worker;
- errors;
- linked work;
- raw records;
- retry/replay actions;
- exact completion/partial/failure state.

#### Queue/worker health

Show Phase 4 metrics and stale workers/tasks.

#### Failure center

Show categorized durable failures with safe retry controls.

#### Record detail

Show source lineage:

```text
raw source record
→ normalized company
→ identifiers/domains
→ opportunity
→ evidence
→ score snapshots/gates
→ people/contact points
→ review decisions
```

#### Checkpoint control

Allow:

- inspect history;
- pause source/partition;
- resume;
- bounded replay;
- privileged checkpoint rewind with typed confirmation and audit.

### 8.2 UX requirements

- clear dense operational layout;
- fast filtering;
- useful empty states;
- no decorative fake charts;
- no hidden failure counts;
- accessible labels and keyboard operation;
- responsive enough for laptop use;
- UTC timestamps plus clear local rendering;
- source and state tooltips;
- explicit dangerous-action confirmation;
- no raw stack traces exposed to ordinary users;
- pagination for large tables;
- server-side filtering for large datasets.

### 8.3 Operator safety

Every action must state:

- what it will affect;
- maximum records;
- whether it is reversible;
- whether it enqueues work;
- whether it moves a checkpoint;
- whether it changes readiness;
- whether it creates external network traffic.

### Tests

- authenticated access;
- authorization;
- truthful counts;
- filters;
- pagination;
- empty states;
- action audit;
- dangerous confirmation;
- no hardcoded metrics;
- no secret exposure;
- consistency between API and persisted rows.

### Exit gate

An operator can understand the system’s current state, explain where records were lost or blocked, intervene safely, and verify the result without shell access for normal operations.

---

## PHASE 9 — Live-source benchmark and quality calibration

### Objective

Measure actual source behavior and determine safe operating limits.

Do not enable nightly schedules before this phase.

### 9.1 Controlled ramp

Run separate controlled batches:

```text
25 records
100 records
250 records
500 records
```

Increase only if the previous size passes its gates.

Do not combine source benchmarking with automatic contact discovery at first.

### 9.2 Required metrics

For each source and run measure:

- requested;
- fetched;
- raw persisted;
- unchanged duplicate raw records;
- changed raw versions;
- normalized;
- new companies;
- updated companies;
- duplicate companies;
- ICP eligible/rejected;
- source errors by category;
- retry counts;
- rate-limit events;
- checkpoint advancement;
- run duration;
- p50/p95 per-record stage duration;
- queue lag;
- memory/CPU;
- database growth;
- enrichment dispatch rate;
- terminal failures;
- unexplained losses.

### 9.3 Quality sampling

For each ramp, manually review a statistically useful sample.

At minimum classify:

- correct legal entity;
- active status;
- correct official identifier;
- correct domain;
- vertical fit;
- size plausibility;
- evidence accuracy;
- duplicate handling;
- operational hypothesis quality;
- contact-role accuracy where contact research is enabled.

Record false positives and false negatives.

### 9.4 Acceptance rules

A batch fails if:

- records disappear without an explainable state;
- checkpoint advances past uncommitted raw records;
- replay creates duplicate entities;
- source errors are hidden;
- a run remains indefinitely active;
- queue lag grows without bound;
- database constraints are bypassed;
- source terms/rate budgets are violated;
- quality precision is too low for the next stage;
- memory or database growth is uncontrolled.

### 9.5 Sustained test

After controlled batches, run a scheduler-disabled sustained test using explicit bounded commands over several cycles.

Prove:

- progressive movement across source space;
- no page-one plateau;
- stable duplicate rate;
- bounded retries;
- checkpoint recovery after worker restart;
- no overlap under concurrent trigger attempts;
- no stale locks;
- source lag decreases;
- daily raw capacity is measured.

Do not claim “hundreds per day” unless live evidence supports it. If a source cannot support the target, document the bottleneck and propose another compliant source or partition strategy.

### Deliverables

- `docs/benchmarks/live-source-benchmark.md`
- machine-readable benchmark output;
- quality sample CSV/JSON;
- recommended source budgets;
- safe scheduler limits;
- activation decision.

### Exit gate

At least one primary France source demonstrates progressive sustained acquisition with truthful counts, durable raw records, safe checkpoints, and acceptable data quality.

---

## PHASE 10 — Controlled scheduler and stage activation

### Objective

Activate automation gradually with independent feature flags and rollback controls.

### 10.1 Required independent flags

Support explicit flags equivalent to:

```text
ENABLE_SCHEDULER
ENABLE_REGISTRY_INGESTION
ENABLE_DECP_INGESTION
ENABLE_NORMALIZATION
ENABLE_IDENTITY_ENRICHMENT
ENABLE_EVIDENCE_ENRICHMENT
ENABLE_SCORING
ENABLE_CONTACT_RESEARCH
ENABLE_RETENTION
ENABLE_AUTOMATIC_OUTREACH=false
```

A global scheduler flag must not silently enable every stage.

### 10.2 Activation sequence

#### Stage A — Registry/DECP discovery only

- enable one source;
- conservative limit;
- observe several runs;
- verify checkpoint movement and source health.

#### Stage B — Normalization

- activate after raw backlog and deduplication are stable.

#### Stage C — Identity/evidence enrichment

- separate queues;
- conservative concurrency;
- source/site budgets;
- monitor failures and SSRF controls.

#### Stage D — Scoring

- activate after score calibration;
- no contact discovery yet.

#### Stage E — Contact research

- activate only for gate-passing records;
- bounded daily budget;
- no automatic approval.

#### Stage F — Retention/staleness

- activate after freshness policies are proven.

### 10.3 Scheduler requirements

- timezone explicit;
- no duplicate Beat instances;
- lock-protected tasks;
- jitter where useful;
- catch-up behavior defined;
- no unbounded backlog after downtime;
- missed-run policy;
- source-specific cadence;
- visible next-run time;
- pause/resume control;
- build/version visible.

### 10.4 Automatic outreach

Keep:

```text
ENABLE_AUTOMATIC_OUTREACH=false
```

Production validation must reject any configuration attempting to enable unsupported automatic cold outreach.

### Exit gate

Automated discovery and approved downstream stages run for a controlled observation window without overlap, silent failure, unexplained loss, or unsafe backlog.

---

## PHASE 11 — Optional source expansion

### Objective

Add sources only when they contribute a specific evidence type and pass the same durability contract.

Do not enable every placeholder.

### 11.1 BODACC

Use primarily for:

- legal/commercial events;
- ownership or proceeding signals;
- acquisition/transfer events;
- timing triggers.

Do not treat every BODACC item as a prospect.

Requirements:

- immutable raw records;
- progressive checkpoint;
- company identity resolution;
- event classification;
- trigger evidence;
- freshness;
- source-contract tests;
- feature flag;
- truthful health.

### 11.2 OCDS/other public procurement

Determine whether it adds unique data beyond DECP.

Avoid duplicate source noise. Use it only when it provides:

- additional procurement coverage;
- better award structure;
- missing identifiers;
- useful contract timing.

### 11.3 Companies House

Keep disabled for `FIELD_OPERATIONS_FR_V2`.

It may be activated only under a separate UK market play with:

- explicit play;
- UK company identity rules;
- UK source configuration;
- separate scoring;
- separate legal/commercial review.

Never let the UK adapter execute under the France play.

### 11.4 Source admission gate

No source becomes active until:

- adapter configuration validation passes;
- source contract tests pass;
- raw record persistence works;
- checkpoint/replay works;
- rate budget is documented;
- live bounded run passes;
- source value is measured;
- operations health is truthful;
- rollback/pause is available.

---

## PHASE 12 — Security, privacy, and production hardening

### Objective

Harden the now-expanded pipeline before broad operation.

### Required work

#### Authentication and authorization

- protect all operator routes;
- least-privilege roles;
- secure sessions;
- CSRF;
- rate limit sensitive actions;
- audit privileged actions.

#### Secrets

- no secrets in repository;
- no secrets in logs or operations UI;
- environment validation;
- secret rotation documentation;
- separate test and production credentials.

#### Network fetching

- SSRF controls from Phase 6;
- bounded DNS/HTTP behavior;
- egress visibility;
- safe redirects;
- content limits.

#### Data minimization

- collect only relevant professional data;
- define retention;
- define stale/contact deletion behavior;
- preserve suppression records;
- document exports;
- protect backups;
- redact logs.

#### Database

- constraints and indexes;
- least-privilege application role;
- statement/lock timeout policy;
- connection-pool limits;
- backup and restoration tests;
- database-growth monitoring.

#### Redis/Celery

- authentication/network isolation;
- result retention policy;
- visibility timeout/ack strategy;
- worker shutdown behavior;
- duplicate-execution safety;
- queue separation;
- concurrency limits.

#### Supply chain

- pinned dependencies;
- audit dependencies;
- frontend audit;
- reproducible assets;
- container image versioning;
- no floating production tags where avoidable.

#### Observability

- structured logs;
- correlation/run/work IDs;
- sensitive-field redaction;
- error aggregation;
- health vs readiness separation;
- alerts for stalled runs, stale workers, source degradation, checkpoint stagnation, queue age, and reconciliation anomalies.

### Exit gate

Security checks, release gate, backup/restore, and recovery drills pass with the expanded pipeline.

---

## PHASE 13 — Complete test and release proof

### Objective

Create executable proof that the finished system behaves correctly.

### Required test categories

#### Unit

- checkpoint comparison;
- source-envelope hashing;
- raw idempotency;
- identity resolution;
- domain states;
- evidence grading/freshness;
- score factors;
- gates;
- state transitions;
- retry classification;
- suppression.

#### Integration

- PostgreSQL migrations;
- raw-to-company pipeline;
- company-to-opportunity;
- evidence-to-score;
- score-to-contact eligibility;
- contact-to-review;
- worker heartbeat;
- failed-work retry;
- scheduler flags;
- projection read-only behavior;
- authenticated operations APIs.

#### Contract

For every enabled source:

- fixture schema;
- empty result;
- pagination/checkpoint;
- malformed item;
- timeout;
- rate limit;
- duplicate item;
- changed record;
- source unavailable;
- configuration missing.

#### End-to-end

Create a controlled pipeline fixture:

```text
source records
→ raw persistence
→ normalization
→ duplicate resolution
→ ICP decision
→ identity/domain
→ evidence
→ scoring/gates
→ contact dossier
→ human approval
→ export eligibility
```

Include:

- good company;
- irrelevant company;
- duplicate;
- ambiguous identity;
- failed website;
- stale evidence;
- suppressed contact;
- retryable source failure;
- terminal malformed record.

#### Reliability

- worker killed mid-task;
- broker temporarily unavailable;
- database deadlock/serialization retry where applicable;
- duplicate task delivery;
- checkpoint crash boundary;
- run-lock contention;
- stale lease;
- source 429;
- source 500;
- timeout;
- malformed payload;
- replay after code change.

#### Migration

- clean database;
- previous schema;
- production-shaped anonymized database;
- upgrade;
- reconciliation;
- downgrade only in rehearsal;
- re-upgrade;
- restore from backup.

#### Performance

- large raw insert batch;
- index/query performance;
- operations pagination;
- queue throughput;
- memory bounds;
- database growth.

### Release gate

Extend `scripts/release-gate.sh` so it fails on:

- wrong Python version;
- migration multiple heads;
- reconciliation anomaly;
- missing enabled-source configuration;
- automatic outreach enabled;
- placeholder source marked active;
- failing tests/lint/assets;
- unsafe production defaults;
- missing required indexes/constraints where testable.

### Exit gate

The complete suite passes using Python 3.12, PostgreSQL, and Redis. Do not use SQLite as the authoritative integration environment.

---

# 9. File-level investigation map

Do not assume these exact files are the only ones. Search the repository.

Likely areas:

```text
app/config.py
app/models.py
app/schemas.py
app/jobs/ingestion.py
app/discovery/*
app/sources/*
app/services/pipeline_runs.py
app/services/run_lock.py
app/services/scoring_v4.py
app/services/identity_resolution.py
app/services/domain_verification.py
app/services/evidence*
app/services/readiness*
app/contact_intelligence/*
app/workers/celery_app.py
app/workers/tasks.py
app/routers/operations.py
app/routers/sourcing.py
app/routers/prospects.py
app/routers/queue.py
app/routers/contact_intelligence.py
app/templates/operations/*
app/templates/sourcing*
app/templates/prospects/*
app/static/*
alembic/versions/*
scripts/*
tests/*
docker-compose.yml
.env.production.example
```

For each major feature, identify:

- model;
- service;
- worker;
- API/router;
- UI;
- configuration;
- migration;
- test;
- runbook;
- metrics.

Do not place business logic directly in templates or routers.

---

# 10. Coding standards

- Use explicit typed service boundaries.
- Keep source adapters separate from canonical transformation.
- Keep network IO outside database transactions.
- Use database constraints for core invariants.
- Use deterministic idempotency keys.
- Use timezone-aware UTC timestamps.
- Use structured error categories.
- Avoid broad `except Exception` unless the error is classified, logged, persisted, and re-raised or converted deliberately.
- Do not log raw personal data unnecessarily.
- Keep migrations reversible where feasible and document irreversible behavior.
- Avoid N+1 queries in operations pages.
- Add indexes based on actual query patterns.
- Keep feature flags centralized.
- Do not create a second scoring or readiness implementation.
- Do not create another run ledger.
- Do not add another legacy compatibility model.
- Do not silently coerce UUIDs into integers or vice versa.
- Do not use mutable default configuration.
- Do not hard-code production hostnames, secrets, or counts.
- Do not weaken tests to pass.
- Do not mark skipped tests as proof.

---

# 11. What you must not do

Do not:

- replace the application framework without a proven blocker;
- rewrite the repository from scratch;
- delete the Codex migration;
- remove advisory locks;
- remove per-record savepoints;
- collapse source discovery and enrichment;
- increment a checkpoint before commit;
- make `Prospect` canonical again;
- use company name as a join;
- use guessed domains as official;
- call SMTP acceptance verification;
- activate UK ingestion for the France play;
- activate all schedules at once;
- add broad scraping merely to inflate counts;
- claim success from seeded test data;
- add fake source records to production metrics;
- expose retry endpoints without authentication;
- delete failed-work history after retry;
- enable automatic cold outreach;
- create LinkedIn automation;
- ignore source rate limits or platform restrictions;
- declare the system “elite” because the interface looks polished.

---

# 12. Work method

Work in coherent patch sets.

After each patch set:

1. run focused tests;
2. run compile/lint checks;
3. run migration checks when schema changes;
4. update `TEST_LOG.md`;
5. update `CURRENT_STATE.md`;
6. update `DECISION_LOG.md`;
7. update the defect register;
8. verify `git diff --check`;
9. leave the repository runnable;
10. continue without waiting for confirmation unless an external credential or irreversible production decision is required.

Do not stop after writing an architectural document.

When a live credential is unavailable:

- implement the adapter contract;
- add fixture/contract tests;
- mark the source `MISCONFIGURED` or `UNAVAILABLE`;
- document the exact required configuration;
- do not mark the live acceptance gate passed.

When a decision is uncertain:

- prefer the safest reversible design;
- document the decision;
- continue with everything that does not depend on the external decision.

---

# 13. Required documentation

Maintain the root handoff files:

- `CURRENT_STATE.md`
- `NEXT_ACTIONS.md`
- `TEST_LOG.md`
- `DECISION_LOG.md`
- `CODEX_HANDOFF.md` or rename/add `ANTIGRAVITY_HANDOFF.md` without deleting useful Codex history.

Add:

```text
docs/continuation/baseline-verification.md
docs/continuation/production-copy-rehearsal.md
docs/continuation/canonical-model-cutover-map.md
docs/continuation/source-contract.md
docs/continuation/decp-checkpoint-design.md
docs/continuation/scoring-and-readiness-spec.md
docs/continuation/contact-dossier-spec.md
docs/continuation/automation-activation-record.md
docs/benchmarks/live-source-benchmark.md
docs/operations/operator-guide.md
docs/operations/failure-recovery.md
docs/operations/source-control.md
```

Documentation must match implemented behavior.

---

# 14. Final acceptance criteria

Do not claim the complete mission is finished until all applicable criteria pass.

## Production safety

- Python 3.12 certified.
- Production-shaped rehearsal passed.
- Reconciliation has no unexplained P0 anomalies.
- Backup and restore tested.
- Migration path documented.
- Scheduler activation is reversible.

## Source durability

- Registry and DECP use durable checkpoints.
- DECP raw records are immutable and replayable.
- Raw counters reflect committed rows.
- Source retries do not duplicate raw records.
- Checkpoint recovery cannot skip unseen records.
- Source health is truthful.

## Canonical data

- Company/opportunity/evidence/person/contact are canonical.
- Legacy mutable writes are eliminated.
- Compatibility is read-only.
- No name-based identity joins remain.
- Ambiguities are visible.
- Migration/backfill is idempotent.

## Pipeline reliability

- Every stage has idempotent work.
- Network calls are outside long transactions.
- Retry and terminal failures are classified.
- Worker heartbeat is visible.
- Stale work can recover safely.
- Failed work can be retried with audit.
- No unexplained stage loss exists.

## Commercial intelligence

- France field-service scoring is real and versioned.
- Hard gates are separate.
- Evidence is graded and fresh.
- Domain identity is defensible.
- Buyer roles are appropriate.
- Contacts have provenance.
- Suppression is enforced.
- Human approval is required.
- Automatic outreach is disabled.

## Throughput

- Live controlled benchmarks completed.
- Progressive source movement proven.
- The system no longer plateaus on repeated first pages.
- Safe daily capacity is measured.
- Backlogs remain bounded.
- Source-imposed limitations are documented.

## Operations

- Funnel, source, run, queue, worker, failure, record lineage, checkpoint, and review states are visible.
- Metrics derive from persisted truth.
- Operator actions are authenticated and audited.
- Dangerous actions are bounded and confirmed.

## Tests

- Complete Python 3.12 PostgreSQL/Redis suite passes.
- Source contract tests pass.
- End-to-end controlled pipeline passes.
- Replay/failure/overlap tests pass.
- Release gate passes.
- No meaningful test was removed or weakened.

---

# 15. Final response format

Your final response must contain the following sections.

## A. Executive result

State exactly:

- which phases were completed;
- which automation is enabled;
- which automation remains disabled;
- whether production activation is approved, conditionally approved, or blocked.

## B. Baseline and preserved work

List:

- prior Codex controls verified;
- any divergence found;
- unrelated user changes preserved.

## C. Remaining root causes resolved

Table:

```text
Gap
Old state
Implemented state
Proof
```

## D. Files changed

Group by:

- models/migrations;
- sources;
- pipeline/workers;
- scoring/readiness;
- identity/evidence;
- contacts;
- operations/UI;
- deployment/scripts;
- tests;
- documentation.

## E. Database migrations and reconciliation

Include:

- revision IDs;
- parent revisions;
- tables/columns/indexes/constraints;
- backfill rules;
- anonymized production-copy counts;
- anomalies;
- upgrade/downgrade/re-upgrade results;
- rollback guidance.

## F. Tests and exact commands

Include real commands and outputs:

- Python version;
- lint;
- compile;
- tests;
- source contract tests;
- migration tests;
- release gate;
- frontend audit;
- Compose validation.

Do not say “tests passed” without counts and commands.

## G. Live-source benchmark

Include:

- source;
- batch sizes;
- fetched;
- raw persisted;
- unique companies;
- duplicates;
- ICP eligible;
- errors;
- checkpoint before/after;
- duration;
- queue lag;
- quality sample;
- sustained capacity;
- limitations.

## H. Scoring and contact-quality proof

Include:

- score version;
- gate version;
- reviewed sample;
- false positives/negatives;
- contact provenance distribution;
- suppression tests;
- human-approval behavior.

## I. Deployment and activation

Provide exact:

- backup;
- deploy;
- migration;
- reconciliation;
- diagnostic;
- controlled-run;
- feature-flag;
- scheduler-start;
- pause;
- rollback;
- restore commands.

## J. Security and operational controls

State:

- worker heartbeat;
- retry controls;
- SSRF controls;
- authentication/authorization;
- audit events;
- data retention;
- automatic-outreach state.

## K. Remaining risks

List only real unfinished risks. Do not hide them.

## L. Updated handoff files

Provide paths and concise purpose.

---

# 16. Start instruction

Begin now.

Do not reply with a generic plan and stop.

First read the repository handoff files, verify the current release gate, and create the baseline matrix. Then implement the highest-priority remaining phase.

Continue through the phases in dependency order. If execution limits prevent completing the entire continuation in one session, complete the current phase fully, leave the repository tested and coherent, update all handoff files, and identify the exact next command and next file for continuation.

Never mark a future phase complete merely because its interface, placeholder, or model exists.
