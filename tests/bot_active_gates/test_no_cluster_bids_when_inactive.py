"""Gate: cluster bids не пишет в WB при bot_active=False."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.bot_active_gates.helpers import unwrap_coroutine

pytestmark = [pytest.mark.unit, pytest.mark.bot_active_gates, pytest.mark.asyncio]


async def test_cluster_bids_skipped_when_bot_inactive(
    coroutines_manager_gate: MagicMock,
    inactive_complex_adv: MagicMock,
) -> None:
    manager = coroutines_manager_gate
    inactive_complex_adv.adv_setting.bidder_active = True
    manager._wb_shop_data_manager.get_complex_advs = AsyncMock(
        return_value=[inactive_complex_adv]
    )
    update_cluster_mock = AsyncMock()

    container_instance = MagicMock()
    container_instance.update_cluster_bids_manager = MagicMock(
        return_value=MagicMock(update_cluster_bids=update_cluster_mock)
    )

    with (
        patch(
            "app.modules.shop_runner.service_manager.manager.settings"
        ) as mock_settings,
        patch(
            "app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.di.ClusterBidsManagerContainer",
            return_value=container_instance,
        ),
    ):
        mock_settings.AUTO_SETTING_ACTIVE = True
        await unwrap_coroutine(manager.update_cluster_bids)(manager)

    update_cluster_mock.assert_not_called()
