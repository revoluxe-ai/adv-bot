"""RED regression: A2 «Изменить значение» must open numeric-entry (FINDING-PBH-002).

UX contract (telegram-ux-contract.md): action ``auto_bid_edit`` on A2
«opens numeric-entry sub-flow for Auto bid draft value».

Current production ``on_auto_bid_edit`` is a TODO stub: alert
«подflow — TODO в следующем apply», no numeric entry, draft[``auto_bid``]
never mutated — user can only confirm default CPM.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
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
    CahAutoBidEdit,
    ConfirmStep,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_draft import (
    load_draft,
    save_draft,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_keyboards import (
    build_a2_keyboard,
)

_TODO_STUB_MARKERS = (
    "TODO в следующем apply",
    "подflow — TODO",
)

_ENTRY_DRAFT_FLAGS = (
    "auto_bid_entry_open",
    "awaiting_auto_bid_input",
    "awaiting_auto_bid_numeric",
    "numeric_entry_open",
    "waiting_auto_bid",
    "auto_bid_numeric_entry",
)


def _make_fsm() -> FSMContext:
    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=1, user_id=1)
    return FSMContext(storage=storage, key=key)


def _make_adv(*, cpm: float = 120.0) -> SimpleNamespace:
    return SimpleNamespace(
        id=42,
        adv_id=4242,
        bot_active=True,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
        card_ab_hold_phase=CardAbHoldPhase.AWAITING_AUTO_BID_CONFIRM.value,
        card_ab_hold_confirmed_keywords_json=["alpha"],
        card_ab_hold_confirmed_target_places_json={"alpha": 5},
        card_ab_hold_generation=0,
        card_ab_hold_sync_status=None,
        card_ab_hold_degraded=False,
        cpm=cpm,
    )


def _make_query() -> MagicMock:
    msg = MagicMock(spec=Message)
    msg.edit_text = AsyncMock()
    msg.answer = AsyncMock()
    msg.bot = AsyncMock()
    query = MagicMock()
    query.message = msg
    query.answer = AsyncMock()
    query.bot = AsyncMock()
    query.from_user = SimpleNamespace(id=1)
    return query


def _callback(*, adv_id: int = 42, revision: int = 1) -> CahAutoBidEdit:
    return CahAutoBidEdit(
        adv_setting_original_id=adv_id,
        step=ConfirmStep.A2.value,
        revision=revision,
    )


def _user_notice_texts(query: MagicMock) -> list[str]:
    """Тексты user-visible notice (message.answer / bot.send_message), не CallbackQuery.answer."""
    texts: list[str] = []
    for mock in (
        getattr(query.message, "answer", None),
        getattr(query, "bot", None) and getattr(query.bot, "send_message", None),
        getattr(getattr(query.message, "bot", None), "send_message", None),
        getattr(query, "answer", None),  # legacy / forbidden path — still scan for TODO stub
    ):
        if mock is None or not hasattr(mock, "await_args_list"):
            continue
        for call in mock.await_args_list:
            if call.args:
                # bot.send_message(chat_id, text) — text is args[1]
                if mock is getattr(getattr(query, "bot", None), "send_message", None) or mock is getattr(
                    getattr(query.message, "bot", None), "send_message", None
                ):
                    if len(call.args) >= 2:
                        texts.append(str(call.args[1]))
                    elif "text" in call.kwargs:
                        texts.append(str(call.kwargs["text"]))
                else:
                    texts.append(str(call.args[0]))
            elif "text" in call.kwargs:
                texts.append(str(call.kwargs["text"]))
    return texts


def _todo_stub_alert_present(query: MagicMock) -> bool:
    return any(
        any(marker in text for marker in _TODO_STUB_MARKERS)
        for text in _user_notice_texts(query)
    )


async def _numeric_entry_opened(
    state: FSMContext,
    draft: dict[str, Any],
    query: MagicMock,
) -> bool:
    """Observable signals that numeric-entry sub-flow was opened (impl-agnostic)."""
    if await state.get_state() is not None:
        return True
    if any(bool(draft.get(flag)) for flag in _ENTRY_DRAFT_FLAGS):
        return True
    if query.message.edit_text.await_count > 0:
        return True
    if query.message.answer.await_count > 0:
        return True
    if query.bot.send_message.await_count > 0:
        return True
    if query.message.bot.send_message.await_count > 0:
        return True
    return False


async def _try_apply_numeric_to_draft(
    state: FSMContext,
    adv: SimpleNamespace,
    new_bid: float,
) -> bool:
    """Invoke a production apply path for A2 numeric entry if one exists."""
    message = SimpleNamespace(
        text=str(int(new_bid)),
        chat=SimpleNamespace(id=1),
        from_user=SimpleNamespace(id=1),
        bot=AsyncMock(),
        answer=AsyncMock(),
    )
    for name in (
        "on_auto_bid_numeric_message",
        "on_auto_bid_value_entered",
        "apply_auto_bid_draft_input",
        "apply_auto_bid_numeric_entry",
    ):
        fn = getattr(confirm_handlers, name, None)
        if fn is None or not callable(fn):
            continue
        try:
            await fn(message, state)
        except TypeError:
            try:
                await fn(message, state, adv)
            except TypeError:
                await fn(message, state, int(adv.id))
        draft = await load_draft(state, int(adv.id))
        if draft.get("auto_bid") is not None and float(draft["auto_bid"]) == float(
            new_bid
        ):
            return True
    return False


@pytest.mark.unit
def test_a2_keyboard_exposes_auto_bid_edit_button() -> None:
    """Sibling: A2 keyboard already exposes «Изменить значение» (CahAutoBidEdit)."""
    kb = build_a2_keyboard(adv_id=42, revision=3, auto_bid=120.0)
    texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "Изменить значение" in texts
    expected = CahAutoBidEdit(
        adv_setting_original_id=42,
        step=ConfirmStep.A2.value,
        revision=3,
    ).pack()
    packed = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert expected in packed


@pytest.mark.unit
@pytest.mark.asyncio
async def test_on_auto_bid_edit_does_not_todo_alert() -> None:
    """FINDING-PBH-002: edit must not answer alert «подflow — TODO в следующем apply»."""
    state = _make_fsm()
    adv = _make_adv()
    query = _make_query()
    callback = _callback()

    with (
        patch.object(
            confirm_handlers, "_load_adv", new=AsyncMock(return_value=adv)
        ),
        patch.object(
            confirm_handlers, "is_card_ab_hold_ui_visible", return_value=True
        ),
        patch.object(
            confirm_handlers, "_check_stale", new=AsyncMock(return_value=False)
        ),
        patch.object(
            confirm_handlers, "_render_for_adv", new=AsyncMock()
        ),
    ):
        await confirm_handlers.on_auto_bid_edit(query, callback, state)

    query.answer.assert_not_awaited()
    assert not _todo_stub_alert_present(query), (
        "FINDING-PBH-002: on_auto_bid_edit answered TODO stub alert "
        f"{_user_notice_texts(query)!r}; UX requires numeric-entry sub-flow, not TODO"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_on_auto_bid_edit_opens_numeric_entry_subflow() -> None:
    """FINDING-PBH-002: auto_bid_edit must open numeric-entry (not alert-only dead end)."""
    state = _make_fsm()
    adv = _make_adv()
    query = _make_query()
    callback = _callback()

    with (
        patch.object(
            confirm_handlers, "_load_adv", new=AsyncMock(return_value=adv)
        ),
        patch.object(
            confirm_handlers, "is_card_ab_hold_ui_visible", return_value=True
        ),
        patch.object(
            confirm_handlers, "_check_stale", new=AsyncMock(return_value=False)
        ),
        patch.object(
            confirm_handlers, "_render_for_adv", new=AsyncMock()
        ),
    ):
        await confirm_handlers.on_auto_bid_edit(query, callback, state)

    query.answer.assert_not_awaited()
    assert not _todo_stub_alert_present(query), (
        "FINDING-PBH-002: TODO stub alert is not numeric-entry "
        f"(answers={_user_notice_texts(query)!r})"
    )
    draft = await load_draft(state, int(adv.id))
    opened = await _numeric_entry_opened(state, draft, query)
    assert opened, (
        "FINDING-PBH-002: on_auto_bid_edit did not open numeric-entry sub-flow "
        "(no FSM state, draft entry flag, or prompt message); "
        "user cannot enter a new Auto bid"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_auto_bid_edit_flow_can_update_draft_auto_bid() -> None:
    """FINDING-PBH-002: after edit, draft['auto_bid'] must be mutable before confirm."""
    state = _make_fsm()
    adv = _make_adv(cpm=120.0)
    query = _make_query()
    callback = _callback()
    draft0 = await load_draft(state, int(adv.id))
    assert draft0.get("auto_bid") is None

    with (
        patch.object(
            confirm_handlers, "_load_adv", new=AsyncMock(return_value=adv)
        ),
        patch.object(
            confirm_handlers, "is_card_ab_hold_ui_visible", return_value=True
        ),
        patch.object(
            confirm_handlers, "_check_stale", new=AsyncMock(return_value=False)
        ),
        patch.object(
            confirm_handlers, "_render_for_adv", new=AsyncMock()
        ),
    ):
        await confirm_handlers.on_auto_bid_edit(query, callback, state)

    query.answer.assert_not_awaited()
    assert not _todo_stub_alert_present(query), (
        "FINDING-PBH-002: TODO stub leaves draft auto_bid immutable "
        f"(answers={_user_notice_texts(query)!r})"
    )

    draft_mid = await load_draft(state, int(adv.id))
    opened = await _numeric_entry_opened(state, draft_mid, query)
    assert opened, (
        "FINDING-PBH-002: without numeric-entry open, draft['auto_bid'] cannot "
        "be updated via the edit affordance"
    )

    new_bid = 250.0
    applied = await _try_apply_numeric_to_draft(state, adv, new_bid)
    if not applied:
        # Allow fix that writes draft immediately inside on_auto_bid_edit
        # after collecting a value via an inline path; still require mutation.
        draft_direct = await load_draft(state, int(adv.id))
        if draft_direct.get("auto_bid") is not None:
            applied = float(draft_direct["auto_bid"]) == new_bid
        else:
            # Last resort for fixes that expose a draft-setter used by the sub-flow:
            # if entry is open, production may expect a follow-up save — but RED
            # requires an actual apply path, not test-side save_draft forgery.
            applied = False

    assert applied, (
        "FINDING-PBH-002: no path from auto_bid_edit numeric-entry to mutate "
        "draft['auto_bid'] (still "
        f"{(await load_draft(state, int(adv.id))).get('auto_bid')!r}); "
        "user stuck confirming default CPM only"
    )
    draft_final = await load_draft(state, int(adv.id))
    assert float(draft_final["auto_bid"]) == new_bid
    assert confirm_handlers._draft_auto_bid(draft_final, adv) == new_bid


@pytest.mark.unit
@pytest.mark.asyncio
async def test_draft_auto_bid_feeds_a2_display_when_set() -> None:
    """Sibling: once draft auto_bid is set, A2 SoT uses it (not only adv.cpm)."""
    state = _make_fsm()
    adv = _make_adv(cpm=120.0)
    draft = await load_draft(state, int(adv.id))
    draft["auto_bid"] = 333.0
    await save_draft(state, int(adv.id), draft)
    loaded = await load_draft(state, int(adv.id))
    assert confirm_handlers._draft_auto_bid(loaded, adv) == 333.0
    kb = build_a2_keyboard(
        adv_id=int(adv.id),
        revision=int(loaded.get("revision") or 1),
        auto_bid=confirm_handlers._draft_auto_bid(loaded, adv),
    )
    texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert any("333" in t for t in texts)
