"""
Rate limiter для контроля частоты API запросов.

Этот модуль предоставляет декоратор для ограничения частоты вызовов функций,
что особенно полезно при работе с внешними API с лимитами.
"""

import asyncio
import time
from collections import deque
from functools import wraps
from typing import Any, Callable, Deque, Optional, TypeVar, cast

import logging

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class RateLimiter:
    """
    Ограничитель частоты вызовов с использованием sliding window алгоритма.

    Attributes:
        max_calls: Максимальное количество вызовов
        period: Период времени в секундах
        calls: Очередь временных меток вызовов
    """

    def __init__(self, max_calls: int, period: float):
        """
        Инициализация rate limiter.

        Args:
            max_calls: Максимальное количество вызовов за период
            period: Период времени в секундах
        """
        self.max_calls = max_calls
        self.period = period
        self.calls: Deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Ожидает, пока можно будет выполнить вызов."""
        async with self._lock:
            now = time.time()

            # Удаляем устаревшие вызовы
            while self.calls and self.calls[0] <= now - self.period:
                self.calls.popleft()

            # Если достигнут лимит, ждем
            if len(self.calls) >= self.max_calls:
                sleep_time = self.period - (now - self.calls[0])
                if sleep_time > 0:
                    logger.debug(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                    await asyncio.sleep(sleep_time)
                    # Рекурсивно пробуем снова
                    await self.acquire()
                    return

            # Записываем время вызова
            self.calls.append(now)


def rate_limit(max_calls: int, period: float) -> Callable[[F], F]:
    """
    Декоратор для ограничения частоты вызовов функции.

    Args:
        max_calls: Максимальное количество вызовов за период
        period: Период времени в секундах

    Returns:
        Декорированная функция с ограничением частоты вызовов

    Example:
        @rate_limit(max_calls=10, period=60)  # 10 вызовов в минуту
        async def api_call():
            pass
    """
    limiter = RateLimiter(max_calls, period)

    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            await limiter.acquire()
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError(
                f"Synchronous function {func.__name__} cannot be rate limited. "
                "Use async functions with rate_limit decorator."
            )

        # Определяем, асинхронная ли функция
        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        else:
            return cast(F, sync_wrapper)

    return decorator


class AdaptiveRateLimiter:
    """
    Адаптивный rate limiter, который автоматически подстраивается под ответы API.

    Увеличивает задержку при получении 429 ошибок и уменьшает при успешных запросах.
    """

    def __init__(
        self,
        initial_rate: float = 1.0,
        min_interval: float = 0.1,
        max_interval: float = 60.0,
        backoff_factor: float = 2.0,
        recovery_factor: float = 0.9,
    ):
        """
        Args:
            initial_rate: Начальный интервал между запросами в секундах
            min_interval: Минимальный интервал между запросами
            max_interval: Максимальный интервал между запросами
            backoff_factor: Множитель увеличения интервала при ошибке
            recovery_factor: Множитель уменьшения интервала при успехе
        """
        self.current_interval = initial_rate
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.backoff_factor = backoff_factor
        self.recovery_factor = recovery_factor
        self._last_call_time: Optional[float] = None
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Ожидает перед следующим вызовом."""
        async with self._lock:
            if self._last_call_time is not None:
                elapsed = time.time() - self._last_call_time
                if elapsed < self.current_interval:
                    await asyncio.sleep(self.current_interval - elapsed)

            self._last_call_time = time.time()

    def on_success(self) -> None:
        """Вызывается при успешном запросе."""
        self.current_interval = max(
            self.min_interval, self.current_interval * self.recovery_factor
        )
        logger.debug(f"Rate limit interval decreased to {self.current_interval:.2f}s")

    def on_rate_limit(self) -> None:
        """Вызывается при получении ошибки rate limit (429)."""
        self.current_interval = min(
            self.max_interval, self.current_interval * self.backoff_factor
        )
        logger.warning(
            f"Rate limit hit! Interval increased to {self.current_interval:.2f}s"
        )
