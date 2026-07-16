#!/usr/bin/env bash
# Deploy / update ProspectForge on a VPS (custom ports supported).
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  echo "Missing .env — copy the production template first:" >&2
  echo "  cp .env.production.example .env && nano .env" >&2
  exit 1
fi

# shellcheck disable=SC1091
set -a; source .env; set +a

fail=0
if [[ -z "${SECRET_KEY:-}" || "$SECRET_KEY" == CHANGE_ME* || "$SECRET_KEY" == "change-me" ]]; then
  echo "ERROR: set a real SECRET_KEY (openssl rand -hex 32)" >&2
  fail=1
fi
if [[ -z "${POSTGRES_PASSWORD:-}" || "$POSTGRES_PASSWORD" == CHANGE_ME* ]]; then
  echo "ERROR: set POSTGRES_PASSWORD (openssl rand -hex 24, alphanumerics preferred)" >&2
  fail=1
fi
if [[ -z "${ADMIN_PASSWORD:-}" || "$ADMIN_PASSWORD" == CHANGE_ME* || "$ADMIN_PASSWORD" == "changeme" ]]; then
  echo "ERROR: set a strong ADMIN_PASSWORD" >&2
  fail=1
fi
if [[ "$fail" -ne 0 ]]; then
  exit 1
fi

# URL-unsafe password chars break DATABASE_URL interpolation
if [[ "${POSTGRES_PASSWORD}" =~ [@#/:?\ %] ]]; then
  echo "ERROR: POSTGRES_PASSWORD contains URL-reserved characters (@ # / : ? %)." >&2
  echo "       Use: openssl rand -hex 24" >&2
  exit 1
fi

HTTP_PORT="${HTTP_PORT:-18080}"
HTTPS_PORT="${HTTPS_PORT:-18443}"
APP_PORT="${APP_PORT:-18081}"
POSTGRES_PORT="${POSTGRES_PORT:-15432}"
TLS_MODE="${TLS_MODE:-internal}"

echo "==> Ports plan (shared-VPS safe defaults)"
echo "    HTTP   → 0.0.0.0:${HTTP_PORT}"
echo "    HTTPS  → 0.0.0.0:${HTTPS_PORT}  (TLS_MODE=${TLS_MODE})"
echo "    App    → 127.0.0.1:${APP_PORT}"
echo "    Postgres → 127.0.0.1:${POSTGRES_PORT}"
echo

echo "==> Building"
docker compose build --pull app

echo "==> Starting stack"
docker compose up -d --remove-orphans

echo "==> Waiting for app health on 127.0.0.1:${APP_PORT}"
ok=0
for i in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:${APP_PORT}/health" >/dev/null 2>&1; then
    ok=1
    break
  fi
  sleep 2
done

if [[ "$ok" -ne 1 ]]; then
  echo "App did not become healthy. Recent logs:" >&2
  docker compose logs --tail=100 app >&2
  exit 1
fi

echo "==> Ready"
curl -sS "http://127.0.0.1:${APP_PORT}/health" || true
echo
curl -sS "http://127.0.0.1:${APP_PORT}/ready" || true
echo
docker compose ps
echo
echo "Access URLs:"
echo "  HTTP:  http://YOUR_VPS_IP:${HTTP_PORT}"
if [[ "$TLS_MODE" != "off" ]]; then
  echo "  HTTPS: https://YOUR_VPS_IP:${HTTPS_PORT}  (self-signed if TLS_MODE=internal)"
fi
echo "  Local: http://127.0.0.1:${APP_PORT}/health"
echo
echo "Firewall (example):"
echo "  ufw allow ${HTTP_PORT}/tcp"
echo "  ufw allow ${HTTPS_PORT}/tcp"
echo
echo "If you already have nginx/Caddy on 80/443, either:"
echo "  • open only ${HTTP_PORT}/${HTTPS_PORT}, or"
echo "  • set TLS_MODE=off and proxy_pass http://127.0.0.1:${APP_PORT}"
