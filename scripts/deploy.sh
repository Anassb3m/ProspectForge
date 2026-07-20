#!/usr/bin/env bash
# Validate, back up, migrate, and deploy ProspectForge on a VPS.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: missing $ENV_FILE. Copy .env.production.example to .env first." >&2
  exit 1
fi
ENV_FILE="$(realpath "$ENV_FILE")"
export ENV_FILE

# The env file is administrator-owned input. Compose also reads the same file.
# shellcheck disable=SC1090
set -a; source "$ENV_FILE"; set +a

fail() { echo "ERROR: $*" >&2; exit 1; }
compose() { docker compose --env-file "$ENV_FILE" "$@"; }

command -v docker >/dev/null || fail "Docker is not installed"
command -v curl >/dev/null || fail "curl is not installed"
docker compose version >/dev/null || fail "Docker Compose v2 is not available"

[[ "${ENVIRONMENT:-}" == "production" ]] || fail "ENVIRONMENT must be production"
[[ "${DEBUG:-false}" == "false" ]] || fail "DEBUG must be false"
[[ -n "${SECRET_KEY:-}" && "${#SECRET_KEY}" -ge 32 && "$SECRET_KEY" != CHANGE_ME* ]] || \
  fail "set SECRET_KEY to: openssl rand -hex 32"
[[ -n "${POSTGRES_PASSWORD:-}" && "$POSTGRES_PASSWORD" != CHANGE_ME* ]] || \
  fail "set POSTGRES_PASSWORD to: openssl rand -hex 24"
[[ ! "$POSTGRES_PASSWORD" =~ [@#/:?%\ ] ]] || \
  fail "POSTGRES_PASSWORD must not contain URL-reserved characters; use a hex value"
[[ "${ADMIN_EMAIL:-}" == *@* && "$ADMIN_EMAIL" != *@prospectforge.local ]] || \
  fail "set ADMIN_EMAIL to the real operator email"
[[ -n "${ADMIN_PASSWORD:-}" && "${#ADMIN_PASSWORD}" -ge 14 && "$ADMIN_PASSWORD" != CHANGE_ME* ]] || \
  fail "ADMIN_PASSWORD must be a unique passphrase of at least 14 characters"
[[ -n "${DOMAIN:-}" && "$DOMAIN" != "prospects.example.com" ]] || fail "set DOMAIN"
[[ -n "${TRUSTED_HOSTS:-}" && "$TRUSTED_HOSTS" != "*" ]] || \
  fail "TRUSTED_HOSTS must explicitly include DOMAIN and 127.0.0.1"
[[ ",${TRUSTED_HOSTS}," == *",${DOMAIN},"* ]] || fail "TRUSTED_HOSTS must include DOMAIN"
[[ "${FORCE_HTTPS_COOKIES:-}" == "true" ]] || fail "FORCE_HTTPS_COOKIES must be true"

TLS_MODE="${TLS_MODE:-acme}"
case "$TLS_MODE" in
  acme)
    [[ "${HTTP_PORT:-80}" == "80" && "${HTTPS_PORT:-443}" == "443" ]] || \
      fail "TLS_MODE=acme requires HTTP_PORT=80 and HTTPS_PORT=443"
    CADDYFILE_PATH="$ROOT/deploy/Caddyfile.acme"
    CADDY_BIND="0.0.0.0"
    ;;
  external)
    CADDYFILE_PATH="$ROOT/deploy/Caddyfile.external"
    CADDY_BIND="127.0.0.1"
    # Keep the bundled plain-HTTP hop away from an existing proxy on 80/443.
    HTTP_PORT="${EXTERNAL_HTTP_PORT:-18080}"
    HTTPS_PORT="${EXTERNAL_HTTPS_PORT:-18443}"
    ;;
  internal)
    CADDYFILE_PATH="$ROOT/deploy/Caddyfile.internal"
    CADDY_BIND="${CADDY_BIND:-0.0.0.0}"
    ;;
  *) fail "TLS_MODE must be acme, external, or internal" ;;
esac
export TLS_MODE CADDYFILE_PATH CADDY_BIND HTTP_PORT HTTPS_PORT

chmod 600 "$ENV_FILE"
mkdir -p "$ROOT/backups" "$ROOT/.deploy"
chmod 700 "$ROOT/backups" "$ROOT/.deploy"

echo "==> Validating Compose and Caddy configuration"
compose config --quiet
compose pull --quiet db caddy
compose run --rm --no-deps caddy caddy validate --config /etc/caddy/Caddyfile

running_services="$(compose ps --status running --services 2>/dev/null || true)"
if [[ "$running_services" == *"db"* ]]; then
  echo "==> Creating pre-deploy database backup"
  "$ROOT/scripts/backup-host.sh"
fi

if docker image inspect prospectforge:latest >/dev/null 2>&1; then
  docker tag prospectforge:latest prospectforge:rollback
fi

echo "==> Building immutable application image"
APP_IMAGE=prospectforge:latest compose build --pull app

echo "==> Starting PostgreSQL"
compose up -d db

echo "==> Applying migrations before replacing the application"
compose run --rm --no-deps app alembic upgrade head

echo "==> Starting application and edge proxy"
compose up -d --remove-orphans app caddy

APP_PORT="${APP_PORT:-18081}"
echo "==> Waiting for readiness on 127.0.0.1:${APP_PORT}"
ready=0
for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:${APP_PORT}/ready" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done
if [[ "$ready" -ne 1 ]]; then
  compose logs --tail=150 app db caddy >&2
  fail "release failed readiness; previous image is tagged prospectforge:rollback"
fi

check_edge() {
  case "$TLS_MODE" in
    acme) curl -fsS "https://${DOMAIN}/health" >/dev/null 2>&1 ;;
    internal)
      curl -kfsS --resolve "${DOMAIN}:${HTTPS_PORT}:127.0.0.1" \
        "https://${DOMAIN}:${HTTPS_PORT}/health" >/dev/null 2>&1
      ;;
    external)
      curl -fsS -H "Host: ${DOMAIN}" \
        "http://127.0.0.1:${HTTP_PORT}/health" >/dev/null 2>&1
      ;;
  esac
}

edge_ready=0
for _ in $(seq 1 60); do
  if check_edge; then edge_ready=1; break; fi
  sleep 2
done
[[ "$edge_ready" -eq 1 ]] || fail "edge proxy did not become ready"

case "$TLS_MODE" in
  acme) PUBLIC_URL="https://${DOMAIN}" ;;
  internal) PUBLIC_URL="https://${DOMAIN}:${HTTPS_PORT}" ;;
  external) PUBLIC_URL="https://${DOMAIN} (through the external proxy)" ;;
esac

git rev-parse HEAD > "$ROOT/.deploy/current-git-sha" 2>/dev/null || true
compose ps
echo
echo "ProspectForge is ready: ${PUBLIC_URL}"
echo "Backup directory: $ROOT/backups"
