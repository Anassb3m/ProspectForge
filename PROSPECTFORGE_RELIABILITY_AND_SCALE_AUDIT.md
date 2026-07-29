# ProspectForge Reliability and Scale Audit

**Codebase audited:** `ProspectForge-antigravity-prospectforge-level-300(1)`  
**Audit type:** static code and architecture audit  
**Primary incident:** only about 11 prospects produced after more than four days in production  
**Audit date:** 2026-07-28

---

## 1. Executive verdict

ProspectForge is **not currently a reliable continuous prospect-acquisition engine**. It contains useful components, but the active production path is an incomplete hybrid of:

1. a small, manually reviewed meeting-ready queue;
2. a legacy `Prospect` pipeline;
3. a newer normalized `Company` / `Opportunity` platform;
4. placeholder source adapters and durable-runtime models that are not connected to execution.

The low output is not explained by one parameter. Multiple defects compound:

- nightly ingestion defaults to a tiny deterministic batch;
- repeated runs restart from the same source pages and revisit the same top-ranked companies;
- the selected market play is discarded in important paths;
- the default UI path selects a UK source whose runtime branch returns zero;
- automatic contact discovery depends on a score that is never calculated in the active legacy pipeline;
- the bulk enrichment worker crashes because it calls `deep_enrich()` incorrectly and references a nonexistent field;
- one record-level error can roll back previously successful rows in the same transaction while counters still claim success;
- operational dashboards read different tables from those actually written by ingestion;
- source checkpoints, durable work items, source runs, and rate budgets exist as models but are unused;
- the codebase dual-writes to two incompatible data models and reads from them inconsistently.

**Current rating: 3/10 as a dependable acquisition engine.**

It is closer to a pilot queue generator than a production-grade discovery, enrichment, and qualification platform.

The system can be repaired without discarding everything, but the repair must begin by choosing one canonical pipeline and fixing orchestration before increasing volume.

---

## 2. Define the output correctly

A reliable engine must show separate counts for:

```text
raw source records
→ unique legal entities
→ ICP-eligible companies
→ domain/evidence-enriched companies
→ qualified opportunities
→ buyer/contact dossiers
→ human-approved contact-ready prospects
```

Hundreds of **raw companies** per day are realistic from broad registry sources. Hundreds of genuinely verified, evidence-backed, contact-ready prospects per day are a much more expensive objective.

The present application collapses several stages into “prospects,” making expectations and diagnostics unreliable.

### Sensible initial production targets after repair

| Stage | Daily target | Notes |
|---|---:|---|
| Raw records discovered | 500–2,000 | Registry/source dependent |
| Unique companies normalized | 200–800 | After legal-ID deduplication |
| ICP-eligible companies | 75–300 | Depends on market-play filters |
| Domain/evidence enrichment | 100–300 | Bounded by web/API limits |
| Contact dossiers attempted | 20–75 | Higher cost and error rate |
| Human-reviewed contact-ready | 5–25 | Quality-controlled output |

Do **not** change the current batch from 10 to 1,000 before separating stages. The current inline enrichment design would become slower and more fragile.

---

# Part I — Confirmed critical defects

## P0-1 — The nightly task defaults to only 10 companies

**Files**

- `app/workers/tasks.py`, `ingest_market_play()`
- `app/workers/celery_app.py`, `beat_schedule`

The task signature is:

```python
def ingest_market_play(self, play_code: str, mode: str, limit: int = 10)
```

The nightly Celery Beat call does not provide `limit`, so it uses 10:

```python
"kwargs": {"play_code": "DEFAULT", "mode": "full"}
```

This is a hard throughput constraint, but it does not alone prove why production stopped at exactly 11. In `full` mode, the registry branch uses a minimum of 40. Production run statistics and errors must therefore be inspected.

### Fix

Make limits explicit and source-specific, but only raise them after cursors and stage separation exist:

```python
"kwargs": {
    "play_code": "FIELD_OPERATIONS_FR_V2",
    "mode": "full",
    "discovery_limit": 500,
}
```

---

## P0-2 — Every run restarts from the same source pages

**Files**

- `app/discovery/annuaire.py`, `discover_companies_for_play()`
- `app/discovery/decp.py`, `filter_relevant()` and `aggregate_by_siret()`
- `app/models.py`, `SourceCheckpoint`

The Annuaire path starts again at page 1 for the same NAF codes and keyword queries, sorts candidates, and returns the same top slice. There is no persisted `(play, query, page)` cursor.

The DECP path sorts awards newest-first, aggregates companies, ranks by award count/value, and slices the same first `max_companies` entries. It has no high-water mark or processed-record ledger.

A `SourceCheckpoint` model exists, but active ingestion never reads or updates it.

### Result

Day 2, 3, and 4 can mostly update the same companies instead of discovering new ones. Deduplication then makes the database appear stuck.

### Fix

Use connector-specific checkpoints:

```text
annuaire:{play_code}:{naf_code} → next_page
annuaire:{play_code}:keyword:{query_hash} → next_page
decp:{play_code} → last_seen(dateAttribution, external_id)
companies_house:{play_code}:{sic_code} → start_index
```

Advance a checkpoint only after raw records are durably stored.

---

## P0-3 — The selected market play is discarded

**Files**

- `app/routers/sourcing.py`
- `app/workers/tasks.py`
- `app/jobs/ingestion.py`
- `app/plays/__init__.py`

The form sends `play_code` to `ingest_market_play`, but the worker calls `run_ingestion()` without passing it. The ingestion service therefore defaults to:

```python
DEFAULT_PLAY_CODE = "FIELD_OPERATIONS_UK_V1"
```

The registry implementation also hardcodes `DEFAULT_PLAY_CODE`, and newly created legacy and normalized records are tagged with the default.

### Result

The UI can display the France play while the worker runs and tags data as UK. Filtering, evidence rules, messaging policy, and analytics become unreliable.

### Fix

Pass the play through every function:

```python
# app/workers/tasks.py
stats = run_async(
    run_ingestion(
        play_code=play_code,
        mode=mode,
        max_companies=limit,
        run_contact_discovery=run_contacts,
        skip_sirene=skip_sirene,
    )
)
```

Change `ingest_registry()` to accept `play_code`, use it in `discover_companies_for_play()`, and pass it into both legacy and normalized record creation.

Do not use `"DEFAULT"` as a production play code.

---

## P0-4 — The default UK acquisition route produces zero companies

**Files**

- `app/templates/sourcing.html`
- `app/jobs/ingestion.py`
- `app/sources/companies_house.py`

The acquisition wizard defaults to:

```text
play = FIELD_OPERATIONS_UK_V1
mode = companies_house
```

But `run_ingestion(mode="companies_house")` only logs the request and returns:

```python
{"companies": 0, "created": 0, "updated": 0, "errors": 0}
```

A `CompaniesHouseAdapter` exists, but it is not wired into `run_ingestion()`.

### Result

The application presents a working UK path that is operationally a zero-result placeholder.

### Fix

Either:

1. remove/disable the UK option until implemented; or
2. integrate `CompaniesHouseAdapter` into the canonical source pipeline with SIC partitioning, pagination, checkpoints, normalization, and health reporting.

Never show a source as healthy merely because an interface class exists.

---

## P0-5 — Automatic contact discovery is starved by a score that remains zero

**Files**

- `app/jobs/contact_discovery.py`
- `app/commercial.py`
- `app/jobs/recalculate_scores.py`
- `app/models.py`

Nightly contact discovery requires:

```python
Prospect.opportunity_score >= settings.contact_min_opportunity_score
```

The default threshold is 40. New prospects default to `opportunity_score = 0`.

`recompute_commercial_state()` claims to apply the V3 commercial projection, but it only loads evidence, qualification, suppression, and offer assets. It never calculates or assigns:

- `pain_score`
- `trigger_score`
- `authority_score`
- `value_score`
- `data_quality_score`
- `opportunity_score`
- `readiness_state`

The nightly score recalculation calls this no-op projection.

### Result

The contact scheduler can select zero records forever, even when companies were ingested successfully.

### Fix

Build one deterministic scoring service and call it from:

- ingestion;
- evidence updates;
- contact updates;
- qualification changes;
- nightly reconciliation.

The score service must persist dimension values, total score, failure reasons, and readiness state. Add unit tests for every gate.

---

## P0-6 — The bulk enrichment worker is broken at runtime

**File**

- `app/workers/tasks.py`, `extract_website_evidence()`

`deep_enrich()` is keyword-only:

```python
async def deep_enrich(
    *,
    siren=None,
    siret=None,
    company_name=None,
    existing=None,
    ...
)
```

The worker calls it positionally and references `prospect.name`, which does not exist; the model field is `company_name`.

### Correct call

```python
data = await deep_enrich(
    siren=prospect.siren,
    siret=prospect.siret,
    company_name=prospect.company_name,
    existing={
        "website": prospect.website,
        "email": prospect.email,
        "decision_maker_name": prospect.decision_maker_name,
        "dirigeants": prospect.dirigeants,
    },
    run_contacts=False,
    infer_web=True,
)
```

The task should then enqueue contact discovery separately only after domain/evidence enrichment succeeds.

---

## P0-7 — UI ingestion options are ignored in background runs

**File**

- `app/routers/sourcing.py`

The form accepts:

- `contacts`
- `skip_sirene`

but only sends `play_code`, `mode`, and `limit` to Celery.

The API background path has the same problem. The worker hardcodes:

```python
run_contact_discovery=False
skip_sirene=False
```

### Result

The interface claims to control behavior that the runtime ignores.

### Fix

Extend the Celery task contract:

```python
def ingest_market_play(
    self,
    play_code: str,
    mode: str,
    discovery_limit: int,
    run_contacts: bool = False,
    skip_sirene: bool = False,
)
```

Store the complete requested configuration in the run record for auditability.

---

## P0-8 — A single row failure can erase earlier successful rows

**File**

- `app/jobs/ingestion.py`, `ingest_decp()` and `ingest_registry()`

The code commits every 15 companies. On an individual company exception it executes:

```python
await session.rollback()
```

That rollback removes all uncommitted successful changes since the previous commit. However, `stats["created"]` and `stats["updated"]` are not corrected.

### Result

A run can report successful creates that do not exist in the database. For a batch under 15, a late failure can erase most of the batch.

### Fix

Use a savepoint per company:

```python
for company in companies:
    try:
        async with session.begin_nested():
            prospect, created, status = await upsert_prospect(...)
    except Exception:
        stats["errors"] += 1
        continue

await session.commit()
```

An even stronger design is one durable work item/session per company after raw discovery.

---

## P0-9 — Production observability reads the wrong runtime tables

**Files**

- `app/jobs/ingestion.py`
- `app/routers/operations.py`
- `app/services/__init__.py`
- `app/models.py`

Ingestion writes `IngestionRun`. The operations page queries `PipelineRun`, which active ingestion never creates.

Dashboard fields such as these are hardcoded:

```text
failed_or_blocked_jobs = 0
companies_imported_per_day = 0
opportunities_created_per_day = 0
contact_ready_yield = 0
duplicate_rate = 0
domain_verification_rate = 0
```

`/ready` checks only the database. It does not check Redis, workers, Beat, queues, last successful source run, or source health.

### Result

The application can look healthy while acquisition is stalled or failing.

### Fix

Choose one runtime model and make every task emit:

- run ID;
- source/play/config;
- discovered count;
- accepted count;
- duplicate count;
- created/updated count;
- enriched/contacted count;
- error count and categories;
- checkpoint before/after;
- start/end timestamps;
- queue latency.

The operations page must read those actual records. Readiness should remain lightweight, but add a separate `/ops/health` or authenticated diagnostics endpoint for the full engine.

---

## P0-10 — Scheduler feature flags do not control Celery Beat

**Files**

- `.env.production.example`
- `app/config.py`
- `app/workers/celery_app.py`
- `docker-compose.yml`

The environment exposes:

```text
ENABLE_SCHEDULER=false
ENABLE_NIGHTLY_INGESTION=false
```

But the Beat schedule is always declared, and `celery-beat` is always started by normal Compose deployment. The flags are not used in schedule construction.

### Result

Configuration and documentation do not reflect actual runtime behavior. Operators cannot safely reason about whether automation is enabled.

### Fix

Build `beat_schedule` conditionally from settings, or place Beat behind a Compose profile:

```python
schedule = {}

if settings.enable_scheduler and settings.enable_nightly_ingestion:
    schedule["nightly-ingestion"] = {...}

if settings.enable_scheduler and settings.enable_nightly_contact_discovery:
    schedule["nightly-contact-discovery"] = {...}

celery_app.conf.beat_schedule = schedule
```

A startup log must list enabled schedules and resolved batch sizes.

---

# Part II — Structural defects preventing reliable scale

## P1-1 — Discovery and deep enrichment run sequentially in one transaction

The current ingestion loop does all of this inline for every company:

1. source discovery;
2. Annuaire enrichment;
3. optional SIRENE call;
4. website inference with up to four sequential HEAD requests;
5. optional contact discovery;
6. dual model write;
7. evidence write;
8. commercial-state projection.

This makes source ingestion slow and fragile. One slow website or API call holds the entire run open.

### Required architecture

```text
Source Scheduler
  → raw source records
  → normalize/dedupe
  → ICP prefilter
  → identity/domain enrichment
  → website/evidence extraction
  → score/readiness
  → contact dossier
  → human review
```

Each transition must be a durable idempotent task.

---

## P1-2 — The codebase has two competing sources of truth

Legacy model:

```text
Prospect
EvidenceSignal
QualificationReview
OutreachEvent
```

New normalized model:

```text
Company
CompanyIdentifier
CompanyDomain
Opportunity
EvidenceItem
ScoreSnapshot
Person
```

Ingestion writes to both, but not equivalently. Several pages query normalized `Opportunity` IDs while sourcing and contact jobs work with legacy integer `Prospect` IDs. Legacy linkage is sometimes reconstructed by company name, which is not a safe identifier.

Evidence is written to `EvidenceSignal`, while V4 scoring reads `EvidenceItem`. Therefore the normalized score engine may not see the evidence collected by ingestion.

### Fix

Select the normalized schema as the canonical source of truth.

Use a temporary compatibility projection for old screens, but stop independent dual writes. Every legacy view should derive from normalized entities using explicit IDs, never company-name matching.

Migration sequence:

1. add `legacy_prospect_id` mapping table or foreign key;
2. backfill normalized identifiers/domains/evidence;
3. switch ingestion to normalized only;
4. switch services and UI reads;
5. switch contact intelligence;
6. remove legacy writes;
7. archive legacy tables after reconciliation.

---

## P1-3 — V4 scoring is placeholder logic and cannot produce outreach-ready records

**File**

- `app/services/scoring_v4.py`

Problems include:

- ICP fit boosts Technology/IT/Cybersecurity instead of the field-operations play;
- commercial value is always 50;
- contact quality adds a flat value per person;
- risk penalty is always zero;
- usable contact path and suppression are hardcoded true;
- human approval is hardcoded false.

Because hard gates use `all()`, no normalized opportunity can become outreach-ready.

### Fix

Delete placeholder scoring behavior from production paths. Implement a play-versioned score profile with tested dimensions and explicit evidence requirements.

Scores should prioritize work. Hard gates should control readiness. A high score must never override missing legal identity, suppression, contact provenance, or human approval.

---

## P1-4 — The source adapter layer is mostly not integrated

- `CompaniesHouseAdapter` performs API calls but is not invoked by ingestion.
- `BodaccAdapter.discover()` returns `[]`.
- `OcdsAdapter.discover()` returns `[]`.
- Health checks for placeholder adapters claim they are healthy/interface-ready.

### Fix

A source is `enabled` only when all are true:

- configuration validated;
- healthcheck performs a meaningful upstream check;
- discovery implemented;
- normalization implemented;
- checkpoint strategy implemented;
- contract tests pass;
- source is wired into scheduler and run records.

Otherwise mark it `planned` or `disabled`.

---

## P1-5 — Domain inference is too weak to support contact discovery

**File**

- `app/discovery/enrich.py`, `infer_website()`

It strips legal-form words, removes all non-ASCII characters without transliteration, concatenates the name, and tries only `.fr` and `.com` variants using HEAD.

Valid sites may reject HEAD, use hyphens/acronyms, or have unrelated domains. A responding guessed domain may belong to another company.

### Fix

Build evidence-backed domain resolution:

1. use official registry/company-controlled URLs when available;
2. search trusted source pages;
3. generate transliterated/acronym candidates;
4. use GET with bounded content retrieval when HEAD is rejected;
5. verify company name, address, legal notice, SIREN, phone, or brand on page;
6. store candidate, evidence, confidence, and contradiction state;
7. require a confidence gate before contact inference.

---

## P1-6 — No distributed lock prevents overlapping runs

Manual ingestion and Beat can run at the same time. Multiple Beat instances could also duplicate work.

### Fix

Use a Redis lock or PostgreSQL advisory lock keyed by:

```text
ingestion:{play_code}:{source_partition}
```

The lock requires:

- unique run ID;
- lease/heartbeat;
- safe expiry;
- explicit skipped-overlap result;
- idempotent work items even if lock recovery occurs.

---

## P1-7 — Reacher is optional but not started by normal deployment

The `reacher` service is behind the `reacher` Compose profile. Plain deployment does not start it.

If `REACHER_ENABLED=true` but deployment does not use `--profile reacher`, verification will fail.

### Fix

Validate startup configuration:

- fail fast when `REACHER_ENABLED=true` and the service is unreachable;
- document `docker compose --profile reacher up -d`;
- show verifier health in operations;
- never equate guessed email patterns with verified contact paths.

---

# Part III — Target architecture

## 1. Canonical entities

Use:

```text
SourceConnector
SourceRun
SourceRecord
Company
CompanyIdentifier
CompanyDomain
CompanyLocation
CompanyClassification
Opportunity
EvidenceItem
Person
PersonRole
ContactPoint
ScoreSnapshot
QualificationReview
SuppressionEntry
PipelineRun
WorkItem
FailedWorkItem
SourceCheckpoint
SourceRateBudget
```

## 2. Canonical pipeline

### Stage A — Source discovery

Input:

- play version;
- connector;
- source partition;
- checkpoint;
- requested limit.

Output:

- immutable `SourceRun`;
- immutable deduplicated `SourceRecord` rows;
- next checkpoint candidate.

No website, contact, or scoring calls occur here.

### Stage B — Normalize and deduplicate

Identity keys in order:

1. official legal identifier;
2. establishment identifier;
3. verified official domain;
4. carefully normalized legal name + address;
5. human conflict review.

Output:

- company created/updated;
- source provenance link;
- duplicate/contradiction decision.

### Stage C — ICP prefilter

Reject obvious non-fit entities cheaply using:

- jurisdiction;
- active status;
- legal form;
- classification;
- size band;
- geography;
- explicit exclusion rules.

### Stage D — Identity/domain enrichment

Resolve:

- official legal status;
- establishments;
- domain candidates;
- company-controlled evidence;
- freshness and provenance.

### Stage E — Operational evidence

Collect only source-backed evidence relevant to the selected play:

- branches;
- recurring service;
- field-team indicators;
- hiring;
- portals/forms;
- maintenance/SAV language;
- contracts and triggers;
- technology/integration evidence.

### Stage F — Scoring and gates

Persist:

- dimensions;
- weights/profile version;
- reasons;
- contradictions;
- hard-gate results;
- total score;
- readiness.

### Stage G — Contact dossier

Attempt only when the company passes a minimum evidence/fit threshold.

Persist:

- person/company relationship;
- role category;
- source URL;
- contact point provenance;
- verification result;
- confidence;
- legal/compliance decision.

### Stage H — Human review

Human decision:

- accept;
- more research;
- park;
- reject;
- suppress.

Only accepted records enter the contact-ready queue.

---

# Part IV — Exact implementation order

## Patch Set 1 — Stop false behavior and data loss

1. Pass `play_code`, `contacts`, and `skip_sirene` through UI → Celery → ingestion.
2. Change the production default play to `FIELD_OPERATIONS_FR_V2` if France is the active launch market.
3. Disable the UK wizard option until Companies House is truly wired.
4. Fix `extract_website_evidence()`.
5. Replace batch-level rollback with per-record savepoints.
6. Make Beat settings conditional and visible at startup.
7. Change operations UI to read actual ingestion/failure records.
8. Add run IDs to every log line.
9. Add a distributed run lock.
10. Add regression tests for all above.

### Exit gate

- one manual run processes the selected play;
- one row failure does not erase other rows;
- options selected in the UI appear in the stored run config;
- failed worker tasks appear in operations;
- UK cannot falsely report success with zero implementation.

---

## Patch Set 2 — Make discovery progressive and durable

1. Use `SourceRun` and `SourceRecord` for all raw discovery.
2. Add unique constraints for connector/external record identity and payload hash.
3. Implement Annuaire checkpoint by NAF/query/page.
4. Implement DECP high-water mark and unseen-record filtering.
5. Advance checkpoints only after commit.
6. Add retry-safe idempotency.
7. Store duplicates and rejects as measured outcomes, not silent disappearance.
8. Add source health and last-success metrics.

### Exit gate

Run the same source five times:

- no duplicate company inflation;
- each run continues to new pages/records;
- checkpoint progression is visible;
- replaying a completed run creates zero duplicate records;
- a failed run resumes safely.

---

## Patch Set 3 — Separate ingestion from enrichment

1. Source ingestion writes raw records only.
2. Enqueue one normalize task per raw record.
3. Enqueue one domain/evidence task per eligible company.
4. Recompute score after evidence changes.
5. Enqueue contact discovery only after score/gates permit it.
6. Add source-specific concurrency and rate budgets.
7. Add retry classes:
   - transient network;
   - rate-limited;
   - permanent invalid record;
   - policy/compliance reject;
   - code defect.
8. Add dead-letter retry and operator controls.

### Exit gate

- discovery throughput is not blocked by website latency;
- failed enrichments do not fail the source run;
- queue age and success rate are visible per stage;
- workers can be scaled independently.

---

## Patch Set 4 — Consolidate the data model

1. Establish normalized entities as canonical.
2. Create explicit legacy-to-normalized mapping.
3. Backfill current production data with a reconciliation report.
4. Convert evidence to `EvidenceItem`.
5. Convert contact records to canonical people/contact points.
6. Update UI/services to use normalized UUIDs consistently.
7. Stop writing new legacy `Prospect` rows.
8. Remove company-name-based linkage.

### Exit gate

- one company has one canonical identity;
- every source record has provenance;
- every opportunity links to one play version;
- every evidence item is visible to scoring;
- every UI route and worker uses the same IDs.

---

## Patch Set 5 — Build real scoring and contact readiness

1. Implement play-versioned scoring rules.
2. Separate rank score from hard gates.
3. Persist reason codes and evidence references.
4. Make suppression and contact provenance real gates.
5. Add human approval workflow.
6. Add a nightly reconciliation job that detects stale/inconsistent state.
7. Add score-distribution and gate-failure analytics.

### Exit gate

- scoring tests cover fit, evidence, contact, suppression, and contradictions;
- contact discovery receives eligible records;
- no record becomes contact-ready without required evidence and approval;
- operators can see exactly why each record failed.

---

# Part V — Required metrics and alerts

## Throughput

- raw records discovered per source/run/day;
- unique companies created;
- companies updated;
- duplicate rate;
- ICP acceptance rate;
- enrichment attempted/completed/failed;
- contact attempted/completed/failed;
- human-review acceptance rate;
- contact-ready yield;
- processing latency at every stage;
- queue depth and oldest-message age.

## Reliability

- last successful run per source;
- checkpoint age;
- retry count;
- permanent failure count;
- rollback count;
- source HTTP status/rate-limit events;
- worker heartbeat;
- Beat heartbeat;
- Redis connectivity;
- database connectivity;
- lock conflicts.

## Alerts

Alert when:

- no successful discovery run for 26 hours;
- two consecutive runs create zero new raw records;
- duplicate rate exceeds 90% unexpectedly;
- a checkpoint does not move for three successful runs;
- any queue’s oldest task exceeds its SLO;
- contact selection remains zero while eligible companies exist;
- worker failures exceed a fixed percentage;
- a source healthcheck contradicts actual discovery failures.

---

# Part VI — Production diagnostics to run now

These commands determine which defects caused the current 11-record incident. Adjust the deployment directory and database credentials to your environment.

```bash
cd /opt/prospectforge
docker compose ps
```

```bash
docker compose logs --since=96h \
  celery-beat worker-ingestion worker-evidence worker-contact \
  | grep -Eai 'ingest|created|updated|selected|checkpoint|error|failed|traceback'
```

Inspect actual ingestion runs:

```bash
docker compose exec db psql \
  -U "${POSTGRES_USER:-prospectforge}" \
  -d "${POSTGRES_DB:-prospectforge}" \
  -c "
SELECT id, adapter, market_play_code, status,
       started_at, finished_at, stats_json, error_summary
FROM ingestion_runs
ORDER BY id DESC
LIMIT 30;
"
```

Count legacy prospects by day and play:

```bash
docker compose exec db psql \
  -U "${POSTGRES_USER:-prospectforge}" \
  -d "${POSTGRES_DB:-prospectforge}" \
  -c "
SELECT DATE(created_at) AS day,
       market_play_code,
       COUNT(*) AS created
FROM prospects
GROUP BY 1, 2
ORDER BY 1 DESC, 2;
"
```

Check whether score starvation blocks contact discovery:

```bash
docker compose exec db psql \
  -U "${POSTGRES_USER:-prospectforge}" \
  -d "${POSTGRES_DB:-prospectforge}" \
  -c "
SELECT opportunity_score, readiness_state,
       contact_discovery_state, COUNT(*)
FROM prospects
GROUP BY 1, 2, 3
ORDER BY 1 DESC, 2, 3;
"
```

Inspect failures:

```bash
docker compose exec db psql \
  -U "${POSTGRES_USER:-prospectforge}" \
  -d "${POSTGRES_DB:-prospectforge}" \
  -c "
SELECT failed_at, task_name, error_message, payload
FROM failed_work_items
ORDER BY failed_at DESC
LIMIT 50;
"
```

Compare legacy and normalized counts:

```bash
docker compose exec db psql \
  -U "${POSTGRES_USER:-prospectforge}" \
  -d "${POSTGRES_DB:-prospectforge}" \
  -c "
SELECT
  (SELECT COUNT(*) FROM prospects) AS legacy_prospects,
  (SELECT COUNT(*) FROM companies) AS normalized_companies,
  (SELECT COUNT(*) FROM opportunities) AS normalized_opportunities,
  (SELECT COUNT(*) FROM evidence_signals) AS legacy_evidence,
  (SELECT COUNT(*) FROM evidence_items) AS normalized_evidence;
"
```

Check scheduler registration:

```bash
docker compose exec celery-beat \
  celery -A app.workers.celery_app inspect registered
```

Check active and reserved tasks:

```bash
docker compose exec worker-ingestion \
  celery -A app.workers.celery_app inspect active reserved scheduled
```

---

# Part VII — Tests that must exist before calling the engine reliable

## Unit tests

- play propagation;
- source partition/cursor calculation;
- normalization and identity matching;
- evidence deduplication;
- score dimensions;
- hard gates;
- suppression;
- contact provenance;
- checkpoint advancement;
- retry classification.

## Integration tests

Use real PostgreSQL and Redis containers.

Required scenarios:

1. 100 raw source records create expected unique companies.
2. Replaying the same source run creates no duplicates.
3. A failure on record 37 does not erase records 1–36.
4. A retry after network failure resumes without duplication.
5. Selected France play remains France through every table and task.
6. Contact discovery runs after score eligibility.
7. Suppressed companies never enter contact tasks.
8. Operations shows the same run and counts written by workers.
9. Scheduler flags genuinely enable/disable tasks.
10. UK mode either works or is visibly unavailable.

## Contract tests

Mock or fixture:

- Recherche Entreprises;
- SIRENE;
- DECP;
- Companies House;
- website/domain resolver;
- email verifier.

Record response-shape changes and malformed data cases.

## Current validation performed during this audit

- Python source compilation with `python -m compileall -q app tests`: **passed**.
- Full automated tests were **not executed** because the audit environment was not installed as the project runtime with all dependencies and services. This is not evidence that tests pass or fail.

---

# Part VIII — What should not be done

Do not:

- merely change `limit=10` to `limit=1_000`;
- enable every source simultaneously;
- perform contacts inside source ingestion;
- keep dual-writing two independent models;
- use company name as an identity join;
- call a placeholder adapter healthy;
- use guessed domains as verified evidence;
- treat SMTP acceptance as proof that a person is correct;
- send outreach automatically from ingestion;
- optimize contact-ready volume before raw/source metrics are trustworthy;
- deploy the refactor without a migration and reconciliation report.

---

# Final recommendation

The fastest defensible route is:

```text
Week 1:
repair play propagation, worker calls, transactions, scheduler controls,
and observability

Week 2:
implement SourceRun/SourceRecord/checkpoints and progressive discovery

Week 3:
split normalization, enrichment, scoring, and contact queues

Week 4:
migrate to one canonical normalized data model and production-test replay,
failure recovery, and throughput
```

After those gates pass, raise raw discovery gradually:

```text
100/day → 300/day → 750/day → 1,500/day
```

At each increase, measure:

- novelty;
- duplicate rate;
- error rate;
- queue age;
- source limits;
- enrichment yield;
- contact-ready yield.

The application should be judged by a stable funnel and explainable losses—not by a single total prospect count.
