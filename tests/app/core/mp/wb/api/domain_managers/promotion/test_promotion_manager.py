import pytest
from unittest.mock import AsyncMock
from app.core.mp.wb.api.adapter.promotion_client.promotion_client import PromotionClient
from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.dto import NormqueryStatsDTO, NormqueryStat
from app.core.mp.wb.api.domain_managers.promotion.promotion_manager import PromotionManager
from app.core.mp.wb.api.domain_managers.promotion.methods.get_normquery_stats.convertor import (
    dto_to_command,
)
from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
    V0GetNormQueryStatsItem,
    V0GetNormQueryStatsItemStat,
)
import datetime
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import ComplexAdv
from tests.factories.adv_factory import AdvSettingFactory


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

    mock_adv_setting = AdvSettingFactory.build(
        adv_id=advert_id,
        nmids=[nm_id]
    )

    async def mock_get_keywords_func(*args, **kwargs):
        return []

    complex_adv = ComplexAdv(
        shop_id="test_shop_id",
        adv_setting=mock_adv_setting,
        search_adv=None,
        get_keywords_func=mock_get_keywords_func,
    )
    complex_advs = [complex_adv]

    expected_dto = [
        NormqueryStatsDTO(
            adv_id=advert_id,
            nmid=nm_id,
            stats=[
                NormqueryStat(
                    norm_query="test phrase",
                    views=10,
                    clicks=5,
                    ctr=0.5,
                    cpm=100.0,
                    add_to_cart=5,
                    orders=2,
                    cpc=0.5,
                    avr_pos=3.0,
                )
            ],
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
    # mock_response = V0GetNormQueryStatsResponse(
    #     stats=[mock_response_item],
    # )

    # Исправляем ошибку TypeError: object AsyncMock can't be used in 'await' expression
    mock_promotion_client.normquery_stats_adapter.get_adv_v0_normquery_stats = AsyncMock(return_value=expected_dto)

    result = await promotion_manager.get_normquery_stats(complex_advs, today, today)

    expected_command = dto_to_command(complex_advs, today, today)
    mock_promotion_client.normquery_stats_adapter.get_adv_v0_normquery_stats.assert_awaited_once_with(
        expected_command
    )
    assert result == expected_dto
