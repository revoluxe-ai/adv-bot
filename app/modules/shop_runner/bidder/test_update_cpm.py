import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientResponseError

from ...common_slaves.wildberries.ABC_WB_API import Headers
from ...common_slaves.wildberries.models import WBToken
from ...common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from .wb_api import WBApi as BidderAPI


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
async def test_update_with_wrong_cpm_run():
    access_mock = AsyncMock(spec=WBCabinetAccess)

    wb_token_mock = MagicMock(spec=WBToken)
    wb_token_mock.categories = MagicMock(return_value="Тестовая категория")
    access_mock.tokens = [wb_token_mock]

    bidder_api = BidderAPI(wb_access=access_mock)

    headers_mock = MagicMock(spec=Headers)
    headers_mock.api_key = {"Authorization": "test_api_key"}
    bidder_api.headers = headers_mock

    # Тут важная часть: side_effect для session.request
    def request_side_effect(method, url, *, json=None, headers=None, **kwargs):
        response_mock = MagicMock()
        bid = int(json["bids"][0]["nm_bids"][0]["bid"])
        if bid < 200:
            # ответ от API с ошибкой
            response_mock.status = 400
            response_mock.text = AsyncMock(
                return_value=get_test_response_for_min_bid_error(bid, 200)
            )
            # raise_for_status вызовет get_error_from_response(...) → MinAdvBidWBApiError
            response_mock.raise_for_status = MagicMock(
                side_effect=ClientResponseError(
                    request_info=None,  # type: ignore
                    history=(None,),  # type: ignore
                    status=400,
                    message="Bad request",
                )
            )
        elif bid == 200:
            # успешный ответ
            response_mock.status = 200
            response_mock.text = AsyncMock(return_value="OK")
            response_mock.raise_for_status = MagicMock()
        request_cm = MagicMock()
        request_cm.__aenter__ = AsyncMock(return_value=response_mock)
        request_cm.__aexit__ = AsyncMock(return_value=None)
        return request_cm

    # Мокаем сессию и ClientSession
    session_mock = MagicMock()
    session_mock.request = MagicMock(side_effect=request_side_effect)

    client_session_cm = MagicMock()
    client_session_cm.__aenter__ = AsyncMock(return_value=session_mock)
    client_session_cm.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession", return_value=client_session_cm):
        await bidder_api.update_cpm(adv_id=123456789, nmid=123456789, new_bid=150)

        assert session_mock.request.call_count == 2
