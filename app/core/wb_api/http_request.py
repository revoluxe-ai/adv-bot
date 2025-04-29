"""
Обертки для работы с API Wildberries.


"""

import asyncio
import json
import logging
import time
from typing import (
    Callable,
    Awaitable,
    Optional,
    Union,
    Any,
    TypeVar,
    Dict,
    TypedDict,
    cast,
)

import aiohttp
from aiohttp import ClientOSError, ServerDisconnectedError, ClientResponseError

from .exceptions import (
    ApiForbiddenError,
    TooManyRequests,
    UnknownApiRequestError,
    BadRequestError,
    NotValidDataError,
    ApiErrorWithCode,
)
from .protocols import WBAPIProtocol

logger = logging.getLogger(__name__)


# Тип возвращаемого значения
TypeWBAPIProtocol = TypeVar("TypeWBAPIProtocol", bound=WBAPIProtocol)
# Тип результата функции
R = TypeVar("R")
F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


class APICallState(TypedDict):
    _last_query_time: Optional[float]
    _current_pause: float
    _attempts: int


def try_except_decorator(
    requests_per_interval: int,
    interval_seconds: Union[int, float],
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
                last_query_time: Optional[float] = state["_last_query_time"]
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
                    await instance.set_next_token()
                    state["_current_pause"] = 0
                except (
                    TooManyRequests,
                    BadRequestError,
                    UnknownApiRequestError,
                    NotValidDataError,
                    ClientOSError,
                    ServerDisconnectedError,
                    ClientResponseError,
                ) as e:
                    if state["_attempts"] >= max_attempts:
                        raise e
                    state["_attempts"] += 1
                    state["_current_pause"] = min(
                        max(state["_current_pause"], 1) * 2, max_delay
                    )
                    logger.debug(
                        f'Следующая пауза между запросами: {state["_current_pause"]} секунд для shop_id: {shop_id}'
                    )
                except Exception as e:
                    raise e

            raise RuntimeError(
                f"Не удалось выполнить {method_name} за {max_attempts} попыток для shop_id={shop_id}"
            )

        return cast(F, wrapper)

    return decorator


async def requests(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    data: Optional[Any] = None,
    json_data: Optional[Any] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """Обертка для выполнения HTTP-запросов с обработкой ошибок и логированием."""
    async with session.request(
        method, url, data=data, headers=headers, json=json_data
    ) as response:
        try:
            logger.debug(f"Запрос к {url} выполнен. Статус: {response.status}")
            response.raise_for_status()
        except aiohttp.ClientResponseError as e:  # Предполагая использование aiohttp
            if e.status == 401:
                raise ApiForbiddenError("Неверный API ключ") from e
            if e.status == 429:
                logger.debug(f"Превышен лимит запросов к API: {url}")
                raise TooManyRequests(e) from e
            else:
                resp = await response.text()
                logger.error(f"Ошибка запроса: {resp}")
                raise BadRequestError(e) from e
        except NotValidDataError as e:
            raise NotValidDataError(e) from e
        except Exception as e:
            raise UnknownApiRequestError(e) from e

        # Если код не в блоке except, значит ответ был успешным (статус 200-299)
        response_text: str = await response.text()
        if response_text:
            json_answer = json.loads(response_text)
            if isinstance(json_answer, dict):
                if code := json_answer.get("code"):
                    message = json_answer.get("message", "")
                    rejection = json_answer.get("rejection", "")
                    raise ApiErrorWithCode(code, message, rejection)
        return response_text
