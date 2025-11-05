from __future__ import annotations

import asyncio
import functools
import logging
import random
from typing import Any, TypeVar, ParamSpec
from collections.abc import Callable
import weakref

from app.modules.wb_keywords_parser.wb_parser.excs import (
    TooManyRequestsInParserError,
    WBConnectionRateLimitError,
)
from app.settings import settings
from app.utils.net import get_public_ip

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")

# Глобальный пул локов на IP (weak)
_locks: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()


def _get_lock(ip: str) -> asyncio.Lock:
    """Возвращает lock для конкретного IP (создаёт при необходимости)."""
    lock = _locks.get(ip)
    if lock is None:
        # Защита от гонки: пытаемся атомарно вставить
        lock = asyncio.Lock()
        _locks[ip] = lock
    return lock


def rate_limited_request(
        rate_limit_manager: Any,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Декоратор для адаптивного ограничения скорости запросов на основе IP.

    При успешном запросе постепенно уменьшает TTL блокировки (быстрое восстановление).
    При TooManyRequestsInParserError увеличивает TTL экспоненциально.

    Args:
        rate_limit_manager: Менеджер с is_ip_blocked, block_ip, delete_block
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            ip = await get_public_ip()
            base_delay = settings.WB_RATE_LIMIT_BASE_DELAY_SEC
            multiplier = settings.WB_RATE_LIMIT_MULTIPLIER
            max_delay = settings.WB_RATE_LIMIT_MAX_DELAY_SEC
            success_threshold = 3  # N успешных запросов подряд для уменьшения
            cooldown_sec = 60.0    # если 429 не было > 60c, можно сбросить сильнее

            async with _get_lock(ip):
                # Ожидание, пока IP не разблокируется
                while True:
                    blocked, ttl_left = await rate_limit_manager.is_ip_blocked(ip)
                    if not blocked:
                        break
                    jitter = random.uniform(0, 0.1)
                    sleep_time = ttl_left + jitter
                    logger.debug(
                        "IP %s заблокирован, ожидание %.2fs (TTL=%.2fs)",
                        ip, sleep_time, ttl_left,
                    )
                    await asyncio.sleep(sleep_time)

                # Выполнение запроса
                try:
                    result = await func(*args, **kwargs) # pyright: ignore
                except (TooManyRequestsInParserError, WBConnectionRateLimitError) as e:
                    if isinstance(e, WBConnectionRateLimitError):
                        logger.error(
                            "WBConnectionRateLimitError encountered: %s", e, exc_info=True
                        )


                    # Увеличиваем счётчик последовательных ошибок (до расчёта TTL)
                    error_count = await rate_limit_manager.increment_error_counter(ip)
                    await rate_limit_manager.set_last_error_ts(ip)

                    # TTL = base_delay * multiplier^error_count (экспонента)
                    new_ttl = base_delay * (multiplier ** error_count)
                    new_ttl = min(new_ttl, max_delay)

                    await rate_limit_manager.block_ip(ip, new_ttl)

                    # Логируем с указанием типа ошибки
                    logger.warning(
                        "WB rate-limit для IP %s, серия=%s, новый TTL=%.2fs",
                        ip, error_count, new_ttl,
                    )
                else:
                    # AIMD: Additive Increase при успехе
                    success_count = await rate_limit_manager.increment_success_counter(ip)

                    # Уменьшаем delay только после N успехов подряд
                    # threshold param initialized above
                    blocked, current_ttl = await rate_limit_manager.is_ip_blocked(ip)

                    if success_count >= success_threshold and blocked and current_ttl > base_delay:
                        last_err_ts = await rate_limit_manager.get_last_error_ts(ip)
                        import time
                        if time.time() - last_err_ts >= cooldown_sec:
                            # долго не было 429 — можно резко сбросить
                            new_ttl = base_delay
                        else:
                            new_ttl = max(base_delay, current_ttl * 0.95)

                        if new_ttl <= base_delay:
                            await rate_limit_manager.delete_block(ip)
                            logger.info(
                                "IP %s разблокирован после %s успехов подряд",
                                ip, success_count,
                            )
                        else:
                            await rate_limit_manager.refresh_block(ip, new_ttl)
                            logger.debug(
                                "TTL для IP %s уменьшен: %.2fс → %.2fс (%s успехов)",
                                ip, current_ttl, new_ttl, success_count,
                            )
                    elif blocked:
                        logger.debug(
                            "IP %s: успешный запрос (%s/%s для уменьшения)",
                            ip, success_count, success_threshold,
                        )

                    return result # pyright: ignore

        return wrapper  # type: ignore[return-value]

    return decorator

