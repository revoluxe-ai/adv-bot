"""Regression: CH plan_fact write boundary must persist base Plan, not overlay.plan.

ROOT-001 (BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z): ``process_pre_adv`` must
read ``PlanFactProvider.get_plan_data`` at the write boundary (as ``process_adv``
does), even when ``PreComplexAdv.plan_data`` carries overlay Plan from
``WBShopDataManager._build_pre_complex_adv``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.plan_fact.provider import PlanFactProvider
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_controller import (
    PlanFactController,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.pre_complex_adv import (
    PreComplexAdv,
)


def _overlay_pre_adv(*, base_max: int = 500, overlay_max: int = 1000) -> PreComplexAdv:
    """Simulate ``_build_pre_complex_adv`` seed: plan_data is overlay, not base."""
    auto_adv = MagicMock(spec=AdvSetting)
    auto_adv.plan_for_sales_for_day = 10
    auto_adv.target_price_for_order = 400
    auto_adv.max_price_for_order = base_max

    wb_cabinet = MagicMock()
    wb_cabinet.shop_id = "shop-promo-1"
    auto_adv.wb_cabinet = wb_cabinet
    auto_adv.adv_id = 9001

    base_plan = PlanData(orders=10, target_pay_for_order=400, max_pay_for_order=base_max)
    overlay_plan = PlanData(
        orders=10,
        target_pay_for_order=800,
        max_pay_for_order=overlay_max,
    )
    assert not hasattr(auto_adv, "adv_setting")
    assert PlanFactProvider.get_plan_data(auto_adv) == base_plan
    assert overlay_plan.max_pay_for_order != base_plan.max_pay_for_order

    return PreComplexAdv(
        auto_adv=auto_adv,
        plan_data=overlay_plan,
        plan_fact_summary=None,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_pre_adv_persists_base_plan_not_overlay_on_write_boundary() -> None:
    """Overlay active on seed → DTO plan columns must equal base Plan (500), not scaled (1000)."""
    pre_adv = _overlay_pre_adv(base_max=500, overlay_max=1000)
    base_plan = PlanFactProvider.get_plan_data(pre_adv.auto_adv)
    assert base_plan is not None
    fact = FactData(
        predict_orders=3.0,
        original_orders=2.0,
        pay_for_order=50.0,
        fact_method=FactMethods.DIRECT_SALES,
    )

    with patch.object(
        PlanFactProvider,
        "get_plan_data",
        wraps=PlanFactProvider.get_plan_data,
    ) as get_plan_data:
        with patch.object(
            PlanFactController,
            "_resolve_fact_for_pre_adv",
            new=AsyncMock(return_value=fact),
        ):
            dto = await PlanFactController.process_pre_adv(pre_adv, version=42.0)

    assert dto is not None
    get_plan_data.assert_called_once_with(pre_adv.auto_adv)
    assert dto.plan_max_pay_for_order == base_plan.max_pay_for_order
    assert dto.plan_target_pay_for_order == base_plan.target_pay_for_order
    assert dto.plan_orders == base_plan.orders
