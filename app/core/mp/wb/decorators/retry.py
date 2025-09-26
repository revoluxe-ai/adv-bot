from __future__ import annotations

import asyncio
from functools import wraps
from typing import Callable, Awaitable, Any, Tuple


def retry_decorator(
    max_attempts: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    retry_http_codes: Tuple[int, ...] = (429, 500, 502, 503, 504),
) -> Callable[..., Callable[..., Awaitable[Any]]]:
    """Decorator to retry adapter methods on specific HTTP codes with exponential backoff."""

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            for attempt in range(max_attempts):
                try:
                    result = await func(*args, **kwargs)
                    # Assuming the result has a status_code attribute for checking
                    status_code = getattr(result, 'status_code', None)

                    if status_code in retry_http_codes:
                        if attempt < max_attempts - 1:
                            await asyncio.sleep(delay)
                            delay *= backoff_factor
                            continue
                    return result
                except Exception as e:
                    # Catching generic Exception for now, can be more specific later
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay)
                        delay *= backoff_factor
                        continue
                    raise  # Re-raise the last exception if all retries fail
            # Should not reach here if max_attempts is handled in loop, but for safety
            raise RuntimeError("Max retries exceeded without a successful response.")

        return wrapper

    return decorator
