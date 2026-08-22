"""Integration tests for entry points: gate, start_registration, shop_settings call MainMenu/ShopsListPage."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from aiogram.types import CallbackQuery, Chat, Message, User as TelegramUser
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.client_bot.user_interface.handlers.gate import gate_invite_process_code
from app.client_bot.user_interface.handlers.start_registration_func import (
    start_registration,
)
from app.client_bot.user_interface.handlers.shop_settings import delete_wb_user_cabinet
from app.client_bot.user_interface.views import callbacks
from app.client_bot.user_interface.views.gate import get_gate_message_text
from app.modules.common_slaves.wildberries.models import WBUserCabinet
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.settings.settings_master import Settings
from app.utils.db.models import Invite, InviteStatus, User


pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.destructive_local]


async def _create_user_with_cabinet(
    async_session,
    user_telegram_id: int = 88881,
    passed_gate: bool = True,
):
    """Create user with one WBUserCabinet."""
    user = User(
        user_telegram_id=user_telegram_id,
        username="entry_point_test_user",
        passed_gate=passed_gate,
    )
    async_session.add(user)
    await async_session.flush()

    cabinet = WBCabinet(
        shop_id=f"test_shop_{user_telegram_id}",
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
    )
    async_session.add(cabinet)
    await async_session.flush()

    uc = WBUserCabinet(
        user_id=user.id,
        wb_cabinet_id=cabinet.id,
        name="Test Shop",
    )
    async_session.add(uc)
    await async_session.flush()

    await async_session.commit()
    await async_session.refresh(user)
    return user, uc, cabinet


async def test_gate_invite_success_calls_main_menu(
    async_session,
):
    """After successful invite code entry, gate calls MainMenu(bot, chat_id)(), not ShopChoice."""
    from app.client_bot.user_interface.handlers.gate import _sm

    user = User(
        user_telegram_id=88882,
        username="gate_test",
        passed_gate=False,
    )
    async_session.add(user)
    await async_session.flush()

    now = datetime.now(UTC).replace(tzinfo=None)
    invite = Invite(
        code="TEST-INVITE-CODE",
        status=InviteStatus.ACTIVE,
        issued_to_user_id=user.id,
        issued_at=now,
        expires_at=now + timedelta(days=7),
    )
    async_session.add(invite)
    await async_session.flush()
    await async_session.commit()

    bot = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()

    message = MagicMock(spec=Message)
    message.text = "TEST-INVITE-CODE"
    message.chat = MagicMock(spec=Chat)
    message.chat.id = 88882
    message.from_user = MagicMock(spec=TelegramUser)
    message.from_user.id = 88882

    class MockSessionMaker:
        def __init__(self, s):
            self._s = s

        def __call__(self, read_only=False):
            return self

        async def __aenter__(self):
            return self._s

        async def __aexit__(self, *args):
            pass

    with patch(
        "app.client_bot.user_interface.handlers.gate._sm",
        MockSessionMaker(async_session),
    ), patch("app.client_bot.user_interface.handlers.gate.MainMenu") as mock_main_menu:
        mock_main_menu.return_value = AsyncMock()

        await gate_invite_process_code(message, bot, state)

        mock_main_menu.assert_called_once_with(bot, 88882, full_client_ui=True)
        mock_main_menu.return_value.assert_awaited_once()


async def test_start_registration_new_user_creates_user_and_shows_gate(
    async_session,
):
    """New user (no record in DB): start_registration creates user, shows gate screen, does not call MainMenu."""
    telegram_id = 88880
    chat_id = 88880
    # Ensure no user with this id (we do not create one)
    stmt = select(User).where(User.user_telegram_id == telegram_id)
    result = await async_session.execute(stmt)
    assert result.scalar_one_or_none() is None

    bot = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()

    message = MagicMock(spec=Message)
    message.text = "/start"
    message.chat = MagicMock(spec=Chat)
    message.chat.id = chat_id
    message.from_user = MagicMock(spec=TelegramUser)
    message.from_user.id = telegram_id
    message.from_user.username = "new_user_88880"

    with patch(
        "app.client_bot.user_interface.handlers.start_registration_func.sm"
    ) as mock_sm, patch(
        "app.client_bot.user_interface.handlers.start_registration_func.MainMenu"
    ) as mock_main_menu, patch.object(
        Settings, "invite_gate", PropertyMock(return_value=True)
    ), patch.object(
        Settings, "presentation_only", PropertyMock(return_value=False)
    ):
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=async_session)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_sm.return_value = mock_cm
        mock_main_menu.return_value = AsyncMock()

        await start_registration(message, bot, state)

    # User must exist in DB with passed_gate=False (create_user already committed)
    stmt2 = select(User).where(User.user_telegram_id == telegram_id)
    result2 = await async_session.execute(stmt2)
    user = result2.scalar_one_or_none()
    assert user is not None
    assert user.user_telegram_id == telegram_id
    assert user.username == "new_user_88880"
    assert user.passed_gate is False

    # Gate screen was sent
    bot.send_message.assert_awaited_once()
    call_args, call_kw = bot.send_message.call_args
    assert call_args[0] == chat_id
    text = call_args[1] if len(call_args) > 1 else call_kw.get("text", "")
    assert get_gate_message_text() in text or "Доступ" in text
    assert call_kw.get("reply_markup") is not None

    # MainMenu was not called (user has not passed gate)
    mock_main_menu.assert_not_called()


async def test_start_registration_passed_gate_calls_main_menu(
    async_session,
):
    """start_registration with passed_gate calls MainMenu(bot, chat_id)()."""
    user, _, _ = await _create_user_with_cabinet(async_session, 88883, passed_gate=True)
    bot = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()

    message = MagicMock(spec=Message)
    message.text = "/start"
    message.chat = MagicMock(spec=Chat)
    message.chat.id = 88883
    message.from_user = MagicMock(spec=TelegramUser)
    message.from_user.id = 88883
    message.from_user.username = "test_user"

    with patch(
        "app.client_bot.user_interface.handlers.start_registration_func.sm"
    ) as mock_sm:
        async_session_maker = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=async_session)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        async_session_maker.return_value = mock_cm
        mock_sm.return_value = mock_cm

        with patch(
            "app.client_bot.user_interface.handlers.start_registration_func.MainMenu"
        ) as mock_main_menu:
            mock_main_menu.return_value = AsyncMock()

            await start_registration(message, bot, state)

            mock_main_menu.assert_called_once_with(bot, 88883, full_client_ui=True)
            mock_main_menu.return_value.assert_awaited_once()


async def test_shop_settings_delete_cabinet_calls_shops_list_page(
    async_session,
):
    """delete_wb_user_cabinet calls ShopsListPage with shop_ids_with_active_tokens."""
    user, uc, cabinet = await _create_user_with_cabinet(
        async_session, 88884, passed_gate=True
    )

    bot = AsyncMock()
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = MagicMock(spec=TelegramUser)
    callback.from_user.id = 88884
    callback.message = MagicMock(spec=Message)
    callback.message.chat = MagicMock(spec=Chat)
    callback.message.chat.id = 88884

    with patch("app.client_bot.user_interface.handlers.shop_settings.sm") as mock_sm:
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=async_session)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_sm.return_value = mock_cm

        with patch(
            "app.client_bot.user_interface.handlers.shop_settings.get_shop_ids_with_complete_token_status",
            new=AsyncMock(return_value=set()),
        ), patch(
            "app.client_bot.user_interface.handlers.shop_settings.ShopsListPage"
        ) as mock_shops_list_page:
            mock_shops_list_page.return_value = AsyncMock()

            await delete_wb_user_cabinet(
                callback,
                callbacks.DeleteWbUserCabinet(wb_user_cabinet_original_id=uc.id),
                bot,
            )

            mock_shops_list_page.assert_called_once()
            call_args = mock_shops_list_page.call_args
            assert call_args[0][0] == bot
            assert call_args[0][1] == 88884
            assert len(call_args[0]) >= 4
            assert call_args[0][3] is not None
            mock_shops_list_page.return_value.assert_awaited_once()
