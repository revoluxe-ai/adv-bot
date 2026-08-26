"""Mock-only handoff proofs for off_auto_cpm PG WRITE seam (no live DB)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.wb_adv_updater.modules.bidder.tg_bot_handlers import on_off_controller

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _session_cm(session: AsyncSession):
    """Build session-maker double that records explicit ``read_only=``."""

    @asynccontextmanager
    async def cm(*, read_only: bool = False) -> AsyncGenerator[AsyncSession, None]:
        cm.last_read_only = read_only  # type: ignore[attr-defined]
        yield session

    cm.last_read_only = None  # type: ignore[attr-defined]
    return cm


@pytest.mark.asyncio
async def test_off_auto_cpm_hands_write_session_to_child() -> None:
    """Parent opens ``sm(read_only=False)`` and delegates to in-session child."""
    session = AsyncMock(spec=AsyncSession)
    sm_cm = _session_cm(session)
    child = AsyncMock(return_value=SimpleNamespace(id=42, bidder_active=False))
    cpm_page = AsyncMock()
    bot = AsyncMock()
    callback = SimpleNamespace(message=SimpleNamespace(chat=SimpleNamespace(id=100)))
    callback_data = SimpleNamespace(adv_original_id=42)
    state = AsyncMock()

    with (
        patch.object(on_off_controller, "sm", sm_cm),
        patch.object(on_off_controller, "off_auto_cpm_in_session", child),
        patch(
            "app.client_bot.user_interface.views.messages.CPMSetting",
            MagicMock(return_value=cpm_page),
        ),
    ):
        await on_off_controller.off_auto_cpm(callback, callback_data, bot, state)

    assert sm_cm.last_read_only is False
    child.assert_awaited_once_with(session, 42)
    cpm_page.assert_awaited_once_with(42)


@pytest.mark.asyncio
async def test_off_auto_cpm_in_session_sets_bidder_inactive_and_commits() -> None:
    """WRITE child clears bidder_active then commits on injected session."""
    adv = SimpleNamespace(id=7, bidder_active=True)
    result = MagicMock()
    result.scalar_one_or_none.return_value = adv
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock(return_value=result)

    out = await on_off_controller.off_auto_cpm_in_session(session, 7)

    assert out is adv
    assert adv.bidder_active is False
    session.commit.assert_awaited_once()
