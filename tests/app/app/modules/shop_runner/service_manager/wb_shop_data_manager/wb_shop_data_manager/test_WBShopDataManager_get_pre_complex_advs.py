"""Unit-тесты WBShopDataManager.get_pre_complex_advs: синтетический суточный бюджет."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    PlanData,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.pre_complex_adv import (
    PreComplexAdv,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager import (
    WBShopDataManager,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_WBShopDataManager_get_pre_complex_advs_raise_sintetic_max_cpo() -> None:
    """При auto_common_budget синтетический суточный лимит = max_pay_for_order * plan_for_sales_for_day."""
    wb_cabinet = MagicMock()
    wb_cabinet.shop_id = "shop-1"
    manager = WBShopDataManager(
        wb_cabinet=wb_cabinet,
        tasks_manager=None,
        wb_api_data_manager=MagicMock(),
        wb_manager=MagicMock(),
    )

    adv = MagicMock()
    adv.id = 10
    adv.adv_id = 111
    adv.nmids = [1]
    adv.search_adv_id = None
    adv.auto_common_budget = True
    adv.max_price_for_order = 600
    adv.plan_for_sales_for_day = 7
    adv.common_budget_daily_limit = 0

    manager._get_active_advs = AsyncMock(return_value=[adv])

    plan_data = PlanData(
        orders=7,
        target_pay_for_order=450,
        max_pay_for_order=600,
    )

    with (
        patch(
            "app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager.PlanFactProvider.get_plan_data",
            return_value=plan_data,
        ),
        patch(
            "app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager.PlanFactReader.get_latest_plan_facts",
            new=AsyncMock(return_value={}),
        ),
    ):
        pre_advs = await manager.get_pre_complex_advs()

    assert len(pre_advs) == 1
    pre_adv = pre_advs[0]
    assert isinstance(pre_adv, PreComplexAdv)
    assert pre_adv.auto_adv is adv
    assert pre_adv.adv_id == 111
    assert pre_adv.plan_data == plan_data
    assert adv.common_budget_daily_limit == 600 * 7
