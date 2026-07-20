# Operator playbook

## Review a dossier

Open the prospect and use **Contact Intelligence**. Read the recommended buyer, recommended path, utility, freshness, source links, and run warnings. A high score does not replace pain, trigger, buyer, contact, proof, and human qualification gates.

## Interpret contact paths

- `usable_personal`: source-backed named-person path; still check context and suppression.
- `usable_role`: public department/role path or operator-assisted phone path.
- `usable_generic`: legitimate company mailbox or contact form, not a named buyer.
- `manual_confirmation_required`: guessed, catch-all, risky, conflicting, or technically indeterminate.
- `verification_required`: potentially strong pattern but missing technical evidence.
- `suppressed`, `invalid`, `stale`: do not use.

## Common actions

- Confirm primary buyer only after the source shows that person belongs to the company and the role is current.
- For LinkedIn, use the manual search link, inspect the profile yourself, then add the public URL and evidence. Do not automate login or messages.
- For catch-all, do not call it verified. Find an official publication, call the switchboard, or use another public path.
- For a generic email, address the relevant department and do not pretend it reaches the named person.
- For a switchboard, ask for the recommended buyer role; record only public business information.
- For a contact form, inspect its category/CAPTCHA and submit manually only when outreach is separately authorized.
- Reject false identities or points; the rejection prevents weaker automation from resurrecting them.
- Suppress a contact immediately on opt-out or other suppression reason.
- Refresh only stale dossiers; nightly jobs skip fresh completed runs.

## Contact-ready decision

Contact discovery creates research paths. Email-send readiness requires the approved utility policy, global suppression clearance, first-contact disclosure, and the existing strict human qualification gate. The system never sends automatically.
