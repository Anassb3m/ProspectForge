#!/usr/bin/env bash
# Persist small live Registry and DECP slices into an isolated PostgreSQL DB,
# report their durable funnel/checkpoints, reconcile, then remove the database.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
RUN_ID="$(date -u +%Y%m%d%H%M%S)_$$"
ACCEPTANCE_DB="prospectforge_live_acceptance_${RUN_ID}"
TEST_DB_USER="prospectforge_test"
TEST_DB_PORT="${TEST_DB_PORT:-55439}"
TEST_REDIS_PORT="${TEST_REDIS_PORT:-56380}"
REGISTRY_LIMIT="${LIVE_REGISTRY_LIMIT:-25}"
DECP_LIMIT="${LIVE_DECP_LIMIT:-25}"
DATABASE_URL="postgresql+asyncpg://${TEST_DB_USER}:test-only-password@127.0.0.1:${TEST_DB_PORT}/${ACCEPTANCE_DB}"
REDIS_URL="redis://127.0.0.1:${TEST_REDIS_PORT}/0"
CREATED=0

compose() {
  POSTGRES_PASSWORD=test-unused docker compose --profile test "$@"
}

cleanup() {
  status=$?
  if [[ "$CREATED" -eq 1 ]]; then
    compose exec -T test-db dropdb --if-exists -U "$TEST_DB_USER" "$ACCEPTANCE_DB" \
      >/dev/null 2>&1 || true
  fi
  rm -f "/tmp/prospectforge-live-acceptance-${RUN_ID}.parquet"
  return "$status"
}
trap cleanup EXIT

compose up -d test-db test-redis
for _ in $(seq 1 30); do
  if compose exec -T test-db pg_isready -U "$TEST_DB_USER" -d prospectforge_test \
    >/dev/null 2>&1 && compose exec -T test-redis redis-cli ping \
    | grep -qx PONG; then
    break
  fi
  sleep 1
done
compose exec -T test-db createdb -U "$TEST_DB_USER" "$ACCEPTANCE_DB"
CREATED=1

export DEBUG=false ENVIRONMENT=test DATABASE_URL REDIS_URL
export CELERY_BROKER_URL="$REDIS_URL" CELERY_RESULT_BACKEND="$REDIS_URL"
export DECP_CACHE_PATH="/tmp/prospectforge-live-acceptance-${RUN_ID}.parquet"

[[ "$REGISTRY_LIMIT" =~ ^[0-9]+$ && "$REGISTRY_LIMIT" -ge 1 && "$REGISTRY_LIMIT" -le 100 ]] || {
  echo "ERROR: LIVE_REGISTRY_LIMIT must be 1..100" >&2; exit 2;
}
[[ "$DECP_LIMIT" =~ ^[0-9]+$ && "$DECP_LIMIT" -ge 1 && "$DECP_LIMIT" -le 100 ]] || {
  echo "ERROR: LIVE_DECP_LIMIT must be 1..100" >&2; exit 2;
}

"$PYTHON_BIN" -m alembic upgrade head
"$PYTHON_BIN" -m app.jobs.ingestion \
  --play-code FIELD_OPERATIONS_FR_V2 --mode registry \
  --max-companies "$REGISTRY_LIMIT" --skip-sirene
"$PYTHON_BIN" -m app.jobs.ingestion \
  --play-code FIELD_OPERATIONS_FR_V2 --mode decp \
  --days 365 --max-companies "$DECP_LIMIT" --skip-sirene
"$PYTHON_BIN" scripts/reconcile_reliability.py --fail-on-anomaly

compose exec -T test-db psql -v ON_ERROR_STOP=1 -U "$TEST_DB_USER" \
  -d "$ACCEPTANCE_DB" -c \
  "SELECT connector_code, status, raw_discovered, raw_persisted,
          duplicate_count, invalid_count, companies_created, companies_updated,
          enrichment_queued, error_count, checkpoint_before_json,
          checkpoint_after_json
     FROM pipeline_runs ORDER BY started_at;"
compose exec -T test-db psql -v ON_ERROR_STOP=1 -U "$TEST_DB_USER" \
  -d "$ACCEPTANCE_DB" -c \
  "SELECT pr.connector_code, sr.processing_status, count(*)
     FROM source_records sr
     JOIN pipeline_runs pr ON pr.id = sr.pipeline_run_id
     GROUP BY pr.connector_code, sr.processing_status
     ORDER BY pr.connector_code, sr.processing_status;"
compose exec -T test-db psql -v ON_ERROR_STOP=1 -U "$TEST_DB_USER" \
  -d "$ACCEPTANCE_DB" -c \
  "SELECT task_name, status, count(*)
     FROM work_items GROUP BY task_name, status ORDER BY task_name, status;"

echo "Persisted live-source acceptance passed; disposable database will now be removed."
