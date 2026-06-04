"""Unit: один fetch bid profiles за полный цикл process_adv_v3."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator import (
    process_adv_v3,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_adv_v3_fetches_bid_profiles_once() -> None:
    complex_adv = MagicMock()
    complex_adv.adv_id = 10
    complex_adv.adv_setting = MagicMock()
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = False
    complex_adv.v3_rollout_aggressiveness = 2
    complex_adv.get_keywords = AsyncMock(return_value=[])

    dto = MagicMock()
    dto.min_target_position = 5

    predictor = MagicMock()
    predictor.get_keyword_bid_profiles = AsyncMock(return_value={"kw": []})

    wb_manager = MagicMock()
    wb_manager.get_wb_advs_dto = AsyncMock(return_value=[dto])

    plan_fact = MagicMock()
    plan_fact.check_equal_in_cache = AsyncMock(return_value=False)
    plan_fact.set_new_plan_fact = AsyncMock()

    state = MagicMock()
    state.name = "UNDERPERFORM"

    load_ctx = AsyncMock(return_value=(dto, {"kw": []}))

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.load_v3_wb_context",
            new=load_ctx,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.AdvSettingAutoUpdater.get_plan_data",
            return_value=MagicMock(max_pay_for_order=100.0, orders=10, target_pay_for_order=80.0),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.AdvSettingAutoUpdater"
        ) as updater_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.ChangePlanFact",
            return_value=plan_fact,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.ChangePlanFactViews",
        ) as views_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.V3CalibrationStepState",
        ) as step_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.resolve_complex_adv_total_views",
            new=AsyncMock(return_value=100),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.pay_for_order_gap_enable.PayForOrderGapEnableExecutor.execute",
            return_value=None,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.resolve_calibration.ResolveCalibrationExecutor.execute",
            return_value=None,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.detect_campaign_state",
            return_value=SalesStates.UNDERPERFORM,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.cost_reallocation.RebalanceExecutor.execute",
            return_value=None,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager.select_v3_post_gate_actions",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger.V3TickKeywordLedger.flush_to_db",
            new=AsyncMock(return_value=False),
        ),
    ):
        views_cls.return_value.get_cached_views = AsyncMock(return_value=100)
        views_cls.return_value.set_views = AsyncMock()
        step_cls.return_value.get_state = AsyncMock(return_value=None)
        step_cls.return_value.set_state = AsyncMock()
        updater_cls.return_value.get_fact_data = AsyncMock(
            return_value=MagicMock(pay_for_order=50.0, predict_orders=5)
        )
        await process_adv_v3(complex_adv, wb_shop_data_manager=wb_manager)

    load_ctx.assert_awaited_once()
