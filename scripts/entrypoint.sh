#!/usr/bin/env bash
# ProspectForge container entrypoint — wait for DB, migrate, run app.
set -euo pipefail

echo "[entrypoint] ProspectForge starting…"

# ── Wait for Postgres ───────────────────────────────────────────────────────
if [[ "${DATABASE_URL:-}" == postgresql* ]] || [[ "${DATABASE_URL:-}" == postgres* ]]; then
  # Extract host/port roughly for pg_isready-style wait via Python
  echo "[entrypoint] Waiting for database…"
  python - <<'PY'
import asyncio
import os
import sys
import time

url = os.environ.get("DATABASE_URL", "")
if not url.startswith("postgresql"):
    sys.exit(0)

# Prefer asyncpg ping via SQLAlchemy
async def wait(timeout=60):
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text
    engine = create_async_engine(url, pool_pre_ping=True)
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()
            print("[entrypoint] Database is ready")
            return
        except Exception as exc:
            last = exc
            time.sleep(1)
    print(f"[entrypoint] Database not ready: {last}", file=sys.stderr)
    sys.exit(1)

asyncio.run(wait())
PY
fi

# ── Migrations ──────────────────────────────────────────────────────────────
# Prefer Alembic; app lifespan still runs create_all as a safety net for fresh DBs.
if [[ "${RUN_MIGRATIONS:-true}" == "true" ]]; then
  echo "[entrypoint] Running Alembic migrations…"
  set +e
  MIG_OUT=$(alembic upgrade head 2>&1)
  MIG_RC=$?
  set -e
  if [[ $MIG_RC -eq 0 ]]; then
    echo "[entrypoint] Migrations applied"
  else
    echo "[entrypoint] Alembic warning (rc=$MIG_RC) — lifespan create_all will ensure tables exist"
    echo "$MIG_OUT" | tail -20
  fi
fi

# ── Uvicorn ─────────────────────────────────────────────────────────────────
# Single worker: APScheduler runs in-process; multi-worker would duplicate jobs.
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
LOG_LEVEL="${LOG_LEVEL:-info}"

echo "[entrypoint] Starting uvicorn on ${HOST}:${PORT} (1 worker)"
exec uvicorn app.main:app \
  --host "$HOST" \
  --port "$PORT" \
  --proxy-headers \
  --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-*}" \
  --log-level "$LOG_LEVEL" \
  --no-access-log
