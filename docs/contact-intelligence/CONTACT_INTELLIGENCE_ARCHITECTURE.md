# Contact intelligence architecture

## Components

```mermaid
flowchart LR
    UI[Authenticated operator UI] --> ORCH[Discovery orchestrator]
    JOB[Bounded nightly job] --> ORCH
    ORCH --> SAFE[URL and SSRF gate]
    SAFE --> WEB[Official website adapter]
    WEB --> HTML[HTML and JSON-LD parser]
    WEB --> PDF[Bounded PDF text parser]
    ORCH --> REG[Existing public registry dirigeants]
    ORCH --> PAT[Published pattern learner]
    ORCH --> DNS[DNS and MX validation]
    ORCH --> REACHER[Private Reacher verification]
    ORCH --> DB[(PostgreSQL normalized dossier)]
    DB --> PROJ[Compatibility projection]
    PROJ --> SCORE[Strict commercial scoring]
    DB --> TASKS[Deduplicated operator tasks]
```

## Data flow

```mermaid
sequenceDiagram
    participant O as Operator or scheduler
    participant R as Orchestrator
    participant W as Official source adapter
    participant V as DNS/Reacher
    participant D as PostgreSQL
    O->>R: Run eligible prospect
    R->>D: Acquire advisory lock and lease
    R->>W: Bounded same-domain discovery
    W-->>R: People, points, evidence, metrics
    R->>R: Merge registry and learn patterns
    R->>V: Verify strongest bounded candidates
    V-->>R: Technical states only
    R->>D: Idempotent merge and verification history
    R->>D: Select primary path and create tasks
    R->>D: Project safe legacy fields and rescore
```

## Trust boundaries

1. Browser to application: authenticated; HTML state changes pass CSRF middleware and server validation.
2. Application to public web: hostile input boundary; no JavaScript execution, private addresses blocked, redirects revalidated, bodies and MIME types bounded.
3. Application to Reacher: private Compose network only; minimal address input, normalized summary output, no raw payload persistence.
4. Application to PostgreSQL: normalized dossier is authoritative; manual facts outrank automation.
5. Human research: LinkedIn is manual only. The system creates search paths and records operator confirmation; it does not log in, scrape, connect, or message.

## Failure behavior

- One adapter failure is recorded on the run and does not erase existing facts.
- Reacher failure leaves website contacts available and guessed mailboxes unpromoted.
- Ambiguous company/domain match stops site fact application.
- Active lease rejects a duplicate run.
- Per-prospect nightly errors roll back that prospect and continue the batch.
- Suppression prevents discovery and cancels contact-intelligence tasks.
