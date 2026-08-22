"""Тесты cache-only получения ключей в UpdateClusterBidsManager."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.dto import (
    NormqueryBidDTO,
)
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.mappers.adv_id_item_map import (
    AdvIdItemCalculateData,
)
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.update_cluster_bids_manager import (
    UpdateClusterBidsManager,
)
from app.modules.shop_runner.required_data_miss import ShopRunnerKeywordsCacheMissError
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
)
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy
from tests.factories import GoodKeywordFactory


@pytest.fixture(autouse=True)
def _snapshot_cluster_bids_flags_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """Без adapter path — только mock ``adv.get_keywords`` (не Redis snapshot store)."""
    monkeypatch.setenv("SNAPSHOT_CLUSTER_BIDS_SHADOW", "0")
    monkeypatch.setenv("SNAPSHOT_CLUSTER_BIDS_READ", "0")
    from app.snapshot_data_updater.config import reload_snapshot_config

    reload_snapshot_config()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_calculate_data_raises_on_keywords_cache_miss() -> None:
    manager = UpdateClusterBidsManager(
        wb_manager=MagicMock(),
        redis_keyword_bidder_status_manager=MagicMock(),
        redis_cluster_bids_manager=MagicMock(),
        redis_api_cluster_bids_manager=MagicMock(),
        redis_cluster_bids_timestamp_manager=MagicMock(),
        tasks_manager=MagicMock(),
    )
    adv = MagicMock()
    adv.auction_adv_id = 10
    adv.adv_id = 1
    adv.get_keywords = AsyncMock(
        side_effect=ShopRunnerKeywordsCacheMissError(
            "miss", shop_id="s", adv_id=1
        )
    )

    with pytest.raises(ShopRunnerKeywordsCacheMissError):
        await manager._UpdateClusterBidsManager__get_calculate_data(adv, set())
    adv.get_keywords.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("adv_target_place", [99, None])
async def test_get_calculate_data_individual_mode_no_kw_target_snap_ignores_adv_target_place(
    adv_target_place: int | None,
) -> None:
    """Нет target_place у ключа: snap, target_position=None, цель РК в карту не попадает."""
    manager = UpdateClusterBidsManager(
        wb_manager=MagicMock(),
        redis_keyword_bidder_status_manager=MagicMock(),
        redis_cluster_bids_manager=MagicMock(),
        redis_api_cluster_bids_manager=MagicMock(),
        redis_cluster_bids_timestamp_manager=MagicMock(),
        tasks_manager=MagicMock(),
    )
    cluster_text = "normquery_snap_test"
    kw = GoodKeywordFactory.build(
        keyword_setting__text=cluster_text,
        keyword_setting__target_place=None,
        cluster_stat__norm_query=cluster_text,
    )
    adv = MagicMock()
    adv.auction_adv_id = 10
    adv.adv_id = 1
    adv.nmids = [200]
    adv.individual_keywords_target_place_mode = True
    adv.target_place = adv_target_place
    adv.max_user_cpm = 500
    adv.bid_cpm_step = 10
    adv.get_keywords = AsyncMock(return_value=[kw])

    result = await manager._UpdateClusterBidsManager__get_calculate_data(
        adv, {cluster_text}
    )

    assert len(result) == 1
    (md,) = tuple(result)
    assert md.snap_to_min_bid_no_keyword_target is True
    assert md.target_position is None
    assert md.nmid == 200
    assert md.cluster == cluster_text
    if adv_target_place is not None:
        assert md.target_position is not adv_target_place


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_fact_datas_uses_batch_plan_fact_reader_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = UpdateClusterBidsManager(
        wb_manager=MagicMock(),
        redis_keyword_bidder_status_manager=MagicMock(),
        redis_cluster_bids_manager=MagicMock(),
        redis_api_cluster_bids_manager=MagicMock(),
        redis_cluster_bids_timestamp_manager=MagicMock(),
        tasks_manager=MagicMock(),
    )
    adv1 = MagicMock()
    adv1.adv_id = 101
    adv1.adv_setting = MagicMock()
    adv2 = MagicMock()
    adv2.adv_id = 202
    adv2.adv_setting = MagicMock()

    batch_mock = AsyncMock(return_value={})
    single_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.update_cluster_bids_manager.PlanFactReader.get_latest_plan_facts",
        batch_mock,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.update_cluster_bids_manager.PlanFactReader.get_latest_plan_fact",
        single_mock,
    )

    result = await manager._get_fact_datas([adv1, adv2])

    assert result == {}
    batch_mock.assert_awaited_once_with([101, 202])
    single_mock.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_cluster_bids_for_maps_maps_auto_advert_id_to_search() -> None:
    """WB fallback: ответ с auto advert_id нормализуется к search_adv_id."""
    api_cache = MagicMock()
    api_cache.get_bids = AsyncMock(return_value={})
    api_cache.replace_from_api = AsyncMock(return_value=1)

    wb_manager = MagicMock()
    wb_manager.get_current_bids = AsyncMock(
        return_value=[
            NormqueryBidDTO(
                advert_id=32824944,
                nm_id=1,
                norm_query="q1",
                bid=42,
            )
        ]
    )

    manager = UpdateClusterBidsManager(
        wb_manager=wb_manager,
        redis_keyword_bidder_status_manager=MagicMock(),
        redis_cluster_bids_manager=MagicMock(),
        redis_api_cluster_bids_manager=api_cache,
        redis_cluster_bids_timestamp_manager=MagicMock(),
        tasks_manager=MagicMock(),
    )

    map_data = AdvIdItemCalculateData(
        search_adv_id=29734515,
        adv_id=32824944,
        nmid=1,
        cluster="q1",
        current_position=1.0,
        target_position=5,
        max_cpm=500,
        step=10,
        current_cpm=None,
        keyword_setting_original_id=1,
        strategy_mode=KeywordStrategyMode.MIN_CPA,
        snap_to_min_bid_no_keyword_target=False,
    )
    adv = MagicMock()
    adv.auction_adv_id = 29734515
    adv.auto_adv_id = 32824944

    result = await manager._get_cluster_bids_for_maps({map_data}, [adv])

    assert len(result) == 1
    assert result[0].bid == 42
    assert result[0].advert_id == 29734515
    api_cache.replace_from_api.assert_awaited_once()
    written = api_cache.replace_from_api.await_args.args[0]
    assert written[0].advert_id == 29734515


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_cluster_bids_for_maps_fetches_wb_on_redis_miss() -> None:
    """Cold Redis API cache: WB fills bids and warms Redis (same as cache_current_cluster_bids)."""
    api_cache = MagicMock()
    api_cache.get_bids = AsyncMock(return_value={})
    api_cache.replace_from_api = AsyncMock(return_value=1)

    wb_manager = MagicMock()
    wb_manager.get_current_bids = AsyncMock(
        return_value=[
            NormqueryBidDTO(
                advert_id=100,
                nm_id=1,
                norm_query="q1",
                bid=42,
            )
        ]
    )

    manager = UpdateClusterBidsManager(
        wb_manager=wb_manager,
        redis_keyword_bidder_status_manager=MagicMock(),
        redis_cluster_bids_manager=MagicMock(),
        redis_api_cluster_bids_manager=api_cache,
        redis_cluster_bids_timestamp_manager=MagicMock(),
        tasks_manager=MagicMock(),
    )

    map_data = AdvIdItemCalculateData(
        search_adv_id=100,
        adv_id=1,
        nmid=1,
        cluster="q1",
        current_position=1.0,
        target_position=5,
        max_cpm=500,
        step=10,
        current_cpm=None,
        keyword_setting_original_id=1,
        strategy_mode=KeywordStrategyMode.MIN_CPA,
        snap_to_min_bid_no_keyword_target=False,
    )
    adv = MagicMock()
    adv.auction_adv_id = 100

    result = await manager._get_cluster_bids_for_maps({map_data}, [adv])

    assert len(result) == 1
    assert result[0].bid == 42
    wb_manager.get_current_bids.assert_awaited_once_with([adv])
    api_cache.replace_from_api.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_calculate_data_v3_excludes_off_strategy_keywords() -> None:
    manager = UpdateClusterBidsManager(
        wb_manager=MagicMock(),
        redis_keyword_bidder_status_manager=MagicMock(),
        redis_cluster_bids_manager=MagicMock(),
        redis_api_cluster_bids_manager=MagicMock(),
        redis_cluster_bids_timestamp_manager=MagicMock(),
        tasks_manager=MagicMock(),
    )
    adv = MagicMock()
    adv.auction_adv_id = 10
    adv.adv_id = 1
    adv.bot_active = True
    adv.strategy = Strategy.MIN_CPO
    adv.nmids = [100]
    adv.individual_keywords_target_place_mode = False
    adv.target_place = 5
    adv.max_user_cpm = 500
    adv.bid_cpm_step = 10

    kw_off = MagicMock()
    kw_off.status = KeywordStatus.GOOD
    kw_off.strategy_mode = KeywordStrategyMode.OFF
    kw_off.cluster_stat = MagicMock()
    kw_off.cluster_stat.text = "q_off"
    kw_off.text = "q_off"
    kw_off.position = 1.0
    kw_off.cpm = 50.0

    kw_on = MagicMock()
    kw_on.status = KeywordStatus.GOOD
    kw_on.hard_status = 2
    kw_on.strategy_mode = KeywordStrategyMode.MIN_CPA
    kw_on.cluster_stat = MagicMock()
    kw_on.cluster_stat.text = "q_on"
    kw_on.text = "q_on"
    kw_on.position = 2.0
    kw_on.cpm = 60.0

    kw_auto_stale = MagicMock()
    kw_auto_stale.status = KeywordStatus.GOOD
    kw_auto_stale.hard_status = 1
    kw_auto_stale.strategy_mode = KeywordStrategyMode.MIN_CPA
    kw_auto_stale.cluster_stat = MagicMock()
    kw_auto_stale.cluster_stat.text = "q_auto"
    kw_auto_stale.text = "q_auto"
    kw_auto_stale.position = 3.0
    kw_auto_stale.cpm = 70.0

    adv.get_keywords = AsyncMock(return_value=[kw_off, kw_on, kw_auto_stale])

    result = await manager._UpdateClusterBidsManager__get_calculate_data(
        adv, {"q_off", "q_on", "q_auto"}
    )
    assert len(result) == 1
    only = next(iter(result))
    assert only.cluster == "q_on"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_calculate_data_v3_excludes_auto_with_non_off_mode() -> None:
    manager = UpdateClusterBidsManager(
        wb_manager=MagicMock(),
        redis_keyword_bidder_status_manager=MagicMock(),
        redis_cluster_bids_manager=MagicMock(),
        redis_api_cluster_bids_manager=MagicMock(),
        redis_cluster_bids_timestamp_manager=MagicMock(),
        tasks_manager=MagicMock(),
    )
    adv = MagicMock()
    adv.auction_adv_id = 10
    adv.adv_id = 1
    adv.bot_active = True
    adv.strategy = Strategy.MIN_CPO
    adv.nmids = [100]
    adv.individual_keywords_target_place_mode = False
    adv.target_place = 5
    adv.max_user_cpm = 500
    adv.bid_cpm_step = 10

    kw_auto = MagicMock()
    kw_auto.status = KeywordStatus.GOOD
    kw_auto.hard_status = 1
    kw_auto.strategy_mode = KeywordStrategyMode.MIN_CPA
    kw_auto.cluster_stat = MagicMock()
    kw_auto.cluster_stat.text = "q_auto"
    kw_auto.text = "q_auto"
    kw_auto.position = 1.0
    kw_auto.cpm = 50.0

    adv.get_keywords = AsyncMock(return_value=[kw_auto])

    result = await manager._UpdateClusterBidsManager__get_calculate_data(
        adv, {"q_auto"}
    )
    assert result == set()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_calculate_data_non_v3_includes_off_strategy_keywords() -> None:
    manager = UpdateClusterBidsManager(
        wb_manager=MagicMock(),
        redis_keyword_bidder_status_manager=MagicMock(),
        redis_cluster_bids_manager=MagicMock(),
        redis_api_cluster_bids_manager=MagicMock(),
        redis_cluster_bids_timestamp_manager=MagicMock(),
        tasks_manager=MagicMock(),
    )
    adv = MagicMock()
    adv.auction_adv_id = 10
    adv.adv_id = 1
    adv.bot_active = False
    adv.nmids = [100]
    adv.individual_keywords_target_place_mode = False
    adv.target_place = 5
    adv.max_user_cpm = 500
    adv.bid_cpm_step = 10

    kw_off = MagicMock()
    kw_off.status = KeywordStatus.GOOD
    kw_off.strategy_mode = KeywordStrategyMode.OFF
    kw_off.cluster_stat = MagicMock()
    kw_off.cluster_stat.text = "q_off"
    kw_off.text = "q_off"
    kw_off.position = 1.0
    kw_off.cpm = 50.0

    adv.get_keywords = AsyncMock(return_value=[kw_off])

    result = await manager._UpdateClusterBidsManager__get_calculate_data(adv, {"q_off"})
    assert len(result) == 1
