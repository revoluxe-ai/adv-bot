"""
Декоратор для API запросов с rate limiting и retry логикой.

Сохраняет полную совместимость с текущим синтаксисом try_except_decorator.
"""

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, TypeVar, cast

from app.core.wb_api.exceptions import (
    ApiForbiddenError,
    MaxAttemptsError,
    TooManyRequests,
)
from app.core.mp.wb.utils.rate_limiter import AdaptiveRateLimiter

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def rate_limited_retry(
    max_calls: int,
    period_seconds: float,
    max_attempts: int = 5,
    initial_retry_delay: float = 1.0,
    max_retry_delay: float = 60.0,
    backoff_factor: float = 2.0,
) -> Callable[[F], F]:
    """
    Декоратор для обработки API запросов с ограничением частоты и повторными попытками.

    Полностью совместим с текущим синтаксисом try_except_decorator.

    Args:
        max_calls: Максимальное количество вызовов за период
        period_seconds: Период в секундах
        max_attempts: Максимальное количество попыток
        initial_retry_delay: Начальная задержка между попытками
        max_retry_delay: Максимальная задержка между попытками
        backoff_factor: Множитель увеличения задержки

    Returns:
        Декорированная функция
    """
    # Создаем адаптивный rate limiter
    rate_limiter = AdaptiveRateLimiter(
        initial_rate=period_seconds / max_calls,
        min_interval=0.1,
        max_interval=max_retry_delay,
        backoff_factor=backoff_factor,
    )

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(instance: Any, *args: Any, **kwargs: Any) -> Any:
            """
            Обертка с rate limiting и повторными попытками.

            Args:
                instance: Экземпляр класса, к которому применяется декоратор
                *args: Позиционные аргументы метода
                **kwargs: Именованные аргументы метода

            Returns:
                Результат вызова метода
            """
            attempt = 0
            retry_delay = initial_retry_delay
            last_error = None

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
