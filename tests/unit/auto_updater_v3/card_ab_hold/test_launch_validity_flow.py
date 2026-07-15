"""Enable-поток soft-gate низкого объёма показов (spec §2c / decision §2c).

Класс: unit. Handler-поведение с замоканными session/Redis/CH:
- 13.2: low views → mode остаётся OFF, ENTER не пишется, warning+choice; paired
  sufficient → PENDING_SETUP + ENTER;
- 13.3: «Всё равно запустить» → PENDING_SETUP + ENTER (объёмный gate пропущен);
  «Отмена» → остаётся OFF, ENTER не пишется;
- 13.5 wiring: объёмный gate — после freshness, до записи PENDING; launch-anyway
  пропускает объёмный gate.
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
    CardAbHoldCancel,
    CardAbHoldEnable,
    CardAbHoldLaunchAnyway,
)


def _make_off_adv() -> SimpleNamespace:
    """OFF V3 paid кампания, проходящая bot_active/no-op/V3 gates."""
    return SimpleNamespace(
        id=42,
        adv_id=4242,
        bot_active=True,
        automatic_version=3,
        card_ab_hold_mode=CardAbHoldMode.OFF.value,
        card_ab_hold_degraded=False,
        search_adv_id=None,
    )


def _make_session(adv: SimpleNamespace) -> tuple[MagicMock, MagicMock]:
    """(session, session_cm) с async scalar/commit/refresh."""
    session = MagicMock()
    session.scalar = AsyncMock(return_value=adv)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    return session, session_cm


def _make_query() -> MagicMock:
    query = MagicMock()
    query.answer = AsyncMock()
    query.message = None
    return query


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enable_low_views_warns_and_stays_off() -> None:
    """13.2: Σ 24h views < порога → mode OFF, ENTER не пишется, warning показан."""
    adv = _make_off_adv()
    session, session_cm = _make_session(adv)
    query = _make_query()
    set_signal = AsyncMock()

    with (
        patch.object(handlers, "sm", return_value=session_cm),
        patch.object(
            handlers,
            "evaluate_ab_hold_enable_stats",
            new=AsyncMock(return_value=(True, None)),
        ),
        patch.object(
            handlers,
            "evaluate_ab_hold_launch_view_volume",
            new=AsyncMock(return_value=(False, 300)),
        ),
        patch.object(
            handlers,
            "CardAbHoldSignalRedisCache",
            return_value=MagicMock(set_signal=set_signal),
        ),
    ):
        await handlers.enable_card_ab_hold(
            query, CardAbHoldEnable(adv_setting_original_id=42)
        )

    assert adv.card_ab_hold_mode == CardAbHoldMode.OFF.value
    session.commit.assert_not_awaited()
    set_signal.assert_not_awaited()
    query.answer.assert_awaited()
    assert "Мало показов" in query.answer.await_args.args[0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enable_sufficient_views_proceeds_to_pending() -> None:
    """13.2 paired: Σ >= порога → PENDING_SETUP + Redis ENTER (без warning)."""
    adv = _make_off_adv()
    session, session_cm = _make_session(adv)
    query = _make_query()
    set_signal = AsyncMock()
    view_eval = AsyncMock(return_value=(True, 5000))

    with (
        patch.object(handlers, "sm", return_value=session_cm),
        patch.object(
            handlers,
            "evaluate_ab_hold_enable_stats",
            new=AsyncMock(return_value=(True, None)),
        ),
        patch.object(handlers, "evaluate_ab_hold_launch_view_volume", new=view_eval),
        patch.object(
            handlers,
            "CardAbHoldSignalRedisCache",
            return_value=MagicMock(set_signal=set_signal),
        ),
        patch.object(
            handlers,
            "CardAbHoldLastAbortRedisCache",
            return_value=MagicMock(get_abort=AsyncMock(return_value=None)),
        ),
    ):
        await handlers.enable_card_ab_hold(
            query, CardAbHoldEnable(adv_setting_original_id=42)
        )

    view_eval.assert_awaited_once()
    assert adv.card_ab_hold_mode == CardAbHoldMode.PENDING_SETUP.value
    session.commit.assert_awaited()
    set_signal.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_launch_anyway_proceeds_without_volume_check() -> None:
    """13.3: «Всё равно запустить» → PENDING_SETUP + ENTER; объём НЕ проверяется."""
    adv = _make_off_adv()
    session, session_cm = _make_session(adv)
    query = _make_query()
    set_signal = AsyncMock()
    view_eval = AsyncMock(return_value=(False, 10))

    with (
        patch.object(handlers, "sm", return_value=session_cm),
        patch.object(
            handlers,
            "evaluate_ab_hold_enable_stats",
            new=AsyncMock(return_value=(True, None)),
        ),
        patch.object(handlers, "evaluate_ab_hold_launch_view_volume", new=view_eval),
        patch.object(
            handlers,
            "CardAbHoldSignalRedisCache",
            return_value=MagicMock(set_signal=set_signal),
        ),
        patch.object(
            handlers,
            "CardAbHoldLastAbortRedisCache",
            return_value=MagicMock(get_abort=AsyncMock(return_value=None)),
        ),
    ):
        await handlers.launch_card_ab_hold_anyway(
            query, CardAbHoldLaunchAnyway(adv_setting_original_id=42)
        )

    view_eval.assert_not_awaited()
    assert adv.card_ab_hold_mode == CardAbHoldMode.PENDING_SETUP.value
    session.commit.assert_awaited()
    set_signal.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cancel_keeps_off_and_no_enter() -> None:
    """13.3: «Отмена» → mode остаётся OFF, ENTER не пишется."""
    adv = _make_off_adv()
    session, session_cm = _make_session(adv)
    query = _make_query()
    set_signal = AsyncMock()

    with (
        patch.object(handlers, "sm", return_value=session_cm),
        patch.object(
            handlers,
            "CardAbHoldSignalRedisCache",
            return_value=MagicMock(set_signal=set_signal),
        ),
    ):
        await handlers.cancel_card_ab_hold_enable(
            query, CardAbHoldCancel(adv_setting_original_id=42)
        )

    assert adv.card_ab_hold_mode == CardAbHoldMode.OFF.value
    session.commit.assert_not_awaited()
    set_signal.assert_not_awaited()
    query.answer.assert_awaited()
    assert "отмен" in query.answer.await_args.args[0].lower()


@pytest.mark.unit
def test_view_volume_gate_runs_after_freshness_before_pending_write() -> None:
    """13.5 wiring: объёмный gate — после freshness и до записи PENDING_SETUP."""
    src = inspect.getsource(handlers._handle_ab_hold_enable)
    freshness_at = src.find("evaluate_ab_hold_enable_stats")
    volume_at = src.find("evaluate_ab_hold_launch_view_volume")
    pending_at = src.find("PENDING_SETUP.value")
    assert -1 < freshness_at < volume_at < pending_at
    assert "skip_view_volume_gate" in src


@pytest.mark.unit
def test_enable_uses_volume_gate_and_launch_anyway_skips_it() -> None:
    """13.5 wiring: enable проверяет объём; launch-anyway его пропускает."""
    enable_src = inspect.getsource(handlers.enable_card_ab_hold)
    launch_src = inspect.getsource(handlers.launch_card_ab_hold_anyway)
    assert "skip_view_volume_gate=False" in enable_src
    assert "skip_view_volume_gate=True" in launch_src
