#!/usr/bin/env bash
# Restore a gzipped pg_dump into the running compose Postgres.
# Usage (on VPS, from project root):
#   ./scripts/restore.sh backups/prospectforge_20260716T030000Z.sql.gz
set -euo pipefail

FILE="${1:-}"
if [[ -z "$FILE" || ! -f "$FILE" ]]; then
  echo "Usage: $0 path/to/prospectforge_YYYYMMDD.sql.gz" >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "No .env in current directory" >&2
  exit 1
fi

# shellcheck disable=SC1091
set -a; source .env; set +a

USER="${POSTGRES_USER:-prospectforge}"
DB="${POSTGRES_DB:-prospectforge}"

echo "⚠  This will overwrite database '$DB'."
read -r -p "Type YES to continue: " confirm
[[ "$confirm" == "YES" ]] || { echo "Aborted"; exit 1; }

echo "Restoring $FILE …"
gunzip -c "$FILE" | docker compose exec -T db \
  psql -U "$USER" -d "$DB" -v ON_ERROR_STOP=1

echo "Restore complete. Restart app: docker compose restart app"
