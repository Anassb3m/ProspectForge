# Production-Copy Migration Rehearsal

Status: **blocked on an approved anonymized production dump**.

The deterministic PostgreSQL 16 rehearsal is complete and proves upgrade,
backfill, reconciliation, anonymization, and cleanup mechanics for 1,001 linked
entities. It is not an actual production-copy result. No production dump or
backup is present in this workspace.

## Safety contract

- Create and verify the backup through the production backup procedure.
- Transfer only an approved copy; never copy application secrets into the
  rehearsal environment.
- Run only against the disposable PostgreSQL test service. The script creates
  a unique database whose name starts with
  `prospectforge_production_rehearsal_` and removes it on exit.
- Do not downgrade, reset, truncate, or delete production data.
- Do not print database URLs or discovered contact values.

## Procedure

On the production host, create and verify the backup:

```bash
./scripts/backup-host.sh
gzip -t backups/prospectforge_YYYYMMDDTHHMMSSZ.sql.gz
sha256sum backups/prospectforge_YYYYMMDDTHHMMSSZ.sql.gz
```

Move the approved copy through the organization’s encrypted transfer process,
then run from a controlled ProspectForge checkout:

```bash
PYTHON_BIN=.venv/bin/python bash scripts/rehearse-production-migration.sh \
  /path/to/approved-production-copy.sql.gz
```

The script:

1. verifies the gzip stream and prints its SHA-256 digest;
2. creates an isolated database in the test PostgreSQL service;
3. restores with `ON_ERROR_STOP`;
4. upgrades to the single Alembic head and checks all heads are current;
5. runs strict reconciliation;
6. irreversibly replaces user/company/person/contact identifiers, disables
   copied password hashes, clears message/free-text fields, and recursively
   redacts sensitive JSON values while preserving rows and JSON shape;
7. asserts that email, password, message-body, and note redaction succeeded;
8. reruns strict reconciliation and reports structural counts;
9. drops the disposable database even when a step fails.

## Required acceptance record

Record in `TEST_LOG.md`:

- dump timestamp and SHA-256 (never credentials or contact values);
- starting and ending Alembic revisions;
- company/opportunity/prospect/source/run/work/failure/checkpoint counts;
- every reconciliation anomaly category;
- anonymization assertion result;
- application smoke result;
- cleanup result;
- activation decision.

Deployment remains blocked if restore, upgrade, reconciliation,
anonymization, smoke, or cleanup fails. The supported rollback is an
application rollback with the additive schema retained, or restore of the
verified pre-deploy backup during a maintenance window. Pipeline raw data and
checkpoints must never be deleted to force a downgrade.
