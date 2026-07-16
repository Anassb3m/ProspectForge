# ProspectForge — Technical Specification (Python Stack)
### Version 2.0 — Client Acquisition OS

> This is the target architecture to build once your manual pilot (see the execution plan) shows a reply/meeting rate worth automating. Everything here is scoped so you can build it solo, in Python, without over-engineering.

---

## 1. Executive Summary

**What it is:** An internal web application that stores prospects (French SMEs sourced via BOAMP tenders, LinkedIn signals, and Morocco-corridor signals), automatically scores them by urgency, and tracks the full outreach lifecycle from first contact to closed deal.

**What changed from v1.0:** Backend moves from Laravel/PHP to Python. Rationale:

| Factor | Why Python wins here |
|---|---|
| Data enrichment & scraping-adjacent tasks | Python's ecosystem (`httpx`, `BeautifulSoup`, `pandas`) is far stronger than PHP's for CSV wrangling, Hunter.io/BOAMP API calls, and future LinkedIn-post signal parsing (Phase 2) |
| Scoring engine | Urgency scoring will evolve into a small weighted/ML-assisted model as you get real data (Phase 4) — Python (`scikit-learn`, `pandas`) is the natural home for that, Laravel is not |
| Solo maintenance | One language across backend + data scripts + future analysis notebooks (Jupyter) reduces context switching for a single builder |
| Async I/O | FastAPI's async support handles concurrent enrichment calls (Hunter.io, email verification) cleanly |

**Design philosophy unchanged:** simple to operate, powerful through prioritization and tracking — not through feature count.

---

## 2. Architecture Overview

```
┌─────────────────────┐      ┌──────────────────────┐      ┌─────────────────┐
│   Frontend (HTMX +   │◄────►│   FastAPI Backend      │◄────►│   PostgreSQL     │
│   Jinja2 + Tailwind) │      │   (Python 3.12)        │      │   Database       │
└─────────────────────┘      └──────────────────────┘      └─────────────────┘
                                        │
                              ┌─────────┴──────────┐
                              │  Background jobs    │
                              │  (APScheduler)       │
                              │  - urgency recalculation
                              │  - follow-up reminders
                              │  - Hunter.io enrichment
                              └─────────────────────┘
```

**Frontend choice — HTMX + Jinja2 + Tailwind, not React.**
For a single-user internal tool with server-rendered tables, forms, and a Kanban board, HTMX removes the need for a separate JS build pipeline, API-shaped endpoints for every UI action, and client-side state management — you get interactivity (inline status updates, live filtering, drag-and-drop) with a fraction of the code. If you later want a richer UI (multi-user, mobile app, public-facing dashboard), swapping to a React frontend against the same FastAPI JSON API is a clean, isolated migration — the backend doesn't change.

---

## 3. Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.12 | |
| Web framework | FastAPI | Async, auto-generated OpenAPI docs, strong typing via Pydantic |
| ORM | SQLAlchemy 2.0 | Explicit, mature, works well with Alembic |
| Migrations | Alembic | |
| Database | PostgreSQL 16 | SQLite is fine for local dev only — use Postgres from the start to avoid a migration later |
| Frontend | Jinja2 templates + HTMX + Tailwind CSS | No JS build step |
| Background jobs | APScheduler (in-process) | No need for Celery/Redis at this scale — one background thread is enough for a single-user tool |
| Auth | FastAPI's built-in `OAuth2PasswordBearer` + `passlib` (bcrypt) | Simple session/JWT auth, single or few users |
| CSV import/export | `pandas` | |
| Email enrichment | Hunter.io REST API via `httpx` | |
| Deployment | Docker Compose (app + Postgres) on a single VPS | |
| Testing | `pytest` + `httpx.AsyncClient` for API tests | |

---

## 4. Data Model

### 4.1 `prospects`

```python
class Prospect(Base):
    __tablename__ = "prospects"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_name: Mapped[str] = mapped_column(String(200), index=True)
    sector: Mapped[str] = mapped_column(String(100))  # Construction, Manufacturing, Logistics, Engineering, Professional Services, Other
    company_size: Mapped[str] = mapped_column(String(20))  # "1-10", "11-50", "51-200", "200+"
    signal_type: Mapped[str] = mapped_column(String(50))  # BOAMP_WIN, MOROCCO_OPS, PAIN_POST, OTHER
    signal_details: Mapped[str] = mapped_column(Text, nullable=True)

    decision_maker_name: Mapped[str] = mapped_column(String(150), nullable=True)
    decision_maker_title: Mapped[str] = mapped_column(String(150), nullable=True)
    linkedin_url: Mapped[str] = mapped_column(String(300), nullable=True)
    email: Mapped[str] = mapped_column(String(150), nullable=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    website: Mapped[str] = mapped_column(String(300), nullable=True)

    # GDPR / compliance trail — required, not optional
    data_source: Mapped[str] = mapped_column(String(200))       # e.g. "BOAMP public tender search", "LinkedIn public profile"
    informed_at: Mapped[datetime] = mapped_column(nullable=True) # timestamp of first-contact disclosure
    opted_out: Mapped[bool] = mapped_column(default=False)
    opted_out_at: Mapped[datetime] = mapped_column(nullable=True)

    urgency_score: Mapped[int] = mapped_column(default=50)
    priority_level: Mapped[str] = mapped_column(String(10), default="Medium")  # High/Medium/Low
    source: Mapped[str] = mapped_column(String(50))  # BOAMP, LinkedIn, Manual, Registry

    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    outreach_events: Mapped[list["OutreachEvent"]] = relationship(back_populates="prospect")
```

### 4.2 `outreach_events` (append-only log, not a single mutable row)

Modeling outreach as an **event log** rather than one row with a `status` field is the key improvement over v1.0 — it gives you full history per prospect and makes the pipeline/Kanban view and metrics trivial to compute correctly.

```python
class OutreachEvent(Base):
    __tablename__ = "outreach_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospects.id"), index=True)
    channel: Mapped[str] = mapped_column(String(20))  # LinkedIn, Email, Phone
    event_type: Mapped[str] = mapped_column(String(20))
    # New, Sent, Replied, Refused, MeetingBooked, PositiveConversation,
    # ProposalSent, ClosedWon, ClosedLost, OptOut
    event_date: Mapped[datetime] = mapped_column(server_default=func.now())
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    next_action: Mapped[str] = mapped_column(String(300), nullable=True)
    next_action_date: Mapped[datetime] = mapped_column(nullable=True)

    prospect: Mapped["Prospect"] = relationship(back_populates="outreach_events")
```

A prospect's **current status** is just its most recent `OutreachEvent.event_type` — computed, never stored redundantly. This avoids the classic bug of the status field and the history disagreeing.

### 4.3 `users` (even for a single user — keeps auth simple and future-proofs multi-user)

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(150), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

---

## 5. Urgency Scoring Engine

Kept as an explicit, inspectable weighted function — not a black box — so you can see exactly why a prospect ranks where it does, and adjust weights as real conversion data comes in.

```python
def calculate_urgency_score(prospect: Prospect, events: list[OutreachEvent]) -> int:
    score = 50

    if prospect.signal_type == "BOAMP_WIN":
        score += 25
        if "multiple" in (prospect.signal_details or "").lower():
            score += 10
    if prospect.signal_type == "MOROCCO_OPS":
        score += 15
    if prospect.signal_type == "PAIN_POST":
        score += 20

    if prospect.decision_maker_title and any(
        t in prospect.decision_maker_title.lower()
        for t in ["fondateur", "dirigeant", "directeur commercial"]
    ):
        score += 10

    if prospect.company_size in ("11-50", "51-200"):
        score += 5

    # Decay: no activity in 21+ days since last outreach event
    if events:
        last_event_age_days = (datetime.utcnow() - events[-1].event_date).days
        if last_event_age_days > 21:
            score -= 10

    return max(0, min(100, score))
```

Run this as a **recalculation job** (nightly, via APScheduler) rather than only on save — scores should decay as prospects go stale, which a save-time-only calculation misses. This was a gap in the v1.0 spec.

Priority label derived from score: `High` ≥ 75, `Medium` 45–74, `Low` < 45.

---

## 6. API Endpoints

FastAPI auto-generates OpenAPI/Swagger docs at `/docs` — no separate API documentation to maintain.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/prospects` | List, filterable by `sector`, `signal_type`, `priority_level`, `status`; sortable by `urgency_score` |
| `POST` | `/prospects` | Create a prospect |
| `GET` | `/prospects/{id}` | Full detail incl. outreach history |
| `PATCH` | `/prospects/{id}` | Edit fields |
| `POST` | `/prospects/import` | CSV bulk import (pandas-parsed, validated row by row, errors returned per row not as a single failure) |
| `POST` | `/prospects/{id}/events` | Log a new outreach event (Sent, Replied, etc.) |
| `GET` | `/prospects/{id}/events` | History for one prospect |
| `GET` | `/dashboard/metrics` | Aggregate metrics (see §7) |
| `GET` | `/dashboard/follow-ups-due` | Prospects with `next_action_date <= today` |
| `POST` | `/auth/login` | Session/JWT login |

---

## 7. Core Features

### Prospect management
- Manual add form + CSV bulk import with per-row validation feedback (which rows failed and why — not a silent partial import)
- Filter/search by sector, signal type, urgency score range, current status
- Bulk actions: bulk status update, bulk export

### Outreach tracking
- One-click event logging (Sent → Replied → Meeting Booked, etc.) from the list view, no page reload (HTMX)
- Kanban board view: columns = New / Sent / Replied / Meeting / Closed, drag-and-drop updates the underlying event log
- Follow-up queue: a dedicated view listing everything with `next_action_date` due today or overdue — this is the "what do I do right now" screen you open every morning

### Dashboard
- Total prospects, contacted this week, reply rate, meeting rate
- Reply rate broken down **by signal_type** — this is the number that tells you which sourcing method to keep investing in
- Reply rate broken down by channel (LinkedIn vs Email)
- Simple table of most common objection notes (manually tagged, not NLP — don't over-build this)

### Compliance built into the schema, not bolted on
- `data_source` and `informed_at` are required fields on every prospect — you cannot log a `Sent` event without them populated (enforced at the API layer)
- Opting out via a `OptOut` event type immediately excludes the prospect from any future bulk action or reminder in the UI layer, not just a manual note

---

## 8. Non-Functional Requirements

| Requirement | Approach |
|---|---|
| Security | Single-user or small-team auth via hashed passwords + session cookies; HTTPS via the VPS reverse proxy (Caddy or nginx) |
| Data protection | Postgres on the VPS, not a third-party SaaS, for data residency simplicity given GDPR scope; nightly `pg_dump` backup to a separate volume |
| Performance | At pilot scale (hundreds to low thousands of prospects) a single small VPS instance handles this comfortably — no need to plan for scale you don't have |
| Retention | A scheduled job flags/anonymizes prospects inactive 3+ years, per CNIL guidance on B2B prospect retention |

---

## 9. Project Structure

```
prospectforge/
├── app/
│   ├── main.py                 # FastAPI app entrypoint
│   ├── models.py                # SQLAlchemy models
│   ├── schemas.py                # Pydantic request/response schemas
│   ├── database.py               # Engine/session setup
│   ├── scoring.py                 # Urgency scoring logic
│   ├── routers/
│   │   ├── prospects.py
│   │   ├── events.py
│   │   ├── dashboard.py
│   │   └── auth.py
│   ├── jobs/
│   │   ├── scheduler.py           # APScheduler setup
│   │   ├── recalculate_scores.py
│   │   └── enrichment.py          # Hunter.io calls
│   ├── templates/                 # Jinja2 + HTMX templates
│   └── static/                    # Tailwind output, minimal JS
├── alembic/                       # migrations
├── tests/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── .env.example
```

---

## 10. Implementation Plan

**Week 1**
- Day 1–2: Project scaffold, models, Alembic migration, Docker Compose (app + Postgres)
- Day 3: Prospect CRUD (API + basic Jinja2 list/detail templates)
- Day 4: Outreach event logging + status-derivation logic
- Day 5: Urgency scoring function + nightly recalculation job

**Week 2**
- Day 6–7: CSV import with per-row validation; export
- Day 8: Dashboard metrics endpoint + page
- Day 9: Kanban view (HTMX drag-and-drop) + follow-up queue view
- Day 10: Auth, deploy to VPS via Docker Compose, backup cron

**Explicitly deferred to Phase 2 (after 100+ real outreaches):**
- Hunter.io auto-enrichment on import
- Any LinkedIn-post signal automation (must stay manual/ToS-compliant)
- Weight tuning or ML-assisted scoring based on real conversion data
- Multi-user roles, if you bring on a second person doing outreach

---

## 11. Testing Strategy

- `pytest` unit tests for `scoring.py` (pure function, easy to test exhaustively with edge cases)
- API tests via `httpx.AsyncClient` for CRUD + event logging + the "cannot log Sent without data_source" compliance rule
- No need for browser/E2E tests at this scale — HTMX interactions are simple enough to verify manually during the 2-week build

---

## 12. Deployment

```yaml
# docker-compose.yml (excerpt)
services:
  app:
    build: .
    env_file: .env
    depends_on: [db]
    ports: ["8000:8000"]
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: prospectforge
    volumes: ["pgdata:/var/lib/postgresql/data"]
volumes:
  pgdata:
```

Single cheap VPS (e.g. 2 vCPU / 4GB RAM tier) is more than sufficient at this scale. Caddy in front for automatic HTTPS with minimal config.

---

## 13. What This Spec Deliberately Leaves Out

Consistent with the earlier recommendation: no AI-based lead scoring, no automated LinkedIn scraping, no multi-channel sequencing engine, no CRM-replacement ambitions. Every deferred item above is deferred because it needs real usage data to be built correctly, not because it's technically hard. Build the smaller version first; the data from actually using it tells you which of these is worth adding.
