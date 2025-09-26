"""
Обертки для работы с API Wildberries.


"""

import asyncio
import json
import logging
import re
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast

import aiohttp
from aiohttp import (
    ClientConnectionError,
    ClientOSError,
    ClientResponseError,
    ServerDisconnectedError,
)

from .exceptions import (
    ApiErrorWithCode,
    ApiForbiddenError,
    BadRequestError,
    MaxAttemptsError,
    MinAdvBidWBApiError,
    NotMatchWBApiError,
    NotValidDataError,
    TooManyRequests,
    UnknownApiRequestError,
)
from .protocols import WBAPIProtocol

logger = logging.getLogger(__name__)


# Тип возвращаемого значения
TypeWBAPIProtocol = TypeVar("TypeWBAPIProtocol", bound=WBAPIProtocol)
# Тип результата функции
R = TypeVar("R")
F = TypeVar("F", bound=Callable[..., Awaitable[Any]])

from .

def auth_for_adapter(
    requests_per_interval: int,
    interval_seconds: int | float,
    max_attempts: int = 50,
    max_delay: int = 120,
) -> Callable[[F], F]:
    """
    Декоратор для обработки ошибок API запросов с повторными попытками и адаптивным ожиданием.
    """

    def decorator(func: F) -> F:
        """
        Декоратор для обработки ошибок API запросов с повторными попытками и адаптивным ожиданием.
        """

        async def wrapper(
            instance: TypeWBAPIProtocol, *args: Any, **kwargs: Any
        ) -> Any:
            """Обертка для декоратора, которая добавляет обработку ошибок и адаптивное ожидание."""
            if not hasattr(instance, "api_call_state"):
                instance.api_call_state = {}

            method_name = func.__name__
            if method_name not in instance.api_call_state:
                instance.api_call_state[method_name] = {
                    "_last_query_time": None,
                    "_current_pause": interval_seconds / requests_per_interval,
                    "_attempts": 0,
                }

            state = instance.api_call_state[method_name]
            shop_id = instance.shop_id
            while state["_attempts"] < max_attempts:
                last_query_time: float | None = state["_last_query_time"]
                if last_query_time:
                    current_time = time.time()
                    time_since_last_query = current_time - last_query_time
                    time_to_wait = max(
                        state["_current_pause"] - time_since_last_query, 0
                    )
                    await asyncio.sleep(time_to_wait)

                try:
                    state["_last_query_time"] = time.time()
                    result = await func(instance, *args, **kwargs)
                    logger.debug(f"Запрос {method_name} выполнен успешно для {shop_id}")
                    next_pause = (
                        interval_seconds / requests_per_interval
                        + state["_current_pause"]
                    ) / 2
                    state["_current_pause"] = next_pause
                    state["_attempts"] = 0
                    return result
                except ApiForbiddenError:
                    await instance.set_next_token(method_name)
                    state["_current_pause"] = 0
                except (
                    TooManyRequests,
                    BadRequestError,
                    UnknownApiRequestError,
                    NotValidDataError,
                    ClientOSError,
                    ServerDisconnectedError,
                    ClientResponseError,
                    ClientConnectionError,
                    NotMatchWBApiError,
                ) as e:
                    if state["_attempts"] >= max_attempts:
                        raise MaxAttemptsError(
                            f"Не удалось выполнить {method_name} за {max_attempts} попыток для shop_id={shop_id}"
                        ) from e
                    state["_attempts"] += 1
                    state["_current_pause"] = min(
                        max(state["_current_pause"], 1) * 2, max_delay
                    )
                    logger.debug(
                        f"Следующая пауза между запросами: {state['_current_pause']} секунд для shop_id: {shop_id}"
                    )
                except Exception as e:
                    raise e

        return cast(F, wrapper)

    return decorator

