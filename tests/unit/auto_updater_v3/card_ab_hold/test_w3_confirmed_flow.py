"""Unit-тесты W3-confirmed UX между TP confirm и A1 (ux contract §7)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    CardAbHoldPhase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
    confirm_handlers,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_callbacks import (
    CahConfirmBack,
    CahTpConfirmAll,
    ConfirmStep,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_draft import (
    is_w3_confirmed_visible,
    load_draft,
    should_show_w3_confirmed_read_only,
)


def _make_fsm() -> FSMContext:
    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=1, user_id=1)
    return FSMContext(storage=storage, key=key)


def _make_adv(*, phase: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=42,
        adv_id=4242,
        bot_active=True,
        automatic_version=3,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
        card_ab_hold_phase=phase,
        card_ab_hold_confirmed_keywords_json=["alpha", "beta"],
        card_ab_hold_confirmed_target_places_json={"alpha": 5, "beta": 8},
        card_ab_hold_factual_positions_json={"alpha": 7.0, "beta": 10.0},
        card_ab_hold_generation=0,
        card_ab_hold_sync_status=None,
        card_ab_hold_degraded=False,
        cpm=120.0,
    )


def _adv_after_tp_confirm(adv: SimpleNamespace) -> SimpleNamespace:
    """Adv после durable confirm_target_places (phase → A1 gate)."""
    return SimpleNamespace(
        **{
            **adv.__dict__,
            "card_ab_hold_phase": (
                CardAbHoldPhase.AWAITING_AUTO_PARTICIPATION_CONFIRM.value
            ),
        }
    )


def _make_query() -> MagicMock:
    msg = MagicMock(spec=Message)
    msg.edit_text = AsyncMock()
    query = MagicMock()
    query.message = msg
    query.answer = AsyncMock()
    return query


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tp_confirm_all_sets_w3_confirmed_and_renders_read_only() -> None:
    """После tp_confirm_all показывается W3-confirmed, не A1."""
    state = _make_fsm()
    adv = _make_adv(phase=CardAbHoldPhase.AWAITING_TP_CONFIRM.value)
    adv_after = _adv_after_tp_confirm(adv)
    query = _make_query()
    callback_data = CahTpConfirmAll(
        adv_setting_original_id=adv.id,
        step=ConfirmStep.W3_PROPOSE.value,
        revision=1,
        page=0,
    )

    with (
        patch.object(
            confirm_handlers,
            "_load_adv",
            new=AsyncMock(side_effect=[adv, adv_after]),
        ),
        patch.object(
            confirm_handlers,
            "confirm_target_places",
            new=AsyncMock(),
        ),
        patch.object(
            confirm_handlers,
            "is_card_ab_hold_ui_visible",
            return_value=True,
        ),
        patch.object(
            confirm_handlers,
            "_check_stale",
            new=AsyncMock(return_value=False),
        ),
    ):
        await confirm_handlers.on_tp_confirm_all(query, callback_data, state)

    draft = await load_draft(state, adv.id)
    assert is_w3_confirmed_visible(draft) is True
    edit_args = query.message.edit_text.await_args
    assert edit_args is not None
    text = edit_args.args[0] if edit_args.args else edit_args.kwargs.get("text", "")
    assert "зафиксированы для текущей эпохи" in text
    assert "Участие Auto" not in text
    kb = edit_args.kwargs.get("reply_markup")
    button_texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "Продолжить →" in button_texts


@pytest.mark.unit
@pytest.mark.asyncio
async def test_back_from_a1_lands_on_w3_confirmed_not_propose() -> None:
    """Back с A1 → W3-confirmed (read-only), не editable W3-propose и не summary."""
    state = _make_fsm()
    adv = _make_adv(
        phase=CardAbHoldPhase.AWAITING_AUTO_PARTICIPATION_CONFIRM.value
    )
    query = _make_query()
    callback_data = CahConfirmBack(
        adv_setting_original_id=adv.id,
        step=ConfirmStep.A1.value,
        revision=1,
        page=0,
    )

    with (
        patch.object(
            confirm_handlers,
            "_load_adv",
            new=AsyncMock(side_effect=[adv, adv]),
        ),
        patch.object(
            confirm_handlers,
            "is_card_ab_hold_ui_visible",
            return_value=True,
        ),
        patch.object(
            confirm_handlers,
            "_check_stale",
            new=AsyncMock(return_value=False),
        ),
    ):
        await confirm_handlers.on_back(query, callback_data, state)

    draft = await load_draft(state, adv.id)
    assert is_w3_confirmed_visible(draft) is True
    assert draft.get("summary_visible") is not True
    edit_args = query.message.edit_text.await_args
    text = edit_args.args[0] if edit_args.args else edit_args.kwargs.get("text", "")
    assert "зафиксированы для текущей эпохи" in text
    assert "предложенная цель" not in text
    assert "Участие Auto" not in text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_render_after_restart_shows_w3_confirmed_from_durable_tp() -> None:
    """Restart recovery: пустой FSM + durable TP + A1 phase → W3-confirmed (§7)."""
    state = _make_fsm()
    adv = _make_adv(
        phase=CardAbHoldPhase.AWAITING_AUTO_PARTICIPATION_CONFIRM.value
    )
    query = _make_query()
    draft = await load_draft(state, adv.id)
    assert is_w3_confirmed_visible(draft) is False
    assert should_show_w3_confirmed_read_only(adv, draft) is True

    with patch.object(
        confirm_handlers,
        "is_card_ab_hold_ui_visible",
        return_value=True,
    ):
        await confirm_handlers._render_for_adv(query, adv, state)

    edit_args = query.message.edit_text.await_args
    assert edit_args is not None
    text = edit_args.args[0] if edit_args.args else edit_args.kwargs.get("text", "")
    assert "зафиксированы для текущей эпохи" in text
    assert "Участие Auto" not in text
    kb = edit_args.kwargs.get("reply_markup")
    button_texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "Продолжить →" in button_texts
