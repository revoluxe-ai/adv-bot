"""§11: Telegram Enable idempotent while PENDING_SETUP / ACTIVE (decision §10).

Blocked: ACTIVE/PENDING Enable не demote и не пишет Redis ENTER.
Allowed: OFF Enable → путь ENTER (wiring: predicate false + handler order).

На d999e49 shop-allowlist bug прошёл suite: success-fixture сажал ``shop_id``
прямо на AdvSetting-stub (фантом), а feature_flag тестировал allowlist
изолированно с уже переданным ``shop_id`` — wiring Enable→cabinet не проверялся.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import inspect as sa_inspect

from app.modules.common_slaves.wildberries.models.models import AdvSetting
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
def test_advsetting_orm_has_no_shop_id_column() -> None:
    """Reality gate: ``shop_id`` живёт на WBCabinet, не на AdvSetting."""
    assert "shop_id" not in sa_inspect(AdvSetting).columns


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
    msg = MagicMock()
    msg.answer = AsyncMock()
    query.message = msg
    query.bot = MagicMock()
    query.bot.send_message = AsyncMock()
    query.from_user = SimpleNamespace(id=1)
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
    query.answer.assert_not_awaited()
    assert "включён" in query.message.answer.await_args.args[0]


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
    msg = MagicMock()
    msg.answer = AsyncMock()
    query.message = msg
    query.bot = MagicMock()
    query.bot.send_message = AsyncMock()
    query.from_user = SimpleNamespace(id=1)
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
    query.answer.assert_not_awaited()
    assert "подготовка" in query.message.answer.await_args.args[0].lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enable_success_calls_start_epoch_on_enable_not_manual_phase() -> None:
    """ENTER после gates вызывает ``start_epoch_on_enable``; phase не setattr в handler."""
    adv = SimpleNamespace(
        id=9,
        adv_id=99,
        wb_cabinet=SimpleNamespace(shop_id="1"),
        bot_active=True,
        max_price_for_order=100.0,
        card_ab_hold_mode=CardAbHoldMode.OFF.value,
        card_ab_hold_degraded=False,
    )
    session = MagicMock()
    session.scalar = AsyncMock(return_value=adv)
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)

    refreshed = SimpleNamespace(
        id=9,
        adv_id=99,
        bot_active=True,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
        card_ab_hold_degraded=False,
    )
    refresh_session = MagicMock()
    refresh_session.scalar = AsyncMock(return_value=refreshed)
    refresh_cm = MagicMock()
    refresh_cm.__aenter__ = AsyncMock(return_value=refresh_session)
    refresh_cm.__aexit__ = AsyncMock(return_value=None)

    query = MagicMock()
    query.answer = AsyncMock()
    msg = MagicMock()
    msg.answer = AsyncMock()
    query.message = msg
    callback = CardAbHoldEnable(adv_setting_original_id=9)

    start_epoch = AsyncMock(return_value=True)
    set_signal = AsyncMock()

    with (
        patch.object(handlers, "sm", side_effect=[session_cm, refresh_cm]),
        patch.object(handlers, "start_epoch_on_enable", start_epoch),
        patch.object(
            handlers,
            "evaluate_ab_hold_enable_stats",
            new_callable=AsyncMock,
            return_value=(True, None),
        ),
        patch.object(
            handlers,
            "evaluate_ab_hold_launch_view_volume",
            new_callable=AsyncMock,
        ) as eval_volume,
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
        patch.object(handlers, "_edit_screen", new_callable=AsyncMock),
    ):
        eval_volume.return_value.is_unavailable = False
        eval_volume.return_value.is_sufficient = True
        await handlers.enable_card_ab_hold(query, callback)

    start_epoch.assert_awaited_once_with(9, adv_id=99, shop_id=1)
    set_signal.assert_awaited_once()
    assert start_epoch.await_args.kwargs["adv_id"] == 99


def _off_adv_for_enable(
    *,
    adv_setting_id: int = 10,
    adv_id: int = 100,
    wb_cabinet: object | None = None,
) -> SimpleNamespace:
    """AdvSetting-like stub без ``shop_id`` — только ORM path ``wb_cabinet.shop_id``."""
    return SimpleNamespace(
        id=adv_setting_id,
        adv_id=adv_id,
        wb_cabinet=wb_cabinet,
        bot_active=True,
        max_price_for_order=100.0,
        card_ab_hold_mode=CardAbHoldMode.OFF.value,
        card_ab_hold_degraded=False,
    )


async def _run_enable_success_path(
    adv: SimpleNamespace,
    *,
    start_epoch: AsyncMock,
) -> None:
    """Прогнать Enable после успешных gates; вернуть control через patched start_epoch."""
    session = MagicMock()
    session.scalar = AsyncMock(return_value=adv)
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)

    refreshed = SimpleNamespace(
        id=adv.id,
        adv_id=adv.adv_id,
        bot_active=True,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
        card_ab_hold_degraded=False,
    )
    refresh_session = MagicMock()
    refresh_session.scalar = AsyncMock(return_value=refreshed)
    refresh_cm = MagicMock()
    refresh_cm.__aenter__ = AsyncMock(return_value=refresh_session)
    refresh_cm.__aexit__ = AsyncMock(return_value=None)

    query = MagicMock()
    query.answer = AsyncMock()
    query.message = MagicMock(answer=AsyncMock())
    callback = CardAbHoldEnable(adv_setting_original_id=int(adv.id))

    with (
        patch.object(handlers, "sm", side_effect=[session_cm, refresh_cm]),
        patch.object(handlers, "start_epoch_on_enable", start_epoch),
        patch.object(
            handlers,
            "evaluate_ab_hold_enable_stats",
            new_callable=AsyncMock,
            return_value=(True, None),
        ),
        patch.object(
            handlers,
            "evaluate_ab_hold_launch_view_volume",
            new_callable=AsyncMock,
        ) as eval_volume,
        patch.object(
            handlers,
            "CardAbHoldSignalRedisCache",
            return_value=MagicMock(set_signal=AsyncMock()),
        ),
        patch.object(
            handlers,
            "CardAbHoldLastAbortRedisCache",
            return_value=MagicMock(get_abort=AsyncMock(return_value=None)),
        ),
        patch.object(handlers, "_edit_screen", new_callable=AsyncMock),
    ):
        eval_volume.return_value.is_unavailable = False
        eval_volume.return_value.is_sufficient = True
        await handlers.enable_card_ab_hold(query, callback)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enable_passes_wb_cabinet_shop_id_to_start_epoch() -> None:
    """Regression ROOT-001: shop allowlist wiring через ``wb_cabinet.shop_id``, не ``adv.shop_id``."""
    adv = _off_adv_for_enable(wb_cabinet=SimpleNamespace(shop_id="7"))
    assert not hasattr(adv, "shop_id")
    start_epoch = AsyncMock(return_value=True)

    await _run_enable_success_path(adv, start_epoch=start_epoch)

    start_epoch.assert_awaited_once_with(10, adv_id=100, shop_id=7)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enable_non_numeric_wb_cabinet_shop_id_passes_none() -> None:
    """Non-numeric cabinet.shop_id → shop_id=None (fail-closed shop allowlist, no crash)."""
    adv = _off_adv_for_enable(wb_cabinet=SimpleNamespace(shop_id="not-a-number"))
    start_epoch = AsyncMock(return_value=True)

    await _run_enable_success_path(adv, start_epoch=start_epoch)

    start_epoch.assert_awaited_once_with(10, adv_id=100, shop_id=None)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enable_missing_wb_cabinet_passes_shop_id_none() -> None:
    """Нет joined cabinet → shop_id=None; epoch только через adv_id/OD-05."""
    adv = _off_adv_for_enable(wb_cabinet=None)
    start_epoch = AsyncMock(return_value=True)

    await _run_enable_success_path(adv, start_epoch=start_epoch)

    start_epoch.assert_awaited_once_with(10, adv_id=100, shop_id=None)
