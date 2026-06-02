"""Декоратор single_run: один in-flight вызов на ключ (args/kwargs).

Waiter ждёт Event первого caller; timeout waiter не удаляет shared state — только first
caller очищает key после завершения func.
"""

import asyncio
import logging
import os
import time
from collections import Counter
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

from app.modules.shop_runner.service_manager.exc import StopShopUpdateException
from app.modules.shop_runner.service_manager.exceptions import NotFoundActiveAdvCompany

logger = logging.getLogger(__name__)

SINGLE_RUN_WAIT_TIMEOUT_SECONDS = 900

_TRACE_TIMING_ENABLED: bool | None = None


def _coroutine_trace_enabled() -> bool:
    """True, если включён whitelist ``COROUTINE_PHASE_TRACE_ADV_IDS``."""
    global _TRACE_TIMING_ENABLED
    if _TRACE_TIMING_ENABLED is None:
        raw = os.environ.get("COROUTINE_PHASE_TRACE_ADV_IDS", "").strip()
        _TRACE_TIMING_ENABLED = bool(raw)
    return bool(_TRACE_TIMING_ENABLED)


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
                wait_started: float | None = None
                if _coroutine_trace_enabled():
                    wait_started = time.perf_counter()
                    logger.info(
                        "[coroutine_timing] coroutine=single_run phase=%s step=wait_start "
                        "waiters=%s key=%s",
                        func.__name__,
                        self._single_run_call_counter[key],
                        key[:240],
                    )
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
                    if wait_started is not None:
                        wait_ms = (time.perf_counter() - wait_started) * 1000.0
                        logger.info(
                            "[coroutine_timing] coroutine=single_run phase=%s step=wait_end "
                            "duration_ms=%.2f waiters=%s",
                            func.__name__,
                            wait_ms,
                            self._single_run_call_counter[key],
                        )
                    return payload
                finally:
                    self._single_run_call_counter[key] -= 1

            # Первый вызов — единственный, кто создаёт и очищает shared state.
            event = asyncio.Event()
            event.clear()
            events[key] = event
            self._single_run_call_counter[key] = 0

            try:
                run_started: float | None = None
                if _coroutine_trace_enabled():
                    run_started = time.perf_counter()
                    logger.info(
                        "[coroutine_timing] coroutine=single_run phase=%s step=run_start key=%s",
                        func.__name__,
                        key[:240],
                    )
                result = await func(self, *args, **kwargs)
                if run_started is not None:
                    run_ms = (time.perf_counter() - run_started) * 1000.0
                    logger.info(
                        "[coroutine_timing] coroutine=single_run phase=%s step=run_end "
                        "duration_ms=%.2f",
                        func.__name__,
                        run_ms,
                    )
                results[key] = ("ok", result)
                return result
            except asyncio.CancelledError as exc:
                # Если first caller отменили, waiters должны получить тот же cancel,
                # а не падать с KeyError из-за пустого results.
                results[key] = ("exc", exc)
                raise
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
