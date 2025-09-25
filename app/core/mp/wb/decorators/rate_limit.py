from __future__ import annotations

from typing import Any, Callable, Coroutine
import asyncio


def _extract_raw_method(self: Any, kwargs: dict, func_name: str) -> str:
    # try kwargs, then method-specific attribute, then generic _raw_method, then function name
    if kwargs.get("raw_method"):
        return kwargs.get("raw_method")
    method_attr = f"_raw_method_{func_name}"
    val = getattr(self, method_attr, None)
    if val:
        return val
    val = getattr(self, "_raw_method", None)
    if val:
        return val
    return func_name


def rate_limit_decorator(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Decorator that consults RateLimitStorage before executing call and updates it after.

    Expects the wrapped method to be a bound adapter method: first arg is `self` and
    `self` should expose `rate_limit_storage`, `shop_id` and `section` attributes.
    The `raw_method` is resolved from kwargs['raw_method'] or `self._raw_method` or
    the wrapped function name.
    """

    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not args:
            return await func(*args, **kwargs)

        self = args[0]
        shop_id = getattr(self, "shop_id", None)
        section = getattr(self, "section", None)
        raw_method = _extract_raw_method(self, kwargs, func.__name__)

        storage = getattr(self, "rate_limit_storage", None)

        # preflight delay
        try:
            if storage is not None:
                delay = await storage.preflight_delay(shop_id, section, raw_method)  # type: ignore[attr-defined]
                if delay and delay > 0:
                    await asyncio.sleep(delay)
        except Exception:
            # don't fail the request because of RL storage issues
            pass

        resp = await func(*args, **kwargs)

        # after response update storage
        try:
            if storage is not None:
                status = getattr(resp, "status_code", None)
                headers = getattr(resp, "headers", {}) or {}
                await storage.update_from_response(shop_id, section, raw_method, status, headers)  # type: ignore[attr-defined]
        except Exception:
            # swallow storage errors
            pass

        return resp

    return wrapper
