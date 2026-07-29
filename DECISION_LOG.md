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
