from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.auto_shelf_bid_repository import (
    AutoShelfBidRepository,
)


pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_get_current_mode_delegates_to_control_repository() -> None:
    repository = AutoShelfBidRepository(
        wb_manager_hub=MagicMock(),
        auto_recommendations_bid_cache_manager=MagicMock(),
    )
    repository._control_repository = MagicMock()
    repository._control_repository.get_mode_for_nmid = AsyncMock(return_value="test")

    mode = await repository.get_current_mode(111)

    assert mode == "test"
    repository._control_repository.get_mode_for_nmid.assert_awaited_once_with(111)

