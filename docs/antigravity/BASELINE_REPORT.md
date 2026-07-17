# ProspectForge — Baseline Report (Phase 1)

**Date:** 2026-07-17  
**Branch:** `antigravity/prospectforge-production-pilot`  
**Base commit:** `3fb12fb` (main, "Harden V3 commercial workflow")

---

## Git Status

```
Branch: main → antigravity/prospectforge-production-pilot (new)
Commit: 3fb12fb03780c7bd2a72537cce4f6101455c31af
Untracked: ANTIGRAVITY_PROSPECTFORGE_MASTER_EXECUTION_PROMPT.md (master prompt, not committed)
Working tree: clean (no uncommitted changes to existing files)
```

---

## Environment

```
Python: 3.14.5
Virtual environment: .venv (active)
Package manager: pip + hatchling
```

---

## Test Suite

```
$ pytest -q
..................................................................       [100%]
66 passed in 10.50s
```

**Result: ALL 66 TESTS PASS** ✓

---

## Linting (ruff)

```
$ ruff check .
alembic/versions/004_v3_market_play.py:7:20  F401  `typing.Sequence` imported but unused
tests/test_discovery.py:196:69               E741  Ambiguous variable name: `l`
tests/test_discovery.py:197:35               E741  Ambiguous variable name: `l`
tests/test_p0_commercial.py:10:5             F401  `app.scoring_v3.normalize_signals` imported but unused
Found 4 errors. [*] 2 fixable with the `--fix` option.
```

**Result: 4 minor warnings** (2 unused imports, 2 variable naming) — no functional issues.

---

## Compilation Check

```
$ python -m compileall app tests
All files compiled successfully.
```

**Result: CLEAN** ✓

---

## Alembic Migrations

```
$ alembic heads
004 (head)

$ alembic history
003 -> 004 (head), V3 market play, evidence, qualification, tasks, suppression
002 -> 003, Acquisition intelligence fields: ICP scores, dirigeants, geo, stage
001 -> 002, Add DECP discovery / enrichment fields on prospects
<base> -> 001, Initial schema: users, prospects, outreach_events
```

**Result: 4 migrations, linear chain, head=004** ✓

---

## Docker Compose Validation

```
$ docker compose config --quiet
error while interpolating services.db.environment.POSTGRES_PASSWORD:
  required variable POSTGRES_PASSWORD is missing a value
```

**Result: EXPECTED FAILURE** — `.env` file uses SQLite for local dev and doesn't set POSTGRES_PASSWORD. Docker compose requires it. This is correct behavior — production `.env` would set it.

**Docker runtime:** Using podman emulation (`Emulate Docker CLI using podman`).

---

## Docker Build/Run

**Not attempted yet** — will be validated after implementation changes are complete.

---

## Database Status (Local)

Using SQLite (`prospectforge.db`). Schema created via `create_all()` (dev mode).

### Critical Issue: `create_all()` in Production

`database.py:init_db()` calls `Base.metadata.create_all()` unconditionally. In production:
- `entrypoint.sh` runs `alembic upgrade head` first (correct, fails hard on error)
- But `init_db()` is also called in the lifespan — this could mask migration issues by creating tables directly

**Required fix:** Disable `create_all()` in production mode.

---

## Key Findings

### Working Well
1. V3 scoring engine is comprehensive and correctly separates pain from trigger
2. Human qualification with 6 mandatory gates is server-enforced
3. Evidence fingerprint deduplication is implemented
4. CSRF protection is active with double-submit cookie
5. Login rate limiting is in place
6. Suppression table exists with email/domain/siren kinds
7. DECP discovery is play-driven with proper CPV/keyword filters
8. Entrypoint script correctly fails hard on migration failure

### Issues Found
1. **`create_all()` fallback in production** — bypasses Alembic
2. **Legacy `scoring.py` still active** — imported by `discovery/naf.py`, could overwrite V3 state
3. **`ENABLE_SCHEDULER=true` and `ENABLE_NIGHTLY_INGESTION=true` in `.env.example`** — unsafe defaults
4. **`docker-compose.yml` sets `ENABLE_SCHEDULER: true`** — should default to false
5. **`FORWARDED_ALLOW_IPS: "*"` in docker-compose** — overly permissive proxy trust
6. **Tasks not surfaced in daily queue** — created but invisible
7. **Suppression not checked at all boundaries** — missing from qualification accept, contact-ready, CSV export
8. **`logic_specification.txt` still references V2 IT/cyber concepts** — stale
9. **4 minor ruff warnings** — should be cleaned

---

## Boundary of Validation

- **Tests:** Verified — all 66 pass
- **Lint:** Verified — 4 minor warnings
- **Compilation:** Verified — clean
- **Migrations:** Schema verified (4 migrations, linear)
- **Docker build:** NOT verified (will be done after implementation)
- **Browser smoke tests:** NOT yet performed (will be done after implementation)
- **Live-source validation:** NOT yet performed
- **VPS deployment:** NOT yet performed (no SSH target or DEPLOY_NOW=yes provided)
