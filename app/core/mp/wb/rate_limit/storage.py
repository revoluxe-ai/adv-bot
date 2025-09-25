from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

Key = tuple[str, str, str]  # (shop_id, section, method_raw)


@dataclass
class RateLimitRecord:
    # последняя отметка времени вызова (для равномерной подачи)
    last_call_ts: float = 0.0
    # сколько запросов осталось в текущем окне burst
    remaining: int | None = None
    # когда полностью восстановится burst (epoch seconds), если известно
    reset_at: float | None = None
    # если получили 429 и сервер сказал подождать
    retry_after_until: float | None = None


class RateLimitStorage:
    """In-memory RL-хранилище под ключ (shop_id, section, method_raw)."""

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

    async def preflight_delay(self, shop_id: str, section: str, method: str) -> float:
        """Верни сколько секунд подождать перед вызовом с учётом retry_after/reset."""
        key: Key = (shop_id, section, method)
        rec = self.get(shop_id, section, method)
        now = time.time()

        delay = 0.0
        # если есть активный retry-after, ждём до него
        if rec.retry_after_until and rec.retry_after_until > now:
            delay = max(delay, rec.retry_after_until - now)

        # если reset_at в будущем и remaining == 0, тоже подождём до reset
        if rec.remaining == 0 and rec.reset_at and rec.reset_at > now:
            delay = max(delay, rec.reset_at - now)

        return delay

    async def update_from_response(
        self,
        shop_id: str,
        section: str,
        method: str,
        status_code: int,
        headers: dict[str, str],
    ) -> None:
        """Обновить состояние по заголовкам WB.
        Ожидаем заголовки: X-Ratelimit-Limit, X-Ratelimit-Remaining, X-Ratelimit-Reset, X-Ratelimit-Retry
        """
        key: Key = (shop_id, section, method)
        lock = self._lock_for(key)
        async with lock:
            rec = self.get(shop_id, section, method)
            now = time.time()

            # remaining
            remaining = headers.get("X-Ratelimit-Remaining")
            if remaining is not None:
                try:
                    rec.remaining = int(remaining)
                except ValueError:
                    pass

            # reset
            reset = headers.get("X-Ratelimit-Reset")
            if reset is not None:
                try:
                    secs = float(reset)
                    rec.reset_at = now + secs
                except ValueError:
                    pass

            # retry-after (актуально при 429)
            retry = headers.get("X-Ratelimit-Retry")
            if retry is not None and status_code == 429:
                try:
                    secs = float(retry)
                    rec.retry_after_until = now + secs
                except ValueError:
                    pass

            rec.last_call_ts = now
