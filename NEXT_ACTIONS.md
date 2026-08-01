# Next Actions

Only unfinished work is listed.

1. **P0 — rehearse on a production-copy fixture.** Run the
   release gate and `scripts/reconcile_reliability.py --fail-on-anomaly` on an
   anonymized production snapshot before deployment.
2. **P0 — finish the final compatibility projection migration.** Move remaining contact/UI operational
   fields out of `Prospect`, make it a read-only compatibility projection, and
   add parity assertions before retiring legacy writes.
3. **P1 — calibrate the implemented score profile on reviewed production
   examples.** The dimensions, explainability, input revisions, penalties, and
   hard gates are implemented and table-tested. Do not enable nightly contact
   discovery until operators accept false-positive/false-negative results.
4. **P1 — run controlled persisted live-source validation.** The registry connector has
   returned 250 unique live records; next measure registry/DECP
   pages, duplicate rate, invalid rate, identity linkage, enrichment yield,
   latency, and upstream errors in a production-copy database. Keep schedules
   off until reviewed.
5. **P2 — activate optional connectors one at a time.** Companies House,
   BODACC, and OCDS each require real pagination, raw persistence,
   checkpoints, rate budgets, health checks, and fixtures before registration.
