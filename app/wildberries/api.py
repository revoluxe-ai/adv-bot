from .ABC_WB_API import ABC_WB_API
from .data_classes.card_from_wb import CardFromWB
import aiohttp
from typing import Union
import logging
import asyncio
import datetime
from .data_classes.adv import Adv
import time
import json
from .data_classes.keywordstat import KeywordStat
from .models import WBToken, AdvSetting
from . import exceptions
from . import api_rights
import app



logger = logging.getLogger(__name__)



def _try_except_decorator(requests_per_interval, interval_seconds):
    min_interval = interval_seconds / requests_per_interval
    last_query_time = 0
    sleep_on_error = min_interval
    def decorator(request_func):
        async def wrapper(*args, **kwargs):
            nonlocal sleep_on_error
            nonlocal last_query_time
            # Рассчитываем время, через которое можно сделать следующий запрос
            current_time = time.time()
            time_since_last_query = current_time - last_query_time
            time_to_wait = max(0, min_interval - time_since_last_query)
            while True:
                if time_to_wait > 0:
                    # Если нужно подождать, ждем до конца интервала
                    await asyncio.sleep(time_to_wait)
                try:
                    result = await request_func(*args, **kwargs)
                    last_query_time = time.time()
                    sleep_on_error = min_interval
                    return result
                except exceptions.ApiForbiddenError:
                    raise exceptions.ApiForbiddenError
                except exceptions.UnknownApiRequestError as e:
                    logger.error(f'Ошибка при запросе к API: {e},'
                                 f' повтор через {sleep_on_error} секунд')
                    await asyncio.sleep(sleep_on_error)

                    sleep_on_error *= 2

        return wrapper

    return decorator






class AdvertApi(ABC_WB_API):
    _rights: set = {api_rights.Rights.PROMOTION}
    _only_read = api_rights.OnlyRead.FALSE
    live_company_status = [4, 9, 11]
    auto_adv_types = [8]


    @_try_except_decorator(4, 1)
    async def get_keywords_stat(self, adv_setting: AdvSetting)-> list[KeywordStat]:
        keywords = []
        url = f'https://advert-api.wb.ru/adv/v2/auto/daily-words?id={adv_setting.adv_id}'
        async with aiohttp.ClientSession() as session:
            response_text = await self.requests(session, 'GET', url,
                                                headers=self.headers.standart)
            answer = json.loads(response_text)
            update_timestamp = datetime.datetime.now()
            for data in answer:
                wb_timestamp = datetime.datetime.fromisoformat(data['date']).date()
                stat = data['stat']
                for keyword_stat in stat:
                    keyword_stat['date'] = wb_timestamp
                    keyword_stat['update_timestamp'] = update_timestamp
                    keyword_stat['adv_id'] = adv_setting.adv_id
                    keyword_stat['text'] = keyword_stat.pop('keyword')
                    keyword_stat['spend'] = keyword_stat.pop('sum')
                    keyword = KeywordStat(**keyword_stat)
                    keywords.append(keyword)
        return keywords



    @_try_except_decorator(1, 1)
    async def get_cards_by_text(self, texts: set[Union[str, int]]):
        cards = []
        url = 'https://suppliers-api.wildberries.ru/content/v2/get/cards/list'
        async with aiohttp.ClientSession() as session:
            for text in texts:
                text = str(text)
                data_for_req = {
                    "settings": {
                        "sort": {
                            "ascending": False
                        },
                        "cursor": {
                            "limit": 1
                        },
                        "filter": {
                            "withPhoto": -1,
                            'textSearch': text

                        }
                    }
                }
                async with session.post(url, json=data_for_req, headers=self.headers.standart) as response:
                    answer = await self.requests(session, 'POST', url,
                                           json_data=data_for_req,
                                           headers=self.headers.standart)
                    answer = json.loads(answer)
                card_json = answer['cards'][0]
                card = CardFromWB(card_json)
                cards.append(card)
        return cards


    @_try_except_decorator(5, 1)
    async def get_advertIds(self, statuses: list, adv_types)->list[Adv]:
        advertIds = []
        url = 'https://advert-api.wb.ru/adv/v1/promotion/count'
        async with aiohttp.ClientSession() as session:
            response_text = await self.requests(session, 'GET', url,
                                                headers=self.headers.standart)
            answer = json.loads(response_text)
            # Используем json.loads для преобразования текста ответа в JSON
            adverts:list = answer['adverts']
            for advert in adverts:
                adv_type = advert['type']
                adv_status = advert['status']
                if adv_status in statuses and adv_type in adv_types:
                    for advert in advert['advert_list']:
                        advertId = advert['advertId']
                        advertIds.append(advertId)

        return advertIds
    @_try_except_decorator(5, 1)
    async def get_advs(self, adv_ids: list):
        advs = []
        url = f'https://advert-api.wb.ru/adv/v1/promotion/adverts'
        for chunk in self.chunks(adv_ids, 50):
            async with aiohttp.ClientSession() as session:
                response_text = await self.requests(session, 'POST', url, json_data=chunk,
                                                    headers=self.headers.standart)
                answer = json.loads(response_text)
                for advert in answer:
                        adv = Adv(advert)
                        advs.append(adv)
        return advs


    async def get_live_advs(self):
        adv_ids = await self.get_advertIds(self.live_company_status, self.auto_adv_types)
        advs = await self.get_advs(adv_ids)
        return advs



class WBApi:
    def __init__(self, wb_user_cabinet: app.my_types.WBUserCabinet):
        self.advert = AdvertApi(wb_user_cabinet)









