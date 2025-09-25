from __future__ import annotations

from typing import Any, Callable, Coroutine


def retry_decorator(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Decorator that retries the wrapped call on transient errors like 429 or 5xx."""

    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Implementation deferred
        return await func(*args, **kwargs)

    return wrapper
