"""SSRF-resistant URL validation for public company-site fetching."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit


class UnsafeURLError(ValueError):
    pass


BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "db",
    "app",
    "reacher",
    "caddy",
    "host.docker.internal",
    "gateway.docker.internal",
    "metadata.google.internal",
}
ALLOWED_PORTS = {None, 80, 443}


@dataclass(frozen=True, slots=True)
class SafeURL:
    url: str
    host: str
    port: int | None
    resolved_addresses: frozenset[str]


def is_public_ip(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return bool(
        address.is_global
        and not address.is_loopback
        and not address.is_private
        and not address.is_link_local
        and not address.is_multicast
        and not address.is_unspecified
        and not address.is_reserved
    )


def normalize_http_url(value: str, *, base: str | None = None) -> str:
    candidate = urljoin(base, value.strip()) if base else value.strip()
    if not candidate:
        raise UnsafeURLError("empty_url")
    if "://" not in candidate:
        candidate = "https://" + candidate
    parsed = urlsplit(candidate)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise UnsafeURLError("unsupported_scheme")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeURLError("embedded_credentials")
    try:
        port = parsed.port
    except ValueError as exc:
        raise UnsafeURLError("invalid_port") from exc
    if port not in ALLOWED_PORTS:
        raise UnsafeURLError("port_not_allowed")
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host or host in BLOCKED_HOSTNAMES or "." not in host:
        raise UnsafeURLError("blocked_hostname")
    if host.endswith((".local", ".internal", ".localhost")):
        raise UnsafeURLError("blocked_hostname")
    try:
        ascii_host = host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise UnsafeURLError("invalid_idn") from exc
    netloc = ascii_host
    default_port = 80 if parsed.scheme.lower() == "http" else 443
    if port and port != default_port:
        netloc = f"{ascii_host}:{port}"
    path = parsed.path or "/"
    return urlunsplit((parsed.scheme.lower(), netloc, path, parsed.query, ""))


async def _resolve(host: str, port: int) -> set[str]:
    loop = asyncio.get_running_loop()
    try:
        records = await loop.getaddrinfo(
            host, port, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM
        )
    except socket.gaierror as exc:
        raise UnsafeURLError("dns_resolution_failed") from exc
    return {str(record[4][0]).split("%", 1)[0] for record in records}


async def validate_public_url(value: str, *, base: str | None = None) -> SafeURL:
    url = normalize_http_url(value, base=base)
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        addresses = {str(literal)}
    else:
        addresses = await _resolve(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    if not addresses or any(not is_public_ip(address) for address in addresses):
        raise UnsafeURLError("non_public_address")
    return SafeURL(url=url, host=host, port=parsed.port, resolved_addresses=frozenset(addresses))


def validate_peer_address(peer: object, expected: frozenset[str]) -> None:
    """Reject a peer that differs from the preflight public DNS result (rebinding guard)."""
    if not peer:
        raise UnsafeURLError("peer_address_unavailable")
    address = str(peer[0] if isinstance(peer, tuple) else peer).split("%", 1)[0]
    if not is_public_ip(address) or address not in expected:
        raise UnsafeURLError("dns_rebinding_or_private_peer")


def same_company_host(candidate: str, canonical_host: str) -> bool:
    """Allow only the exact canonical host and its www spelling."""
    try:
        host = (urlsplit(candidate).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return False
    return host == canonical_host.lower().removeprefix("www.")
