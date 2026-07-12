"""Gate: common search bid не пишет в WB при bot_active=False."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.bot_active_gates.helpers import unwrap_coroutine

pytestmark = [pytest.mark.unit, pytest.mark.bot_active_gates, pytest.mark.asyncio]


async def test_common_bid_skipped_when_bot_inactive(
    coroutines_manager_gate: MagicMock,
    inactive_complex_adv: MagicMock,
) -> None:
    manager = coroutines_manager_gate
    manager._wb_shop_data_manager.get_complex_advs = AsyncMock(
        return_value=[inactive_complex_adv]
    )
    update_mock = AsyncMock(return_value=None)
    manager_mock = MagicMock()
    manager_mock.update_common_bid_in_search_adv = update_mock

    with (
        patch(
            "app.modules.shop_runner.service_manager.manager.settings"
        ) as mock_settings,
        patch(
            "app.modules.shop_runner.service_manager.services.update_commot_bid_in_search_advs_manager.UpdateCommotBidInSearchAdvsManager",
            return_value=manager_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.update_commot_bid_in_search_advs_manager.CurrentCommonBidsResolver",
        ) as resolver_cls,
    ):
        mock_settings.AUTO_SETTING_ACTIVE = True
        resolver_cls.return_value.get_merged_bids = AsyncMock(return_value={})
        manager._wb_shop_data_manager.get_wb_advs_dto = AsyncMock(return_value=[])

        await unwrap_coroutine(manager.update_common_bid_in_search_adv)(manager)

    update_mock.assert_not_called()
