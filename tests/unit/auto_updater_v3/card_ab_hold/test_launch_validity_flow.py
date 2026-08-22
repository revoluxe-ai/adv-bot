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

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
    handlers,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.launch_validity_gate import (
    LaunchViewVolumeEvaluation,
    LaunchViewVolumeOutcome,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.callbacks import (
    CardAbHoldCancel,
    CardAbHoldEnable,
    CardAbHoldLaunchAnyway,
)


def _make_off_adv() -> SimpleNamespace:
    """OFF V3 paid кампания, проходящая bot_active/no-op/V3/max-CPO gates.

    ``max_price_for_order`` > 0 обязателен: с §16 (decision §14a) enable hard-gate’ит
    отсутствующий/непозитивный план max CPO раньше объёмного soft-gate.
    """
    return SimpleNamespace(
        id=42,
        adv_id=4242,
        bot_active=True,
        max_price_for_order=100,
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
    msg = MagicMock()
    msg.answer = AsyncMock()
    query.message = msg
    query.bot = MagicMock()
    query.bot.send_message = AsyncMock()
    query.from_user = SimpleNamespace(id=1)
    return query


def _user_notice_text(query: MagicMock) -> str:
    """Текст user-visible notice (message.answer / bot.send_message)."""
    if query.message is not None and getattr(query.message, "answer", None):
        if query.message.answer.await_count > 0:
            args = query.message.answer.await_args.args
            if args:
                return str(args[0])
    send = getattr(getattr(query, "bot", None), "send_message", None)
    if send is not None and send.await_count > 0:
        args = send.await_args.args
        if len(args) >= 2:
            return str(args[1])
        if "text" in send.await_args.kwargs:
            return str(send.await_args.kwargs["text"])
    return ""


def _make_enable_success_mocks(
    adv: SimpleNamespace,
    session_cm: MagicMock,
) -> tuple[AsyncMock, MagicMock, SimpleNamespace]:
    """Mocks для успешного ENTER: start_epoch_on_enable + refresh session."""
    refreshed = SimpleNamespace(
        **{
            **adv.__dict__,
            "card_ab_hold_mode": CardAbHoldMode.PENDING_SETUP.value,
        }
    )
    refresh_session = MagicMock()
    refresh_session.scalar = AsyncMock(return_value=refreshed)
    refresh_cm = MagicMock()
    refresh_cm.__aenter__ = AsyncMock(return_value=refresh_session)
    refresh_cm.__aexit__ = AsyncMock(return_value=None)
    start_epoch = AsyncMock(return_value=True)
    sm_side_effect = MagicMock(side_effect=[session_cm, refresh_cm])
    return start_epoch, sm_side_effect, refreshed


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
            new=AsyncMock(
                return_value=LaunchViewVolumeEvaluation(
                    outcome=LaunchViewVolumeOutcome.LOW,
                    total_views=300,
                )
            ),
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
    query.answer.assert_not_awaited()
    assert "Мало показов" in _user_notice_text(query)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enable_sufficient_views_proceeds_to_pending() -> None:
    """13.2 paired: Σ >= порога → PENDING_SETUP + Redis ENTER (без warning)."""
    adv = _make_off_adv()
    session, session_cm = _make_session(adv)
    query = _make_query()
    set_signal = AsyncMock()
    view_eval = AsyncMock(
        return_value=LaunchViewVolumeEvaluation(
            outcome=LaunchViewVolumeOutcome.SUFFICIENT,
            total_views=5000,
        )
    )
    start_epoch, sm_side_effect, refreshed = _make_enable_success_mocks(
        adv, session_cm
    )

    with (
        patch.object(handlers, "sm", sm_side_effect),
        patch.object(handlers, "start_epoch_on_enable", start_epoch),
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
    start_epoch.assert_awaited_once()
    assert refreshed.card_ab_hold_mode == CardAbHoldMode.PENDING_SETUP.value
    set_signal.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_launch_anyway_proceeds_without_volume_check() -> None:
    """13.3: «Всё равно запустить» → PENDING_SETUP + ENTER; объём НЕ проверяется."""
    adv = _make_off_adv()
    session, session_cm = _make_session(adv)
    query = _make_query()
    set_signal = AsyncMock()
    view_eval = AsyncMock(
        return_value=LaunchViewVolumeEvaluation(
            outcome=LaunchViewVolumeOutcome.LOW,
            total_views=10,
        )
    )

    start_epoch, sm_side_effect, refreshed = _make_enable_success_mocks(
        adv, session_cm
    )

    with (
        patch.object(handlers, "sm", sm_side_effect),
        patch.object(handlers, "start_epoch_on_enable", start_epoch),
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
    start_epoch.assert_awaited_once()
    assert refreshed.card_ab_hold_mode == CardAbHoldMode.PENDING_SETUP.value
    set_signal.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enable_ch_error_shows_distinct_reason_and_stays_off() -> None:
    """17.1: CH unavailable → mode OFF, ENTER не пишется, distinct reason (не low warn)."""
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
            new=AsyncMock(
                return_value=LaunchViewVolumeEvaluation(
                    outcome=LaunchViewVolumeOutcome.UNAVAILABLE,
                    total_views=0,
                )
            ),
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
    query.answer.assert_not_awaited()
    alert = _user_notice_text(query)
    assert "недоступна" in alert
    assert "Мало показов" not in alert


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
    query.answer.assert_not_awaited()
    assert "отмен" in _user_notice_text(query).lower()
