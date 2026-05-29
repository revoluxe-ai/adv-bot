"""Unit tests: process_adv_v3 и Redis plan/fact / стоп при кампании «Н»."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator import (
    process_adv_v3,
)


@pytest.mark.asyncio
async def test_process_adv_v3_does_not_cache_plan_fact_when_state_unknown() -> None:
    complex_adv = MagicMock()
    complex_adv.adv_id = 1
    complex_adv.adv_setting = MagicMock()

    plan_fact = MagicMock()
    plan_fact.check_equal_in_cache = AsyncMock(return_value=False)
    plan_fact.set_new_plan_fact = AsyncMock()

    no_data = MagicMock(return_value=[])

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator._load_v3_wb_context",
            new=AsyncMock(return_value=(MagicMock(), {})),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_no_data_activation_v3",
            no_data,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.AdvSettingAutoUpdater.get_plan_data",
            return_value=MagicMock(),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.AdvSettingAutoUpdater"
        ) as updater_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.ChangePlanFact",
            return_value=plan_fact,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.detect_campaign_state",
            return_value=None,
        ),
    ):
        updater_cls.return_value.get_fact_data = AsyncMock(return_value=MagicMock())
        complex_adv.get_keywords = AsyncMock(return_value=[])
        complex_adv.shelf_promotion_active = False
        complex_adv.individual_keywords_target_place_mode = False
        await process_adv_v3(
            complex_adv,
            wb_shop_data_manager=MagicMock(),
        )

    plan_fact.set_new_plan_fact.assert_not_awaited()
    no_data.assert_not_called()


@pytest.mark.asyncio
async def test_process_adv_v3_does_not_cache_plan_fact_when_no_wb_dto() -> None:
    complex_adv = MagicMock()
    complex_adv.adv_id = 2
    complex_adv.adv_setting = MagicMock()
    complex_adv.shelf_promotion_active = False

    plan_fact = MagicMock()
    plan_fact.check_equal_in_cache = AsyncMock(return_value=False)
    plan_fact.set_new_plan_fact = AsyncMock()

    wb_manager = MagicMock()
    wb_manager.get_wb_advs_dto = AsyncMock(return_value=[])

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.AdvSettingAutoUpdater.get_plan_data",
            return_value=MagicMock(),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.AdvSettingAutoUpdater"
        ) as updater_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.ChangePlanFact",
            return_value=plan_fact,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.detect_campaign_state",
            return_value=MagicMock(name="UNDERPERFORM"),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.SalesStates"
        ) as sales_states,
    ):
        sales_states.OPTIMAL = MagicMock()
        updater_cls.return_value.get_fact_data = AsyncMock(return_value=MagicMock())
        complex_adv.get_keywords = AsyncMock(return_value=[])
        await process_adv_v3(
            complex_adv,
            wb_shop_data_manager=wb_manager,
        )

    plan_fact.set_new_plan_fact.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_adv_v3_skips_ladder_when_campaign_no_data() -> None:
    complex_adv = MagicMock()
    complex_adv.adv_id = 3
    complex_adv.adv_setting = MagicMock()
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = True
    complex_adv.v3_rollout_aggressiveness = 2

    dto = MagicMock()
    dto.min_target_position = 5
    no_data = MagicMock(return_value=[])
    select_mock = MagicMock(return_value=[])
    sync_mock = AsyncMock()
    plan_fact = MagicMock()
    plan_fact.check_equal_in_cache = AsyncMock(return_value=False)
    plan_fact.set_new_plan_fact = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator._load_v3_wb_context",
            new=AsyncMock(return_value=(dto, {})),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_no_data_activation_v3",
            no_data,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.select_v3_actions",
            select_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.sync_keyword_target_places_v3",
            sync_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.AdvSettingAutoUpdater.get_plan_data",
            return_value=MagicMock(max_pay_for_order=100.0, orders=10),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.AdvSettingAutoUpdater"
        ) as updater_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.ChangePlanFact",
            return_value=plan_fact,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.detect_campaign_state",
            return_value=SalesStates.NO_DATA,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.V3TickKeywordLedger.flush_to_db",
            new=AsyncMock(return_value=False),
        ),
    ):
        updater_cls.return_value.get_fact_data = AsyncMock(
            return_value=MagicMock(pay_for_order=None, predict_orders=5.0)
        )
        complex_adv.get_keywords = AsyncMock(return_value=[])
        await process_adv_v3(complex_adv, wb_shop_data_manager=MagicMock())

    no_data.assert_not_called()
    select_mock.assert_not_called()
    sync_mock.assert_not_awaited()
    plan_fact.set_new_plan_fact.assert_not_awaited()
