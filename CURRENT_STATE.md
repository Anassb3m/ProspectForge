# Current State — Reliability, Canonical Evidence, and Scale Rebuild

Updated: 2026-08-01

## UI, enrichment, and contact reliability patch

- Operator evidence enrichment now commits a `PipelineRun` and idempotent
  `WorkItem` rows before broker publication. Broker failures leave work
  `pending`; accepted work becomes `enqueued`; the evidence worker updates
  completion/failure counts and closes the run when all items terminate.
- Contact discovery is no longer executed inside an HTTP request. The operator
  action commits a `ContactDiscoveryRun(status=queued)` first, deduplicates
  repeated clicks, dispatches to `buyer-contact`, and records enqueue failure,
  retry-pending, terminal failure, not-eligible, and completed states.
- Evidence enrichment and contact research are separate stages. Source
  ingestion and deep enrichment cannot request contacts. Guessed addresses and
  SMTP acceptance remain review-only and never establish person identity.
- All primary authenticated pages are covered by a route-render smoke test.
  Broken dashboard destinations now resolve, sourcing/queue links use the
  explicit opportunity bridge, Kanban movement has a real endpoint, and inbox,
  campaign, and draft controls mutate persisted state instead of acting as
  placeholders.
- Native browser forms now participate in the double-submit CSRF contract via
  a cookie-bound `_csrf` field. The middleware safely replays parsed request
  bodies to FastAPI; HTMX continues to use the CSRF header. This closes the
  authenticated-button 403 path without exempting browser mutations.
- Dashboard contact, draft, reply-classification, and provider/automation
  values are database/configuration derived. Automatic reply sending and cold
  outreach are explicitly disabled.

## Implemented architecture

- `PipelineRun` is the canonical ingestion-run ledger. The immutable request is
  committed before Celery enqueue and includes play/version, connector mode,
  limit, source partition, contact/Sirene choices, requester, correlation ID,
  timestamp, and application revision.
- PostgreSQL session advisory locks serialize each
  `play/connector/partition`. A competing run exits as `skipped_overlap`.
- Registry discovery reads the active V2 play's
  `classifications.include_codes`, follows the upstream `total_pages`, and
  advances a versioned plan/partition/page/row checkpoint only after item
  outcomes and failed-work records commit. A changed or legacy plan cursor is
  safely rebased and replayed through identifier idempotency.
- Each source record uses a nested transaction. A bad item enters
  `failed_work_items`; it cannot roll back previously committed items.
- Registry and DECP ingestion commit immutable pipeline-owned raw payload
  envelopes before normalization, then create idempotent
  `WorkItem` rows. Deep enrichment runs on the `website-evidence` queue with
  three bounded retries. Contact discovery is never run inside source
  ingestion.
- Retryable registry/DECP normalization failures can be reconciled from their
  persisted raw rows without rediscovery. Expired work leases are reclaimed
  under row locks; exhausted or unsupported work is dead-lettered once.
- Normalized `Company`/`Opportunity` records are the canonical identity and
  opportunity records. The legacy `Prospect` compatibility row links through
  explicit `company_id` and `opportunity_id`; company names are not joins.
- Statutory SIREN/SIRET identifiers are the only automated company joins.
  Missing establishments are attached to the existing legal entity; a
  SIREN/SIRET contradiction is rejected and marked for identity review.
- `EvidenceItem` is the canonical evidence writer. `EvidenceSignal` is a
  linked compatibility projection. Fingerprints, source record IDs,
  extractor versions, verification state, freshness, strength, and
  contradiction state are retained.
- The field-operations score uses the configured 25/20/15/15/15/10 profile,
  persists input revisions and evidence references, and applies 13 hard
  gates. Numeric score never overrides identity, domain, suppression,
  provenance, compliance, or human-approval failures.
- Celery Beat schedules are generated only from explicit feature flags. The
  Compose scheduler profile is not started by a normal deploy.
- `/api/operations/acquisition-health` and `/operations` expose committed raw,
  normalized, checkpoint, work, queue, error, source-capability, automation,
  and queue-specific worker-heartbeat state.
- Authenticated operations actions enqueue raw reconciliation and stale-work
  recovery. They report broker acceptance only; resolution is recorded only
  after durable processing succeeds.

## Active source and play

- Active mutation play: `FIELD_OPERATIONS_FR_V2`.
- Enabled manual connectors: France registry and DECP.
- Companies House sourcing: disabled until pagination, checkpoints, canonical
  identity, and production validation exist.
- BODACC and OCDS: planned, not executable and never reported healthy.
- Sirene: `misconfigured` without `INSEE_API_KEY`; otherwise still requires a
  live health check.
- Live registry check on 2026-07-31: the seven intended NAF segments exposed
  7,108 active companies in the configured employee tranches. The application
  connector returned 250/250 unique SIRENs, carried 250 raw payloads, advanced
  to page 11, and did not report exhaustion.
- Persisted live acceptance on 2026-08-01 completed for both enabled sources.
  A 25-registry/25-DECP run committed 50 raw rows, companies, opportunities,
  evidence items, and downstream work with no invalid rows, duplicates, or
  reconciliation anomalies. A clean end-to-end rerun at 2+2 proved both
  checkpoints move and the report remains reproducible.
- The website crawler now validates the connected peer while the streamed
  response is still open, bounds response bytes during transfer, and fails
  closed when the peer cannot be verified. Live public-site checks produced
  generic published contacts and a named buyer contact with provenance; a
  site returning HTTP 403 is now classified truthfully instead of crashing.

## Automation state

All schedules are intentionally disabled by default:

```text
ENABLE_SCHEDULER=false
ENABLE_NIGHTLY_INGESTION=false
ENABLE_NIGHTLY_CONTACT_DISCOVERY=false
ENABLE_SCORE_RECONCILIATION=false
ENABLE_RETENTION_SWEEP=false
OUTREACH_ENABLED=false
```

Automatic cold outreach is unsupported and production validation rejects
`OUTREACH_ENABLED=true`.

## Migration and reconciliation state

- Single Alembic head: `pfscale03_20260731` (the accidental second head through
  `76aae9630f93` is now in the same linear chain).
- PostgreSQL 16 clean upgrade passed. The isolated, anonymized
  production-shaped rehearsal from `pfscale02_20260731` migrated 1,001 linked
  companies/opportunities/prospects to `pfscale03_20260731`, mapped the seeded
  legacy signal, retained its deliberate duplicate evidence, and reported zero
  identifier, orphan, projection, or duplicate-active-fingerprint anomalies.
- The migration is additive. Once pipeline-owned raw records exist, downgrade
  deliberately refuses to discard them; application rollback keeps the
  additive schema in place.
- Reconciliation reports company/opportunity identity, evidence projection,
  inactive legacy duplicates, contacts retained, run/work state, and manual
  review cases. `--fail-on-anomaly` rejects orphaned evidence/opportunities,
  duplicate active fingerprints/identifiers, and mappable unmapped evidence.
- This UI/contact patch is schema-compatible and adds no Alembic revision. The
  single head remains `pfscale03_20260731`; the existing additive migration and
  reconciliation contract is unchanged.

## Safe production state

This is an automation-disabled release candidate. The deterministic
production-shaped migration, live source execution, live public-contact yield,
and Python 3.12 runtime are certified. Deployment still requires a verified
production backup and rehearsal against that actual production copy; no such
dump is present in this workspace. Manual progressive runs of up to 2,000
records are supported and resume from durable checkpoints. This is not
approval for automated cold outreach.

## Known limitations

- The compatibility `Prospect` row still projects mutable company/contact
  fields for old screens. Canonical identity, opportunity, evidence, and score
  truth are explicit, but removing the remaining compatibility writes requires
  a later UI/contact migration and is not represented as complete.
- DECP persists award-level raw records before company aggregation. Its
  checkpoint combines a forward `(event date, external award ID)` high-water
  mark with a descending historical backfill cursor, so bounded runs neither
  repeat the newest companies nor miss incremental awards.
- Scoring and hard gates are implemented, but nightly score reconciliation and
  contact discovery remain intentionally off until production evidence/domain
  quality and compliance decisions are reviewed.
- Celery ingestion has three bounded exponential-backoff retries. Registry and
  DECP raw normalization replay and enrichment work are idempotent. Operators
  can retry classified raw failures and recover stale leases from `/operations`.
- Worker heartbeats are durable and queue-labelled. The health API evaluates
  ingestion, identity, website-evidence, buyer-contact, and campaign queues
  separately; a missing worker degrades only the affected capability.
- The 2,000-record progression proof uses deterministic source fixtures; the
  live connector proof is 250 records, not a synthetic production count.
- The final release gate passes 166 PostgreSQL tests plus lint, compile,
  migration, reconciliation, frontend, shell, Compose, and Caddy checks. The
  complete suite also passes in the production Python 3.12 image
  (`166 passed`; Python 3.12.13), and the disposable HTTPS production smoke
  test passes.
- Public-site live validation produced source-backed generic and named-person
  contact evidence without provider credentials. `INSEE_API_KEY` and
  `HUNTER_API_KEY` remain unconfigured and Reacher/harvester remain disabled;
  provider-specific yield and latency therefore require approved credentials.
