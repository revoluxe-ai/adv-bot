from __future__ import annotations

import asyncio
import functools
import logging
import random
import time
import weakref
from typing import Any, Callable

from app.modules.wb_keywords_parser.wb_parser.excs import (
    TooManyRequestsInParserError,
    WBConnectionRateLimitError,
)

import typing
if typing.TYPE_CHECKING:
    from app.modules.wb_keywords_parser.wb_parser.rate_limit_manager import ParserRateLimitRedisManager
from app.settings import settings
from app.utils.net import get_public_ip

logger = logging.getLogger(__name__)

_locks: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()


def _get_lock(ip: str) -> asyncio.Lock:
    lock = _locks.get(ip)
    if lock is None:
        lock = asyncio.Lock()
        _locks[ip] = lock
    return lock


def rate_limited_request(rate_limit_manager: 'ParserRateLimitRedisManager',
                         max_retries: int = 50,
                         delay: float = settings.PARSING_LIMITER_DELAY)\
                           -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Декоратор адаптивного rate-limit по IP.

    Сохраняет поведение: при 429 — увеличивает TTL экспоненциально, при успешных запросах
    постепенно снижает TTL и в итоге снимает блокировку.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            ip = await get_public_ip()
            base = delay
            mult = settings.WB_RATE_LIMIT_MULTIPLIER
            max_delay = settings.WB_RATE_LIMIT_MAX_DELAY_SEC
            success_threshold = 3
            cooldown = 60.0

            attempt = 0
            while attempt < max_retries:
                attempt += 1

                async with _get_lock(ip):
                    # Ждём, пока IP не разблокирован
                    while True:
                        blocked, ttl = await rate_limit_manager.is_ip_blocked(ip)
                        if not blocked:
                            break
                        await asyncio.sleep(ttl + random.uniform(0, 0.1))

                    try:
                        result = await func(*args, **kwargs)  # pyright: ignore
                    except (TooManyRequestsInParserError, WBConnectionRateLimitError) as e:
                        if isinstance(e, WBConnectionRateLimitError):
                            logger.warning("WBConnectionRateLimitError")

                        err_count = await rate_limit_manager.increment_error_counter(ip)
                        await rate_limit_manager.set_last_error_ts(ip)

                        new_ttl = min(base * (mult ** err_count), max_delay)
                        await rate_limit_manager.block_ip(ip, new_ttl)

                        logger.warning(
                            "IP %s rate-limited: errors=%s, TTL=%.2fs, attempt=%s/%s",
                            ip, err_count, new_ttl, attempt, max_retries,
                        )

                        if attempt >= max_retries:
                            logger.error("Exceeded attempts (%s) for IP %s", max_retries, ip)
                            raise e

                        continue

                    else:
                        # Успешный вызов — уменьшаем счётчик задержки при серии успехов
                        succ = await rate_limit_manager.increment_success_counter(ip)
                        blocked, cur_ttl = await rate_limit_manager.is_ip_blocked(ip)

                        if succ >= success_threshold and blocked and cur_ttl > base:
                            last_err = await rate_limit_manager.get_last_error_ts(ip)
                            if time.time() - last_err >= cooldown:
                                new_ttl = base
                            else:
                                new_ttl = max([base, cur_ttl * 0.95])

                            if new_ttl <= base:
                                await rate_limit_manager.delete_block(ip)
                                logger.info("IP %s unblocked after %s successes", ip, succ)
                            else:
                                await rate_limit_manager.refresh_block(ip, new_ttl)
                                logger.debug(
                                    "IP %s TTL decreased: %.2f -> %.2f (%s successes)",
                                    ip, cur_ttl, new_ttl, succ,
                                )
                        elif blocked:
                            logger.debug("IP %s success (%s/%s to decrease)", ip, succ, success_threshold)

                        return result  # pyright: ignore

            # Если не удалось: выбрасываем специфичную ошибку
            raise TooManyRequestsInParserError(f"Failed after {max_retries} attempts")

        return wrapper

    return decorator

