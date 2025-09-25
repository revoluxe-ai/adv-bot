from __future__ import annotations

from typing import Any, Callable, Coroutine


def auth_decorator(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Decorator that injects an AuthenticatedClient with correct token into the call.

    The decorator will obtain token from TokenManager and create per-request AuthenticatedClient.
    """

    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Implementation deferred
        return await func(*args, **kwargs)

    return wrapper
