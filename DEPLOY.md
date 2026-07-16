# Deploy ProspectForge on a shared VPS (custom ports)

Stack: **Caddy (optional edge) → FastAPI → PostgreSQL 16**.

Designed so it **does not need ports 80/443** — safe next to other stacks on the same machine.

**Defaults (change in `.env` if busy):**

| Role | Host bind | Default |
|---|---|---|
| Public HTTP | `0.0.0.0:HTTP_PORT` | **18080** |
| Public HTTPS (self-signed) | `0.0.0.0:HTTPS_PORT` | **18443** |
| App (loopback only) | `127.0.0.1:APP_PORT` | **18081** |
| Postgres (loopback only) | `127.0.0.1:POSTGRES_PORT` | **15432** |

Recommended VPS: **2 vCPU / 4 GB RAM**. Ubuntu 22.04/24.04 LTS.

---

## 1. Server prep

```bash
apt update && apt upgrade -y
apt install -y ca-certificates curl git ufw
curl -fsSL https://get.docker.com | sh
usermod -aG docker "$USER"   # re-login

# Only open what ProspectForge needs (NOT 80/443 unless you want them)
ufw allow OpenSSH
ufw allow 18080/tcp
ufw allow 18443/tcp
ufw enable
```

---

## 2. Install code

```bash
sudo mkdir -p /opt/prospectforge
sudo chown "$USER":"$USER" /opt/prospectforge
cd /opt/prospectforge
# git clone <repo> .   OR rsync from your laptop
```

---

## 3. Configure `.env`

```bash
cp .env.production.example .env
nano .env
```

**Must set:**

```bash
HTTP_PORT=18080
HTTPS_PORT=18443
APP_PORT=18081
POSTGRES_PORT=15432
TLS_MODE=internal          # self-signed HTTPS on 18443 (no Let's Encrypt fight)
FORCE_HTTPS_COOKIES=false  # set true only if you only use HTTPS

SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_PASSWORD=$(openssl rand -hex 24)   # alphanumerics only
ADMIN_EMAIL=you@example.com
ADMIN_PASSWORD='long-unique-passphrase'
INSEE_API_KEY=your-key-here
ENVIRONMENT=production
DEBUG=false
```

> Never commit `.env`.  
> Avoid `@ # / : ? %` in `POSTGRES_PASSWORD` (breaks `DATABASE_URL`).

### Two access patterns

**A) Standalone on high ports (default)**  
Open `http://VPS_IP:18080` or `https://VPS_IP:18443` (browser warns on self-signed — OK).

**B) Behind your existing nginx/Caddy on 80/443**

```bash
# .env
TLS_MODE=off
# optional: don't publish Caddy publicly — or keep it for direct high-port access

# nginx example:
# location / {
#   proxy_pass http://127.0.0.1:18081;
#   proxy_set_header Host $host;
#   proxy_set_header X-Forwarded-Proto $scheme;
#   proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
# }
```

Then set `FORCE_HTTPS_COOKIES=true` if that proxy serves HTTPS.

---

## 4. Launch

```bash
chmod +x scripts/*.sh
./scripts/deploy.sh
```

Checks:

```bash
curl -s http://127.0.0.1:18081/health
curl -s http://127.0.0.1:18081/ready
docker compose ps
```

Login: `ADMIN_EMAIL` / `ADMIN_PASSWORD`.

---

## 5. Backups (cron)

```bash
mkdir -p /opt/prospectforge/backups
crontab -e
# 15 3 * * * /opt/prospectforge/scripts/backup-host.sh >> /var/log/prospectforge-backup.log 2>&1
```

Restore:

```bash
./scripts/restore.sh backups/prospectforge_YYYYMMDDTHHMMSSZ.sql.gz
docker compose restart app
```

---

## 6. Updates

```bash
cd /opt/prospectforge
git pull   # or rsync
./scripts/deploy.sh
```

---

## 7. Ops cheat sheet

```bash
docker compose logs -f app caddy
docker compose restart app
docker compose exec app python -m app.jobs.ingestion --mode registry --max-companies 40
./scripts/backup-host.sh
```

---

## 8. Architecture

```
Internet
   │ :18080 (HTTP)  and/or  :18443 (HTTPS self-signed)
   ▼
 Caddy  (optional edge — custom ports only)
   │
   ▼
 app  127.0.0.1:18081 → container :8000
   │
   ▼
 db   127.0.0.1:15432 → container :5432
```

**One uvicorn worker only** (APScheduler in-process).

---

## 9. Pre-deploy checklist

- [ ] Ports 18080/18443 (or your choices) free: `ss -tlnp | grep -E '18080|18443|18081|15432'`
- [ ] Strong `SECRET_KEY` (≥32 chars), `POSTGRES_PASSWORD`, `ADMIN_PASSWORD`
- [ ] `INSEE_API_KEY` if you want Sirene enrich
- [ ] UFW allows your chosen ports + SSH
- [ ] `.env` not world-readable: `chmod 600 .env`
- [ ] After first login, confirm admin password works
- [ ] Cron backup installed

---

## 10. Troubleshooting

| Symptom | Fix |
|---|---|
| Port already allocated | Change `HTTP_PORT` / `HTTPS_PORT` / `APP_PORT` / `POSTGRES_PORT` in `.env` |
| App unhealthy | `docker compose logs app` — bad DB password or weak SECRET_KEY |
| 502 from Caddy | App still booting; `curl 127.0.0.1:$APP_PORT/ready` |
| Browser SSL warning | Expected with `TLS_MODE=internal`; or put your main proxy in front |
| Login cookie lost | If pure HTTP, keep `FORCE_HTTPS_COOKIES=false` |
| DB URL error | Simplify `POSTGRES_PASSWORD` (hex only) |
| Sirene 401 | Check `INSEE_API_KEY` |

---

## 11. Copy-paste first deploy

```bash
curl -fsSL https://get.docker.com | sh
ufw allow OpenSSH && ufw allow 18080/tcp && ufw allow 18443/tcp && ufw --force enable

cd /opt && git clone <REPO> prospectforge && cd prospectforge
cp .env.production.example .env
# edit secrets + ports if needed

chmod +x scripts/*.sh
./scripts/deploy.sh
# open http://VPS_IP:18080
```
