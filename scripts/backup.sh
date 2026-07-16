#!/bin/sh
# Nightly (or on-demand) Postgres dump. Runs inside the backup container
# or on the host if DATABASE is reachable.
set -eu

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUT_DIR="${BACKUP_DIR:-/backups}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
USER="${POSTGRES_USER:-prospectforge}"
DB="${POSTGRES_DB:-prospectforge}"
HOST="${POSTGRES_HOST:-db}"

mkdir -p "$OUT_DIR"
FILE="$OUT_DIR/prospectforge_${STAMP}.sql.gz"

echo "[backup] Dumping $DB@$HOST → $FILE"
pg_dump -h "$HOST" -U "$USER" -d "$DB" --no-owner --clean --if-exists | gzip -c > "$FILE"
ls -lh "$FILE"

# Prune old dumps
find "$OUT_DIR" -name 'prospectforge_*.sql.gz' -type f -mtime +"$KEEP_DAYS" -print -delete 2>/dev/null || true
echo "[backup] Done (retention ${KEEP_DAYS}d)"
