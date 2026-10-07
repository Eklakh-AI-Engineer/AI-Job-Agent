"""SSRF-safe validation for server-side URL fetches.

The validator fails closed for local/private/link-local destinations. It also
resolves hostnames before use to reduce DNS-rebinding exposure. Callers that
accept arbitrary external URLs should validate immediately before opening a
network/browser connection.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


class UnsafeURL(ValueError):
    """Raised when a URL targets a disallowed destination."""


def _is_public_ip(value: str, *, allow_loopback: bool = False) -> bool:
    ip = ipaddress.ip_address(value)
    if allow_loopback and ip.is_loopback:
        return True
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_unspecified
        or ip.is_reserved
    )


def validate_public_url(url: str, *, allow_loopback: bool = False) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeURL("Only http and https URLs are allowed")
    if parsed.username or parsed.password:
        raise UnsafeURL("Userinfo in URLs is not allowed")
    hostname = parsed.hostname
    if not hostname:
        raise UnsafeURL("URL must contain a hostname")

    lowered = hostname.rstrip(".").casefold()
    if lowered in {"localhost", "localhost.localdomain"} or lowered.endswith(".localhost"):
        if not allow_loopback:
            raise UnsafeURL("Localhost destinations are not allowed")

    try:
        addresses = {
            info[4][0]
            for info in socket.getaddrinfo(lowered, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
        }
    except socket.gaierror as exc:
        raise UnsafeURL(f"Could not resolve URL host: {hostname}") from exc

    if not addresses or not all(_is_public_ip(address, allow_loopback=allow_loopback) for address in addresses):
        raise UnsafeURL("URL resolves to a non-public network address")

    return url
