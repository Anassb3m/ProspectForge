# Source Connector States

| Connector | State | Notes |
|---|---|---|
| France registry | accepted manual capability; runtime health is dynamic | Persisted live run passed; bounded, raw-persisted, progressive plan/partition/page/row checkpoint |
| DECP | accepted manual capability; runtime health is dynamic | Persisted live run passed; award-level raw persistence; forward incremental high-water plus descending historical backfill cursor |
| Sirene | misconfigured/degraded | Misconfigured without key; optional during raw ingestion |
| CSV import | healthy local capability | Operator-supplied data; validation still applies |
| Manual research | healthy local capability | Human-entered, audited path |
| Companies House | misconfigured/disabled | No canonical checkpointed ingestion path in this release |
| BODACC | planned | Placeholder is not registered as executable |
| OCDS | planned | Placeholder is not registered as executable |

`healthy` is reserved for a successful real health check. Placeholder returns,
fixture fallback, missing credentials, and unimplemented pagination never
produce a healthy state.

On 2026-08-01, controlled persisted acceptance committed 25 registry and 25
DECP source rows through canonical company/opportunity/evidence and downstream
work creation with zero invalid rows, duplicates, or reconciliation anomalies.
A clean 2+2 rerun independently confirmed both checkpoint transitions. This is
release evidence for the manual capability; the operations endpoint still
reports current upstream/credential/worker state rather than a static
`healthy` label.

Registry checkpoint format:

```json
{"version": 2, "plan_fingerprint": "463bb0819cffa468", "partition": 0, "page": 11, "offset": 0}
```

It identifies the next row in the deterministic fingerprinted NAF page. A plan
change rebases an obsolete cursor rather than preserving false exhaustion.
