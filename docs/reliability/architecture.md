# Reliability Architecture

## Acquisition sequence

```text
authenticated request / scheduler
  -> validate explicit play + connector + limit
  -> commit immutable PipelineRun(status=queued)
  -> enqueue source-ingestion task
  -> acquire PostgreSQL advisory lock(play/connector/partition)
  -> read committed SourceCheckpoint
  -> retrieve bounded source slice
  -> commit hashed raw SourceRecord envelopes
  -> per raw item SAVEPOINT
       -> statutory identity upsert
       -> canonical Company/Opportunity link
       -> canonical EvidenceItem + linked compatibility projection
       -> idempotent enrichment WorkItem
     on failure -> FailedWorkItem
  -> commit next checkpoint
  -> dispatch pending work to website-evidence queue
  -> commit truthful run totals/status
  -> score from canonical evidence/input revision
  -> apply hard readiness gates independently from numeric rank
  -> operator evidence request commits PipelineRun + WorkItem before publish
  -> eligible contact request commits ContactDiscoveryRun before publish
```

The source task never performs contact discovery or outreach. Enrichment work
has its own status, lease, retry count, idempotency key, and dead-letter
record. Contact research has separate score, suppression, domain, freshness,
and concurrency gates.

Operator-triggered website evidence uses the same durable `WorkItem` ledger as
pipeline enrichment. Contact discovery is a distinct `ContactDiscoveryRun` on
the `buyer-contact` queue; active runs are reused, retries are bounded, and an
enqueue exception is persisted as failure rather than returned as success.
Neither stage performs network I/O in the originating HTTP request.

Website retrieval resolves and validates every destination, then verifies the
actual connected peer while its streamed response is still open. Response
bytes, pages, depth, concurrency, request time, and total run time are bounded.
Redirects are revalidated, private/unverifiable peers fail closed, and rejection
reasons are retained in adapter metrics rather than converted to success.

## Canonical ownership

- `CompanyIdentifier` owns statutory identity.
- `Company` owns canonical organization identity.
- `Opportunity` owns play-specific commercial state.
- `EvidenceItem` owns evidence content, provenance, freshness, contradiction,
  and verification state; `EvidenceSignal` is a linked legacy projection.
- `ScoreSnapshot` owns profile/calculator version, input revision, dimensions,
  penalties, evidence references, gate results, and readiness state.
- `PipelineRun`, `SourceCheckpoint`, `WorkItem`, and `FailedWorkItem` own
  operational history.
- `SourceRecord.pipeline_run_id` owns new registry raw observations;
  `SourceRun` remains legacy history and is not a second run ledger.
- `Prospect` is a temporary compatibility projection linked by foreign keys.

Display names and inferred domains are never identity joins.

## Recovery properties

- Advisory locks are connection-scoped and cannot leave an expired lease.
- Checkpoints move after committed outcomes; a crash replays the prior slice.
- Raw payloads commit before normalization; a crash can replay pending rows
  without pretending canonical company rows are raw input.
- DECP company evidence is aggregated downstream from immutable award rows;
  the award record is never replaced by only an aggregate company payload.
- Prospect identity and work idempotency turn replay into update/no-op.
- A failed record rolls back its savepoint only.
- Broker failure leaves work pending and visible.
- A fast evidence worker cannot be overwritten from a terminal run state back
  to `running` by the publishing request.
- Authenticated raw retry reads the committed source row and resolves the
  failed-work record only after normalization succeeds.
- Expired supported work leases are reclaimed under row locks; exhausted or
  unsupported rows are dead-lettered rather than silently reset.
- Run failure is persisted in a separate session and re-raised.
