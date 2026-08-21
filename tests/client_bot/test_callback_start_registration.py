"""Unit-тесты routing-веток ``callback_start_registration``.

Spec: ``callback-start-menu-return`` — callback Start = menu-return без
``create_user`` (PURE_READ). Покрывает missing-user non-write, minimal/gate/
full UI, admin/invite bypass и early-return без ``callback.message``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import CallbackQuery, Chat, Message, User as TelegramUser

from app.client_bot.user_interface.handlers.start.start import (
    callback_start_registration,
)
from app.client_bot.user_interface.views.gate import get_gate_message_text


def _make_callback(
    user_id: int,
    *,
    chat_id: int | None = None,
    username: str | None = "cb_user",
    with_message: bool = True,
) -> CallbackQuery:
    """Собрать mock CallbackQuery для start-flow."""
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = MagicMock(spec=TelegramUser)
    callback.from_user.id = user_id
    callback.from_user.username = username
    callback.data = "start"
    if not with_message:
        callback.message = None
        return callback
    resolved_chat_id = chat_id if chat_id is not None else user_id
    callback.message = MagicMock(spec=Message)
    callback.message.chat = MagicMock(spec=Chat)
    callback.message.chat.id = resolved_chat_id
    return callback


def _session_cm(session: AsyncMock) -> MagicMock:
    """Async context manager, отдающий session."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


@pytest.mark.asyncio
async def test_callback_start_registration_no_message_returns_after_clear() -> None:
    """Без callback.message — state.clear, UI не отправляется."""
    bot = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()
    callback = _make_callback(71001, with_message=False)

    session = AsyncMock()
    user = MagicMock()
    user.passed_gate = True

    mock_settings = MagicMock()
    mock_settings.invite_gate = True
    mock_settings.presentation_only = False
    mock_settings.extra_admin_telegram_ids = frozenset()

    with (
        patch(
            "app.client_bot.user_interface.handlers.start.start.sm",
            return_value=_session_cm(session),
        ),
        patch(
            "app.client_bot.user_interface.handlers.start.start._load_user_with_wb_cabinets_in_session",
            new_callable=AsyncMock,
            return_value=user,
        ),
        patch(
            "app.client_bot.user_interface.handlers.start.start.MainMenu",
        ) as mock_main_menu,
        patch(
            "app.client_bot.user_interface.handlers.start.start.settings",
            mock_settings,
        ),
        patch("app.client_bot.admin_access.settings", mock_settings),
    ):
        mock_main_menu.return_value = AsyncMock()
        await callback_start_registration(callback, bot, state)

    state.clear.assert_awaited_once()
    bot.send_message.assert_not_awaited()
    mock_main_menu.assert_not_called()


@pytest.mark.asyncio
async def test_callback_start_registration_missing_user_invite_gate_shows_gate_without_create() -> None:
    """Spec Missing user non-write: нет User + invite_gate → gate UI, create_user MUST NOT."""
    bot = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()
    telegram_id = 71002
    chat_id = 71002
    callback = _make_callback(telegram_id, chat_id=chat_id, username="new_cb_71002")

    session = AsyncMock()
    mock_settings = MagicMock()
    mock_settings.invite_gate = True
    mock_settings.presentation_only = False
    mock_settings.extra_admin_telegram_ids = frozenset()

    with (
        patch(
            "app.client_bot.user_interface.handlers.start.start.sm",
            return_value=_session_cm(session),
        ) as mock_sm,
        patch(
            "app.client_bot.user_interface.handlers.start.start._load_user_with_wb_cabinets_in_session",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.client_bot.user_interface.handlers.start.start.create_user",
            new_callable=AsyncMock,
            create=True,
        ) as mock_create_user,
        patch(
            "app.client_bot.user_interface.handlers.start.start.MainMenu",
        ) as mock_main_menu,
        patch(
            "app.client_bot.user_interface.handlers.start.start.settings",
            mock_settings,
        ),
        patch("app.client_bot.admin_access.settings", mock_settings),
    ):
        mock_main_menu.return_value = AsyncMock()
        await callback_start_registration(callback, bot, state)

    mock_sm.assert_called_with(read_only=True)
    mock_create_user.assert_not_awaited()
    bot.send_message.assert_awaited_once()
    send_args, send_kw = bot.send_message.call_args
    assert send_args[0] == chat_id
    assert get_gate_message_text() in (
        send_args[1] if len(send_args) > 1 else send_kw.get("text", "")
    )
    assert send_kw.get("reply_markup") is not None
    mock_main_menu.assert_not_called()


@pytest.mark.asyncio
async def test_callback_start_registration_missing_user_invite_gate_off_no_create() -> None:
    """Spec Missing user without invite gate: нет User + invite_gate off → без create и без full MainMenu."""
    bot = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()
    telegram_id = 71008
    chat_id = 71008
    callback = _make_callback(telegram_id, chat_id=chat_id)

    session = AsyncMock()
    mock_settings = MagicMock()
    mock_settings.invite_gate = False
    mock_settings.presentation_only = False
    mock_settings.extra_admin_telegram_ids = frozenset()

    with (
        patch(
            "app.client_bot.user_interface.handlers.start.start.sm",
            return_value=_session_cm(session),
        ),
        patch(
            "app.client_bot.user_interface.handlers.start.start._load_user_with_wb_cabinets_in_session",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.client_bot.user_interface.handlers.start.start.create_user",
            new_callable=AsyncMock,
            create=True,
        ) as mock_create_user,
        patch(
            "app.client_bot.user_interface.handlers.start.start.MainMenu",
        ) as mock_main_menu,
        patch(
            "app.client_bot.user_interface.handlers.start.start.settings",
            mock_settings,
        ),
        patch("app.client_bot.admin_access.settings", mock_settings),
    ):
        mock_main_menu.return_value = AsyncMock()
        await callback_start_registration(callback, bot, state)

    mock_create_user.assert_not_awaited()
    mock_main_menu.assert_not_called()
    bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_callback_start_registration_presentation_only_still_shows_gate() -> None:
    """Legacy PRESENTATION_ONLY=true + not passed_gate → gate, не minimal MainMenu."""
    bot = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()
    state.set_state = AsyncMock()
    telegram_id = 71003
    chat_id = 71003
    callback = _make_callback(telegram_id, chat_id=chat_id)

    session = AsyncMock()
    user = MagicMock()
    user.passed_gate = False

    mock_settings = MagicMock()
    mock_settings.invite_gate = True
    mock_settings.presentation_only = True
    mock_settings.extra_admin_telegram_ids = frozenset()

    with (
        patch(
            "app.client_bot.user_interface.handlers.start.start.sm",
            return_value=_session_cm(session),
        ),
        patch(
            "app.client_bot.user_interface.handlers.start.start._load_user_with_wb_cabinets_in_session",
            new_callable=AsyncMock,
            return_value=user,
        ),
        patch(
            "app.client_bot.user_interface.handlers.start.start.create_user",
            new_callable=AsyncMock,
            create=True,
        ) as mock_create_user,
        patch(
            "app.client_bot.user_interface.handlers.start.start.MainMenu",
        ) as mock_main_menu,
        patch(
            "app.client_bot.user_interface.handlers.start.start.settings",
            mock_settings,
        ),
        patch("app.client_bot.admin_access.settings", mock_settings),
    ):
        await callback_start_registration(callback, bot, state)

    mock_create_user.assert_not_awaited()
    mock_main_menu.assert_not_called()
    bot.send_message.assert_awaited_once()
    state.set_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_callback_start_registration_invite_gate_off_full_menu() -> None:
    """invite_gate=False + not passed_gate → полный MainMenu, не gate."""
    bot = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()
    telegram_id = 71004
    chat_id = 71004
    callback = _make_callback(telegram_id, chat_id=chat_id)

    session = AsyncMock()
    user = MagicMock()
    user.passed_gate = False

    mock_settings = MagicMock()
    mock_settings.invite_gate = False
    mock_settings.presentation_only = False
    mock_settings.extra_admin_telegram_ids = frozenset()

    with (
        patch(
            "app.client_bot.user_interface.handlers.start.start.sm",
            return_value=_session_cm(session),
        ),
        patch(
            "app.client_bot.user_interface.handlers.start.start._load_user_with_wb_cabinets_in_session",
            new_callable=AsyncMock,
            return_value=user,
        ),
        patch(
            "app.client_bot.user_interface.handlers.start.start.create_user",
            new_callable=AsyncMock,
            create=True,
        ) as mock_create_user,
        patch(
            "app.client_bot.user_interface.handlers.start.start.MainMenu",
        ) as mock_main_menu,
        patch(
            "app.client_bot.user_interface.handlers.start.start.settings",
            mock_settings,
        ),
        patch("app.client_bot.admin_access.settings", mock_settings),
    ):
        menu_instance = AsyncMock()
        mock_main_menu.return_value = menu_instance
        await callback_start_registration(callback, bot, state)

    mock_create_user.assert_not_awaited()
    mock_main_menu.assert_called_once_with(bot, chat_id, full_client_ui=True)
    menu_instance.assert_awaited_once()
    bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_callback_start_registration_admin_bypasses_gate() -> None:
    """Admin + not passed_gate + invite_gate → полный MainMenu (bypass gate)."""
    bot = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()
    telegram_id = 71005
    chat_id = 71005
    callback = _make_callback(telegram_id, chat_id=chat_id)

    session = AsyncMock()
    user = MagicMock()
    user.passed_gate = False

    mock_settings = MagicMock()
    mock_settings.invite_gate = True
    mock_settings.presentation_only = False
    mock_settings.extra_admin_telegram_ids = frozenset({telegram_id})

    with (
        patch(
            "app.client_bot.user_interface.handlers.start.start.sm",
            return_value=_session_cm(session),
        ),
        patch(
            "app.client_bot.user_interface.handlers.start.start._load_user_with_wb_cabinets_in_session",
            new_callable=AsyncMock,
            return_value=user,
        ),
        patch(
            "app.client_bot.user_interface.handlers.start.start.create_user",
            new_callable=AsyncMock,
            create=True,
        ) as mock_create_user,
        patch(
            "app.client_bot.user_interface.handlers.start.start.MainMenu",
        ) as mock_main_menu,
        patch(
            "app.client_bot.user_interface.handlers.start.start.settings",
            mock_settings,
        ),
        patch("app.client_bot.admin_access.settings", mock_settings),
        patch("app.client_bot.admin_access.const.ADMINS", []),
    ):
        menu_instance = AsyncMock()
        mock_main_menu.return_value = menu_instance
        await callback_start_registration(callback, bot, state)

    mock_create_user.assert_not_awaited()
    mock_main_menu.assert_called_once_with(bot, chat_id, full_client_ui=True)
    menu_instance.assert_awaited_once()
    bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_callback_start_registration_passed_gate_full_menu() -> None:
    """passed_gate=True → MainMenu(full_client_ui=True)."""
    bot = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()
    telegram_id = 71006
    chat_id = 71006
    callback = _make_callback(telegram_id, chat_id=chat_id)

    session = AsyncMock()
    user = MagicMock()
    user.passed_gate = True

    mock_settings = MagicMock()
    mock_settings.invite_gate = True
    mock_settings.presentation_only = False
    mock_settings.extra_admin_telegram_ids = frozenset()

    with (
        patch(
            "app.client_bot.user_interface.handlers.start.start.sm",
            return_value=_session_cm(session),
        ),
        patch(
            "app.client_bot.user_interface.handlers.start.start._load_user_with_wb_cabinets_in_session",
            new_callable=AsyncMock,
            return_value=user,
        ),
        patch(
            "app.client_bot.user_interface.handlers.start.start.create_user",
            new_callable=AsyncMock,
            create=True,
        ) as mock_create_user,
        patch(
            "app.client_bot.user_interface.handlers.start.start.MainMenu",
        ) as mock_main_menu,
        patch(
            "app.client_bot.user_interface.handlers.start.start.settings",
            mock_settings,
        ),
        patch("app.client_bot.admin_access.settings", mock_settings),
    ):
        menu_instance = AsyncMock()
        mock_main_menu.return_value = menu_instance
        await callback_start_registration(callback, bot, state)

    state.clear.assert_awaited_once()
    mock_create_user.assert_not_awaited()
    mock_main_menu.assert_called_once_with(bot, chat_id, full_client_ui=True)
    menu_instance.assert_awaited_once()
    bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_callback_start_registration_not_passed_gate_shows_gate() -> None:
    """invite_gate + not passed_gate + не admin → gate screen, не MainMenu."""
    bot = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()
    state.set_state = AsyncMock()
    telegram_id = 71007
    chat_id = 71007
    callback = _make_callback(telegram_id, chat_id=chat_id)

    session = AsyncMock()
    user = MagicMock()
    user.passed_gate = False

    mock_settings = MagicMock()
    mock_settings.invite_gate = True
    mock_settings.presentation_only = False
    mock_settings.extra_admin_telegram_ids = frozenset()

    with (
        patch(
            "app.client_bot.user_interface.handlers.start.start.sm",
            return_value=_session_cm(session),
        ),
        patch(
            "app.client_bot.user_interface.handlers.start.start._load_user_with_wb_cabinets_in_session",
            new_callable=AsyncMock,
            return_value=user,
        ),
        patch(
            "app.client_bot.user_interface.handlers.start.start.create_user",
            new_callable=AsyncMock,
            create=True,
        ) as mock_create_user,
        patch(
            "app.client_bot.user_interface.handlers.start.start.MainMenu",
        ) as mock_main_menu,
        patch(
            "app.client_bot.user_interface.handlers.start.start.settings",
            mock_settings,
        ),
        patch("app.client_bot.admin_access.settings", mock_settings),
        patch("app.client_bot.admin_access.const.ADMINS", []),
    ):
        mock_main_menu.return_value = AsyncMock()
        await callback_start_registration(callback, bot, state)

    mock_create_user.assert_not_awaited()
    bot.send_message.assert_awaited_once()
    send_args, send_kw = bot.send_message.call_args
    assert send_args[0] == chat_id
    assert get_gate_message_text() in (
        send_args[1] if len(send_args) > 1 else send_kw.get("text", "")
    )
    assert send_kw.get("reply_markup") is not None
    mock_main_menu.assert_not_called()
