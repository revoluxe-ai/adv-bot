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
import json
import logging
from .exceptions import ApiForbiddenError
from .ABC_WB_API import ABC_WB_API

logger = logging.getLogger(__name__)




class TokenRightChecker(app.wildberries.ABC_WB_API.ABC_WB_API):

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
            return True


