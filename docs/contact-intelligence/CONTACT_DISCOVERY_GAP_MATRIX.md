# Contact discovery gap matrix

| Capability | Starting state | Implemented state | Evidence |
|---|---|---|---|
| Multiple people per company | Missing; registry JSON only | Normalized `contact_people` | `app/models.py`, migration `pfci60_20260720` |
| Multiple contact paths | Candidate JSON plus single Prospect fields | Normalized `contact_points` | `app/models.py` |
| Provenance | No per-contact source record | Deduplicated `contact_evidence` | `service.py` |
| Verification history | Latest JSON overwrote meaning | Append-only verification events | `app/discovery/reacher.py`, `service.py` |
| Run observability | Ingestion-level only | Per-prospect discovery runs and metrics | `ContactDiscoveryRun`, detail UI |
| Official website discovery | Missing | Same-domain bounded crawler | `crawler.py` |
| Domain/company match | Guessed domain accepted | Legal/brand/probable/ambiguous gate | `company_domain_match()` |
| SSRF defense | Missing on website inference/fetch | Scheme, credential, port, DNS, redirect and peer checks | `safety.py` |
| Published email extraction | theHarvester only | HTML, `mailto`, conservative obfuscation, JSON text | `extractors.py` |
| PDF contacts | Missing | Text-only bounded official PDF parser | `parse_pdf_contacts()` |
| Business phones | Weak single field | Normalized source-backed phone points | `normalize_phone()` |
| Contact forms | Missing | Detected, classified, never submitted | `extractors.py` |
| Person/role extraction | Registry dirigeants only | JSON-LD and deterministic French role extraction | `extractors.py` |
| Pattern learning | Missing | Published same-domain evidence threshold | `patterns.py` |
| Candidate honesty | SMTP could imply usable | Guesses remain manual review | `confidence.py`, regressions |
| DNS/MX | Missing | Cached bounded MX validation | `dns.py` |
| Reacher privacy | Floating image; full email logs | Version-pinned private service; hashed log ID | compose, `reacher.py` |
| Manual LinkedIn | Search link only | Search plus auditable URL/identity confirmation | detail UI and review route |
| Task workflow | Generic research tasks | Deduplicated contact-specific tasks | `_sync_tasks()` |
| Compatibility | Prospect authoritative | Normalized tables authoritative; safe projection | `project_primary_contact_to_prospect()` |
| Scheduler | Contact work tied to ingestion | Separate capped, isolated nightly job | `app/jobs/contact_discovery.py` |
| Live pilot | Six-candidate observation only | Not run; VPS unavailable | `PILOT_EVALUATION.md` |
