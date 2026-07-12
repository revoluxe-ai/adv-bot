"""Paid regression: common bid update вызывается при bot_active=True."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.bot_active_gates.helpers import unwrap_coroutine

pytestmark = [pytest.mark.unit, pytest.mark.paid_regression, pytest.mark.asyncio]


async def test_common_bid_runs_when_bot_active(
    coroutines_manager_paid: MagicMock,
    active_complex_adv: MagicMock,
) -> None:
    manager = coroutines_manager_paid
    manager._wb_shop_data_manager.get_complex_advs = AsyncMock(
        return_value=[active_complex_adv]
    )
    update_mock = AsyncMock(return_value=None)
    manager_mock = MagicMock()
    manager_mock.update_common_bid_in_search_adv = update_mock
    wb_adv_dto = MagicMock()

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
        resolver_cls.return_value.get_merged_bids = AsyncMock(return_value={1: 100})
        manager._wb_shop_data_manager.get_wb_advs_dto = AsyncMock(return_value=[wb_adv_dto])

        await unwrap_coroutine(manager.update_common_bid_in_search_adv)(manager)

    update_mock.assert_awaited_once()
