"""
backend/app/agents/politeness.py

Politeness controls for browser automation against third-party sites:

- :class:`DomainRateLimiter` — enforces a minimum interval between requests to
  the same host (async-safe, per-process).
- :func:`is_allowed_by_robots` — checks a URL against the host's ``robots.txt``
  before any navigation.

These are intentionally conservative defaults. Automation must respect the
terms of service of the target platform; this module makes the *respectful*
path the easy path.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger(__name__)


class DomainRateLimiter:
    """Async per-domain rate limiter (minimum interval between requests)."""

    def __init__(self, min_interval_seconds: float = 5.0, max_concurrency: int = 1):
        self.min_interval = min_interval_seconds
        self.max_concurrency = max_concurrency
        self._last_request: Dict[str, float] = {}
        self._semaphores: Dict[str, asyncio.Semaphore] = {}
        self._lock = asyncio.Lock()

    def _semaphore(self, host: str) -> asyncio.Semaphore:
        if host not in self._semaphores:
            self._semaphores[host] = asyncio.Semaphore(self.max_concurrency)
        return self._semaphores[host]

    async def acquire(self, host: str) -> None:
        """Wait until a request to ``host`` is permitted."""
        sem = self._semaphore(host)
        await sem.acquire()
        async with self._lock:
            last = self._last_request.get(host, 0.0)
            now = time.monotonic()
            wait = self.min_interval - (now - last)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_request[host] = time.monotonic()

    def release(self, host: str) -> None:
        sem = self._semaphores.get(host)
        if sem is not None:
            sem.release()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


# Global default limiter (5s between hits to the same host).
_default_limiter: Optional[DomainRateLimiter] = None


def get_rate_limiter() -> DomainRateLimiter:
    global _default_limiter
    if _default_limiter is None:
        _default_limiter = DomainRateLimiter(min_interval_seconds=5.0)
    return _default_limiter


_robots_cache: Dict[str, Optional[RobotFileParser]] = {}


async def _load_robots(host_root: str) -> Optional[RobotFileParser]:
    if host_root in _robots_cache:
        return _robots_cache[host_root]

    robots_url = urljoin(host_root, "/robots.txt")
    parser: Optional[RobotFileParser] = None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(robots_url)
            if response.status_code == 200:
                parser = RobotFileParser()
                parser.parse(response.text.splitlines())
            else:
                # No robots.txt (or inaccessible) -> treat as allowed.
                parser = None
    except Exception as exc:  # noqa: BLE001 - network failure must not block
        logger.warning(f"Could not fetch robots.txt for {host_root}: {exc}")
        parser = None

    _robots_cache[host_root] = parser
    return parser


async def is_allowed_by_robots(url: str, user_agent: str = "*") -> bool:
    """
    Return True if ``url`` is permitted by the host's robots.txt.

    Network failures fail *open* (allowed) so automation is not blocked by a
    transient robots.txt fetch error, but a disallow rule is always honoured.
    """
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return True
        host_root = f"{parsed.scheme}://{parsed.netloc}"
    except Exception:  # noqa: BLE001
        return True

    parser = await _load_robots(host_root)
    if parser is None:
        return True
    allowed = parser.can_fetch(user_agent, url)
    if not allowed:
        logger.warning(f"robots.txt disallows fetching {url}")
    return allowed


def reset_robots_cache() -> None:
    """Clear the robots.txt cache (for tests)."""
    _robots_cache.clear()