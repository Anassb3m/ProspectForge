# Decision Log

## 2026-07-28 — canonical identity

`Company` and `Opportunity` are canonical. `Prospect` remains a compatibility
row temporarily and links through `company_id` and `opportunity_id`. Rejected:
company-name and guessed-domain joins, because neither is stable identity.

## 2026-07-28 — checkpoint semantics

Registry checkpoints contain the next deterministic partition and row offset.
They advance after all item outcomes and the checkpoint commit. A crash before
that commit replays the same slice; identifier and work-item idempotency make
the replay safe. Rejected: “last page requested” counters and restarting at
page one.

## 2026-07-28 — lock design

Use PostgreSQL session advisory locks keyed by play, connector, and partition.
They survive transaction commits and disappear with the DB connection.
Rejected: in-process locks in production and expiring Redis locks that can
permit overlap while a long run is still active.

## 2026-07-28 — retry and idempotency

Raw item failures use savepoints and durable failed-work rows. Enrichment work
has a payload-derived unique idempotency key and three exponential-backoff
retries. Broker enqueue failure leaves durable work `pending`; it is never
reported as dispatched.

## 2026-07-28 — scoring and contact gates

The existing score implementation is not certified for automation. Contact
discovery is rejected inside source ingestion, nightly score/contact schedules
remain off, and automatic outreach is unsupported. Rejected: treating a high
heuristic score, guessed domain, or SMTP acceptance as readiness.

## 2026-07-28 — legacy migration

Backfill only from unique SIRET/SIREN identifiers and a unique opportunity for
the same market play. Name-only rows remain unlinked for manual review.
Legacy ingestion runs are copied into `PipelineRun`; source/company/evidence
rows are not deleted or reset.

## 2026-07-28 — source capability truth

Unavailable connectors use `planned`, `misconfigured`, `degraded`, or
`upstream_unavailable`. Only a real live health check may return `healthy`.
Placeholder adapters are not executable.

## 2026-07-31 — registry plan and checkpoint versioning

The registry plan is derived from the canonical play classifications and is
fingerprinted with play version, employee tranches, partitions, and page cap.
The cursor stores plan version/fingerprint, partition, page, and row offset.
An old four-page keyword cursor is rebased because it describes a different
plan; existing companies update by SIREN/SIRET and raw/work rows remain
idempotent. Rejected: preserving an exhausted cursor for a plan that never
contained the intended NAF classifications.

## 2026-07-31 — raw stage ownership

New registry raw records link directly to canonical `PipelineRun`; legacy
`SourceRun` rows remain historical only. Raw payloads commit before
normalization and carry content hashes and processing outcomes. Rejected:
reactivating `SourceRun` as a second run ledger or claiming normalized
prospects are raw rows.

## 2026-07-31 — scale boundary

Each recoverable run remains capped at 2,000. Scale comes from progressive
upstream pagination, durable checkpoints, raw-stage replay, connection reuse,
and repeated bounded runs—not an unbounded request limit. The UI defaults to
500 and permits 2,000.

## 2026-07-31 — migration rollback

The raw-stage migration is additive and supports downgrade while no new raw
rows exist. Once such rows exist, schema downgrade refuses to erase them;
application rollback retains the additive schema. Rejected: destructive raw
record deletion to force an old schema.

## 2026-07-31 — DECP award checkpoint

DECP raw ownership is award-level, never company-aggregate-only. Initial
history moves newest-to-oldest through a backfill cursor. New awards above the
committed high-water mark are consumed oldest-unseen-first so a bounded batch
cannot jump past intermediate awards. Company aggregation happens only after
the raw commit, and replay merges evidence by statutory identity. Rejected:
re-sorting the rolling window by company score on every run.

## 2026-07-31 — raw retry and stale lease recovery

Raw retry means replaying a committed `SourceRecord`, never calling discovery
again. Operator requests report `accepted` until the reconciliation worker
commits normalization and resolves the failed-work row. Expired leases return
supported work to `pending` within its retry budget; exhausted and unknown
tasks enter the dead-letter queue. Rejected: marking a broker enqueue as
successful processing or silently resetting every running task.

## 2026-07-31 — canonical evidence projection

`EvidenceItem` owns evidence truth. Fingerprint-deduped canonical rows are
written first; `EvidenceSignal.canonical_evidence_id` creates a temporary
compatibility projection for legacy screens. Existing duplicates are retained
but only one remains active. Rejected: dual independent writers, destructive
deduplication, or scheduling score work before the evidence transaction commits.

## 2026-07-31 — identifier and domain truth

Automated company resolution uses SIREN/SIRET only. A second establishment can
attach to the same SIREN company; contradictory statutory identifiers fail
closed. Inferred websites are stored as `candidate`, never as verified company
identity. Rejected: company-name joins and treating search inference as an
official domain.

## 2026-07-31 — score and readiness separation

The French field-operations profile ranks with six explicit dimensions totaling
100 points and applies contradiction penalties. Thirteen hard gates determine
readiness independently. `CONTACT_READY` requires source-backed operational
evidence, verified statutory identity/domain, legitimate buyer/contact
provenance, suppression/compliance passes, and human approval. Rejected: a high
score overriding a gate, guessed email/SMPP acceptance as identity, or hidden
hardcoded readiness assumptions.

## 2026-08-01 — operator enrichment and contact execution

Web requests may validate, commit queue intent, and publish work, but may not
perform website crawling, registry enrichment, DNS, harvesting, or Reacher
checks inline. Operator evidence work uses the existing canonical
`PipelineRun`/`WorkItem` ledger; contact research uses its purpose-built
`ContactDiscoveryRun` ledger and executes on `buyer-contact`. Repeated requests
reuse active work. Rejected: raising proxy timeouts, returning success after a
broker exception, and running contacts inside deep/source enrichment.

## 2026-08-01 — UI identity and action truth

Links to prospect detail use the explicit `Prospect.opportunity_id` bridge;
legacy integer IDs remain only for compatibility-table mutations. Every visible
operator action must resolve to a route, perform a persisted state transition,
or say that it is intentionally disabled. Rejected: company-name lookups,
`href="#"` controls, fake reply content, hardcoded success metrics, and buttons
whose only behavior is a long synchronous network request.

## 2026-08-01 — campaign and reply safety

Campaign “activation” means preparation for manual review and does not enable
sending. Inbox classification is persisted; opt-out classification uses the
existing suppression/compliance path. Reply composition/sending stays disabled
until a real provider and compliance-approved workflow exist. Rejected:
silently activating cold outreach or presenting a placeholder sender as live.

## 2026-08-01 — browser CSRF contract

HTMX mutations send the cookie-bound token in `X-CSRF-Token`; native browser
forms add the same value as `_csrf`, which middleware validates before replaying
the request body to FastAPI. Bearer API calls retain their explicit exemption.
Rejected: exempting authenticated HTML routes, trusting the cookie without a
submitted token, putting CSRF secrets in query strings, or replacing native
navigation with a global fetch interceptor.

Cookie-authenticated `/api` mutations are subject to the same token check;
only an explicit Bearer authorization header exempts an API call. Operations
controls use the shared CSRF-aware request helper. Rejected: exempting an API
solely because its path begins with `/api/`.

## 2026-08-01 — crawler peer verification and bounded transfer

The crawler validates the connected peer address while the HTTP response is
still open, preferring the transport's stable server address and falling back
to the live socket. It streams into a hard byte budget and closes every
response. An unavailable or private peer fails closed and every rejected page
is counted by reason. Rejected: inspecting a closed socket, disabling SSRF
verification to improve yield, or buffering an unbounded body before applying
the response limit.

## 2026-08-01 — production-copy rehearsal truth

Migration rehearsal always uses an isolated database with the reserved
`prospectforge_production_rehearsal_` prefix. A supplied gzip dump is integrity
checked and hashed before restore; reconciliation and anonymization checks must
pass before the disposable database is removed. The deterministic 1,001-entity
fixture proves the migration machinery but is never reported as an actual
production-copy rehearsal. Rejected: running experimental migration commands
against production, logging database credentials, or using destructive
downgrade/reset as validation.

## 2026-08-01 — activation remains an explicit business gate

Successful live registry, DECP, and public-contact acceptance proves the manual
paths, not permission to schedule acquisition or send messages. Automatic
schedules, score reconciliation, contact discovery, and cold outreach remain
off until the actual production-copy gate, reviewed score calibration, and
separate operator approval are complete. Optional connectors/providers require
their real endpoint or credentials and acceptance evidence before registration.
