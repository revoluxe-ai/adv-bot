"""Unit: finally target_place sync не маскирует исключение из try."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator import (
    process_adv_v3,
)

_ROOT_ERROR = RuntimeError("root cause from try")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_adv_v3_finally_sync_failure_preserves_try_exception() -> None:
    """Ошибка sync в finally не подменяет исключение из try (PEP 409)."""
    complex_adv = MagicMock()
    complex_adv.adv_id = 42
    complex_adv.adv_setting = MagicMock()
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = True
    complex_adv.v3_rollout_aggressiveness = 2
    complex_adv.get_keywords = AsyncMock(return_value=[])

    dto = MagicMock()
    dto.min_target_position = 5

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator._load_v3_wb_context",
            new=AsyncMock(return_value=(dto, {})),
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
            return_value=SalesStates.OPTIMAL,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.build_keyword_v3_contexts",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_data_bootstrap_v3",
            side_effect=_ROOT_ERROR,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.sync_keyword_target_places_v3",
            new=AsyncMock(side_effect=OSError("db down")),
        ),
    ):
        updater_cls.return_value.get_fact_data = AsyncMock(
            return_value=MagicMock(pay_for_order=50.0, predict_orders=10)
        )
        with pytest.raises(RuntimeError, match="root cause from try") as exc_info:
            await process_adv_v3(complex_adv, wb_shop_data_manager=MagicMock())

    assert exc_info.value is _ROOT_ERROR
    assert exc_info.value.__context__ is None or not isinstance(
        exc_info.value.__context__, OSError
    )
