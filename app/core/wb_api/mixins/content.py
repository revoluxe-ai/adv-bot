import asyncio
import json
import logging
from typing import Union

import aiohttp

from app.core.wb_api.data_classes.card_from_wb import CardFromWB
from app.core.wb_api.http_request import try_except_decorator, requests
from app.core.wb_api.interface import InterfaceWBAPI
from app.core.wb_api.mixins.excs import CardNotFoundInWB


logger = logging

class ContentMixin(InterfaceWBAPI):

    HOST = 'https://content-api.wildberries.ru'

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
        url = f'{self.HOST}/content/v2/get/cards/list'
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

    @try_except_decorator(1, 2)
    async def get_all_cards(self, text: Union[str, int])-> list[CardFromWB]:
        url = f'{self.HOST}/content/v2/get/cards/list'
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
        data_cards = answer['cards']
        all_cards = []
        for card_json in data_cards:
            card = CardFromWB(card_json)
            all_cards.append(card)
        return all_cards

    @try_except_decorator(1, 2)
    async def get_all_cards(self):
        url = f'{self.HOST}/content/v2/get/cards/list'

        # Начальные параметры для запроса
        data_for_req = {
            "settings": {
                "cursor": {
                    "limit": 100
                },
                "filter": {
                    "withPhoto": -1
                }
            }
        }

        all_cards = []  # Список для хранения всех карточек

        async with aiohttp.ClientSession() as session:
            while True:
                response = await requests(session, 'POST', url=url,
                                          json_data=data_for_req,
                                          headers=self.headers.standart)
                answer = json.loads(response)

                # Проверяем наличие ключа 'cards' в ответе
                cards_data = answer.get('cards', [])
                if not cards_data:
                    break

                # Добавляем карточки в общий список
                all_cards.extend([CardFromWB(card_json) for card_json in cards_data])

                # Проверяем, есть ли еще данные для пагинации
                if len(cards_data) < data_for_req['settings']['cursor']['limit']:
                    break

                # Обновляем курсор для следующего запроса
                last_card = cards_data[-1]
                data_for_req['settings']['cursor'].update({
                    "updatedAt": last_card.get("updatedAt"),
                    "nmID": last_card.get("nmID")
                })

        return all_cards
