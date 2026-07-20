#!/usr/bin/env bash
# Roll back to the image preserved by the previous deploy.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
ENV_FILE="${ENV_FILE:-.env}"
[[ -f "$ENV_FILE" ]] || { echo "ERROR: missing $ENV_FILE" >&2; exit 1; }
ENV_FILE="$(realpath "$ENV_FILE")"
export ENV_FILE
compose() { docker compose --env-file "$ENV_FILE" "$@"; }

docker image inspect prospectforge:rollback >/dev/null 2>&1 || {
  echo "ERROR: no prospectforge:rollback image is available" >&2
  exit 1
}

read -r -p "Roll back the application image? Type ROLLBACK: " confirm
[[ "$confirm" == "ROLLBACK" ]] || { echo "Aborted"; exit 1; }
"$ROOT/scripts/backup-host.sh"
docker tag prospectforge:rollback prospectforge:latest
compose up -d --force-recreate app caddy

APP_PORT="${APP_PORT:-18081}"
for _ in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:${APP_PORT}/ready" >/dev/null 2>&1; then
    echo "Rollback is ready"
    exit 0
  fi
  sleep 2
done
compose logs --tail=150 app >&2
echo "ERROR: rollback image did not become ready" >&2
exit 1
