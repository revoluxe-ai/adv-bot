import json

import aiohttp

from app.modules.common_slaves.wildberries.api.api import WBApi
from ..interface import InterfaceWBAPI
from ..http_request import try_except_decorator, requests
from ..data_classes import AdvFromWBApi as Adv


class AdvMixin(InterfaceWBAPI):

    @try_except_decorator(1, 2)
    async def get_advs(self, adv_ids: list) -> list[Adv]:
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

