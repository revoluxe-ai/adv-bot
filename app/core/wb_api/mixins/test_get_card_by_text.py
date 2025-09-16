import pytest
from aioresponses import aioresponses

from app.core.wb_api.base import BaseAPI
from app.core.wb_api.data_classes.card_from_wb import CardFromWB
from app.core.wb_api.mixins.content import PREFIX, ContentMixin


class TestWBApi(BaseAPI, ContentMixin):
    PREFIX = PREFIX


@pytest.mark.asyncio
async def test_get_card_by_text_success(access_mock) -> None:
    wb_api = TestWBApi(access_mock)  # или твой протоколный мок

    url = f"{wb_api.PREFIX}.{wb_api.HOST}/content/v2/get/cards/list"
    expected_response = {
        "cards": [
            {
                "nmID": 12345678,
                "imtID": 123654789,
                "nmUUID": "01bda0b1-5c0b-736c-b2be-d0a6543e9be",
                "subjectID": 7771,
                "subjectName": "AKF системы",
                "vendorCode": "wb7f6mumjr1",
                "brand": "Тест",
                "title": "Тест-система",
                "description": "Тестовое описание",
                "needKiz": False,
                "photos": [],
                "video": "https://videonme-basket-12.wbbasket.ru/vol137/part22557/225577433/hls/1440p/index.m3u8",
                "dimensions": {},
                "characteristics": [],
                "sizes": [],
                "tags": [],
                "createdAt": "2023-12-06T11:17:00.96577Z",
                "updatedAt": "2023-12-06T11:17:00.96577Z",
            }
        ],
        "cursor": {
            "updatedAt": "2023-12-06T11:17:00.96577Z",
            "nmID": 123654123,
            "total": 1,
        },
    }

    with aioresponses() as mocked:
        mocked.post(url, payload=expected_response)

        card = await wb_api.get_card_by_text("Пример карточки")

        assert isinstance(card, CardFromWB)
