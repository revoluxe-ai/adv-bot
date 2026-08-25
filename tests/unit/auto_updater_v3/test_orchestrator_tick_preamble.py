"""Unit: preamble phases, campaign modes, target_place sync flags."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fakeredis.aioredis import FakeRedis

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.intent import (
    EmptyKeywordsPauseIntentManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    build_target_place_fallback_zero_by_keyword_id,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator import (
    process_adv_v3,
)
from tests.unit.auto_updater_v3.test_no_data_activation import _kw


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_adv_v3_normal_runs_preamble_and_selector_when_plan_fact_cache_equal() -> None:
    complex_adv = MagicMock()
    complex_adv.adv_id = 11
    complex_adv.adv_setting = MagicMock()
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = False
    complex_adv.v3_rollout_aggressiveness = 2
    complex_adv.keyword_calibration_max_step = 8
    complex_adv.get_keywords = AsyncMock(return_value=[])

    dto = MagicMock()
    dto.min_target_position = 5
    plan_fact = MagicMock()
    plan_fact.check_equal_in_cache = AsyncMock(return_value=True)
    plan_fact.set_new_plan_fact = AsyncMock()
    views_cache = MagicMock()
    views_cache.get_cached_views = AsyncMock(return_value=500)
    views_cache.set_views = AsyncMock()
    step_cache = MagicMock()
    step_cache.get_state = AsyncMock(return_value=None)
    step_cache.set_state = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.load_v3_wb_context",
            new=AsyncMock(return_value=(dto, {})),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.build_keyword_v3_contexts",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.cost_reallocation.RebalanceExecutor.execute",
            return_value=[],
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
            return_value=views_cache,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.resolve_complex_adv_total_views",
            new=AsyncMock(return_value=500),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.V3CalibrationStepState",
            return_value=step_cache,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.detect_campaign_state",
            return_value=SalesStates.OPTIMAL,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager.select_v3_post_gate_actions",
        ) as select_mock,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger.V3TickKeywordLedger.flush_to_db",
            new=AsyncMock(return_value=False),
        ) as flush_mock,
    ):
        updater_cls.return_value.get_fact_data = AsyncMock(
            return_value=MagicMock(pay_for_order=50.0, predict_orders=10)
        )
        await process_adv_v3(complex_adv, wb_shop_data_manager=MagicMock())
    select_mock.assert_called_once()
    flush_mock.assert_awaited_once()
    plan_fact.check_equal_in_cache.assert_awaited_once()
    plan_fact.set_new_plan_fact.assert_awaited_once()
    views_cache.set_views.assert_awaited_once_with(500)
    # plan/fact и views unchanged → calibration gate закрыт → Redis step сбрасывается
    step_cache.set_state.assert_awaited_once()
    saved = step_cache.set_state.await_args[0][0]
    assert saved.effective_steps == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_adv_v3_no_data_calls_bootstrap_and_sync_with_force() -> None:
    complex_adv = MagicMock()
    complex_adv.adv_id = 14
    complex_adv.adv_setting = MagicMock()
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = True
    complex_adv.v3_rollout_aggressiveness = 2
    complex_adv.keyword_calibration_max_step = 8
    complex_adv.get_keywords = AsyncMock(return_value=[])

    dto = MagicMock()
    bootstrap = MagicMock(return_value=[])
    keyword_bootstrap = MagicMock(return_value=[])
    sync_mock = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.load_v3_wb_context",
            new=AsyncMock(return_value=(dto, {})),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_campaign_no_data_bootstrap_safe",
            bootstrap,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.AdvSettingAutoUpdater.get_plan_data",
            return_value=MagicMock(max_pay_for_order=100.0, orders=10, target_pay_for_order=80.0),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.AdvSettingAutoUpdater"
        ) as updater_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.detect_campaign_state",
            return_value=SalesStates.NO_DATA,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager.sync_keyword_target_places_v3",
            sync_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger.V3TickKeywordLedger.flush_to_db",
            new=AsyncMock(return_value=False),
        ) as flush_mock,
    ):
        updater_cls.return_value.get_fact_data = AsyncMock(
            return_value=MagicMock(pay_for_order=None, predict_orders=3.0)
        )
        await process_adv_v3(complex_adv, wb_shop_data_manager=MagicMock())

    keyword_bootstrap.assert_not_called()
    bootstrap.assert_called_once()
    flush_mock.assert_awaited_once()
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
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.load_v3_wb_context",
            new=AsyncMock(return_value=(dto, {})),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility.build_target_place_fallback_zero_by_keyword_id",
            return_value={},
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_campaign_no_data_bootstrap_safe",
            bootstrap,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.AdvSettingAutoUpdater.get_plan_data",
            return_value=MagicMock(max_pay_for_order=100.0, orders=10),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.AdvSettingAutoUpdater"
        ) as updater_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.detect_campaign_state",
            return_value=None,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager.sync_keyword_target_places_v3",
            sync_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger.V3TickKeywordLedger.flush_to_db",
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
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.load_v3_wb_context",
            new=AsyncMock(return_value=(dto, {})),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.AdvSettingAutoUpdater.get_plan_data",
            return_value=None,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager.sync_keyword_target_places_v3",
            sync_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger.V3TickKeywordLedger.flush_to_db",
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
    complex_adv.keyword_calibration_max_step = 8
    complex_adv.get_keywords = AsyncMock(return_value=[])

    dto = MagicMock()
    dto.min_target_position = 5
    sync_mock = AsyncMock()
    build_fallback = MagicMock(return_value={42: True})

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.load_v3_wb_context",
            new=AsyncMock(return_value=(dto, {"kw": []})),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.build_keyword_v3_contexts",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility.build_target_place_fallback_zero_by_keyword_id",
            build_fallback,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.build_target_place_fallback_zero_by_keyword_id",
            build_fallback,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.build_target_place_fallback_zero_by_keyword_id",
            build_fallback,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.v3_point_order_cpo.load_campaign_orders_per_cart_7d",
            new=AsyncMock(return_value=2.0),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.cost_reallocation.RebalanceExecutor.execute",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.AdvSettingAutoUpdater.get_plan_data",
            return_value=MagicMock(max_pay_for_order=100.0, orders=10, target_pay_for_order=80.0),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.AdvSettingAutoUpdater"
        ) as updater_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.ChangePlanFact"
        ) as pfc_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.ChangePlanFactViews"
        ) as views_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.resolve_complex_adv_total_views",
            new=AsyncMock(return_value=100),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.V3CalibrationStepState",
        ) as step_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.detect_campaign_state",
            return_value=SalesStates.OPTIMAL,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager.sync_keyword_target_places_v3",
            sync_mock,
        ),
    ):
        plan_fact = MagicMock()
        plan_fact.check_equal_in_cache = AsyncMock(return_value=True)
        plan_fact.set_new_plan_fact = AsyncMock()
        pfc_cls.return_value = plan_fact
        views_cache = MagicMock()
        views_cache.get_cached_views = AsyncMock(return_value=100)
        views_cache.set_views = AsyncMock()
        views_cls.return_value = views_cache
        step_cls.return_value.get_state = AsyncMock(return_value=None)
        step_cls.return_value.set_state = AsyncMock()
        updater_cls.return_value.get_fact_data = AsyncMock(
            return_value=MagicMock(pay_for_order=50.0, predict_orders=10)
        )
        await process_adv_v3(complex_adv, wb_shop_data_manager=MagicMock())

    assert build_fallback.call_count >= 2
    _args, fb_kwargs = build_fallback.call_args
    assert fb_kwargs.get("campaign_orders_per_cart_7d") == 2.0
    sync_mock.assert_awaited_once()
    assert sync_mock.await_args.kwargs.get("force_all_target_place_zero") is False
    assert (
        sync_mock.await_args.kwargs.get("target_place_fallback_zero_by_keyword_id")
        == {42: True}
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_guard_rebuilds_sync_fallback_after_force_off(
    fake_redis: FakeRedis,
) -> None:
    """После MAX_CPA_GUARD пересобирается fallback-map; OFF NO_CH не force 0 в sync.

    ApplyManager после FORCE_OFF может писать empty-keywords intent в Redis —
    unit изолирует это через fakeredis на ``EmptyKeywordsPauseIntentManager._client``.
    """
    kw = _kw(
        ks_id=10,
        text="expensive no ch",
        mode=KeywordStrategyMode.MIN_CPA,
        hard_status=2,
        conv=0.08,
        cpm_set_bid=510,
    )
    assert kw.pay_for_order is not None

    complex_adv = MagicMock()
    complex_adv.adv_id = 99
    complex_adv.adv_setting = MagicMock()
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = True
    complex_adv.v3_rollout_aggressiveness = 2
    complex_adv.keyword_calibration_max_step = 8
    complex_adv.get_keywords = AsyncMock(return_value=[kw])

    dto = MagicMock()
    dto.min_target_position = 5
    sync_mock = AsyncMock()
    guard_action = V3Action(
        action=V3ActionType.FORCE_OFF,
        keyword_setting_id=10,
        reason="max_cpa_guard_test",
    )
    build_fallback = MagicMock(wraps=build_target_place_fallback_zero_by_keyword_id)

    with (
        patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.load_v3_wb_context",
            new=AsyncMock(return_value=(dto, {})),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.cost_reallocation.RebalanceExecutor.execute",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility.build_target_place_fallback_zero_by_keyword_id",
            build_fallback,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.build_target_place_fallback_zero_by_keyword_id",
            build_fallback,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.build_target_place_fallback_zero_by_keyword_id",
            build_fallback,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.v3_point_order_cpo.load_campaign_orders_per_cart_7d",
            new=AsyncMock(return_value=2.0),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.AdvSettingAutoUpdater.get_plan_data",
            return_value=MagicMock(
                max_pay_for_order=100.0, orders=10, target_pay_for_order=80.0
            ),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.AdvSettingAutoUpdater"
        ) as updater_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.ChangePlanFact"
        ) as pfc_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.ChangePlanFactViews",
        ) as views_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.resolve_complex_adv_total_views",
            new=AsyncMock(return_value=100),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.detect_campaign_state",
            return_value=SalesStates.OPTIMAL,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager.select_v3_post_gate_actions",
            return_value=[guard_action],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.V3CalibrationStepState",
        ) as step_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager.sync_keyword_target_places_v3",
            sync_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger.V3TickKeywordLedger.flush_to_db",
            new=AsyncMock(return_value=False),
        ),
    ):
        plan_fact = MagicMock()
        plan_fact.check_equal_in_cache = AsyncMock(return_value=True)
        plan_fact.set_new_plan_fact = AsyncMock()
        pfc_cls.return_value = plan_fact
        views_cache = MagicMock()
        views_cache.get_cached_views = AsyncMock(return_value=100)
        views_cache.set_views = AsyncMock()
        views_cls.return_value = views_cache
        step_cls.return_value.get_state = AsyncMock(return_value=None)
        step_cls.return_value.set_state = AsyncMock()
        updater_cls.return_value.get_fact_data = AsyncMock(
            return_value=MagicMock(pay_for_order=150.0, predict_orders=10.0)
        )
        await process_adv_v3(complex_adv, wb_shop_data_manager=MagicMock())

    assert build_fallback.call_count >= 2
    fallback_map = sync_mock.await_args.kwargs[
        "target_place_fallback_zero_by_keyword_id"
    ]
    assert fallback_map is not None
    assert fallback_map.get(10) is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_adv_v3_finally_sync_uses_early_fallback_on_preamble_error() -> None:
    """При исключении в NORMAL preamble finally sync сохраняет NO_CH fallback."""
    complex_adv = MagicMock()
    complex_adv.adv_id = 100
    complex_adv.adv_setting = MagicMock()
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = True
    complex_adv.v3_rollout_aggressiveness = 2
    complex_adv.keyword_calibration_max_step = 8
    complex_adv.get_keywords = AsyncMock(return_value=[])

    dto = MagicMock()
    dto.min_target_position = 5
    sync_mock = AsyncMock()
    build_fallback = MagicMock(return_value={99: True})

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.load_v3_wb_context",
            new=AsyncMock(return_value=(dto, {})),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.build_keyword_v3_contexts",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility.build_target_place_fallback_zero_by_keyword_id",
            build_fallback,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.build_target_place_fallback_zero_by_keyword_id",
            build_fallback,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.build_target_place_fallback_zero_by_keyword_id",
            build_fallback,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.v3_point_order_cpo.load_campaign_orders_per_cart_7d",
            new=AsyncMock(return_value=2.0),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.AdvSettingAutoUpdater.get_plan_data",
            return_value=MagicMock(
                max_pay_for_order=100.0, orders=10, target_pay_for_order=80.0
            ),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.AdvSettingAutoUpdater"
        ) as updater_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.detect_campaign_state",
            return_value=SalesStates.OPTIMAL,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.ChangePlanFact"
        ) as pfc_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.ChangePlanFactViews"
        ) as views_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.resolve_complex_adv_total_views",
            new=AsyncMock(return_value=100),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.V3CalibrationStepState",
        ) as step_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view.LadderInputs.from_contexts",
            side_effect=RuntimeError("preamble boom"),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager.sync_keyword_target_places_v3",
            sync_mock,
        ),
    ):
        plan_fact = MagicMock()
        plan_fact.check_equal_in_cache = AsyncMock(return_value=False)
        pfc_cls.return_value = plan_fact
        views_cache = MagicMock()
        views_cache.get_cached_views = AsyncMock(return_value=None)
        views_cls.return_value = views_cache
        step_cls.return_value.get_state = AsyncMock(return_value=None)
        updater_cls.return_value.get_fact_data = AsyncMock(
            return_value=MagicMock(pay_for_order=50.0, predict_orders=10.0)
        )
        with pytest.raises(RuntimeError, match="preamble boom"):
            await process_adv_v3(complex_adv, wb_shop_data_manager=MagicMock())

    build_fallback.assert_called_once()
    sync_mock.assert_awaited_once()
    assert (
        sync_mock.await_args.kwargs.get("target_place_fallback_zero_by_keyword_id")
        == {99: True}
    )
