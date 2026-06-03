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
from tests.unit.test_auto_updater_v3 import _sample_profile
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


def _complex_adv_mock() -> MagicMock:
    """ComplexAdv без truthy MagicMock-полей (rec/shelf gate)."""
    adv = MagicMock()
    adv.rec_system_promotion_mode_active = False
    adv.shelf_promotion_active = False
    return adv


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
async def test_load_keyword_v3_profile_data_returns_failure_without_cabinet() -> None:
    adv = MagicMock()
    adv.wb_cabinet_id = 99
    adv.adv_id = 1
    with patch(
        "app.client_bot.user_interface.services.keyword_v3_profile_loader._load_wb_cabinet",
        new_callable=AsyncMock,
        return_value=None,
    ):
        result = await load_keyword_v3_profile_data(adv, _calculated_keyword())
    assert result is not None
    assert result.load_failure == "нет кабинета WB"


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
            "app.client_bot.user_interface.services.keyword_v3_profile_loader.load_campaign_v3_contexts_from_database",
            new_callable=AsyncMock,
        ) as load_contexts,
        patch(
            "app.client_bot.user_interface.services.keyword_v3_profile_loader.resolve_keyword_bid_profile",
            return_value=bids,
        ),
        patch(
            "app.client_bot.user_interface.services.keyword_v3_profile_loader.profile_points_from_bid_positions",
            return_value=_sample_profile(),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.v3_point_order_cpo.load_rk_orders_per_cart_7d",
            new_callable=AsyncMock,
            return_value=2.0,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.v3_point_order_cpo.load_rec_orders_per_view_for_v3",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
            KeywordV3Context,
        )

        kw = _calculated_keyword()
        stat = kw.cluster_stat.model_copy(update={"views": 100})
        kw = kw.model_copy(update={"cluster_stat": stat})
        prof = _sample_profile()
        load_contexts.return_value = [
            KeywordV3Context(keyword=kw, position_profile=prof)
        ]
        complex_adv = _complex_adv_mock()
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

        result = await load_keyword_v3_profile_data(adv, kw)

    assert result is not None
    assert result.current_mode == KeywordStrategyMode.MIN_CPA
    min_cand = result.candidates[AggressionTargetMode.MIN_CPA]
    assert min_cand.is_valid
    assert min_cand.position is not None
    predictor.load_bid_profiles_for_nmid.assert_awaited_once_with(
        nmid=10749810,
        min_bid=50,
        positions_size=50,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_keyword_v3_profile_data_ch_without_v2_not_n_state() -> None:
    """CH есть, нет V2 CPO — не N-state (лестница через worst/imputed conv)."""
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

    stat = make_zero_keyword_stat("test kw").model_copy(
        update={"conv_views_to_orders": 0.0}
    )
    kw_no_cpo = CalculatedKeyword(
        adv_id=1,
        keyword_setting=KeywordSettingDTO(
            text="test kw",
            relevant=True,
            hard_status=1,
            id=1,
            strategy_mode=KeywordStrategyMode.OFF,
        ),
        cluster_stat=stat,
        state=KeywordState(
            status=KeywordStatus.BAD,
            reason=KeywordStatusReason.BIDDER_BAD_STATUS,
            best_keyword_status=False,
        ),
        target_pay_for_order=None,
        rating=1.0,
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
            return_value=_complex_adv_mock(),
        ),
        patch(
            "app.client_bot.user_interface.services.keyword_v3_profile_loader.DIManager.create",
        ) as di_create,
        patch(
            "app.client_bot.user_interface.services.keyword_v3_profile_loader.build_predict_keywords_target_place",
        ) as build_predictor,
        patch(
            "app.client_bot.user_interface.services.keyword_v3_profile_loader.resolve_keyword_bid_profile",
            return_value=bids,
        ),
        patch(
            "app.client_bot.user_interface.services.keyword_v3_profile_loader.load_campaign_v3_contexts_from_database",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.v3_point_order_cpo.load_rk_orders_per_cart_7d",
            new_callable=AsyncMock,
            return_value=2.0,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.v3_point_order_cpo.load_rec_orders_per_view_for_v3",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        container = MagicMock()
        hub = MagicMock()
        hub.wb_manager.get_min_bids_cache_only = AsyncMock(
            return_value=MagicMock(search={10749810: 50})
        )
        factory = MagicMock()
        factory.get_wb_manager_hub.return_value = hub
        container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory.return_value = factory
        di_create.return_value.__aenter__ = AsyncMock(return_value=container)
        di_create.return_value.__aexit__ = AsyncMock(return_value=None)

        predictor = MagicMock()
        predictor.load_bid_profiles_for_nmid = AsyncMock(return_value={"test kw": bids})
        build_predictor.return_value = predictor

        result = await load_keyword_v3_profile_data(adv, kw_no_cpo)

    assert result is not None
    assert not result.n_state
    assert result.diagnostic is not None
    assert result.diagnostic.has_ch_position_profile
    assert not result.diagnostic.has_v2_cpo
