"""Декоратор повторных попыток WB API с rate-limit и отдельной политикой для PoolTimeout."""

import asyncio
import time
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar, cast


from app.core.mp.wb.api.request_limit_manager import ApiCallState
from .adapter.abc_group_client import AbcAdapter
import logging

from .excs import (
    ApiForbiddenError,
    TooManyRequests,
    BadRequestError,
    UnknownApiRequestError,
    MaxAttemptsError,
    HttpTimeOutError,
    PoolTimeoutError,
)

logger = logging.getLogger(__name__)
# TODO Реализовать систему всплесков

POOL_TIMEOUT_MAX_ATTEMPTS = 3
POOL_TIMEOUT_RETRY_PAUSE_SEC = 2.0

# Тип результата функции
R = TypeVar("R")
F = TypeVar("F", bound=Callable[..., Awaitable[Any]])

_Collection = list[Any] | tuple[Any, ...] | set[Any]


def _collection_length(value: _Collection) -> int:
    """Длина коллекции с явной типизацией для pyright strict."""
    return len(value)


def _extract_items_count(args: tuple[Any, ...], kwargs: dict[str, Any]) -> int | None:
    for value in args:
        if isinstance(value, (list, tuple, set)):
            return _collection_length(cast(_Collection, value))
    body = kwargs.get("body")
    if body is not None:
        items = getattr(body, "items", None)
        if items is not None:
            return len(items)
    ids = kwargs.get("ids")
    if isinstance(ids, str) and ids:
        return len(ids.split(","))
    adv_ids = kwargs.get("adv_ids")
    if isinstance(adv_ids, (list, tuple, set)):
        return _collection_length(cast(_Collection, adv_ids))
    return None


def retry_decorator(
    period: int,
    limit: int | float,
    max_attempts: int = 50,
    max_delay: int = 120,
) -> Callable[[F], F]:

    def decorator(func: F) -> F:

        @wraps(func)
        async def wrapper(instance: AbcAdapter, *args: Any, **kwargs: Any) -> Any:

            interval_seconds = float(period)
            requests_per_interval = float(limit)
            min_pause = interval_seconds / requests_per_interval

            method_name = func.__name__
            api_call_state: dict[str, ApiCallState] = (
                instance.request_limit_manager.api_call_state
            )

            instance.api_call_state = api_call_state

            if method_name not in api_call_state:
                api_call_state[method_name] = {
                    "_last_query_time": None,
                    "_current_pause": min_pause,
                    "_attempts": 0,
                    "_pool_timeout_attempts": 0,
                    "_lock": asyncio.Lock(),
                }

            state = api_call_state[method_name]
            shop_id = instance.shop_id
            section_name = instance.section.name
            locker = state["_lock"]
            async with locker:
                while True:
                    time_since_last_query: float | None = None
                    time_to_wait = 0.0
                    last_query_time = state["_last_query_time"]
                    if last_query_time is not None:
                        current_time = time.time()
                        time_since_last_query = current_time - last_query_time
                        time_to_wait = max(
                            state["_current_pause"] - time_since_last_query, 0.0
                        )
                    await asyncio.sleep(time_to_wait)

                    try:
                        result = await func(instance, *args, **kwargs)
                        state["_last_query_time"] = time.time()
                        blended_pause = (
                            min_pause + state["_current_pause"]
                        ) / 2
                        # После 429 WB задаёт паузу ниже period/limit; без нижней границы
                        # усреднение разгоняло следующие запросы слишком близко друг к другу.
                        state["_current_pause"] = max(min_pause, blended_pause)
                        state["_attempts"] = 0
                        state["_pool_timeout_attempts"] = 0
                        return result

                    except ApiForbiddenError as e:
                        state["_attempts"] += 1
                        token_hash = e.not_valid_token_hash
                        if not token_hash:
                            raise e
                        # TODO: нужно сделать две отдельные ошибки на Api, чтобы пробрасывать без Option Section
                        section = e.section
                        assert section is not None
                        if state["_attempts"] >= max_attempts:
                            raise MaxAttemptsError() from e
                        await instance.auth_client_handler.mark_current_token_invalided(
                            token_hash, section=section
                        )
                        state["_current_pause"] = 0

                    # TODO: Повторный код максимальных попыток - сделать рефакторинг

                    except TooManyRequests as e:
                        state["_last_query_time"] = time.time()
                        state["_attempts"] += 1
                        next_pause = e.next_pause
                        if next_pause:
                            # Не уходить ниже period/limit: в логах min_bids Retry-After 13–15 с
                            # всё равно приводил к повторным 429 при целевом интервале 16 с.
                            state["_current_pause"] = max(
                                float(next_pause), min_pause
                            )
                        else:
                            state["_current_pause"] = min(
                                max(state["_current_pause"], 1.0) * 2, float(max_delay)
                            )
                        if state["_attempts"] >= max_attempts:
                            raise MaxAttemptsError() from e

                    except PoolTimeoutError as e:
                        state["_last_query_time"] = time.time()
                        pool_attempts = state.get("_pool_timeout_attempts", 0) + 1
                        state["_pool_timeout_attempts"] = pool_attempts
                        items_count = _extract_items_count(args, kwargs)
                        if pool_attempts >= POOL_TIMEOUT_MAX_ATTEMPTS:
                            logger.error(
                                "WB PoolTimeout retries exhausted: exc_type=PoolTimeout "
                                "endpoint=%s section=%s shop_id=%s coroutine=%s "
                                "pool_timeout_attempts=%s items_count=%s",
                                method_name,
                                section_name,
                                shop_id,
                                method_name,
                                pool_attempts,
                                items_count,
                            )
                            raise MaxAttemptsError(
                                f"PoolTimeout: не удалось выполнить {method_name} "
                                f"за {POOL_TIMEOUT_MAX_ATTEMPTS} попыток для shop_id={shop_id}"
                            ) from e
                        state["_current_pause"] = POOL_TIMEOUT_RETRY_PAUSE_SEC
                        logger.warning(
                            "WB PoolTimeout retry: exc_type=PoolTimeout endpoint=%s "
                            "section=%s shop_id=%s coroutine=%s attempt=%s/%s items_count=%s",
                            method_name,
                            section_name,
                            shop_id,
                            method_name,
                            pool_attempts,
                            POOL_TIMEOUT_MAX_ATTEMPTS,
                            items_count,
                        )

                    except (
                        UnknownApiRequestError,
                        HttpTimeOutError,
                    ) as e:
                        state["_last_query_time"] = time.time()
                        state["_attempts"] += 1
                        if state["_attempts"] >= max_attempts:
                            raise MaxAttemptsError(
                                f"Не удалось выполнить {method_name} за {max_attempts} попыток для shop_id={shop_id}"
                            ) from e

                        state["_current_pause"] = min(
                            max(state["_current_pause"], 1.0) * 2, float(max_delay)
                        )
                    except BadRequestError as e:
                        raise e

        return cast(F, wrapper)

    return decorator
