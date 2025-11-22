import asyncio
import time
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar, cast


from app.core.mp.wb.api.request_limit_manager import ApiCallState
from .adapter.abc_group_client import AbcAdapter
import logging

from .excs import ApiForbiddenError, TooManyRequests, BadRequestError, UnknownApiRequestError, MaxAttemptsError, \
    HttpTimeOutError

logger = logging.getLogger(__name__)
# TODO Реализовать систему всплесков


# Тип результата функции
R = TypeVar("R")
F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def retry_decorator(
        period: int,
        limit: int | float,
        max_attempts: int = 50,
        max_delay: int = 120,
) -> Callable[[F], F]:

    def decorator(func: F) -> F:

        @wraps(func)
        async def wrapper(
            instance: AbcAdapter, *args: Any, **kwargs: Any
        ) -> Any:

            interval_seconds = float(period)
            requests_per_interval = float(limit)

            method_name = func.__name__
            api_call_state: dict[str, ApiCallState] = (
                instance.request_limit_manager.api_call_state
            )

            instance.api_call_state = api_call_state

            if method_name not in api_call_state:
                api_call_state[method_name] = {
                    "_last_query_time": None,
                    "_current_pause": interval_seconds / requests_per_interval,
                    "_attempts": 0,
                }

            state = api_call_state[method_name]
            shop_id = instance.shop_id

            while True:
                last_query_time = state["_last_query_time"]
                if last_query_time is not None:
                    current_time = time.time()
                    time_since_last_query = current_time - last_query_time
                    time_to_wait = max(
                        state["_current_pause"] - time_since_last_query, 0.0
                    )
                    await asyncio.sleep(time_to_wait)

                try:
                    state["_last_query_time"] = time.time()
                    result = await func(
                        instance, *args, **kwargs
                    )

                    next_pause = (
                        interval_seconds / requests_per_interval
                        + state["_current_pause"]
                    ) / 2

                    state["_current_pause"] = next_pause
                    state["_attempts"] = 0
                    return result

                except ApiForbiddenError as e:
                    state["_attempts"] += 1
                    token_hash = e.not_valid_token_hash
                    if not token_hash:
                        raise e
                    if state["_attempts"] >= max_attempts:
                        raise MaxAttemptsError() from e
                    await instance.auth_client_handler.mark_current_token_invalided(token_hash)
                    state["_current_pause"] = 0


                # TODO: Повторный код максимальных попыток - сделать рефакторинг

                except TooManyRequests as e:
                    state["_attempts"] += 1
                    if state["_attempts"] >= max_attempts:
                        raise MaxAttemptsError() from e
                    next_pause = e.next_pause
                    if next_pause:
                        state["_current_pause"] = next_pause
                    else:
                        state["_current_pause"] = min(
                            max(state["_current_pause"], 1.0) * 2,
                            float(max_delay)
                        )

                except (BadRequestError, UnknownApiRequestError, HttpTimeOutError) as e:
                    state["_attempts"] += 1
                    if state["_attempts"] >= max_attempts:
                        raise MaxAttemptsError(
                            f"Не удалось выполнить {method_name} за {max_attempts} попыток для shop_id={shop_id}"
                        ) from e

                    state["_current_pause"] = min(
                        max(state["_current_pause"], 1.0) * 2,
                        float(max_delay)
                    )

                except Exception as e:
                    raise e
        return cast(F, wrapper)

    return decorator

