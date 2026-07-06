"""Unit tests for white-list mode menu visibility by UI access."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.client_bot.ui_access import UiAccessMode
from app.modules.common_slaves.wildberries.models.white_list_mode import WhiteListMode
from app.modules.white_list_mode_settings.telegram.keyboards import (
    WhiteListModeKeyboards,
)
from app.modules.white_list_mode_settings.telegram.main_message import (
    WhiteListModeMenuMessage,
)
from tests.helpers.telegram_message_asserts import (
    assert_keyboard_has_buttons,
    assert_message_contains_required_phrases,
    assert_message_within_telegram_limit,
    assert_no_raw_technical_text,
    extract_button_texts,
)


def _adv(mode: WhiteListMode = WhiteListMode.ABOVE_MIN_RATING) -> SimpleNamespace:
    return SimpleNamespace(id=1, adv_id=101, white_list_mode=mode, bot_active=False)


@pytest.mark.unit
def test_free_white_list_mode_keyboard_shows_only_free_safe_modes() -> None:
    keyboard = WhiteListModeKeyboards(
        _adv(),
        UiAccessMode.FREE,
    ).build_keyboard()

    texts = extract_button_texts(keyboard)

    assert_keyboard_has_buttons(
        keyboard,
        [
            "✅ Свободная активация ключей",
            "Активация только ключей из БС (Рек для Ручной работы)",
            "Назад к настройкам АРК",
        ],
    )
    assert "Срезание хвоста" not in texts
    assert "Срезание хвоста с Замещением (Для АвтоУправления)" not in texts


@pytest.mark.unit
def test_paid_white_list_mode_keyboard_keeps_paid_modes_visible() -> None:
    keyboard = WhiteListModeKeyboards(
        _adv(WhiteListMode.REPLACE_ON_TRIM),
        UiAccessMode.PAID,
    ).build_keyboard()

    assert_keyboard_has_buttons(
        keyboard,
        [
            "Срезание хвоста",
            "✅ Срезание хвоста с Замещением (Для АвтоУправления)",
            "Активация только ключей из БС (Рек для Ручной работы)",
            "Свободная активация ключей",
            "Назад к настройкам АРК",
        ],
    )


@pytest.mark.unit
def test_free_white_list_mode_message_hides_replacement_copy() -> None:
    message = WhiteListModeMenuMessage.__new__(WhiteListModeMenuMessage)
    message._ui_access = UiAccessMode.FREE

    text = message.text

    assert_message_within_telegram_limit(text)
    assert_message_contains_required_phrases(
        text,
        [
            "Выберите режим работы белого списка",
            "Активация только ключей из БС",
            "Свободная активация ключей",
        ],
    )
    assert "замещением" not in text.lower()
    assert "срезания хвоста" not in text.lower()
    assert_no_raw_technical_text(text)


@pytest.mark.unit
def test_paid_white_list_mode_message_keeps_replacement_copy() -> None:
    message = WhiteListModeMenuMessage.__new__(WhiteListModeMenuMessage)
    message._ui_access = UiAccessMode.PAID

    text = message.text

    assert_message_within_telegram_limit(text)
    assert_message_contains_required_phrases(
        text,
        [
            "Срезание хвоста",
            "Срезание хвоста с замещением",
            "Активация только ключей из БС",
            "Свободная активация ключей",
        ],
    )
    assert_no_raw_technical_text(text)


@pytest.mark.asyncio
async def test_message_fallback_uses_bot_active_for_ui_access() -> None:
    message = WhiteListModeMenuMessage.__new__(WhiteListModeMenuMessage)
    message._adv_id = 101
    message._ui_access = None
    message._adv = None
    message._chat_id = 42
    message._bot = AsyncMock()

    async def _get_adv(_: int) -> SimpleNamespace:
        return SimpleNamespace(
            id=1,
            adv_id=101,
            white_list_mode=WhiteListMode.ABOVE_MIN_RATING,
            bot_active=False,
        )

    message._get_adv = _get_adv  # type: ignore[method-assign]

    with patch(
        "app.modules.white_list_mode_settings.telegram.main_message.TextWithKeyboard.__call__",
        AsyncMock(return_value=None),
    ):
        await message.__call__()

    assert message._ui_access == UiAccessMode.FREE
