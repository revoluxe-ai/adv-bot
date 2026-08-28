"""Mock-only handoff proofs for partner / admin-id / gate PG seams (no live DB)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.client_bot.middlewars.gate as gate_mod
import app.client_bot.user_interface.handlers.admin_panel as admin_panel
import app.modules.partner_program.partner_stats as partner_stats

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
async def test_get_partner_stats_hands_read_session_to_child() -> None:
    """Parent opens ``sm(read_only=True)`` and delegates to in-session child."""
    session = AsyncMock(spec=AsyncSession)
    sm_cm = _session_cm(session)
    child = AsyncMock(return_value=SimpleNamespace(partner_user_id=1))

    with (
        patch.object(partner_stats, "_sm", sm_cm),
        patch.object(partner_stats, "_get_partner_stats_in_session", child),
    ):
        result = await partner_stats.get_partner_stats(7)

    assert sm_cm.last_read_only is True
    child.assert_awaited_once_with(session, 7)
    assert result.partner_user_id == 1


@pytest.mark.asyncio
async def test_list_partner_stats_hands_read_session_to_child() -> None:
    """Parent opens ``sm(read_only=True)`` and delegates to list child."""
    session = AsyncMock(spec=AsyncSession)
    sm_cm = _session_cm(session)
    child = AsyncMock(return_value=[])

    with (
        patch.object(partner_stats, "_sm", sm_cm),
        patch.object(partner_stats, "list_partner_stats_in_session", child),
    ):
        rows = await partner_stats.list_partner_stats()

    assert sm_cm.last_read_only is True
    child.assert_awaited_once_with(session)
    assert rows == []


@pytest.mark.asyncio
async def test_create_partner_payout_hands_write_session_to_child() -> None:
    """Parent opens ``sm(read_only=False)`` and delegates to payout child."""
    session = AsyncMock(spec=AsyncSession)
    sm_cm = _session_cm(session)
    child = AsyncMock(return_value=SimpleNamespace(id=99))

    with (
        patch.object(partner_stats, "_sm", sm_cm),
        patch.object(partner_stats, "create_partner_payout_in_session", child),
    ):
        payout = await partner_stats.create_partner_payout(
            partner_user_id=1,
            admin_user_id=2,
            amount="3.00",
            comment="x",
        )

    assert sm_cm.last_read_only is False
    child.assert_awaited_once()
    assert child.await_args.args[0] is session
    assert child.await_args.kwargs["partner_user_id"] == 1
    assert child.await_args.kwargs["admin_user_id"] == 2
    assert payout.id == 99


@pytest.mark.asyncio
async def test_get_admin_user_db_id_hands_read_session_to_child() -> None:
    """Parent opens ``sm(read_only=True)`` and delegates to admin-id child."""
    session = AsyncMock(spec=AsyncSession)
    sm_cm = _session_cm(session)
    child = AsyncMock(return_value=42)

    with (
        patch.object(admin_panel, "_sm", sm_cm),
        patch.object(admin_panel, "get_admin_user_db_id_in_session", child),
    ):
        resolved = await admin_panel._get_admin_user_db_id(555)

    assert sm_cm.last_read_only is True
    child.assert_awaited_once_with(session, 555)
    assert resolved == 42


@pytest.mark.asyncio
async def test_resolve_user_hands_write_session_to_child() -> None:
    """Parent opens ``sm(read_only=False)`` and delegates to gate child."""
    session = AsyncMock(spec=AsyncSession)
    sm_cm = _session_cm(session)
    child = AsyncMock(return_value=SimpleNamespace(id=3))
    event = MagicMock()

    with (
        patch.object(gate_mod, "_sm", sm_cm),
        patch.object(gate_mod, "resolve_user_in_session", child),
    ):
        user = await gate_mod._resolve_user(event, 777)

    assert sm_cm.last_read_only is False
    child.assert_awaited_once_with(session, event, 777)
    assert user.id == 3


@pytest.mark.asyncio
async def test_invite_show_handler_hands_write_session_to_children() -> None:
    """Parent opens ``sm(read_only=False)`` and loads user via child."""
    from decimal import Decimal
    from unittest.mock import AsyncMock

    import app.client_bot.user_interface.handlers.invite_show as invite_show
    from app.modules.partner_program.partner_stats import PartnerStats

    session = AsyncMock(spec=AsyncSession)
    sm_cm = _session_cm(session)
    user = SimpleNamespace(id=11, user_telegram_id=555)
    invite = SimpleNamespace(
        code="AB12-CD34",
        expires_at=datetime(2030, 1, 2, 3, 4, 5),
    )
    load_user = AsyncMock(return_value=user)
    resolve_invite = AsyncMock(return_value=invite)
    stats = PartnerStats(
        partner_user_id=11,
        invite_count=0,
        used_invite_count=0,
        invited_users_count=0,
        paid_users_count=0,
        clients_paid_sum=Decimal("0.00"),
        earned_amount=Decimal("0.00"),
        paid_out_amount=Decimal("0.00"),
        available_to_payout=Decimal("0.00"),
    )

    callback = MagicMock()
    callback.message = SimpleNamespace(chat=SimpleNamespace(id=555))
    callback.from_user = SimpleNamespace(id=555)
    bot = AsyncMock()

    with (
        patch.object(invite_show, "_sm", sm_cm),
        patch.object(invite_show, "load_user_by_telegram_id_in_session", load_user),
        patch.object(invite_show, "_resolve_active_invite", resolve_invite),
        patch.object(invite_show, "get_partner_stats", AsyncMock(return_value=stats)),
    ):
        await invite_show.invite_show_handler(callback, bot)

    assert sm_cm.last_read_only is False
    load_user.assert_awaited_once_with(session, 555)
    resolve_invite.assert_awaited_once()
    bot.send_message.assert_awaited()
