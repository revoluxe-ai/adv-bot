"""Unit-тесты: ручное изменение target_place ↔ A/B Hold structural freeze.

Spec ``card-ab-hold-mode`` / decision §3: при ``PENDING_SETUP`` / ``ACTIVE``
ручной Telegram write ``KeywordSetting.target_place`` MUST NOT проходить до PG;
при ``OFF`` — прежнее поведение сохраняется.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers.keyword_settings import (
    keyword_target_place_value,
)

_HANDLER = "app.client_bot.user_interface.handlers.keyword_settings"


def _keyword_setting(*, mode: str, target_place: int = 5) -> SimpleNamespace:
    """Stub KeywordSetting + AdvSetting для AB Hold / OFF write-path.

    ``auto_update_target_place=False`` — чтобы handler дошёл до AB Hold /
    OFF asserts (auto-update gate покрыт отдельно в
    ``test_keyword_target_place_guard.py``).
    """
    return SimpleNamespace(
        id=1,
        target_place=target_place,
        adv_setting=SimpleNamespace(
            card_ab_hold_mode=mode,
            auto_update_target_place=False,
        ),
    )


def _session_with_keyword(keyword: SimpleNamespace) -> AsyncMock:
    session = AsyncMock()
    session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=keyword))
    )
    session.commit = AsyncMock()
    return session


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["pending_setup", "active"])
async def test_keyword_target_place_blocked_on_ab_hold(mode: str) -> None:
    """PENDING_SETUP / ACTIVE → PG write target_place заблокирован."""
    keyword = _keyword_setting(mode=mode, target_place=5)
    session = _session_with_keyword(keyword)
    mock_sm = MagicMock()
    mock_sm.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

    message = SimpleNamespace(
        chat=SimpleNamespace(id=42),
        text="10",
        from_user=SimpleNamespace(id=7),
    )
    state = AsyncMock()
    state.get_data = AsyncMock(
        return_value={
            "keyword_setting_for_target_place": 1,
            "last_keyword_setting_page": 1,
        }
    )
    bot = AsyncMock()

    with patch(f"{_HANDLER}._sm", mock_sm), patch(
        f"{_HANDLER}.messages.KeywordSettingMessage", AsyncMock()
    ), patch(f"{_HANDLER}.messages.KeywordTargetPlaceUpdated", MagicMock()):
        await keyword_target_place_value(message, bot, state)

    assert keyword.target_place == 5
    session.commit.assert_not_called()
    sent = bot.send_message.await_args_list[0].args[1]
    assert "A/B Hold" in sent
    assert "заморожена" in sent.lower()
    state.set_state.assert_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_keyword_target_place_allowed_when_ab_hold_off() -> None:
    """OFF → target_place пишется в PG как раньше."""
    keyword = _keyword_setting(mode="off", target_place=5)
    session = _session_with_keyword(keyword)
    mock_sm = MagicMock()
    mock_sm.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_sm.return_value.__aexit__ = AsyncMock(return_value=None)

    message = SimpleNamespace(
        chat=SimpleNamespace(id=42),
        text="10",
        from_user=SimpleNamespace(id=7),
    )
    state = AsyncMock()
    state.get_data = AsyncMock(
        return_value={
            "keyword_setting_for_target_place": 1,
            "last_keyword_setting_page": 1,
        }
    )
    bot = AsyncMock()

    keyword_msg = AsyncMock()
    with patch(f"{_HANDLER}._sm", mock_sm), patch(
        f"{_HANDLER}.messages.KeywordSettingMessage",
        MagicMock(return_value=keyword_msg),
    ), patch(
        f"{_HANDLER}.messages.KeywordTargetPlaceUpdated",
        MagicMock(return_value=AsyncMock()),
    ):
        await keyword_target_place_value(message, bot, state)

    assert keyword.target_place == 10
    session.commit.assert_awaited_once()
    keyword_msg.assert_awaited_once()
