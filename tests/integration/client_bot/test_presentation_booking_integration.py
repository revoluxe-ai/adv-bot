from unittest.mock import AsyncMock, MagicMock, patch
from datetime import UTC, datetime, timedelta

import pytest
from aiogram.types import CallbackQuery, Message, User as TelegramUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.presentation_booking_service import create_slot
from app.client_bot.user_interface.handlers.presentation_booking import (
    admin_slots_deactivate,
    booking_confirm,
    booking_menu,
)
from app.client_bot.user_interface.views import callbacks
from app.utils.db.models import PresentationBooking, PresentationSlot, User


pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class MockSessionMaker:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def __call__(self, read_only: bool = False) -> "MockSessionMaker":
        return self

    async def __aenter__(self) -> AsyncSession:
        return self.session

    async def __aexit__(self, *args: object) -> None:
        return None


async def _create_user(async_session: AsyncSession, telegram_id: int, passed_gate: bool) -> User:
    user = User(
        user_telegram_id=telegram_id,
        username=f"user_{telegram_id}",
        passed_gate=passed_gate,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


def _make_callback(telegram_id: int, username: str | None = None) -> CallbackQuery:
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = MagicMock(spec=TelegramUser)
    callback.from_user.id = telegram_id
    callback.from_user.username = username
    callback.message = MagicMock(spec=Message)
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    return callback


async def test_presentation_booking_flow_for_not_passed_gate_user(async_session: AsyncSession) -> None:
    await _create_user(async_session, telegram_id=401001, passed_gate=False)
    patched_sm = MockSessionMaker(async_session)

    with patch("app.client_bot.presentation_booking_service.sm", patched_sm), patch(
        "app.client_bot.user_interface.handlers.presentation_booking.sm", patched_sm
    ):
        slot = await create_slot(
            start_at_utc=(datetime.now(UTC) + timedelta(days=1)).replace(tzinfo=None),
            duration_minutes=60,
            admin_telegram_id=401001,
        )

        callback = _make_callback(telegram_id=401001, username="book_user")
        await booking_menu(callback)
        callback.message.edit_text.assert_awaited()

        callback_data = callbacks.PresentationBooking(action="confirm", slot_id=slot.id)
        bot = AsyncMock()
        await booking_confirm(callback, callback_data, bot)

    stmt = select(PresentationBooking).where(PresentationBooking.slot_id == slot.id)
    booking = (await async_session.execute(stmt)).scalar_one_or_none()
    assert booking is not None
    assert booking.slot_id == slot.id
    assert booking.user_id is not None
    callback.message.edit_text.assert_awaited()
    _, kwargs = callback.message.edit_text.call_args
    markup = kwargs.get("reply_markup")
    assert markup is not None
    button = markup.inline_keyboard[0][0]
    assert button.text == "Связаться с менеджером"
    assert button.url is not None
    assert "t.me/" in button.url
    assert "text=" in button.url


async def test_admin_deactivate_slot_callback(async_session: AsyncSession) -> None:
    await _create_user(async_session, telegram_id=401002, passed_gate=True)
    patched_sm = MockSessionMaker(async_session)

    with patch("app.client_bot.presentation_booking_service.sm", patched_sm), patch(
        "app.client_bot.user_interface.handlers.presentation_booking.sm", patched_sm
    ):
        slot = await create_slot(
            start_at_utc=(datetime.now(UTC) + timedelta(days=2)).replace(tzinfo=None),
            duration_minutes=45,
            admin_telegram_id=401002,
        )
        callback = _make_callback(telegram_id=401002, username="admin_user")
        data = callbacks.PresentationSlotsAdmin(action="deactivate", slot_id=slot.id)
        await admin_slots_deactivate(callback, data)

    refreshed = (
        await async_session.execute(
            select(PresentationSlot).where(PresentationSlot.id == slot.id)
        )
    ).scalar_one()
    assert refreshed.is_active is False
