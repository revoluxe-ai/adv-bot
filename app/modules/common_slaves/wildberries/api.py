import asyncio
import datetime
import json
import logging
import time
from typing import Union

from aiohttp import ClientOSError, ServerDisconnectedError

from app.exc import CardNotFoundInDB
from app.modules.common_slaves.wildberries import exceptions
import aiohttp

from . import api_rights
from .ABC_WB_API import ABC_WB_API
from .data_classes.adv import Adv
from .data_classes.card_from_wb import CardFromWB
from .data_classes.keywordstat import KeywordStat
from .data_classes.subcategories import Subcategory
from .exceptions import (ApiForbiddenError,
                         TooManyRequests,
                         UnknownApiRequestError,
                         BadRequestError,
                         NotValidDataError,
                         CardNotFoundInWB)
from .models import AdvSetting
from .super_cabinet_manager import WBCabinetAccess

logger = logging.getLogger(__name__)


def try_except_decorator(requests_per_interval, interval_seconds, max_attempts=50, max_delay=120):
    def decorator(func):
        async def wrapper(instance, *args, **kwargs):
            if not hasattr(instance, '_api_call_state'):
                instance._api_call_state = {}

            method_name = func.__name__
            if method_name not in instance._api_call_state:
                instance._api_call_state[method_name] = {
                    '_last_query_time': 0,
                    '_current_pause': interval_seconds / requests_per_interval,
                    '_attempts': 0,
                     '_first_request': True
                }

            state = instance._api_call_state[method_name]
            while state['_attempts'] < max_attempts:
                current_time = time.time()
                time_since_last_query = current_time - state['_last_query_time']
                time_to_wait = max(state['_current_pause'] - time_since_last_query, 0)
                if not state['_first_request']:
                    logger.debug(f'Пауза между запросами: {time_to_wait} секунд')
                    await asyncio.sleep(time_to_wait)
                state['_first_request'] = False

                try:
                    result = await func(instance, *args, **kwargs)
                    state['_last_query_time'] = time.time()
                    state['_current_pause'] = (interval_seconds / requests_per_interval + state['_current_pause']) / 2
                    state['_attempts'] = 0  # Сброс попыток после успешного выполнения
                    return result
                except ApiForbiddenError:
                    instance.set_next_token()
                except (TooManyRequests,
                        UnknownApiRequestError,
                        BadRequestError,
                        NotValidDataError,
                        ClientOSError,
                        ServerDisconnectedError) as e:
                    state['_attempts'] += 1
                    state['_current_pause'] = min(state['_current_pause'] * 2, max_delay)
                    if state['_attempts'] >= max_attempts:
                        raise e
        return wrapper
    return decorator



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
            response_text = await self.requests(session, 'GET', url,
                                                headers=self.headers.standart)
            answer = json.loads(response_text)
            update_timestamp = datetime.datetime.now()
            if not answer:
                logger.debug('Нет данных по ключевым словам: %s', adv_setting.name)
                return  []
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

    @try_except_decorator(1, 3)
    async def get_advertIds(self) -> list[int]:
        advertIds = []
        url = 'https://advert-api.wb.ru/adv/v1/promotion/count'
        async with aiohttp.ClientSession() as session:
            response_text = await self.requests(session, 'GET', url,
                                                headers=self.headers.standart)
            answer = json.loads(response_text)
            # Используем json.loads для преобразования текста ответа в JSON
            adverts: list = answer['adverts']
            if not adverts:
                return []
            for advert in adverts:
                if advert['type'] == 8:
                    for advert in advert['advert_list']:
                        advertId = advert['advertId']
                        advertIds.append(advertId)

        return advertIds



    async def get_advs(self, adv_ids: list[int]) -> list[Adv]:
        advs = []
        for chunk in self.chunks(adv_ids, 50):
            advs.extend(await self._get_advs(chunk))
        return advs


    @try_except_decorator(1, 2)
    async def _get_advs(self, adv_ids: list)->list[Adv]:
        advs = []
        url = f'https://advert-api.wb.ru/adv/v1/promotion/adverts'
        async with aiohttp.ClientSession() as session:
            response_text = await self.requests(session, 'POST', url, json_data=adv_ids,
                                                headers=self.headers.standart)
            answer = json.loads(response_text)
            for advert in answer:
                adv = Adv(advert)
                # if not adv.nmids:
                #     raise exceptions.NotValidDataError('Нет данных об карточках в РК')
                advs.append(adv)
        return advs

    @try_except_decorator(1, 1)
    async def get_live_advs(self):
        adv_ids: list[int] = await self.get_advertIds()
        advs = await self.get_advs(adv_ids)
        return advs


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

    @try_except_decorator(1, 1)
    async def pause_company(self, adv_id: int):
        url = f'https://advert-api.wb.ru/adv/v0/pause?id={adv_id}'
        async with aiohttp.ClientSession() as session:
            try:
                await self.requests(session, 'GET',
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

    async def get_cards_by_text(self, texts):
        cards = []
        for text in texts:
            try:
                cards.append(await self._get_cards_by_text(text))
            except CardNotFoundInWB:
                logger.debug('Карточка с текстом %s не найдена на Wildberries, возможно, карточка не существует',
                             text)
                continue
        return cards


    @try_except_decorator(1, 2)
    async def _get_cards_by_text(self, text: Union[str, int]):
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
            response = await self.requests(session, 'POST', url=url,
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
            response = await self.requests(session, 'POST', url=url, data=data, headers=self.headers.standart)
            return json.loads(response)
        # return self.request('POST', '/content/v2/get/cards/list', data=data)


    # async def get_uploaded_products(
    #     self,
    #     updated_at: str | None = None,
    #     nm_id: int | None = None,
    # ) -> dict:
    #     """Возвращает словарь выгруженных товаров на Wildberries. """
    #
    #     limit = 100
    #
    #     product_info = await self.get_product_list(updated_at, nm_id)
    #     uploaded_products = product_info['cards']
    #
    #     cursor = product_info['cursor']
    #     if cursor['total'] >= limit:
    #         uploaded_products.update(
    #             await self.get_uploaded_products(cursor['updatedAt'], cursor['nmID']),
    #         )
    #
    #     return uploaded_products


class WBApi:
    def __init__(self, wb_access: WBCabinetAccess):
        self.advert = AdvertApi(wb_access)
        self.content = ContentApi(wb_access)
        self._wb_access = wb_access
