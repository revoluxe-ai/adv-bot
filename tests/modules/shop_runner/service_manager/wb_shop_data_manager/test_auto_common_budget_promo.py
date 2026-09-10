"""Unit: auto_common_budget base first, overlay multiplier once."""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager import (
    WBShopDataManager,
)
from app.shared.domains.wb.utils.promo_plan_multiplier import build_effective_promo_plan
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    PlanData,
)


@pytest.mark.unit
def test_auto_common_budget_multiplied_once_after_base_product() -> None:
    adv = SimpleNamespace(
        auto_common_budget=True,
        max_price_for_order=500,
        plan_for_sales_for_day=10,
        common_budget_daily_limit=1,
        raise_plan_on_promobonuses=True,
    )
    WBShopDataManager._set_auto_commom_budget([adv])
    assert adv.common_budget_daily_limit == 5000
    overlay = build_effective_promo_plan(
        flag_enabled=True,
        fraction=Decimal("0.5"),
        base_plan=PlanData(orders=10, target_pay_for_order=400, max_pay_for_order=500),
        auto_budget_daily_limit=0,
        search_auto_budget_daily_limit=0,
        common_budget_daily_limit=5000,
    )
    assert overlay.promo_target_budget == 10000
