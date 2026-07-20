"""Small, same-domain, robots-aware crawler for official company sources."""

from __future__ import annotations

import asyncio
import hashlib
import heapq
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from urllib.parse import urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx

from app.contact_intelligence.extractors import (
    ParsedPage,
    parse_html_contacts,
    parse_pdf_contacts,
    strip_accents,
)
from app.contact_intelligence.safety import (
    SafeURL,
    UnsafeURLError,
    same_company_host,
    validate_peer_address,
    validate_public_url,
)
from app.contact_intelligence.types import (
    ContactDiscoveryContext,
    ContactSourceResult,
    DomainMatchState,
)

PRIORITY_TERMS = (
    "contact", "equipe", "team", "direction", "dirigeant", "agence", "implantation",
    "service", "maintenance", "sav", "exploitation", "mention", "legal", "about",
    "propos", "recrutement", "carriere", "devis", "intervention", "support", "assistance",
)
ALLOWED_HTML_TYPES = {"text/html", "application/xhtml+xml"}


class CrawlError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CrawlLimits:
    max_pages: int = 12
    max_depth: int = 2
    max_redirects: int = 4
    max_response_bytes: int = 2 * 1024 * 1024
    max_pdf_bytes: int = 8 * 1024 * 1024
    request_timeout_seconds: float = 10.0
    total_timeout_seconds: float = 90.0
    concurrency: int = 2


@dataclass(slots=True)
class CrawlPage:
    url: str
    status_code: int
    content_type: str
    content_hash: str
    parsed: ParsedPage | None


@dataclass(slots=True)
class CrawlResult:
    canonical_url: str | None = None
    domain_match_state: str = DomainMatchState.AMBIGUOUS
    pages: list[CrawlPage] = field(default_factory=list)
    rejected: list[dict[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def page_priority(url: str, anchor: str = "") -> int:
    text = strip_accents(f"{url} {anchor}").lower()
    for index, term in enumerate(PRIORITY_TERMS):
        if term in text:
            return index
    return 100


def company_domain_match(company_name: str, page: ParsedPage, host: str, siren: str | None) -> str:
    def tokens(value: str) -> set[str]:
        normalized = strip_accents(value).lower()
        ignored = {"sas", "sarl", "sa", "eurl", "sasu", "societe", "groupe", "france"}
        return {part for part in re.findall(r"[a-z0-9]{3,}", normalized) if part not in ignored}

    company_tokens = tokens(company_name)
    page_tokens = tokens(f"{page.title} {page.text[:5000]}")
    if siren and siren in re.sub(r"\D", "", page.text):
        return DomainMatchState.EXACT_LEGAL_MATCH
    overlap = len(company_tokens & page_tokens) / max(1, len(company_tokens))
    host_tokens = tokens(host.replace(".", " ").replace("-", " "))
    host_overlap = len(company_tokens & host_tokens) / max(1, len(company_tokens))
    if overlap >= 0.8 or host_overlap >= 0.8:
        return DomainMatchState.STRONG_BRAND_MATCH
    if overlap >= 0.5 or host_overlap >= 0.5:
        return DomainMatchState.PROBABLE
    return DomainMatchState.AMBIGUOUS


class BoundedCrawler:
    def __init__(
        self,
        limits: CrawlLimits | None = None,
        *,
        client: httpx.AsyncClient | None = None,
        enforce_peer_address: bool = True,
    ) -> None:
        self.limits = limits or CrawlLimits()
        self._client = client
        self.enforce_peer_address = enforce_peer_address

    async def _request_once(self, client: httpx.AsyncClient, safe: SafeURL) -> httpx.Response:
        response = await client.get(
            safe.url,
            follow_redirects=False,
            headers={"User-Agent": "ProspectForgeContactResearch/1.0 (+public business pages only)"},
        )
        if self.enforce_peer_address:
            stream = response.extensions.get("network_stream")
            sock = stream.get_extra_info("socket") if stream is not None else None
            peer = sock.getpeername() if sock is not None else None
            validate_peer_address(peer, safe.resolved_addresses)
        return response

    async def _fetch(self, client: httpx.AsyncClient, url: str, canonical_host: str) -> tuple[httpx.Response, str]:
        current = url
        for _redirect in range(self.limits.max_redirects + 1):
            safe = await validate_public_url(current)
            if not same_company_host(safe.url, canonical_host):
                raise UnsafeURLError("cross_domain_redirect")
            response = await self._request_once(client, safe)
            if response.status_code not in {301, 302, 303, 307, 308}:
                return response, safe.url
            location = response.headers.get("location")
            if not location:
                raise CrawlError("redirect_without_location")
            current = str(response.url.join(location))
        raise CrawlError("redirect_limit_exceeded")

    async def _read_bounded(self, response: httpx.Response, maximum: int | None = None) -> bytes:
        maximum = maximum or self.limits.max_response_bytes
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > maximum:
            raise CrawlError("response_too_large")
        body = response.content
        if len(body) > maximum:
            raise CrawlError("response_too_large")
        return body

    async def crawl(self, context: ContactDiscoveryContext) -> CrawlResult:
        if not context.website:
            return CrawlResult(warnings=["no_website"])
        first_safe = await validate_public_url(context.website)
        canonical_host = first_safe.host.removeprefix("www.")
        timeout = httpx.Timeout(self.limits.request_timeout_seconds)
        own_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=timeout)
        started = time.monotonic()
        result = CrawlResult(canonical_url=first_safe.url)
        try:
            robots = RobotFileParser()
            robots_url = urlunsplit((urlsplit(first_safe.url).scheme, urlsplit(first_safe.url).netloc, "/robots.txt", "", ""))
            try:
                robots_response, _ = await self._fetch(client, robots_url, canonical_host)
                if robots_response.status_code == 200:
                    robots.parse(robots_response.text[:200_000].splitlines())
                else:
                    robots.parse([])
            except (httpx.HTTPError, UnsafeURLError, CrawlError, ValueError):
                robots.parse([])
                result.warnings.append("robots_unavailable")

            queue: list[tuple[int, int, str]] = [(0, 0, first_safe.url)]
            sitemap_url = urlunsplit((urlsplit(first_safe.url).scheme, urlsplit(first_safe.url).netloc, "/sitemap.xml", "", ""))
            try:
                sitemap_response, _ = await self._fetch(client, sitemap_url, canonical_host)
                if sitemap_response.status_code == 200:
                    sitemap_body = await self._read_bounded(sitemap_response)
                    root = ET.fromstring(sitemap_body)
                    for element in root.iter():
                        if element.tag.rsplit("}", 1)[-1] == "loc" and element.text:
                            candidate = element.text.strip()
                            if same_company_host(candidate, canonical_host):
                                heapq.heappush(queue, (page_priority(candidate), 1, candidate))
            except (ET.ParseError, httpx.HTTPError, UnsafeURLError, CrawlError, ValueError):
                result.warnings.append("sitemap_unavailable")
            seen: set[str] = set()
            accepted = 0
            while queue and accepted < self.limits.max_pages:
                if time.monotonic() - started >= self.limits.total_timeout_seconds:
                    result.warnings.append("domain_budget_exhausted")
                    break
                _priority, depth, url = heapq.heappop(queue)
                clean_url = urlunsplit((*urlsplit(url)[:3], urlsplit(url).query, ""))
                if clean_url in seen:
                    continue
                seen.add(clean_url)
                if not same_company_host(clean_url, canonical_host):
                    result.rejected.append({"url": clean_url, "reason": "cross_domain"})
                    continue
                if not robots.can_fetch("ProspectForgeContactResearch/1.0", clean_url):
                    result.rejected.append({"url": clean_url, "reason": "robots_disallow"})
                    continue
                try:
                    response, final_url = await self._fetch(client, clean_url, canonical_host)
                    if response.status_code >= 400:
                        result.rejected.append({"url": clean_url, "reason": f"http_{response.status_code}"})
                        continue
                    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                    if content_type not in ALLOWED_HTML_TYPES and content_type != "application/pdf":
                        result.rejected.append({"url": final_url, "reason": "unsupported_mime"})
                        continue
                    body = await self._read_bounded(
                        response,
                        self.limits.max_pdf_bytes if content_type == "application/pdf" else None,
                    )
                    parsed = (
                        parse_pdf_contacts(body, final_url)
                        if content_type == "application/pdf"
                        else parse_html_contacts(
                            body.decode(response.encoding or "utf-8", errors="replace"), final_url
                        )
                    )
                    result.pages.append(
                        CrawlPage(
                            url=final_url, status_code=response.status_code, content_type=content_type,
                            content_hash=hashlib.sha256(body).hexdigest(), parsed=parsed,
                        )
                    )
                    accepted += 1
                    if accepted == 1:
                        result.canonical_url = final_url
                        result.domain_match_state = company_domain_match(
                            context.company_name, parsed, canonical_host, context.siren
                        )
                        if result.domain_match_state == DomainMatchState.AMBIGUOUS:
                            result.warnings.append("ambiguous_company_domain")
                            break
                    if depth < self.limits.max_depth:
                        for link, anchor in parsed.links:
                            if not same_company_host(link, canonical_host):
                                continue
                            if urlsplit(link).scheme not in {"http", "https"}:
                                continue
                            heapq.heappush(queue, (page_priority(link, anchor), depth + 1, link))
                except (httpx.HTTPError, UnsafeURLError, CrawlError, UnicodeError, ValueError) as exc:
                    result.rejected.append({"url": clean_url, "reason": str(exc)[:80]})
            return result
        finally:
            if own_client:
                await client.aclose()


class OfficialWebsiteAdapter:
    name = "official_website"

    def __init__(self, crawler: BoundedCrawler | None = None) -> None:
        self.crawler = crawler or BoundedCrawler()

    async def discover(self, context: ContactDiscoveryContext) -> ContactSourceResult:
        result = ContactSourceResult()
        try:
            crawl = await asyncio.wait_for(
                self.crawler.crawl(context), timeout=self.crawler.limits.total_timeout_seconds + 2
            )
        except (TimeoutError, UnsafeURLError, CrawlError, httpx.HTTPError) as exc:
            result.errors.append(exc.__class__.__name__)
            result.metrics = {"pages_requested": 0, "pages_accepted": 0, "pages_rejected": 1}
            return result
        if crawl.domain_match_state == DomainMatchState.AMBIGUOUS:
            result.warnings.extend(crawl.warnings)
            result.metrics = {
                "pages_requested": len(crawl.pages) + len(crawl.rejected),
                "pages_accepted": len(crawl.pages),
                "pages_rejected": len(crawl.rejected),
                "domain_match_state": crawl.domain_match_state,
            }
            return result
        person_keys: set[tuple[str, str]] = set()
        point_keys: set[tuple[str, str]] = set()
        evidence_keys: set[tuple[str, str | None, str | None]] = set()
        for page in crawl.pages:
            if page.parsed is None:
                continue
            for person in page.parsed.people:
                key = (person.full_name.lower(), (person.job_title or "").lower())
                if key not in person_keys:
                    person_keys.add(key)
                    result.people.append(person)
            for point in page.parsed.contact_points:
                key = (point.kind, point.value.lower())
                if key not in point_keys:
                    point_keys.add(key)
                    result.contact_points.append(point)
            for evidence in page.parsed.evidence:
                key = (evidence.evidence_type, evidence.source_url, evidence.contact_value or evidence.person_name)
                if key not in evidence_keys:
                    evidence_keys.add(key)
                    evidence.content_hash = page.content_hash
                    result.evidence.append(evidence)
        result.warnings.extend(crawl.warnings)
        result.metrics = {
            "pages_requested": len(crawl.pages) + len(crawl.rejected),
            "pages_accepted": len(crawl.pages),
            "pages_rejected": len(crawl.rejected),
            "domain_match_state": crawl.domain_match_state,
            "canonical_url": crawl.canonical_url,
        }
        return result
