# CODEX MASTER EXECUTION PROMPT — REBUILD PROSPECTFORGE INTO A RELIABLE ACQUISITION ENGINE

You are working directly inside the existing **ProspectForge** repository. Your task is not to produce another plan, architectural essay, or cosmetic UI refresh. Your task is to **inspect, repair, refactor, test, migrate, and operationalize the existing system** so it becomes a dependable prospect-discovery, enrichment, qualification, and contact-research engine for a real one-person software business.

Treat the current implementation as untrusted until verified. Some components are useful; others are placeholders, disconnected, contradictory, or misleading. Do not preserve broken abstractions merely because they exist. Do not rewrite the whole application blindly either. Reuse sound components, replace defective paths, and prove every important behavior with executable tests and production diagnostics.

Read this prompt completely before changing code.

---

# 1. Primary mission

Transform ProspectForge from an unreliable pilot queue generator into a **production-grade, explainable, progressive, durable acquisition pipeline** that performs this funnel:

```text
source records discovered
→ raw records persisted with provenance
→ legal entities normalized and deduplicated
→ ICP-ineligible records rejected cheaply
→ identity and official domain resolved
→ operational evidence collected
→ opportunities scored with explainable dimensions
→ hard readiness gates evaluated
→ buyer/contact dossiers researched
→ human review performed
→ approved contact-ready prospects queued
```

The system must support hundreds or thousands of raw source records while being honest that only a smaller subset will become evidence-backed, human-approved contact-ready prospects.

The target is not “10,000 emails.” The target is a reliable funnel that produces enough high-quality companies and decision-maker dossiers for controlled direct-client acquisition.

---

# 2. Business context to preserve

ProspectForge supports a solo software business operated by Anass Benameur.

Current launch market:

- Geography: **France**.
- Initial vertical: commercial HVAC, refrigeration, maintenance, field service, installation, repair, and adjacent technical-service companies.
- Approximate target size: 20–150 employees, while retaining configurable ranges.
- Initial operational wedge: the flow from completed field intervention to office validation, documents, parts information, and invoice-ready administration.
- Likely buyer roles: managing director in smaller companies; operations/service director; technical director; administrative/finance lead; IT/digital lead where relevant.

Commercial process:

```text
research
→ qualification
→ relevant contact
→ sales conversation
→ paid mapping or bounded pilot
→ delivery
→ acceptance
→ expansion/support/referral
```

ProspectForge may automate low-risk research and administration. It must **not** impersonate human judgment, invent evidence, fabricate decision-makers, or automatically send cold outreach without explicit human approval.

A record is not contact-ready merely because a guessed email exists. It becomes contact-ready only when identity, relevance, evidence, role, provenance, suppression status, and human approval satisfy explicit gates.

---

# 3. Incident and verified defect context

The application was deployed for more than four days and produced only about **11 prospects**, despite the expectation that raw discovery should produce hundreds.

The existing audit found multiple compounding defects:

1. The scheduled ingestion task defaults to a tiny batch.
2. Source discovery restarts from the same first pages/ranked records because no active persistent cursor/checkpoint strategy is used.
3. Repeated runs mostly revisit the same companies, so deduplication makes the engine appear stuck.
4. The selected market play is dropped between UI, Celery task, and ingestion service.
5. Important paths can default to `FIELD_OPERATIONS_UK_V1` even when France was selected.
6. The sourcing UI defaults to a Companies House path that returns zero records.
7. A Companies House adapter exists but is not wired into active ingestion.
8. “Run contacts” and “skip SIRENE” UI choices are ignored in background execution.
9. Contact discovery requires an opportunity-score threshold, but the active recalculation path does not calculate/persist the needed scores.
10. The bulk website-enrichment worker calls `deep_enrich()` with an invalid positional signature and references `prospect.name` instead of the actual field.
11. One company failure can call `session.rollback()` and erase successful uncommitted rows while counters still report success.
12. Ingestion writes `IngestionRun`, while operations reads `PipelineRun`, hiding real execution state.
13. Several dashboard metrics are hardcoded to zero.
14. `/ready` checks the database but not acquisition-engine health.
15. `ENABLE_SCHEDULER` and `ENABLE_NIGHTLY_INGESTION` do not control Celery Beat registration.
16. Celery Beat is started in normal Compose deployment regardless of those flags.
17. Discovery, identity enrichment, website checks, evidence, scoring, and contacts are combined sequentially inside long transactions.
18. The repository has two competing data architectures: legacy `Prospect` and normalized `Company` / `Opportunity`.
19. Ingestion dual-writes incompletely; workers and screens read the models inconsistently.
20. Some linkage uses company names instead of stable IDs.
21. Evidence is written to legacy `EvidenceSignal`, while newer scoring reads normalized `EvidenceItem`.
22. `scoring_v4.py` contains placeholder logic, irrelevant ICP assumptions, hardcoded contact/suppression states, and unusable readiness behavior.
23. Companies House, BODACC, and OCDS adapters are disconnected or placeholders yet may appear healthy.
24. Domain inference is too weak and may mistake a responding guessed domain for an official company domain.
25. No distributed lock prevents overlapping ingestion runs.
26. Reacher may be enabled while its Compose profile is not running.
27. The operations interface cannot explain where records are lost.

Verify every item against current code because the repository may have changed. Add newly discovered defects to the defect register and repair all defects that affect this mission.

---

# 4. Existing repository and stack

The project currently uses approximately:

- Python 3.12+
- FastAPI
- async SQLAlchemy
- PostgreSQL in production
- Alembic
- Redis
- Celery workers and Celery Beat
- Jinja / HTMX / Alpine
- Docker Compose
- Caddy
- pytest / pytest-asyncio
- ruff
- public sources such as Annuaire/Recherche Entreprises, SIRENE, DECP, Companies House, Reacher, and company websites

Important paths include:

```text
app/config.py
app/models.py
app/database.py
app/commercial.py
app/plays/
app/discovery/
app/sources/
app/jobs/
app/workers/celery_app.py
app/workers/tasks.py
app/services/
app/repositories/
app/routers/sourcing.py
app/routers/operations.py
app/routers/dashboard.py
app/routers/prospects.py
app/templates/sourcing.html
app/templates/operations/index.html
docker-compose.yml
.env.production.example
alembic/
scripts/
tests/
```

Existing models include:

```text
Prospect
EvidenceSignal
IngestionRun
Company
CompanyIdentifier
CompanyName
CompanyClassification
CompanyLocation
CompanyDomain
SourceRun
SourceRecord
Opportunity
EvidenceItem
ScoreSnapshot
PipelineRun
WorkItem
SourceRateBudget
SourceCheckpoint
FailedWorkItem
```

Some are disconnected or redundant. Inspect actual fields, indexes, constraints, relationships, and migrations before consolidation.

---

# 5. Non-negotiable working rules

## Do not stop at analysis

Modify code, migrations, tests, configuration, deployment files, documentation, and diagnostics. An analysis-only response is failure.

## Inspect before editing

Before broad changes:

1. Determine the repository root.
2. Read `README.md`, `DEPLOY.md`, `GUIDE.md`, existing implementation prompts, acceptance docs, and production config.
3. Inspect models and Alembic history.
4. Trace the real path from sourcing UI to router, task, job, adapter, DB write, scoring, contact selection, and operations display.
5. Inspect tests; identify meaningful, outdated, over-mocked, and missing coverage.
6. Inspect Git status and preserve unrelated work.
7. Restrict changes to ProspectForge; do not modify sibling projects.

## Verify audit claims

For every stated defect:

- locate exact current code;
- confirm behavior;
- identify all callers;
- repair root cause;
- add a regression test;
- record it in the implementation report.

## Preserve production data

Never “fix” model inconsistency by deleting the database. Every schema change requires:

- forward migration;
- safe defaults;
- backfill strategy;
- reconciliation report;
- rollback/recovery plan;
- compatibility window when needed;
- explicit duplicate/contradiction handling.

## No fake completion

Do not call a source implemented/healthy if it returns `[]`, uses hardcoded data, only imports successfully, or lacks pagination/checkpoint behavior.

Do not hardcode dashboard metrics.

Do not make tests green by weakening assertions, deleting tests, skipping critical cases, or replacing real behavior with meaningless mocks.

Do not claim production throughput from fixtures alone.

## Do not merely raise limits

Changing `limit=10` to `limit=1000` is forbidden as the primary fix. Build progressive discovery, durable persistence, stage separation, idempotency, retries, rate budgets, and observability first.

## Preserve human control

Do not enable automatic cold outreach. Campaign sending remains disabled by default and requires explicit operator approval, policy checks, suppression checks, and deliberate action.

## Be operationally conservative

Use bounded concurrency, rate limits, request timeouts, response-size limits, backoff, and source-specific failure classifications.

## Keep losses explainable

Every rejected, duplicate, failed, parked, ineligible, and non-contact-ready record must have an explicit reason code. Silent disappearance is unacceptable.

---

# 6. Definition of “elite” for this project

“Elite” means:

## Reliability

- One record failure does not erase successful work.
- Tasks are idempotent and retry-safe.
- Worker restart does not corrupt progress.
- Source runs resume from committed checkpoints.
- Overlapping runs are prevented or safely deduplicated.
- One source outage does not stop all connectors.

## Progressive discovery

- Repeated runs move through new pages/high-water marks.
- Checkpoint movement is visible.
- Completed pages are not pulled forever.
- Source partitions prevent one query/NAF code from monopolizing discovery.

## Explainable funnel

The system reports separate counts for:

```text
raw records
unique companies
duplicates
invalid records
ICP accepted/rejected
identity resolved/unresolved
verified domains
operational evidence
scored opportunities
contact attempts
contact dossiers
human approved
contact-ready
```

## Data integrity

- One canonical company identity.
- Official identifiers have precedence.
- Every fact has provenance and observation time.
- Contradictions are stored, not silently overwritten.
- Scoring uses the same evidence visible to operators.

## Scalable processing

- Discovery is not blocked by website latency.
- Enrichment/contact work uses separate queues.
- Queues scale independently.
- Rate budgets are source-specific.
- Expensive contact research occurs only after cheap fit gates.

## Commercial usefulness

- Prioritization matches French field-service businesses and the actual offer.
- Scoring is not generic SaaS/IT-company scoring.
- Buyer roles map to operational problems.
- Contact paths include provenance and confidence.
- Human reviewers can accept, research, park, reject, or suppress efficiently.

## Operational visibility

- Operators see last success, queue depth, oldest task, checkpoint, failures, retries, and stage yield.
- Web health and acquisition-engine health are separate.
- Logs contain correlation IDs and structured fields.
- Alerts detect stalled and zero-yield pipelines.

## Reproducibility

- A clean checkout can install and test.
- Integration tests use PostgreSQL and Redis.
- Deployment validates configuration before automation.
- Release gate proves migrations, tasks, scheduler, and basic throughput.

---

# 7. Capacity model

Design for gradual validated growth:

| Stage | Initial daily target |
|---|---:|
| Raw source records | 500–2,000 |
| Unique normalized companies | 200–800 |
| ICP-eligible companies | 75–300 |
| Domain/evidence attempts | 100–300 |
| Contact dossier attempts | 20–75 |
| Human-approved contact-ready | 5–25 |

Roll out safely:

```text
100 raw/day → 300/day → 750/day → 1,500/day
```

Each increase requires acceptable novelty, duplicate rate, failure rate, queue age, source-limit behavior, enrichment yield, and contact-ready yield.

---

# 8. Mandatory execution phases

Implement in the order below. Do not remove legacy models before runtime safety, migration, and reconciliation are established.

---

## PHASE 0 — Baseline, reproducibility, and incident diagnostics

### Objective

Establish actual behavior and make the repository reproducible before major edits.

### Required work

1. Create a current-state report covering:
   - active routes;
   - Celery tasks/queues;
   - Beat schedule;
   - adapters and real implementation status;
   - DB model map;
   - ingestion sequence;
   - scoring sequence;
   - contact selection rules;
   - operations/dashboard data sources.

2. Run and record:

```bash
python -m compileall -q app tests
ruff check app tests
pytest -q
```

3. If tests cannot start, fix development installation and dependency instructions rather than silently skipping tests.

4. Provide deterministic Compose-based integration testing with PostgreSQL and Redis. Improve the existing `test-db` profile and add test Redis if required.

5. Inspect Alembic heads. Verify a clean DB migrates to head.

6. Add safe production diagnostics for:
   - ingestion/source/pipeline runs;
   - failed work items;
   - companies created by day/play/source;
   - score/readiness distributions;
   - contact selection;
   - legacy versus normalized counts;
   - duplicate rate;
   - checkpoints;
   - Celery active/reserved/scheduled tasks.

7. Do not expose secrets in logs/reports.

### Deliverables

```text
docs/reliability/current_state.md
docs/reliability/incident_diagnostics.md
scripts/diagnose_pipeline.sh
```

Also update developer setup and record baseline test/migration results.

### Exit gate

- Clean install is documented and works.
- Compilation/lint/tests have explicit results.
- Runtime behavior is documented from code.
- Diagnostics can identify where the 11-record incident lost throughput.

---

## PHASE 1 — Critical reliability and truthfulness hotfix

This phase must be independently deployable before deeper refactoring.

### 1. Repair market-play propagation

Correct this entire chain:

```text
sourcing form/API
→ app/routers/sourcing.py
→ Celery task arguments
→ app/workers/tasks.py
→ app/jobs/ingestion.py
→ source discovery
→ persisted run config
→ persisted opportunity/company records
```

Requirements:

- `play_code` is required and validated against a registered version.
- Never substitute `DEFAULT` or a UK play when France was selected.
- The same play code/version remains visible in every run, record, score, task, and screen.
- Store requested config in a run record, including at least:

```text
play_code
play_version
mode/source connector
discovery_limit
run_contacts
skip_sirene
source partitions
requested_by
requested_at
correlation_id
application version/revision
```

- Add regression tests proving France stays France end to end.

### 2. Repair task contracts

Replace ambiguous signatures with explicit keyword arguments. The ingestion task should conceptually become:

```python
@celery_app.task(bind=True, max_retries=3)
def ingest_market_play(
    self,
    *,
    play_code: str,
    mode: str,
    discovery_limit: int,
    run_contacts: bool = False,
    skip_sirene: bool = False,
    requested_by: str | None = None,
    correlation_id: str | None = None,
) -> dict:
    ...
```

Exact implementation may use a Pydantic command/schema if superior. Do not use mutable or hidden defaults.

Propagate `contacts` and `skip_sirene`; the UI must not claim controls it does not execute.

### 3. Fix `extract_website_evidence()`

Inspect the actual `deep_enrich()` signature. Correct keyword-only invocation and the bad company-name field. The expected form is approximately:

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

Do not keep contact discovery coupled to website enrichment. Enqueue it separately only after eligibility.

Add tests that execute the task path against a database record and detect signature/field errors.

### 4. Stop transaction-wide data loss

Find every per-record exception handler that calls a whole-session rollback during a batch.

Use one of these safe patterns:

- a savepoint (`session.begin_nested()`) per record;
- one short transaction/work item per record;
- bounded chunks with truthful counter rollback.

Preferred compatibility hotfix:

```python
for record in records:
    try:
        async with session.begin_nested():
            await process_record(record)
    except KnownRecordError as exc:
        record_failure(exc)
        continue

await session.commit()
```

Requirements:

- Failure on record 37 cannot erase 1–36.
- Counters derive from committed outcomes, not pre-commit intentions.
- Every failure stores category, external ID, source, run ID, and retryability.
- Add an integration test for the failure-on-record-37 scenario.

### 5. Make source options truthful

For Companies House, BODACC, OCDS, and every source:

- If fully implemented, wire it into canonical execution with pagination, checkpoints, normalization, and tests.
- If incomplete, mark it `disabled` or `planned` in UI/API/config.
- Do not return zero with status “ok” for an unimplemented connector.
- Health must distinguish:

```text
disabled
planned
misconfigured
upstream unavailable
degraded
healthy
```

Default sourcing must be the validated French play and a real source path—not Companies House.

### 6. Make scheduler flags real

Refactor `app/workers/celery_app.py` so Beat schedules are built conditionally from `Settings`.

Expected behavior:

```python
schedule = {}
if settings.enable_scheduler and settings.enable_nightly_ingestion:
    schedule["nightly-ingestion"] = {...}
if settings.enable_scheduler and settings.enable_nightly_contact_discovery:
    schedule["nightly-contact-discovery"] = {...}
```

Add any missing typed setting such as `enable_nightly_contact_discovery` and `enable_score_reconciliation`.

Also improve Compose:

- Prefer a scheduler profile or explicit deployment variable so Beat is not blindly started.
- Startup logs must list the resolved schedules, play codes, limits, and whether outreach is disabled.
- Release checks must fail when config claims automation is disabled but schedules are registered.

### 7. Add distributed run locking

Prevent overlap by source partition/play. Use Redis locks or PostgreSQL advisory locks with a clear design.

Key concept:

```text
ingestion:{play_code}:{connector}:{partition}
```

Requirements:

- unique run ID;
- bounded lease;
- heartbeat/renewal for long work;
- safe expiry;
- explicit `skipped_overlap` outcome;
- tasks remain idempotent after lock recovery;
- tests for concurrent start attempts.

### 8. Repair operations truth

Unify run reporting immediately, even before full model migration.

If ingestion writes `IngestionRun`, operations must read it or ingestion must emit the canonical `PipelineRun`. Do not maintain two invisible runtime systems.

Remove hardcoded metrics. Compute actual counts.

Each run must expose:

```text
run ID
play/source/partition/config
status
started/finished/heartbeat
checkpoint before/after
raw discovered
records persisted
invalid
duplicates
companies created/updated
ICP accepted/rejected
enrichment queued/completed/failed
contact queued/completed/failed
retry count
error count/category
operator/correlation ID
```

### 9. Split health concepts

Keep `/ready` lightweight for web process readiness, but add an authenticated acquisition diagnostics endpoint/page.

It should report:

- DB connectivity;
- Redis connectivity;
- worker heartbeats;
- Beat heartbeat and registered schedules;
- queue depths and oldest task;
- source last success;
- checkpoint age;
- failure count;
- Reacher status if enabled;
- current degraded/stalled reasons.

Do not make the app container unhealthy merely because one external source is down; report acquisition status as `healthy`, `degraded`, or `stalled` separately.

### PHASE 1 exit gate

- Selected play/options survive the full execution path.
- One row failure does not erase others.
- Broken enrichment task is fixed and tested.
- Scheduler flags genuinely work.
- Unimplemented sources cannot report false success.
- Overlapping runs are controlled.
- Operations displays the same runs/counts workers write.
- The hotfix is migration-safe and deployable.

---

## PHASE 2 — Progressive, durable source discovery

### Objective

Stop re-reading page one forever. Persist raw source records before enrichment and continue from durable checkpoints.

### 1. Use a canonical source connector contract

Inspect `app/sources/base.py` and improve it rather than creating another parallel abstraction unless necessary.

Each connector should support concepts equivalent to:

```python
class SourceConnector(Protocol):
    code: str
    version: str

    async def validate_config(self) -> SourceHealth: ...
    async def discover(
        self,
        *,
        play: MarketPlay,
        partition: SourcePartition,
        checkpoint: dict | None,
        limit: int,
        run_id: UUID,
    ) -> DiscoveryBatch: ...
```

A `DiscoveryBatch` should include:

```text
records
checkpoint_before
checkpoint_candidate
source request metadata
rate-limit metadata
warnings
exhausted flag
```

### 2. Persist immutable raw `SourceRecord` rows

Discovery stage performs no deep enrichment or contact research.

For each source record store:

```text
connector code/version
external record ID
source partition
source URL/reference
retrieved_at
payload or normalized raw payload
payload hash
play code/version
source run ID
observed event date when applicable
```

Add unique constraints such as connector + external ID + meaningful version/event key, or connector + payload hash where no stable ID exists.

Never overwrite raw provenance destructively. If the source changes, store a new observation or version according to a documented policy.

### 3. Implement durable checkpoints

Use `SourceCheckpoint` or replace it with one canonical equivalent. A checkpoint is scoped by:

```text
connector
play version
partition
query parameters/version
```

Examples:

```text
annuaire:FIELD_OPERATIONS_FR_V2:naf:4322B → next_page=9
annuaire:FIELD_OPERATIONS_FR_V2:keyword:<hash> → next_page=5
decp:FIELD_OPERATIONS_FR_V2 → (date_attribution, external_id)
companies_house:FIELD_OPERATIONS_UK_V1:sic:<code> → start_index
```

Checkpoint requirements:

- Lock checkpoint while claiming a partition.
- Advance only after raw records and run state commit successfully.
- Failed runs leave committed checkpoint unchanged.
- Support safe reset/replay by an operator without duplicate inflation.
- Store before/after checkpoint in the run.
- Detect a successful run whose checkpoint did not move.

### 4. Partition and rotate discovery

For Annuaire/Recherche Entreprises:

- partition by play-specific NAF code and/or carefully defined keyword query;
- use round-robin or weighted rotation;
- enforce max pages per run and source budgets;
- avoid always consuming the same first partition;
- persist query version/hash;
- handle empty pages/exhaustion and periodic refresh.

For DECP:

- use a stable high-water mark based on source event date plus stable external ID;
- do not repeatedly select the same newest top-ranked companies;
- persist every unseen raw award/record first;
- aggregate company opportunity evidence downstream, not as the only raw representation;
- handle late-arriving and corrected records with a lookback window plus idempotency.

For Companies House:

- either implement SIC partitioning, pagination/start index, checkpointing, and normalization fully;
- or keep it visibly disabled. It is secondary to the French launch and must not delay France reliability.

For BODACC/OCDS:

- do not spend time implementing them until the first French sources and pipeline are stable unless the repository already contains nearly complete tested code.
- keep honest capability states.

### 5. Add source rate budgets

Use `SourceRateBudget` or a better canonical equivalent.

Track/configure:

```text
requests per second/minute/day
concurrency
burst
minimum delay
retry-after
cooldown until
quota remaining if exposed
timeout
max response bytes
```

Use exponential backoff with jitter for transient errors and honor `Retry-After`.

### 6. Add source contract tests

Use fixtures/mocks to test:

- pagination;
- malformed payloads;
- empty pages;
- duplicate records;
- rate limits;
- transient errors;
- permanent auth/config error;
- checkpoint continuation;
- changed source response shape.

### PHASE 2 exit gate

Run the same connector five times and prove:

- each successful run progresses;
- checkpoint movement is visible;
- replay creates no duplicate inflation;
- failed runs resume safely;
- raw discovery does not wait on websites/contact research;
- source status is honest.

---

## PHASE 3 — Durable stage separation and queue architecture

### Objective

Turn the monolithic ingestion loop into independent, idempotent, observable stages.

### Required queues/stages

Use clear task names and routes. Suggested structure:

```text
source-ingestion
normalization
identity-domain
website-evidence
scoring-readiness
buyer-contact
human-review-maintenance
campaigns-notifications
```

Do not create excessive microservices. Celery tasks in the same application are sufficient, but responsibilities must be separated.

### Canonical stage flow

```text
SourceRun/SourceRecord
→ normalize_source_record
→ evaluate_icp_prefilter
→ enrich_identity_domain
→ extract_operational_evidence
→ recompute_score_and_gates
→ discover_buyer_contacts (eligible only)
→ human review queue
```

### Work-item requirements

Use `WorkItem` or one canonical durable job ledger for each transition. It must store:

```text
ID
stage/task type
entity/source record ID
run/correlation ID
status
attempt count
not-before time
claimed/heartbeat/finished timestamps
idempotency key
input version
output summary
error classification
last error
```

Statuses should be explicit, e.g.:

```text
pending
claimed
running
succeeded
retry_wait
permanent_failure
blocked
cancelled
```

### Idempotency

Define idempotency keys per stage, for example:

```text
normalize:{source_record_id}:{normalizer_version}
identity:{company_id}:{identity_policy_version}:{source_freshness_key}
evidence:{company_id}:{evidence_profile_version}:{domain_observation_id}
score:{opportunity_id}:{score_profile_version}:{evidence_revision}
contact:{company_id}:{contact_policy_version}:{domain_revision}
```

Duplicate task delivery must produce one logical outcome.

### Retry classification

Implement typed failure classes or equivalent reason codes:

```text
TRANSIENT_NETWORK
RATE_LIMITED
UPSTREAM_UNAVAILABLE
AUTH_OR_CONFIG
INVALID_SOURCE_RECORD
IDENTITY_CONTRADICTION
DOMAIN_UNVERIFIED
POLICY_REJECT
PERMANENT_NOT_FOUND
CODE_DEFECT
```

Retry only retryable categories. Send exhausted tasks to `FailedWorkItem`/dead-letter state with operator controls.

### Timeouts and concurrency

- Set hard/soft Celery time limits where appropriate.
- Use source-specific concurrency.
- Never allow one website to hang a worker indefinitely.
- Bound crawling depth/pages/bytes.
- Avoid unbounded task fan-out.
- Apply backpressure when downstream queues are old or overloaded.

### Chaining

Do not use brittle chains that lose state on one failure. Persist transition state and enqueue the next stage after committed success.

### PHASE 3 exit gate

- Discovery throughput is independent of website latency.
- Failed enrichment does not fail source ingestion.
- Workers can scale independently.
- Queue depth/age and success/failure are visible by stage.
- Retrying a task does not create duplicate entities/evidence/contacts.

---

## PHASE 4 — Canonical data model and migration from dual truth

### Objective

Make normalized company/opportunity entities the canonical system without losing current production data.

### Canonical entities

Prefer and complete a normalized structure equivalent to:

```text
Company
CompanyIdentifier
CompanyName
CompanyDomain
CompanyLocation
CompanyClassification
SourceRun
SourceRecord
SourceObservation/CompanySourceLink
Opportunity
EvidenceItem
Person
PersonRole/Employment
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

Do not blindly add duplicates if similar models already exist. Consolidate deliberately.

### Identity rules

Identity precedence:

1. verified official legal identifier, such as SIREN;
2. establishment identifier, such as SIRET, linked to legal entity;
3. verified official domain as supporting—not sole—identity evidence;
4. normalized legal name + verified address only as a provisional match;
5. human conflict review when evidence contradicts.

Never use company name alone as a durable join.

### Opportunity rules

- An opportunity is scoped to a company and a market-play version.
- One company may have multiple opportunities for different plays, but duplicate active opportunities for the same company/play must be prevented.
- Store lifecycle/readiness separately from rank score.

### Evidence rules

Every `EvidenceItem` must include:

```text
company/opportunity link
evidence type/taxonomy code
observed value/summary
source URL or source-record reference
source grade/provenance
observed_at
retrieved_at
freshness/expiry
confidence
contradiction status
extractor/version
raw reference when safe
```

The evidence visible in the UI must be the evidence consumed by scoring.

### Contact rules

Separate:

- person identity;
- employment/role relationship;
- contact point;
- verification observation;
- provenance;
- suppression.

A person-company relation requires source evidence and freshness. A guessed pattern is a candidate contact point, not a verified person/contact.

### Migration sequence

1. Inventory legacy and normalized rows.
2. Add explicit legacy mapping, such as a mapping table or `legacy_prospect_id` link.
3. Backfill normalized identifiers, domains, locations, classifications, opportunities, evidence, people, and contact points.
4. Produce a reconciliation report showing:
   - mapped cleanly;
   - duplicates merged;
   - contradictions;
   - orphaned records;
   - evidence/contact losses;
   - manual-review cases.
5. Switch ingestion to normalized writes only.
6. Switch scoring/evidence/contact services to normalized IDs.
7. Switch UI/API reads.
8. Maintain a temporary read-only compatibility projection for old screens if needed.
9. Stop legacy writes.
10. Archive/remove legacy tables only in a later migration after proven reconciliation.

### Migration safety

- Use stable UUIDs/IDs.
- Add indexes and uniqueness constraints after cleaning conflicts.
- Avoid table-wide blocking operations where practical.
- Make backfills resumable and idempotent.
- Create backup instructions and verify restore.
- Do not drop data in the same release that first changes writers.

### PHASE 4 exit gate

- One canonical company identity exists.
- Every source record retains provenance.
- Every opportunity links to one company and play version.
- Every score sees canonical evidence.
- Workers/UI use consistent IDs.
- Legacy backfill reconciliation is documented and repeatable.

---

## PHASE 5 — Real market-play scoring and hard readiness gates

### Objective

Replace placeholder scoring with an explainable, play-versioned ranking and gate system suitable for French field-service acquisition.

### Separate score from gates

A numeric score ranks work. Hard gates determine eligibility. A high score cannot override missing identity, suppression, contact provenance, contradictions, or human approval.

### Suggested score dimensions

Implement configurable profiles rather than burying weights in code. A French field-operations profile may use:

```text
ICP fit                     0–25
operational complexity      0–20
trigger/timing evidence     0–15
buyer/contact-path quality  0–15
evidence/data quality       0–15
commercial relevance        0–10
risk/contradiction penalty  0 to negative value
```

Possible evidence inputs:

#### ICP fit

- relevant NAF/classification;
- active French legal entity;
- target geography;
- employee/establishment band;
- installation/maintenance/repair activity;
- recurring field-service work.

#### Operational complexity

- multiple establishments/territories;
- service contracts;
- technician hiring;
- multiple service categories;
- customer portal/forms;
- documentation/parts/certification complexity;
- field-to-office handoffs.

#### Trigger/timing

- hiring;
- expansion/new establishment;
- acquisition/leadership event;
- public-contract award;
- digital/system initiative;
- current operational change.

#### Buyer/contact quality

- correct buyer role category;
- verified current employment;
- company-controlled contact path;
- source-backed named professional address;
- secondary routing path.

#### Evidence quality

- official/primary source;
- current observation;
- multiple corroborating facts;
- verified domain;
- low contradiction level.

#### Commercial relevance

- problem plausibly relates to the intervention-to-administration wedge;
- organization has sufficient complexity/value;
- scope remains deliverable by a solo software engineer.

### Required hard gates

At minimum:

```text
active legal entity
correct jurisdiction
relevant market-play classification or evidence-based override
official identifier or explicit provisional-review state
no unresolved severe identity contradiction
verified/strongly evidenced official domain for contact inference
minimum operational evidence
appropriate buyer role or legitimate role-based routing path
contact provenance recorded
suppression check passed
compliance/professional-relevance check passed
human approval before contact-ready
```

### Persist explainability

Each score snapshot must store:

```text
profile code/version
input evidence revision
individual dimensions
weights
penalties
reason codes
evidence references
hard-gate results
total score
readiness state
calculated_at
calculator version
```

### Recalculation triggers

Recompute after:

- company identity/status change;
- evidence change;
- domain verification change;
- buyer/contact change;
- qualification decision;
- suppression change;
- play-profile version change;
- nightly reconciliation for stale/inconsistent state.

Avoid unnecessary recalculation through input revisions/idempotency.

### Readiness states

Use explicit states such as:

```text
RAW
NORMALIZED
ICP_REJECTED
IDENTITY_REVIEW
ENRICHMENT_PENDING
EVIDENCE_INSUFFICIENT
SCORED
CONTACT_RESEARCH_ELIGIBLE
CONTACT_RESEARCHED
HUMAN_REVIEW_REQUIRED
CONTACT_READY
PARKED
REJECTED
SUPPRESSED
```

Keep exact names consistent across DB, services, UI, and tests.

### Tests

Create table-driven tests for:

- ideal field-service company;
- irrelevant software company;
- inactive entity;
- strong fit but no domain;
- high score but suppressed;
- conflicting identifiers;
- role-based contact path;
- guessed email only;
- stale evidence;
- human approval transition;
- profile version recalculation.

### PHASE 5 exit gate

- No placeholder/hardcoded score logic remains in production.
- Contact research receives eligible companies.
- No record becomes contact-ready without all hard gates and approval.
- Operators can see why every record passed or failed.

---

## PHASE 6 — Identity, official-domain, and evidence quality

### Objective

Prevent bad identity/domain matches from contaminating scoring and contacts.

### Identity resolution

Create one service that:

- normalizes SIREN/SIRET and names;
- distinguishes legal entity from establishment;
- handles groups/subsidiaries;
- records aliases/trade names;
- scores candidate matches;
- stores contradictions;
- never merges automatically below a conservative threshold;
- supports operator merge/unmerge/review.

### Domain resolution hierarchy

1. official registry/company-controlled URL;
2. official legal notice or verified public profile linking domain;
3. trusted source/partner page with strong identity evidence;
4. search-derived candidate verified against page content;
5. generated candidate only as unverified research candidate.

### Domain verification evidence

Verify using several signals:

- legal/company name or brand;
- SIREN/SIRET in legal notice;
- address;
- phone;
- official email/domain relation;
- services and geography;
- group/subsidiary context.

Use bounded GET when HEAD is rejected. Handle redirects and canonical host safely. Prevent SSRF:

- block private/link-local/loopback/reserved networks;
- validate DNS before and after redirects;
- restrict schemes to HTTP/HTTPS;
- cap redirects, bytes, and time;
- reject credentialed URLs.

Store:

```text
domain candidate
verification status
confidence
signals
contradictions
source/provenance
verified_at
next_refresh_at
```

Do not treat a 200 response as company ownership proof.

### Evidence extraction

Only collect evidence relevant to the active play. Prefer explicit source-backed facts:

- maintenance/SAV/intervention services;
- emergency/on-call service;
- number/locations of branches;
- technician recruitment;
- recurring contracts;
- request/customer portals;
- downloadable intervention/certificate/forms;
- equipment/parts/document workflow clues;
- public contracts;
- digital/ERP/FSM/integration indicators.

Do not produce unsupported “pain” assertions. Store observations and hypotheses separately.

### Freshness

Define refresh windows by evidence type. Legal status and employment/contact data may require different freshness than stable service descriptions.

### PHASE 6 exit gate

- Guessed domains cannot become verified merely by responding.
- Identity contradictions are visible.
- Evidence has provenance and freshness.
- SSRF and crawler bounds are tested.
- Scoring consumes canonical verified evidence.

---

## PHASE 7 — Buyer and contact dossier engine

### Objective

Produce useful, provenance-backed contact dossiers without fabricating certainty.

### Eligibility

Run contact research only when the opportunity passes a configurable minimum fit/evidence gate. Do not spend expensive contact work on obvious rejects.

### Buyer-role resolution

Map operational wedge to role categories:

```text
planning/dispatch → operations/service director
field reports/technical validation → service/technical/quality director
billing handoff → administration/finance plus operational owner
system integration → IT/digital plus operational owner
small company-wide workflow → managing director
```

Use role taxonomy and evidence, not arbitrary job-title keyword count.

### Contact source preference

1. published named professional email on company-controlled source;
2. published role-based email;
3. verified company contact form/routing path;
4. professional switchboard;
5. manually verified professional profile/contact path;
6. generic company email.

Generated email patterns remain candidates. SMTP/Reacher results describe mailbox behavior, not proof of person identity.

### Contact model

Store each contact point separately with:

```text
person/employment link
contact type/value
source URL/reference
observed_at
verification method/result/time
confidence
candidate/verified status
professional relevance
suppression status
notes/contradictions
```

### Reacher

- If `REACHER_ENABLED=true`, startup/release validation must confirm service reachability.
- Compose instructions must use `--profile reacher` or an equivalent explicit deployment path.
- Reacher outage must degrade verification, not fabricate success.
- Never log complete sensitive contact payloads unnecessarily.

### Compliance and suppression

- Maintain suppression at contact point, person, domain/company scope as appropriate.
- Suppression always overrides score.
- Store only the minimum needed to respect objection.
- Human approval is required before the contact-ready queue.
- Automatic campaign sending stays disabled.

### Human review UX

For each candidate show:

- company identity and official identifiers;
- reason it fits;
- evidence with sources;
- score dimensions and failed gates;
- buyer role rationale;
- contact provenance/verification;
- contradictions;
- actions: accept, more research, park, reject, suppress.

### PHASE 7 exit gate

- Contacts are provenance-backed.
- Guesses are labeled.
- Suppression blocks readiness.
- Human approval is enforced server-side.
- Contact refresh/retry behavior is deterministic and observable.

---

## PHASE 8 — Operations control center and truthful product UX

### Objective

Make the product operationally useful rather than decorative.

### Required operations views

#### Funnel overview

Show counts and conversion rates for a selected date range, play, and source:

```text
raw
unique
ICP accepted
identity resolved
domain verified
evidence sufficient
scored
contact eligible
contact researched
human approved
contact-ready
```

#### Source health

For each connector/partition:

- capability state;
- last attempt/success;
- last new record;
- current checkpoint;
- checkpoint age;
- requests/rate-limit status;
- raw/new/duplicate/invalid counts;
- errors by category;
- next scheduled run.

#### Queue health

For every queue/stage:

- pending/running/retry/failed;
- oldest item age;
- throughput;
- success rate;
- worker heartbeat/concurrency;
- retry controls.

#### Run detail

- immutable config;
- timeline;
- counts by stage;
- checkpoint transition;
- failures;
- linked records/work items;
- operator/revision.

#### Failure center

- group by error category/source/task/version;
- inspect sanitized payload/context;
- retry safe items;
- dismiss permanent failures with reason;
- prevent repeated retry storms.

#### Record detail

Show canonical identity, source observations, evidence, score history, contacts, qualification history, and audit trail.

### UX truthfulness

- Do not call raw companies “qualified prospects.”
- Distinguish candidates, opportunities, contact-researched, and contact-ready.
- Do not show a green state when no new records have arrived for days.
- Every zero value must be computed, not hardcoded.
- Show denominators with percentages.

### Operator controls

Provide controlled actions for:

- run source partition now;
- pause/resume connector;
- reset/replay checkpoint with confirmation;
- retry failed work item;
- merge/review identity conflict;
- force score recalculation;
- approve/reject/suppress contact candidate.

All actions require authorization and audit logging.

### PHASE 8 exit gate

An operator can answer, from the UI:

- Did the engine run?
- Which source/partition?
- Did the checkpoint move?
- How many raw and new records were created?
- Where were records rejected?
- Are queues stalled?
- Why is a company not contact-ready?
- What can be safely retried?

---

## PHASE 9 — Performance, resilience, security, and deployment hardening

### Performance

- Add appropriate indexes for queue claims, source uniqueness, company identifiers, opportunity/play, readiness, and timestamps.
- Avoid N+1 queries in operations and review screens.
- Use keyset pagination for large tables.
- Stream/batch large source payloads; avoid loading unlimited datasets into memory.
- Keep transactions short.
- Benchmark with realistic distributions, not only uniform fake data.

### Resilience

- Celery late acknowledgment and prefetch settings must match idempotency guarantees.
- Add soft/hard task time limits.
- Add worker lost handling.
- Use heartbeat/lease recovery for work items.
- Handle Redis/DB temporary loss safely.
- Backpressure expensive queues.
- Add graceful shutdown behavior.

### Security

Review and test:

- SSRF protections in crawler/domain checks;
- authorization for operations/retry/approval actions;
- secret handling;
- safe logging;
- HTML escaping;
- CSRF where relevant;
- SQL injection protections through ORM/bound queries;
- file/import validation;
- rate limits for manual run endpoints;
- production debug disabled;
- private DB/Redis networking;
- secure cookies/trusted hosts.

### Deployment configuration

Update `.env.production.example`, `docker-compose.yml`, deployment scripts, and docs to include explicit settings for:

```text
active market play
source enablement
scheduler/individual schedules
source limits/partitions
queue concurrency
rate budgets
task timeouts
checkpoint behavior
Reacher profile
outreach disabled
health/alert thresholds
```

Validate contradictory config at startup. Examples:

- Reacher enabled but unavailable;
- nightly ingestion enabled but scheduler disabled;
- source enabled without required credentials;
- active play missing;
- contact schedule enabled while scoring/readiness is disabled.

### Backup and rollback

- Verify backup before migrations.
- Provide migration rollback/recovery instructions.
- Test restore in a disposable environment.
- Update release and rollback scripts.

### PHASE 9 exit gate

- Production config is explicit and validated.
- Security tests cover crawler and privileged operations.
- Benchmarks meet defined SLOs at staged capacity.
- Backup/restore and release rollback are documented and tested.

---

## PHASE 10 — Test system, release gates, and proof of reliability

### Objective

Prove behavior through executable tests and controlled benchmarks. A visually working UI is not acceptance.

### Unit tests required

At minimum:

- play/version propagation;
- task command validation;
- source partition selection and round-robin rotation;
- checkpoint claim/advance/failure behavior;
- source-record uniqueness and payload versioning;
- identity normalization and match decisions;
- domain verification signals and contradiction handling;
- ICP prefilter;
- evidence deduplication/freshness;
- score dimensions and profile versioning;
- every hard gate;
- readiness transitions;
- suppression precedence;
- buyer-role mapping;
- contact provenance/confidence;
- retry classification;
- idempotency keys;
- scheduler feature flags;
- operations metrics calculations.

### Integration tests required

Use real PostgreSQL and Redis containers. Do not rely only on SQLite.

Required scenarios:

1. **100 raw records:** expected unique source records and companies are created.
2. **Replay:** replaying the same discovery batch creates no duplicate inflation.
3. **Record failure isolation:** failure on record 37 does not erase 1–36 or 38–100.
4. **Retry after network failure:** task resumes without duplicate evidence or companies.
5. **Checkpoint safety:** failed run does not advance the checkpoint; successful retry does.
6. **Progressive runs:** five runs consume new pages/records instead of repeating page one.
7. **Play integrity:** selected France play remains France in every task/table/snapshot.
8. **Option integrity:** `run_contacts` and `skip_sirene` values are stored and executed.
9. **Contact scheduling:** contact research is queued only after score/gates permit it.
10. **Suppression:** suppressed person/company/contact never enters contact-ready/campaign tasks.
11. **Human approval:** no record becomes contact-ready through score alone.
12. **Operations truth:** UI/service counts match persisted run/work-item facts.
13. **Scheduler truth:** disabling schedules unregisters them.
14. **Overlap:** two simultaneous starts result in one active run and one explicit skipped/locked result.
15. **Dead letter:** exhausted retry is visible and safely retryable by operator.
16. **Migration:** existing legacy fixture data backfills without silent loss.
17. **Reconciliation:** mismatches are reported rather than hidden.
18. **UK behavior:** Companies House either works end to end or is visibly disabled.
19. **Reacher behavior:** enabled/unavailable config fails validation or shows degraded state; it never fabricates verification.
20. **Security:** crawler blocks private/reserved targets and redirect-to-private SSRF.

### Contract tests required

Fixture/mock upstream response shapes for:

- Recherche Entreprises/Annuaire;
- SIRENE/INSEE;
- DECP;
- Companies House when enabled;
- website/domain resolver;
- Reacher/email verifier.

Cover response changes, missing fields, invalid JSON, HTTP 429, 5xx, timeout, redirects, and malformed records.

### End-to-end controlled pipeline test

Create an offline fixture dataset representing French field-service companies with:

- duplicates across sources;
- establishments and parent companies;
- inactive companies;
- relevant and irrelevant NAF codes;
- verified and misleading domains;
- strong and weak operational evidence;
- source-backed and guessed contacts;
- suppression cases;
- identity contradictions.

Run it through the same canonical pipeline used in production. Assert counts at every stage and expected decisions.

### Benchmark/reliability tests

Use realistic fixture data to test at least:

```text
500 raw records
2,000 raw records
10,000 existing canonical companies for query/UI performance
```

Measure:

- source-record persistence throughput;
- normalization throughput;
- duplicate handling;
- queue drain rate;
- p50/p95 stage latency;
- DB query count/time;
- memory use where practical;
- operations page performance.

Do not make live external APIs part of the normal deterministic test suite. Create a separate opt-in live-source smoke test with tiny limits and no contact/outreach.

### Release gate script

Improve `scripts/release-gate.sh` or create a reliable equivalent. It must fail on:

- compile/lint/test failure;
- pending/multiple Alembic heads;
- unsafe production config;
- placeholder active source;
- migration failure;
- unregistered expected queues/tasks;
- scheduler mismatch;
- failed canonical fixture pipeline;
- broken readiness/diagnostics endpoint;
- uncommitted generated migration artifacts when relevant.

### PHASE 10 exit gate

- Critical behavior is covered by automated tests.
- PostgreSQL/Redis integration tests pass.
- Replay, retry, overlap, failure isolation, and migration tests pass.
- Controlled benchmark produces an explainable funnel.
- Release gate blocks known unsafe deployments.

---

# 9. File-level investigation and likely change map

Use this as a guide, but inspect current code rather than mechanically editing only these files.

## `app/config.py`

- Add typed source/scheduler/stage settings.
- Validate active play and contradictory settings.
- Add acquisition health thresholds.
- Add source-specific limits and task timeouts.
- Preserve safe production validation.

## `app/workers/celery_app.py`

- Build schedules conditionally.
- Add precise task routes for new stages.
- Add task time limits/annotations if appropriate.
- Improve failure persistence and correlation metadata.
- Avoid unsafe event-loop handling if current implementation is fragile.
- Log enabled schedules at startup.

## `app/workers/tasks.py`

- Replace ambiguous task contracts.
- Fix enrichment call/field defect.
- Introduce canonical stage tasks.
- Ensure idempotency and correct retries.
- Do not retain placeholders returning `ok`.

## `app/jobs/ingestion.py`

- Stop inline deep enrichment/contact discovery.
- Persist source runs/records.
- Fix transaction isolation.
- Remove hardcoded play/default behavior.
- Return truthful committed statistics.
- Eventually become orchestration or be replaced by source-run service.

## `app/discovery/annuaire.py`

- Add partition-aware pagination/cursors.
- Stop always restarting from first pages.
- Separate discovery from ranking/enrichment.
- Preserve source IDs and provenance.

## `app/discovery/decp.py`

- Store raw unseen records.
- Implement high-water mark plus lookback.
- Avoid repeatedly slicing the same ranked companies.
- Aggregate into evidence downstream.

## `app/discovery/enrich.py`

- Correct interface and responsibilities.
- Split identity/domain/evidence/contact behavior.
- Replace weak domain assumptions with candidate verification.

## `app/sources/*`

- Standardize connector contract.
- Mark placeholder states honestly.
- Add checkpoints, pagination, normalization, health, and contract tests for enabled sources.

## `app/models.py`

- Reconcile runtime/source/work-item models.
- Add missing uniqueness/index/provenance fields.
- Avoid continuing dual sources of truth.
- Keep migration size manageable; extracting model modules is acceptable if done safely.

## `app/services/scoring_v4.py` and scoring services

- Remove placeholder behavior.
- Consolidate into one canonical scoring/readiness engine.
- Use versioned profiles, reason codes, evidence references, and tests.

## `app/commercial.py` / `app/jobs/recalculate_scores.py`

- Remove no-op claims.
- Route all recalculation through canonical scoring.
- Add reconciliation for stale/inconsistent state.

## `app/services/identity_resolution.py`

- Make official identifiers primary.
- Add candidate/contradiction/review behavior.
- Eliminate company-name-only linking.

## `app/services/domain_verification.py`

- Implement evidence-backed domain verification and SSRF safety.
- Store verification observations and freshness.

## `app/contact_intelligence/*`

- Separate candidates, evidence, verification, and readiness.
- Make source provenance mandatory.
- Preserve conservative concurrency/timeouts.
- Do not treat SMTP result as person validation.

## `app/routers/sourcing.py`

- Propagate every operator option.
- Validate source capability and active play.
- Show real run ID/status.
- Prevent duplicate/overlapping starts.

## `app/routers/operations.py`

- Read canonical runtime data.
- Add truthful funnel/source/queue/failure views.
- Add protected operator actions with audit logs.

## `app/routers/dashboard.py`, `app/routers/prospects.py`, `app/routers/queue.py`

- Use canonical IDs and readiness states.
- Remove legacy-name joins and misleading labels.

## Templates

- Update sourcing and operations UI for capability state, progress, failures, and explainability.
- Preserve existing visual language where reasonable; functionality and clarity take priority.

## `docker-compose.yml`

- Make scheduler/Reacher activation explicit.
- Add test Redis/profile if needed.
- Add worker health checks where practical.
- Pass validated stage/source settings to all relevant services.

## `.env.production.example`

- Document safe defaults and real behavior.
- Keep scheduler/outreach disabled until release gate passes.
- Include active France play and source settings.

## Alembic

- Create ordered, reversible/recoverable migrations.
- Avoid one giant destructive migration.
- Add resumable backfill scripts where data volume makes migration code unsafe.

## `scripts/`

Add/improve:

```text
diagnose_pipeline.sh
backfill/reconcile canonical models
run controlled source smoke test
run offline pipeline benchmark
release gate
deploy/rollback verification
```

## `tests/`

- Keep useful existing tests.
- Update tests that encode broken architecture.
- Add unit/integration/contract/e2e tests required above.
- Do not delete hard cases to gain a green suite.

---

# 10. Canonical metrics and alerts

Implement metrics with play/source/stage dimensions while avoiding high-cardinality labels such as raw company IDs in Prometheus.

## Throughput

```text
raw records discovered
raw records persisted
unique companies created/updated
duplicate rate
invalid rate
ICP acceptance rate
identity resolution rate
domain verification rate
evidence completion rate
score/readiness counts
contact attempt/completion/failure
human-review acceptance
contact-ready yield
stage latency
queue depth
oldest task age
```

## Reliability

```text
last successful run per source
last new record per source
checkpoint age/movement
retry count
permanent failures
lock conflicts
source HTTP/rate-limit events
worker heartbeat
Beat heartbeat
DB/Redis status
```

## Required alert conditions

At minimum:

- no successful discovery for 26 hours when enabled;
- two consecutive successful runs create zero raw records;
- duplicate rate unexpectedly exceeds a configurable threshold such as 90%;
- checkpoint does not move for three successful runs;
- oldest queue item exceeds SLO;
- contact selection remains zero while eligible companies exist;
- task failure rate exceeds threshold;
- source health says healthy while discovery consistently fails;
- normalized/legacy reconciliation diverges during transition;
- failed work items grow continuously;
- scheduler expected but heartbeat absent.

Use application logs/operations status and Prometheus-compatible metrics if already supported. Do not require a paid external platform.

---

# 11. Data and state-machine invariants

Enforce and test invariants such as:

1. A `SourceRecord` belongs to exactly one `SourceRun` and connector identity.
2. Replaying the same external source record cannot create another canonical company.
3. A company identifier of the same official type/value cannot belong to two active companies.
4. A company/play version has at most one active canonical opportunity.
5. Evidence used in a score snapshot has stable references/revision.
6. A suppressed entity/contact cannot be contact-ready.
7. Human approval cannot be inferred from score.
8. Contact-ready cannot occur without a legitimate contact path.
9. A checkpoint advances only after durable raw persistence.
10. A succeeded work item is not executed logically twice for the same idempotency key.
11. Failed tasks preserve enough sanitized context for diagnosis.
12. Run counters equal committed outcomes.
13. Operations counts are derived from canonical persisted data.
14. Outreach remains disabled unless explicit controlled configuration and approval exist.

Use database constraints where feasible and service-level checks otherwise.

---

# 12. Coding and architecture standards

- Prefer small cohesive services and typed schemas.
- Avoid a new “god service.”
- Keep source-specific behavior inside connectors; keep canonical normalization/scoring source-agnostic.
- Use explicit enums/reason codes rather than magic strings scattered across files.
- Centralize state transitions and validate allowed transitions.
- Keep async boundaries correct; do not create unsafe event-loop reuse patterns in Celery.
- Use structured logging with run/task/correlation IDs.
- Use UTC-aware datetimes.
- Use database-generated or UUID identifiers consistently.
- Use repository/service abstractions only where they reduce duplication; do not add layers with no behavior.
- Add docstrings/comments for non-obvious invariants, checkpoint semantics, and retry logic.
- Keep functions testable with dependency injection for clients/clock where useful.
- Remove dead code only after proving it is unused or replacing it safely.
- Keep public API/route compatibility where practical; document breaking changes.

---

# 13. What not to do

Do not:

- only increase batch limits;
- enable every source simultaneously;
- perform contacts inside source ingestion;
- keep dual-writing independent models indefinitely;
- use company name as identity join;
- call placeholder adapters healthy;
- use guessed domains as verified evidence;
- use SMTP acceptance as proof a named person is correct;
- automate outreach from ingestion;
- hide errors by catching `Exception` and returning `ok`;
- count uncommitted rows as success;
- reset/delete production data;
- merge companies aggressively without evidence;
- build an elaborate new frontend while core processing remains broken;
- claim “elite” based on a seeded 10k benchmark alone;
- leave TODO placeholders on the active production path;
- create a second/third scoring engine instead of consolidation;
- add paid APIs as mandatory dependencies without explicit need/configuration;
- scrape platforms in ways that violate their rules;
- store unnecessary personal data;
- expose secrets/contact payloads in logs.

---

# 14. Deployment and activation strategy

Do not activate full automation immediately after code compiles.

Use this controlled sequence:

## Stage A — Offline and integration validation

- all tests pass;
- migration dry run passes;
- fixture pipeline passes;
- release gate passes.

## Stage B — Production hotfix with scheduler off

- deploy migrations/code;
- reconcile existing data;
- verify operations views;
- run one manual source partition with a tiny limit;
- confirm run stats/checkpoint/queues.

## Stage C — Controlled France ingestion

- active play: `FIELD_OPERATIONS_FR_V2` or the current verified equivalent;
- one validated source connector;
- 100 raw/day;
- contact research disabled initially;
- inspect novelty, duplicates, errors, identity/domain quality.

## Stage D — Enrichment/scoring

- enable identity/domain/evidence queues;
- validate score/gate distributions;
- confirm no false contact-ready records.

## Stage E — Contact research

- enable small batch only for eligible companies;
- Reacher optional and validated;
- human approval mandatory;
- outreach still disabled.

## Stage F — Scale gradually

Move 100 → 300 → 750 → 1,500 raw/day only when SLOs and quality gates pass.

Provide exact operator commands and rollback steps for each stage.

---

# 15. Acceptance criteria for the complete mission

Do not call the mission complete until all applicable criteria pass.

## Functional

- France market play propagates correctly.
- Active source discovery progressively yields new raw records.
- Checkpoints persist and resume safely.
- Raw persistence is separate from enrichment.
- Identity/domain/evidence/scoring/contact stages are durable and retry-safe.
- Scoring is field-service relevant and explainable.
- Hard gates and human approval control contact readiness.
- Operations accurately explains funnel and failures.

## Reliability

- Record failure isolation test passes.
- Replay/idempotency tests pass.
- Overlap lock test passes.
- Retry/dead-letter tests pass.
- Scheduler flags test passes.
- Queue and source health are visible.

## Data

- Canonical company/opportunity/evidence/contact model is active.
- Legacy migration/backfill is reconciled.
- No company-name-only joins remain in active paths.
- Evidence provenance/freshness exists.
- Score snapshots reference canonical evidence.

## Security/compliance

- SSRF tests pass.
- Suppression always blocks readiness/outreach.
- Privileged operations are authorized/audited.
- Outreach disabled by default.
- Secrets are not logged.

## Test/release

- compile, lint, unit, integration, contract, and controlled e2e tests pass;
- clean migration to head passes;
- production-data migration rehearsal passes on a copy/fixture;
- release gate passes;
- deployment/rollback docs are current.

## Operational proof

A controlled run must show an explainable report similar to:

```text
Run: <id>
Play: FIELD_OPERATIONS_FR_V2
Source/partition: <connector>/<partition>
Checkpoint: <before> → <after>
Raw retrieved: N
Raw persisted: N
Duplicates: N
Invalid: N
Companies created: N
Companies updated: N
ICP accepted: N
Identity/domain queued: N
Failures by category: ...
Next scheduled checkpoint: ...
```

A later pipeline report must show how those records progressed through enrichment, scoring, contact research, and human review.

---

# 16. Required project documentation and handoff files

Create/update these files with concrete truth, not generic prose:

```text
CURRENT_STATE.md
NEXT_ACTIONS.md
TEST_LOG.md
DECISION_LOG.md
CODEX_HANDOFF.md
docs/reliability/architecture.md
docs/reliability/runbook.md
docs/reliability/data_migration.md
docs/reliability/scoring_and_gates.md
docs/reliability/source_connectors.md
docs/reliability/operations_metrics.md
```

## `CURRENT_STATE.md`

Include:

- implemented architecture;
- current active source/play;
- enabled schedules;
- migration state;
- known limitations;
- safe production state.

## `NEXT_ACTIONS.md`

Only genuinely remaining work, prioritized with prerequisites. Do not list completed work.

## `TEST_LOG.md`

Include exact commands, dates, result summaries, failures, and unresolved environmental limitations.

## `DECISION_LOG.md`

Record major decisions and rejected alternatives, especially:

- canonical model choice;
- checkpoint semantics;
- lock design;
- retry/idempotency design;
- scoring profile;
- legacy migration strategy;
- source capability states.

## `CODEX_HANDOFF.md`

Enable another engineer/agent to continue without rediscovering the system. Include exact files, migrations, commands, deployment state, and risks.

## Runbook

Include:

- how to inspect health;
- how to run a source partition;
- how to pause/resume;
- how to reset a checkpoint safely;
- how to retry failures;
- how to reconcile counts;
- how to enable scheduler/Reacher;
- how to rollback;
- what alerts mean.

---

# 17. How you must work and report progress

1. Start by inspecting and writing a brief implementation sequence based on actual code.
2. Then implement; do not wait for additional confirmation unless a truly external secret or irreversible business decision is required.
3. Work in small coherent patch sets.
4. After each patch set:
   - run relevant tests;
   - record results;
   - inspect migrations;
   - update the defect register/current state.
5. Do not leave the repository half-switched between two architectures without an explicit compatibility state.
6. Prefer completing P0 reliability and progressive discovery over attempting every optional source.
7. If the complete rebuild cannot fit one execution, deliver the highest-value safe phase fully, leave tests green, and produce an exact handoff. Never pretend later phases are done.

Suggested patch/commit sequence:

```text
1. baseline and regression tests
2. P0 task/play/transaction/scheduler/operations fixes
3. source-run/source-record/checkpoint implementation
4. separated durable stage queues
5. canonical data-model migration/backfill
6. scoring and hard gates
7. identity/domain/evidence/contact quality
8. operations control center
9. performance/security/deployment hardening
10. release gate and documentation
```

Do not squash all reasoning and changes into one unreviewable giant patch if Git is available.

---

# 18. Final response format

At completion, respond with a precise engineering report containing:

## A. Executive result

- what is now genuinely fixed;
- whether the system is safe to deploy;
- whether automation is enabled or intentionally disabled;
- current reliability limitations.

## B. Root causes confirmed

For every important incident cause:

```text
confirmed/not present/changed
file(s)
old behavior
new behavior
regression test
```

## C. Files changed

Group by runtime, models/migrations, sources, scoring, UI, deployment, tests, docs.

## D. Database migrations

- revision IDs;
- schema changes;
- backfill/reconciliation result;
- rollback/recovery notes.

## E. Tests and commands

List exact commands and real results. Do not say “all tests pass” without counts/output summary.

## F. Throughput and reliability proof

Show controlled test/benchmark counts at each funnel stage, duplicate rate, failure behavior, and checkpoint progression.

## G. Deployment instructions

Provide exact commands for:

- backup;
- deploy;
- migrate;
- smoke test;
- manual controlled run;
- enabling scheduler;
- enabling Reacher if desired;
- rollback.

## H. Remaining risks

Only unresolved real risks, with severity and next action.

## I. Updated handoff files

List them and summarize their purpose.

---

# 19. Priority rule when tradeoffs occur

Use this order:

```text
data safety
→ truthfulness/observability
→ idempotency/recovery
→ progressive discovery
→ canonical identity/evidence
→ scoring/readiness correctness
→ contact quality
→ throughput
→ UI polish
→ optional sources
```

A smaller truthful engine is better than a high-volume engine producing duplicates, false domains, fabricated contacts, or invisible failures.

Begin now. Inspect the repository, verify the defects, implement the highest-priority safe path, and do not stop after producing another plan.
