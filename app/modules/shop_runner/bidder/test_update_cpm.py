import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import ClientResponseError

from ...common_slaves.wildberries.ABC_WB_API import Headers
from ...common_slaves.wildberries.models import WBToken
from ...common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from .wb_api import WBApi as BidderAPI


@pytest.fixture
def client_session_mock():
    session = MagicMock()
    session.close = MagicMock()
    return session


def get_test_response_for_min_bid_error(wrong_bid: int, min_bid: int) -> str:
    return json.dumps(
        {
            "errors": [
                {
                    "detail": f"wrong bid value: {wrong_bid}; min: {min_bid} max:100000",
                    "field": ".bids[0].nm_bids[0].bid",
                }
            ],
            "request_id": "1ad31485d3aa2b8c1bb274475388439b",
            "status": 400,
            "title": "invalid payload",
            "type": "Bad Request",
        }
    )


@pytest.mark.asyncio
async def test_update_with_wrong_cpm_run(client_session_mock): # pyright: ignore
    access_mock = AsyncMock(spec=WBCabinetAccess)

    wb_token_mock = MagicMock(spec=WBToken)
    wb_token_mock.categories = MagicMock(return_value="Тестовая категория")
    access_mock.tokens = [wb_token_mock]

    wb_cabinet_mock = MagicMock()
    wb_cabinet_mock.shop_id = "test_shop_id"
    access_mock.wb_cabinet = wb_cabinet_mock

    bidder_api = BidderAPI(wb_access=access_mock, client_session=client_session_mock) # pyright: ignore

    headers_mock = MagicMock(spec=Headers)
    # code expects headers.standart to be a dict of headers
    headers_mock.standart = {"Authorization": "test_api_key"}
    bidder_api.headers = headers_mock

    # Создаем мок для ответа
    response_mock = AsyncMock()
    response_mock.status = 400
    response_mock.text = AsyncMock(
        return_value=get_test_response_for_min_bid_error(150, 200)
    )
    response_mock.raise_for_status = MagicMock(
        side_effect=ClientResponseError(
            request_info=None,  # type: ignore
            history=(None,),  # type: ignore
            status=400,
            message="Bad request",
        )
    )

    # Создаем контекстный менеджер для ошибочного ответа (первая попытка)
    cm_err = AsyncMock()
    cm_err.__aenter__.return_value = response_mock
    cm_err.__aexit__.return_value = None

    # Создаем контекстный менеджер для успешного ответа (вторая попытка)
    response_ok = AsyncMock()
    response_ok.status = 200
    response_ok.text = AsyncMock(return_value="")
    response_ok.raise_for_status = MagicMock()

    cm_ok = AsyncMock()
    cm_ok.__aenter__.return_value = response_ok
    cm_ok.__aexit__.return_value = None

    # Настраиваем мок для request: сначала возвращаем ошибочный контекст, затем успешный
    client_session_mock.request.side_effect = [cm_err, cm_ok] # pyright: ignore

    await bidder_api.update_cpm(adv_id=123456789, nmid=123456789, new_bid=150)

    # Проверяем, что request был вызван и проверяем параметры запроса (игнорируем дополнительные kwargs)
    assert client_session_mock.request.call_count >= 1 # pyright: ignore
    _args, _kwargs = client_session_mock.request.call_args # pyright: ignore
    assert _args[0] == "PATCH"
    assert _args[1] == "https://advert-api.wildberries.ru/adv/v0/bids"
    assert _kwargs.get("json") == { # pyright: ignore
        "bids": [
            {
                "advert_id": 123456789,
                "nm_bids": [{"nm": 123456789, "bid": 200}],
            }
        ]
    }
    assert _kwargs.get("headers") == {"Authorization": "test_api_key"} # pyright: ignore
