"""Mock-only handoff proofs for batch-A PG seams.

Тесты проверяют, что parent-хендлеры открывают session с явным
``read_only=...`` и передают её в соответствующие ``*_in_session`` children.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers.adv_setting import adv_setting
from app.client_bot.user_interface.handlers import keyword_settings
from app.client_bot.user_interface.handlers import set_common_bid_manual

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

MODULE_ADV = "app.client_bot.user_interface.handlers.adv_setting.adv_setting"
MODULE_KEYWORD = "app.client_bot.user_interface.handlers.keyword_settings"
MODULE_COMMON_BID = "app.client_bot.user_interface.handlers.set_common_bid_manual"


class _MockSessionMaker:
    """Capture the requested read-only polarity and return a fixed session."""

    def __init__(self, session: AsyncMock) -> None:
        self.session = session
        self.calls: list[bool] = []

    def __call__(self, read_only: bool = False) -> "_MockSessionMaker":
        self.calls.append(read_only)
        return self

    async def __aenter__(self) -> AsyncMock:
        return self.session

    async def __aexit__(self, *args: object) -> None:
        return None


def _callback(chat_id: int = 101) -> SimpleNamespace:
    return SimpleNamespace(message=SimpleNamespace(chat=SimpleNamespace(id=chat_id)))


async def test_turn_adv_on_parent_passes_session_to_child() -> None:
    """turn_adv_on должен передавать WRITE session в child helper."""
    session = AsyncMock()
    callback = _callback()
    callback_data = SimpleNamespace(
        wb_user_cabinet_original_id=77,
        adv_original_id=55,
    )
    bot = AsyncMock()
    state = AsyncMock()
    child = AsyncMock()
    session_maker = _MockSessionMaker(session)

    with (
        patch(f"{MODULE_ADV}.sm", session_maker),
        patch(f"{MODULE_ADV}.turn_adv_on_in_session", child),
    ):
        await adv_setting.turn_adv_on(callback, state, callback_data, bot)

    assert session_maker.calls == [False]
    child.assert_awaited_once_with(session, callback, state, callback_data, bot)


async def test_change_keyword_target_place_parent_passes_session_to_child() -> None:
    """change_keyword_target_place должен открывать read-only session."""
    session = AsyncMock()
    callback_query = _callback()
    callback_data = SimpleNamespace(keyword_setting_original_id=11)
    bot = AsyncMock()
    state = AsyncMock()
    child = AsyncMock()
    session_maker = _MockSessionMaker(session)

    with (
        patch(f"{MODULE_KEYWORD}._sm", session_maker),
        patch(f"{MODULE_KEYWORD}.change_keyword_target_place_in_session", child),
    ):
        await keyword_settings.change_keyword_target_place(
            callback_query,
            callback_data,
            bot,
            state,
        )

    assert session_maker.calls == [True]
    child.assert_awaited_once_with(session, callback_query, callback_data, bot, state)


async def test_keyword_target_place_value_parent_passes_session_to_child() -> None:
    """keyword_target_place_value должен открывать WRITE session."""
    session = AsyncMock()
    message = SimpleNamespace(chat=SimpleNamespace(id=101), text="10")
    bot = AsyncMock()
    state = AsyncMock()
    child = AsyncMock()
    session_maker = _MockSessionMaker(session)

    with (
        patch(f"{MODULE_KEYWORD}._sm", session_maker),
        patch(f"{MODULE_KEYWORD}.keyword_target_place_value_in_session", child),
    ):
        await keyword_settings.keyword_target_place_value(message, bot, state)

    assert session_maker.calls == [False]
    child.assert_awaited_once_with(session, message, bot, state)


async def test_set_common_bid_manual_start_parent_passes_session_to_child() -> None:
    """set_common_bid_manual_start должен открывать read-only session."""
    session = AsyncMock()
    callback = _callback()
    callback_data = SimpleNamespace(
        adv_setting_original_id=21,
        wb_user_cabinet_original_id=22,
    )
    bot = AsyncMock()
    state = AsyncMock()
    child = AsyncMock()
    session_maker = _MockSessionMaker(session)

    with (
        patch(f"{MODULE_COMMON_BID}.sm", session_maker),
        patch(f"{MODULE_COMMON_BID}.set_common_bid_manual_start_in_session", child),
    ):
        await set_common_bid_manual.set_common_bid_manual_start(
            callback,
            callback_data,
            bot,
            state,
        )

    assert session_maker.calls == [True]
    child.assert_awaited_once_with(session, callback, callback_data, bot, state)


async def test_set_common_bid_manual_apply_parent_passes_session_to_child() -> None:
    """set_common_bid_manual_apply должен открывать read-only session."""
    session = AsyncMock()
    message = SimpleNamespace(chat=SimpleNamespace(id=101), text="100")
    bot = AsyncMock()
    state = AsyncMock()
    child = AsyncMock()
    session_maker = _MockSessionMaker(session)

    with (
        patch(f"{MODULE_COMMON_BID}.sm", session_maker),
        patch(f"{MODULE_COMMON_BID}.set_common_bid_manual_apply_in_session", child),
    ):
        await set_common_bid_manual.set_common_bid_manual_apply(message, bot, state)

    assert session_maker.calls == [True]
    child.assert_awaited_once_with(session, message, bot, state)


async def test_reload_adv_setting_menu_parent_passes_session_to_child() -> None:
    """_reload_adv_setting_menu opens ``sm(read_only=True)`` → load entities child."""
    session = AsyncMock()
    bot = AsyncMock()
    cabinet = SimpleNamespace(id=10)
    adv = SimpleNamespace(id=1)
    child = AsyncMock(return_value=(cabinet, adv))
    menu_page = AsyncMock()
    session_maker = _MockSessionMaker(session)

    with (
        patch(f"{MODULE_COMMON_BID}.sm", session_maker),
        patch(f"{MODULE_COMMON_BID}.load_adv_setting_menu_entities_in_session", child),
        patch(f"{MODULE_COMMON_BID}.AdvSettingMenu", MagicMock(return_value=menu_page)),
    ):
        await set_common_bid_manual._reload_adv_setting_menu(bot, 111, 10, 1)

    assert session_maker.calls == [True]
    child.assert_awaited_once_with(session, 10, 1)
    menu_page.assert_awaited_once()
