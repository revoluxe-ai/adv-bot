from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

Key = tuple[str, str, str]  # (shop_id, section, method_raw)


@dataclass(frozen=True, slots=True)
class RateLimitConfig:
    """Immutable configuration describing a token bucket style limit."""

    requests_per_interval: int
    interval_seconds: float
    burst: int | None = None
    weight: float = 1.0

    def __post_init__(self) -> None:
        if self.requests_per_interval <= 0:
            raise ValueError("requests_per_interval must be positive")
        if self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        if self.weight <= 0:
            raise ValueError("weight must be positive")

    @property
    def min_interval(self) -> float:
        """Return minimal spacing between requests for the plain weight."""
        return self.interval_seconds / self.requests_per_interval

    def interval_for_weight(self, weight: float | None = None) -> float:
        """Return spacing adjusted for a heavier request."""
        effective_weight = weight if weight and weight > 0 else self.weight
        return self.min_interval * max(effective_weight, 1.0)


@dataclass
class RateLimitRecord:
    last_call_ts: float = 0.0
    remaining: int | None = None
    reset_at: float | None = None
    retry_after_until: float | None = None
    config: RateLimitConfig | None = None


class RateLimitStorage:
    """In-memory rate limit storage shared across adapters."""

    def __init__(self) -> None:
        self._data: dict[Key, RateLimitRecord] = {}
        self._locks: dict[Key, asyncio.Lock] = {}

    def _lock_for(self, key: Key) -> asyncio.Lock:
        lock = self._locks.get(key)
        if not lock:
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock

    def get(self, shop_id: str, section: str, method: str) -> RateLimitRecord:
        key: Key = (shop_id, section, method)
        rec = self._data.get(key)
        if rec is None:
            rec = RateLimitRecord()
            self._data[key] = rec
        return rec

    async def register_config(
        self,
        shop_id: str,
        section: str,
        method: str,
        config: RateLimitConfig,
    ) -> None:
        """Bind a static configuration to the key if it is not set yet."""
        key: Key = (shop_id, section, method)
        lock = self._lock_for(key)
        async with lock:
            rec = self.get(shop_id, section, method)
            if rec.config != config:
                rec.config = config

    async def preflight_delay(self, shop_id: str, section: str, method: str) -> float:
        """Return delay before issuing the next request based on known limits/state."""
        key: Key = (shop_id, section, method)
        lock = self._lock_for(key)
        async with lock:
            rec = self.get(shop_id, section, method)
            now = time.time()
            delay = 0.0

            if rec.retry_after_until and rec.retry_after_until > now:
                delay = max(delay, rec.retry_after_until - now)

            if rec.remaining == 0 and rec.reset_at and rec.reset_at > now:
                delay = max(delay, rec.reset_at - now)

            config = rec.config
            if config is not None and config.requests_per_interval > 0:
                min_interval = config.interval_for_weight()
                if rec.last_call_ts:
                    elapsed = now - rec.last_call_ts
                    if elapsed < min_interval:
                        delay = max(delay, min_interval - elapsed)
                rec.last_call_ts = now + delay

            return delay

    async def update_from_response(
        self,
        shop_id: str,
        section: str,
        method: str,
        status_code: int,
        headers: dict[str, str],
    ) -> None:
        """Update runtime rate-limit state using HTTP response headers."""
        key: Key = (shop_id, section, method)
        lock = self._lock_for(key)
        async with lock:
            rec = self.get(shop_id, section, method)
            now = time.time()

            remaining = headers.get("X-Ratelimit-Remaining")
            if remaining is not None:
                try:
                    rec.remaining = int(remaining)
                except ValueError:
                    pass

            reset = headers.get("X-Ratelimit-Reset")
            if reset is not None:
                try:
                    secs = float(reset)
                    rec.reset_at = now + secs
                except ValueError:
                    pass

            retry = headers.get("X-Ratelimit-Retry")
            if retry is not None and status_code == 429:
                try:
                    secs = float(retry)
                    rec.retry_after_until = now + secs
                except ValueError:
                    pass
            elif status_code != 429:
                rec.retry_after_until = None

            rec.last_call_ts = now
