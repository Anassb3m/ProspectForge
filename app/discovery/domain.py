"""Domain candidate abstraction, verification waterfall, and SSRF-safe web crawler."""

import asyncio
import ipaddress
import logging
import socket
from urllib.parse import urlparse
import httpx
from typing import Optional, List

logger = logging.getLogger(__name__)

class SSRFBlockedError(Exception):
    """Raised when a resolved IP is in a private/reserved range."""
    pass

def _is_ip_private(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved
    except ValueError:
        return True

async def resolve_ssrf_safe(hostname: str) -> str:
    """Resolve a hostname and raise SSRFBlockedError if it resolves to a private IP."""
    loop = asyncio.get_running_loop()
    try:
        # resolve hostname
        addr_info = await loop.getaddrinfo(hostname, None, family=socket.AF_INET)
    except socket.gaierror:
        raise ValueError(f"Could not resolve hostname {hostname}")
    
    if not addr_info:
        raise ValueError(f"No A records found for {hostname}")
        
    ip = addr_info[0][4][0]
    if _is_ip_private(ip):
        raise SSRFBlockedError(f"Hostname {hostname} resolved to private/reserved IP: {ip}")
    
    return ip

class BoundedWebCrawler:
    """SSRF-safe crawler that checks IPs before connecting."""
    
    def __init__(self, timeout: float = 10.0, max_redirects: int = 3):
        self.timeout = timeout
        self.max_redirects = max_redirects

    async def fetch(self, url: str) -> str:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            raise ValueError(f"Invalid URL: {url}")
            
        await resolve_ssrf_safe(hostname)
        
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, max_redirects=self.max_redirects) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            
            # verify final URL is also safe after redirects
            final_host = urlparse(str(resp.url)).hostname
            if final_host and final_host != hostname:
                await resolve_ssrf_safe(final_host)
                
            return resp.text

class DomainCandidateProvider:
    """Provider to generate domain candidates for a company name."""
    
    async def get_candidates(self, company_name: str) -> List[str]:
        """Generate possible domain names for a company."""
        # Clean company name
        clean_name = company_name.lower().replace(" ", "").replace("-", "").replace(".", "")
        return [
            f"{clean_name}.com",
            f"{clean_name}.fr",
            f"{clean_name}.co.uk",
            f"{clean_name}.net",
            f"{clean_name}.io"
        ]

class DomainVerifier:
    """Waterfall logic to verify domain ownership and relevance."""
    
    def __init__(self):
        self.crawler = BoundedWebCrawler()
        self.provider = DomainCandidateProvider()
        
    async def find_valid_domain(self, company_name: str) -> Optional[str]:
        candidates = await self.provider.get_candidates(company_name)
        
        for candidate in candidates:
            try:
                url = f"https://{candidate}"
                logger.info(f"Verifying domain candidate: {url}")
                html = await self.crawler.fetch(url)
                
                # Check relevance (rudimentary)
                if company_name.split()[0].lower() in html.lower():
                    logger.info(f"Verified domain: {candidate}")
                    return candidate
            except (SSRFBlockedError, ValueError, httpx.RequestError) as e:
                logger.debug(f"Candidate {candidate} failed: {e}")
                continue
                
        return None
