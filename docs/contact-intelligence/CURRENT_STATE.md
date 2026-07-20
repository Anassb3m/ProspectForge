# Current state

Recorded 2026-07-20 from `/home/anass/Documents/Systems/ProspectForge`.

## Repository baseline

- Branch: `antigravity/prospectforge-production-pilot`
- Starting commit: `5a3123f10930cd9120456d4d3055e3012896e51d`
- Starting worktree: clean
- Local Alembic head before this change: `005`
- Production checkout requested by the execution brief: `/opt/prospectforge`
- Production checkout result: not present in this environment

The brief reports production revision `pfcc50_20260720`, but that revision is not in this repository. Deployment must stop until the accepted VPS changes and migration lineage are reconciled. No `.env`, production rows, provider payloads, or contact values were inspected or copied.

## Legacy contact flow

Evidence: `app/discovery/contacts.py`, `app/discovery/emails.py`, `app/discovery/reacher.py`, `app/discovery/enrich.py`, `app/jobs/enrichment.py`, and `app/routers/sourcing.py` at the starting commit.

```text
registry dirigeant or operator name
→ guessed website/domain
→ email permutations and role mailboxes
→ optional theHarvester
→ optional Reacher mailbox check
→ JSON candidates on Prospect
→ optional application to Prospect.email
→ commercial-state recomputation
```

Why the pilot could produce candidates but apply no usable email:

1. There was no official-site crawler or published-contact extraction.
2. Candidate generation started from name permutations, not observed company patterns.
3. theHarvester was disabled in accepted production settings.
4. Reacher was disabled or returned an error/indeterminate result; the old logger could emit a blank exception string and logged the full address.
5. `check_emails_batch()` stopped only on `verified`, while its normalizer normally returned `deliverable`.
6. The safe UI/API path used `apply_best=False` or required explicit operator application.
7. The schema could not distinguish mailbox acceptance from person ownership.
8. Candidates existed only in `Prospect.contact_candidates` JSON and had no source evidence.

## Current implementation state

Normalized people, contact points, evidence, verification events, discovery runs, and manual reviews are now implemented. Official-site HTML/PDF extraction, conservative obfuscation, forms, phones, people/roles, same-domain pattern learning, DNS/MX checks, Reacher verification, task creation, compatibility projection, detail UI, scheduler batch caps, and SSRF controls are implemented.

Production state, live pilot metrics, production scheduler status, production image IDs, and current production contact metrics remain unverified because `/opt/prospectforge` and the VPS are unavailable.
