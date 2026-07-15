"""§11: Telegram Enable idempotent while PENDING_SETUP / ACTIVE (decision §10).

Blocked: ACTIVE/PENDING Enable не demote и не пишет Redis ENTER.
Allowed: OFF Enable → путь ENTER (wiring: predicate false + handler order).
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
    handlers,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.callbacks import (
    CardAbHoldEnable,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.ui_access import (
    card_ab_hold_enable_noop_answer,
    is_card_ab_hold_enable_noop,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("mode", "expected_noop"),
    [
        (CardAbHoldMode.OFF.value, False),
        (CardAbHoldMode.PENDING_SETUP.value, True),
        (CardAbHoldMode.ACTIVE.value, True),
    ],
)
def test_enable_noop_predicate_matrix(mode: str, expected_noop: bool) -> None:
    """11.1: OFF → ENTER allowed; PENDING/ACTIVE → Enable no-op."""
    adv = SimpleNamespace(card_ab_hold_mode=mode, bot_active=True)
    assert is_card_ab_hold_enable_noop(adv) is expected_noop


@pytest.mark.unit
def test_enable_noop_answers_distinguish_active_and_pending() -> None:
    """UX: ACTIVE vs PENDING дают разные короткие answers."""
    active = SimpleNamespace(card_ab_hold_mode=CardAbHoldMode.ACTIVE.value)
    pending = SimpleNamespace(card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value)
    assert "включён" in card_ab_hold_enable_noop_answer(active)
    assert "подготовка" in card_ab_hold_enable_noop_answer(pending).lower()


@pytest.mark.unit
def test_enable_handler_checks_noop_before_enter_writes() -> None:
    """11.2 wiring: no-op gate до setattr PENDING / Redis ENTER / stats continue path."""
    src = inspect.getsource(handlers._handle_ab_hold_enable)
    assert "is_card_ab_hold_enable_noop" in src
    assert src.index("is_card_ab_hold_enable_noop") < src.index(
        "card_ab_hold_mode = CardAbHoldMode.PENDING_SETUP"
    )
    assert src.index("is_card_ab_hold_enable_noop") < src.index("set_signal")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enable_active_does_not_demote_or_signal_enter() -> None:
    """11.1 blocked: ACTIVE + Enable → mode ACTIVE, set_signal не вызывается."""
    adv = SimpleNamespace(
        id=7,
        adv_id=77,
        bot_active=True,
        card_ab_hold_mode=CardAbHoldMode.ACTIVE.value,
    )
    session = MagicMock()
    session.scalar = AsyncMock(return_value=adv)
    session.commit = AsyncMock()
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)

    query = MagicMock()
    query.answer = AsyncMock()
    query.message = None
    callback = CardAbHoldEnable(adv_setting_original_id=7)

    set_signal = AsyncMock()
    signal_cache = MagicMock()
    signal_cache.set_signal = set_signal

    with (
        patch.object(handlers, "sm", return_value=session_cm),
        patch.object(
            handlers,
            "CardAbHoldSignalRedisCache",
            return_value=signal_cache,
        ),
        patch.object(
            handlers,
            "evaluate_ab_hold_enable_stats",
            new_callable=AsyncMock,
        ) as eval_stats,
    ):
        await handlers.enable_card_ab_hold(query, callback)

    assert adv.card_ab_hold_mode == CardAbHoldMode.ACTIVE.value
    session.commit.assert_not_awaited()
    set_signal.assert_not_awaited()
    eval_stats.assert_not_awaited()
    query.answer.assert_awaited()
    assert "включён" in query.answer.await_args.args[0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enable_pending_does_not_rewrite_enter_signal() -> None:
    """11.1 blocked: PENDING + Enable → mode PENDING, Redis ENTER не переписывается."""
    adv = SimpleNamespace(
        id=8,
        adv_id=88,
        bot_active=True,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
    )
    session = MagicMock()
    session.scalar = AsyncMock(return_value=adv)
    session.commit = AsyncMock()
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)

    query = MagicMock()
    query.answer = AsyncMock()
    query.message = None
    callback = CardAbHoldEnable(adv_setting_original_id=8)

    set_signal = AsyncMock()
    with (
        patch.object(handlers, "sm", return_value=session_cm),
        patch.object(
            handlers,
            "CardAbHoldSignalRedisCache",
            return_value=MagicMock(set_signal=set_signal),
        ),
    ):
        await handlers.enable_card_ab_hold(query, callback)

    assert adv.card_ab_hold_mode == CardAbHoldMode.PENDING_SETUP.value
    session.commit.assert_not_awaited()
    set_signal.assert_not_awaited()
    assert "подготовка" in query.answer.await_args.args[0].lower()
