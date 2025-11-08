"""Utilities for managing parser proxy rotation and state tracking."""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Protocol, Sequence

from aiohttp import BasicAuth

from .wb_parser.excs import ParserProxyUnavailableError

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ParserProxy:
    """Representation of a proxy used for parsing requests."""

    id: int
    host: str
    port: int
    scheme: str = "http"
    login: str | None = None
    password: str | None = None
    cooldown_until: dt.datetime | None = None
    success_count: int = 0
    failure_count: int = 0
    rate_limit_count: int = 0

    @property
    def proxy_url(self) -> str:
        """Return the proxy URL that can be passed to aiohttp."""

        return f"{self.scheme}://{self.host}:{self.port}"

    def build_proxy_auth(self) -> BasicAuth | None:
        """Return :class:`aiohttp.BasicAuth` for the proxy if credentials are set."""

        if self.login is None:
            return None
        return BasicAuth(self.login, self.password or "")


class ParserProxyRepository(Protocol):
    """Repository interface used by :class:`ParserProxyManager`."""

    async def list_active(self) -> Sequence[ParserProxy]:  # pragma: no cover - interface definition
        """Return a sequence of active proxies."""

    async def mark_success(self, proxy_id: int) -> ParserProxy | None:  # pragma: no cover - interface definition
        """Persist successful usage of the proxy and return the updated record."""

    async def mark_failure(
        self,
        proxy_id: int,
        *,
        cooldown_until: dt.datetime | None = None,
    ) -> ParserProxy | None:  # pragma: no cover - interface definition
        """Persist a failure for the proxy and optionally apply a cooldown."""

    async def mark_rate_limit(
        self,
        proxy_id: int,
        *,
        cooldown_until: dt.datetime,
    ) -> ParserProxy | None:  # pragma: no cover - interface definition
        """Persist a rate-limit event for the proxy and apply a cooldown."""


class ParserProxyManager:
    """Rotate parser proxies and update their state after requests."""

    def __init__(
        self,
        repository: ParserProxyRepository,
        *,
        reload_interval: dt.timedelta | None = None,
        failure_cooldown: dt.timedelta | None = None,
        rate_limit_cooldown: dt.timedelta | None = None,
    ) -> None:
        self._repository = repository
        self._lock = asyncio.Lock()
        self._reload_interval = reload_interval or dt.timedelta(seconds=30)
        self._failure_cooldown = failure_cooldown or dt.timedelta(seconds=120)
        self._rate_limit_cooldown = rate_limit_cooldown or dt.timedelta(minutes=5)
        self._proxies: list[ParserProxy] = []
        self._cursor = 0
        self._last_reload_at: dt.datetime | None = None

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[ParserProxy]:
        """Acquire the next available proxy in a rotation-safe manner."""

        async with self._lock:
            proxy = await self._get_next_proxy()
        logger.debug("Acquired parser proxy %s", proxy.id)
        try:
            yield proxy
        finally:
            logger.debug("Released parser proxy %s", proxy.id)

    async def report_success(self, proxy: ParserProxy) -> None:
        """Notify the repository about a successful request."""

        updated = await self._repository.mark_success(proxy.id)
        async with self._lock:
            self._apply_updated_proxy(updated)

    async def report_failure(self, proxy: ParserProxy) -> None:
        """Notify the repository about a failed request."""

        cooldown_until = self._compute_cooldown(self._failure_cooldown)
        updated = await self._repository.mark_failure(
            proxy.id,
            cooldown_until=cooldown_until,
        )
        async with self._lock:
            self._apply_updated_proxy(updated)

    async def report_rate_limit(self, proxy: ParserProxy) -> None:
        """Notify the repository about a rate-limit event and apply cooldown."""

        cooldown_until = self._compute_cooldown(self._rate_limit_cooldown)
        updated = await self._repository.mark_rate_limit(
            proxy.id,
            cooldown_until=cooldown_until,
        )
        async with self._lock:
            self._apply_updated_proxy(updated)

    async def _get_next_proxy(self) -> ParserProxy:
        await self._reload_if_needed()
        if not self._proxies:
            logger.debug("No parser proxies available after reload")
            raise ParserProxyUnavailableError("No active parser proxies available")

        now = self._now()
        for _ in range(len(self._proxies)):
            proxy = self._proxies[self._cursor]
            self._cursor = (self._cursor + 1) % len(self._proxies)
            if self._is_available(proxy, now):
                return proxy

        # All proxies went on cooldown since the last reload — refresh once more.
        await self._reload()
        if not self._proxies:
            logger.debug("No parser proxies available after forced reload")
            raise ParserProxyUnavailableError("No active parser proxies available")

        proxy = self._proxies[self._cursor % len(self._proxies)]
        self._cursor = (self._cursor + 1) % len(self._proxies)
        return proxy

    async def _reload_if_needed(self) -> None:
        now = self._now()
        if (
            self._last_reload_at is not None
            and self._proxies
            and now - self._last_reload_at < self._reload_interval
        ):
            # Cached proxies are still fresh.
            return

        await self._reload()

    async def _reload(self) -> None:
        proxies = list(await self._repository.list_active())
        now = self._now()
        self._proxies = [proxy for proxy in proxies if self._is_available(proxy, now)]
        self._cursor = 0
        self._last_reload_at = now
        logger.debug("Loaded %s active parser proxies", len(self._proxies))

    def _apply_updated_proxy(self, updated: ParserProxy | None) -> None:
        if updated is None:
            return

        now = self._now()
        available = self._is_available(updated, now)

        for idx, current in enumerate(self._proxies):
            if current.id == updated.id:
                if available:
                    self._proxies[idx] = updated
                else:
                    del self._proxies[idx]
                break
        else:
            if available:
                self._proxies.append(updated)

        self._normalize_cursor()

    def _normalize_cursor(self) -> None:
        if self._proxies:
            self._cursor %= len(self._proxies)
        else:
            self._cursor = 0

    @staticmethod
    def _now() -> dt.datetime:
        return dt.datetime.now(dt.timezone.utc)

    @staticmethod
    def _normalize_dt(value: dt.datetime) -> dt.datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=dt.timezone.utc)
        return value.astimezone(dt.timezone.utc)

    def _is_available(self, proxy: ParserProxy, now: dt.datetime | None = None) -> bool:
        if proxy.cooldown_until is None:
            return True

        current = now or self._now()
        cooldown_until = self._normalize_dt(proxy.cooldown_until)
        return cooldown_until <= current

    def _compute_cooldown(self, delta: dt.timedelta) -> dt.datetime | None:
        if delta.total_seconds() <= 0:
            return None
        return self._now() + delta


__all__ = [
    "ParserProxy",
    "ParserProxyManager",
    "ParserProxyRepository",
]

