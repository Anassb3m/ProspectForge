#!/usr/bin/env bash
# Fast, deterministic checks required before publishing or deploying.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PYTHON_BIN="${PYTHON_BIN:-python}"

if command -v npm >/dev/null; then
  npm ci
  npm run build:assets
else
  echo "ERROR: npm is required to reproduce frontend assets" >&2
  exit 1
fi

"$PYTHON_BIN" -m ruff check .
"$PYTHON_BIN" -m pytest -q
"$PYTHON_BIN" -m compileall -q app alembic
git diff --check

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
