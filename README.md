# ProspectForge

### Client Acquisition OS for French IT / digital SMEs

**Version 2.2** · Python · FastAPI · PostgreSQL · HTMX

ProspectForge is an internal operating system for **finding, ranking, and converting** high-signal French mid-market companies — especially those winning public IT/cyber/digital contracts or sitting in the IT SME registry with reachable dirigeants.

It is built for a **solo operator or small team**: few features, high leverage, full audit trail (GDPR/CNIL-friendly B2B prospecting). The machine does the mechanical work. You keep the last mile that converts — LinkedIn confirmation and the first personalized message.

---

## Why it exists

Manual prospecting for French public-market winners and IT SMEs is slow:

1. Browse BOAMP / DECP / LinkedIn for hours  
2. Copy company names into a spreadsheet  
3. Guess emails  
4. Forget follow-ups  
5. Never know which signal type actually replies  

ProspectForge collapses steps 1–3 into a **nightly (or on-demand) pipeline**, then forces steps 4–5 into a **queue you open every morning**.

```
Public awards + company registry
        ↓  filter · enrich · score
   Acquisition cockpit (ranked)
        ↓  LinkedIn last-mile + email
   Outreach event log
        ↓
   Dashboard (what sourcing works)
```

---

## What you get

| Capability | What it does |
|---|---|
| **Multi-source discovery** | DECP public awards + Recherche Entreprises IT SME hunt |
| **Sirene compliance** | Official INSEE data; blocks partial-diffusion companies |
| **Dirigeant extraction** | Président / DG names from open registry (email-ready) |
| **ICP acquisition score** | Explicit fit × timing × contactability × value |
| **Contact waterfall** | French email patterns + optional Reacher SMTP verify |
| **Sourcing cockpit** | Ranked queue with “why this lead” badges |
| **Outreach event log** | Append-only history; status always derived |
| **Pipeline (Kanban)** | New → Sent → Replied → Meeting → Closed |
| **Follow-up queue** | Due / overdue next actions for the morning |
| **Dashboard** | Reply rates by signal type & channel |
| **CSV import/export** | Bulk load + backup of the list |
| **VPS-ready Docker** | Custom ports (no fight for 80/443), Caddy, backups |

**Honest limits (by design):** no automated LinkedIn scraping, no black-box AI scoring, no multi-channel sequencer. Decision-maker *confirmation* stays human — that is where conversion quality lives.

---

## Documentation map

| Doc | Audience |
|---|---|
| **[GUIDE.md](./GUIDE.md)** | **You** — use cases, daily workflow, how to use the system efficiently |
| **[DEPLOY.md](./DEPLOY.md)** | Ops — VPS, custom ports, TLS, backups, firewall |
| [prospectforge_spec_python.md](./prospectforge_spec_python.md) | Architecture v2.0 core |
| [logic_specification.txt](./logic_specification.txt) | Discovery / enrichment pipeline v2.1 |

---

## Screens (mental model)

| Route | Purpose |
|---|---|
| `/` | **Dashboard** — volume, reply rates, DECP this week, needs-review |
| `/sourcing` | **Acquisition cockpit** — run discovery, rank leads, deep-enrich, LinkedIn |
| `/prospects` | Full CRM-style list with filters + quick event log |
| `/prospects/{id}` | Company detail, award history, compliance, timeline |
| `/kanban` | Pipeline board (drag updates event log) |
| `/follow-ups` | Everything due today or overdue |
| `/import` | CSV bulk import with per-row errors |
| `/docs` | OpenAPI (disabled in production unless `DEBUG=true`) |

---

## Quick start (local development)

**Requirements:** Python 3.12+, optional Docker for Postgres later.

```bash
git clone <repo> ProspectForge && cd ProspectForge
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# SQLite by default via .env
uvicorn app.main:app --reload --port 8000
```

| | |
|---|---|
| App | http://localhost:8000 |
| Login (dev defaults) | `admin@prospectforge.local` / `admin123` |
| Sourcing | http://localhost:8000/sourcing |
| API docs | http://localhost:8000/docs |

> Change admin credentials before any shared or production use.

### First discovery run (local)

```bash
# In .env: INSEE_API_KEY=...  (recommended)
python -m app.jobs.ingestion --mode registry --max-companies 30
# or full (DECP parquet download can be large):
# python -m app.jobs.ingestion --mode full --max-companies 40
```

Or open **Sourcing → Run acquisition**.

### Tests

```bash
pytest -q
```

---

## Production deploy (shared VPS, custom ports)

ProspectForge is built to live **next to other services** without taking 80/443.

| Role | Default host port |
|---|---|
| Public HTTP | **18080** |
| Public HTTPS (self-signed) | **18443** |
| App (loopback) | **18081** |
| Postgres (loopback) | **15432** |

```bash
cp .env.production.example .env
# set SECRET_KEY, POSTGRES_PASSWORD, ADMIN_*, INSEE_API_KEY, ports if needed
chmod +x scripts/*.sh
./scripts/deploy.sh
```

Then open `http://VPS_IP:18080` (or HTTPS on 18443).

**Full guide:** [DEPLOY.md](./DEPLOY.md) — firewall, nginx reverse-proxy option, backups, restore, troubleshooting.

---

## Architecture

### Runtime stack

```
Browser (HTMX + Jinja2 + Tailwind CDN)
        ↕
FastAPI (async) + JWT cookie auth
        ↕
PostgreSQL 16  (SQLite OK for local only)
        ↕
APScheduler (in-process: nightly ingestion, score recalc, retention)
```

### Discovery pipeline

```
┌─────────────────────┐     ┌──────────────────────┐
│ DECP Parquet        │     │ Recherche Entreprises│
│ (public awards)     │     │ (IT SME + dirigeants)│
└─────────┬───────────┘     └──────────┬───────────┘
          │ filter / aggregate         │ NAF 62/63 first
          └────────────┬───────────────┘
                       ▼
              Sirene (INSEE) compliance gate
                       ▼
              Deep enrich + ICP acquisition score
                       ▼
              Prospect row (one per SIRET)
                       ▼
              /sourcing  →  LinkedIn  →  outreach events
```

### Scoring (inspectable, not ML)

```
acquisition ≈ 0.35×fit + 0.30×timing + 0.20×contactability + 0.15×value
```

| Axis | What it captures |
|---|---|
| **Fit** | NAF (IT/digital), headcount sweet spot, dirigeant seniority |
| **Timing** | Fresh DECP wins, multi-award streak, cyber/cloud language, premium buyers |
| **Contactability** | Verified/likely email, named DM, website, phone |
| **Value** | Contract amounts, SME size, IT NAF |

Every lead can show **badges** and **“why this lead”** reasons in the cockpit.

### Compliance (built-in)

- `data_source` required on every prospect  
- Cannot log **Sent** without `informed_at` (first-contact disclosure)  
- **OptOut** event freezes further outreach  
- Partial-diffusion Sirene records are never imported  
- Retention job can anonymize stale records (CNIL B2B guidance)

---

## Project layout

```
app/
  main.py                 # FastAPI entry + lifespan
  models.py / schemas.py  # SQLAlchemy + Pydantic
  scoring.py              # Urgency + blend with acquisition
  services.py             # CRUD, metrics, CSV, compliance
  discovery/              # DECP, Annuaire, Sirene, ICP, emails, enrich
  jobs/                   # ingestion, scheduler, retention
  routers/                # auth, prospects, events, dashboard, sourcing
  templates/ + static/    # HTMX UI
deploy/Caddyfile          # Edge proxy (custom ports)
scripts/                  # deploy, backup, restore, entrypoint
alembic/                  # migrations
tests/                    # pytest
DEPLOY.md  GUIDE.md       # ops + usage
```

---

## Environment (essentials)

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | JWT signing — long random in production |
| `POSTGRES_*` | DB credentials (compose builds `DATABASE_URL`) |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Bootstrap user if DB empty |
| `INSEE_API_KEY` | Sirene enrichment (free public plan) |
| `HTTP_PORT` / `HTTPS_PORT` / `APP_PORT` / `POSTGRES_PORT` | Shared-VPS port map |
| `TLS_MODE` | `internal` · `off` · `acme` |
| `FORCE_HTTPS_COOKIES` | `true` only when serving over HTTPS |
| `DECP_DAYS_BACK` / `DECP_MAX_COMPANIES` | Ingestion scope |
| `ENABLE_NIGHTLY_INGESTION` | APScheduler discovery job |
| `REACHER_ENABLED` | Optional SMTP email verification |

See `.env.production.example` for the full production template.

---

## CLI cheat sheet

```bash
# Discovery modes
python -m app.jobs.ingestion --mode registry --max-companies 40
python -m app.jobs.ingestion --mode decp --days 120 --max-companies 50
python -m app.jobs.ingestion --mode full --max-companies 60
python -m app.jobs.ingestion --rescore-only

# Inside Docker
docker compose exec app python -m app.jobs.ingestion --mode registry --max-companies 40

# Deploy / backup
./scripts/deploy.sh
./scripts/backup-host.sh
./scripts/restore.sh backups/prospectforge_YYYYMMDD.sql.gz
```

---

## Security notes

- App binds to **loopback** on the host; only Caddy (or your reverse proxy) should be public  
- Postgres is loopback-only  
- `/docs` is **off** when `ENVIRONMENT=production` and `DEBUG=false`  
- Production refuses weak/short `SECRET_KEY` at startup  
- Never commit `.env` (gitignored)  
- Reacher is dual-licensed (AGPL / commercial) if you enable it for business use  

---

## Roadmap discipline

**In scope now:** discovery, enrichment, ranking, tracking, compliance, deploy.  
**Deferred until real volume:** ML weight tuning, Hunter.io, multi-user roles, automated LinkedIn.

Build small → use daily → let reply rates tell you what to automate next.

---

## License / data sources

- Application code: your repository license  
- DECP: open data (data.gouv.fr consolidations)  
- Sirene: INSEE API (requires free key)  
- Recherche Entreprises: api.gouv.fr (no key)  

Prospecting remains subject to **GDPR / CNIL B2B rules** — this tool helps you document sources and opt-outs; it does not replace legal judgment.

---

## Start here

1. Local: `uvicorn` + open `/sourcing`  
2. Read **[GUIDE.md](./GUIDE.md)** for the efficient operating rhythm  
3. When ready: **[DEPLOY.md](./DEPLOY.md)** on your VPS with custom ports  
