"""Unit tests for get_connect_existing_candidates service."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.connect_existing_advs.candidates_service import (
    ConnectExistingCandidatesResult,
)
from app.modules.connect_existing_advs.service import get_connect_existing_candidates


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_connect_existing_candidates_calls_hub_and_returns_result() -> None:
    """get_connect_existing_candidates uses DI hub and returns promotion_manager result."""
    expected = ConnectExistingCandidatesResult(
        auction_candidates=[],
        auto_candidates=[],
    )
    mock_pm = MagicMock()
    mock_pm.get_connect_existing_candidates = AsyncMock(return_value=expected)
    mock_hub = MagicMock()
    mock_hub.wb_data_manager.promotion_manager = mock_pm
    mock_factory = MagicMock()
    mock_factory.get_wb_manager_hub = MagicMock(return_value=mock_hub)
    mock_wb_factory_container = MagicMock()
    mock_wb_factory_container.wb_manager_hub_factory = MagicMock(
        return_value=mock_factory
    )
    mock_module_resources = MagicMock()
    mock_module_resources.wb_manager_hub_factory_container = mock_wb_factory_container
    mock_container = MagicMock()
    mock_container.module_resources = mock_module_resources

    @asynccontextmanager
    async def async_cm():
        yield mock_container

    mock_create = AsyncMock(return_value=async_cm())

    with patch(
        "app.modules.connect_existing_advs.service.DIManager.create",
        mock_create,
    ):
        result = await get_connect_existing_candidates("shop_1", 12345)

    assert result is expected
    mock_factory.get_wb_manager_hub.assert_called_once_with("shop_1")
    mock_pm.get_connect_existing_candidates.assert_called_once_with(12345)
