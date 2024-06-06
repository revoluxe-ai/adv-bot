import asyncio
from asyncio import Lock
import datetime

from app.utils import redis_manager
from .models import WBToken


class OnlyRead:
    TRUE = True
    FALSE = False



locker = Lock()

class Rights:
    CONTENT = 'Контент'
    ANALYTICS = 'Аналитика'
    PRICES_AND_DISCOUNTS = 'Цены и скидки'
    MARKETPLACE = 'Маркетплейс'
    STATISTICS = 'Статистика'
    PROMOTION = 'Продвижение'
    QUESTIONS_AND_REVIEWS = 'Вопросы и отзывы'
    RECOMMENDATIONS = 'Рекомендации'




import logging

import aiohttp

from .ABC_WB_API import Headers, WbRequestApiMixin
from .exceptions import ApiForbiddenError, TooManyRequests, UnknownApiRequestError, BadRequestError

logger = logging.getLogger(__name__)







class TokenRightChecker(WbRequestApiMixin):
     def __init__(self, token):
        self.token = token
        self.headers = Headers(token)

     @property
     def _wb_user_cabinet(self):
        return None

     @property
     def _only_read(self):
         return OnlyRead.FALSE

     @property
     def _rights(self) -> set[str]:
         return {Rights.CONTENT, Rights.PROMOTION}


     async def adverts(self):
        url = 'https://advert-api.wb.ru/adv/v1/promotion/count'

        async with aiohttp.ClientSession() as session:
             await self.requests(session, 'GET', url, headers=self.headers.standart)


     async def content(self):
        limit = 1
        url = 'https://suppliers-api.wildberries.ru/content/v2/get/cards/list'
        data_for_req = {
            "settings": {
                "sort": {
                    "ascending": False
                },
                "cursor": {
                    "limit": limit
                },
                "filter": {
                    "withPhoto": -1,
                }
            }
        }

        async with aiohttp.ClientSession() as session:
            await self.requests(session, 'POST',  url, json_data=data_for_req,
                                        headers=self.headers.standart)






async def check_token(token: WBToken):
    hash_token = hash(token)
    logger.debug('Проверка прав на токен')
    check = await redis_manager.get_token_rights(hash_token)
    if check:
        logger.debug('Права на токен уже проверены')
        return
    try:
        expire = token.expires
        if expire < datetime.datetime.now():
            raise ApiForbiddenError
        async with locker:
            checker = TokenRightChecker(token)
            await asyncio.gather(checker.adverts(), checker.content())
        await redis_manager.set_token_rights(hash_token, timeout=60*60)
    except ApiForbiddenError as exc:
        logger.debug(f'Токен отозван')
        raise exc
    except UnknownApiRequestError:
        logger.debug('Ошибка проверки токена (пропущено)')
    except TooManyRequests:
        logger.debug('Превышен лимит запросов')
    except BadRequestError:
        logger.debug('Ошибка запроса')
