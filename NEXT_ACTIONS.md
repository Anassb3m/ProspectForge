# Next Actions

Only unfinished work is listed.

1. **P0 — certify on Python 3.12 and a production-copy fixture.** Run the
   release gate and `scripts/reconcile_reliability.py --fail-on-anomaly` on an
   anonymized production snapshot before deployment.
2. **P0 — finish canonical write consolidation.** Move mutable operational
   fields out of `Prospect`, make it a read-only compatibility projection, and
   add parity assertions before retiring legacy writes.
3. **P0 — add DECP raw records and checkpointing.** Persist immutable source
   records with content hashes and a date/record cursor; advance only after
   committed normalization.
4. **P1 — implement and calibrate the real score profile.** Persist component
   explanations, confidence, evidence freshness, hard-gate failures, and
   reconciliation history. Do not enable nightly contact discovery before
   this passes acceptance fixtures.
5. **P1 — add work recovery controls.** Add authenticated retry/requeue for
   pending and failed work, stale-lease recovery, worker heartbeats, and tests
   proving retry exhaustion and restart recovery.
6. **P1 — run controlled live-source validation.** Measure registry/DECP
   pages, duplicate rate, invalid rate, identity linkage, enrichment yield,
   latency, and upstream errors. Keep schedules off until reviewed.
7. **P2 — activate optional connectors one at a time.** Companies House,
   BODACC, and OCDS each require real pagination, raw persistence,
   checkpoints, rate budgets, health checks, and fixtures before registration.
