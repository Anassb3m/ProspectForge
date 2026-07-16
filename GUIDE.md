# ProspectForge — Use Cases & Operator Guide

How to run the system so it produces **meetings**, not just a pretty database.

This guide is written for a solo founder / BD operator selling IT, cyber, digital, or nearshore delivery capacity into **French mid-market companies** (the Elevya-style ICP the scoring engine optimizes for). Adapt filters if your ICP differs.

---

## Table of contents

1. [Core idea](#1-core-idea)
2. [Who this is for (ICP)](#2-who-this-is-for-icp)
3. [Use cases](#3-use-cases)
4. [System map (where to click)](#4-system-map-where-to-click)
5. [Daily operating rhythm](#5-daily-operating-rhythm)
6. [Weekly operating rhythm](#6-weekly-operating-rhythm)
7. [How discovery works (so you trust the queue)](#7-how-discovery-works-so-you-trust-the-queue)
8. [How to rank and prioritize](#8-how-to-rank-and-prioritize)
9. [From lead → first message (efficient path)](#9-from-lead--first-message-efficient-path)
10. [Outreach tracking that stays honest](#10-outreach-tracking-that-stays-honest)
11. [Compliance without friction](#11-compliance-without-friction)
12. [Dashboard: what to actually look at](#12-dashboard-what-to-actually-look-at)
13. [CSV import / export](#13-csv-import--export)
14. [Tuning the machine](#14-tuning-the-machine)
15. [Anti-patterns](#15-anti-patterns)
16. [90-day playbook](#16-90-day-playbook)
17. [FAQ](#17-faq)

---

## 1. Core idea

ProspectForge is not a full CRM. It is a **priority engine + memory**.

| Layer | Job |
|---|---|
| **Discovery** | Fill the top of funnel with *relevant* French companies |
| **Enrichment** | Attach SIRET, NAF, size, dirigeants, contact hints |
| **Scoring** | Put the best 10–30 in front of you every morning |
| **Tracking** | Remember what you said, when, and what is due next |
| **Learning** | Show which *signals* (DECP vs registry vs manual) actually reply |

The only step the tool deliberately **does not** automate: confirming the decision-maker on LinkedIn and writing a human first message. That step is where quality lives.

**Success metric:** not “rows in database”, but **meetings booked per hour of operator time**.

---

## 2. Who this is for (ICP)

Default ICP encoded in `app/discovery/icp.py`:

| Dimension | Sweet spot |
|---|---|
| Geography | France (public awards + Sirene) |
| Sector | IT / digital / cyber / software / SI conseil (NAF 62.xx, 63.xx…) |
| Size | **11–50** and **51–200** employees |
| Timing signal | Recent **public contract win** (DECP) or multi-win streak |
| Contact | Named **Président / DG / DSI / Directeur commercial** |
| Story fit | Capacity pressure, digital transformation, cyber, cloud, TMA, nearshore |

**High-intent story examples you can use in outreach:**

- They just won a multi-lot public SI / cyber marché → capacity strain  
- Multiple awards in 90 days → growth / delivery risk  
- Mid-size ESN/SSII → often subcontract or partner  
- Premium public buyer (ministère, région, hôpital) → durable budget  

**Usually deprioritize:** pure telecom giants, 200+ headcount, non-diffusible Sirene, cinema/broadcast NAF unless cyber-related.

---

## 3. Use cases

### Use case A — “Monday morning: what do I work?”

**Goal:** 60–90 minutes of high-focus outreach.

1. Open **Follow-ups** first (overdue promises kill reputation).  
2. Open **Sourcing**, sort by **Acquisition score**, min score **65**.  
3. Take the top **10** uncontacted leads with a named dirigeant.  
4. For each: LinkedIn DM → confirm person → Emails → set `informed_at` → log **Sent**.  
5. Stop when you hit 10 quality touches — not when the list ends.

**Why it works:** scoring already did the browsing. You only spend attention on the top of the queue.

---

### Use case B — “Find companies that just won public IT work”

**Goal:** capacity / timing plays.

1. **Sourcing → Run acquisition → mode DECP** (or Full).  
2. Filter signal = **DECP_WIN**.  
3. Prefer badges: *Win ≤90d*, *Multi-win*, *Hot topic (cyber/digital)*, *Premium public buyer*.  
4. Open the company → read **Award history** (objet, montant, acheteur).  
5. Personalize message around the *specific marché* (not a generic “we do IT”).

**Message angle:** “Vu votre attribution sur [objet / acheteur] — souvent la phase suivante est la capacité d’exécution…”

---

### Use case C — “Build a pure IT SME list with dirigeants”

**Goal:** volume of mid-market IT companies with names attached.

1. **Sourcing → Run acquisition → mode Registry** (or CLI `--mode registry`).  
2. Requires network + preferably `INSEE_API_KEY`.  
3. Filter **Has dirigeant** / stage **enriched**.  
4. Deep-enrich thin records (bulk button).  
5. Work by geography or NAF if you niche (filter via search: city, SIREN).

**Message angle:** partnership / nearshore capacity / overflow TMA / cyber delivery.

---

### Use case D — “I already have a spreadsheet”

**Goal:** stop living in Excel.

1. Normalize columns to the import template (see [§13](#13-csv-import--export)).  
2. **Import** → fix per-row errors (sector enums, etc.).  
3. Bulk **deep-enrich** to attach dirigeants / scores.  
4. From then on, **never** update status only in the sheet — use events.

---

### Use case E — “Track a real pipeline without lying to yourself”

**Goal:** status = truth.

1. Every touch = new **Outreach event** (append-only).  
2. Current status is always the **latest event** — no parallel “status” field to desync.  
3. Use **Kanban** for visual flow; drag creates an event.  
4. Put **next_action + next_action_date** on every Sent / Replied.  
5. Morning = **Follow-ups**, not memory.

---

### Use case F — “Prove which sourcing channel to double down on”

**Goal:** capital allocation of your time.

1. After ~50+ outreaches, open **Dashboard**.  
2. Compare **reply rate by signal type** (DECP_WIN vs REGISTRY_IT vs Manual…).  
3. Compare **reply rate by channel** (LinkedIn vs Email vs Phone).  
4. Kill the bottom source for 2 weeks; double the top source.

This is the whole point of tagging `signal_type` and `channel` rigorously.

---

### Use case G — “Compliance-safe B2B prospecting”

**Goal:** sleep at night.

1. Every prospect has a real `data_source` string.  
2. Before first **Sent**, set **informed_at** (disclosure timestamp).  
3. If someone asks to stop → event **OptOut** (blocks further bulk/reminders).  
4. Never re-import partial-diffusion companies (Sirene already filters).  
5. Export / backup stays under your control (Postgres on your VPS).

---

## 4. System map (where to click)

```
┌──────────────────────────────────────────────────────────────┐
│  NAV                                                         │
│  Dashboard │ Sourcing │ Prospects │ Pipeline │ Follow-ups │ Import │
└──────────────────────────────────────────────────────────────┘

Dashboard     → health of the machine (metrics)
Sourcing      → discover + prioritize (THE main screen)
Prospects     → search / filter entire base
Prospect page → deep work: awards, enrich, timeline, compliance
Pipeline      → visual stage board
Follow-ups    → due work only
Import        → CSV bulk
```

### Sourcing cockpit (most important UI)

| Control | When to use |
|---|---|
| **Run acquisition · Full** | Weekly top-up (DECP + registry) |
| **Run acquisition · DECP** | Hunting fresh public winners |
| **Run acquisition · Registry** | Hunting IT SMEs + dirigeants |
| **Bulk deep-enrich** | After import or thin records |
| **Sort: Acquisition** | Default daily work order |
| **Min score** | e.g. `65` to hide noise |
| **Contact: Has dirigeant** | Skip nameless rows |
| **Stage: contact_ready** | Only leads with usable email |
| **LinkedIn DM** | One click Google/`site:linkedin.com/in` query |
| **Emails** | Generate FR permutations from dirigeant name |
| **Deep enrich** | Refresh Annuaire + Sirene + scores for one row |

---

## 5. Daily operating rhythm

Target: **45–90 minutes**. Consistency beats marathons.

### Block 0 — Follow-ups (10 min)

Open **`/follow-ups`**.

- Overdue first (red), then due today.  
- For each: act (call / mail / LinkedIn) → log event → set next date.  
- Never skip this block. Broken promises poison reply rates.

### Block 1 — New high-score work (40–60 min)

Open **`/sourcing`**.

Suggested filters for a focused session:

| Filter | Value |
|---|---|
| Sort | Acquisition score |
| Min score | 65 (or 70 if queue is fat) |
| Contact | Has dirigeant (or Needs review if you’re researching) |
| Signal | All, or DECP_WIN if hunting timing |

For each of **8–12 leads**:

1. Skim badges + “why this lead”.  
2. Open company (award history if DECP).  
3. **LinkedIn DM** → confirm the person is still relevant.  
4. If name differs, paste correct name into **Emails** panel.  
5. Generate / pick email → **Use this**.  
6. On detail page: set **informed_at** if first contact.  
7. Send message (outside the tool — your mailbox / LinkedIn).  
8. Back in tool: log **Sent** + next_action “Relance si silence” + date +3–5 days.

### Block 2 — Hygiene (5 min)

- Mark reviewed any dead ends.  
- OptOut anyone who asked.  
- Glance Dashboard only if you have energy left.

**Done.** Close the laptop. Do not “just check one more page of low scores”.

---

## 6. Weekly operating rhythm

| Day | Action |
|---|---|
| **Mon** | Full acquisition run (if not nightly). Work top ACQ. |
| **Tue–Thu** | Follow-ups + top of queue only |
| **Fri** | Dashboard review 15 min; export backup; note what replied |
| **Weekend** | Optional: CSV of wins for a partner / CRM mirror |

### Weekly acquisition commands

From the VPS (or local with network):

```bash
# Balanced top-up
docker compose exec app python -m app.jobs.ingestion --mode full --max-companies 60

# Or split:
docker compose exec app python -m app.jobs.ingestion --mode decp --max-companies 40
docker compose exec app python -m app.jobs.ingestion --mode registry --max-companies 40
```

If nightly ingestion is enabled (`ENABLE_NIGHTLY_INGESTION=true`), Monday can skip the run and go straight to the queue.

---

## 7. How discovery works (so you trust the queue)

### Mode `decp`

1. Downloads consolidated DECP Parquet (data.gouv.fr / ColinMaudry-style pipeline).  
2. Filters last N days (`DECP_DAYS_BACK`, default ~120).  
3. Keeps IT/cyber/digital CPV prefixes + keyword hits in marché object.  
4. Aggregates by SIRET → `award_history`.  
5. Enriches via Annuaire + Sirene.  
6. Upserts as `signal_type=DECP_WIN`, `source=DECP`.

**Best for:** timing, capacity, concrete personalization.

### Mode `registry`

1. Queries Recherche Entreprises (free API).  
2. Prioritizes NAF 62.01 / 62.02 / 62.03 / 62.09 / 63.11 / 63.12.  
3. Pulls **dirigeants** (Président, DG…).  
4. Sirene compliance + size mapping.  
5. Upserts as `signal_type=REGISTRY_IT`, `source=Annuaire`.

**Best for:** volume + named decision-makers.

### Mode `full`

DECP then registry. Use when the queue is thin.

### Deep enrich (per company or bulk)

Annuaire → Sirene → website inference → email candidates → recompute ICP scores → stage update.

Stages:

| Stage | Meaning |
|---|---|
| `discovered` | In system, thin profile |
| `enriched` | Dirigeant and/or registry data present |
| `contact_ready` | Email with decent confidence |
| `in_outreach` | (manual discipline via events) |
| `parked` | You decided later / not fit |

---

## 8. How to rank and prioritize

### Read the score stack

On each sourcing row:

| Label | Meaning |
|---|---|
| **ACQ** | Composite acquisition score (primary sort) |
| **Fit** | ICP match (NAF, size, title) |
| **Time** | Freshness / award pressure |
| **Reach** | How easy contact is |

**Rule of thumb:**

| ACQ | Action |
|---|---|
| ≥ 75 | Work today |
| 60–74 | Work this week |
| 45–59 | Only if queue empty |
| < 45 | Ignore or park |

### Prefer leads that have *both*

1. Timing story (DECP badge / recent award), **and**  
2. Named dirigeant (Reach not zero).

A high Fit with zero contact path is research, not outreach.

### “Why this lead”

Trust badges over gut feel:

- Multi-win streak  
- Hot topic (cyber/digital)  
- SME sweet spot  
- Premium public buyer  
- Verified / likely email  
- DM named  

If you cannot explain the lead in one sentence using a badge, skip it.

---

## 9. From lead → first message (efficient path)

### The 7-step assembly line (per lead)

```
1. Select from high-ACQ queue
2. Read award / NAF / size (30 seconds)
3. LinkedIn confirm dirigeant
4. Generate email candidates (tool)
5. Set informed_at (compliance)
6. Send personalized note (you)
7. Log Sent + next_action_date
```

Time budget: **5–8 minutes per lead** once you’re fluent.  
10 leads ≈ one solid session.

### Personalization that actually matters

Use **one** concrete hook:

| Source | Hook |
|---|---|
| DECP objet | Name the marché / theme (cyber, cloud, TMA…) |
| Acheteur | “Travail avec [ministère / région]…” |
| Multi-win | “Plusieurs attributions récentes…” |
| Size + NAF | “ESN mid-market / 50–150 collab…” |

Avoid: generic “we help companies digitalize”.

### Channels

| Channel | When |
|---|---|
| **LinkedIn** | First touch when email unknown / cold |
| **Email** | When you have a plausible professional address |
| **Phone** | After a reply or for high ACQ + switchboard |

Always set **channel** correctly on the event — Dashboard channel stats depend on it.

---

## 10. Outreach tracking that stays honest

### Event types (lifecycle)

| Event | Meaning |
|---|---|
| `New` | Created / discovered |
| `Sent` | You contacted them |
| `Replied` | They answered (any tone) |
| `PositiveConversation` | Real interest |
| `MeetingBooked` | Calendar win |
| `ProposalSent` | Commercial step |
| `Refused` | Explicit no (add note = objection) |
| `ClosedWon` / `ClosedLost` | Outcome |
| `OptOut` | Stop all outreach |

### Rules that keep data clean

1. **One reality:** status = latest event. Don’t invent a second status.  
2. **Notes on Refuse / ClosedLost** become “common objections” on the Dashboard.  
3. **Every Sent gets a next_action_date** (even “no follow-up — park”).  
4. Kanban drag = event with note “Moved via Kanban” — fine for speed.  
5. After first reply, prefer detail page over quick list actions (richer notes).

### Pipeline columns

| Column | Event types |
|---|---|
| New | New |
| Sent | Sent |
| Replied | Replied, PositiveConversation |
| Meeting | MeetingBooked, ProposalSent |
| Closed | Won, Lost, Refused, OptOut |

---

## 11. Compliance without friction

| Field / action | Rule |
|---|---|
| `data_source` | Always filled (e.g. “DECP consolidated public awards + Sirene”) |
| `informed_at` | Set before or when logging first **Sent** |
| OptOut | Use event type — not a sticky note |
| Partial diffusion | System drops them — don’t force import |
| Exports | Prefer excluding opted-out (default list filters) |

**Practical habit:** when you open the enrich panel for a first touch, set informed_at on the edit form the same day you send.

The API will **reject** `Sent` without `data_source` + `informed_at` — that is intentional.

---

## 12. Dashboard: what to actually look at

| Metric | Decision it drives |
|---|---|
| **New DECP this week** | Is discovery still running? |
| **Needs manual review** | Enrichment debt — bulk deep-enrich |
| **Reply rate by signal type** | Where to spend sourcing time |
| **Reply rate by channel** | LinkedIn vs email mix |
| **Meeting rate** | Funnel health after reply |
| **Common objections** | Message / offer iteration |
| **Follow-ups due** | Operator discipline |

### After 50 outreaches

1. If DECP reply rate ≫ registry → bias weekly runs to DECP.  
2. If registry ≫ DECP → your award personalization may be weak; fix messaging before killing DECP.  
3. If email ≪ LinkedIn → invest in Reacher / better domains, or accept LinkedIn-first.  
4. If objections cluster (“déjà un partenaire”, “pas de budget”) → change offer angle, not volume.

---

## 13. CSV import / export

### Expected columns

**Required:**  
`company_name`, `sector`, `company_size`, `signal_type`, `source`, `data_source`

**Optional:**  
`signal_details`, `decision_maker_name`, `decision_maker_title`, `linkedin_url`, `email`, `phone`, `website`, `notes`

### Allowed enums (must match exactly)

| Field | Values |
|---|---|
| sector | Construction, Manufacturing, Logistics, Engineering, Professional Services, **IT / Digital**, Other |
| company_size | 1-10, 11-50, 51-200, 200+ |
| signal_type | DECP_WIN, BOAMP_WIN, MOROCCO_OPS, PAIN_POST, REGISTRY_IT, OTHER |
| source | DECP, BOAMP, LinkedIn, Manual, Registry, Annuaire |

### Efficient import workflow

1. Import → read **per-row errors** (row N: sector invalid…).  
2. Fix CSV → re-import only failed rows.  
3. Bulk deep-enrich.  
4. Work via Sourcing, not Excel.

### Export

Use list filters then **Export CSV** for partner shares or offline analysis. Keep OptOut discipline — don’t mail merged lists of opted-out contacts.

Sample file: `tests/fixtures/sample_prospects.csv`.

---

## 14. Tuning the machine

### Environment knobs

| Knob | Effect |
|---|---|
| `DECP_DAYS_BACK` | Wider window = more awards, more noise |
| `DECP_MAX_COMPANIES` | Cap nightly load (start 40–80 on small VPS) |
| `SIRENE_DELAY_SECONDS` | Stay under INSEE rate limits (~2.1s) |
| `INGESTION_RUN_CONTACTS` | Heavy; enable when Reacher is up |
| `ENABLE_NIGHTLY_INGESTION` | Auto top-up at 01:00 UTC |

### When to re-score

```bash
python -m app.jobs.ingestion --rescore-only
```

After changing ICP weights in code, or bulk-editing many records.

### When to change ICP code

Only after **≥50–100 real outreaches** with honest signal tags. Premature weight tweaks optimize fiction.

---

## 15. Anti-patterns

| Don’t | Do instead |
|---|---|
| Spray 100 low-score emails/day | 10 high-ACQ personalized touches |
| Skip logging “quick” LinkedIn DMs | Log Sent — future you needs the trail |
| Use status notes instead of events | Append events |
| Import without `data_source` | Always set a real source string |
| Chase 200+ headcount logos | Stay in 11–200 unless strategy changes |
| Ignore Follow-ups for “new leads” | Follow-ups first every day |
| Treat the DB as a vanity metric | Track meetings / reply rate |
| Leave `informed_at` empty forever | Set it on first contact day |
| Run Full ingestion hourly | Nightly or weekly is enough |

---

## 16. 90-day playbook

### Days 1–7 — Install the habit

- Deploy (or run local).  
- One registry + one DECP run.  
- Work **10 leads/day** from Sourcing.  
- Log every touch.  

**Exit criteria:** 50+ events in the log, Follow-ups used daily.

### Days 8–30 — Find the signal

- Keep daily rhythm.  
- Mid-month: first Dashboard review.  
- Double the best signal type for 2 weeks.  

**Exit criteria:** first meetings booked; known best channel.

### Days 31–90 — Systematize

- Nightly ingestion on.  
- Weekly backup cron.  
- Message templates refined from objection table.  
- Optional Reacher if email path is strategic.  

**Exit criteria:** predictable weekly meeting rate; clear “keep / kill” on each source.

---

## 17. FAQ

**Q: The queue is full of companies I don’t want.**  
A: Raise min ACQ score; filter DECP only or Registry only; run bulk mark-reviewed on junk; tighten NAF later in code if systematic.

**Q: No dirigeants on many rows.**  
A: Run **deep enrich** (needs network). Registry mode yields more names than DECP-only.

**Q: Emails all fail / look wrong.**  
A: Confirm domain (website). Paste LinkedIn-accurate name. Enable Reacher only if SMTP port 25 works. Otherwise LinkedIn-first is valid.

**Q: Sent is rejected by the API.**  
A: Set `data_source` and `informed_at` on the prospect first.

**Q: Should I still use a real CRM?**  
A: For late-stage deals, maybe. ProspectForge is the **acquisition front-end**. Export or copy ClosedWon to your CRM if needed — don’t dual-enter early pipeline.

**Q: Can multiple people use it?**  
A: Auth supports multiple users in the DB, but there are no roles yet. Fine for 1–2 people who coordinate; not a multi-team CRM.

**Q: How often to run acquisition?**  
A: Nightly if enabled; otherwise 1–2× per week is enough. More does not mean more meetings.

---

## One-page cheat sheet

```
MORNING
  1. /follow-ups          → clear overdue
  2. /sourcing            → ACQ ≥ 65, has dirigeant
  3. For each top lead:
       LinkedIn → email → informed_at → send → log Sent + next date
  4. Stop at 8–12 quality touches

WEEKLY
  1. Run acquisition (full or decp+registry)
  2. Bulk deep-enrich thin records
  3. Dashboard: double the winning signal
  4. Backup

NEVER
  Skip logging · Skip follow-ups · Spray low scores · Forget OptOut
```

---

*ProspectForge is a lever. The force is still you — applied daily, on the right 10 names.*
