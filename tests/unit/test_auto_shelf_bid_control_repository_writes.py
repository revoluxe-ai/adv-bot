"""Unit-тесты записи AutoShelfBidControlRepository (commit транзакции)."""

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
async def test_set_enabled_commits_transaction(mock_get_session_maker: MagicMock) -> None:
    """Включение control сохраняется в PostgreSQL через commit, не только flush."""
    adv = MagicMock()
    adv.auto_shelf_bid_control_enabled = False
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = adv

    session = AsyncMock()
    session.execute = AsyncMock(return_value=execute_result)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    mock_get_session_maker.return_value = _make_async_cm(session)

    repository = AutoShelfBidControlRepository()
    await repository.set_enabled(42, True)

    assert adv.auto_shelf_bid_control_enabled is True
    session.flush.assert_awaited_once()
    session.commit.assert_awaited_once()


@patch(
    "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager."
    "auto_shelf_bid_control_repository.get_session_maker"
)
async def test_set_enabled_missing_adv_does_not_commit(
    mock_get_session_maker: MagicMock,
) -> None:
    """При отсутствии AdvSetting транзакция не коммитится."""
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = None

    session = AsyncMock()
    session.execute = AsyncMock(return_value=execute_result)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    mock_get_session_maker.return_value = _make_async_cm(session)

    repository = AutoShelfBidControlRepository()
    with pytest.raises(ValueError, match="adv_setting_not_found"):
        await repository.set_enabled(99, True)

    session.flush.assert_not_awaited()
    session.commit.assert_not_awaited()
