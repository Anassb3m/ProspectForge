#!/usr/bin/env bash
# Restore a verified backup while keeping application traffic stopped.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
FILE="${1:-}"
[[ -n "$FILE" && -f "$FILE" ]] || { echo "Usage: $0 backups/file.sql.gz" >&2; exit 1; }
gzip -t "$FILE"

ENV_FILE="${ENV_FILE:-.env}"
[[ -f "$ENV_FILE" ]] || { echo "ERROR: missing $ENV_FILE" >&2; exit 1; }
ENV_FILE="$(realpath "$ENV_FILE")"
export ENV_FILE
# shellcheck disable=SC1090
set -a; source "$ENV_FILE"; set +a
compose() { docker compose --env-file "$ENV_FILE" "$@"; }

echo "WARNING: this replaces database '${POSTGRES_DB:-prospectforge}'."
read -r -p "Type RESTORE to continue: " confirm
[[ "$confirm" == "RESTORE" ]] || { echo "Aborted"; exit 1; }

echo "==> Creating safety backup"
"$ROOT/scripts/backup-host.sh"
echo "==> Stopping application traffic"
compose stop app caddy
trap 'compose up -d app caddy >/dev/null 2>&1 || true' EXIT

gunzip -c "$FILE" | compose exec -T db psql \
  -U "${POSTGRES_USER:-prospectforge}" \
  -d "${POSTGRES_DB:-prospectforge}" \
  -v ON_ERROR_STOP=1

echo "==> Reapplying current migrations"
compose run --rm --no-deps app alembic upgrade head
compose up -d app caddy
trap - EXIT
echo "Restore complete"
