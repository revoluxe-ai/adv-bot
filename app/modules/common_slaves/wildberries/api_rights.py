import asyncio
import datetime

from aiohttp import ClientTimeout

from app.utils import redis_manager
from aiocache import cached_stampede
from asyncio import Lock
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




import aiohttp
import logging
from .exceptions import ApiForbiddenError, UnknownApiRequestError, TooManyRequests, BadRequestError
from .ABC_WB_API import ABC_WB_API, WbRequestApiMixin, Headers

logger = logging.getLogger(__name__)

timeout = aiohttp.ClientTimeout(
    total=3,  # Общий таймаут для запроса
    connect=2,  # Таймаут для подключения
    sock_read=2,  # Таймаут для чтения сокета
    sock_connect=2  # Таймаут для соединения сокета
)





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
        logger.debug('Проверка прав на рекламу')
        url = 'https://advert-api.wb.ru/adv/v1/promotion/count'

        async with aiohttp.ClientSession(timeout=timeout) as session:
              await self.requests(session, 'GET', url, headers=self.headers.standart)
        logger.debug('Проверка прав на рекламу завершена')

     async def content(self):
        logger.debug('Проверка прав на контент')
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

        async with aiohttp.ClientSession(timeout=timeout) as session:
            await self.requests(session, 'POST',  url, json_data=data_for_req,
                                        headers=self.headers.standart)

        logger.debug('Проверка прав на контент завершена')


async def check_token(token):
    hash_token = hash(token)
    logger.debug('Проверка прав на токен')
    check = await redis_manager.get_token_rights(hash_token)
    logger.debug(f'Данные о проверке из Redis: {check}')
    if check:
        logger.debug('Права на токен уже проверены')
        return
    try:
        logger.debug('Проверка прав на токен')
        expire = token.expires
        if expire < datetime.datetime.now():
            raise ApiForbiddenError('Токен просрочен')
        async with locker:
            logger.debug('Проверка прав на в чекере')
            checker = TokenRightChecker(token)
            await asyncio.gather(checker.adverts(), checker.content())
            logger.debug('Проверка прав на токен завершена')
        await redis_manager.set_token_rights(hash_token, timeout=60*60)
        logger.debug('Права на токен сохранены в Redis')
    except ApiForbiddenError as exc:
        logger.debug(f'Токен отозван')
        raise exc
    except UnknownApiRequestError:
        logger.debug('Ошибка проверки токена (пропущено)')
    except TooManyRequests:
        logger.debug('Превышен лимит запросов')
    except BadRequestError:
        logger.debug('Ошибка запроса')