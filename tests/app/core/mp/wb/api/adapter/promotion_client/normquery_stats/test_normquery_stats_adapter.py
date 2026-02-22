import datetime

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.adapter import NormqueryStatsAdapter
from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.dto import (
    NormqueryStat,
    NormqueryStatsDTO,
)
from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.get_normquery_stats import (
    command_to_bodies,
)
from app.core.mp.wb.api.adapter.promotion_client.promotion_client import PromotionClient
from app.core.mp.wb.api.domain_managers.promotion.methods.get_normquery_stats.convertor import (
    dto_to_command,
)
from app.core.mp.wb.api.domain_managers.promotion.promotion_manager import PromotionManager
from app.core.mp.wb.api.generated.promotion.v4.marketing_and_promotions_client.marketing_and_promotions_client.models import (
    V0GetNormQueryStatsItem,
    V0GetNormQueryStatsItemStat,
    V0GetNormQueryStatsResponse,
)
from app.core.mp.wb.api.request_limit_manager import RequestLimitManager
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from tests.factories.adv_factory import AdvSettingFactory


@pytest.fixture
def mock_auth_client_handler():
    return AsyncMock()


@pytest.fixture
def mock_request_limit_manager():
    mock = AsyncMock(spec=RequestLimitManager)
    mock.api_call_state = {}
    return mock


@pytest.fixture
def complex_adv():
    """Мок ComplexAdv без БД (корневой complex_adv тянет Docker)."""
    mock_adv = MagicMock()
    mock_adv.nmids = [456]
    mock_adv.auto_adv_id = 123
    mock_adv.search_adv = None
    return mock_adv


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
    command = dto_to_command([complex_adv], today, today)
    expected_body = command_to_bodies(command)[0]
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
        spend=10.0,
    )

    # TODO: Переделать запрос рейтинга ключей, чтобы брал превентивные данные более широко
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
            body=expected_body,
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
        assert result[0].stats[0].spend == 10.0


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
        nmids=[nm_id],
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
    mock_promotion_client.normquery_stats_adapter.get_adv_v0_normquery_stats = (
        AsyncMock(return_value=expected_dto)
    )

    result = await promotion_manager.get_normquery_stats(complex_advs, today, today)

    expected_command = dto_to_command(complex_advs, today, today)
    mock_promotion_client.normquery_stats_adapter.get_adv_v0_normquery_stats.assert_awaited_once_with(
        expected_command
    )
    assert result == expected_dto

