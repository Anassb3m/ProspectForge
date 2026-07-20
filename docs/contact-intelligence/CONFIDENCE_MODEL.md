# Confidence model

The engine stores independent dimensions; SMTP results never stand in for identity.

| Dimension | Allowed states |
|---|---|
| Publication | `published_personal`, `published_role`, `published_generic`, `not_published`, `unknown` |
| Deliverability | `deliverable`, `catch_all`, `risky`, `invalid`, `indeterminate`, `unchecked`, `error` |
| Person match | `exact_person_published`, `exact_person_pattern_confirmed`, `strong_person_match`, `role_mailbox`, `generic_company_mailbox`, `pattern_inferred`, `name_only_guess`, `conflicting`, `unknown` |
| Utility | `usable_personal`, `usable_role`, `usable_generic`, `manual_confirmation_required`, `verification_required`, `invalid`, `suppressed`, `stale`, `no_contact` |

Key rules implemented in `app/contact_intelligence/confidence.py`:

- Published exact personal contact can be usable even before Reacher, subject to suppression/freshness.
- A name-only guessed address remains `manual_confirmation_required` even when Reacher says deliverable.
- Catch-all, risky, indeterminate, and provider errors require manual confirmation.
- Published role and generic mailboxes are legitimate paths but are not represented as named-person mailboxes.
- A pattern-confirmed address needs at least two same-domain published-person observations and a deliverable result before personal usability.
- Suppression and staleness override other positive states.

Merge precedence is manual confirmation, official page, structured data, official PDF, public registry, pattern inference, technical verification, weak inference, legacy guess.
