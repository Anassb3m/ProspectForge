#!/usr/bin/env bash
# Create an atomic, integrity-checked PostgreSQL backup from the VPS host.
set -euo pipefail
umask 077

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
ENV_FILE="${ENV_FILE:-.env}"
[[ -f "$ENV_FILE" ]] || { echo "ERROR: missing $ENV_FILE" >&2; exit 1; }
ENV_FILE="$(realpath "$ENV_FILE")"
export ENV_FILE
# shellcheck disable=SC1090
set -a; source "$ENV_FILE"; set +a

compose() { docker compose --env-file "$ENV_FILE" "$@"; }
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${BACKUP_DIR:-$ROOT/backups}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
mkdir -p "$OUT_DIR"
chmod 700 "$OUT_DIR"

FILE="$OUT_DIR/prospectforge_${STAMP}.sql.gz"
PARTIAL="${FILE}.partial"
trap 'rm -f "$PARTIAL"' EXIT

echo "[$(date -Is)] Backing up PostgreSQL to $FILE"
compose exec -T db pg_dump \
  -U "${POSTGRES_USER:-prospectforge}" \
  -d "${POSTGRES_DB:-prospectforge}" \
  --no-owner --clean --if-exists | gzip -c > "$PARTIAL"
gzip -t "$PARTIAL"
mv "$PARTIAL" "$FILE"
chmod 600 "$FILE"
find "$OUT_DIR" -name 'prospectforge_*.sql.gz' -type f -mtime +"$KEEP_DAYS" -delete
ls -lh "$FILE"
echo "[$(date -Is)] Backup complete"
