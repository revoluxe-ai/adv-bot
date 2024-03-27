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
from .data_classes.subcategories import Subcategory
from .models import AdvSetting
from . import exceptions
from . import api_rights
from .super_cabinet_manager import WBCabinetAccess


logger = logging.getLogger(__name__)


def _try_except_decorator(requests_per_interval, interval_seconds):
    first_request = True
    base_interval = interval_seconds / requests_per_interval
    last_query_time = 0
    current_pause = base_interval

    def decorator(request_func):
        async def wrapper(*args, **kwargs):
            nonlocal last_query_time, current_pause, first_request
            while True:
                current_time = time.time()
                time_since_last_query = current_time - last_query_time
                time_to_wait = max(current_pause - time_since_last_query, 0)
                if not first_request:
                    await asyncio.sleep(time_to_wait)
                else:
                    first_request = False
                try:
                    result = await request_func(*args, **kwargs)
                    last_query_time = time.time()
                    current_pause = (base_interval + current_pause) / 2
                    if current_pause < base_interval:
                        current_pause = base_interval
                    return result
                except exceptions.ApiForbiddenError:
                    raise
                except exceptions.UnknownApiRequestError as e:
                    current_pause *= 2
                    if current_pause > 120:
                        current_pause = 120
                    logger.error(f'Ошибка при запросе к API: {e}, повтор через {current_pause} секунд')
                    await asyncio.sleep(time_to_wait)



        return wrapper

    return decorator






class AdvertApi(ABC_WB_API):

    _rights: set = {api_rights.Rights.PROMOTION}
    _only_read = api_rights.OnlyRead.FALSE
    live_company_status = [4, 9, 11]
    auto_adv_types = [8]


    @_try_except_decorator(2, 1)
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




    @_try_except_decorator(1, 3)
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
    @_try_except_decorator(1, 2)
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

    @_try_except_decorator(1, 1)
    async def get_live_advs(self):
        adv_ids = await self.get_advertIds(self.live_company_status, self.auto_adv_types)
        advs = await self.get_advs(adv_ids)
        return advs


    @_try_except_decorator(1, 6)
    async def set_minus_phrases(self, adv_setting: AdvSetting, phrases: list):
        url = f'https://advert-api.wb.ru/adv/v1/auto/set-excluded?id={adv_setting.adv_id}'
        data = {
            "excluded": phrases
        }

        async with aiohttp.ClientSession() as session:
            await self.requests(session, 'POST', url, json_data=data, headers=self.headers.standart)
            logger.debug('Минус-фразы установлены')

    async def create_adv_company(self, nmids: list, budget_type: int, budget: int) -> Union[Adv, str]:
        """
        0 - balance
        1 - net
        3 - bonus

        """
        assert budget >= 500
        if budget_type == 'balance':
            budget_type = 0
        elif budget_type == 'net':
            budget_type = 1
        elif budget_type == 'bonus':
            budget_type = 3
        cards = await self.get_cards()
        catch_card = None
        for card in cards:
            if card.nmid in nmids:
                catch_card = card
                break
        subjectID = catch_card.subjectID

        url = 'https://advert-api.wb.ru/adv/v1/save-ad'
        data_json = {
            "type": 8,
            "name": ', '.join([str(nmid) for nmid in nmids]),
            "subjectId": subjectID,
            "sum": budget,
            "btype": budget_type,
            "on_pause": True
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data_json, headers=self.headers.standart) as response:
                answer = await response.text()
                if 'error' in answer:
                    error = json.loads(answer)['error']
                    return error
        adv_id = int(answer)  # Это предполагает, что ответ содержит ID рекламной кампании
        company = (await self.get_adv_companies([adv_id]))[0]
        await asyncio.sleep(60)  # Замена sleep на асинхронный asyncio.sleep
        await self.tune_company(company, nmids)
        return company




class ContentApi(ABC_WB_API):
    _only_read = api_rights.OnlyRead.FALSE
    _rights: set = {api_rights.Rights.CONTENT}


    async def get_subcategories(self):
        @_try_except_decorator(1, 1)
        async def request(session, url)-> list[Subcategory]:
            all_categories = []
            response = await self.requests(session, 'GET', url,
                                           headers=self.headers.standart)
            answer = json.loads(response)
            for data in answer['data']:
                subcategory = Subcategory(**data)
                all_categories.append(subcategory)
            return all_categories



        offset = 0
        limit = 1000

        all_categories = []
        async with aiohttp.ClientSession() as session:
            while True:
                url = f'https://suppliers-api.wildberries.ru/content/v2/object/all?offset={offset}&limit={limit}'
                categories = await request(session, url)
                if categories:
                     all_categories.extend(categories)
                if not categories:
                    break
                else:
                    offset = offset + limit

        return all_categories



    async def get_patent_categories(self):
        url = 'https://suppliers-api.wildberries.ru/content/v2/object/parent/all'
        async with aiohttp.ClientSession() as session:
            response_text = await self.requests(session, 'GET', url,
                                                headers=self.headers.standart)
            answer = json.loads(response_text)
            return answer['data']

    @_try_except_decorator(1, 2)
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


class WBApi:
    def __init__(self, wb_access: WBCabinetAccess):
        self.advert = AdvertApi(wb_access)
        self.content = ContentApi(wb_access)
        self._wb_access = wb_access









