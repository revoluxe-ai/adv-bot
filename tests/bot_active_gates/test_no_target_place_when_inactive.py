"""Gate: target place не обновляется при bot_active=False."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.bot_active_gates.helpers import unwrap_coroutine

pytestmark = [pytest.mark.unit, pytest.mark.bot_active_gates, pytest.mark.asyncio]


async def test_individual_target_place_skipped_when_bot_inactive(
    coroutines_manager_gate: MagicMock,
    inactive_complex_adv: MagicMock,
) -> None:
    manager = coroutines_manager_gate
    manager._wb_shop_data_manager.get_complex_advs = AsyncMock(
        return_value=[inactive_complex_adv]
    )
    manager._wb_shop_data_manager.get_wb_advs_dto = AsyncMock()

    with patch(
        "app.modules.shop_runner.service_manager.manager.run_tasks",
        new=AsyncMock(),
    ) as run_tasks_mock:
        await unwrap_coroutine(manager.update_individual_keyword_target_places)(
            manager
        )

    run_tasks_mock.assert_not_called()
