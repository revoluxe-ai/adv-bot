"""
Обертки для работы с API Wildberries.


"""

import asyncio
import json
import logging
import re
import time
from collections.abc import Awaitable, Callable
from json import JSONDecodeError
from typing import (
    Any,
    TypeVar,
    cast,
)

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


def try_except_decorator(
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
            while state["_attempts"] < max_attempts:  # noqa
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
                    logger.debug(
                        "Запрос %s выполнен успешно для %s", method_name, shop_id
                    )
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
                    BadRequestError,
                    NotMatchWBApiError,
                    NotValidDataError,
                    UnknownApiRequestError,
                ):
                    # Клиентские и неизвестные ошибки не ретраим — повтор не поможет.
                    raise
                except (
                    TooManyRequests,
                    ClientOSError,
                    ServerDisconnectedError,
                    ClientResponseError,
                    ClientConnectionError,
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
                        "Следующая пауза между запросами: %s секунд для shop_id: %s, ошибка: %s",
                        state["_current_pause"],
                        shop_id,
                        e,
                    )
                except Exception as e:
                    raise e

        return cast(F, wrapper)

    return decorator


async def requests(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    data: Any | None = None,
    json_data: Any | None = None,
    headers: dict[str, str] | None = None,
) -> str:
    """Обертка для выполнения HTTP-запросов с обработкой ошибок и логированием."""
    response_text: str = ""
    async with session.request(
        method, url, data=data, headers=headers, json=json_data
    ) as response:
        try:
            response_text = await response.text()
            logger.debug(
                "Запрос к %s выполнен. Статус: %s, ответ: %s",
                url,
                response.status,
                response_text[:500],
            )
            response.raise_for_status()
        except aiohttp.ClientResponseError as e:  # Предполагая использование aiohttp
            if e.status == 401:
                raise ApiForbiddenError("Неверный API ключ") from e
            if e.status == 403 and "scope is not allowed" in response_text:
                # Токен есть, но не имеет нужного scope — переключаем на следующий
                raise ApiForbiddenError(
                    "Токен не имеет нужного scope для данного ресурса"
                ) from e
            if e.status == 429:
                logger.debug("Превышен лимит запросов к API: %s", url)
                raise TooManyRequests(e) from e
            if e.status == 400:
                exc = get_error_from_response(response_text)
                raise exc
            else:
                exc = get_error_from_response(response_text)
                raise exc

        except NotValidDataError as e:
            raise NotValidDataError(e) from e
        except Exception as e:
            raise UnknownApiRequestError(e) from e

        # Если код не в блоке except, значит ответ был успешным (статус 200-299)

        if response_text:
            if isinstance(response_text, dict):
                if code := response_text.get("code"):
                    message = response_text.get("message", "")
                    rejection = response_text.get("rejection", "")
                    raise ApiErrorWithCode(code, message, rejection)
        return response_text


def get_error_from_response(response_text: str) -> Exception:
    """
    Извлекает ошибку из ответа API Wildberries.
    """
    try:
        response_json = json.loads(response_text)
    except JSONDecodeError as e:
        logger.error(
            'Ошибка декодирования JSON из ответа API Wildberries: "%s"',
            response_text[:500],
        )
        raise NotValidDataError("Ответ не является валидным JSON") from e
    match response_json:
        case {
            "errors": [{"detail": detail, "field": field}],
            "status": status,
            "title": title,
        }:
            if "wrong bid value" in detail:
                pattern = re.compile(r"min: (?P<min>\d+)")
                match_result = re.search(pattern, detail)
                if match_result is not None:
                    match_min_cpm_group: str = match_result.group("min")
                    if match_min_cpm_group is not None:
                        assert match_min_cpm_group
                        new_min_ctr = int(match_min_cpm_group)
                        exc = MinAdvBidWBApiError(new_min_ctr)
                        return exc
                return ApiErrorWithCode(
                    status, title, f"Поле: {field}, Ошибка: {detail}"
                )
            else:
                return ApiErrorWithCode(
                    status, title, f"Поле: {field}, Ошибка: {detail}"
                )
    return NotMatchWBApiError("Неизвестная ошибка", response_text)
