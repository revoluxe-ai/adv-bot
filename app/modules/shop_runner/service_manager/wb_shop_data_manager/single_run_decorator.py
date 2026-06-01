"""Декоратор single_run: один in-flight вызов на ключ (args/kwargs).

Waiter ждёт Event первого caller; timeout waiter не удаляет shared state — только first
caller очищает key после завершения func.
"""

import asyncio
import logging
from collections import Counter
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

from app.modules.shop_runner.service_manager.exc import StopShopUpdateException
from app.modules.shop_runner.service_manager.exceptions import NotFoundActiveAdvCompany

logger = logging.getLogger(__name__)

SINGLE_RUN_WAIT_TIMEOUT_SECONDS = 900


def _to_hashable(val: Any) -> Any:
    """Convert a value to a hashable form for cache key; dicts become sorted tuples."""
    if isinstance(val, dict):
        return tuple(sorted((_to_hashable(k), _to_hashable(v)) for k, v in val.items()))
    if isinstance(val, (list, tuple)):
        return tuple(_to_hashable(x) for x in val)
    try:
        hash(val)
        return val
    except TypeError:
        raise TypeError(f"Unhashable type in single_run cache key: {type(val)}") from None


def make_key(func_name: str, args: tuple[Any, ...], kwargs: dict[Any, Any]) -> str:
    key_items = [(k, _to_hashable(v)) for k, v in kwargs.items()]
    return f"{func_name}:{args}:{frozenset(key_items)}"


def single_run() -> (
    Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]
):
    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            if not hasattr(self, "_single_run_events"):
                self._single_run_events = {}
            if not hasattr(self, "_single_run_results"):
                self._single_run_results = {}
            if not hasattr(self, "_single_run_call_counter"):
                self._single_run_call_counter = Counter()

            events: dict[str, asyncio.Event] = self._single_run_events
            results: dict[str, Any] = self._single_run_results

            key = make_key(func.__name__, args, kwargs)

            # Уже выполняется — ждём завершения first caller (не удаляем key при timeout).
            if key in events:
                self._single_run_call_counter[key] += 1
                try:
                    try:
                        await asyncio.wait_for(
                            events[key].wait(),
                            timeout=SINGLE_RUN_WAIT_TIMEOUT_SECONDS,
                        )
                    except asyncio.TimeoutError:
                        logger.error(
                            "single_run wait timed out (function=%s, key=%s, timeout_sec=%s)",
                            func.__name__,
                            key,
                            SINGLE_RUN_WAIT_TIMEOUT_SECONDS,
                            exc_info=True,
                        )
                        raise
                    value = results.get(key)
                    if value is None:
                        raise KeyError(key)
                    value_type, payload = value
                    if value_type == "exc":
                        raise payload
                    return payload
                finally:
                    self._single_run_call_counter[key] -= 1

            # Первый вызов — единственный, кто создаёт и очищает shared state.
            event = asyncio.Event()
            event.clear()
            events[key] = event
            self._single_run_call_counter[key] = 0

            try:
                result = await func(self, *args, **kwargs)
                results[key] = ("ok", result)
                return result
            except NotFoundActiveAdvCompany as exc:
                results[key] = ("exc", exc)
                raise
            except Exception as exc:
                logger.error(
                    f"Ошибка обернутой функции: {func.__name__}", exc_info=True
                )
                results[key] = ("exc", exc)
                raise
            finally:
                event.set()
                # Ждём, пока активные waiters прочитают results; только first caller чистит state.
                while self._single_run_call_counter.get(key, 0) > 0:
                    await asyncio.sleep(0)
                events.pop(key, None)
                results.pop(key, None)
                self._single_run_call_counter.pop(key, None)

        return wrapper

    return decorator
