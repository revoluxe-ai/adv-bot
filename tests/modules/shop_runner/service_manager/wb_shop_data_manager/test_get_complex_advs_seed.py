from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    PlanData,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactSummary,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager import (
    WBShopDataManager,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_complex_advs_prefills_target_pay_for_order_from_seed() -> None:
    wb_cabinet = MagicMock()
    wb_cabinet.shop_id = "shop-1"
    manager = WBShopDataManager(
        wb_cabinet=wb_cabinet,
        tasks_manager=None,
        wb_api_data_manager=MagicMock(),
        wb_manager=MagicMock(),
    )

    adv1 = MagicMock()
    adv1.id = 10
    adv1.adv_id = 111
    adv1.nmids = [1]
    adv1.search_adv_id = None
    adv1.rec_system_mode = False

    adv2 = MagicMock()
    adv2.id = 20
    adv2.adv_id = 222
    adv2.nmids = [2]
    adv2.search_adv_id = None
    adv2.rec_system_mode = False

    manager._get_active_advs = AsyncMock(return_value=[adv1, adv2])
    manager._WBShopDataManager__get_adv_id_to_search_adv_map = AsyncMock(return_value={})
    manager._traffic_clicks_manager.enrich = AsyncMock(return_value=None)
    manager._get_min_bids = AsyncMock(return_value=None)

    plans = [
        PlanData(orders=100, target_pay_for_order=500, max_pay_for_order=800),
        PlanData(orders=100, target_pay_for_order=700, max_pay_for_order=900),
    ]
    summaries = {
        111: PlanFactSummary(
            adv_id=111,
            plan_orders=100,
            plan_target_pay_for_order=500,
            plan_max_pay_for_order=800,
            fact_predict_orders=120.0,
            fact_pay_for_order=450.0,
        ),
        # Для второй РК summary нет: факт как 0 заказов → план не выполнен → max_pay_for_order.
    }

    with (
        patch(
            "app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager.PlanFactProvider.get_plan_data",
            side_effect=plans,
        ),
        patch(
            "app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager.PlanFactReader.get_latest_plan_facts",
            new=AsyncMock(return_value=summaries),
        ),
    ):
        complex_advs = await manager.get_complex_advs()

    assert len(complex_advs) == 2
    by_adv_id = {adv.adv_id: adv for adv in complex_advs}
    assert by_adv_id[111].target_pay_for_order == 500.0
    assert by_adv_id[222].target_pay_for_order == 900.0
