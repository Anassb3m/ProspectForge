# Source Connector States

| Connector | State | Notes |
|---|---|---|
| France registry | degraded until live check | Executable, bounded, progressive partition/row checkpoint |
| DECP | degraded until live check | Executable rolling-window replay; progressive raw checkpoint still pending |
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
{"partition": 12, "offset": 7}
```

It identifies the next row in the next deterministic NAF/keyword page slice.
