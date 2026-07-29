"""Unit: calibration views cache helper и AND-gate plan/fact × views."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_views_cache import (
    ChangePlanFactViews,
    resolve_complex_adv_total_views,
)
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager.full_wb_adv_stat import (
    SmallFullAdvStat,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_complex_adv_total_views_sums_all_adv_ids() -> None:
    complex_adv = MagicMock()
    complex_adv.all_adv_ids = {100, 200}

    captured: dict[str, object] = {}

    async def _fake_get_stats(
        adv_ids: list[int], start: datetime, end: datetime
    ) -> SmallFullAdvStat:
        captured["adv_ids"] = adv_ids
        captured["start"] = start
        captured["end"] = end
        return SmallFullAdvStat(
            views=1500,
            clicks=0,
            spend=0.0,
            added_to_cart=0,
            orders=0,
            sum_price=0.0,
        )

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_views_cache.full_wb_adv_stat.get_stats_by_last_days",
        new=AsyncMock(side_effect=_fake_get_stats),
    ):
        views = await resolve_complex_adv_total_views(complex_adv, max_last_period=2)

    assert views == 1500
    assert set(captured["adv_ids"]) == {100, 200}  # type: ignore[arg-type]
    start = captured["start"]
    end = captured["end"]
    assert isinstance(start, datetime)
    assert isinstance(end, datetime)
    assert (end - start).days == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_complex_adv_total_views_empty_adv_ids() -> None:
    complex_adv = MagicMock()
    complex_adv.all_adv_ids = set()

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_views_cache.full_wb_adv_stat.get_stats_by_last_days",
        new=AsyncMock(),
    ) as ch_mock:
        views = await resolve_complex_adv_total_views(complex_adv)

    assert views == 0
    ch_mock.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_change_plan_fact_views_roundtrip() -> None:
    adv = MagicMock()
    adv.adv_id = 42
    cache = ChangePlanFactViews(adv)
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value="999")
    mock_client.set = AsyncMock()

    with patch.object(type(cache), "_client", new_callable=PropertyMock) as client_prop:
        client_prop.return_value = mock_client
        assert await cache.get_cached_views() == 999
        await cache.set_views(1234)
        mock_client.set.assert_awaited_once_with(cache._key, "1234")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_views_resolve_failure_defers_plan_fact_snapshot() -> None:
    """Сбой CH views: calibration/enable off, plan/fact Redis не обновляется."""
    from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
        SalesStates,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator import (
        process_adv_v3,
    )

    complex_adv = MagicMock()
    complex_adv.adv_id = 77
    complex_adv.adv_setting = MagicMock()
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = False
    complex_adv.v3_rollout_aggressiveness = 2
    complex_adv.keyword_calibration_max_step = 8
    complex_adv.get_keywords = AsyncMock(return_value=[])

    dto = MagicMock()
    plan_fact = MagicMock()
    plan_fact.check_equal_in_cache = AsyncMock(return_value=False)
    plan_fact.set_new_plan_fact = AsyncMock()
    views_cache = MagicMock()
    views_cache.get_cached_views = AsyncMock(return_value=100)
    views_cache.set_views = AsyncMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.load_v3_wb_context",
            new=AsyncMock(return_value=(dto, {})),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.AdvSettingAutoUpdater.get_plan_data",
            return_value=MagicMock(
                max_pay_for_order=100.0,
                orders=10,
                target_pay_for_order=80.0,
            ),
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
            new=AsyncMock(side_effect=RuntimeError("clickhouse unavailable")),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.detect_campaign_state",
            return_value=SalesStates.STABLE,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.cost_reallocation.RebalanceExecutor.execute",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.calibration_runner.run_calibration_up",
        ) as cal_up,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.calibration_runner.run_calibration_down",
        ) as cal_down,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.pay_for_order_gap_enable.PayForOrderGapEnableExecutor.execute",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.pay_for_order_over_max_off_on_deep_overspend.PayForOrderOverMaxOffOnDeepOverspendExecutor.execute",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.apply_manager.manager.select_v3_post_gate_actions",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.V3CalibrationStepState"
        ) as step_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger.V3TickKeywordLedger.flush_to_db",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.persist_v3_tick_report",
            new=AsyncMock(),
        ),
        # Isolate views-gate body from CardAbHold ENTER interrupt Redis (DI Provide /
        # closed loop). Same target as tests/unit/auto_updater_v3/conftest.py
        # for test_orchestrator*; this nodeid is outside that autouse filter.
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "orchestrator.abort_ordinary_v3_if_enter_signaled",
            new=AsyncMock(return_value=False),
        ),
    ):
        step_cls.return_value.get_state = AsyncMock(return_value=None)
        step_cls.return_value.set_state = AsyncMock()
        updater_cls.return_value.get_fact_data = AsyncMock(
            return_value=MagicMock(pay_for_order=85.0, predict_orders=10)
        )
        await process_adv_v3(complex_adv, wb_shop_data_manager=MagicMock())

    cal_up.assert_not_called()
    cal_down.assert_not_called()
    plan_fact.set_new_plan_fact.assert_not_awaited()
    views_cache.set_views.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_change_plan_fact_views_missing_key() -> None:
    adv = MagicMock()
    adv.adv_id = 43
    cache = ChangePlanFactViews(adv)
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=None)

    with patch.object(type(cache), "_client", new_callable=PropertyMock) as client_prop:
        client_prop.return_value = mock_client
        assert await cache.get_cached_views() is None
