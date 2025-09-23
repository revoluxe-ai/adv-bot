import asyncio
from functools import wraps
from typing import Any, Awaitable, Callable


def make_key(func_name: str, args: tuple[Any, ...], kwargs: dict[Any, Any]) -> str:
    """Генерирует уникальный ключ для вызова функции по имени и аргументам."""
    return f"{func_name}:{args}:{frozenset(kwargs.items())}"


def single_run() -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """
    Декоратор для асинхронных методов класса: не допускает одновременного запуска одной и той же функции
    с одинаковыми аргументами. Если вызов уже идёт — остальные ждут результат.
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            if not hasattr(self, "_single_run_futures"):
                self._single_run_futures = {}
            futures: dict[str, asyncio.Future] = self._single_run_futures
            key = make_key(func.__name__, args, kwargs)
            if key in futures:
                return await futures[key]
            loop = asyncio.get_running_loop()
            future = loop.create_future()
            futures[key] = future
            try:
                result = await func(self, *args, **kwargs)
                future.set_result(result)
                return result
            except Exception as e:
                future.set_exception(e)
                raise
            finally:
                futures.pop(key, None)

        return wrapper

    return decorator
