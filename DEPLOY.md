# ProspectForge production deployment

The supported production stack is **Caddy → FastAPI → PostgreSQL 16**, managed
with Docker Compose. PostgreSQL is private to the Compose network, the app is
also bound to host loopback for health checks, and only Caddy is public.

Recommended VPS: Ubuntu 24.04 LTS, 2 vCPU, 4 GB RAM, 20 GB disk, and a domain
whose `A`/`AAAA` record already points to the VPS.

## 1. Prepare the VPS

Run as a sudo-capable user:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git openssl ufw
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
```

Log out and back in, then verify:

```bash
docker version
docker compose version
```

For the recommended trusted-certificate deployment, allow SSH and web traffic:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
```

## 2. Clone the release

```bash
sudo mkdir -p /opt/prospectforge
sudo chown "$USER":"$USER" /opt/prospectforge
git clone https://github.com/Anassb3m/ProspectForge.git /opt/prospectforge
cd /opt/prospectforge
git switch main
```

Production should track `main`, not a development branch.

## 3. Generate the production configuration

The generator creates shell-safe random secrets, locks `.env` to mode `600`,
and prints the initial admin password once:

```bash
./scripts/configure-production.sh prospects.yourdomain.com you@yourdomain.com acme
```

Store the printed admin password in your password manager. Optionally add the
free INSEE key afterward:

```bash
nano .env
# INSEE_API_KEY=...
```

The app refuses to start when production uses a weak secret, SQLite, debug
mode, wildcard trusted hosts, insecure cookies, or an unsupported TLS mode.

## 4. Deploy

```bash
./scripts/deploy.sh
```

The deploy command:

1. validates secrets, Compose, and the selected Caddy configuration;
2. creates an atomic database backup when an existing database is running;
3. preserves the current image as `prospectforge:rollback`;
4. builds the new non-root/read-only image;
5. starts PostgreSQL and applies Alembic migrations before replacing the app;
6. waits for database-backed readiness and verifies the HTTPS edge.

Verify afterward:

```bash
curl -fsS http://127.0.0.1:18081/ready
docker compose ps
docker compose logs --tail=100 app caddy db
```

Open `https://prospects.yourdomain.com` and sign in with the generated admin
credentials.

## TLS modes

### `acme` — recommended public production

- Requires a real DNS name pointing to this VPS.
- Requires public ports 80 and 443.
- Caddy obtains and renews a publicly trusted certificate.
- Generated with:

```bash
./scripts/configure-production.sh prospects.yourdomain.com you@yourdomain.com acme
```

### `external` — behind an existing HTTPS proxy

Use this when nginx, Caddy, Traefik, or a hosting panel already owns ports
80/443:

```bash
./scripts/configure-production.sh prospects.yourdomain.com you@yourdomain.com external
./scripts/deploy.sh
```

The bundled plain-HTTP hop binds only to `127.0.0.1:18080`. Example nginx
upstream:

```nginx
location / {
    proxy_pass http://127.0.0.1:18080;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto https;
}
```

Only the existing public proxy should expose 80/443.

### `internal` — private/admin deployment

This uses Caddy's internal CA and custom ports 18080/18443. Browsers will not
trust it until you install Caddy's root certificate. Do not present it as a
public trusted website.

```bash
./scripts/configure-production.sh prospect-vps.internal you@example.com internal
./scripts/deploy.sh
```

## Backups

Create and integrity-check a backup manually:

```bash
./scripts/backup-host.sh
ls -lh backups/
```

Install a daily cron job:

```bash
crontab -e
```

```cron
15 3 * * * /opt/prospectforge/scripts/backup-host.sh >> /opt/prospectforge/backups/backup.log 2>&1
```

Backups are atomic, gzip-verified, mode `600`, and retained for 14 days by
default. Copy them off the VPS as well; a disk failure can destroy both the
database volume and local backups.

Restore a backup during a maintenance window:

```bash
cd /opt/prospectforge
./scripts/restore.sh backups/prospectforge_YYYYMMDDTHHMMSSZ.sql.gz
```

Restore validates the archive, creates a safety backup, stops application
traffic, restores with `ON_ERROR_STOP`, reapplies migrations, and starts the
stack again.

## Updates

```bash
cd /opt/prospectforge
DEPLOY_BRANCH=main ./scripts/vps-update.sh
```

The update refuses a dirty checkout, fast-forwards only, records the previous
Git SHA, and runs the complete guarded deployment.

## Rollback

If the newest image fails after deployment:

```bash
./scripts/rollback.sh
```

This creates a safety backup and restores the image preserved by the preceding
deploy. Database migrations are forward-applied; if a future release contains
an incompatible migration, restore the pre-deploy database backup as well.

## Operations

```bash
docker compose ps
docker compose logs -f app caddy db
docker compose restart app
docker compose exec app alembic current
docker compose exec app python -m app.jobs.ingestion --mode registry --max-companies 40
./scripts/backup-host.sh
```

The scheduler and nightly ingestion remain disabled by default. Enable them
only after manually validating live-source quality.

## Release verification

Before publishing a release from a development machine:

```bash
PYTHON_BIN=.venv/bin/python ./scripts/release-gate.sh
./scripts/smoke-production.sh
```

The first command rebuilds pinned frontend assets, runs lint/tests/compile
checks, validates shell scripts and Compose. The second performs a disposable
PostgreSQL migration and HTTPS boot test and deletes all smoke data afterward.

## Troubleshooting

| Symptom | Check |
|---|---|
| Deployment rejects `.env` | Replace placeholders; use the configuration generator |
| ACME certificate fails | Confirm DNS points to the VPS and ports 80/443 are reachable |
| App is unhealthy | `docker compose logs --tail=200 app db` |
| Caddy returns 502 | Wait for `/ready`, then inspect app logs |
| Existing proxy port conflict | Use `TLS_MODE=external` |
| Login loop or missing cookie | Confirm the browser uses HTTPS and `FORCE_HTTPS_COOKIES=true` |
| Migration failure | Do not bypass it; inspect logs and restore the pre-deploy backup if needed |
