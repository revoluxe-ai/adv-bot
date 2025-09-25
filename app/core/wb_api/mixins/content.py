"""Миксин для работы с карточками товаров через Content API Wildberries. Legacy, в разработке новый модуль"""

import json
import logging
from typing import Any, cast

from app.modules.common_slaves.wildberries.data_classes.card_from_wb import CardFromWB
from app.core.wb_api.http_request import requests, try_except_decorator
from app.core.wb_api.mixins.excs import CardNotFoundInWB
from app.core.wb_api.protocols import WBAPIProtocol

logger = logging.getLogger(__name__)


PREFIX = "https://content-api"


class ContentMixin(WBAPIProtocol):
    HOST = "wildberries.ru"

    @try_except_decorator(1, 60)
    async def get_card_by_text(self, query_text: str | int) -> CardFromWB:
        url = f"{PREFIX}.{self.HOST}/content/v2/get/cards/list"

        data = {
            "settings": {
                "filter": {"textSearch": str(query_text)},
                "cursor": {"limit": 1},
            }
        }

        response_text = await requests(
            self.session,
            "POST",
            url,
            json_data=data,
            headers=self.headers.standart,
        )
        answer = json.loads(response_text)
        card_data = answer["cards"][0]
        return CardFromWB(card_data)

    @try_except_decorator(1, 60)
    async def get_card_by_nm_id(self, nm_id: int) -> CardFromWB:
        url = f"{PREFIX}.{self.HOST}/content/v2/get/cards/list"

        data = {
            "settings": {
                "filter": {"textSearch": str(nm_id)},
                "cursor": {"limit": 1},
            }
        }

        response_text = await requests(
            self.session,
            "POST",
            url,
            json_data=data,
            headers=self.headers.standart,
        )
        answer = json.loads(response_text)
        card_data = answer["cards"][0]
        return CardFromWB(card_data)

    @try_except_decorator(1, 60)
    async def get_card_by_imt_id(self, imt_id: int) -> CardFromWB:
        url = f"{PREFIX}.{self.HOST}/content/v2/get/cards/list"

        data = {
            "settings": {
                "filter": {"imtID": imt_id},
                "cursor": {"limit": 1},
            }
        }

        response_text = await requests(
            self.session,
            "POST",
            url,
            json_data=data,
            headers=self.headers.standart,
        )
        answer = json.loads(response_text)
        card_data = answer["cards"][0]
        return CardFromWB(card_data)
