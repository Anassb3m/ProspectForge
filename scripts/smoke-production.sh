#!/usr/bin/env bash
# Ephemeral production-like PostgreSQL/Caddy smoke test. Data is deleted on exit.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PROJECT="prospectforge-smoke-${USER:-runner}-$$"
ENV_FILE="$(mktemp /tmp/prospectforge-smoke.XXXXXX.env)"
export ENV_FILE CADDYFILE_PATH="$ROOT/deploy/Caddyfile.internal"
export COMPOSE_ANSI=never

cleanup() {
  status=$?
  if [[ "$status" -ne 0 ]]; then
    echo "Smoke stack failed; final state and logs:" >&2
    docker compose --env-file "$ENV_FILE" -p "$PROJECT" ps >&2 || true
    docker compose --env-file "$ENV_FILE" -p "$PROJECT" logs --tail=200 >&2 || true
  fi
  docker compose --env-file "$ENV_FILE" -p "$PROJECT" down -v --remove-orphans >/dev/null 2>&1 || true
  rm -f "$ENV_FILE"
  return "$status"
}
trap cleanup EXIT

cat > "$ENV_FILE" <<EOF
HTTP_PORT=${PF_SMOKE_HTTP_PORT:-28080}
HTTPS_PORT=${PF_SMOKE_HTTPS_PORT:-28443}
APP_PORT=${PF_SMOKE_APP_PORT:-28081}
CADDY_BIND=127.0.0.1
TLS_MODE=internal
FORCE_HTTPS_COOKIES=true
DOMAIN=localhost
ACME_EMAIL=smoke@example.com
TRUSTED_HOSTS=localhost,127.0.0.1
FORWARDED_ALLOW_IPS=*
APP_NAME=ProspectForge
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=smoke-$(openssl rand -hex 32)
POSTGRES_USER=prospectforge
POSTGRES_PASSWORD=$(openssl rand -hex 24)
POSTGRES_DB=prospectforge
ADMIN_EMAIL=smoke@example.com
ADMIN_PASSWORD=smoke-$(openssl rand -hex 16)
ENABLE_SCHEDULER=false
ENABLE_NIGHTLY_INGESTION=false
RUN_MIGRATIONS=true
APP_HEALTH_INTERVAL=2s
APP_HEALTH_START_PERIOD=30s
EOF
chmod 600 "$ENV_FILE"
# Make the generated file authoritative over inherited shell variables during
# Compose interpolation (for example a host-level DEBUG value).
# shellcheck disable=SC1090
set -a; source "$ENV_FILE"; set +a

compose() { docker compose --env-file "$ENV_FILE" -p "$PROJECT" "$@"; }
compose config --quiet
if [[ "${SMOKE_SKIP_BUILD:-false}" != "true" ]]; then
  compose build app
fi
compose up -d db app caddy

APP_PORT="${PF_SMOKE_APP_PORT:-28081}"
for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:${APP_PORT}/ready" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
curl -fsS "http://127.0.0.1:${APP_PORT}/ready"
edge_ready=0
for _ in $(seq 1 30); do
  if curl -kfsS \
    --resolve "localhost:${PF_SMOKE_HTTPS_PORT:-28443}:127.0.0.1" \
    "https://localhost:${PF_SMOKE_HTTPS_PORT:-28443}/health"; then
    edge_ready=1
    break
  fi
  sleep 1
done
[[ "$edge_ready" -eq 1 ]] || { echo "HTTPS edge did not become ready" >&2; exit 1; }
compose exec -T app alembic current
compose run --rm backup
compose run --rm --no-deps --entrypoint /bin/sh backup -c \
  'set -eu; file=$(find /backups -name "prospectforge_*.sql.gz" -type f | head -n 1); test -n "$file"; gzip -t "$file"'
compose ps
echo "Production smoke test passed"
