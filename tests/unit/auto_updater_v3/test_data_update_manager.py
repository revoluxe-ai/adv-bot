"""Unit: DataUpdateManager."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager import (
    DataUpdateManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_campaign_mode import (
    CampaignMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report import (
    V3TickReportCollector,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_builds_tick_input_for_normal() -> None:
    """NORMAL: ``tick_input`` с plan/fact и gates заполнен."""
    complex_adv = MagicMock()
    complex_adv.adv_id = 1
    complex_adv.adv_setting = MagicMock()
    complex_adv.shelf_promotion_active = False
    complex_adv.v3_rollout_aggressiveness = 2
    complex_adv.rec_system_promotion_mode_active = False
    complex_adv.keyword_calibration_max_step = 8
    complex_adv.get_keywords = AsyncMock(return_value=[])

    plan = MagicMock(max_pay_for_order=100, orders=10, target_pay_for_order=80)
    fact = MagicMock(pay_for_order=50.0, predict_orders=10.0)
    dto = MagicMock()

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.load_v3_wb_context",
            new=AsyncMock(return_value=(dto, {})),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.AdvSettingAutoUpdater.get_plan_data",
            return_value=plan,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.AdvSettingAutoUpdater"
        ) as updater_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.resolve_v3_fact_data",
            new=AsyncMock(return_value=(fact, "dto")),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.detect_campaign_state",
            return_value=SalesStates.OPTIMAL,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.prepare_v3_operable_ladder_contexts",
            return_value=([], []),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.build_keyword_v3_contexts",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.v3_point_order_cpo.load_campaign_orders_per_cart_7d",
            new=AsyncMock(return_value=2.0),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.v3_point_order_cpo.load_rec_orders_per_view_for_v3",
            new=AsyncMock(return_value=0.01),
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
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.V3CalibrationStepState"
        ) as step_cls,
    ):
        pfc = MagicMock()
        pfc.check_equal_in_cache = AsyncMock(return_value=True)
        pfc_cls.return_value = pfc
        views = MagicMock()
        views.get_cached_views = AsyncMock(return_value=100)
        views_cls.return_value = views
        step = MagicMock()
        step.get_state = AsyncMock(return_value=None)
        step_cls.return_value = step
        updater_cls.return_value.get_fact_data = AsyncMock(return_value=fact)

        tick_data = await DataUpdateManager().load(
            complex_adv,
            wb_shop_data_manager=MagicMock(),
            tick_report=V3TickReportCollector(),
        )

    assert tick_data.campaign_mode == CampaignMode.NORMAL
    assert tick_data.tick_input is not None
    assert tick_data.tick_input.fact is fact
    assert tick_data.fact_source == "dto"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_not_ready_without_plan() -> None:
    """Без plan — ``NOT_READY``, ``tick_input`` None."""
    complex_adv = MagicMock()
    complex_adv.adv_id = 2
    complex_adv.adv_setting = MagicMock()
    complex_adv.get_keywords = AsyncMock(return_value=[])

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.load_v3_wb_context",
            new=AsyncMock(return_value=(None, {})),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.AdvSettingAutoUpdater.get_plan_data",
            return_value=None,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.manager.build_keyword_v3_contexts",
            return_value=[],
        ),
    ):
        tick_data = await DataUpdateManager().load(
            complex_adv,
            wb_shop_data_manager=MagicMock(),
            tick_report=V3TickReportCollector(),
        )

    assert tick_data.campaign_mode == CampaignMode.NOT_READY
    assert tick_data.tick_input is None


@pytest.mark.unit
def test_prepare_v3_operable_ladder_contexts_does_not_sync_hard_status() -> None:
    """prepare только фильтрует; MIN+hs=1 не трогаем (validate — в preamble)."""
    from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.tick_context import (
        prepare_v3_operable_ladder_contexts,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_contexts import (
        build_keyword_v3_contexts,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger import (
        V3TickKeywordLedger,
    )
    from tests.unit.auto_updater_v3.test_tick_ledger import _kw

    kw = _kw(ks_id=1, mode=KeywordStrategyMode.MIN_CPA, hard_status=1)
    ledger = V3TickKeywordLedger.from_keywords([kw])
    all_contexts = build_keyword_v3_contexts(ledger.keywords, {})

    operable, rebuilt = prepare_v3_operable_ladder_contexts(
        ledger,
        {},
        all_contexts,
    )

    assert ledger.keywords[0].keyword_setting.hard_status == 1
    assert ledger.keywords[0].keyword_setting.strategy_mode == KeywordStrategyMode.MIN_CPA
    assert len(operable) == 1
    assert len(rebuilt) == 1
