# Known limitations

1. Production state is unverified: `/opt/prospectforge` and reported revision `pfcc50_20260720` are unavailable.
2. No live 20-prospect pilot has run; precision and coverage targets are not claimed.
3. Deterministic person extraction favors precision and may miss unconventional layouts or JavaScript-rendered content. Page JavaScript is deliberately not executed.
4. PDF extraction is text-only. Scanned documents require manual review; OCR is not included.
5. Exact-host crawling may miss legitimate related subdomains. They must be explicitly validated in a future change.
6. DNS cache is process-local. Multi-instance deployments would benefit from a shared cache, though this deployment uses one scheduler instance.
7. Reacher depends on outbound SMTP availability and cannot establish person ownership. Catch-all and ambiguous results remain manual.
8. External search-provider support is not enabled; no paid service or key was authorized.
9. theHarvester remains disabled and non-authoritative.
10. Buyer ranking is deterministic French terminology, not an AI semantic model. Operators must correct unusual titles.
11. The current manual-source form stores the operator identity on the subsequent review record; the evidence row identifies manual entry but does not duplicate the operator email.
12. Existing legacy contact endpoints remain for compatibility but refuse Reacher-only/guessed promotion without source-backed review.
