# ProspectForge Operator Guide

ProspectForge supports careful research and human-qualified outreach to French
field-service and technical-operations SMEs. The active play is
`FIELD_OPERATIONS_FR_V2`.

It is not an automatic lead blaster. Source discovery, enrichment, scoring,
contact research, human review, and outreach are separate stages. Automatic
cold outreach is disabled.

## Daily workflow

1. Open **Operations**. Resolve failed runs, pending work, Redis issues, and
   stale checkpoints before starting new acquisition.
2. Open **Follow-ups**. Complete operator commitments first.
3. Open **Queue**. Review evidence, identity, fit, pain, trigger, buyer, and
   contact quality.
4. Accept only when every required human gate is checked. An award is timing
   evidence, not proof of software pain.
5. Confirm the person and the contact evidence. A guessed domain, generated
   email pattern, catch-all response, or SMTP acceptance is not verified
   identity.
6. Edit and approve the message manually. Log each real event and next action.
7. Record opt-outs immediately. Suppression blocks further contact.

## Controlled acquisition

The Sourcing wizard runs only the supported France play and rejects contact
discovery inside ingestion.

For a first production check, use a bounded registry slice without Sirene:

```bash
docker compose exec -T app python -m app.jobs.ingestion \
  --play-code FIELD_OPERATIONS_FR_V2 \
  --mode registry --max-companies 500 --skip-sirene
```

Then inspect:

```bash
./scripts/diagnose_pipeline.sh
docker compose exec -T app python scripts/reconcile_reliability.py
```

The run report must explain:

- requested play, mode, limit, and partition;
- checkpoint before and after;
- records discovered;
- raw records durably persisted and processing outcomes;
- companies created and updated;
- idempotent enrichment work dispatched;
- failures by category.

`completed` means source-stage completion only. It does not mean enrichment,
scoring, contact research, qualification, or outreach completed.

After reviewing the first run, repeat the same command with 500–2,000. The
versioned checkpoint resumes at the next NAF page/row; do not reset it. An old
pre-scale checkpoint is automatically rebased because its discovery-plan
fingerprint is incompatible, while SIREN/SIRET and payload hashes keep replay
idempotent.

## Source modes

| Mode | Meaning |
|---|---|
| `registry` | Progressive NAF/keyword registry partitions |
| `decp` | Award-level raw persistence with descending history and forward incremental checkpoints |
| `full` | Splits the requested limit across DECP and registry |

Companies House, BODACC, and OCDS are not production ingestion sources in this
release. Missing credentials and placeholder adapters are never treated as
healthy.

## Contact research

Contact research is an explicit action after identity, evidence, score, and
suppression gates. It examines bounded official-company sources and records
provenance. It does not send messages.

Acceptable evidence includes:

- a person/contact published on the official company site;
- a registry person with a matching legal entity;
- a human-confirmed public professional source.

Technical delivery checks help assess a contact point but do not prove that
the person or company identity is correct.

## Human qualification

The acceptance checklist is mandatory:

- company fit confirmed;
- pain supported by evidence;
- trigger supported and current;
- buyer/role confirmed;
- contact path appropriate to the channel;
- offer match confirmed;
- suppression clear.

If a field is uncertain, choose **research more** or **park**. Do not use a high
score to bypass a gate.

## Automation

The safe default is:

```text
ENABLE_SCHEDULER=false
ENABLE_NIGHTLY_INGESTION=false
ENABLE_NIGHTLY_CONTACT_DISCOVERY=false
ENABLE_SCORE_RECONCILIATION=false
ENABLE_RETENTION_SWEEP=false
OUTREACH_ENABLED=false
```

Scheduler activation is an operations decision after a controlled live-source
run, backup, reconciliation, and review. See
[`docs/reliability/runbook.md`](docs/reliability/runbook.md).

## Incident handling

Do not retry blindly or reset data.

1. Match the correlation ID and run ID.
2. Inspect the checkpoint and committed counters.
3. Classify failed work and determine whether it is retryable.
4. Fix credentials, upstream availability, or invalid data.
5. Preserve the failed-work row.
6. Replay the exact bounded partition only when idempotency is verified.

For a retryable registry/DECP normalization failure, use **Retry** in
`/operations`; it replays the persisted raw record and does not rediscover the
source. Use **Recover stale work** for expired enrichment leases. Both actions
report queue acceptance first; verify the final durable status afterward.

See [`docs/reliability/incident_diagnostics.md`](docs/reliability/incident_diagnostics.md).

## Compliance

- retain `data_source` and evidence provenance;
- set `informed_at` before a real first send;
- log outreach events append-only;
- honor opt-out and suppression immediately;
- never scrape or automate LinkedIn;
- never auto-send cold outreach from discovery or enrichment.
