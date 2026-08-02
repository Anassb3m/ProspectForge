#!/usr/bin/env python3
"""Non-persisting live smoke for public, source-backed contact extraction.

The report contains aggregate states only; it never prints discovered contact
values. Reacher/SMTP is deliberately outside this identity/source test.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections import Counter

# The smoke never opens the application database. Pin non-production settings
# before importing the contact package so an unrelated host .env cannot make a
# read-only diagnostic fail validation or point it at production services.
os.environ["DEBUG"] = "false"
os.environ["ENVIRONMENT"] = "test"

from app.contact_intelligence.crawler import (
    BoundedCrawler,
    CrawlLimits,
    OfficialWebsiteAdapter,
)
from app.contact_intelligence.types import ContactDiscoveryContext


async def run(company_name: str, website: str, max_pages: int) -> dict[str, object]:
    adapter = OfficialWebsiteAdapter(
        BoundedCrawler(
            CrawlLimits(
                max_pages=max_pages,
                max_depth=2,
                request_timeout_seconds=15,
                total_timeout_seconds=90,
                concurrency=2,
            )
        )
    )
    result = await adapter.discover(
        ContactDiscoveryContext(
            prospect_id=0,
            company_name=company_name,
            website=website,
        )
    )
    return {
        "company": company_name,
        "canonical_url": result.metrics.get("canonical_url"),
        "domain_match_state": result.metrics.get("domain_match_state"),
        "pages_requested": result.metrics.get("pages_requested", 0),
        "pages_accepted": result.metrics.get("pages_accepted", 0),
        "pages_rejected": result.metrics.get("pages_rejected", 0),
        "rejection_reasons": result.metrics.get("rejection_reasons", {}),
        "people_found": len(result.people),
        "contact_points_found": len(result.contact_points),
        "contact_kinds": dict(Counter(point.kind for point in result.contact_points)),
        "publication_states": dict(
            Counter(str(point.publication_state) for point in result.contact_points)
        ),
        "person_match_states": dict(
            Counter(str(point.person_match_state) for point in result.contact_points)
        ),
        "evidence_items": len(result.evidence),
        "warnings": result.warnings,
        "errors": result.errors,
        "contact_values_redacted": True,
        "reacher_used": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--company", required=True)
    parser.add_argument("--website", required=True)
    parser.add_argument("--max-pages", type=int, default=6, choices=range(1, 13))
    args = parser.parse_args()
    report = asyncio.run(run(args.company, args.website, args.max_pages))
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["errors"] or int(report["pages_accepted"]) == 0:
        raise SystemExit(1)
    if int(report["contact_points_found"]) == 0:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
