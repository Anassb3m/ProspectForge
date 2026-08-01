# Source Connector States

| Connector | State | Notes |
|---|---|---|
| France registry | degraded pending persisted production acceptance | Live connector checked; bounded, raw-persisted, progressive plan/partition/page/row checkpoint |
| DECP | degraded until persisted live check | Award-level raw persistence; forward incremental high-water plus descending historical backfill cursor |
| Sirene | misconfigured/degraded | Misconfigured without key; optional during raw ingestion |
| CSV import | healthy local capability | Operator-supplied data; validation still applies |
| Manual research | healthy local capability | Human-entered, audited path |
| Companies House | misconfigured/disabled | No canonical checkpointed ingestion path in this release |
| BODACC | planned | Placeholder is not registered as executable |
| OCDS | planned | Placeholder is not registered as executable |

`healthy` is reserved for a successful real health check. Placeholder returns,
fixture fallback, missing credentials, and unimplemented pagination never
produce a healthy state.

Registry checkpoint format:

```json
{"version": 2, "plan_fingerprint": "463bb0819cffa468", "partition": 0, "page": 11, "offset": 0}
```

It identifies the next row in the deterministic fingerprinted NAF page. A plan
change rebases an obsolete cursor rather than preserving false exhaustion.
