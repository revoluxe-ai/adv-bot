"""Unit-тесты загрузчика профиля V3 для карточки ключа."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.services.keyword_v3_profile_loader import (
    _positions_size_for_adv,
    load_keyword_v3_profile_data,
)
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.predict_keywords_target_place.clickhouse_manager.dto.bid_position import (
    BidPosition,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.keyword_state import (
    KeywordState,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
    KeywordStatusReason,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_setting_dto import (
    KeywordSettingDTO,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_stat import (
    make_zero_keyword_stat,
)


def _calculated_keyword() -> CalculatedKeyword:
    stat = make_zero_keyword_stat("test kw").model_copy(
        update={"conv_views_to_orders": 0.01}
    )
    return CalculatedKeyword(
        adv_id=1,
        keyword_setting=KeywordSettingDTO(
            text="test kw",
            relevant=True,
            hard_status=2,
            id=1,
            strategy_mode=KeywordStrategyMode.MIN_CPA,
        ),
        cluster_stat=stat,
        state=KeywordState(
            status=KeywordStatus.GOOD,
            reason=KeywordStatusReason.WHITE_LIST,
            best_keyword_status=False,
        ),
        target_pay_for_order=None,
        rating=1.0,
    )


@pytest.mark.unit
def test_positions_size_for_adv_clamps_above_predictor_limit() -> None:
    adv = MagicMock()
    adv.adv_id = 99
    adv.min_target_position = 500
    assert _positions_size_for_adv(adv) == 300


@pytest.mark.unit
def test_positions_size_for_adv_uses_default_when_none() -> None:
    adv = MagicMock()
    adv.adv_id = 1
    adv.min_target_position = None
    assert _positions_size_for_adv(adv) == 300


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_keyword_v3_profile_data_returns_none_without_cabinet() -> None:
    adv = MagicMock()
    adv.wb_cabinet_id = 99
    adv.adv_id = 1
    with patch(
        "app.client_bot.user_interface.services.keyword_v3_profile_loader._load_wb_cabinet",
        new_callable=AsyncMock,
        return_value=None,
    ):
        result = await load_keyword_v3_profile_data(adv, _calculated_keyword())
    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_keyword_v3_profile_data_success() -> None:
    adv = MagicMock()
    adv.wb_cabinet_id = 1
    adv.adv_id = 32824944
    adv.nmids = [10749810]
    adv.min_target_position = 50
    adv.search_adv_id = None

    cabinet = MagicMock()
    cabinet.shop_id = "shop-1"

    ts = datetime.now()
    bids = [BidPosition("test kw", 1, 100, ts)]

    min_cpa = ModeCandidate(
        mode=AggressionTargetMode.MIN_CPA,
        bid=100.0,
        position=1,
        predicted_cpa=50.0,
        is_valid=True,
    )

    with (
        patch(
            "app.client_bot.user_interface.services.keyword_v3_profile_loader._load_wb_cabinet",
            new_callable=AsyncMock,
            return_value=cabinet,
        ),
        patch(
            "app.client_bot.user_interface.services.keyword_v3_profile_loader._build_complex_adv",
            new_callable=AsyncMock,
        ) as build_adv,
        patch(
            "app.client_bot.user_interface.services.keyword_v3_profile_loader.DIManager.create",
        ) as di_create,
        patch(
            "app.client_bot.user_interface.services.keyword_v3_profile_loader.build_predict_keywords_target_place",
        ) as build_predictor,
        patch(
            "app.client_bot.user_interface.services.keyword_v3_profile_loader.build_mode_candidates",
            return_value={
                AggressionTargetMode.MIN_CPA: min_cpa,
                AggressionTargetMode.OPTIMUM: min_cpa,
                AggressionTargetMode.MAX_CONVERSION: min_cpa,
            },
        ),
        patch(
            "app.client_bot.user_interface.services.keyword_v3_profile_loader.resolve_keyword_bid_profile",
            return_value=bids,
        ),
        patch(
            "app.client_bot.user_interface.services.keyword_v3_profile_loader.profile_points_from_bid_positions",
            return_value=[],
        ),
    ):
        complex_adv = MagicMock()
        build_adv.return_value = complex_adv

        container = MagicMock()
        hub = MagicMock()
        hub.wb_manager.get_min_bids_cache_only = AsyncMock(
            return_value=MagicMock(search={10749810: 50})
        )
        hub.wb_data_manager = MagicMock()
        factory = MagicMock()
        factory.get_wb_manager_hub.return_value = hub
        container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory.return_value = factory
        di_create.return_value.__aenter__ = AsyncMock(return_value=container)
        di_create.return_value.__aexit__ = AsyncMock(return_value=None)

        predictor = MagicMock()
        predictor.load_bid_profiles_for_nmid = AsyncMock(return_value={"test kw": bids})
        build_predictor.return_value = predictor

        result = await load_keyword_v3_profile_data(adv, _calculated_keyword())

    assert result is not None
    assert result.current_mode == KeywordStrategyMode.MIN_CPA
    assert result.candidates[AggressionTargetMode.MIN_CPA].position == 1
    predictor.load_bid_profiles_for_nmid.assert_awaited_once_with(
        nmid=10749810,
        min_bid=50,
        positions_size=50,
    )
