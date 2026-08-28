"""Unit tests for keyword_settings AdvSetting load helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.client_bot.user_interface.handlers.keyword_settings import (
    _load_adv_setting,
    _load_adv_setting_with_cabinet_in_session,
    _notify_adv_setting_not_found,
)


pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


async def test_load_adv_setting_returns_none_when_missing() -> None:
    """Missing AdvSetting row must return None, not a fake casted value."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)

    adv = await _load_adv_setting(session, adv_original_id=999)
    assert adv is None


async def test_load_adv_setting_with_cabinet_returns_none_when_missing() -> None:
    """Missing AdvSetting with cabinet load must return None."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)

    adv = await _load_adv_setting_with_cabinet_in_session(session, adv_original_id=999)
    assert adv is None


async def test_notify_adv_setting_not_found_sends_user_message() -> None:
    """User-facing miss text is sent to the chat."""
    bot = AsyncMock()
    await _notify_adv_setting_not_found(bot, chat_id=42)
    bot.send_message.assert_awaited_once()
    assert "Не удалось найти рекламную кампанию" in bot.send_message.await_args.args[1]
