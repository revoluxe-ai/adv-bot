from __future__ import annotations

import asyncio
import functools
import inspect
import logging
import random
import time
import weakref
from typing import Any, Awaitable, Callable

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


def _get_lock(identity: str) -> asyncio.Lock:
    lock = _locks.get(identity)
    if lock is None:
        lock = asyncio.Lock()
        _locks[identity] = lock
    return lock


async def _resolve_identity(
    identity_getter: Callable[..., Awaitable[str] | str] | None,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> str:
    if identity_getter is not None:
        identity = identity_getter(*args, **kwargs)
        if inspect.isawaitable(identity):
            identity = await identity
        if identity is None:
            raise ValueError("identity_getter must return a non-empty identity string")
        return str(identity)

    return await get_public_ip()


def rate_limited_request(
    rate_limit_manager: 'ParserRateLimitRedisManager' | None,
    *,
    max_retries: int = 50,
    delay: float = settings.PARSING_LIMITER_DELAY,
    identity_getter: Callable[..., Awaitable[str] | str] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Декоратор адаптивного rate-limit по IP.

    Сохраняет поведение: при 429 — увеличивает TTL экспоненциально, при успешных запросах
    постепенно снижает TTL и в итоге снимает блокировку.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if rate_limit_manager is None:
            @functools.wraps(func)
            async def passthrough(*args: Any, **kwargs: Any) -> Any:
                return await func(*args, **kwargs)  # pyright: ignore

            return passthrough

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            identity = await _resolve_identity(identity_getter, args, kwargs)
            base = delay
            mult = settings.WB_RATE_LIMIT_MULTIPLIER
            max_delay = settings.WB_RATE_LIMIT_MAX_DELAY_SEC
            success_threshold = 3
            cooldown = 60.0

            attempt = 0
            while attempt < max_retries:
                attempt += 1

                async with _get_lock(identity):
                    # Ждём, пока IP не разблокирован
                    while True:
                        blocked, ttl = await rate_limit_manager.is_ip_blocked(identity)
                        if not blocked:
                            break
                        await asyncio.sleep(ttl + random.uniform(0, 0.1))

                    try:
                        result = await func(*args, **kwargs)  # pyright: ignore
                    except (TooManyRequestsInParserError, WBConnectionRateLimitError) as e:
                        if isinstance(e, WBConnectionRateLimitError):
                            logger.warning("WBConnectionRateLimitError")

                        err_count = await rate_limit_manager.increment_error_counter(identity)
                        await rate_limit_manager.set_last_error_ts(identity)

                        new_ttl = min(base * (mult ** err_count), max_delay)
                        await rate_limit_manager.block_ip(identity, new_ttl)

                        logger.warning(
                            "IP %s rate-limited: errors=%s, TTL=%.2fs, attempt=%s/%s",
                            identity, err_count, new_ttl, attempt, max_retries,
                        )

                        if attempt >= max_retries:
                            logger.error(
                                "Exceeded attempts (%s) for identity %s",
                                max_retries,
                                identity,
                            )
                            raise e

                        continue

                    else:
                        # Успешный вызов — уменьшаем счётчик задержки при серии успехов
                        succ = await rate_limit_manager.increment_success_counter(identity)
                        blocked, cur_ttl = await rate_limit_manager.is_ip_blocked(identity)

                        if succ >= success_threshold and blocked and cur_ttl > base:
                            last_err = await rate_limit_manager.get_last_error_ts(identity)
                            if time.time() - last_err >= cooldown:
                                new_ttl = base
                            else:
                                new_ttl = max([base, cur_ttl * 0.95])

                            if new_ttl <= base:
                                await rate_limit_manager.delete_block(identity)
                                logger.info(
                                    "Identity %s unblocked after %s successes",
                                    identity,
                                    succ,
                                )
                            else:
                                await rate_limit_manager.refresh_block(identity, new_ttl)
                                logger.debug(
                                    "Identity %s TTL decreased: %.2f -> %.2f (%s successes)",
                                    identity,
                                    cur_ttl,
                                    new_ttl,
                                    succ,
                                )
                        elif blocked:
                            logger.debug(
                                "Identity %s success (%s/%s to decrease)",
                                identity,
                                succ,
                                success_threshold,
                            )

                        return result  # pyright: ignore

            # Если не удалось: выбрасываем специфичную ошибку
            raise TooManyRequestsInParserError(f"Failed after {max_retries} attempts")

        return wrapper

    return decorator

