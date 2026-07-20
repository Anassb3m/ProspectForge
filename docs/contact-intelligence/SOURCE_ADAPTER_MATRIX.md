# Source adapter matrix

| Adapter | Default | Data | Strength | Bounds / failure |
|---|---:|---|---|---|
| Official website | Enabled | pages, people, email, phone, forms, LinkedIn links | Highest automated source | 12 pages, depth 2, 90 seconds, same domain, robots |
| Official PDF | Enabled within website adapter | text-only people/contact facts | Strong official source | 8 MB, 30 pages, no OCR, no attachments |
| Public registry | Enabled from existing prospect data | legal representatives | Strong identity, weaker buyer relevance | 20 entries; never assumed operational buyer |
| DNS/MX | Enabled | domain mail capability | Technical only | cached, five-second lookup |
| Reacher | Configuration-gated | mailbox behavior | Technical only | private, concurrency 2, timeout, circuit breaker |
| Domain pattern | Enabled after official extraction | inferred candidate | Inference | six candidates; two observations needed for confirmed pattern |
| Manual operator | Enabled | source URL, profile, phone, form, email | Highest precedence | authenticated, CSRF, audited |
| Search provider | Interface deferred | result links/snippets | Weak until official page opened | disabled; no key or paid service authorized |
| theHarvester | Disabled | open-web email hints | Weak and inconsistent provenance | retained only as legacy optional code; not authoritative |

theHarvester remains disabled because it is not installed in the production image, its free backends are unstable, and its results do not provide sufficient page-level provenance. The deterministic official-source adapter replaces its core role.
