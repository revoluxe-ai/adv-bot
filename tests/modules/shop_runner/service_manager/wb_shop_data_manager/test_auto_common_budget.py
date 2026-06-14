"""Unit-тесты синхронизации auto common budget в WBShopDataManager."""

from types import SimpleNamespace

import pytest

from app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager import (
    WBShopDataManager,
)


def _adv(
    *,
    auto_common_budget: bool = False,
    max_price_for_order: int | None = None,
    plan_for_sales_for_day: int | None = None,
    common_budget_daily_limit: int = 100,
) -> SimpleNamespace:
    return SimpleNamespace(
        auto_common_budget=auto_common_budget,
        max_price_for_order=max_price_for_order,
        plan_for_sales_for_day=plan_for_sales_for_day,
        common_budget_daily_limit=common_budget_daily_limit,
    )


@pytest.mark.unit
def test_set_auto_commom_budget_recalculates_when_enabled() -> None:
    adv = _adv(
        auto_common_budget=True,
        max_price_for_order=500,
        plan_for_sales_for_day=10,
        common_budget_daily_limit=1,
    )
    WBShopDataManager._set_auto_commom_budget([adv])
    assert adv.common_budget_daily_limit == 5000


@pytest.mark.unit
def test_set_auto_commom_budget_keeps_limit_when_disabled() -> None:
    adv = _adv(
        auto_common_budget=False,
        max_price_for_order=500,
        plan_for_sales_for_day=10,
        common_budget_daily_limit=777,
    )
    WBShopDataManager._set_auto_commom_budget([adv])
    assert adv.common_budget_daily_limit == 777


@pytest.mark.unit
def test_set_auto_commom_budget_skips_when_plan_or_max_missing() -> None:
    adv_missing_max = _adv(
        auto_common_budget=True,
        max_price_for_order=None,
        plan_for_sales_for_day=10,
        common_budget_daily_limit=333,
    )
    adv_missing_plan = _adv(
        auto_common_budget=True,
        max_price_for_order=500,
        plan_for_sales_for_day=None,
        common_budget_daily_limit=444,
    )
    WBShopDataManager._set_auto_commom_budget([adv_missing_max, adv_missing_plan])
    assert adv_missing_max.common_budget_daily_limit == 333
    assert adv_missing_plan.common_budget_daily_limit == 444
