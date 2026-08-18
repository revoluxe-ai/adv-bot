"""Unit tests for white-list mode toggle free/paid guards."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.ui_access import UiAccessMode
from app.client_bot.user_interface.handlers.white_list_mode_toggle import (
    toggle_white_list_mode,
)
from app.modules.common_slaves.wildberries.models.white_list_mode import WhiteListMode
from app.modules.white_list_mode_settings.telegram.main_callback import (
    WhiteListModeToggle,
)
from tests.helpers.telegram_message_asserts import (
    assert_message_contains_required_phrases,
    assert_message_within_telegram_limit,
    assert_no_raw_technical_text,
)


class _FakeSession:
    def __init__(self, adv_setting: SimpleNamespace) -> None:
        self.adv_setting = adv_setting
        self.executed_updates: list[object] = []
        self.commits = 0

    async def execute(self, stmt: object) -> SimpleNamespace:
        if "Update" in type(stmt).__name__:
            self.executed_updates.append(stmt)
            value = stmt.compile().params["white_list_mode"]
            self.adv_setting.white_list_mode = value
        return SimpleNamespace(scalar_one=lambda: self.adv_setting)

    async def commit(self) -> None:
        self.commits += 1


class _FakeSessionMaker:
    def __init__(self, adv_setting: SimpleNamespace) -> None:
        self.session = _FakeSession(adv_setting)
        self.read_only: bool | None = None

    def __call__(self, *, read_only: bool = False) -> "_FakeSessionMaker":
        self.read_only = read_only
        return self

    async def __aenter__(self) -> _FakeSession:
        return self.session

    async def __aexit__(self, *args: object) -> None:
        return None


def _callback_query() -> SimpleNamespace:
    return SimpleNamespace(
        from_user=SimpleNamespace(id=777),
        message=SimpleNamespace(chat=SimpleNamespace(id=42)),
    )


@pytest.mark.asyncio
async def test_free_guard_blocks_replace_on_trim_callback() -> None:
    adv = SimpleNamespace(id=1, adv_id=101, white_list_mode=WhiteListMode.ABOVE_MIN_RATING)
    session_maker = _FakeSessionMaker(adv)
    bot = AsyncMock()
    screen = AsyncMock()

    with patch(
        "app.client_bot.user_interface.handlers.white_list_mode_toggle.sm",
        session_maker,
    ), patch(
        "app.client_bot.user_interface.handlers.white_list_mode_toggle._resolve_white_list_mode_ui_access",
        MagicMock(return_value=UiAccessMode.FREE),
    ), patch(
        "app.client_bot.user_interface.handlers.white_list_mode_toggle.WhiteListModeMenuMessage",
        MagicMock(return_value=screen),
    ):
        await toggle_white_list_mode(
            _callback_query(),
            WhiteListModeToggle(
                new_mode=WhiteListMode.REPLACE_ON_TRIM.name,
                adv_setting_original_id=1,
            ),
            bot,
            AsyncMock(),
        )

    assert adv.white_list_mode == WhiteListMode.ABOVE_MIN_RATING
    assert session_maker.read_only is False
    assert session_maker.session.executed_updates == []
    assert session_maker.session.commits == 0
    bot.send_message.assert_awaited_once()
    text = bot.send_message.await_args.args[1]
    assert_message_within_telegram_limit(text)
    assert_message_contains_required_phrases(
        text,
        ["доступен только в платном автоуправлении"],
    )
    assert_no_raw_technical_text(text)
    screen.assert_awaited_once()


@pytest.mark.asyncio
async def test_free_allows_above_min_rating_callback() -> None:
    adv = SimpleNamespace(
        id=1,
        adv_id=101,
        white_list_mode=WhiteListMode.ACTIVE_ONLY_WHITE_LIST,
    )
    session_maker = _FakeSessionMaker(adv)
    bot = AsyncMock()
    screen = AsyncMock()

    with patch(
        "app.client_bot.user_interface.handlers.white_list_mode_toggle.sm",
        session_maker,
    ), patch(
        "app.client_bot.user_interface.handlers.white_list_mode_toggle._resolve_white_list_mode_ui_access",
        MagicMock(return_value=UiAccessMode.FREE),
    ), patch(
        "app.client_bot.user_interface.handlers.white_list_mode_toggle.WhiteListModeMenuMessage",
        MagicMock(return_value=screen),
    ):
        await toggle_white_list_mode(
            _callback_query(),
            WhiteListModeToggle(
                new_mode=WhiteListMode.ABOVE_MIN_RATING.name,
                adv_setting_original_id=1,
            ),
            bot,
            AsyncMock(),
        )

    assert adv.white_list_mode == WhiteListMode.ABOVE_MIN_RATING
    assert session_maker.read_only is False
    assert len(session_maker.session.executed_updates) == 1
    assert session_maker.session.commits == 1
    bot.send_message.assert_awaited_once()
    text = bot.send_message.await_args.args[1]
    assert_message_within_telegram_limit(text)
    assert_message_contains_required_phrases(text, ["Выбран режим Above Min Rating."])
    assert_no_raw_technical_text(text)
    screen.assert_awaited_once()


@pytest.mark.asyncio
async def test_free_allows_active_only_white_list_callback() -> None:
    adv = SimpleNamespace(id=1, adv_id=101, white_list_mode=WhiteListMode.ABOVE_MIN_RATING)
    session_maker = _FakeSessionMaker(adv)
    bot = AsyncMock()
    screen = AsyncMock()

    with patch(
        "app.client_bot.user_interface.handlers.white_list_mode_toggle.sm",
        session_maker,
    ), patch(
        "app.client_bot.user_interface.handlers.white_list_mode_toggle._resolve_white_list_mode_ui_access",
        MagicMock(return_value=UiAccessMode.FREE),
    ), patch(
        "app.client_bot.user_interface.handlers.white_list_mode_toggle.WhiteListModeMenuMessage",
        MagicMock(return_value=screen),
    ):
        await toggle_white_list_mode(
            _callback_query(),
            WhiteListModeToggle(
                new_mode=WhiteListMode.ACTIVE_ONLY_WHITE_LIST.name,
                adv_setting_original_id=1,
            ),
            bot,
            AsyncMock(),
        )

    assert adv.white_list_mode == WhiteListMode.ACTIVE_ONLY_WHITE_LIST
    assert session_maker.read_only is False
    assert len(session_maker.session.executed_updates) == 1
    assert session_maker.session.commits == 1
    bot.send_message.assert_awaited_once()
    text = bot.send_message.await_args.args[1]
    assert_message_within_telegram_limit(text)
    assert_message_contains_required_phrases(
        text,
        ["Выбран режим Active Only White List."],
    )
    assert_no_raw_technical_text(text)
    screen.assert_awaited_once()


@pytest.mark.asyncio
async def test_parent_hands_write_session_to_child() -> None:
    """Родитель открывает ``sm(read_only=False)`` и передает session child."""
    session = MagicMock()
    session_maker = MagicMock()
    session_maker.__aenter__ = AsyncMock(return_value=session)
    session_maker.__aexit__ = AsyncMock(return_value=False)
    child = AsyncMock()
    bot = AsyncMock()
    callback = _callback_query()
    callback_data = WhiteListModeToggle(
        new_mode=WhiteListMode.ABOVE_MIN_RATING.name,
        adv_setting_original_id=1,
    )

    with (
        patch(
            "app.client_bot.user_interface.handlers.white_list_mode_toggle.sm",
            MagicMock(return_value=session_maker),
        ) as sm_mock,
        patch(
            "app.client_bot.user_interface.handlers.white_list_mode_toggle"
            ".toggle_white_list_mode_in_session",
            child,
        ),
    ):
        await toggle_white_list_mode(callback, callback_data, bot, AsyncMock())

    sm_mock.assert_called_once_with(read_only=False)
    child.assert_awaited_once_with(
        session,
        callback,
        callback_data,
        bot,
    )
