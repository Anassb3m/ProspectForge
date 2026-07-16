#!/usr/bin/env bash
# Run Postgres backup from the VPS host (for cron).
# Install:
#   chmod +x scripts/backup-host.sh
#   crontab -e
#   15 3 * * * /opt/prospectforge/scripts/backup-host.sh >> /var/log/prospectforge-backup.log 2>&1
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "No .env" >&2
  exit 1
fi

# shellcheck disable=SC1091
set -a; source .env; set +a

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUT_DIR="${ROOT}/backups"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
mkdir -p "$OUT_DIR"
FILE="$OUT_DIR/prospectforge_${STAMP}.sql.gz"

echo "[$(date -Is)] Dumping to $FILE"
docker compose exec -T db \
  pg_dump -U "${POSTGRES_USER:-prospectforge}" -d "${POSTGRES_DB:-prospectforge}" \
    --no-owner --clean --if-exists \
  | gzip -c > "$FILE"

ls -lh "$FILE"
find "$OUT_DIR" -name 'prospectforge_*.sql.gz' -type f -mtime +"$KEEP_DAYS" -delete
echo "[$(date -Is)] Done"
