import asyncio
import json
import time
from typing import Optional

import aiohttp
from aiohttp import ClientOSError, ServerDisconnectedError, ClientResponseError

from .exceptions import (ApiForbiddenError,
                         TooManyRequests,
                         UnknownApiRequestError,
                         BadRequestError,
                         NotValidDataError,
                         CardNotFoundInWB, ApiErrorWithCode)
import logging

logger = logging.getLogger(__name__)

def try_except_decorator(requests_per_interval, interval_seconds, max_attempts=50, max_delay=120):
    def decorator(func):
        async def wrapper(instance, *args, **kwargs):
            if not hasattr(instance, '_api_call_state'):
                instance._api_call_state = {}

            method_name = func.__name__
            if method_name not in instance._api_call_state:
                instance._api_call_state[method_name] = {
                    '_last_query_time': None,
                    '_current_pause': interval_seconds / requests_per_interval,
                    '_attempts': 0,
                }

            state = instance._api_call_state[method_name]
            shop_id = instance.shop_id
            while state['_attempts'] < max_attempts:
                last_query_time: Optional[float] = state['_last_query_time']
                if last_query_time:
                    current_time = time.time()
                    time_since_last_query = current_time - last_query_time
                    time_to_wait = max(state['_current_pause'] - time_since_last_query, 0)
                    await asyncio.sleep(time_to_wait)

                try:
                    state['_last_query_time'] = time.time()
                    result = await func(instance, *args, **kwargs)
                    logger.debug(f'Запрос {method_name} выполнен успешно для {shop_id}')
                    next_pause = (interval_seconds / requests_per_interval + state['_current_pause']) / 2
                    state['_current_pause'] = next_pause
                    state['_attempts'] = 0  # Сброс попыток после успешного выполнения
                    return result
                except ApiForbiddenError:
                    await instance.set_next_token()
                    state['_current_pause'] = 0
                except (TooManyRequests,
                        UnknownApiRequestError,
                        NotValidDataError,
                        ClientOSError,
                        ServerDisconnectedError,
                        ClientResponseError) as e:
                    if state['_attempts'] >= max_attempts:
                        raise e
                    state['_attempts'] += 1
                    new_next_pause = min(max(state['_current_pause'], 1) * 2, max_delay)
                    state['_current_pause'] = new_next_pause
                    logger.debug(f'Следующая пауза между запросами: {state["_current_pause"]} секунд для shop_id: {shop_id}')

        return wrapper
    return decorator


async def requests(session, method, url, data=None, json_data=None, headers=None):
    async with session.request(method, url, data=data, headers=headers, json=json_data) as response:
        try:
            logger.debug(f'Запрос к {url} выполнен. Статус: {response.status}')
            text = await response.text()
            response.raise_for_status()
        except aiohttp.ClientResponseError as e:  # Предполагая использование aiohttp
            if e.status == 401:
                raise ApiForbiddenError('Неверный API ключ') from e
            if e.status == 429:
                logger.debug(f'Превышен лимит запросов к API: {url}')
                raise TooManyRequests(e) from e
            else:
                logger.error(f'Ошибка при запросе к {url}: {text}', exc_info=True)
                raise BadRequestError(e) from e
        except NotValidDataError as e:
            raise NotValidDataError(e) from e
        except Exception as e:
            raise UnknownApiRequestError(e) from e

        # Если код не в блоке except, значит ответ был успешным (статус 200-299)
        text = await response.text()
        if text:
            json_answer = json.loads(text)
            if isinstance(json_answer, dict):
                if code := json_answer.get('code'):
                    raise ApiErrorWithCode(code, \
                                                      json_answer.get('message'), json_answer.get('rejection'))

        return text