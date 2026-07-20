#!/usr/bin/env bash
# Generate a shell/Compose-safe production .env with strong random secrets.
set -euo pipefail
umask 077

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DOMAIN="${1:-}"
ADMIN_EMAIL="${2:-}"
TLS_MODE="${3:-acme}"

if [[ -z "$DOMAIN" || -z "$ADMIN_EMAIL" ]]; then
  echo "Usage: $0 DOMAIN ADMIN_EMAIL [acme|external|internal]" >&2
  exit 1
fi
[[ "$DOMAIN" =~ ^[A-Za-z0-9.-]+$ ]] || { echo "Invalid domain or IP" >&2; exit 1; }
[[ "$ADMIN_EMAIL" =~ ^[^[:space:]@]+@[^[:space:]@]+$ ]] || {
  echo "Invalid admin email" >&2
  exit 1
}
[[ "$TLS_MODE" =~ ^(acme|external|internal)$ ]] || { echo "Invalid TLS mode" >&2; exit 1; }
[[ ! -e .env ]] || { echo "ERROR: .env already exists; refusing to overwrite it" >&2; exit 1; }
command -v openssl >/dev/null || { echo "ERROR: openssl is required" >&2; exit 1; }

case "$TLS_MODE" in
  acme)
    HTTP_PORT=80; HTTPS_PORT=443; CADDY_BIND=0.0.0.0
    CADDYFILE_PATH=./deploy/Caddyfile.acme
    ;;
  external)
    HTTP_PORT=18080; HTTPS_PORT=18443; CADDY_BIND=127.0.0.1
    CADDYFILE_PATH=./deploy/Caddyfile.external
    ;;
  internal)
    HTTP_PORT=18080; HTTPS_PORT=18443; CADDY_BIND=0.0.0.0
    CADDYFILE_PATH=./deploy/Caddyfile.internal
    ;;
esac

SECRET_KEY="$(openssl rand -hex 32)"
POSTGRES_PASSWORD="$(openssl rand -hex 24)"
ADMIN_PASSWORD="$(openssl rand -hex 20)"

cat > .env <<EOF
HTTP_PORT=$HTTP_PORT
HTTPS_PORT=$HTTPS_PORT
APP_PORT=18081
CADDY_BIND=$CADDY_BIND
TLS_MODE=$TLS_MODE
CADDYFILE_PATH=$CADDYFILE_PATH
FORCE_HTTPS_COOKIES=true
DOMAIN=$DOMAIN
ACME_EMAIL=$ADMIN_EMAIL
TRUSTED_HOSTS=$DOMAIN,127.0.0.1,localhost
FORWARDED_ALLOW_IPS=*

APP_NAME=ProspectForge
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=$SECRET_KEY

POSTGRES_USER=prospectforge
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_DB=prospectforge

ADMIN_EMAIL=$ADMIN_EMAIL
ADMIN_PASSWORD=$ADMIN_PASSWORD
ACCESS_TOKEN_EXPIRE_MINUTES=1440

ENABLE_SCHEDULER=false
ENABLE_NIGHTLY_INGESTION=false
RUN_MIGRATIONS=true
BACKUP_KEEP_DAYS=14

INSEE_API_KEY=
SIRENE_DELAY_SECONDS=2.1
DECP_DAYS_BACK=120
DECP_MAX_COMPANIES=150
DECP_CACHE_PATH=/app/data/decp_cache.parquet
DECP_CACHE_HOURS=20
INGESTION_RUN_CONTACTS=false
REACHER_ENABLED=false
REACHER_URL=http://reacher:8080
HARVESTER_ENABLED=false
EOF
chmod 600 .env

echo "Created $ROOT/.env with mode 600"
echo "Admin email: $ADMIN_EMAIL"
echo "Initial admin password: $ADMIN_PASSWORD"
echo "Store that password now, then run: ./scripts/deploy.sh"
