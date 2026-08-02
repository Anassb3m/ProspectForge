# Operations Metrics

## Canonical run fields

Every `PipelineRun` exposes:

- immutable request configuration and application revision;
- play/version, connector, partition, requester, correlation ID;
- queued/running/completed/completed-with-errors/failed/overlap status;
- start, heartbeat, and finish timestamps;
- checkpoint before and after;
- discovered/raw-persisted/duplicate/invalid counts;
- company create/update and downstream queued/completed/failed counts;
- error count, categories, summary, and committed statistics.

`raw_persisted` is populated from pipeline-owned `SourceRecord` rows for both
France registry companies and DECP awards. DECP aggregation outcomes are
separate from award-level raw counts; values are never inferred from company
counts.

## Dashboard formulas

The dashboard now derives:

- companies imported/day from committed run creates over 30 days;
- opportunities/day from persisted opportunities over 30 days;
- qualification acceptance from accepted/(accepted+rejected);
- contact-ready yield from readiness state;
- duplicate rate from committed run duplicate/discovered totals;
- domain verification from explicitly verified website-bearing prospects;
- evidence coverage from persisted evidence;
- stale count from `last_enriched_at`;
- failed/blocked jobs from persisted run and work states.

No displayed metric is a hardcoded success count.

Contact and operator evidence state is also persisted, not inferred from a
button click. Evidence requests report the `PipelineRun`/`WorkItem` states;
contact requests report queued, retry-pending, running, not-eligible,
enqueue-failed, failed, or completed `ContactDiscoveryRun` states. Dashboard
draft, reply-classification, and contact-review counts come from `Touch`,
`OutreachEvent`, and `Prospect` queries respectively. Disabled providers and
outreach remain displayed as disabled.

## Acquisition health

`GET /api/operations/acquisition-health` is authenticated. It reports database,
Redis, queues, work states, stale work, stale runs, latest committed run, source
capabilities, raw-source states, and automation flags. Worker state is
`healthy` only when fresh queue-labelled heartbeats cover source ingestion,
identity/domain, website evidence, buyer contact, and campaigns/notifications.
Each queue has its own count/state; no heartbeat is `unknown`, and missing or
stale queue consumers are `degraded`.
