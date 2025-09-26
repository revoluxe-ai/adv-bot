from __future__ import annotations

import time
import asyncio
from dataclasses import dataclass
from typing import Dict, Tuple, Optional


@dataclass
class RateLimitState:
    """Represents the current state of a rate limit for a specific key."""
    last_call_timestamp: float = 0.0
    quota_used: int = 0
    # interval_seconds: float = 1.0 # The interval over which rate limits apply
    # requests_per_interval: int = 1 # Max requests per interval
    # burst: int = 1 # Max burst requests


@dataclass
class RateLimitConfig:
    """Configuration for a specific rate limit."""
    requests_per_interval: int
    interval_seconds: float
    burst: int


class RateLimitStorage:
    """Centralized storage for API rate limits and delays, implemented as a singleton."""

    def __init__(self) -> None:
        # Key: (shop_id, section, method)
        self._storage: Dict[Tuple[str, str, str], RateLimitState] = {}
        self._locks: Dict[Tuple[str, str, str], asyncio.Lock] = {}

    def get_state(self, shop_id: str, section: str, method: str) -> RateLimitState:
        key = (shop_id, section, method)
        if key not in self._storage:
            self._storage[key] = RateLimitState()
        return self._storage[key]
    
    async def acquire_lock(self, shop_id: str, section: str, method: str) -> asyncio.Lock:
        key = (shop_id, section, method)
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]


def get_rate_limit_storage() -> RateLimitStorage:
    """Singleton accessor for RateLimitStorage. Will be replaced by DI wiring."""
    # This function will be replaced by DI container wiring
    return RateLimitStorage()
