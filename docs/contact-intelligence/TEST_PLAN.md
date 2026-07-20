# Test plan

## Automated suites

- Pure parsing and confidence: sanitized team, contact, agency, legal, JSON-LD, obfuscated, generic-only, empty, and malformed fixtures.
- Pattern learning: generic exclusion, evidence thresholds, bounded fallback.
- SSRF: schemes, credentials, ports, hostnames, IPv4/IPv6 ranges, mixed DNS answers, peer rebinding, body limits.
- Persistence: person/point/evidence deduplication, run records, task deduplication, manual precedence, projection.
- Compliance: suppression gate, guessed-only non-usability, catch-all review, no `Sent` events.
- Existing regression suite: discovery, scoring, strict pain/human gates, API, UI authentication, messaging, DECP and registry behavior.

## Commands and recorded results

```text
TEST_DATABASE_URL=<disposable PostgreSQL 16 URL> PYTHONPATH=. pytest -q
140 passed, 1 deprecation warning, 39.38s

ruff check .
passed

python -m compileall -q app tests alembic
passed during implementation; rerun in final release gate

alembic upgrade head on empty PostgreSQL 16
passed through pfci60_20260720

alembic downgrade 005; alembic upgrade head
passed

Production image build
passed; image ID b46a80197c9a9d1da7016c9f844ffb630eb6a2876ad76a0c696a67b1d028408c

scripts/release-gate.sh
passed, including assets, npm audit (0 vulnerabilities), tests, lint, compile, Compose, and Caddy validation

scripts/smoke-production.sh
passed with PostgreSQL 16, Caddy, migration head, health/readiness, backup, and restore checks
```

The host sandbox cannot run `aiosqlite`: even a bare in-memory connection blocks. Database tests were therefore run against the production database engine, PostgreSQL 16. The application remains SQLite-capable for development.

## Remaining gates

Live production health/login/docs checks, production scheduler inspection, migration-lineage reconciliation, and a real 20-prospect pilot remain required before deployment authorization.
