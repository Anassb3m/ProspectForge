# Incident Diagnostics

## Confirmed low-throughput causes

The reported “about 11 records” outcome had no single reliable ledger. Code
inspection confirmed:

- UI/worker arguments were dropped, so requested play/mode/limit/options did
  not reliably reach ingestion.
- the scheduler supplied `DEFAULT`, while source discovery used a France/UK
  mixture;
- the full-mode registry branch imposed its own limit and registry keyword
  queries repeatedly fetched page one;
- per-item failures called whole-session rollback, erasing uncommitted good
  work;
- operations read `PipelineRun` while ingestion wrote `IngestionRun`;
- placeholder source health and catch-and-return-success paths hid failures.

Because the old system did not persist request configuration, checkpoints, or
stage counters, the historical incident cannot be reconstructed exactly from
synthetic counts. The patch fixes forward observability rather than inventing
an attribution.

## Diagnostic procedure

1. Run `./scripts/diagnose_pipeline.sh`.
2. Match the request correlation ID to `pipeline_runs`.
3. Compare immutable `discovery_limit` with `raw_discovered`.
4. Check checkpoint before/after and `source_exhausted`.
5. Compare created+updated+skipped+errors with discovered.
6. Inspect error categories and matching `failed_work_items`.
7. Compare enrichment work `pending/enqueued/running/completed/failed`.
8. Inspect Redis queue lengths and worker logs; worker state is not assumed.
9. Run `scripts/reconcile_reliability.py`.

The source-run total and every downstream stage are separate. A completed
source run does not claim enrichment, scoring, contact research, or outreach
completion.
