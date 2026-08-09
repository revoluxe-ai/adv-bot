"""Telegram payload limits для empty-keywords pause messages.

Authority: openspec/policies/telegram_bot_api_limits.md
"""

from __future__ import annotations

import pytest

from app.client_bot import const as client_bot_const
from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.messages import (
    build_empty_keywords_pause_message,
)

# Telegram Bot API limits (openspec/policies/telegram_bot_api_limits.md).
_TG_MESSAGE_TEXT_MAX = 4096


@pytest.mark.unit
def test_message_contains_reason_recheck_and_support_link() -> None:
    """T1/T6/5.2: причина + перепроверка; SUPPORT_LINK; без сырого enum."""
    text = build_empty_keywords_pause_message(
        campaign_name="Кампания",
        adv_id=123,
        include_support_link=True,
    )
    assert "паузу" in text.lower() or "пауз" in text.lower()
    assert "поиск" in text.lower()
    assert "ключ" in text.lower()
    assert "перепровер" in text.lower()
    assert client_bot_const.SUPPORT_LINK in text
    assert "empty_keywords" not in text
    assert "EMPTY_KEYWORDS" not in text
    assert "AutoReasonCode" not in text
    assert "pause_auto_campaign" not in text
    assert "pause_auction_campaign" not in text


@pytest.mark.unit
def test_message_worst_case_within_telegram_limit() -> None:
    """T2/T3: длинное имя РК ≤ 4096 символов."""
    long_name = "Ж" * 500 + " «Promo» " + "X" * 500
    text = build_empty_keywords_pause_message(
        campaign_name=long_name,
        adv_id=9_999_999_999,
        include_support_link=True,
    )
    assert len(text) <= _TG_MESSAGE_TEXT_MAX
    assert client_bot_const.SUPPORT_LINK in text


@pytest.mark.unit
def test_message_no_html_parse_mode_required() -> None:
    """T4: plain text — без незакрытых HTML-тегов / raw callback."""
    text = build_empty_keywords_pause_message(
        campaign_name='РК <script>alert(1)</script> & "q"',
        adv_id=1,
    )
    assert "<script>" in text  # plain text, не HTML parse_mode
    assert "callback_data" not in text


@pytest.mark.unit
def test_no_callback_buttons_in_surface() -> None:
    """T5: callback_data не добавляются этим change (только текст)."""
    text = build_empty_keywords_pause_message(campaign_name="A", adv_id=1)
    assert isinstance(text, str)
    assert len(text.encode("utf-8")) <= _TG_MESSAGE_TEXT_MAX
