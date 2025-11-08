from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Sequence


@dataclass
class ParserProxy:
    """Representation of a proxy used by the parser."""

    name: str
    rate_limit_key: str
    cooldown_until: float = 0.0
    consecutive_failures: int = 0
    consecutive_successes: int = 0

    def in_cooldown(self, now: float | None = None) -> bool:
        current = time.time() if now is None else now
        return current < self.cooldown_until


class ProxyProxyManager:
    """Tracks parser proxies and their cooldown/health state."""

    def __init__(self, proxies: Sequence[ParserProxy] | None = None) -> None:
        self._proxies: List[ParserProxy] = list(proxies or [])
        self._last_index: int = -1

    @property
    def proxies(self) -> Sequence[ParserProxy]:
        return tuple(self._proxies)

    def add_proxy(self, proxy: ParserProxy) -> None:
        self._proxies.append(proxy)

    def acquire_proxy(self, now: float | None = None) -> ParserProxy:
        if not self._proxies:
            raise RuntimeError("No parser proxies configured")

        current_time = time.time() if now is None else now
        total = len(self._proxies)
        for _ in range(total):
            self._last_index = (self._last_index + 1) % total
            proxy = self._proxies[self._last_index]
            if not proxy.in_cooldown(current_time):
                return proxy

        # Все прокси в кулдауне — выбираем ту, что освободится раньше
        proxy = min(self._proxies, key=lambda item: item.cooldown_until)
        self._last_index = self._proxies.index(proxy)
        return proxy

    def report_success(self, proxy: ParserProxy) -> None:
        proxy.consecutive_successes += 1
        proxy.consecutive_failures = 0

    def report_failure(self, proxy: ParserProxy) -> None:
        proxy.consecutive_failures += 1
        proxy.consecutive_successes = 0

    def report_rate_limit(self, proxy: ParserProxy, ttl_seconds: float) -> None:
        self.report_failure(proxy)
        if ttl_seconds <= 0:
            return
        current_time = time.time()
        proxy.cooldown_until = max(proxy.cooldown_until, current_time + ttl_seconds)

