import asyncio
import hashlib
import json
import logging
from functools import wraps
from typing import Callable, Awaitable, Any, Dict

logger = logging.getLogger(__name__)


def make_key(func_name: str, args: Any, kwargs: Any) -> str:
    key_data = {"func_name": func_name, "args": args, "kwargs": kwargs}
    key_json = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_json.encode()).hexdigest()


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

            events: Dict[str, asyncio.Event] = self._single_run_events

            # Генерируем уникальный ключ для набора параметров
            key = make_key(func.__name__, args, kwargs)

            event = events.get(key)
            if event is None:
                event = asyncio.Event()
                event.set()
                events[key] = event

            if not event.is_set():
                await event.wait()
                result = self._single_run_results[key]
                return result

            try:
                event.clear()
                try:
                    result = await func(self, *args, **kwargs)
                except Exception as exc:
                    logger.error(
                        f"Ошибка обернутой функции: {func.__name__}", exc_info=True
                    )
                    raise exc
                self._single_run_results[key] = result
                event.set()
                return result
            except Exception as e:
                # Здесь можно вставить свой логгер
                print(f"Ошибка в {func.__name__}: {e}", flush=True)
                raise

        return wrapper

    return decorator
