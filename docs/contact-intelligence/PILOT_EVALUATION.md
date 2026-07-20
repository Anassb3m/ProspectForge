# Pilot evaluation

Status: **not run**.

Reason: `DEPLOY_NOW=no`, `/opt/prospectforge` is unavailable, and no authorized production dataset is accessible in this environment. Fabricating contacts or pilot success is prohibited.

## Required sample

Twenty non-suppressed prospects covering DECP/registry, website/no website, small/larger companies, ambiguous brands, catch-all, team page, and contact-form-only outcomes.

## Aggregate metrics to record

Eligible prospects; confirmed/ambiguous/rejected domains; pages examined; people and relevant buyers; published personal/role/generic emails; phones; forms; inferred candidates; MX and Reacher states; utility paths; no-contact outcomes; operator corrections; runtime; adapter errors; duplicate counts; and sent-event delta.

## Gold-set review

For every prospect, manually record domain correctness, company membership, role correctness, buyer relevance, publication/person match, phone/form legitimacy, utility honesty, and correction. Compute domain, person, role, buyer, published-contact, and usable-contact precision plus false-positive and manual-review rates.

## Acceptance invariants

- All facts have source or explicit inference provenance.
- Guesses never become verified-person facts.
- Catch-all always requires review.
- No suppression bypass, duplicate dossier facts/tasks, weak overwrite, outreach event, LinkedIn automation, or private-network fetch.

Coverage targets will be evaluated only after the authorized pilot. They are not claimed here.
