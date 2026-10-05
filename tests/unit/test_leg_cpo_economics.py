"""Regression tests для spec leg-cpo-economics: CPO каждой рекламной ноги изолирован."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.common_advs_stat import data_manager as common_advs_stat_module
from app.modules.common_advs_stat.data_manager import CommonAdvsStatDataManager
from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode
from app.modules.full_stat_adv_updater.types.full_adv_stat import SmallFullAdvStat
from app.modules.shop_runner.service_manager.wb_shop_data_manager import (
    wb_shop_data_manager as wb_shop_data_manager_module,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager import (
    WBShopDataManager,
)
from app.modules.shop_runner.wb_stat_manager.leg_cpo import (
    LegCpoSnapshot,
    build_leg_cpo_snapshot,
    compute_leg_cpo,
)
from app.shared.domains.wb.dto.wb_adv_dto import WBAdvDTO
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods


pytestmark = pytest.mark.unit


def _stat(*, spend: float, orders: int) -> SmallFullAdvStat:
    """Создать production-shaped рекламный stat для проверки leg-cpo формулы."""
    return SmallFullAdvStat(
        views=100,
        clicks=10,
        spend=spend,
        added_to_cart=2,
        orders=orders,
        sum_price=0.0,
    )


def test_compute_leg_cpo_preserves_denominator_floor() -> None:
    """Spec leg-cpo-economics: ноль заказов не должен делить на ноль или смешивать ноги."""
    assert compute_leg_cpo(_stat(spend=240.0, orders=0)) == pytest.approx(240.0)
    assert compute_leg_cpo(_stat(spend=240.0, orders=3)) == pytest.approx(80.0)
    assert compute_leg_cpo(None) is None


def test_build_leg_cpo_snapshot_keeps_auto_search_independent() -> None:
    """Spec leg-cpo-economics: один window обязан вернуть независимые Auto/Search CPO."""
    start = datetime(2026, 9, 28)
    end = datetime(2026, 9, 29)
    snapshot = build_leg_cpo_snapshot(
        auto_adv_id=101,
        search_adv_id=202,
        stats_by_adv_id={
            101: _stat(spend=600.0, orders=2),
            202: _stat(spend=300.0, orders=3),
        },
        start_date=start,
        end_date=end,
    )

    assert snapshot.auto_cpo == pytest.approx(300.0)
    assert snapshot.search_cpo == pytest.approx(100.0)
    assert snapshot.start_date == start
    assert snapshot.end_date == end


def test_build_leg_cpo_snapshot_missing_search_is_unavailable() -> None:
    """Spec leg-cpo-economics: отсутствующая Search-нога не получает Auto/common fallback."""
    snapshot = build_leg_cpo_snapshot(
        auto_adv_id=101,
        search_adv_id=None,
        stats_by_adv_id={101: _stat(spend=120.0, orders=2)},
        start_date=datetime(2026, 9, 28),
        end_date=datetime(2026, 9, 29),
    )

    assert snapshot.auto_cpo == pytest.approx(60.0)
    assert snapshot.search_cpo is None


def test_existing_search_leg_without_ch_rows_is_unavailable_not_zero() -> None:
    """Structural Search без строк за window — unknown, а не синтетический CPO=0."""
    snapshot = build_leg_cpo_snapshot(
        auto_adv_id=101,
        search_adv_id=202,
        stats_by_adv_id={101: _stat(spend=120.0, orders=2)},
        start_date=datetime(2026, 9, 28),
        end_date=datetime(2026, 9, 29),
    )

    assert snapshot.auto_cpo == pytest.approx(60.0)
    assert snapshot.search_adv_id == 202
    assert snapshot.search_cpo is None


def test_runtime_dto_keeps_common_and_leg_cpo_distinct() -> None:
    """Spec leg-cpo-economics: aggregate fact и leg CPO должны coexist без semantic overwrite."""
    adv_setting = MagicMock()
    adv_setting.adv_id = 101
    adv_setting.search_adv_id = 202
    adv_setting.plan_for_sales_for_day = 10
    adv_setting.target_price_for_order = 100
    adv_setting.max_price_for_order = 150
    adv_setting.nmids = [777]
    complex_adv = ComplexAdv(adv_setting=adv_setting, fact_pay_for_order=500.0)
    snapshot = LegCpoSnapshot(
        auto_adv_id=101,
        search_adv_id=202,
        auto_cpo=300.0,
        search_cpo=100.0,
        start_date=datetime(2026, 9, 28),
        end_date=datetime(2026, 9, 29),
    )
    complex_adv.attach_leg_cpo(snapshot)

    dto = WBAdvDTO(
        complex_adv=complex_adv,
        plan=PlanData(orders=10, target_pay_for_order=100, max_pay_for_order=150),
        fact=FactData(
            predict_orders=2,
            original_orders=2,
            pay_for_order=500.0,
            fact_method=FactMethods.DIRECT_SALES,
        ),
        keywords=[],
        min_bids=MagicMock(search={777: 50}),
    )

    assert complex_adv.fact_pay_for_order == pytest.approx(500.0)
    assert complex_adv.auto_fact_cpo == pytest.approx(300.0)
    assert complex_adv.search_fact_cpo == pytest.approx(100.0)
    assert dto.fact_pay_for_order == pytest.approx(500.0)
    assert dto.auto_fact_cpo == pytest.approx(300.0)
    assert dto.search_fact_cpo == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_common_stat_projection_keeps_connected_leg_without_rows_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """UI/read-model не превращает отсутствие CH-строк Search в synthetic CPO=0."""
    adv = MagicMock()
    adv.adv_id = 101
    adv.search_adv_id = 202
    adv.nmids = [777]
    adv.orders_source_for_auto_mode = OrdersSourceForAutoMode.ADV_SUM
    adv.hard_min_ctr = None
    adv.cpm = 100
    adv.sales_predict_method = FactMethods.DIRECT_SALES

    manager = CommonAdvsStatDataManager()
    manager._fetch_auction_cpm_if_any = AsyncMock(return_value=90)  # type: ignore[method-assign]
    manager._get_predict_orders_for_day = AsyncMock(return_value=2.0)  # type: ignore[method-assign]
    exact_read = AsyncMock(
        return_value={101: _stat(spend=120.0, orders=2)}
    )
    monkeypatch.setattr(
        common_advs_stat_module.full_wb_adv_stat,
        "get_stats_by_adv_ids_last_days",
        exact_read,
    )
    monkeypatch.setattr(
        common_advs_stat_module.common_stat_manager,
        "get_stats_for_last_period",
        AsyncMock(return_value=MagicMock(orders=2, add_to_cart=1)),
    )
    monkeypatch.setattr(
        common_advs_stat_module.full_wb_adv_stat,
        "get_keywords_spend",
        AsyncMock(return_value=0.0),
    )
    monkeypatch.setattr(
        common_advs_stat_module.full_wb_adv_stat,
        "get_additional_cost_per_order_for_adv",
        AsyncMock(return_value=None),
    )

    result = await manager.get_data(adv, [], last_days=2)

    assert result.auto_cpo == pytest.approx(60.0)
    assert result.search_cpo is None
    assert result.full_adv_stat_for_last_days_for_auction.spend == 0.0
    assert result.full_adv_stat_for_last_days_for_auction.orders == 0
    exact_read.assert_awaited_once()
    requested_adv_ids = exact_read.await_args.args[0]
    assert requested_adv_ids == [101, 202]


@pytest.mark.asyncio
async def test_wb_dto_runtime_reuses_common_stat_leg_cpo_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spec leg-cpo-economics: runtime DTO получает те же leg CPO, что read-model/UI."""
    adv_setting = MagicMock()
    adv_setting.adv_id = 101
    adv_setting.search_adv_id = 202
    adv_setting.plan_for_sales_for_day = 10
    adv_setting.target_price_for_order = 100
    adv_setting.max_price_for_order = 150
    adv_setting.nmids = [777]
    complex_adv = ComplexAdv(adv_setting=adv_setting, search_adv=MagicMock(adv_id=202))

    manager = WBShopDataManager.__new__(WBShopDataManager)
    manager._collect_plan_data = AsyncMock(
        return_value=PlanData(orders=10, target_pay_for_order=100, max_pay_for_order=150)
    )
    manager._collect_keywords = AsyncMock(return_value=[])

    stat = SimpleNamespace(
        auto_cpo=300.0,
        search_cpo=100.0,
        stat_start_date=datetime(2026, 9, 28),
        stat_end_date=datetime(2026, 9, 29),
    )
    fact = FactData(
        predict_orders=2,
        original_orders=2,
        pay_for_order=500.0,
        fact_method=FactMethods.DIRECT_SALES,
    )
    provider = MagicMock()
    provider.get_stat_data = AsyncMock(return_value=stat)
    provider.get_fact_data = AsyncMock(return_value=fact)
    monkeypatch.setattr(
        wb_shop_data_manager_module,
        "PlanFactProvider",
        MagicMock(return_value=provider),
    )

    parts = await manager._collect_adv_data_parts(complex_adv, None)

    assert parts.complex_adv.auto_fact_cpo == pytest.approx(300.0)
    assert parts.complex_adv.search_fact_cpo == pytest.approx(100.0)
    assert parts.complex_adv.leg_cpo_snapshot is not None
    assert parts.complex_adv.leg_cpo_snapshot.start_date == stat.stat_start_date
    assert parts.complex_adv.leg_cpo_snapshot.end_date == stat.stat_end_date
    assert parts.fact.pay_for_order == pytest.approx(500.0)
