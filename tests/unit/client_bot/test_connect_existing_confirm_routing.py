"""Регрессия FSM: confirm callback из списка РК матчится в waiting_*_adv_id через Dispatcher."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram import Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Chat, Message, Update, User

from app.client_bot.user_interface.handlers import connect_existing_advs
from app.client_bot.user_interface.states import ConnectExistingAdvsStates
from app.client_bot.user_interface.views import callbacks

BOT_ID = 1234567890
CHAT_ID = 100
USER_ID = 200
MODULE = "app.client_bot.user_interface.handlers.connect_existing_advs"


@pytest.fixture
def dispatcher_with_router() -> tuple[Dispatcher, MemoryStorage]:
    """Dispatcher с connect_existing router; сброс parent между тестами."""
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    router = connect_existing_advs.router
    if router.parent_router is not None:
        router._parent_router = None  # type: ignore[attr-defined]
    dp.include_router(router)
    yield dp, storage
    if router.parent_router is not None:
        router._parent_router = None  # type: ignore[attr-defined]


def _make_fsm(storage: MemoryStorage) -> FSMContext:
    """Изолированный FSM с ключом, совпадающим с private CallbackQuery."""
    return FSMContext(
        storage=storage,
        key=StorageKey(bot_id=BOT_ID, chat_id=CHAT_ID, user_id=USER_ID),
    )


def _make_callback_update(packed_data: str) -> Update:
    """Synthetic Update с CallbackQuery для feed_update."""
    user = User(id=USER_ID, is_bot=False, first_name="Test")
    chat = Chat(id=CHAT_ID, type="private")
    message = Message(
        message_id=1,
        date=datetime.now(tz=timezone.utc),
        chat=chat,
    )
    callback = CallbackQuery(
        id="cq-routing-1",
        from_user=user,
        chat_instance="test-instance",
        message=message,
        data=packed_data,
    )
    return Update(update_id=1, callback_query=callback)


def _make_bot() -> MagicMock:
    """Bot double с фиксированным id для StorageKey."""
    bot = MagicMock()
    bot.id = BOT_ID
    bot.send_message = AsyncMock()
    return bot


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_confirm_type2_routes_in_waiting_auto_adv_id(
    dispatcher_with_router: tuple[Dispatcher, MemoryStorage],
) -> None:
    """ce_confirm_t2 в waiting_auto_adv_id доходит до _save через StateFilter + Dispatcher."""
    dp, storage = dispatcher_with_router
    state = _make_fsm(storage)
    await state.set_state(ConnectExistingAdvsStates.waiting_auto_adv_id)
    await state.update_data(
        chosen_auction_adv_id=10,
        nmid=266109990,
        wb_cabinet_id=1,
        auto_candidates=[{"id": 34331280, "name": "test auto"}],
    )

    bot = _make_bot()
    packed = callbacks.ConnectExistingConfirmType2(adv_id=34331280).pack()
    update = _make_callback_update(packed)

    mock_save = AsyncMock()
    with patch(f"{MODULE}._save_connect_existing_finish", mock_save):
        await dp.feed_update(bot, update)

    mock_save.assert_awaited_once()
    save_args = mock_save.await_args.args
    assert save_args[4] == 10
    assert save_args[5] == 34331280


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_existing_confirm_type1_routes_in_waiting_auction_adv_id(
    dispatcher_with_router: tuple[Dispatcher, MemoryStorage],
) -> None:
    """ce_confirm_t1 в waiting_auction_adv_id доходит до auto menu через Dispatcher."""
    dp, storage = dispatcher_with_router
    state = _make_fsm(storage)
    await state.set_state(ConnectExistingAdvsStates.waiting_auction_adv_id)
    await state.update_data(
        nmid=266109990,
        wb_cabinet_id=1,
        auction_candidates=[{"id": 55, "name": "auction"}],
        auto_candidates=[],
        wb_user_cabinet_original_id=1,
    )

    bot = _make_bot()
    packed = callbacks.ConnectExistingConfirmType1(adv_id=55).pack()
    update = _make_callback_update(packed)

    mock_auto_menu = AsyncMock()
    with patch(f"{MODULE}._send_auto_choice_menu", mock_auto_menu):
        await dp.feed_update(bot, update)

    mock_auto_menu.assert_awaited_once()
