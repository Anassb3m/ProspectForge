#!/usr/bin/env bash
# Fast, deterministic checks required before publishing or deploying.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PYTHON_BIN="${PYTHON_BIN:-python}"
GATE_DB="prospectforge_gate_$$"
GATE_STARTED=0
test_compose() {
  POSTGRES_PASSWORD=test-unused docker compose --profile test "$@"
}
cleanup_gate() {
  test_compose exec -T test-db dropdb --if-exists -U prospectforge_test "$GATE_DB" \
    >/dev/null 2>&1 || true
  if [[ "$GATE_STARTED" -eq 1 ]]; then
    test_compose stop test-db test-redis >/dev/null 2>&1 || true
  fi
}
trap cleanup_gate EXIT

if command -v npm >/dev/null; then
  npm ci
  npm run build:assets
else
  echo "ERROR: npm is required to reproduce frontend assets" >&2
  exit 1
fi

"$PYTHON_BIN" -m ruff check .
"$PYTHON_BIN" -m compileall -q app alembic
git diff --check

if ! test_compose ps --status running --services | grep -qx "test-db"; then
  GATE_STARTED=1
fi
test_compose up -d test-db test-redis
for _ in $(seq 1 30); do
  if test_compose exec -T test-db pg_isready \
    -U prospectforge_test -d prospectforge_test >/dev/null 2>&1 &&
    test_compose exec -T test-redis redis-cli ping | grep -qx PONG; then
    break
  fi
  sleep 1
done
test_compose exec -T test-db createdb -U prospectforge_test "$GATE_DB"
export TEST_DATABASE_URL="postgresql+asyncpg://prospectforge_test:test-only-password@127.0.0.1:${TEST_DB_PORT:-55439}/${GATE_DB}"
export TEST_REDIS_URL="redis://127.0.0.1:${TEST_REDIS_PORT:-56380}/0"
DEBUG=false ENVIRONMENT=test DATABASE_URL="$TEST_DATABASE_URL" \
  "$PYTHON_BIN" -m alembic upgrade head
DEBUG=false ENVIRONMENT=test DATABASE_URL="$TEST_DATABASE_URL" \
  "$PYTHON_BIN" scripts/reconcile_reliability.py --fail-on-anomaly
"$PYTHON_BIN" -m pytest -q

for script in scripts/*.sh; do
  bash -n "$script"
done

docker compose --env-file .env.production.example config --quiet
for mode in internal external acme; do
  docker run --rm \
    -e DOMAIN=prospects.example.com \
    -e HTTPS_PORT=18443 \
    -e ACME_EMAIL=ops@example.com \
    -v "$ROOT/deploy/Caddyfile.${mode}:/etc/caddy/Caddyfile:ro,Z" \
    caddy:2-alpine caddy validate --config /etc/caddy/Caddyfile >/dev/null
done
echo "Release gate passed"
