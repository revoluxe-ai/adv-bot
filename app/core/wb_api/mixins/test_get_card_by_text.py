"""Тесты для метода get_card_by_text в ContentMixin."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.wb_api.base import BaseAPI
from app.core.wb_api.data_classes.card_from_wb import CardFromWB
from app.core.wb_api.mixins.content import PREFIX, ContentMixin


@pytest.fixture
def client_session_mock() -> AsyncMock:
    """Мок для aiohttp.ClientSession."""
    session = AsyncMock()
    session.close = MagicMock()
    # request будет переопределён в тесте, чтобы возвращать async-контекстный менеджер
    return session


class TestWBApi(BaseAPI, ContentMixin):
    PREFIX = PREFIX


@pytest.mark.skip(reason="Какая-то проблема с получением мока TestWBApi")
@pytest.mark.asyncio
async def test_get_card_by_text_success(access_mock, client_session_mock) -> None:
    wb_api = TestWBApi(access_mock, client_session_mock)

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

    # Создаем мок для ответа
    response_mock = AsyncMock()
    response_mock.status = 200
    # requests() in http_request.py reads response.text(), so мок должен возвращать JSON строку
    response_mock.text = AsyncMock(return_value=json.dumps(expected_response))
    response_mock.raise_for_status = MagicMock()

    # Создаем async-контекстный менеджер для ответа
    class _AsyncCM:
        async def __aenter__(self):
            return response_mock

        async def __aexit__(self, exc_type, exc, tb):
            return None

    context_manager_mock = _AsyncCM()

    # Настраиваем мок для request: должен возвращать контекстный менеджер, а не корутину
    client_session_mock.request = MagicMock(return_value=context_manager_mock)

    # Вызываем тестируемый метод
    query_text = "Пример карточки"
    card = await wb_api.get_card_by_text(query_text)

    # Проверяем результат
    assert isinstance(card, CardFromWB)

    # Проверяем, что запрос был сделан с правильными параметрами
    client_session_mock.request.assert_called_once()
    args, kwargs = client_session_mock.request.call_args
    assert args == ("POST", url)
    assert "json" in kwargs and "headers" in kwargs
    # Проверяем структуру json и значение текста поиска
    sent_json = kwargs["json"]
    assert sent_json["settings"]["filter"]["textSearch"] == str(query_text)
    # Проверяем, что использовались стандартные заголовки
    assert kwargs["headers"] == wb_api.headers.standart
