"""Unit-тесты mode для инкремента при включённом control без state."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_repository import (
    AutoShelfBidControlRepository,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _make_async_cm(session: AsyncMock) -> MagicMock:
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return ctx


@patch(
    "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager."
    "auto_shelf_bid_control_repository.get_session_maker"
)
async def test_get_mode_for_nmid_enabled_without_state_returns_test(
    mock_get_session_maker: MagicMock,
) -> None:
    """Пассивный сбор: до первого тика control инкремент пишет mode=test."""
    enabled_row = MagicMock()
    enabled_row.first.return_value = (1,)
    state_result = MagicMock()
    state_result.scalar_one_or_none.return_value = None

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[enabled_row, state_result])
    mock_get_session_maker.return_value = _make_async_cm(session)

    repository = AutoShelfBidControlRepository()
    mode = await repository.get_mode_for_nmid(10749810)

    assert mode == "test"


@patch(
    "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager."
    "auto_shelf_bid_control_repository.get_session_maker"
)
async def test_get_mode_for_nmid_disabled_returns_test(
    mock_get_session_maker: MagicMock,
) -> None:
    """Control выключен: инкремент всё равно пишет mode=test (пассивный сбор)."""
    disabled_row = MagicMock()
    disabled_row.first.return_value = None

    session = AsyncMock()
    session.execute = AsyncMock(return_value=disabled_row)
    mock_get_session_maker.return_value = _make_async_cm(session)

    repository = AutoShelfBidControlRepository()
    mode = await repository.get_mode_for_nmid(10749810)

    assert mode == "test"
