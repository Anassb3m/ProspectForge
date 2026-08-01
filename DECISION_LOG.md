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
