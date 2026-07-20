# Implementation plan and status

## Completed reversible repository work

- [x] Phase 0: local repository comprehension and baseline evidence
- [x] Phase 1: current contact-flow audit
- [x] Phase 2: normalized architecture, confidence model, and migration
- [x] Phase 3: official HTML/PDF adapter, extraction, patterns, DNS, Reacher hardening, persistence, projection
- [x] Phase 4: SSRF and adversarial tests
- [x] Phase 5: authenticated detail UI, manual reviews, tasks, scheduler, observability
- [x] PostgreSQL 16 fresh migration and `005` upgrade/downgrade test
- [x] Python 3.12/PostgreSQL test suite

## Pending external/production work

- [ ] Reconcile the unavailable `/opt/prospectforge` worktree and `pfcc50_20260720` migration with this branch.
- [ ] Inspect live image IDs, health, scheduler, Reacher, schema, and contact metrics without exposing data.
- [ ] Back up production before migration.
- [ ] Run the controlled 20-prospect pilot on authorized, non-suppressed production records.
- [ ] Manually audit the pilot gold set.
- [ ] Deploy only after explicit authorization changes `DEPLOY_NOW` from `no`.

No paid service, outreach, DNS change, public-port change, LinkedIn automation, or production mutation is part of the completed work.
