import asyncio
import logging
from collections import Counter
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

from app.modules.shop_runner.service_manager.exc import StopShopUpdateException
from app.modules.shop_runner.service_manager.exceptions import NotFoundActiveAdvCompany

logger = logging.getLogger(__name__)


def make_key(func_name: str, args: tuple[Any, ...], kwargs: dict[Any, Any]) -> str:
    return f"{func_name}:{args}:{frozenset(kwargs.items())}"


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

            # Если уже запущена функция — ждём
            if key in events:
                self._single_run_call_counter[key] += 1
                try:
                    await events[key].wait()
                    value = results.get(key)
                    if value is None:
                        raise KeyError(key)
                    value_type, payload = value
                    if value_type == "exc":
                        raise payload
                    return payload

                finally:
                    self._single_run_call_counter[key] -= 1
                    if self._single_run_call_counter[key] <= 0:
                        events.pop(key, None)
                        results.pop(key, None)
                        self._single_run_call_counter.pop(key, None)

            # Первый вызов
            event = asyncio.Event()
            event.clear()
            events[key] = event
            self._single_run_call_counter[key] = 0  # Никто ещё не ждёт

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
                await asyncio.sleep(1)  # Даем время другим задачам обработать событие
                if self._single_run_call_counter[key] <= 0:
                    events.pop(key, None)
                    results.pop(key, None)
                    self._single_run_call_counter.pop(key, None)

        return wrapper

    return decorator
