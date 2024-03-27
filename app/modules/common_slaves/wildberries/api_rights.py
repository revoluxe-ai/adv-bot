import app



class OnlyRead:
    TRUE = True
    FALSE = False


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
from .exceptions import ApiForbiddenError
from .ABC_WB_API import ABC_WB_API, WbRequestApiMixin, Headers

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


     async def adverts(self)-> bool:
        url = 'https://advert-api.wb.ru/adv/v1/promotion/count'
        async with aiohttp.ClientSession() as session:
            try:
                await self.requests(session, 'GET', url, headers=self.headers.standart)
            except ApiForbiddenError:
                return False
            except Exception as e:
                logger.error(e)
                return True
            return True


     async def content(self)-> bool:
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
            try:
                await self.requests(session, 'POST',  url, json_data=data_for_req,
                                    headers=self.headers.standart)
            except ApiForbiddenError:
                return False
            except Exception as e:
                logger.error(e)
                return True
            return True


