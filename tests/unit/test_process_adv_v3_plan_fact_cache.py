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

_ORCH = "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator"
_DM = "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager"
_AM = "app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager"
_TC = "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.tick_context"
_UP = "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors"
_NDA = "app.modules.shop_runner.service_manager.services.auto_updater_v3.no_data_activation"
_RP = "app.modules.shop_runner.service_manager.services.auto_updater_v3.resolve_threshold"
_TL = "app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger"
_V3_CPO = "app.modules.shop_runner.service_manager.services.v3_point_order_cpo"
_AB_HOLD_INTERRUPT = (
    "app.modules.shop_runner.service_manager.services.auto_updater_v3."
    "orchestrator.abort_ordinary_v3_if_enter_signaled"
)


@pytest.fixture(autouse=True)
def _stub_card_ab_hold_interrupt() -> None:
    """card-ab-hold-mode: файл вне auto_updater_v3/conftest — stub Redis interrupt."""
    with patch(_AB_HOLD_INTERRUPT, new=AsyncMock(return_value=False)):
        yield


def _start_patches(patch_map: dict[str, object]) -> list:
    patchers = [patch(target, new=val) for target, val in patch_map.items()]
    for p in patchers:
        p.start()
    return patchers


def _stop_patches(patchers: list) -> None:
    for p in patchers:
        p.stop()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_adv_v3_does_not_cache_plan_fact_when_state_unknown() -> None:
    """state=None → no plan/fact Redis cache; no live CH via CPO loader."""
    complex_adv = MagicMock()
    complex_adv.adv_id = 1
    complex_adv.adv_setting = MagicMock()
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = False

    plan_fact = MagicMock()
    plan_fact.check_equal_in_cache = AsyncMock(return_value=False)
    plan_fact.set_new_plan_fact = AsyncMock()

    bootstrap = MagicMock(return_value=[])

    updater_cls = MagicMock()
    updater_cls.return_value.get_fact_data = AsyncMock(return_value=MagicMock())
    patchers = _start_patches(
        {
            f"{_DM}.load_v3_wb_context": AsyncMock(return_value=(MagicMock(), {})),
            # Early-path CH: DataUpdateManager always loads CPO when dto+plan set.
            f"{_V3_CPO}.load_campaign_orders_per_cart_7d": AsyncMock(return_value=None),
            f"{_ORCH}.plan_campaign_no_data_bootstrap_safe": bootstrap,
            f"{_DM}.AdvSettingAutoUpdater.get_plan_data": lambda *a, **k: MagicMock(),
            f"{_DM}.AdvSettingAutoUpdater": updater_cls,
            f"{_DM}.ChangePlanFact": lambda *a, **k: plan_fact,
            f"{_DM}.detect_campaign_state": lambda *a, **k: None,
            f"{_TL}.V3TickKeywordLedger.flush_to_db": AsyncMock(return_value=False),
            f"{_ORCH}.persist_v3_tick_report": AsyncMock(),
        }
    )
    try:
        complex_adv.get_keywords = AsyncMock(return_value=[])
        await process_adv_v3(
            complex_adv,
            wb_shop_data_manager=MagicMock(),
        )
    finally:
        _stop_patches(patchers)

    plan_fact.set_new_plan_fact.assert_not_awaited()
    bootstrap.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_adv_v3_caches_plan_fact_and_views_each_normal_tick() -> None:
    """NORMAL + dto: snapshot plan/fact и views в конце каждого тика."""
    complex_adv = MagicMock()
    complex_adv.adv_id = 4
    complex_adv.adv_setting = MagicMock()
    complex_adv.adv_setting.name = "Test"
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = False
    complex_adv.v3_rollout_aggressiveness = 2
    complex_adv.keyword_calibration_max_step = 8
    complex_adv.rec_system_promotion_mode_active = False

    dto = MagicMock()
    dto.min_target_position = 5

    plan_fact = MagicMock()
    plan_fact.check_equal_in_cache = AsyncMock(return_value=False)
    plan_fact.set_new_plan_fact = AsyncMock()
    views_cache = MagicMock()
    views_cache.get_cached_views = AsyncMock(return_value=50)
    views_cache.set_views = AsyncMock()
    step_cache = MagicMock()
    step_cache.get_state = AsyncMock(return_value=None)
    step_cache.set_state = AsyncMock()

    updater_cls = MagicMock()
    updater_cls.return_value.get_fact_data = AsyncMock(
        return_value=MagicMock(pay_for_order=50.0, predict_orders=10)
    )
    patchers = _start_patches(
        {
            f"{_DM}.load_v3_wb_context": AsyncMock(return_value=(dto, {})),
            f"{_V3_CPO}.load_campaign_orders_per_cart_7d": AsyncMock(return_value=None),
            f"{_V3_CPO}.load_rec_orders_per_view_for_v3": AsyncMock(return_value=None),
            f"{_UP}.cost_reallocation.RebalanceExecutor.execute": lambda *a, **k: None,
            f"{_UP}.pay_for_order_gap_enable.PayForOrderGapEnableExecutor.execute": lambda *a, **k: None,
            f"{_UP}.pay_for_order_over_max_off_on_deep_overspend.PayForOrderOverMaxOffOnDeepOverspendExecutor.execute": lambda *a, **k: None,
            f"{_UP}.resolve_calibration.ResolveCalibrationExecutor.execute": lambda *a, **k: None,
            f"{_RP}.is_resolve_valid": lambda *a, **k: True,
            f"{_RP}.compute_resolve_cost_threshold": lambda *a, **k: 90.0,
            f"{_AM}.select_v3_post_gate_actions": lambda *a, **k: [],
            f"{_DM}.AdvSettingAutoUpdater.get_plan_data": lambda *a, **k: MagicMock(
                max_pay_for_order=100.0, orders=10, target_pay_for_order=80.0
            ),
            f"{_DM}.AdvSettingAutoUpdater": updater_cls,
            f"{_DM}.ChangePlanFact": lambda *a, **k: plan_fact,
            f"{_DM}.ChangePlanFactViews": lambda *a, **k: views_cache,
            f"{_DM}.V3CalibrationStepState": lambda *a, **k: step_cache,
            f"{_DM}.resolve_complex_adv_total_views": AsyncMock(return_value=777),
            f"{_DM}.detect_campaign_state": lambda *a, **k: SalesStates.OPTIMAL,
            f"{_TL}.V3TickKeywordLedger.flush_to_db": AsyncMock(return_value=False),
            f"{_ORCH}.persist_v3_tick_report": AsyncMock(),
        }
    )
    try:
        complex_adv.get_keywords = AsyncMock(return_value=[])
        await process_adv_v3(complex_adv, wb_shop_data_manager=MagicMock())
    finally:
        _stop_patches(patchers)

    plan_fact.set_new_plan_fact.assert_awaited_once()
    views_cache.set_views.assert_awaited_once_with(777)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_adv_v3_does_not_cache_plan_fact_when_no_wb_dto() -> None:
    complex_adv = MagicMock()
    complex_adv.adv_id = 2
    complex_adv.adv_setting = MagicMock()
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = False
    complex_adv.v3_rollout_aggressiveness = 2

    plan_fact = MagicMock()
    plan_fact.check_equal_in_cache = AsyncMock(return_value=False)
    plan_fact.set_new_plan_fact = AsyncMock()

    with (
        patch(
            f"{_DM}.load_v3_wb_context",
            new=AsyncMock(return_value=(None, {})),
        ),
        patch(
            f"{_DM}.AdvSettingAutoUpdater.get_plan_data",
            return_value=MagicMock(),
        ),
        patch(
            f"{_DM}.AdvSettingAutoUpdater",
        ) as updater_cls,
        patch(
            f"{_DM}.ChangePlanFact",
            return_value=plan_fact,
        ),
        patch(
            f"{_DM}.detect_campaign_state",
            return_value=SalesStates.UNDERPERFORM,
        ),
    ):
        updater_cls.return_value.get_fact_data = AsyncMock(return_value=MagicMock())
        complex_adv.get_keywords = AsyncMock(return_value=[])
        await process_adv_v3(
            complex_adv,
            wb_shop_data_manager=MagicMock(),
        )

    plan_fact.set_new_plan_fact.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_adv_v3_no_data_bootstrap_only_no_selector() -> None:
    """NO_DATA: bootstrap + ApplyManager; post-gate selector вызывается, NORMAL pipeline — нет."""
    complex_adv = MagicMock()
    complex_adv.adv_id = 3
    complex_adv.adv_setting = MagicMock()
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = True
    complex_adv.v3_rollout_aggressiveness = 2

    dto = MagicMock()
    bootstrap = MagicMock(return_value=[])
    select_mock = MagicMock(return_value=[])
    sync_mock = AsyncMock()
    plan_fact = MagicMock()
    plan_fact.check_equal_in_cache = AsyncMock(return_value=False)
    plan_fact.set_new_plan_fact = AsyncMock()

    updater_cls = MagicMock()
    updater_cls.return_value.get_fact_data = AsyncMock(
        return_value=MagicMock(pay_for_order=None, predict_orders=5.0)
    )
    patchers = _start_patches(
        {
            f"{_DM}.load_v3_wb_context": AsyncMock(return_value=(dto, {})),
            f"{_V3_CPO}.load_campaign_orders_per_cart_7d": AsyncMock(return_value=None),
            f"{_ORCH}.plan_campaign_no_data_bootstrap_safe": bootstrap,
            f"{_AM}.select_v3_post_gate_actions": select_mock,
            f"{_AM}.sync_keyword_target_places_v3": sync_mock,
            f"{_DM}.AdvSettingAutoUpdater.get_plan_data": lambda *a, **k: MagicMock(
                max_pay_for_order=100.0, orders=10, target_pay_for_order=80.0
            ),
            f"{_DM}.AdvSettingAutoUpdater": updater_cls,
            f"{_DM}.ChangePlanFact": lambda *a, **k: plan_fact,
            f"{_DM}.detect_campaign_state": lambda *a, **k: SalesStates.NO_DATA,
            f"{_TL}.V3TickKeywordLedger.flush_to_db": AsyncMock(return_value=False),
            f"{_ORCH}.persist_v3_tick_report": AsyncMock(),
            f"{_ORCH}.persist_v3_keyword_changes": AsyncMock(),
            f"{_ORCH}.persist_keyword_decision_trace": AsyncMock(),
        }
    )
    try:
        complex_adv.get_keywords = AsyncMock(return_value=[])
        await process_adv_v3(complex_adv, wb_shop_data_manager=MagicMock())
    finally:
        _stop_patches(patchers)

    bootstrap.assert_called_once()
    select_mock.assert_called_once()
    sync_mock.assert_awaited_once()
    assert sync_mock.await_args.kwargs.get("force_all_target_place_zero") is True
    plan_fact.set_new_plan_fact.assert_not_awaited()
