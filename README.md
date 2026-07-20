# ProspectForge V3

### Client acquisition OS for **operational** French SMEs

**Version 3.0** · FastAPI · PostgreSQL · HTMX

ProspectForge finds, qualifies, prioritizes, and helps convert **non-technical / lightly technical mid-market companies** that buy **custom operational software** — not software houses that build it themselves.

**Primary market play:** `FIELD_SERVICE_OPERATIONS_FR`  
(field technicians · maintenance · installation · cold chain · HVAC · electrical · facilities)

> The machine produces a **small meeting-ready queue**.  
> You keep the last mile: human qualification, LinkedIn confirmation, and final message edits.

---

## What changed in V3

| V2.x (wrong default) | V3 |
|---|---|
| Targets IT/cyber/ESN | Targets **field-service / technical ops SMEs** |
| Award ≈ need | Award = **timing only**; pain needs separate evidence |
| One urgency score | **Opportunity score** (fit/pain/trigger/authority/value/DQ) + readiness gates |
| Guessed email = contact-ready | Guessed emails labeled; **human qualification required** |
| `REGISTRY_IT` discovery | `REGISTRY_FIELD` + play-driven NAF/CPV/keywords |
| Volume dashboard | **Daily action queue** + qualify checklist |

Historical product/engineering plans are preserved in
[`docs/archive/`](./docs/archive/) and are not the current source of truth.

---

## Docs

| File | Purpose |
|---|---|
| **[GUIDE.md](./GUIDE.md)** | Daily operator rhythm (update for V3 queue) |
| **[DEPLOY.md](./DEPLOY.md)** | VPS deploy, custom ports, backups |
| **[docs/archive/](./docs/archive/)** | Historical specifications and decision context |

---

## Core screens

| Route | Role |
|---|---|
| **`/queue`** | **Daily action queue** — ranked work + qualify |
| `/queue/{id}/qualify` | Human checklist (accept / research / park / reject) |
| `/prospects/{id}#message-drafts` | Editable LinkedIn/email drafts after acceptance |
| `/sourcing` | Run DECP + registry discovery |
| `/prospects` | Full list |
| `/` | Dashboard |
| `/follow-ups` | Due tasks / next actions |
| `/kanban` | Pipeline |

---

## Quick start (local)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
rm -f prospectforge.db   # fresh schema
uvicorn app.main:app --reload --port 8000
```

- http://localhost:8000/queue  
- Login: `admin@prospectforge.local` / `admin123` (dev only)

```bash
# Field-service registry discovery
export INSEE_API_KEY=...
python -m app.jobs.ingestion --mode registry --max-companies 30

# Public awards (maintenance / installation filters)
python -m app.jobs.ingestion --mode decp --max-companies 40
```

```bash
pytest -q
```

---

## Production (VPS)

The supported stack is Caddy, a non-root/read-only FastAPI container, and a
private PostgreSQL 16 service. Public production defaults to trusted HTTPS on
ports 80/443; existing reverse proxies and private custom-port deployments are
also supported.

```bash
./scripts/configure-production.sh prospects.example.com you@example.com acme
./scripts/deploy.sh
```

Deploy validates configuration, backs up an existing database, applies
migrations before replacing the app, verifies readiness/HTTPS, and preserves a
rollback image. See [DEPLOY.md](./DEPLOY.md) for first install, updates,
external-proxy mode, backups, restore, and rollback.

---

## Architecture (V3)

### Contact Intelligence

ProspectForge now keeps people, contact points, evidence, verification history, and discovery runs in normalized tables. The official company website is crawled narrowly with SSRF controls; public emails, business phones, contact forms, people, French buyer roles, JSON-LD, and bounded PDF text are extracted with provenance. Published same-domain patterns guide candidate generation, while DNS and private Reacher checks remain technical verification layers.

Guessed-only and catch-all addresses always require manual review. Full values are shown only on authenticated detail workflows, manual LinkedIn research is auditable but never automated, and contact discovery cannot send outreach. See [`docs/contact-intelligence/OPERATOR_PLAYBOOK.md`](./docs/contact-intelligence/OPERATOR_PLAYBOOK.md).

```
Market play FIELD_SERVICE_OPERATIONS_FR
        ↓
DECP awards (CPV 45/50/453… + maintenance keywords)
  + Registry (NAF 43/33/81…)
        ↓
Sirene identity / diffusion gate
        ↓
Evidence list (structural ≠ pain ≠ trigger)
        ↓
Opportunity score + hard readiness gates
        ↓
Human qualification (required)
        ↓
Deterministic editable drafts → LinkedIn/email → careful first outreach
        ↓
Append-only events + follow-up tasks
```

### Opportunity score

```
0.25×fit + 0.25×pain + 0.20×trigger + 0.15×authority + 0.10×value + 0.05×data_quality
× confidence_multiplier − penalties
```

**High score cannot skip gates:** fit/pain/trigger floors, contact quality, and **human accept**.

### Contact honesty

| State | May auto-send? |
|---|---|
| deliverable / published personal / reply-confirmed | After role confirm |
| catch-all / guessed pattern | **No** — LinkedIn or more verify |
| invalid / bounced | Block |

---

## Packaged offer (default play)

> A focused **operations-control system** for quotes, interventions, technicians, reports, parts, and management visibility — configured around the company’s real workflow, not sold as generic software development.

---

## Project layout

```
app/
  plays/field_service.py   # Active market-play config
  scoring_v3.py            # Opportunity + readiness
  messaging.py             # Accepted-only LinkedIn/email drafts
  discovery/               # DECP, Annuaire, Sirene, contacts (play-driven)
  routers/queue.py         # Daily queue + qualification
  models.py                # Prospects + evidence + reviews + tasks + runs
scripts/ deploy/           # VPS
tests/
```

---

## Security & compliance

- Loopback-bound app/DB; Caddy on custom ports  
- `/docs` off in production  
- Weak `SECRET_KEY` refused at startup  
- `data_source` + `informed_at` before `Sent`  
- Opt-out + suppression table  
- Partial-diffusion companies never imported  

---

## What V3 deliberately does *not* do yet

- Autonomous LinkedIn scrape/send  
- High-volume email sequences  
- Opaque ML scoring  
- Full multi-entity CRM rewrite (companies/campaigns normalized tables seeded; legacy `prospects` still the operator row with V3 fields)  
- BODACC / website crawler / BOAMP adapters (spec’d; next increment)

Those are listed as non-goals until the manual commercial loop works.

---

## License / sources

Open data: DECP, Recherche Entreprises, Sirene (API key).  
You remain responsible for GDPR/CNIL B2B practice.
