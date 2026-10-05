"""Overlay для cost-activity: явный complex_adv vs bare-вызов без fraction на setting.

Инвариант: при ``f=0.5`` (M=2) и ``fact_predict_orders < plan.orders`` порог —
overlay max (200 при base max=100). Avg=150:

- overlay → ``is_active is True`` (150 <= 200);
- сырой Plan → ``is_active is False`` при плохом total CPO (150 > 100).

Стек вызовов не читается: локаль ``complex_adv`` без аргумента overlay не включает.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.shop_runner.service_manager.services.v3_point_order_cpo import (
    load_rec_orders_per_view_for_v3,
)
from app.shared.domains.wb.utils.auto_campaign_cost_activity import (
    _promo_fraction_from_object,
    _resolve_runtime_complex_adv,
    get_auto_campaign_cost_activity_metrics,
    is_auto_campaign_active,
)
from app.shared.domains.wb.utils.rec_system_shelf_mode import (
    is_rec_system_shelf_mode_operational,
)

pytestmark = pytest.mark.unit

_AVG_BETWEEN_BASE_AND_OVERLAY = 150.0
_BASE_MAX = 100.0
_OVERLAY_MAX = 200.0
_PROMO_HALF = Decimal("0.5")


def _plan_fact_summary(
    *,
    fact_predict_orders: float = 5.0,
    fact_pay_for_order: float | None = 150.0,
) -> SimpleNamespace:
    return SimpleNamespace(
        fact_predict_orders=fact_predict_orders,
        fact_original_orders=None,
        fact_pay_for_order=fact_pay_for_order,
        fact_method=None,
        plan_fact_ch_ts_msk="01.01.2025 00:00",
    )


def _adv_setting(
    *,
    flag_on: bool = True,
    max_pay: float = _BASE_MAX,
    promo_fraction: Decimal | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        adv_id=88001,
        plan_for_sales_for_day=10,
        target_price_for_order=50.0,
        max_price_for_order=max_pay,
        raise_plan_on_promobonuses=flag_on,
        sales_predict_method=FactMethods.DIRECT_SALES,
        auto_shelf_bid_control_enabled=False,
        bidder_coroutine_type=None,
        promo_fraction=promo_fraction,
        rec_system_mode=True,
        active_status="started",
        auto_budget_daily_limit=0,
        search_auto_budget_daily_limit=0,
        common_budget_daily_limit=None,
    )


def _overlay_carrier(
    *,
    promo_fraction: Decimal = _PROMO_HALF,
    auto_fact_cpo: float | None = 150.0,
) -> SimpleNamespace:
    return SimpleNamespace(
        promo_fraction=promo_fraction,
        auto_fact_cpo=auto_fact_cpo,
    )


def _reader(
    *,
    fact_pay_for_order: float | None = 150.0,
) -> SimpleNamespace:
    return SimpleNamespace(
        get_latest_plan_fact=AsyncMock(
            return_value=_plan_fact_summary(fact_pay_for_order=fact_pay_for_order)
        )
    )


def _avg_patch():
    return patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity."
        "full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=_AVG_BETWEEN_BASE_AND_OVERLAY),
    )


@pytest.mark.asyncio
async def test_explicit_complex_adv_raises_max_threshold_and_keeps_campaign_active() -> None:
    adv = _adv_setting()
    overlay = _overlay_carrier()
    reader = _reader()
    with _avg_patch():
        metrics = await get_auto_campaign_cost_activity_metrics(
            adv,
            plan_fact_reader=reader,
            complex_adv=overlay,
        )
        active = await is_auto_campaign_active(
            adv,
            plan_fact_reader=reader,
            complex_adv=overlay,
        )
    assert metrics.target_cost == _OVERLAY_MAX
    assert metrics.cost_threshold_kind == "max"
    assert metrics.is_active is True
    assert active is True


@pytest.mark.asyncio
async def test_bare_call_without_fraction_on_setting_uses_base_plan() -> None:
    adv = _adv_setting()
    reader = _reader()
    with _avg_patch():
        metrics = await get_auto_campaign_cost_activity_metrics(
            adv,
            plan_fact_reader=reader,
        )
    assert metrics.target_cost == _BASE_MAX
    assert metrics.is_active is False


@pytest.mark.asyncio
async def test_bare_call_ignores_adjacent_overlay_object_without_argument() -> None:
    """Локальный overlay без ``complex_adv=`` не влияет на расчёт (нет inspect)."""
    adv = _adv_setting()
    overlay_dto = _overlay_carrier()
    reader = _reader()
    with _avg_patch():
        metrics = await get_auto_campaign_cost_activity_metrics(
            adv,
            plan_fact_reader=reader,
        )
    assert metrics.target_cost == _BASE_MAX
    assert metrics.is_active is False
    assert overlay_dto.promo_fraction == _PROMO_HALF


@pytest.mark.asyncio
async def test_fraction_already_on_adv_setting_used_on_bare_call() -> None:
    adv = _adv_setting(promo_fraction=_PROMO_HALF)
    reader = _reader()
    with _avg_patch():
        metrics = await get_auto_campaign_cost_activity_metrics(
            adv,
            plan_fact_reader=reader,
        )
    assert metrics.target_cost == _OVERLAY_MAX
    assert metrics.is_active is True


@pytest.mark.asyncio
async def test_zero_fraction_on_complex_adv_stays_on_base_plan() -> None:
    adv = _adv_setting()
    overlay = _overlay_carrier(promo_fraction=Decimal("0"))
    reader = _reader()
    with _avg_patch():
        metrics = await get_auto_campaign_cost_activity_metrics(
            adv,
            plan_fact_reader=reader,
            complex_adv=overlay,
        )
    assert metrics.target_cost == _BASE_MAX
    assert metrics.is_active is False


def test_promo_fraction_from_object_reads_fraction_alias_and_rejects_junk() -> None:
    assert _promo_fraction_from_object(None) is None
    assert _promo_fraction_from_object(SimpleNamespace(promo_fraction=None)) is None
    assert _promo_fraction_from_object(SimpleNamespace(promo_fraction=0)) is None
    assert _promo_fraction_from_object(
        SimpleNamespace(promo_fraction=None, fraction=Decimal("0.2"))
    ) == Decimal("0.2")
    assert _promo_fraction_from_object(SimpleNamespace(promo_fraction="not-a-number")) is None


def test_resolve_runtime_prefers_explicit_then_setting_then_effective_plan() -> None:
    overlay = _overlay_carrier()
    adv = _adv_setting(promo_fraction=Decimal("0.2"))
    assert _resolve_runtime_complex_adv(adv, overlay) is overlay

    bare = _adv_setting(promo_fraction=Decimal("0.3"))
    assert _resolve_runtime_complex_adv(bare, None) is bare

    via_plan = _adv_setting(promo_fraction=None)
    via_plan.effective_promo_plan = SimpleNamespace(fraction=Decimal("0.4"))
    resolved = _resolve_runtime_complex_adv(via_plan, None)
    assert _promo_fraction_from_object(resolved) == Decimal("0.4")

    empty = _adv_setting(promo_fraction=None)
    assert _resolve_runtime_complex_adv(empty, None) is None


@pytest.mark.asyncio
async def test_shelf_mode_bare_call_uses_base_plan_without_complex_adv() -> None:
    adv = _adv_setting()
    reader = _reader()
    with _avg_patch():
        operational = await is_rec_system_shelf_mode_operational(
            adv,
            plan_fact_reader=reader,
        )
    assert operational is False


@pytest.mark.asyncio
async def test_shelf_mode_forwards_complex_adv_for_overlay() -> None:
    adv = _adv_setting()
    overlay = _overlay_carrier()
    reader = _reader()
    with _avg_patch():
        operational = await is_rec_system_shelf_mode_operational(
            adv,
            plan_fact_reader=reader,
            complex_adv=overlay,
        )
    assert operational is True


@pytest.mark.asyncio
async def test_shelf_mode_uses_overlay_when_fraction_already_on_adv() -> None:
    adv = _adv_setting(promo_fraction=_PROMO_HALF)
    reader = _reader()
    with _avg_patch():
        operational = await is_rec_system_shelf_mode_operational(
            adv,
            plan_fact_reader=reader,
        )
    assert operational is True


@pytest.mark.asyncio
async def test_v3_rec_orders_bare_adv_without_overlay_skips_rec_conversion() -> None:
    adv = _adv_setting()
    rec = AsyncMock(return_value=0.01)
    with (
        patch(
            "app.shared.domains.wb.utils.auto_campaign_cost_activity."
            "PlanFactReader.get_latest_plan_fact",
            new=AsyncMock(return_value=_plan_fact_summary()),
        ),
        _avg_patch(),
        patch(
            "app.modules.shop_runner.wb_stat_manager.rec_conversion_service.get_rec_conversion",
            rec,
        ),
    ):
        result = await load_rec_orders_per_view_for_v3(
            adv,
            rec_system_promotion_mode_active=True,
        )
    assert result is None
    rec.assert_not_called()


@pytest.mark.asyncio
async def test_v3_rec_orders_forwards_complex_adv_for_overlay() -> None:
    adv = _adv_setting()
    overlay = _overlay_carrier()
    rec = AsyncMock(return_value=0.01)
    with (
        patch(
            "app.shared.domains.wb.utils.auto_campaign_cost_activity."
            "PlanFactReader.get_latest_plan_fact",
            new=AsyncMock(return_value=_plan_fact_summary()),
        ),
        _avg_patch(),
        patch(
            "app.modules.shop_runner.wb_stat_manager.rec_conversion_service.get_rec_conversion",
            rec,
        ),
    ):
        result = await load_rec_orders_per_view_for_v3(
            adv,
            rec_system_promotion_mode_active=True,
            complex_adv=overlay,
        )
    assert result == 0.01
    rec.assert_awaited_once_with(adv.adv_id)


@pytest.mark.asyncio
async def test_v3_rec_orders_uses_overlay_when_fraction_already_on_adv() -> None:
    adv = _adv_setting(promo_fraction=_PROMO_HALF)
    rec = AsyncMock(return_value=0.01)
    with (
        patch(
            "app.shared.domains.wb.utils.auto_campaign_cost_activity."
            "PlanFactReader.get_latest_plan_fact",
            new=AsyncMock(return_value=_plan_fact_summary()),
        ),
        _avg_patch(),
        patch(
            "app.modules.shop_runner.wb_stat_manager.rec_conversion_service.get_rec_conversion",
            rec,
        ),
    ):
        result = await load_rec_orders_per_view_for_v3(
            adv,
            rec_system_promotion_mode_active=True,
        )
    assert result == 0.01
    rec.assert_awaited_once_with(adv.adv_id)
