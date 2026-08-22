"""Тесты admin-кнопки разбора V3-решения в клавиатуре карточки ключа."""

from __future__ import annotations

import pytest

from app.client_bot import const
from app.client_bot.user_interface.views.keyboards import get_keyword_setting_keyboard
from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
)


def _keyword(*, ks_id: int = 10) -> KeywordSetting:
    return KeywordSetting(id=ks_id, text="test", hard_status=const.AUTO_MODE)


def _adv(*, bot_active: bool = True) -> AdvSetting:
    return AdvSetting(
        id=1,
        adv_id=100,
        bot_active=bot_active,
        nmids=[519358830],
    )


def _button_texts(markup) -> list[str]:
    return [
        btn.text
        for row in markup.inline_keyboard
        for btn in row
    ]


@pytest.mark.unit
def test_trace_button_visible_v3_admin_good() -> None:
    markup = get_keyword_setting_keyboard(
        _keyword(),
        _adv(bot_active=True),
        page=2,
        telegram_user_id=const.ADMINS[0],
        keyword_display_status=KeywordStatus.GOOD,
    )
    texts = _button_texts(markup)
    assert "🔎 Почему бот включил?" in texts


@pytest.mark.unit
def test_trace_button_visible_v3_admin_bad() -> None:
    markup = get_keyword_setting_keyboard(
        _keyword(),
        _adv(bot_active=True),
        page=1,
        telegram_user_id=const.ADMINS[0],
        keyword_display_status=KeywordStatus.BAD,
    )
    texts = _button_texts(markup)
    assert "🔎 Почему бот не включил?" in texts


@pytest.mark.unit
def test_trace_button_hidden_non_v3() -> None:
    markup = get_keyword_setting_keyboard(
        _keyword(),
        _adv(bot_active=False),
        page=1,
        telegram_user_id=const.ADMINS[0],
        keyword_display_status=KeywordStatus.GOOD,
    )
    texts = _button_texts(markup)
    assert not any("🔎 Почему бот" in t for t in texts)


@pytest.mark.unit
def test_trace_button_hidden_without_admin() -> None:
    markup = get_keyword_setting_keyboard(
        _keyword(),
        _adv(bot_active=True),
        page=1,
        telegram_user_id=999999999,
        keyword_display_status=KeywordStatus.GOOD,
    )
    texts = _button_texts(markup)
    assert not any("🔎 Почему бот" in t for t in texts)


@pytest.mark.unit
def test_trace_button_hidden_without_telegram_user_id() -> None:
    markup = get_keyword_setting_keyboard(
        _keyword(),
        _adv(bot_active=True),
        page=1,
        keyword_display_status=KeywordStatus.GOOD,
    )
    texts = _button_texts(markup)
    assert not any("🔎 Почему бот" in t for t in texts)


@pytest.mark.unit
def test_trace_button_hidden_without_display_status() -> None:
    markup = get_keyword_setting_keyboard(
        _keyword(),
        _adv(bot_active=True),
        page=1,
        telegram_user_id=const.ADMINS[0],
    )
    texts = _button_texts(markup)
    assert not any("🔎 Почему бот" in t for t in texts)
