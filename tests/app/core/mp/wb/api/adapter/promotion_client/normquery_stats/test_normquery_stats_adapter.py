import pytest
from unittest.mock import AsyncMock, patch
from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.adapter import NormqueryStatsAdapter
from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.command import GetNormqueryStatsCommand
from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.dto import NormqueryStatsDTO
from app.core.mp.wb.api.generated.promotion.marketing_and_promotions_client.models import (
    V0GetNormQueryStatsRequest,
    V0GetNormQueryStatsResponse,
    V0GetNormQueryStatsItem,
    V0GetNormQueryStatsItemStat,
    V0GetNormQueryStatsRequestItemsItem,
)
import datetime
from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
from app.core.mp.wb.api.request_limit_manager import RequestLimitManager
from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.raw_response_to_dto import raw_response_to_dto
from app.core.mp.wb.api.retry_decorator import retry_decorator
from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors


@pytest.fixture
def mock_auth_client_handler():
    return AsyncMock()


@pytest.fixture
def mock_request_limit_manager():
    mock = AsyncMock(spec=RequestLimitManager)
    mock.api_call_state = {}
    return mock


@pytest.fixture
def normquery_stats_adapter(
    mock_auth_client_handler, mock_request_limit_manager
):
    adapter = NormqueryStatsAdapter(
        base_url="http://test_url",
        auth_client_handler=mock_auth_client_handler,
        request_limit_manager=mock_request_limit_manager,
    )
    return adapter


@pytest.mark.asyncio
async def test_get_adv_v0_normquery_stats(normquery_stats_adapter,
                                          mock_auth_client_handler,
                                          complex_adv):
    today = datetime.date.today()
    command = GetNormqueryStatsCommand(complex_advs=[complex_adv], date_from=today,
                                       date_to=today)
    #
    # stat_mock = V0GetNormQueryStatsItemStat(
    #     norm_query='phrase1',
    #     clicks=10,
    #     orders=2,
    #     atbs=5,
    #     ctr=0.5,
    #     cpm=5.0,
    # )
    # mock_stats_item = V0GetNormQueryStatsItem(advert_id=123, nm_id=456, stats=[stat_mock])
    mock_client = AsyncMock()
    mock_auth_client_handler.get_proxy_client = AsyncMock(return_value=mock_client)

    mock_stats_item = V0GetNormQueryStatsItemStat(
        norm_query="phrase1",
        views=100,
        clicks=10,
        ctr=10.0,
        cpm=5.0,
        atbs=5,
        orders=2,
        cpc=0.5,
        avg_pos=3.0,
    )
    mock_response_item = V0GetNormQueryStatsItem(
        advert_id=123,
        nm_id=456,
        stats=[mock_stats_item],
    )
    mock_response_parsed = V0GetNormQueryStatsResponse(
        stats=[mock_response_item],
    )

    with patch(
        "app.core.mp.wb.api.adapter.promotion_client.normquery_stats.adapter.asyncio_detailed",
        new_callable=AsyncMock,
    ) as mock_asyncio_detailed:
        mock_response_from_api = AsyncMock(parsed=mock_response_parsed, status_code=200)
        mock_asyncio_detailed.return_value = mock_response_from_api

        result = await normquery_stats_adapter.get_adv_v0_normquery_stats(command)

        mock_auth_client_handler.get_proxy_client.assert_awaited_once_with(
            normquery_stats_adapter
        )
        mock_asyncio_detailed.assert_awaited_once_with(
            client=mock_client,
            body=V0GetNormQueryStatsRequest(
                from_=today,
                to=today,
                items=[V0GetNormQueryStatsRequestItemsItem(advert_id=123, nm_id=456)]
            ),
        )

        assert len(result) == 1
        assert result[0].adv_id == 123
        assert result[0].nmid == 456
        assert len(result[0].stats) == 1
        assert result[0].stats[0].norm_query == "phrase1"
        assert result[0].stats[0].views == 100
        assert result[0].stats[0].clicks == 10
        assert result[0].stats[0].ctr == 10.0
        assert result[0].stats[0].cpm == 5.0
        assert result[0].stats[0].add_to_cart == 5
        assert result[0].stats[0].orders == 2
        assert result[0].stats[0].cpc == 0.5
        assert result[0].stats[0].avr_pos == 3.0

