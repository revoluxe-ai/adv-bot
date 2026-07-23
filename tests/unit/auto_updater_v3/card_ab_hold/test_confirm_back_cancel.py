"""Unit-тесты Back vs Cancel в confirm-draft FSM (§24.2, ux contract §§7–8)."""

from __future__ import annotations

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_callbacks import (
    ConfirmStep,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_draft import (
    close_cancel_dialog,
    discard_edit_draft_only,
    get_revision,
    load_draft,
    mark_summary_visible,
    open_cancel_dialog,
    reset_draft,
    toggle_keyword_inclusion,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_keyboards import (
    build_s1_keyboard,
)


def _make_fsm() -> FSMContext:
    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=1, user_id=1)
    return FSMContext(storage=storage, key=key)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_back_preserves_keyword_toggle_draft() -> None:
    """Back (summary) сохраняет toggles и page; revision увеличивается."""
    state = _make_fsm()
    adv_id = 42
    await toggle_keyword_inclusion(state, adv_id, "alpha")
    draft = await load_draft(state, adv_id)
    draft["page"] = 2
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_draft import (
        save_draft,
    )

    await save_draft(state, adv_id, draft)
    rev_before = await get_revision(state, adv_id)
    await mark_summary_visible(state, adv_id, return_step=ConfirmStep.S1)
    draft_after = await load_draft(state, adv_id)
    assert draft_after["summary_visible"] is True
    assert draft_after["return_step"] == ConfirmStep.S1.value
    assert draft_after["keyword_included"]["alpha"] is False
    assert draft_after["page"] == 2
    assert await get_revision(state, adv_id) == rev_before + 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cancel_dialog_is_separate_from_back() -> None:
    """Cancel открывает поддиалог; Back-кнопка и Cancel — разные callback_data."""
    state = _make_fsm()
    adv_id = 7
    revision = await get_revision(state, adv_id)
    kb = build_s1_keyboard(
        adv_id=adv_id,
        all_keywords=["kw"],
        draft=await load_draft(state, adv_id),
        revision=revision,
        page=0,
    )
    texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "← Назад" in texts
    assert "Отмена" in texts
    back_data = next(
        btn.callback_data
        for row in kb.inline_keyboard
        for btn in row
        if btn.text == "← Назад"
    )
    cancel_data = next(
        btn.callback_data
        for row in kb.inline_keyboard
        for btn in row
        if btn.text == "Отмена"
    )
    assert back_data != cancel_data
    await open_cancel_dialog(state, adv_id)
    draft = await load_draft(state, adv_id)
    assert draft["cancel_dialog_open"] is True
    await close_cancel_dialog(state, adv_id)
    draft = await load_draft(state, adv_id)
    assert draft["cancel_dialog_open"] is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_s1b_cancel_discards_edit_keeps_structure() -> None:
    """S1b cancel_confirm_yes: сброс edit-draft, return_step → S3."""
    state = _make_fsm()
    adv_id = 99
    draft = await load_draft(state, adv_id)
    draft["return_step"] = ConfirmStep.S1B.value
    draft["keyword_included"] = {"a": False}
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_draft import (
        save_draft,
    )

    await save_draft(state, adv_id, draft)
    await discard_edit_draft_only(state, adv_id)
    draft = await load_draft(state, adv_id)
    assert draft["keyword_included"] == {}
    assert draft["return_step"] == ConfirmStep.S3.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fresh_epoch_cancel_resets_draft() -> None:
    """Abort fresh attempt: reset_draft возвращает defaults."""
    state = _make_fsm()
    adv_id = 5
    await toggle_keyword_inclusion(state, adv_id, "x")
    await reset_draft(state, adv_id)
    draft = await load_draft(state, adv_id)
    assert draft["keyword_included"] == {}
    assert draft["revision"] == 1
