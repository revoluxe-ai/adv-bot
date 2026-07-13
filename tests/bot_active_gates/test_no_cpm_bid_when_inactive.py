"""Gate: CPM bidder не запускается при bot_active=False."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.bot_active_gates.helpers import unwrap_coroutine

pytestmark = [pytest.mark.unit, pytest.mark.bot_active_gates, pytest.mark.asyncio]


async def test_cpm_bid_skipped_when_bot_inactive(
    coroutines_manager_gate: MagicMock,
    inactive_complex_adv: MagicMock,
) -> None:
    manager = coroutines_manager_gate
    inactive_complex_adv.adv_setting.bidder_active = True
    manager._wb_shop_data_manager.get_complex_advs = AsyncMock(
        return_value=[inactive_complex_adv]
    )

    with patch(
        "app.modules.shop_runner.service_manager.manager.run_bidder_process_for_adv",
        new=AsyncMock(),
    ) as bidder_mock:
        await unwrap_coroutine(manager.update_cpm_bid)(manager)

    bidder_mock.assert_not_called()
