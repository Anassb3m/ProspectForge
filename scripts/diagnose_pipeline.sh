#!/usr/bin/env bash
# Read-only production acquisition diagnostics.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
ENV_FILE="${ENV_FILE:-.env}"
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "$ENV_FILE"
  set +a
fi

compose() {
  docker compose --env-file "$ENV_FILE" "$@"
}

echo "== Compose services =="
compose ps

echo "== Application readiness =="
curl -fsS "http://127.0.0.1:${APP_PORT:-18081}/ready"
printf "\n"

echo "== Migration head =="
compose exec -T app alembic current

echo "== Canonical reconciliation =="
compose exec -T app python scripts/reconcile_reliability.py

echo "== Recent pipeline runs =="
compose exec -T db psql \
  -U "${POSTGRES_USER:-prospectforge}" \
  -d "${POSTGRES_DB:-prospectforge}" \
  -c "SELECT id, play_code, connector_code, status, raw_discovered, companies_created, companies_updated, error_count, checkpoint_before_json, checkpoint_after_json, started_at, finished_at FROM pipeline_runs ORDER BY started_at DESC LIMIT 10;"

echo "== Work item states =="
compose exec -T db psql \
  -U "${POSTGRES_USER:-prospectforge}" \
  -d "${POSTGRES_DB:-prospectforge}" \
  -c "SELECT status, task_name, count(*) FROM work_items GROUP BY status, task_name ORDER BY status, task_name;"
