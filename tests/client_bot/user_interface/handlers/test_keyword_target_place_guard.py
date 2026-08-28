"""Integration tests for manual keyword target place guard."""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.user_interface import states
from app.client_bot.user_interface.handlers import keyword_settings
from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from tests.helpers.telegram_message_asserts import (
    assert_html_is_telegram_safe,
    assert_message_contains_required_phrases,
    assert_message_within_telegram_limit,
    assert_no_raw_technical_text,
)

pytestmark = pytest.mark.integration


class _MockSessionMaker:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def __call__(self, read_only: bool = False) -> "_MockSessionMaker":
        return self

    async def __aenter__(self) -> AsyncSession:
        return self._session

    async def __aexit__(self, *args: object) -> None:
        pass


class _FakeState:
    def __init__(self, data: dict[str, int] | None = None) -> None:
        self.data: dict[str, int] = dict(data or {})
        self.state_calls: list[object] = []

    async def update_data(self, **kwargs: int | None) -> None:
        self.data.update(kwargs)

    async def get_data(self) -> dict[str, int]:
        return dict(self.data)

    async def set_state(self, state: object = None) -> None:
        self.state_calls.append(state)


def _message_stub(*, text: str, chat_id: int = 42, user_id: int = 1001) -> SimpleNamespace:
    """Telegram Message-shaped stub: chat + from_user required by happy-path handler."""
    return SimpleNamespace(
        chat=SimpleNamespace(id=chat_id),
        text=text,
        from_user=SimpleNamespace(id=user_id),
    )


async def _create_keyword(
    session: AsyncSession, *, auto_update_target_place: bool
) -> tuple[int, int]:
    cabinet = WBCabinet(
        shop_id=f"shop_{datetime.now().timestamp()}",
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
        expiration_time=datetime.now() + timedelta(days=7),
    )
    adv = AdvSetting(
        adv_id=int(datetime.now().timestamp() * 1000000) % 2_000_000_000,
        name="adv_keyword_target",
        wb_cabinet=cabinet,
        active_status="started",
        bot_active=False,
        auto_update_target_place=auto_update_target_place,
    )
    session.add_all([cabinet, adv])
    await session.flush()
    keyword = KeywordSetting(text="alpha", adv_setting_id=adv.id, target_place=4)
    session.add(keyword)
    await session.commit()
    return adv.id, keyword.id


async def _get_keyword(session: AsyncSession, keyword_id: int) -> KeywordSetting:
    session.expire_all()
    result = await session.execute(select(KeywordSetting).where(KeywordSetting.id == keyword_id))
    return result.scalar_one()


@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_change_keyword_target_place_callback_is_blocked_when_auto_update_enabled(
    async_session: AsyncSession,
) -> None:
    _adv_id, keyword_id = await _create_keyword(
        async_session, auto_update_target_place=True
    )
    state = _FakeState()
    bot = AsyncMock()
    callback_query = SimpleNamespace(message=SimpleNamespace(chat=SimpleNamespace(id=42)))
    callback_data = SimpleNamespace(keyword_setting_original_id=keyword_id)
    mock_sm = _MockSessionMaker(async_session)
    prompt = AsyncMock()

    with patch(
        "app.client_bot.user_interface.handlers.keyword_settings._sm",
        mock_sm,
    ), patch(
        "app.client_bot.user_interface.handlers.keyword_settings.messages.KeywordTargetPlacePrompt",
        MagicMock(return_value=prompt),
    ):
        await keyword_settings.change_keyword_target_place(
            callback_query, callback_data, bot, state
        )

    bot.send_message.assert_awaited_once()
    locked_text = bot.send_message.await_args.args[1]
    assert_message_within_telegram_limit(locked_text)
    assert_html_is_telegram_safe(locked_text)
    assert_message_contains_required_phrases(
        locked_text,
        [
            "автообновление target_place",
            "Max CPM остаётся доступным",
        ],
    )
    assert_no_raw_technical_text(locked_text)
    prompt.assert_not_awaited()
    assert state.state_calls[-1] is None


@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_keyword_target_place_submit_is_blocked_when_auto_update_enabled(
    async_session: AsyncSession,
) -> None:
    _adv_id, keyword_id = await _create_keyword(
        async_session, auto_update_target_place=True
    )
    state = _FakeState({"keyword_setting_for_target_place": keyword_id})
    bot = AsyncMock()
    message = _message_stub(text="9")
    mock_sm = _MockSessionMaker(async_session)

    with patch(
        "app.client_bot.user_interface.handlers.keyword_settings._sm",
        mock_sm,
    ):
        await keyword_settings.keyword_target_place_value(message, bot, state)

    updated = await _get_keyword(async_session, keyword_id)
    assert updated.target_place == 4
    bot.send_message.assert_awaited_once()
    locked_text = bot.send_message.await_args.args[1]
    assert_message_within_telegram_limit(locked_text)
    assert_html_is_telegram_safe(locked_text)
    assert_message_contains_required_phrases(
        locked_text,
        [
            "автообновление target_place",
            "Max CPM остаётся доступным",
        ],
    )
    assert_no_raw_technical_text(locked_text)
    assert state.data["keyword_setting_for_target_place"] is None
    assert state.state_calls[-1] is None


@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_keyword_target_place_submit_updates_value_when_auto_update_disabled(
    async_session: AsyncSession,
) -> None:
    _adv_id, keyword_id = await _create_keyword(
        async_session, auto_update_target_place=False
    )
    state = _FakeState(
        {"keyword_setting_for_target_place": keyword_id, "last_keyword_setting_page": 1}
    )
    bot = AsyncMock()
    message = _message_stub(text="9", user_id=1001)
    mock_sm = _MockSessionMaker(async_session)
    updated_message = AsyncMock()
    keyword_screen = AsyncMock()
    keyword_screen_cls = MagicMock(return_value=keyword_screen)

    with patch(
        "app.client_bot.user_interface.handlers.keyword_settings._sm",
        mock_sm,
    ), patch(
        "app.client_bot.user_interface.handlers.keyword_settings.messages.KeywordTargetPlaceUpdated",
        MagicMock(return_value=updated_message),
    ), patch(
        "app.client_bot.user_interface.handlers.keyword_settings.messages.KeywordSettingMessage",
        keyword_screen_cls,
    ):
        await keyword_settings.keyword_target_place_value(message, bot, state)

    updated = await _get_keyword(async_session, keyword_id)
    assert updated.target_place == 9
    updated_message.assert_awaited_once()
    keyword_screen_cls.assert_called_once_with(
        bot, 42, keyword_id, 1, telegram_user_id=1001
    )
    keyword_screen.assert_awaited_once()
