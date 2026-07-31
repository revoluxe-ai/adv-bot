"""Unit-тесты W3-confirmed UX между TP confirm и A1 (ux contract §7).

Также regression: W3 fact/proposed TP берутся из live read-model позиций,
а не из фантомного ``card_ab_hold_factual_positions_json`` на AdvSetting
(decision ``ab-hold-confirmed-epoch-parameters-sot`` §2).

На d999e49 suite пропустил баг, потому что fixture сам сажал фантомное
поле на SimpleNamespace — тесты зеленели без колонки, migration и write-path.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from sqlalchemy import inspect as sa_inspect

from app.modules.common_slaves.wildberries.models.models import AdvSetting
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
    msg.answer = AsyncMock()
    query = MagicMock()
    query.message = msg
    query.answer = AsyncMock()
    return query


_LIVE_POSITIONS = {"alpha": 14.4, "beta": 9.2}

_EPOCH_MIGRATION = (
    Path(__file__).resolve().parents[4]
    / "alembic_"
    / "versions"
    / "d0e1f2a3b4c5_add_card_ab_hold_epoch_lifecycle_fields.py"
)


@pytest.mark.unit
def test_advsetting_has_no_factual_positions_column_or_migration() -> None:
    """Reality gate: фантомного ``card_ab_hold_factual_positions_json`` нет в ORM/migration.

    Без этого fixture может посадить attr на stub и скрыть missing write-path.
    """
    cols = sa_inspect(AdvSetting).columns
    assert "card_ab_hold_factual_positions_json" not in cols
    assert not hasattr(AdvSetting, "card_ab_hold_factual_positions_json")
    migration = _EPOCH_MIGRATION.read_text(encoding="utf-8")
    assert "card_ab_hold_factual_positions_json" not in migration


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_factual_positions_uses_keyboard_read_model() -> None:
    """``_load_factual_positions`` читает live keyboard path, не AdvSetting attr."""
    adv = SimpleNamespace(
        id=42,
        card_ab_hold_factual_positions_json={"alpha": 99.0},
    )
    kw_alpha = SimpleNamespace(
        text="alpha", cluster_stat=SimpleNamespace(position=14.4)
    )
    kw_beta = SimpleNamespace(
        text="beta", cluster_stat=SimpleNamespace(position=9.2)
    )
    with patch(
        "app.client_bot.utils.get_keywords_for_keyboard",
        new=AsyncMock(return_value=[kw_alpha, kw_beta]),
    ) as mock_fetch:
        positions = await confirm_handlers._load_factual_positions(adv)

    mock_fetch.assert_awaited_once_with(adv)
    assert positions == {"alpha": 14.4, "beta": 9.2}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_factual_positions_uses_injected_keywords_loader() -> None:
    """Injectable ``keywords_loader`` bypasses default keyboard/CH path."""
    adv = SimpleNamespace(id=7)
    kw = SimpleNamespace(text="gamma", cluster_stat=SimpleNamespace(position=3.5))
    loader = AsyncMock(return_value=[kw])

    with patch(
        "app.client_bot.utils.get_keywords_for_keyboard",
        new=AsyncMock(side_effect=AssertionError("default loader must not run")),
    ):
        positions = await confirm_handlers._load_factual_positions(
            adv, keywords_loader=loader
        )

    loader.assert_awaited_once_with(adv)
    assert positions == {"gamma": 3.5}


@pytest.mark.unit
def test_tp_rows_use_passed_live_positions_not_adv_attr() -> None:
    """Fact/proposed берутся из positions-аргумента; фантомный attr на adv игнорируется."""
    adv = SimpleNamespace(
        card_ab_hold_confirmed_keywords_json=["alpha", "beta"],
        card_ab_hold_confirmed_target_places_json={},
        card_ab_hold_factual_positions_json={"alpha": 99.0, "beta": 99.0},
    )
    rows = confirm_handlers._tp_rows_from_adv(adv, _LIVE_POSITIONS)
    assert rows == [("alpha", 14, 14), ("beta", 9, 9)]


@pytest.mark.unit
def test_tp_rows_empty_positions_do_not_invent_facts() -> None:
    """Без live positions fact/target остаются 0 — не silent fallback к phantom attr."""
    adv = SimpleNamespace(
        card_ab_hold_confirmed_keywords_json=["alpha"],
        card_ab_hold_confirmed_target_places_json={},
        card_ab_hold_factual_positions_json={"alpha": 7.0},
    )
    rows = confirm_handlers._tp_rows_from_adv(adv, {})
    assert rows == [("alpha", 0, 0)]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tp_confirm_all_persists_proposed_from_live_positions() -> None:
    """tp_confirm_all пишет proposed TP из live positions, не нули."""
    state = _make_fsm()
    adv = _make_adv(phase=CardAbHoldPhase.AWAITING_TP_CONFIRM.value)
    adv.card_ab_hold_confirmed_target_places_json = {}
    adv_after = _adv_after_tp_confirm(adv)
    query = _make_query()
    callback_data = CahTpConfirmAll(
        adv_setting_original_id=adv.id,
        step=ConfirmStep.W3_PROPOSE.value,
        revision=1,
        page=0,
    )
    confirm_mock = AsyncMock()

    with (
        patch.object(
            confirm_handlers,
            "_load_adv",
            new=AsyncMock(side_effect=[adv, adv_after]),
        ),
        patch.object(
            confirm_handlers,
            "_load_factual_positions",
            new=AsyncMock(return_value=_LIVE_POSITIONS),
        ),
        patch.object(
            confirm_handlers,
            "confirm_target_places",
            new=confirm_mock,
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

    confirm_mock.assert_awaited_once_with(42, {"alpha": 14, "beta": 9})


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
            "_load_factual_positions",
            new=AsyncMock(return_value=_LIVE_POSITIONS),
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
            "_load_factual_positions",
            new=AsyncMock(return_value=_LIVE_POSITIONS),
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

    with (
        patch.object(
            confirm_handlers,
            "is_card_ab_hold_ui_visible",
            return_value=True,
        ),
        patch.object(
            confirm_handlers,
            "_load_factual_positions",
            new=AsyncMock(return_value=_LIVE_POSITIONS),
        ),
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
