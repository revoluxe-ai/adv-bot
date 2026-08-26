"""Integration tests for onboarding handlers: callback_start_registration, show_shops_list, shops_list_paginator."""

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from aiogram.types import CallbackQuery, Chat, Message, User as TelegramUser
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.client_bot.user_interface.handlers.start.start import (
    callback_start_registration,
    show_shops_list,
    shops_list_paginator,
)
from app.client_bot.user_interface.views.gate import (
    get_gate_message_text,
    get_gate_keyboard,
)
from app.client_bot.user_interface.handlers.shop_choice_message import (
    SHOPS_LIST_PAGE_TITLE,
)
from app.client_bot.user_interface.views import callbacks
from app.modules.common_slaves.wildberries.models import WBUserCabinet
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.settings.settings_master import Settings
from app.utils.db.models import User


pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.destructive_local]


async def _create_user_with_cabinets(
    async_session,
    user_telegram_id: int = 99991,
    passed_gate: bool = True,
    num_cabinets: int = 0,
) -> User:
    """Create user with optional WBUserCabinet(s)."""
    user = User(
        user_telegram_id=user_telegram_id,
        username="test_onboarding_user",
        passed_gate=passed_gate,
    )
    async_session.add(user)
    await async_session.flush()
    await async_session.refresh(user)

    for i in range(num_cabinets):
        cabinet = WBCabinet(
            shop_id=f"test_shop_{user_telegram_id}_{i}",
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
            name=f"Shop {i}",
        )
        async_session.add(uc)
        await async_session.flush()

    await async_session.commit()
    await async_session.refresh(user)
    stmt = (
        select(User)
        .options(joinedload(User.wb_user_cabinets).joinedload(WBUserCabinet.wb_cabinet))
        .where(User.user_telegram_id == user_telegram_id)
    )
    result = await async_session.execute(stmt)
    return result.unique().scalar_one()


def _make_callback(user_id: int, data: str, chat_id: int = 99991) -> CallbackQuery:
    """Create mock CallbackQuery."""
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = MagicMock(spec=TelegramUser)
    callback.from_user.id = user_id
    callback.data = data
    callback.message = MagicMock(spec=Message)
    callback.message.chat = MagicMock(spec=Chat)
    callback.message.chat.id = chat_id
    return callback


async def test_callback_start_registration_passed_gate_shows_main_menu(
    async_session,
    patch_start_and_token_services,
):
    """User passed_gate -> MainMenu shown (bot.send_message with get_main_text content)."""
    user = await _create_user_with_cabinets(async_session, 99992, passed_gate=True)
    bot = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()
    state.set_state = AsyncMock()

    callback = _make_callback(user.user_telegram_id, callbacks.Start().pack(), 99992)

    await callback_start_registration(callback, bot, state)

    bot.send_message.assert_awaited_once()
    call_kw = bot.send_message.call_args[1]
    assert "Экономическое управление" in call_kw["text"]
    assert call_kw["reply_markup"] is not None


async def test_callback_start_registration_not_passed_gate_shows_gate(
    async_session,
    patch_start_and_token_services,
):
    """User not passed_gate -> gate screen."""
    user = await _create_user_with_cabinets(async_session, 99993, passed_gate=False)
    bot = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()
    state.set_state = AsyncMock()

    callback = _make_callback(user.user_telegram_id, callbacks.Start().pack(), 99993)

    with patch.object(
        Settings, "invite_gate", PropertyMock(return_value=True)
    ), patch.object(
        Settings, "presentation_only", PropertyMock(return_value=False)
    ):
        await callback_start_registration(callback, bot, state)

    bot.send_message.assert_awaited_once()
    call_args, call_kw = bot.send_message.call_args
    text = call_kw.get("text", call_args[1] if len(call_args) > 1 else "")
    assert get_gate_message_text() in text or "Доступ" in text


async def test_show_shops_list_passed_gate_with_shops_shows_shops_list_page(
    async_session,
    patch_start_and_token_services,
):
    """User passed_gate with cabinets -> ShopsListPage with Add shop and shop buttons."""
    user = await _create_user_with_cabinets(
        async_session, 99994, passed_gate=True, num_cabinets=2
    )
    bot = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()
    state.set_state = AsyncMock()

    callback = _make_callback(
        user.user_telegram_id, callbacks.ShowShopsList().pack(), 99994
    )

    await show_shops_list(callback, bot, state)

    bot.send_message.assert_awaited_once()
    call_kw = bot.send_message.call_args[1]
    assert call_kw["text"] == SHOPS_LIST_PAGE_TITLE
    rows = call_kw["reply_markup"].inline_keyboard
    assert rows[0][0].text == "➕Добавить магазин"
    assert rows[-1][0].text == "Назад"
    assert len(rows) >= 4  # Add, 2 shops, Back


async def test_show_shops_list_not_passed_gate_shows_gate(
    async_session,
    patch_start_and_token_services,
):
    """User not passed_gate -> gate screen."""
    user = await _create_user_with_cabinets(async_session, 99995, passed_gate=False)
    bot = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()
    state.set_state = AsyncMock()

    callback = _make_callback(
        user.user_telegram_id, callbacks.ShowShopsList().pack(), 99995
    )

    with patch("app.client_bot.user_interface.handlers.start.start.settings") as mock_settings:
        mock_settings.invite_gate = True
        await show_shops_list(callback, bot, state)

    bot.send_message.assert_awaited_once()
    call_args, call_kw = bot.send_message.call_args
    text = call_kw.get("text", call_args[1] if len(call_args) > 1 else "")
    assert "Доступ" in text or get_gate_message_text()[:50] in text


async def test_shops_list_paginator_page2_shows_page2(
    async_session,
    patch_start_and_token_services,
):
    """page=2 with 25+ shops -> ShopsListPage with pagination."""
    user = await _create_user_with_cabinets(
        async_session, 99996, passed_gate=True, num_cabinets=25
    )
    bot = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()
    state.set_state = AsyncMock()

    callback = _make_callback(
        user.user_telegram_id,
        callbacks.ShopsListPaginator(page=2).pack(),
        99996,
    )
    callback_data = callbacks.ShopsListPaginator.unpack(callback.data)

    await shops_list_paginator(callback, callback_data, bot, state)

    bot.send_message.assert_awaited_once()
    call_kw = bot.send_message.call_args[1]
    assert call_kw["text"] == SHOPS_LIST_PAGE_TITLE
    rows = call_kw["reply_markup"].inline_keyboard
    paginator_found = False
    for row in rows:
        for btn in row:
            if btn.text == "⬅️ Назад" and "shops_list_pg:1" in (btn.callback_data or ""):
                paginator_found = True
                break
    assert paginator_found or any(
        "shops_list_pg" in str(getattr(btn, "callback_data", ""))
        for row in rows
        for btn in row
    )


async def test_shops_list_paginator_page0_normalized_to_page1(
    async_session,
    patch_start_and_token_services,
):
    """page=0 or negative -> normalized to page 1."""
    user = await _create_user_with_cabinets(
        async_session, 99997, passed_gate=True, num_cabinets=5
    )
    bot = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()
    state.set_state = AsyncMock()

    callback = _make_callback(
        user.user_telegram_id,
        callbacks.ShopsListPaginator(page=0).pack(),
        99997,
    )
    callback_data = callbacks.ShopsListPaginator.unpack(callback.data)
    assert callback_data.page == 0

    await shops_list_paginator(callback, callback_data, bot, state)

    bot.send_message.assert_awaited_once()
    call_kw = bot.send_message.call_args[1]
    assert call_kw["text"] == SHOPS_LIST_PAGE_TITLE


async def test_shops_list_paginator_not_passed_gate_shows_gate(
    async_session,
    patch_start_and_token_services,
):
    """Paginator with user not passed_gate -> gate screen."""
    user = await _create_user_with_cabinets(async_session, 99998, passed_gate=False)
    bot = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()
    state.set_state = AsyncMock()

    callback = _make_callback(
        user.user_telegram_id,
        callbacks.ShopsListPaginator(page=1).pack(),
        99998,
    )
    callback_data = callbacks.ShopsListPaginator.unpack(callback.data)

    with patch("app.client_bot.user_interface.handlers.start.start.settings") as mock_settings:
        mock_settings.invite_gate = True
        await shops_list_paginator(callback, callback_data, bot, state)

    bot.send_message.assert_awaited_once()
    call_args, call_kw = bot.send_message.call_args
    text = call_kw.get("text", call_args[1] if len(call_args) > 1 else "")
    assert "Доступ" in text or get_gate_message_text()[:50] in text
