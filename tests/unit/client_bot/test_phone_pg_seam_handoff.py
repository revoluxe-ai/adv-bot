"""Mock-only handoff proofs for phone PG seams (no live DB)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.middlewars import phone_required
from app.client_bot.user_interface.handlers import phone_collection
from app.utils.db.models import User

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _session_cm(session: AsyncSession):
    @asynccontextmanager
    async def cm(read_only: bool = False) -> AsyncGenerator[AsyncSession, None]:
        yield session

    return cm


async def test_phone_required_parent_passes_session_to_child() -> None:
    """PhoneRequiredMiddleware opens sm(read_only=True) and hands session to child."""
    user = MagicMock(spec=User)
    user.passed_gate = True
    user.phone = "+7999"
    session = AsyncMock(spec=AsyncSession)
    handler = AsyncMock(return_value="ok")
    event = MagicMock()
    event.from_user = MagicMock(id=101)
    event.data = None
    event.text = None

    with (
        patch.object(phone_required, "_sm", _session_cm(session)),
        patch.object(
            phone_required,
            "load_user_phone_gate_fields_in_session",
            new_callable=AsyncMock,
            return_value=user,
        ) as load_mock,
        patch.object(phone_required, "settings") as mock_settings,
    ):
        mock_settings.invite_gate = True
        middleware = phone_required.PhoneRequiredMiddleware()
        result = await middleware(handler, event, {"bot": AsyncMock()})

    assert result == "ok"
    load_mock.assert_awaited_once_with(session, 101)
    handler.assert_awaited_once()


async def test_save_user_phone_parent_passes_session_to_child() -> None:
    """save_user_phone opens sm(read_only=False) and hands session to child."""
    user = MagicMock(spec=User)
    user.phone = None
    session = AsyncMock(spec=AsyncSession)
    message = MagicMock()
    message.from_user = MagicMock(id=202)
    message.contact = MagicMock(user_id=202, phone_number="+70001112233")
    message.chat = MagicMock(id=202)
    message.message_id = 1
    bot = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    dispatcher = AsyncMock()

    with (
        patch.object(phone_collection, "_sm", _session_cm(session)),
        patch.object(
            phone_collection,
            "save_user_phone_in_session",
            new_callable=AsyncMock,
            return_value=user,
        ) as save_mock,
    ):
        await phone_collection.save_user_phone(message, bot, state, dispatcher)

    save_mock.assert_awaited_once_with(session, 202, "+70001112233")
    bot.send_message.assert_awaited()
