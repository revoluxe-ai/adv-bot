import pytest
from unittest.mock import AsyncMock, patch
from app.core.mp.wb.api.adapter.promotion_client.promotion_client import PromotionClient
from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.command import GetNormqueryStatsCommand
from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.dto import NormqueryStatsDTO
from app.core.mp.wb.api.domain_managers.promotion.promotion_manager import PromotionManager
from app.core.mp.wb.api.generated.promotion.marketing_and_promotions_client.models import (
    V0GetNormQueryStatsItem,
    V0GetNormQueryStatsItemStat,
    V0GetNormQueryStatsResponse
)
import datetime


@pytest.fixture
def mock_promotion_client():
    return AsyncMock(spec=PromotionClient)


@pytest.fixture
def promotion_manager(mock_promotion_client):
    return PromotionManager(promotion_client=mock_promotion_client)


@pytest.mark.asyncio
async def test_get_normquery_stats(promotion_manager, mock_promotion_client):
    advert_id = 123
    nm_id = 456
    today = datetime.date.today()

    expected_dto = [
        NormqueryStatsDTO(
            advert_id=advert_id,
            nm_id=nm_id,
            norm_query="test phrase",
            views=10,
            clicks=5,
            ctr=0.5,
            cpm=100.0,
            add_to_cart=5,
            orders=2,
            cpc=0.5,
            avr_pos=3.0,
            add_keys=[],
            add_properties={},
        )
    ]
    mock_stats_item = V0GetNormQueryStatsItemStat(
        norm_query="test phrase",
        views=10,
        clicks=5,
        ctr=0.5,
        cpm=100.0,
        atbs=5,
        orders=2,
        cpc=0.5,
        avg_pos=3.0,
    )
    mock_response_item = V0GetNormQueryStatsItem(
        advert_id=advert_id,
        nm_id=nm_id,
        stats=[mock_stats_item],
    )
    mock_response = V0GetNormQueryStatsResponse(
        stats=[mock_response_item],
    )

    # Исправляем ошибку TypeError: object AsyncMock can't be used in 'await' expression
    mock_promotion_client.normquery_stats_adapter.get_adv_v0_normquery_stats = AsyncMock(return_value=expected_dto)

    result = await promotion_manager.get_normquery_stats(advert_id, today, today, nm_id)

    mock_promotion_client.normquery_stats_adapter.get_adv_v0_normquery_stats.assert_awaited_once_with(
        GetNormqueryStatsCommand(advert_id=advert_id, date_from=today, date_to=today, nm_id=nm_id)
    )
    assert result == expected_dto
