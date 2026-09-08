"""Unit: пропорциональный promo-множитель и five Owner entities."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.modules.plan_fact.provider import PlanFactProvider
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    PlanData,
)
from app.shared.domains.wb.utils.promo_plan_multiplier import (
    PROMO_AUTO_BUDGET_LABEL,
    PROMO_MAX_CPO_LABEL,
    PROMO_TARGET_BUDGET_LABEL,
    PROMO_TARGET_CPO_LABEL,
    PROPO_SEARCH_BUDGET_LABEL,
    build_effective_promo_plan,
    promo_fraction_from_amounts,
    promo_multiplier,
    scale_int,
)


@pytest.mark.unit
def test_fraction_and_multiplier_full_fifty_percent() -> None:
    fraction = promo_fraction_from_amounts(promo_amount=500, total_amount=1000)
    assert fraction == Decimal("0.5")
    assert promo_multiplier(fraction) == Decimal("2.000000")


@pytest.mark.unit
def test_fraction_and_multiplier_partial_200_of_1000() -> None:
    fraction = promo_fraction_from_amounts(promo_amount=200, total_amount=1000)
    assert fraction == Decimal("0.2")
    assert promo_multiplier(fraction) == Decimal("1.250000")


@pytest.mark.unit
def test_fraction_zero_and_full_boundaries() -> None:
    assert promo_fraction_from_amounts(promo_amount=0, total_amount=1000) == Decimal("0")
    assert promo_multiplier(Decimal("0")) == Decimal("1")
    capped = promo_fraction_from_amounts(promo_amount=1000, total_amount=1000)
    assert capped < Decimal("1")
    assert promo_multiplier(Decimal("1")) == Decimal("1")


@pytest.mark.unit
def test_scale_int_half_up() -> None:
    assert scale_int(100, Decimal("1.25")) == 125
    assert scale_int(3, Decimal("1.5")) == 5


@pytest.mark.unit
def test_five_entities_share_one_multiplier() -> None:
    base = PlanData(orders=10, target_pay_for_order=400, max_pay_for_order=500)
    overlay = build_effective_promo_plan(
        flag_enabled=True,
        fraction=Decimal("0.2"),
        base_plan=base,
        auto_budget_daily_limit=1000,
        search_auto_budget_daily_limit=800,
        common_budget_daily_limit=5000,
    )
    assert overlay.active is True
    assert overlay.multiplier == Decimal("1.250000")
    assert overlay.PromoMaxCPO == 625
    assert overlay.PromoTargetCPO == 500
    assert overlay.PromoAutoBudget == 1250
    assert overlay.PropoSearchBudget == 1000
    assert overlay.promo_target_budget == 6250
    assert overlay.PromoTarget_Budget == 6250
    assert overlay.plan is not None
    assert overlay.plan.max_pay_for_order == 625
    assert overlay.plan.target_pay_for_order == 500
    assert PROMO_MAX_CPO_LABEL == "PromoMaxCPO"
    assert PROMO_TARGET_CPO_LABEL == "PromoTargetCPO"
    assert PROMO_AUTO_BUDGET_LABEL == "PromoAutoBudget"
    assert PROPO_SEARCH_BUDGET_LABEL == "PropoSearchBudget"
    assert PROMO_TARGET_BUDGET_LABEL == "PromoTarget Budget"


@pytest.mark.unit
def test_flag_off_keeps_base() -> None:
    base = PlanData(orders=10, target_pay_for_order=400, max_pay_for_order=500)
    overlay = build_effective_promo_plan(
        flag_enabled=False,
        fraction=Decimal("0.5"),
        base_plan=base,
        auto_budget_daily_limit=1000,
        search_auto_budget_daily_limit=800,
        common_budget_daily_limit=5000,
    )
    assert overlay.active is False
    assert overlay.multiplier == Decimal("1")
    assert overlay.PromoMaxCPO == 500
    assert overlay.PromoAutoBudget == 1000


@pytest.mark.unit
def test_get_plan_data_stays_raw() -> None:
    adv = SimpleNamespace(
        plan_for_sales_for_day=10,
        target_price_for_order=400,
        max_price_for_order=500,
        raise_plan_on_promobonuses=True,
        auto_budget_daily_limit=1000,
        search_auto_budget_daily_limit=800,
        common_budget_daily_limit=5000,
        promo_fraction=Decimal("0.5"),
    )
    raw = PlanFactProvider.get_plan_data(adv)
    effective = PlanFactProvider.get_effective_plan_data(adv)
    assert raw is not None
    assert raw.max_pay_for_order == 500
    assert effective is not None
    assert effective.max_pay_for_order == 1000
