from __future__ import annotations

from typing import Any, Callable, Coroutine
import asyncio
import random


class _RetryExceeded(Exception):
    pass


def retry_decorator(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Decorator that retries the wrapped call on 429/5xx/transport errors.

    Behavior:
    - Up to 3 attempts for 429/5xx by default.
    - Respect Retry-After header when present.
    - For PATCH methods (raw method name contains 'patch' or kwargs/raw_method == 'patch'), limit to 1 retry.
    """

    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # determine if this is a PATCH-like method
        raw_method = kwargs.get("raw_method") or getattr(args[0], "_raw_method", func.__name__ if args else "")
        is_patch = "patch" in (raw_method or "").lower()
        max_attempts = 2 if is_patch else 4  # attempts = retries+1 -> patch: 2 attempts (1 retry), else 4 attempts

        attempt = 0
        while True:
            attempt += 1
            try:
                resp = await func(*args, **kwargs)
            except Exception as exc:
                # treat as transport error -> retry with backoff
                if attempt >= max_attempts:
                    raise
                delay = (2 ** (attempt - 1)) + random.random() * 0.1
                await asyncio.sleep(delay)
                continue

            status = getattr(resp, "status_code", 0)
            if status == 429:
                if attempt >= max_attempts:
                    return resp
                # try to read Retry-After from headers or storage provided in kwargs
                ra = None
                headers = getattr(resp, "headers", {}) or {}
                if "retry-after" in headers:
                    try:
                        ra = int(headers.get("retry-after"))
                    except Exception:
                        ra = None
                if ra is None:
                    # small default backoff
                    ra = 1
                await asyncio.sleep(ra)
                continue

            if 500 <= status < 600:
                if attempt >= max_attempts:
                    return resp
                delay = (2 ** (attempt - 1)) + random.random() * 0.2
                await asyncio.sleep(delay)
                continue

            return resp

    return wrapper
