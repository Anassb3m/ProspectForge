# Compliance and provenance

This is an engineering control record, not legal advice.

- Only public business-relevant facts are collected.
- Every stored automated fact has a source adapter, retrieval time, evidence fingerprint, and source URL or an explicit public-registry provenance marker.
- Inferred addresses are labeled `not_published` with inference metadata.
- LinkedIn research is manual; there is no scraper, login automation, connection request, or messaging code.
- Contact forms are detected but never submitted.
- Discovery never creates a `Sent` event; a regression counts sent events before and after a run.
- Existing global email/domain/SIREN suppression is checked before discovery and for each point.
- Opt-out and anonymized prospects are ineligible; suppression cancels open contact tasks.
- Manual confirmations, corrections, rejections, primary selection, and suppression create audit records.
- Broad queue and sourcing lists redact email local parts; complete values are limited to authenticated prospect detail/edit workflows.
- Provider raw bodies and full page bodies are not persisted.
- Existing retention/anonymization and first-contact disclosure gates remain in place.
