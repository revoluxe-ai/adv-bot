import functools
import json
import logging
import re
import time
from typing import Union

import aiohttp
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor


import asyncio

from exceptions import UnauthorizedError
from python_modules.pause_func import get_pause
from .data_classes.adv import Adv, AdvType, Balances
from .ABC_WB_API import ABC_WB_API
from  .data_classes.card_from_wb import CardFromWB
from .data_classes.interfaces import ShopInterface
from .data_classes.wb_shop import WbShop
from .data_classes  import interfaces


logger = logging.getLogger(__name__)


def async_cache_ttl(seconds: int):
    cache = {}

    def decorator(func):
        @functools.wraps(func)  # И использование wraps для сохранения метаданных функции
        async def wrapper(*args, **kwargs):
            key = (args, frozenset(kwargs.items()))
            if key in cache and time.time() - cache[key]['time'] < seconds:
                return cache[key]['result']

            result = await func(*args, **kwargs)
            cache[key] = {'time': time.time(), 'result': result}
            return result

        return wrapper

    return decorator


class async_WBApi(ABC_WB_API):

    def __init__(self, shop: ShopInterface):
        super().__init__(shop)
        self._folder = 'adv_backup_reports'
        self._wb_stat_backup_file = 'wb_stat_backup_file'

    async def turn_on_only_booster(self, adv):
        url = f'https://advert-api.wb.ru/adv/v1/auto/active?id={adv.advertId}'
        data = {
            "recom": False,
            "booster": True,
            "carousel": False
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=self.headers.standart) as response:
                response_text = await response.text()
                logger.debug(response_text)



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

    async def get_adv_companies(self, adv_ids: list[int]):
        url = 'https://advert-api.wb.ru/adv/v1/promotion/adverts'
        advs = []
        async with aiohttp.ClientSession() as session:
            # Предполагаем, что у вас есть способ сериализации adv_ids в формат, подходящий для вашего запроса # Пример сериализации, уточните в соответствии с API
            async with session.post(url, json=adv_ids,
                                    # data=serialized_data,
                                    headers=self.headers.standart) as response:
                # Убедитесь, что ответ от сервера соответствует ожидаемому формату
                response_data = await response.json()  # предполагается, что API возвращает JSON
                for data in response_data:
                    adv = Adv(data)
                    advs.append(adv)
        return advs

    async def tune_company(self, full_adv: Adv, nmids):
        assert isinstance(full_adv, Adv)
        if set(full_adv.nmids) != set(nmids):
            await self.update_adv_nmids(full_adv, nmids)
        if not all([not full_adv.active.recom,
                    not full_adv.active.carousel,
                    full_adv.active.booster]):
            await self.turn_on_only_booster(full_adv)

    async def update_adv_nmids(self, adv: Adv, need_nmids: list[int]):
        nmids_in_adv = adv.nmids
        nmids_for_del = list(set(nmids_in_adv) - set(need_nmids))
        nmids_for_add = list(set(need_nmids) - set(nmids_in_adv))
        await self.update_nmids_in_adv(adv, nmids_for_add, nmids_for_del)

    async def update_nmids_in_adv(self, adv: Adv, nmids_for_add: list[int], nmids_for_del: list[int]):
        url = f'https://advert-api.wb.ru/adv/v1/auto/updatenm?id={adv.advertId}'
        data = {
            'add': nmids_for_add,
            'delete': nmids_for_del
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=self.headers.standart) as response:
                response_text = await response.text()
                logger.debug(response_text)





    async def _requests(self, session, method, url, data=None, json_data=None, headers=None, ):
        # Передача JSON данных, если они предоставлены
        async with session.request(method, url, data=data, headers=headers, json=json_data) as response:
            return await response.text()


    # @async_cache_ttl(60*30)
    async def get_all_adv_companies(self, queue_for_advs: Union[asyncio.Queue, None] = None,
                                    success_even: Union[asyncio.Event, None] = None,
                                    error_event: Union[asyncio.Event, None] = None)-> list[Adv]:
        MAX_ITER_PER_MINUTE = 300
        url = 'https://advert-api.wb.ru/adv/v1/promotion/adverts'
        adversIds = await self._get_all_advertIds(success_even, error_event)
        advs = []
        pause = get_pause(MAX_ITER_PER_MINUTE)
        for part in self.chunks(adversIds, 50):
            data = json.dumps(part)
            while True:
                try:
                    async with aiohttp.ClientSession() as session:
                        answer = await self._requests(session,'POST', url, data=data,
                                              headers=self.headers.standart)
                        logger.debug('Кампания получена')
                        break
                except Exception as exc:
                    logger.error('Ошибка получения кампаний: %s', exc)
                    await asyncio.sleep(pause)
                    pause *= pause
            answer = json.loads(answer)
            if isinstance(answer, dict):
                if code := answer.get('code', None):
                    if code in [401, 403]:
                        logger.error(f'Доступ к API запрещен')
                        error_event.set()
                        return []

                if error_code := answer.get('code', None):
                    if error_code == 429:
                        logger.error(f'Ошибка получения кампаний: {answer}')
                        pause *= pause
                        continue
            for advert in answer:
                if advert['type'] == 8:
                    adv = Adv(advert)
                    if queue_for_advs:
                        await queue_for_advs.put(adv)
                else:
                    continue
                if adv.status_native == 'done':
                    continue
                advs.append(adv)
        await asyncio.sleep(pause)
        return advs




    async def get_keywords_stat(self, company):
        timer = 5
        url = f'https://advert-api.wb.ru/adv/v2/auto/daily-words?id={company.advertId}'
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    response_text = await self._requests(session, 'GET', url, headers=self.headers.standart)
                    answer = json.loads(response_text)
                    if isinstance(answer, list):
                        return answer
                    elif answer is None:
                        return []
                    else:
                        logger.error('Ошибка получения статистики ключей: %s', answer)
                        await asyncio.sleep(timer)  # Используйте asyncio.sleep для асинхронного ожидания
                        timer *= 2
            except Exception as exc:
                logger.error('Ошибка получения статистики ключей: %s', exc)
                await asyncio.sleep(timer)
                timer *= 2






    @async_cache_ttl(60*60*3)
    async def get_cards(self, success_event:asyncio.Event = None,
                        error_event: asyncio.Event = None ) -> list[CardFromWB]:
        limit = 1000
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

        cards = []
        total = float('inf')
        async with aiohttp.ClientSession() as session:
            while total >= limit:
                response = None  # Инициализация переменной перед блоком try
                try:
                    response = await session.post(url, json=data_for_req, headers=self.headers.standart)
                    response.raise_for_status()
                    answer = await response.json()
                    logger.debug(f"Карточки получены, всего {len(answer['cards'])}")
                    success_event.set()
                except Exception as exc:
                    logger.error(f'Ошибка получения карточек: {exc}, {self.shop.name}')
                    if response.status == 403:
                        error_event.set()
                        logger.error(f'Ошибка авторизации: {exc}, {self.shop.name}')
                        return []
                    if response is None or response.status == 500:  # Теперь это условие безопасно для проверки
                        logger.error('Временно возврат только полученных карт! Переделать!')
                        return cards
                    await asyncio.sleep(10)
                    continue

                data_for_cards = answer['cards']
                for data in data_for_cards:
                    card = CardFromWB(data)
                    # if card.brand == self.shop.brand:
                    cards.append(card)

                cursor = answer['cursor']
                total = cursor['total']
                del cursor['total']
                data_for_req['settings']['cursor'] = cursor
                data_for_req['settings']['cursor']['limit'] = limit

                nmids = list(set([card.nmid for card in cards]))
                logger.debug(f'Всего уникальных карточек: {len(nmids)}')
        return cards



    async def set_minus_phrases(self, adv: Adv, phrases: list):
        url = f'https://advert-api.wb.ru/adv/v1/auto/set-excluded?id={adv.advertId}'
        timer = 5
        data = {
            "excluded": phrases
        }

        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    response = await session.post(url, json=data, headers=self.headers.standart)
                    response.raise_for_status()  # Генерирует исключение для ответов с ошибкой
                    logger.debug('Минус-фразы установлены')
                    break
                except aiohttp.ClientError as e:
                    logger.error(f'РК {adv.name} Ошибка установки минус-фраз: {e}')
                    await asyncio.sleep(timer)  # Асинхронная задержка перед следующей попыткой
                    timer *= 2  # Увеличиваем таймер вдвое для экспоненциального отката

    async def get_adv_balances(self):
        url = 'https://advert-api.wb.ru/adv/v1/balance'
        async with aiohttp.ClientSession() as session:
            response = await session.get(url, headers=self.headers.standart)
            answer = await response.json()
            balance = Balances(answer)
            return balance

    async def cards_to_queue(self, queue_for_adv:asyncio.Queue,
                             queue_for_cards:asyncio.Queue,
                             success_event: asyncio.Event, error_event: asyncio.Event):
        while True:
            adv = await queue_for_adv.get()
            if adv is None:
                queue_for_adv.task_done()
                break
            else:
                nmids = adv.nmids
                try:
                    cards = await self.get_cards_by_text(nmids)
                    success_event.set()
                    for card in cards:
                        await queue_for_cards.put(card)
                    queue_for_adv.task_done()
                except UnauthorizedError:
                    error_event.set()
                    return

