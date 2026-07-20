# Deployment record

Status: **not deployed**. `DEPLOY_NOW` is `no`.

## Repository record

- Starting branch: `antigravity/prospectforge-production-pilot`
- Starting commit: `5a3123f10930cd9120456d4d3055e3012896e51d`
- New migration: `pfci60_20260720` after local head `005`
- Production-reported revision: `pfcc50_20260720` (unavailable here; mismatch must be resolved)
- Reacher image: `reacherhq/backend:v0.11.7`, private Compose network, no host port
- Locally built application image: `b46a80197c9a9d1da7016c9f844ffb630eb6a2876ad76a0c696a67b1d028408c`

## Local release evidence (2026-07-20)

- Full PostgreSQL-backed suite: 140 passed, one third-party deprecation warning.
- Release gate: passed, including assets, npm audit, lint, compile, Compose, and Caddy modes.
- Fresh migration, downgrade to `005`, and re-upgrade to `pfci60_20260720`: passed.
- Production-like smoke: app and database readiness, Caddy, migration-head check, backup, and restore passed.
- No production service or production data was accessed; these results do not authorize deployment.

## Pre-deploy checklist

1. Obtain and inspect `/opt/prospectforge` status/diff without exposing secrets or contact data.
2. Preserve accepted VPS changes as a protected evidence patch.
3. Rebase or create a merge migration so exactly one Alembic head follows the real production revision.
4. Show changed files, tests, migration results, pilot metrics, limitations, and rollback.
5. Confirm no secrets, cache, crawl data, dumps, or personal-data exports are in Git.
6. Confirm automated outreach and LinkedIn automation remain absent.
7. Create and verify a PostgreSQL backup.
8. Record image ID, Git SHA, sent-event count, scheduler jobs, and Reacher privacy.

## Rollback

Application rollback uses the existing `scripts/rollback.sh` image record. Schema rollback to `005` drops only the new normalized contact tables and returns `prospects.contact_confidence` to length 20; before doing so, restore the pre-deploy backup if production has begun collecting dossier data. Never downgrade across an unreconciled `pfcc50_20260720` lineage.
