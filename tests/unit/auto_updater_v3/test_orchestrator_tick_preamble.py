"""Unit: preamble (phase0 + target_place) до plan/fact gate, без пропусков."""

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
async def test_process_adv_v3_runs_phase0_before_plan_fact_cache_check() -> None:
    complex_adv = MagicMock()
    complex_adv.adv_id = 11
    complex_adv.adv_setting = MagicMock()
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = False
    complex_adv.v3_rollout_aggressiveness = 2
    complex_adv.get_keywords = AsyncMock(return_value=[])

    dto = MagicMock()
    dto.min_target_position = 5

    phase0 = AsyncMock(return_value=[])
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
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.run_ladder_gap_rebalance_v3",
            phase0,
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
            return_value=SalesStates.OPTIMAL,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.select_v3_actions",
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

    phase0.assert_awaited_once()
    select_mock.assert_not_called()
    flush_mock.assert_awaited_once()
    plan_fact.check_equal_in_cache.assert_awaited_once()


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
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.run_ladder_gap_rebalance_v3",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.AdvSettingAutoUpdater.get_plan_data",
            return_value=MagicMock(max_pay_for_order=100.0, orders=10),
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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_adv_v3_rebuilds_contexts_after_phase0_before_no_data() -> None:
    """После gap-rebalance in-memory контексты пересобираются до no_data."""
    from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
        V3Action,
        V3ActionType,
    )
    from tests.unit.auto_updater_v3.test_tick_ledger import _kw

    kw = _kw(ks_id=1, mode=KeywordStrategyMode.OFF, hard_status=1)
    complex_adv = MagicMock()
    complex_adv.adv_id = 13
    complex_adv.adv_setting = MagicMock()
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = False
    complex_adv.v3_rollout_aggressiveness = 2
    complex_adv.get_keywords = AsyncMock(return_value=[kw])

    dto = MagicMock()
    dto.min_target_position = 5
    build_calls: list[int] = []

    def _build_contexts(_keywords: object, _profiles: object) -> list[object]:
        build_calls.append(len(build_calls))
        return []

    phase0_action = V3Action(
        action=V3ActionType.UP,
        keyword_setting_id=1,
        target_strategy_mode=KeywordStrategyMode.MIN_CPA,
        reason="ladder_gap_rebalance_up",
    )

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator._load_v3_wb_context",
            new=AsyncMock(return_value=(dto, {})),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.build_keyword_v3_contexts",
            side_effect=_build_contexts,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.run_ladder_gap_rebalance_v3",
            new=AsyncMock(return_value=[phase0_action]),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_no_data_activation_v3",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.V3TickKeywordLedger.flush_to_db",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.AdvSettingAutoUpdater.get_plan_data",
            return_value=None,
        ),
    ):
        await process_adv_v3(complex_adv, wb_shop_data_manager=MagicMock())

    assert build_calls == [0, 1]
    assert complex_adv.get_keywords.await_count == 1
