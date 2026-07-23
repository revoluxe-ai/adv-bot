"""S3 keyboard MUST include keyword_edit_open (§24.6, ux contract §5)."""

from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_callbacks import (
    CahKeywordEditOpen,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_keyboards import (
    build_s3_keyboard,
)


@pytest.mark.unit
def test_s3_keyboard_includes_keyword_edit_open_button() -> None:
    adv_id = 123
    revision = 4
    kb = build_s3_keyboard(adv_id=adv_id, revision=revision)
    button_texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "Изменить набор ключей" in button_texts
    expected = CahKeywordEditOpen(
        adv_setting_original_id=adv_id,
        step="s3",
        revision=revision,
    ).pack()
    callback_data = [
        btn.callback_data for row in kb.inline_keyboard for btn in row
    ]
    assert expected in callback_data


@pytest.mark.unit
def test_s3_keyboard_has_no_cancel_button() -> None:
    """S3 — status screen: Cancel не предлагается (§8)."""
    kb = build_s3_keyboard(adv_id=1, revision=1)
    texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "Отмена" not in texts
    assert "Выключить A/B тест" in texts
