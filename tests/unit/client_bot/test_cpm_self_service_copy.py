"""Regression tests for CPM and target_place self-service copy."""

from __future__ import annotations

from app.client_bot.user_interface.utils.target_place_messages import (
    get_auto_target_place_manual_change_locked_text,
)
from app.client_bot.user_interface.views.messages.messages import (
    AutoCPMSettingGetMaxCPM,
    AutoCPMSettingGetMinPosition,
    KeywordTargetPlacePrompt,
    ManualCPMSetting,
)
from tests.helpers.telegram_message_asserts import (
    assert_html_is_telegram_safe,
    assert_message_contains_required_phrases,
    assert_message_within_telegram_limit,
    assert_no_raw_technical_text,
)


def _assert_safe_message(text: str, phrases: list[str]) -> None:
    assert_message_within_telegram_limit(text)
    assert_html_is_telegram_safe(text)
    assert_message_contains_required_phrases(text, phrases)
    assert_no_raw_technical_text(text)


def test_cpm_and_target_place_prompts_explain_manual_mode() -> None:
    min_position_prompt = AutoCPMSettingGetMinPosition.__new__(AutoCPMSettingGetMinPosition)
    max_cpm_prompt = AutoCPMSettingGetMaxCPM.__new__(AutoCPMSettingGetMaxCPM)
    manual_cpm_prompt = ManualCPMSetting.__new__(ManualCPMSetting)
    keyword_prompt = KeywordTargetPlacePrompt.__new__(KeywordTargetPlacePrompt)
    keyword_prompt._current_value = "7"
    keyword_prompt._adv_default = "12"

    _assert_safe_message(
        min_position_prompt.text,
        [
            "целевая позиция",
            "Бесплатный инструмент",
        ],
    )
    _assert_safe_message(
        max_cpm_prompt.text,
        [
            "Max CPM",
            "верхний предел ставки",
            "Бесплатный инструмент",
        ],
    )
    _assert_safe_message(
        manual_cpm_prompt.text,
        [
            "Max CPM",
            "верхний предел ставки",
            "Бесплатный инструмент",
        ],
    )
    _assert_safe_message(
        keyword_prompt.text,
        [
            "целевая позиция",
            "место, которое вы хотите удерживать по ключу",
        ],
    )


def test_target_place_guard_mentions_auto_update_and_manual_max_cpm() -> None:
    text = get_auto_target_place_manual_change_locked_text()

    _assert_safe_message(
        text,
        [
            "автообновление target_place",
            "Max CPM остаётся доступным",
        ],
    )
