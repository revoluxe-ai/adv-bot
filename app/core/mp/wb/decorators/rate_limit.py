from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Coroutine
import asyncio

from app.core.mp.wb.rate_limit.storage import RateLimitConfig


_DEF_RATE_LIMIT_WEIGHT = 1.0


def _resolve_config(
    instance: Any,
    raw_method: str,
    supplied: RateLimitConfig | None,
    requests_per_interval: int | None,
    interval_seconds: float | None,
    burst: int | None,
    weight: float,
) -> RateLimitConfig | None:
    if supplied is not None:
        return supplied
    if requests_per_interval is not None and interval_seconds is not None:
        return RateLimitConfig(
            requests_per_interval=requests_per_interval,
            interval_seconds=interval_seconds,
            burst=burst,
            weight=weight,
        )
    resolver = getattr(instance, "get_rate_limit_config", None)
    if callable(resolver):
        resolved = resolver(raw_method)
        if resolved is not None:
            return resolved
    section_default = getattr(instance, "section_rate_limit", None)
    if isinstance(section_default, RateLimitConfig):
        return section_default
    return None


def rate_limit_decorator(
    func: Callable[..., Coroutine[Any, Any, Any]] | None = None,
    *,
    config: RateLimitConfig | None = None,
    requests_per_interval: int | None = None,
    limits: int | None = None,
    interval_seconds: float | None = None,
    interval: float | None = None,
    burst: int | None = None,
    weight: float = _DEF_RATE_LIMIT_WEIGHT,
) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Decorator wiring asynchronous rate-limiting around adapter calls.

    Every decorated adapter method MUST have an explicit RateLimitConfig:
    - either passed directly via config
    - or via numeric overrides
    - or provided by the adapter (method-specific or section default)
    """

    if func is None:
        return lambda f: rate_limit_decorator(
            f,
            config=config,
            requests_per_interval=requests_per_interval,
            limits=limits,
            interval_seconds=interval_seconds,
            interval=interval,
            burst=burst,
            weight=weight,
        )

    effective_requests = requests_per_interval if requests_per_interval is not None else limits
    effective_interval = interval_seconds if interval_seconds is not None else interval

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not args:
            return await func(*args, **kwargs)

        adapter = args[0]
        storage = getattr(adapter, "rate_limit_storage", None)
        raw_method = func.__name__
        shop_id = adapter.shop_id
        section = adapter.section

        resolved_config = _resolve_config(
            adapter,
            raw_method,
            config,
            effective_requests,
            effective_interval,
            burst,
            weight,
        )

        if resolved_config is None:
            raise RuntimeError(
                f"Missing rate-limit configuration for {adapter.__class__.__name__}.{raw_method}"
            )

        if storage is not None:
            # Remember method-level configuration so concurrent calls share the same limits.
            await storage.register_config(shop_id, section, raw_method, resolved_config)

            # Respect any delay suggested by the storage (retry-after/reset windows, etc.).
            delay = await storage.preflight_delay(shop_id, section, raw_method)
            if delay and delay > 0:
                await asyncio.sleep(delay)

        resp = await func(*args, **kwargs)

        if storage is not None:
            status = getattr(resp, "status_code", None)
            headers = getattr(resp, "headers", {}) or {}
            await storage.update_from_response(shop_id, section, raw_method, status, headers)

        return resp

    return wrapper

