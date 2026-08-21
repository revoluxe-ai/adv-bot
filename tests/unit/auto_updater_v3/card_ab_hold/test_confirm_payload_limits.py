"""Telegram payload limits для confirm-flow A/B Hold (§24.4)."""

from __future__ import annotations

import pytest

from app.client_bot import const
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_callbacks import (
    CahAutoBidConfirm,
    CahAutoParticipationConfirm,
    CahCancelConfirmYes,
    CahConfirmBack,
    CahConfirmDisable,
    CahKeywordToggle,
    CahPageNav,
    CahTpConfirmAll,
    CahWarmupDurationPreset,
    ConfirmStep,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_keyboards import (
    build_a2_keyboard,
    build_s1_keyboard,
    build_s3_keyboard,
    build_w3_propose_keyboard,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_screens import (
    STALE_TOAST,
    build_s1_text,
    build_s3_text,
    build_w3_propose_text,
)

_TG_MESSAGE_TEXT_MAX = const.MAX_MESSAGE_LENGTH
_TG_CALLBACK_ANSWER_MAX = 200
_TG_CALLBACK_DATA_BYTES_MAX = 64
_WORST_CASE_ADV_ID = 2_147_483_647
_WORST_KEYWORD = "к" * 120


@pytest.mark.unit
def test_stale_toast_within_callback_answer_limit() -> None:
    assert len(STALE_TOAST) <= _TG_CALLBACK_ANSWER_MAX


@pytest.mark.unit
def test_worst_case_keyword_toggle_callback_bytes() -> None:
    packed = CahKeywordToggle(
        adv_setting_original_id=_WORST_CASE_ADV_ID,
        step=ConfirmStep.S1.value,
        revision=999_999,
        page=9,
        keyword_idx=99,
    ).pack()
    assert 1 <= len(packed.encode("utf-8")) <= _TG_CALLBACK_DATA_BYTES_MAX


@pytest.mark.unit
@pytest.mark.parametrize(
    "factory",
    [
        lambda: CahPageNav(
            adv_setting_original_id=_WORST_CASE_ADV_ID,
            step=ConfirmStep.W3_PROPOSE.value,
            revision=123456,
            page=5,
            direction="n",
        ).pack(),
        lambda: CahWarmupDurationPreset(
            adv_setting_original_id=_WORST_CASE_ADV_ID,
            step=ConfirmStep.S2.value,
            revision=1,
            hours=72,
        ).pack(),
        lambda: CahAutoParticipationConfirm(
            adv_setting_original_id=_WORST_CASE_ADV_ID,
            step=ConfirmStep.A1.value,
            revision=42,
            participates=1,
        ).pack(),
        lambda: CahAutoBidConfirm(
            adv_setting_original_id=_WORST_CASE_ADV_ID,
            step=ConfirmStep.A2.value,
            revision=42,
        ).pack(),
        lambda: CahCancelConfirmYes(
            adv_setting_original_id=_WORST_CASE_ADV_ID,
            step=ConfirmStep.S1.value,
            revision=7,
            page=3,
        ).pack(),
        lambda: CahConfirmBack(
            adv_setting_original_id=_WORST_CASE_ADV_ID,
            step=ConfirmStep.S2.value,
            revision=7,
            page=3,
        ).pack(),
    ],
)
def test_confirm_callback_data_bytes_worst_case(factory) -> None:
    packed = factory()
    assert 1 <= len(packed.encode("utf-8")) <= _TG_CALLBACK_DATA_BYTES_MAX


@pytest.mark.unit
def test_tp_and_disable_callback_data_bytes_worst_case() -> None:
    """S03/S08: TP confirm и EXIT callbacks остаются в лимите UTF-8 bytes."""
    callbacks = (
        CahTpConfirmAll(
            adv_setting_original_id=_WORST_CASE_ADV_ID,
            step=ConfirmStep.W3_PROPOSE.value,
            revision=999_999,
            page=99,
        ).pack(),
        CahConfirmDisable(
            adv_setting_original_id=_WORST_CASE_ADV_ID,
            step=ConfirmStep.S3.value,
            revision=999_999,
        ).pack(),
    )
    for packed in callbacks:
        assert 1 <= len(packed.encode("utf-8")) <= _TG_CALLBACK_DATA_BYTES_MAX


@pytest.mark.unit
def test_s1_screen_text_within_message_limit_worst_case() -> None:
    keywords = [_WORST_KEYWORD] * 10
    text = build_s1_text(
        keywords=keywords,
        page=0,
        total_pages=99,
        draft={"keyword_included": {kw: True for kw in keywords}},
    )
    assert len(text) <= _TG_MESSAGE_TEXT_MAX
    assert "{" not in text


@pytest.mark.unit
def test_w3_propose_screen_within_message_limit_worst_case() -> None:
    rows = [(_WORST_KEYWORD, 999, 888)] * 10
    text = build_w3_propose_text(rows=rows, page=0, total_pages=50)
    assert len(text) <= _TG_MESSAGE_TEXT_MAX


@pytest.mark.unit
def test_w3_exclusion_reasons_with_worst_case_unicode_stay_safe() -> None:
    """S05/S06: dynamic Cyrillic/emoji exclusions fit and contain no placeholders."""
    keyword = "ключ-🚀-" + "я" * 120
    exclusions = [
        (f"{keyword}-{index}", "фактическая позиция недоступна")
        for index in range(20)
    ]
    text = build_w3_propose_text(
        rows=[(keyword, 12, 12)],
        page=0,
        total_pages=1,
        exclusions=exclusions,
    )
    assert len(text) <= _TG_MESSAGE_TEXT_MAX
    assert "{" not in text
    assert "}" not in text
    assert "🚀" in text


@pytest.mark.unit
def test_w3_exclusions_are_bounded_for_arbitrary_volume() -> None:
    """Доказать лимит Telegram для реалистичного большого списка исключений."""
    exclusions = [
        (
            f"phrase-{index}-" + "я" * 100,
            "фактическая позиция недоступна",
        )
        for index in range(100)
    ]
    text = build_w3_propose_text(
        rows=[("valid-keyword", 12, 12)],
        page=0,
        total_pages=1,
        exclusions=exclusions,
    )

    assert len(text) <= _TG_MESSAGE_TEXT_MAX
    assert "phrase-0-" in text


@pytest.mark.unit
def test_s3_screen_within_message_limit() -> None:
    text = build_s3_text(started_at=None, duration_hours=72)
    assert len(text) <= _TG_MESSAGE_TEXT_MAX


@pytest.mark.unit
def test_s1_keyboard_all_callbacks_within_byte_limit() -> None:
    keywords = [f"phrase-{i}-{'x' * 40}" for i in range(25)]
    kb = build_s1_keyboard(
        adv_id=_WORST_CASE_ADV_ID,
        all_keywords=keywords,
        draft={"keyword_included": {}},
        revision=999,
        page=1,
    )
    for row in kb.inline_keyboard:
        for btn in row:
            assert btn.callback_data is not None
            assert (
                len(btn.callback_data.encode("utf-8")) <= _TG_CALLBACK_DATA_BYTES_MAX
            )


@pytest.mark.unit
def test_s3_and_a2_keyboards_callback_bytes() -> None:
    s3 = build_s3_keyboard(adv_id=_WORST_CASE_ADV_ID, revision=555)
    a2 = build_a2_keyboard(
        adv_id=_WORST_CASE_ADV_ID, revision=555, auto_bid=99999.0
    )
    w3 = build_w3_propose_keyboard(
        adv_id=_WORST_CASE_ADV_ID,
        rows=[("kw", 1, 2)] * 15,
        revision=555,
        page=0,
    )
    for kb in (s3, a2, w3):
        for row in kb.inline_keyboard:
            for btn in row:
                assert btn.callback_data is not None
                assert (
                    len(btn.callback_data.encode("utf-8"))
                    <= _TG_CALLBACK_DATA_BYTES_MAX
                )
