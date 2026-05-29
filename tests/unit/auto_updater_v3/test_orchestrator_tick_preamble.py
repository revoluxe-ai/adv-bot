"""Unit: preamble phases, campaign modes, target_place sync flags."""

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
async def test_process_adv_v3_normal_runs_preamble_when_selector_skipped_by_cache() -> None:
    complex_adv = MagicMock()
    complex_adv.adv_id = 11
    complex_adv.adv_setting = MagicMock()
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = False
    complex_adv.v3_rollout_aggressiveness = 2
    complex_adv.get_keywords = AsyncMock(return_value=[])

    dto = MagicMock()
    dto.min_target_position = 5

    bootstrap = MagicMock(return_value=[])
    expansion = MagicMock(return_value=[])
    plan_fact = MagicMock()
    plan_fact.check_equal_in_cache = AsyncMock(return_value=True)
    plan_fact.set_new_plan_fact = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator._load_v3_wb_context",
            new=AsyncMock(return_value=(dto, {})),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.build_keyword_v3_contexts",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_data_bootstrap_v3",
            bootstrap,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_profitable_expansion",
            expansion,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_cost_reallocation",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.AdvSettingAutoUpdater.get_plan_data",
            return_value=MagicMock(max_pay_for_order=100.0, orders=10, target_pay_for_order=80.0),
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
            return_value=SalesStates.OPTIMAL,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.select_v3_post_gate_actions",
        ) as select_mock,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.V3TickKeywordLedger.flush_to_db",
            new=AsyncMock(return_value=False),
        ) as flush_mock,
    ):
        updater_cls.return_value.get_fact_data = AsyncMock(
            return_value=MagicMock(pay_for_order=50.0, predict_orders=10)
        )
        await process_adv_v3(complex_adv, wb_shop_data_manager=MagicMock())

    bootstrap.assert_called_once()
    expansion.assert_called_once()
    select_mock.assert_not_called()
    flush_mock.assert_awaited_once()
    plan_fact.check_equal_in_cache.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_adv_v3_no_data_calls_bootstrap_and_sync_with_force() -> None:
    complex_adv = MagicMock()
    complex_adv.adv_id = 14
    complex_adv.adv_setting = MagicMock()
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = True
    complex_adv.v3_rollout_aggressiveness = 2
    complex_adv.get_keywords = AsyncMock(return_value=[])

    dto = MagicMock()
    bootstrap = MagicMock(return_value=[])
    keyword_bootstrap = MagicMock(return_value=[])
    sync_mock = AsyncMock()
    expansion = MagicMock(return_value=[])

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator._load_v3_wb_context",
            new=AsyncMock(return_value=(dto, {})),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_data_bootstrap_v3",
            keyword_bootstrap,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_campaign_no_data_bootstrap_safe",
            bootstrap,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_profitable_expansion",
            expansion,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.AdvSettingAutoUpdater.get_plan_data",
            return_value=MagicMock(max_pay_for_order=100.0, orders=10, target_pay_for_order=80.0),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.AdvSettingAutoUpdater"
        ) as updater_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.detect_campaign_state",
            return_value=SalesStates.NO_DATA,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.sync_keyword_target_places_v3",
            sync_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.V3TickKeywordLedger.flush_to_db",
            new=AsyncMock(return_value=False),
        ),
    ):
        updater_cls.return_value.get_fact_data = AsyncMock(
            return_value=MagicMock(pay_for_order=None, predict_orders=3.0)
        )
        await process_adv_v3(complex_adv, wb_shop_data_manager=MagicMock())

    keyword_bootstrap.assert_not_called()
    bootstrap.assert_called_once()
    expansion.assert_not_called()
    sync_mock.assert_awaited_once()
    assert sync_mock.await_args.kwargs.get("force_all_target_place_zero") is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_adv_v3_not_ready_full_stop() -> None:
    """NOT_READY: без bootstrap, realloc, selector, flush и target_place sync."""
    complex_adv = MagicMock()
    complex_adv.adv_id = 15
    complex_adv.adv_setting = MagicMock()
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = True
    complex_adv.get_keywords = AsyncMock(return_value=[])

    dto = MagicMock()
    sync_mock = AsyncMock()
    bootstrap = MagicMock(return_value=[])
    keyword_bootstrap = MagicMock(return_value=[])

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator._load_v3_wb_context",
            new=AsyncMock(return_value=(dto, {})),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.build_target_place_fallback_zero_by_keyword_id",
            return_value={},
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_data_bootstrap_v3",
            keyword_bootstrap,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_campaign_no_data_bootstrap_safe",
            bootstrap,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.AdvSettingAutoUpdater.get_plan_data",
            return_value=MagicMock(max_pay_for_order=100.0, orders=10),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.AdvSettingAutoUpdater"
        ) as updater_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.detect_campaign_state",
            return_value=None,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.sync_keyword_target_places_v3",
            sync_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.V3TickKeywordLedger.flush_to_db",
            new=AsyncMock(return_value=False),
        ) as flush_mock,
    ):
        updater_cls.return_value.get_fact_data = AsyncMock(
            return_value=MagicMock(pay_for_order=50.0, predict_orders=5.0)
        )
        await process_adv_v3(complex_adv, wb_shop_data_manager=MagicMock())

    keyword_bootstrap.assert_not_called()
    bootstrap.assert_not_called()
    sync_mock.assert_not_awaited()
    flush_mock.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_adv_v3_no_plan_full_stop() -> None:
    """plan is None → NOT_READY по умолчанию, без bootstrap и sync."""
    complex_adv = MagicMock()
    complex_adv.adv_id = 16
    complex_adv.adv_setting = MagicMock()
    complex_adv.individual_keywords_target_place_mode = True
    complex_adv.get_keywords = AsyncMock(return_value=[])

    dto = MagicMock()
    sync_mock = AsyncMock()
    keyword_bootstrap = MagicMock(return_value=[])

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator._load_v3_wb_context",
            new=AsyncMock(return_value=(dto, {})),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_data_bootstrap_v3",
            keyword_bootstrap,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.AdvSettingAutoUpdater.get_plan_data",
            return_value=None,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.sync_keyword_target_places_v3",
            sync_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.V3TickKeywordLedger.flush_to_db",
            new=AsyncMock(return_value=False),
        ) as flush_mock,
    ):
        await process_adv_v3(complex_adv, wb_shop_data_manager=MagicMock())

    keyword_bootstrap.assert_not_called()
    sync_mock.assert_not_awaited()
    flush_mock.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_adv_v3_syncs_target_place_when_plan_fact_unchanged() -> None:
    complex_adv = MagicMock()
    complex_adv.adv_id = 12
    complex_adv.adv_setting = MagicMock()
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = True
    complex_adv.v3_rollout_aggressiveness = 2
    complex_adv.get_keywords = AsyncMock(return_value=[])

    dto = MagicMock()
    dto.min_target_position = 5
    sync_mock = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator._load_v3_wb_context",
            new=AsyncMock(return_value=(dto, {"kw": []})),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.build_keyword_v3_contexts",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_data_bootstrap_v3",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_cost_reallocation",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_profitable_expansion",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.AdvSettingAutoUpdater.get_plan_data",
            return_value=MagicMock(max_pay_for_order=100.0, orders=10, target_pay_for_order=80.0),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.AdvSettingAutoUpdater"
        ) as updater_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.ChangePlanFact"
        ) as pfc_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.detect_campaign_state",
            return_value=SalesStates.OPTIMAL,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.sync_keyword_target_places_v3",
            sync_mock,
        ),
    ):
        plan_fact = MagicMock()
        plan_fact.check_equal_in_cache = AsyncMock(return_value=True)
        pfc_cls.return_value = plan_fact
        updater_cls.return_value.get_fact_data = AsyncMock(
            return_value=MagicMock(pay_for_order=50.0, predict_orders=10)
        )
        await process_adv_v3(complex_adv, wb_shop_data_manager=MagicMock())

    sync_mock.assert_awaited_once()
    assert sync_mock.await_args.kwargs.get("force_all_target_place_zero") is False
