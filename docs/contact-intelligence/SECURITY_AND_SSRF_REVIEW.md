# Security and SSRF review

## Controls

- Only HTTP and HTTPS are accepted.
- Embedded credentials, unusual ports, localhost, Compose service names, `.local`, `.internal`, and non-host URLs are rejected.
- DNS is resolved before each request. Any private, loopback, link-local, multicast, unspecified, or reserved answer rejects the host.
- The connected peer must be public and in the preflight answer set, protecting against DNS rebinding.
- Every redirect is resolved and revalidated; cross-company redirects are rejected.
- Crawling is exact-domain/`www` only, depth two, twelve pages, four redirects, two-megabyte HTML, eight-megabyte PDF, ten seconds per request, ninety seconds total.
- MIME allowlist is HTML/XHTML/PDF. No JavaScript is executed. Archives are not unpacked. Forms are never submitted.
- robots.txt is evaluated; disallowed pages are recorded and skipped.
- Extracted excerpts are short and escaped by Jinja. Email evidence excerpts are redacted.
- Reacher logs an irreversible address correlation ID, error category, and retryability; it does not log full addresses or raw responses.

## Tests

`tests/test_contact_intelligence.py` covers loopback, private IPv4/IPv6, link-local metadata, service hostnames, schemes, credentials, ports, mixed public/private DNS, peer rebinding, redirects to private targets, redirect limits, robots exclusions, unsupported MIME types, and oversized bodies. The full PostgreSQL-backed suite passed 140 tests on 2026-07-20.

## Residual risks

- A registrable-domain/public-suffix library is not used; the crawler intentionally uses the stricter exact host plus `www` rule.
- Robots failure defaults to narrow public crawling and records a warning. Operators may choose not to run affected domains.
- PDF parsing is complex third-party input. Size/page caps and no OCR reduce, but do not eliminate, parser risk.
