"""Unit-тесты V3 cluster bid safety cap (только update_cluster_bids path)."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.cluster_bids_redis import ClusterBidKey
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.mappers.adv_id_item_map import (
    AdvIdItemCalculateData,
)
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.new_bids_calculator.calculation_input import (
    CalculationInput,
)
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.new_bids_calculator.update_bids_command import (
    DirectEnum,
    NewBid,
    UpdateBidsCommand,
)
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.update_cluster_bids_manager import (
    UpdateClusterBidsManager,
)
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.v3_cluster_bid_safety_cap import (
    apply_v3_cluster_bid_safety_cap,
    resolve_reference_bid_for_cap,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.keyword_cpm_sources import (
    KeywordCpmSources,
)
from app.shared.domains.wb.dto.redis_keyword_bidder_status_manager.bidder_keyword_status import (
    BidderKeywordStatus,
)
from app.modules.shop_runner.wb_stat_manager.leg_cpo import LegCpoSnapshot
from tests.factories import GoodKeywordFactory

ADV_ID = 37326138
SEARCH_ADV_ID = 37464744
NMID = 123456
CLUSTER = "test cluster"
KS_ID = 42
CAP_BID = 897


def _fact(pay_for_order: float) -> FactData:
    return FactData(
        predict_orders=10.0,
        original_orders=10.0,
        pay_for_order=pay_for_order,
        fact_method=FactMethods.DIRECT_SALES,
    )


def _plan(max_pay_for_order: int = 500) -> PlanData:
    return PlanData(
        orders=10,
        target_pay_for_order=400,
        max_pay_for_order=max_pay_for_order,
    )


def _cell(
    *,
    v3_managed: bool = True,
    adv_id: int = ADV_ID,
    search_adv_id: int = SEARCH_ADV_ID,
) -> AdvIdItemCalculateData:
    return AdvIdItemCalculateData(
        search_adv_id=search_adv_id,
        nmid=NMID,
        cluster=CLUSTER,
        current_position=10.0,
        target_position=5,
        max_cpm=5000,
        step=10,
        current_cpm=3000,
        adv_id=adv_id,
        keyword_setting_original_id=KS_ID,
        strategy_mode=KeywordStrategyMode.MIN_CPA,
        v3_managed=v3_managed,
    )


def _calc_input(current_bid: int) -> CalculationInput:
    return CalculationInput(
        search_adv_id=SEARCH_ADV_ID,
        nmid=NMID,
        current_bid=current_bid,
        current_position=10.0,
        target_position=5,
        cluster=CLUSTER,
        step=10,
        min_bid=100,
        max_bid=5000,
        predict_target_bids=None,
    )


def _new_bid(new_bid: int) -> NewBid:
    return NewBid(
        new_bid=new_bid,
        search_adv_id=SEARCH_ADV_ID,
        nmid=NMID,
        cluster=CLUSTER,
        bidder_keyword_status=BidderKeywordStatus.GOOD,
        step=10,
        direct=DirectEnum.UP,
    )


def _apply(
    *,
    command: UpdateBidsCommand,
    cells: set[AdvIdItemCalculateData],
    fact_datas: dict[int, FactData],
    plan_datas: dict[int, PlanData],
    cap_index: dict[tuple[int, int, str], int],
    stored_bids: dict[ClusterBidKey, int] | None = None,
    calculation_inputs: list[CalculationInput] | None = None,
    keywords_by_cell: dict[tuple[int, int, str], object] | None = None,
) -> UpdateBidsCommand:
    return apply_v3_cluster_bid_safety_cap(
        command=command,
        map_datas=cells,
        calculation_inputs=calculation_inputs or [],
        fact_datas=fact_datas,
        plan_datas=plan_datas,
        cap_index=cap_index,
        stored_bids=stored_bids or {},
        keywords_by_cell=keywords_by_cell or {},
    )


@pytest.mark.unit
def test_cap_clamp_direct_vs_candidate_not_reference() -> None:
    """Cap 3000→897: direct DOWN от candidate, даже если reference (stats) ниже cap."""
    cell = _cell()
    result = _apply(
        command=UpdateBidsCommand(
            new_bids=[
                NewBid(
                    new_bid=3000,
                    search_adv_id=SEARCH_ADV_ID,
                    nmid=NMID,
                    cluster=CLUSTER,
                    bidder_keyword_status=BidderKeywordStatus.GOOD,
                    step=10,
                    direct=DirectEnum.UP,
                )
            ]
        ),
        cells={cell},
        fact_datas={ADV_ID: _fact(600.0)},
        plan_datas={ADV_ID: _plan(max_pay_for_order=500)},
        cap_index={(SEARCH_ADV_ID, NMID, CLUSTER): CAP_BID},
        stored_bids={},
        calculation_inputs=[_calc_input(671)],
    )
    assert result.new_bids[0].new_bid == CAP_BID
    assert result.new_bids[0].direct == DirectEnum.DOWN


@pytest.mark.unit
def test_clamps_high_candidate_when_reference_already_at_cap() -> None:
    """Stored/reference уже на cap, но candidate выше — всё равно clamp до cap."""
    cell = _cell()
    result = _apply(
        command=UpdateBidsCommand(new_bids=[_new_bid(3000)]),
        cells={cell},
        fact_datas={ADV_ID: _fact(600.0)},
        plan_datas={ADV_ID: _plan(max_pay_for_order=500)},
        cap_index={(SEARCH_ADV_ID, NMID, CLUSTER): CAP_BID},
        stored_bids={ClusterBidKey(SEARCH_ADV_ID, NMID, CLUSTER): CAP_BID},
        calculation_inputs=[_calc_input(671)],
    )
    assert result.new_bids[0].new_bid == CAP_BID


@pytest.mark.unit
def test_no_op_when_stored_and_candidate_already_at_cap() -> None:
    """reference и candidate уже на cap — лишний WB write не нужен."""
    cell = _cell()
    result = _apply(
        command=UpdateBidsCommand(new_bids=[_new_bid(CAP_BID)]),
        cells={cell},
        fact_datas={ADV_ID: _fact(600.0)},
        plan_datas={ADV_ID: _plan(max_pay_for_order=500)},
        cap_index={(SEARCH_ADV_ID, NMID, CLUSTER): CAP_BID},
        stored_bids={ClusterBidKey(SEARCH_ADV_ID, NMID, CLUSTER): CAP_BID},
    )
    assert result.new_bids[0].new_bid == CAP_BID


@pytest.mark.unit
def test_auto_search_id_split_caps_outgoing_bid() -> None:
    """Fact/max по Auto adv_id; исходящая ставка — Search adv_id."""
    cell = _cell()
    cap_index = {(SEARCH_ADV_ID, NMID, CLUSTER): CAP_BID}
    result = _apply(
        command=UpdateBidsCommand(new_bids=[_new_bid(3000)]),
        cells={cell},
        fact_datas={ADV_ID: _fact(600.0)},
        plan_datas={ADV_ID: _plan(max_pay_for_order=500)},
        cap_index=cap_index,
        stored_bids={
            ClusterBidKey(SEARCH_ADV_ID, NMID, CLUSTER): 3000,
        },
        calculation_inputs=[_calc_input(3000)],
    )
    assert len(result.new_bids) == 1
    assert result.new_bids[0].search_adv_id == SEARCH_ADV_ID
    assert result.new_bids[0].new_bid == CAP_BID


@pytest.mark.unit
def test_wrong_fact_key_fails_safe_no_clamp() -> None:
    """Fact только под Search id — overspend gate не срабатывает."""
    cell = _cell()
    result = _apply(
        command=UpdateBidsCommand(new_bids=[_new_bid(3000)]),
        cells={cell},
        fact_datas={SEARCH_ADV_ID: _fact(600.0)},
        plan_datas={SEARCH_ADV_ID: _plan(max_pay_for_order=500)},
        cap_index={(SEARCH_ADV_ID, NMID, CLUSTER): CAP_BID},
        stored_bids={ClusterBidKey(SEARCH_ADV_ID, NMID, CLUSTER): 3000},
    )
    assert result.new_bids[0].new_bid == 3000


@pytest.mark.unit
def test_resolve_reference_bid_redis_set_bid_over_stats() -> None:
    """cluster-bid Redis=3000 важнее stats/current_bid=150."""
    ref = resolve_reference_bid_for_cap(
        search_adv_id=SEARCH_ADV_ID,
        nmid=NMID,
        cluster=CLUSTER,
        stored_bids={ClusterBidKey(SEARCH_ADV_ID, NMID, CLUSTER): 3000},
        keyword=GoodKeywordFactory(
            cpm_sources=KeywordCpmSources(
                cpm_set_bid=None,
                cpm_from_stats=150.0,
                cpm_from_bid_log=671.0,
            ),
        ),
        calculation_input=_calc_input(150),
    )
    assert ref == 3000


@pytest.mark.unit
def test_redis_set_bid_fallback_caps_to_matrix_bid() -> None:
    """API miss, stored=3000, stats=150 — reference 3000, outgoing cap."""
    cell = _cell()
    result = _apply(
        command=UpdateBidsCommand(new_bids=[_new_bid(3000)]),
        cells={cell},
        fact_datas={ADV_ID: _fact(600.0)},
        plan_datas={ADV_ID: _plan(max_pay_for_order=500)},
        cap_index={(SEARCH_ADV_ID, NMID, CLUSTER): CAP_BID},
        stored_bids={ClusterBidKey(SEARCH_ADV_ID, NMID, CLUSTER): 3000},
        calculation_inputs=[_calc_input(150)],
    )
    assert result.new_bids[0].new_bid == CAP_BID


@pytest.mark.unit
def test_stored_bid_wins_over_api_cache_stale() -> None:
    """cluster-bid=3000 побеждает CalculationInput.current_bid=671 (api-cluster-bid)."""
    cell = _cell()
    result = _apply(
        command=UpdateBidsCommand(new_bids=[_new_bid(3000)]),
        cells={cell},
        fact_datas={ADV_ID: _fact(600.0)},
        plan_datas={ADV_ID: _plan(max_pay_for_order=500)},
        cap_index={(SEARCH_ADV_ID, NMID, CLUSTER): CAP_BID},
        stored_bids={ClusterBidKey(SEARCH_ADV_ID, NMID, CLUSTER): 3000},
        calculation_inputs=[_calc_input(671)],
    )
    assert result.new_bids[0].new_bid == CAP_BID


@pytest.mark.unit
def test_proactive_lowering_injects_new_bid_when_calculator_returned_none() -> None:
    """Нет candidate в command, reference=3000, cap=897 — inject NewBid."""
    cell = _cell()
    result = _apply(
        command=UpdateBidsCommand(new_bids=[]),
        cells={cell},
        fact_datas={ADV_ID: _fact(600.0)},
        plan_datas={ADV_ID: _plan(max_pay_for_order=500)},
        cap_index={(SEARCH_ADV_ID, NMID, CLUSTER): CAP_BID},
        stored_bids={ClusterBidKey(SEARCH_ADV_ID, NMID, CLUSTER): 3000},
    )
    assert len(result.new_bids) == 1
    assert result.new_bids[0].new_bid == CAP_BID
    assert result.new_bids[0].direct == DirectEnum.DOWN


@pytest.mark.unit
def test_overspend_false_leaves_command_unchanged() -> None:
    cell = _cell()
    original = _new_bid(3000)
    result = _apply(
        command=UpdateBidsCommand(new_bids=[original]),
        cells={cell},
        fact_datas={ADV_ID: _fact(400.0)},
        plan_datas={ADV_ID: _plan(max_pay_for_order=500)},
        cap_index={(SEARCH_ADV_ID, NMID, CLUSTER): CAP_BID},
        stored_bids={ClusterBidKey(SEARCH_ADV_ID, NMID, CLUSTER): 3000},
    )
    assert result.new_bids[0].new_bid == 3000


@pytest.mark.unit
def test_missing_matrix_bid_leaves_command_unchanged() -> None:
    cell = _cell()
    result = _apply(
        command=UpdateBidsCommand(new_bids=[_new_bid(3000)]),
        cells={cell},
        fact_datas={ADV_ID: _fact(600.0)},
        plan_datas={ADV_ID: _plan(max_pay_for_order=500)},
        cap_index={},
        stored_bids={ClusterBidKey(SEARCH_ADV_ID, NMID, CLUSTER): 3000},
    )
    assert result.new_bids[0].new_bid == 3000


@pytest.mark.unit
def test_non_v3_cell_skipped() -> None:
    cell = _cell(v3_managed=False)
    result = _apply(
        command=UpdateBidsCommand(new_bids=[_new_bid(3000)]),
        cells={cell},
        fact_datas={ADV_ID: _fact(600.0)},
        plan_datas={ADV_ID: _plan(max_pay_for_order=500)},
        cap_index={(SEARCH_ADV_ID, NMID, CLUSTER): CAP_BID},
        stored_bids={ClusterBidKey(SEARCH_ADV_ID, NMID, CLUSTER): 3000},
    )
    assert result.new_bids[0].new_bid == 3000


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_command_empty_command_skips_remember_bids() -> None:
    """Пустой command после cap — WB/Redis не трогаются (_apply_command контракт)."""
    wb_manager = MagicMock()
    wb_manager.set_new_cluster_bids = AsyncMock()
    status_manager = MagicMock()
    status_manager.update_statuses = AsyncMock()
    cluster_bids_manager = MagicMock()
    cluster_bids_manager.remember_bids = AsyncMock()
    manager = UpdateClusterBidsManager(
        wb_manager=wb_manager,
        redis_keyword_bidder_status_manager=status_manager,
        redis_cluster_bids_manager=cluster_bids_manager,
        redis_api_cluster_bids_manager=MagicMock(),
        redis_cluster_bids_timestamp_manager=MagicMock(),
        tasks_manager=MagicMock(),
    )
    await manager._apply_command(UpdateBidsCommand(new_bids=[]))
    wb_manager.set_new_cluster_bids.assert_awaited_once()
    cluster_bids_manager.remember_bids.assert_awaited_once_with([])

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_fact_datas_uses_search_cpo_and_never_aggregate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cluster safety cap получает Search CPO из structural Search leg."""
    plan_fact_reader = MagicMock()
    plan_fact_reader.get_latest_plan_facts = AsyncMock(
        return_value={ADV_ID: SimpleNamespace()}
    )
    manager = UpdateClusterBidsManager(
        wb_manager=MagicMock(),
        redis_keyword_bidder_status_manager=MagicMock(),
        redis_cluster_bids_manager=MagicMock(),
        redis_api_cluster_bids_manager=MagicMock(),
        redis_cluster_bids_timestamp_manager=MagicMock(),
        tasks_manager=MagicMock(),
        plan_fact_reader=plan_fact_reader,
    )
    adv = SimpleNamespace(
        adv_id=ADV_ID,
        shop_id="shop-1",
        adv_setting=MagicMock(),
    )
    aggregate_fact = _fact(999.0)
    monkeypatch.setattr(
        "app.modules.plan_fact.provider.PlanFactProvider.fact_data_from_plan_fact_summary",
        lambda *_args, **_kwargs: aggregate_fact,
    )
    now = datetime(2026, 9, 30)
    leg_snapshot = LegCpoSnapshot(
        auto_adv_id=ADV_ID,
        search_adv_id=SEARCH_ADV_ID,
        auto_cpo=999.0,
        search_cpo=80.0,
        start_date=now,
        end_date=now,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.update_cluster_bids_manager.load_leg_cpo_snapshots",
        AsyncMock(return_value={ADV_ID: leg_snapshot}),
    )

    result = await manager._get_fact_datas([adv])  # type: ignore[list-item]

    assert result[ADV_ID].pay_for_order == 80.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_fact_datas_missing_search_cpo_has_no_aggregate_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing Search CPO остаётся None, даже если aggregate CPO плохой."""
    plan_fact_reader = MagicMock()
    plan_fact_reader.get_latest_plan_facts = AsyncMock(
        return_value={ADV_ID: SimpleNamespace()}
    )
    manager = UpdateClusterBidsManager(
        wb_manager=MagicMock(),
        redis_keyword_bidder_status_manager=MagicMock(),
        redis_cluster_bids_manager=MagicMock(),
        redis_api_cluster_bids_manager=MagicMock(),
        redis_cluster_bids_timestamp_manager=MagicMock(),
        tasks_manager=MagicMock(),
        plan_fact_reader=plan_fact_reader,
    )
    adv = SimpleNamespace(
        adv_id=ADV_ID,
        shop_id="shop-1",
        adv_setting=MagicMock(),
    )
    monkeypatch.setattr(
        "app.modules.plan_fact.provider.PlanFactProvider.fact_data_from_plan_fact_summary",
        lambda *_args, **_kwargs: _fact(999.0),
    )
    now = datetime(2026, 9, 30)
    leg_snapshot = LegCpoSnapshot(
        auto_adv_id=ADV_ID,
        search_adv_id=SEARCH_ADV_ID,
        auto_cpo=999.0,
        search_cpo=None,
        start_date=now,
        end_date=now,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.update_cluster_bids_manager.load_leg_cpo_snapshots",
        AsyncMock(return_value={ADV_ID: leg_snapshot}),
    )

    result = await manager._get_fact_datas([adv])  # type: ignore[list-item]

    assert result[ADV_ID].pay_for_order is None
