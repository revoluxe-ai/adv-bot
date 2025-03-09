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




async def requests(session, method, url, data=None, json_data=None, headers=None):
    async with session.request(method, url, data=data, headers=headers, json=json_data) as response:
        try:
            logger.debug(f'Запрос к {url} выполнен. Статус: {response.status}')
            text = await response.text()
            logger.debug(f'Ответ от сервера: {text}')
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