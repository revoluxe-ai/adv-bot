"""
Декоратор для API запросов с rate limiting и retry логикой.

Объединяет функциональность ограничения частоты запросов и повторных попыток
при ошибках API.
"""

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, cast

from app.core.wb_api.exceptions import (
    ApiForbiddenError,
    MaxAttemptsError,
    TooManyRequests,
)
from app.core.wb_api.utils.rate_limiter import AdaptiveRateLimiter

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def rate_limited_retry(
    max_calls_per_minute: int = 60,
    max_attempts: int = 5,
    initial_retry_delay: float = 1.0,
    max_retry_delay: float = 60.0,
    backoff_factor: float = 2.0,
) -> Callable[[F], F]:
    """
    Декоратор для API методов с ограничением частоты и повторными попытками.

    Комбинирует:
    - Адаптивное ограничение частоты запросов
    - Экспоненциальный backoff при ошибках
    - Автоматические повторные попытки

    Args:
        max_calls_per_minute: Максимальное количество вызовов в минуту
        max_attempts: Максимальное количество попыток
        initial_retry_delay: Начальная задержка между попытками
        max_retry_delay: Максимальная задержка между попытками
        backoff_factor: Множитель увеличения задержки

    Returns:
        Декорированная функция
    """
    # Создаем rate limiter
    rate_limiter = AdaptiveRateLimiter(
        initial_rate=60.0 / max_calls_per_minute,  # Конвертируем в интервал
        min_interval=0.1,
        max_interval=max_retry_delay,
        backoff_factor=backoff_factor,
        recovery_factor=0.9,
    )

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(instance: Any, *args: Any, **kwargs: Any) -> Any:
            """Обертка с rate limiting и retry логикой."""
            attempt = 0
            retry_delay = initial_retry_delay
            last_error: Optional[Exception] = None

            while attempt < max_attempts:
                try:
                    # Ждем разрешения от rate limiter
                    await rate_limiter.acquire()

                    # Выполняем запрос
                    result = await func(instance, *args, **kwargs)

                    # Успех - уменьшаем интервал
                    rate_limiter.on_success()

                    return result

                except TooManyRequests as e:
                    # API сообщил о превышении лимита
                    logger.warning(
                        f"Rate limit hit for {func.__name__}, attempt {attempt + 1}/{max_attempts}"
                    )
                    rate_limiter.on_rate_limit()
                    last_error = e

                    # Ждем перед следующей попыткой
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay = min(retry_delay * backoff_factor, max_retry_delay)

                except ApiForbiddenError as e:
                    # Проблема с токеном - пробуем переключить
                    logger.error(f"Forbidden error in {func.__name__}: {e}")

                    # Пытаемся переключить токен если есть такой метод
                    if hasattr(instance, "set_next_token"):
                        await instance.set_next_token(func.__name__)
                        # Сбрасываем счетчик попыток при смене токена
                        attempt = -1
                    else:
                        raise

                except Exception as e:
                    # Другие ошибки - просто повторяем
                    logger.error(
                        f"Error in {func.__name__}, attempt {attempt + 1}/{max_attempts}: {e}"
                    )
                    last_error = e

                    if attempt < max_attempts - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay = min(retry_delay * backoff_factor, max_retry_delay)

                attempt += 1

            # Все попытки исчерпаны
            shop_id = getattr(instance, "shop_id", "unknown")
            raise MaxAttemptsError(
                f"Failed to execute {func.__name__} after {max_attempts} attempts "
                f"for shop_id={shop_id}"
            ) from last_error

        return cast(F, wrapper)

    return decorator


class BatchRateLimiter:
    """
    Rate limiter специально для батчевых операций.

    Учитывает размер батча при расчете задержек.
    """

    def __init__(
        self,
        max_items_per_minute: int = 1000,
        max_batch_size: int = 50,
        min_interval: float = 0.1,
    ):
        """
        Args:
            max_items_per_minute: Максимальное количество элементов в минуту
            max_batch_size: Максимальный размер батча
            min_interval: Минимальный интервал между батчами
        """
        self.max_items_per_minute = max_items_per_minute
        self.max_batch_size = max_batch_size
        self.min_interval = min_interval

        self._rate_limiter = AdaptiveRateLimiter(
            initial_rate=min_interval, min_interval=min_interval, max_interval=60.0
        )

    async def acquire_for_batch(self, batch_size: int) -> None:
        """
        Ожидает разрешения для обработки батча.

        Args:
            batch_size: Размер батча
        """
        # Рассчитываем задержку на основе размера батча
        items_per_second = self.max_items_per_minute / 60.0
        required_time = batch_size / items_per_second

        # Устанавливаем интервал для rate limiter
        self._rate_limiter.current_interval = max(required_time, self.min_interval)

        await self._rate_limiter.acquire()
