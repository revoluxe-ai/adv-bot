"""Gate-тесты scheduling / UI / interrupt / Excel (spec ``card-ab-hold-mode``)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.interrupt import (
    abort_ordinary_v3_if_enter_signaled,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.redis_coordination import (
    CardAbHoldLastAbortSnapshot,
    CardAbHoldSignalKind,
    CardAbHoldSignalSnapshot,
    SETUP_LOCK_KEY_PREFIX,
    setup_lock_redis_key,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.scheduling import (
    should_allow_bidder_on_ab_hold,
    should_allow_structural_act,
    should_run_ab_hold,
    should_run_ab_setup,
    should_schedule_ordinary_updater,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.ui_access import (
    can_enable_card_ab_hold,
    is_card_ab_hold_ui_visible,
)


@pytest.mark.unit
def test_scheduling_matrix_characterization_bot_active_like_off_baseline() -> None:
    """1.1: при OFF ordinary eligible; setup/hold нет; structural ACT ок."""
    mode = CardAbHoldMode.OFF
    assert should_schedule_ordinary_updater(mode) is True
    assert should_run_ab_setup(mode) is False
    assert should_run_ab_hold(mode) is False
    assert should_allow_structural_act(mode) is True
    assert should_allow_bidder_on_ab_hold(mode) is True


@pytest.mark.unit
@pytest.mark.parametrize(
    "mode",
    [CardAbHoldMode.PENDING_SETUP, CardAbHoldMode.ACTIVE],
)
def test_structural_freeze_gates_exclude_writes(mode: CardAbHoldMode) -> None:
    """1.4: PENDING/ACTIVE — structural ACT запрещён; ordinary нет."""
    assert should_allow_structural_act(mode) is False
    assert should_schedule_ordinary_updater(mode) is False


@pytest.mark.unit
def test_pending_schedules_setup_only() -> None:
    """1.4/4.3: PENDING_SETUP → setup, не hold, не ordinary."""
    mode = CardAbHoldMode.PENDING_SETUP
    assert should_run_ab_setup(mode) is True
    assert should_run_ab_hold(mode) is False
    assert should_schedule_ordinary_updater(mode) is False


@pytest.mark.unit
def test_active_schedules_hold_only() -> None:
    """HOLD path + bidder allowed (1.5)."""
    mode = CardAbHoldMode.ACTIVE
    assert should_run_ab_hold(mode) is True
    assert should_run_ab_setup(mode) is False
    assert should_allow_bidder_on_ab_hold(mode) is True
    assert should_allow_structural_act(mode) is False


@pytest.mark.unit
def test_exit_reopens_ordinary_target_place_eligible() -> None:
    """1.7: после EXIT (OFF) ordinary снова eligible; restore не нужен."""
    assert should_schedule_ordinary_updater(CardAbHoldMode.OFF) is True
    assert should_allow_structural_act(CardAbHoldMode.OFF) is True


@pytest.mark.unit
def test_paid_ui_visibility_paired() -> None:
    """1.3: bot_active False скрывает; True показывает / enable ok."""
    inactive = SimpleNamespace(bot_active=False, card_ab_hold_mode="off")
    active = SimpleNamespace(bot_active=True, card_ab_hold_mode="off")
    assert is_card_ab_hold_ui_visible(inactive) is False  # type: ignore[arg-type]
    assert can_enable_card_ab_hold(inactive) is False  # type: ignore[arg-type]
    assert is_card_ab_hold_ui_visible(active) is True  # type: ignore[arg-type]
    assert can_enable_card_ab_hold(active) is True  # type: ignore[arg-type]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_interrupt_enter_before_apply_sets_safe_abort(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """1.6: signal ENTER → abort True + LastAbort safe/can_continue."""
    adv = SimpleNamespace(adv_id=42)
    signal_cache = MagicMock()
    signal_cache.get_signal = AsyncMock(
        return_value=CardAbHoldSignalSnapshot(signal=CardAbHoldSignalKind.ENTER)
    )
    signal_cache.clear = AsyncMock()
    abort_cache = MagicMock()
    abort_cache.set_abort = AsyncMock()

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.interrupt.CardAbHoldSignalRedisCache",
        lambda _adv: signal_cache,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.interrupt.CardAbHoldLastAbortRedisCache",
        lambda _adv: abort_cache,
    )
    # Redis path must short-circuit before PG read.
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.interrupt._fetch_durable_card_ab_hold_mode",
        AsyncMock(side_effect=AssertionError("PG must not be read on ENTER")),
    )

    aborted = await abort_ordinary_v3_if_enter_signaled(adv)  # type: ignore[arg-type]
    assert aborted is True
    abort_cache.set_abort.assert_awaited_once()
    snap: CardAbHoldLastAbortSnapshot = abort_cache.set_abort.await_args.args[0]
    assert snap.safe is True
    assert snap.can_continue is True
    assert snap.reason == "enter_requested"
    signal_cache.clear.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_interrupt_without_enter_does_not_abort(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Interrupt без ENTER и PG OFF → apply path может продолжить."""
    adv = SimpleNamespace(adv_id=7, card_ab_hold_mode="off")
    signal_cache = MagicMock()
    signal_cache.get_signal = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.interrupt.CardAbHoldSignalRedisCache",
        lambda _adv: signal_cache,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.interrupt._fetch_durable_card_ab_hold_mode",
        AsyncMock(return_value=CardAbHoldMode.OFF),
    )
    assert await abort_ordinary_v3_if_enter_signaled(adv) is False  # type: ignore[arg-type]


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "pg_mode",
    [CardAbHoldMode.PENDING_SETUP, CardAbHoldMode.ACTIVE],
)
async def test_interrupt_aborts_on_durable_pg_freeze_without_redis(
    monkeypatch: pytest.MonkeyPatch,
    pg_mode: CardAbHoldMode,
) -> None:
    """Commit→Redis окно: Redis пуст, но PG уже PENDING/ACTIVE → abort до apply."""
    adv = SimpleNamespace(adv_id=99, card_ab_hold_mode="off")
    signal_cache = MagicMock()
    signal_cache.get_signal = AsyncMock(return_value=None)
    signal_cache.clear = AsyncMock()
    abort_cache = MagicMock()
    abort_cache.set_abort = AsyncMock()

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.interrupt.CardAbHoldSignalRedisCache",
        lambda _adv: signal_cache,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.interrupt.CardAbHoldLastAbortRedisCache",
        lambda _adv: abort_cache,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.interrupt._fetch_durable_card_ab_hold_mode",
        AsyncMock(return_value=pg_mode),
    )

    aborted = await abort_ordinary_v3_if_enter_signaled(adv)  # type: ignore[arg-type]
    assert aborted is True
    signal_cache.clear.assert_not_called()
    abort_cache.set_abort.assert_awaited_once()
    snap: CardAbHoldLastAbortSnapshot = abort_cache.set_abort.await_args.args[0]
    assert snap.reason == "durable_mode_freeze"
    assert snap.safe is True
    assert snap.can_continue is True
    assert adv.card_ab_hold_mode == pg_mode.value


@pytest.mark.unit
def test_setup_lock_redis_key_prefix() -> None:
    """3.3: ключ CardAbHoldSetupLock:{adv_id}."""
    assert setup_lock_redis_key(99) == f"{SETUP_LOCK_KEY_PREFIX}:99"


@pytest.mark.unit
def test_excel_enable_rejected_for_all_modes_decision_section_9() -> None:
    """§9: Excel apply gate always False (supersedes 1.8 paid-only excel enable)."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.scheduling import (
        can_apply_card_ab_hold_mode_via_excel,
    )

    assert (
        can_apply_card_ab_hold_mode_via_excel(
            bot_active=False, requested_mode="active"
        )
        is False
    )
    assert (
        can_apply_card_ab_hold_mode_via_excel(
            bot_active=True, requested_mode="off"
        )
        is False
    )
