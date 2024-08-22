from .data_classes.card_from_wb import CardFromWB
import asyncio
import datetime
import json
import logging
import time
from typing import Union
from aiohttp import ClientOSError, ServerDisconnectedError
import aiohttp
from .ABC_WB_API import ABC_WB_API
from .data_classes.adv import Adv
import json
from .data_classes.keywordstat import KeywordStat
from .data_classes.subcategories import Subcategory
from .exceptions import CardNotFoundInWB
from .http_request import requests, try_except_decorator
from .models import AdvSetting
from . import api_rights
from .super_cabinet_manager import WBCabinetAccess
import time

logger = logging.getLogger(__name__)



def escape_special_characters(text):
    text = text.replace('"', '\\"')  # Экранирование двойных кавычек
    text = text.replace("'", "\\'")  # Экранирование одинарных кавычек
    text = text.replace("\t", "\\t") # Экранирование табуляции
    text = text.replace("\n", "\\n") # Экранирование новой строки
    return text


class AdvertApi(ABC_WB_API):

    _rights: set = {api_rights.Rights.PROMOTION}
    _only_read = api_rights.OnlyRead.FALSE
    live_company_status = [4, 9, 11]
    auto_adv_types = [8, 9]


    @try_except_decorator(2, 1)
    async def get_keywords_stat(self, adv_setting: AdvSetting)-> list[KeywordStat]:
        keywords = []
        url = f'https://advert-api.wb.ru/adv/v2/auto/daily-words?id={adv_setting.adv_id}'
        async with aiohttp.ClientSession() as session:
            response_text = await requests(session, 'GET', url,
                                                headers=self.headers.standart)

            response_text = escape_special_characters(response_text)
            answer = json.loads(response_text)
            update_timestamp = datetime.datetime.now()
            if not answer:
                logger.debug('Нет данных по ключевым словам: %s', adv_setting.name)
                return  []
            for data in answer:
                wb_timestamp = datetime.datetime.fromisoformat(data['date']).date()
                stat = data['stat']
                for keyword_stat in stat:
                    keyword_text = keyword_stat.pop('keyword')
                    keyword_text = keyword_text.replace(r'"', '')
                    keyword_text = keyword_text.replace('_', '')
                    keyword_stat['date'] = wb_timestamp
                    keyword_stat['update_timestamp'] = update_timestamp
                    keyword_stat['adv_id'] = adv_setting.adv_id
                    keyword_stat['text'] = keyword_text
                    keyword_stat['spend'] = keyword_stat.pop('sum')
                    keyword = KeywordStat(**keyword_stat)
                    keywords.append(keyword)
        keywords.sort(key=lambda x: x.date)
        return keywords

    @try_except_decorator(1, 1)
    async def update_cpm(self, adv_id, new_cpm):
        url = 'https://advert-api.wildberries.ru/adv/v0/cpm'
        data = {
            "advertId": adv_id,
            "type": 8,
            "cpm": int(new_cpm),
            # "param": None
        }
        async with aiohttp.ClientSession() as session:
            response_text = await requests(session,
                                              'POST',
                                                url,
                                                json_data=data,
                                                headers=self.headers.standart)

            assert response_text == ''
            pass


    @try_except_decorator(1, 3)
    async def get_advertIds(self) -> list[int]:
        advertIds = []
        url = 'https://advert-api.wb.ru/adv/v1/promotion/count'
        async with aiohttp.ClientSession() as session:
            response_text = await requests(session, 'GET', url,
                                                headers=self.headers.standart)
            answer = json.loads(response_text)
            # Используем json.loads для преобразования текста ответа в JSON
            adverts:list = answer['adverts']
            if not adverts:
                return []
            for advert in adverts:
                if advert['type'] == 8:
                    for advert in advert['advert_list']:
                        advertId = advert['advertId']
                        advertIds.append(advertId)

        return advertIds
    @try_except_decorator(1, 2)
    async def _get_advs(self, adv_ids: list)->list[Adv]:
        advs = []
        url = f'https://advert-api.wb.ru/adv/v1/promotion/adverts'
        async with aiohttp.ClientSession() as session:
            response_text = await requests(session, 'POST', url, json_data=adv_ids,
                                                headers=self.headers.standart)
            answer = json.loads(response_text)
            for advert in answer:
                adv = Adv(advert)
                advs.append(adv)
        return advs

    @try_except_decorator(1, 1)
    async def get_advs(self, adv_ids: list[int] = None) -> list[Adv]:
        if not adv_ids:
            adv_ids: list[int] = await self.get_advertIds()
        all_advs = []
        part = 50
        for i in range(0, len(adv_ids), part):
            part_of_advs = adv_ids[i:i + part]
            advs = await self._get_advs(part_of_advs)
            all_advs.extend(advs)
        return all_advs


    @try_except_decorator(1, 6)
    async def set_minus_phrases(self, adv_setting: AdvSetting, phrases: list):
        if len(phrases) > 1000:
            phrases.sort(key=lambda x: len(x), reverse=True)
            phrases = phrases[:1000]
            logger.debug('Больше 1000 минус-фраз, обрезаем до 1000')
        url = f'https://advert-api.wb.ru/adv/v1/auto/set-excluded?id={adv_setting.adv_id}'
        data = {
            "excluded": phrases
        }

        async with aiohttp.ClientSession() as session:
            await requests(session, 'POST', url, json_data=data, headers=self.headers.standart)
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

    @try_except_decorator(1, 1)
    async def pause_company(self, adv_id: int):
        url = f'https://advert-api.wb.ru/adv/v0/pause?id={adv_id}'
        async with aiohttp.ClientSession() as session:
            try:
                await requests(session, 'GET',
                                url,
                                headers=self.headers.standart)
                logger.debug(f'Рекламная кампания {adv_id} успешно поставлена на паузу')
            except:
                raise
        return


class ContentApi(ABC_WB_API):
    _only_read = api_rights.OnlyRead.FALSE
    _rights: set = {api_rights.Rights.CONTENT}


    async def get_subcategories(self):
        @try_except_decorator(1, 1)
        async def request(session, url)-> list[Subcategory]:
            all_categories = []
            response = await requests(session, 'GET', url,
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
            response_text = await requests(session, 'GET', url,
                                                headers=self.headers.standart)
            answer = json.loads(response_text)
            return answer['data']

    async def get_cards_by_text(self, texts):
        cards = []
        for text in texts:
            try:
                cards.append(await self.get_card_by_text(text))
            except CardNotFoundInWB:
                logger.debug('Карточка с текстом %s не найдена на Wildberries, возможно, карточка не существует',
                             text)
                continue
            await asyncio.sleep(0)
        return cards


    @try_except_decorator(1, 2)
    async def get_card_by_text(self, text: Union[str, int]):
        url = 'https://suppliers-api.wildberries.ru/content/v2/get/cards/list'
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
                    'textSearch': str(text)

                }
            }
        }

        async with aiohttp.ClientSession() as session:
            response = await requests(session, 'POST', url=url,
                                               json_data=data_for_req,
                                               headers=self.headers.standart)
            answer = json.loads(response)
        cards = answer['cards']
        if not cards:
            raise CardNotFoundInWB(f'Карточка с текстом {text} не найдена на Wildberries')
        card_json = answer['cards'][0]
        card = CardFromWB(card_json)
        return card


    async def get_product_list(
        self,
        updated_at: str | None = None,
        nm_id: int | None = None,
    ) -> dict:
        """Возвращает список товаров на Wildberries. """

        url = 'https://suppliers-api.wildberries.ru/content/v2/get/cards/list'

        limit = 100

        data = json.dumps({
            'settings': {
                'cursor': {
                    'limit': limit,
                    'updatedAt': updated_at,
                    'nmID': nm_id,
                },
                'filter': {
                    'withPhoto': -1,
                    # 'textSearch': str(nm_id),

                },
            },
        })
        async with aiohttp.ClientSession() as session:
            response = await requests(session, 'POST', url=url, data=data, headers=self.headers.standart)
            return json.loads(response)



class WBApi:
    def __init__(self, wb_access: WBCabinetAccess):
        self.advert = AdvertApi(wb_access)
        self.content = ContentApi(wb_access)
        self.wb_access = wb_access
