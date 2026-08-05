"""Mock-only handoff proofs for admin_panel PG WRITE seams (no live DB)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.client_bot.user_interface.handlers.admin_panel as admin_panel

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _session_cm(session: AsyncSession):
    """Build session-maker double that records explicit ``read_only=``."""

    @asynccontextmanager
    async def cm(read_only: bool = False) -> AsyncGenerator[AsyncSession, None]:
        cm.last_read_only = read_only  # type: ignore[attr-defined]
        yield session

    cm.last_read_only = None  # type: ignore[attr-defined]
    return cm


@pytest.mark.asyncio
async def test_admin_grant_gate_process_hands_write_session_to_child() -> None:
    """Parent opens ``sm(read_only=False)`` and delegates to grant child."""
    session = AsyncMock(spec=AsyncSession)
    sm_cm = _session_cm(session)
    user = SimpleNamespace(username="granted_user")
    grant = AsyncMock(return_value=user)

    message = MagicMock()
    message.text = "123456789"
    message.answer = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()

    with (
        patch.object(admin_panel, "_sm", sm_cm),
        patch.object(admin_panel, "grant_user_gate_in_session", grant),
    ):
        await admin_panel.admin_grant_gate_process(message, state)

    assert sm_cm.last_read_only is False
    grant.assert_awaited_once()
    assert grant.await_args.args[0] is session
    assert grant.await_args.args[1] == 123456789
    assert isinstance(grant.await_args.kwargs["now_utc"], datetime)
    state.clear.assert_awaited_once()
    message.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_reset_user_access_process_hands_write_session_to_child() -> None:
    """Parent opens ``sm(read_only=False)`` and delegates to reset child."""
    session = AsyncMock(spec=AsyncSession)
    sm_cm = _session_cm(session)
    user = SimpleNamespace(username="reset_user")
    reset = AsyncMock(return_value=user)
    redis_client = MagicMock()
    redis_client.delete = AsyncMock(return_value=1)

    message = MagicMock()
    message.text = "987654321"
    message.answer = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()

    with (
        patch.object(admin_panel, "_sm", sm_cm),
        patch.object(admin_panel, "reset_user_access_in_session", reset),
        patch.object(admin_panel, "AppContainer") as app_container_cls,
    ):
        app_container_cls.return_value.redis_client_wrapper.return_value = redis_client
        await admin_panel.admin_reset_user_access_process(message, state)

    assert sm_cm.last_read_only is False
    reset.assert_awaited_once_with(session, 987654321)
    redis_client.delete.assert_awaited_once_with(
        "client_bot:support_channel_subscription:987654321"
    )
    state.clear.assert_awaited_once()
    message.answer.assert_awaited_once()
