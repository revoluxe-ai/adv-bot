"""RECORD gate (xfail): common sale stat для inactive после loader refactor."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.bot_active_gates.helpers import unwrap_coroutine

pytestmark = [pytest.mark.unit, pytest.mark.bot_active_gates, pytest.mark.asyncio]


@pytest.mark.xfail(reason="loader refactor pending: end-to-end loader excludes inactive")
async def test_common_sale_stat_end_to_end_includes_inactive_adv(
    coroutines_manager_gate: MagicMock,
    inactive_complex_adv: MagicMock,
) -> None:
    manager = coroutines_manager_gate
    real_dm = manager._wb_shop_data_manager
    advs = await real_dm.get_complex_advs(load_extras=False)
    assert inactive_complex_adv in advs or any(not a.bot_active for a in advs)


async def test_common_sale_stat_coroutine_processes_inactive_when_in_list(
    coroutines_manager_gate: MagicMock,
    inactive_complex_adv: MagicMock,
) -> None:
    manager = coroutines_manager_gate
    manager._wb_shop_data_manager.get_complex_advs = AsyncMock(
        return_value=[inactive_complex_adv]
    )
    updater_instance = MagicMock()
    updater_instance.update_last_week_stats = AsyncMock(return_value=set())

    container = MagicMock()
    container.common_sale_stat_updater = MagicMock(return_value=updater_instance)

    with patch(
        "app.modules.shop_runner.service_manager.services.common_sale_stat_updater.CommonSaleStatUpdaterContainer",
        return_value=container,
    ):
        await unwrap_coroutine(manager.update_common_sale_stat)(manager)

    updater_instance.update_last_week_stats.assert_awaited_once()
