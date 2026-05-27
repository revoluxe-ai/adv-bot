"""Unit: один fetch bid profiles за полный цикл process_adv_v3."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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

    async def _phase0_noop(
        _adv: object,
        *,
        keywords: list[object],
        contexts: list[object],
        dto: object,
    ) -> tuple[list[object], bool]:
        return keywords, False

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.build_predict_keywords_target_place",
            return_value=predictor,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator._run_phase0_gap_rebalance",
            new=AsyncMock(side_effect=_phase0_noop),
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
            return_value=state,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.select_v3_actions",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.apply_v3_actions",
            new=AsyncMock(),
        ),
    ):
        updater_cls.return_value.get_fact_data = AsyncMock(
            return_value=MagicMock(pay_for_order=50.0, predict_orders=5)
        )
        await process_adv_v3(complex_adv, wb_shop_data_manager=wb_manager)

    predictor.get_keyword_bid_profiles.assert_awaited_once()
