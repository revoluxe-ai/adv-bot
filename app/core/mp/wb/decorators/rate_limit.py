from __future__ import annotations

import asyncio
import time
from functools import wraps
from typing import Callable, Awaitable, Any, TYPE_CHECKING

from app.core.mp.wb.rate_limit.storage import RateLimitStorage, RateLimitConfig

if TYPE_CHECKING:
    from app.core.mp.wb.adapters.base import BaseAdapter


def rate_limit_decorator(
    limits: int,
    interval: float,
    burst: int = 1,
) -> Callable[..., Callable[..., Awaitable[Any]]]:
    """Decorator to apply rate limiting to adapter methods."""

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(self: BaseAdapter, *args: Any, **kwargs: Any) -> Any:
            if not hasattr(self, 'rate_limit_storage') or not isinstance(self.rate_limit_storage, RateLimitStorage):
                raise RuntimeError("RateLimitStorage not configured on adapter.")

            storage: RateLimitStorage = self.rate_limit_storage
            # Assuming method name can be extracted from func.__name__ or passed as arg
            method_name = func.__name__
            shop_id = self.shop_id
            section = self.section

            key = (shop_id, section, method_name)
            lock = await storage.acquire_lock(*key)

            async with lock:
                state = storage.get_state(*key)
                config = RateLimitConfig(limits, interval, burst)

                # Calculate delay based on token bucket algorithm or similar
                now = time.time()
                elapsed = now - state.last_call_timestamp
                tokens = elapsed * (config.requests_per_interval / config.interval_seconds)
                state.quota_used = max(0, state.quota_used - int(tokens))

                delay = 0.0
                if state.quota_used >= config.requests_per_interval:
                    # Out of quota, calculate wait time until next token is available
                    # This is a simplified calculation; a real token bucket might be more complex
                    time_to_wait = (state.quota_used - config.requests_per_interval + 1) * \
                                 (config.interval_seconds / config.requests_per_interval)
                    delay = max(0.0, time_to_wait - elapsed)

                if delay > 0:
                    await asyncio.sleep(delay)

                state.last_call_timestamp = time.time()
                state.quota_used += 1 # Consume one quota

                # Call original function
                return await func(self, *args, **kwargs)

        return wrapper

    return decorator

