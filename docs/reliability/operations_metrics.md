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

`raw_persisted` currently remains zero because immutable raw storage is not
activated. It must not be inferred from company counts.

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

## Acquisition health

`GET /api/operations/acquisition-health` is authenticated. It reports database,
Redis, queues, work states, stale runs, latest committed run, source
capabilities, and automation flags. Worker state is deliberately `unknown`
until canonical heartbeats are implemented.
