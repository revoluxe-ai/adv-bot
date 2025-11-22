from __future__ import annotations

import asyncio
import os
import time
from typing import Final

from aiohttp import ClientSession
from dependency_injector.wiring import inject, Provide

_CACHE_TTL_SECONDS: Final[int] = 3600
_IP_LOCK: Final[asyncio.Lock] = asyncio.Lock()
_cached_ip: str | None = None
_cache_expire_at: float = 0.0


@inject
async def get_public_ip(
    session: ClientSession = Provide["http_sessions.get_ip_session"],
) -> str:
    env_ip = os.getenv("ADV_PUBLIC_IP")
    if env_ip:
        return env_ip

    global _cached_ip, _cache_expire_at

    now = time.monotonic()
    if _cached_ip and now < _cache_expire_at:
        return _cached_ip

    async with _IP_LOCK:
        now = time.monotonic()
        if _cached_ip and now < _cache_expire_at:
            return _cached_ip

        async with session.get(
            "https://api.ipify.org", params={"format": "text"}
        ) as response:
            response.raise_for_status()
            ip = (await response.text()).strip()

        _cached_ip = ip
        _cache_expire_at = time.monotonic() + _CACHE_TTL_SECONDS
        return ip
