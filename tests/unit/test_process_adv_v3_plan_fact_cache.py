"""Unit tests: process_adv_v3 обновляет Redis plan/fact при раннем выходе."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator import (
    process_adv_v3,
)


@pytest.mark.asyncio
async def test_process_adv_v3_caches_plan_fact_when_state_unknown() -> None:
    complex_adv = MagicMock()
    complex_adv.adv_id = 1
    complex_adv.adv_setting = MagicMock()

    plan_fact = MagicMock()
    plan_fact.check_equal_in_cache = AsyncMock(return_value=False)
    plan_fact.set_new_plan_fact = AsyncMock()

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
            return_value=None,
        ),
    ):
        updater_cls.return_value.get_fact_data = AsyncMock(return_value=MagicMock())
        complex_adv.get_keywords = AsyncMock(return_value=[])
        await process_adv_v3(
            complex_adv,
            wb_shop_data_manager=MagicMock(),
        )

    plan_fact.set_new_plan_fact.assert_awaited_once()


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
