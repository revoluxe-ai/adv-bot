from .http_request import requests, try_except_decorator
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
from .ABC_WB_API import WbRequestApiMixin, Headers

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


     def set_next_token(self):
        raise ApiForbiddenError('Токен отозван')

     @property
     def _wb_user_cabinet(self):
        return None

     @property
     def _only_read(self):
         return OnlyRead.FALSE

     @property
     def _rights(self) -> set[str]:
         return {Rights.CONTENT, Rights.PROMOTION}

     @try_except_decorator(1, 1, max_attempts=50, max_delay=120)
     async def adverts(self):
        logger.debug('Проверка прав на рекламу')
        url = 'https://advert-api.wb.ru/adv/v1/promotion/count'

        async with aiohttp.ClientSession(timeout=timeout) as session:
              await requests(session, 'GET', url, headers=self.headers.standart)
        logger.debug('Проверка прав на рекламу завершена')


     # @try_except_decorator(1, 1, max_attempts=50, max_delay=120)
     # async def content(self):
     #    logger.debug('Проверка прав на контент')
     #    limit = 1
     #    url = 'https://suppliers-api.wildberries.ru/content/v2/get/cards/list'
     #    data_for_req = {
     #        "settings": {
     #            "sort": {
     #                "ascending": False
     #            },
     #            "cursor": {
     #                "limit": limit
     #            },
     #            "filter": {
     #                "withPhoto": -1,
     #            }
     #        }
     #    }
     #    async with aiohttp.ClientSession() as session:
     #        await requests(
     #            session,
     #            'POST',
     #            url,
     #            json_data=data_for_req,
     #            headers=self.headers.standart
     #        )
     #
     #    logger.debug('Проверка прав на контент завершена')


