import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientResponseError

from ...common_slaves.wildberries.ABC_WB_API import Headers
from ...common_slaves.wildberries.models import WBToken
from ...common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from .wb_api import WBApi as BidderAPI


@pytest.fixture
def client_session_mock():
    session = AsyncMock()
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
async def test_update_with_wrong_cpm_run(client_session_mock):
    access_mock = AsyncMock(spec=WBCabinetAccess)

    wb_token_mock = MagicMock(spec=WBToken)
    wb_token_mock.categories = MagicMock(return_value="Тестовая категория")
    access_mock.tokens = [wb_token_mock]

    wb_cabinet_mock = MagicMock()
    wb_cabinet_mock.shop_id = "test_shop_id"
    access_mock.wb_cabinet = wb_cabinet_mock

    bidder_api = BidderAPI(wb_access=access_mock, client_session=client_session_mock)

    headers_mock = MagicMock(spec=Headers)
    headers_mock.api_key = {"Authorization": "test_api_key"}
    bidder_api.headers = headers_mock

    # Создаем мок для ответа
    response_mock = AsyncMock()
    response_mock.status = 400
    response_mock.text = AsyncMock(return_value=get_test_response_for_min_bid_error(150, 200))
    response_mock.raise_for_status = MagicMock(
        side_effect=ClientResponseError(
            request_info=None,  # type: ignore
            history=(None,),  # type: ignore
            status=400,
            message="Bad request",
        )
    )

    # Создаем контекстный менеджер для ответа
    context_manager_mock = AsyncMock()
    context_manager_mock.__aenter__ = AsyncMock(return_value=response_mock)
    context_manager_mock.__aexit__ = AsyncMock(return_value=None)

    # Настраиваем мок для request
    client_session_mock.request = AsyncMock(return_value=context_manager_mock)

    await bidder_api.update_cpm(adv_id=123456789, nmid=123456789, new_bid=150)

    client_session_mock.request.assert_called_once_with(
        "POST",
        "https://advert-api.wb.ru/adv/v0/cpm",
        json={
            "advert_id": 123456789,
            "type": 8,
            "cpm": 150,
            "param": str(123456789),
        },
        headers={"Authorization": "test_api_key"},
    )
