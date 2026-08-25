"""Mock-only: ASEP repository parent→child session handoff + read_only polarity.

Pre-live proof that public writers open ``sm(read_only=False)`` / readers
``sm(read_only=True)`` and delegate to ``*_in_session`` (no bare ``sm()``).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_repository import (
    DEFAULT_RETEST_INTERVAL_DAYS,
    AutoShelfBidControlRepository,
)

_REPO_GSM = (
    "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager."
    "auto_shelf_bid_control_repository.get_session_maker"
)

_NMID = 91001
_NOW = datetime(2026, 8, 13, 12, 0, 0, tzinfo=UTC)
_DUE = _NOW + timedelta(days=7)


def _make_async_cm(session: AsyncMock) -> MagicMock:
    """Async context manager stub for ``get_session_maker``."""
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return ctx


def _inactive_state() -> SimpleNamespace:
    """State row without our-block."""
    return SimpleNamespace(
        shelf_exhausted_pause_active=False,
        shelf_exhausted_paused_at=None,
        shelf_exhausted_due_at=None,
        shelf_exhausted_notify_sent_at=None,
        shelf_exhausted_resolve_cpo_kind=None,
        shelf_exhausted_resolve_cpo_value=None,
        shelf_exhausted_epoch_pending=False,
        shelf_exhausted_epoch_start=None,
    )


@pytest.mark.asyncio
@patch(_REPO_GSM)
async def test_latch_public_uses_write_session_polarity(
    mock_get_session_maker: MagicMock,
) -> None:
    """Public latch MUST call get_session_maker(read_only=False)."""
    state = _inactive_state()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = state
    session = AsyncMock()
    session.execute = AsyncMock(return_value=execute_result)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    mock_get_session_maker.return_value = _make_async_cm(session)

    repo = AutoShelfBidControlRepository()
    await repo.latch_shelf_exhausted_pause(
        _NMID,
        now=_NOW,
        due_at=_DUE,
        resolve_cpo_kind="target",
        resolve_cpo_value=250.0,
    )

    mock_get_session_maker.assert_called_with(read_only=False)
    assert state.shelf_exhausted_pause_active is True
    session.commit.assert_awaited()


@pytest.mark.asyncio
@patch(_REPO_GSM)
async def test_get_state_public_uses_read_only_true(
    mock_get_session_maker: MagicMock,
) -> None:
    """Public get_state MUST call get_session_maker(read_only=True)."""
    state = _inactive_state()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = state
    session = AsyncMock()
    session.execute = AsyncMock(return_value=execute_result)
    mock_get_session_maker.return_value = _make_async_cm(session)

    repo = AutoShelfBidControlRepository()
    loaded = await repo.get_state(_NMID)
    assert loaded is state
    mock_get_session_maker.assert_called_with(read_only=True)


@pytest.mark.asyncio
@patch(_REPO_GSM)
async def test_get_or_create_settings_uses_explicit_write_polarity(
    mock_get_session_maker: MagicMock,
) -> None:
    """get_or_create_settings MUST NOT use bare sm(); write polarity required."""
    existing = SimpleNamespace(
        nmid=_NMID,
        retest_interval_days=DEFAULT_RETEST_INTERVAL_DAYS,
    )
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = existing
    session = AsyncMock()
    session.execute = AsyncMock(return_value=execute_result)
    session.commit = AsyncMock()
    mock_get_session_maker.return_value = _make_async_cm(session)

    repo = AutoShelfBidControlRepository()
    out = await repo.get_or_create_settings(_NMID, default_max_bid_minor=50_000)

    assert out is existing
    mock_get_session_maker.assert_called_with(read_only=False)
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_latch_in_session_mutates_without_opening_sm() -> None:
    """HANDOFF: in_session mutates injected session state (no sm open)."""
    state = _inactive_state()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = state
    session = AsyncMock()
    session.execute = AsyncMock(return_value=execute_result)
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    repo = AutoShelfBidControlRepository()
    out = await repo.latch_shelf_exhausted_pause_in_session(
        session,
        _NMID,
        now=_NOW,
        due_at=_DUE,
        resolve_cpo_kind="max",
        resolve_cpo_value=180.0,
    )
    assert out is state
    assert state.shelf_exhausted_pause_active is True
    assert state.shelf_exhausted_resolve_cpo_kind == "max"
    session.commit.assert_not_called()
