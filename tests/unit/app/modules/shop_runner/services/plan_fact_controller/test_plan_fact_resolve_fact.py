"""_resolve_fact_for_pre_adv: strict Redis keywords, без fallback на summary."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    PlanData,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_controller import (
    PlanFactController,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactSummary,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.pre_complex_adv import (
    PreComplexAdv,
)
from app.modules.shop_runner.required_data_miss import ShopRunnerKeywordsCacheMissError


def _pre_adv(*, summary: PlanFactSummary | None = None) -> PreComplexAdv:
    wb_cabinet = MagicMock()
    wb_cabinet.shop_id = "shop-1"
    auto_adv = MagicMock()
    auto_adv.wb_cabinet = wb_cabinet
    auto_adv.adv_id = 42
    auto_adv.sales_predict_method = FactMethods.DIRECT_SALES
    return PreComplexAdv(
        auto_adv=auto_adv,
        plan_data=PlanData(orders=10, target_pay_for_order=100, max_pay_for_order=200),
        plan_fact_summary=summary,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_fact_on_cache_miss_raises() -> None:
    summary = PlanFactSummary(
        adv_id=42,
        fact_predict_orders=5.0,
        fact_original_orders=4.0,
        fact_pay_for_order=50.0,
        fact_method="DIRECT_SALES",
    )
    pre_adv = _pre_adv(summary=summary)

    with patch(
        "app.modules.shop_runner.required_data_miss.fetch_calculated_keywords_from_redis",
        new=AsyncMock(
            side_effect=ShopRunnerKeywordsCacheMissError(
                "miss", shop_id="shop-1", adv_id=42
            )
        ),
    ):
        with pytest.raises(ShopRunnerKeywordsCacheMissError):
            await PlanFactController._resolve_fact_for_pre_adv(pre_adv)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_pre_adv_returns_none_when_no_fact() -> None:
    pre_adv = _pre_adv(summary=None)

    with patch.object(
        PlanFactController,
        "_resolve_fact_for_pre_adv",
        new=AsyncMock(return_value=None),
    ):
        assert await PlanFactController.process_pre_adv(pre_adv, version=1.0) is None
