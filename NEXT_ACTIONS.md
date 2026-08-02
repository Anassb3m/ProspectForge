# Next Actions

Only unfinished work is listed.

1. **P0 — supply and rehearse an actual production copy.** No production dump
   is available in this workspace. After creating and verifying an anonymized
   backup, run
   `PYTHON_BIN=.venv/bin/python bash scripts/rehearse-production-migration.sh /path/to/backup.sql.gz`.
   The completed 1,001-entity deterministic rehearsal validates mechanics but
   is not a substitute for this data-specific gate.
2. **P0 — finish the final compatibility projection migration.** Move remaining contact/UI operational
   fields out of `Prospect`, make it a read-only compatibility projection, and
   add parity assertions before retiring legacy writes.
3. **P1 — calibrate the implemented score profile on reviewed production
   examples.** The dimensions, explainability, input revisions, penalties, and
   hard gates are implemented and table-tested. Do not enable nightly contact
   discovery until operators accept false-positive/false-negative results.
4. **P1 — validate optional provider behavior if credentials are approved.**
   Public website yield is live-validated, including a published named-person
   result. INSEE, Hunter, Reacher, and harvester credentials/services are not
   configured, so their yield, latency, failure, and suppression behavior must
   be checked separately before enablement. Reacher may add deliverability
   evidence but must never upgrade identity.
5. **P2 — activate optional connectors one at a time.** Companies House,
   BODACC, and OCDS each require real pagination, raw persistence,
   checkpoints, rate budgets, health checks, and fixtures before registration.
