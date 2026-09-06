"""Gate-тесты A/B Hold: enable только при ``bot_active`` (spec drift §12 → bot_active SoT).

Проверяют:
- enable A/B Hold только при включённом боте (иначе OFF + причина);
- ``change_adv_strategy`` остаётся V2-scope: A/B Hold НЕ добавляет freeze-гард на этот путь.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.ui_access import (
    can_enable_card_ab_hold_on_version,
    card_ab_hold_requires_v3_message,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    "bot_active, expected",
    [(True, True), (False, False)],
)
def test_enable_version_gate_allows_only_when_bot_active(
    bot_active: bool, expected: bool
) -> None:
    """14.1/14.3: enable A/B Hold разрешён только при bot_active=True (V3 runtime)."""
    adv = SimpleNamespace(bot_active=bot_active)
    assert can_enable_card_ab_hold_on_version(adv) is expected


@pytest.mark.unit
def test_enable_version_gate_message_mentions_bot_active() -> None:
    """14.3: причина блокировки называет включение бота."""
    assert "бот" in card_ab_hold_requires_v3_message().lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enable_handler_runs_v3_gate_before_pending_and_enter_write() -> None:
    """14.1/14.3: bot inactive Enable → mode OFF, start_epoch/set_signal не вызываются."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
        handlers,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.callbacks import (
        CardAbHoldEnable,
    )

    adv = SimpleNamespace(
        id=7,
        adv_id=77,
        bot_active=False,
        max_price_for_order=100.0,
        card_ab_hold_mode=CardAbHoldMode.OFF.value,
        card_ab_hold_degraded=False,
    )
    session = MagicMock()
    session.scalar = AsyncMock(return_value=adv)
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    query = MagicMock()
    query.answer = AsyncMock()
    query.message = MagicMock(answer=AsyncMock())
    query.bot = MagicMock(send_message=AsyncMock())
    query.from_user = SimpleNamespace(id=1)
    start_epoch = AsyncMock()
    set_signal = AsyncMock()
    eval_stats = AsyncMock()

    with (
        patch.object(handlers, "sm", return_value=session_cm),
        patch.object(handlers, "start_epoch_on_enable", start_epoch),
        patch.object(
            handlers,
            "CardAbHoldSignalRedisCache",
            return_value=MagicMock(set_signal=set_signal),
        ),
        patch.object(handlers, "evaluate_ab_hold_enable_stats", eval_stats),
        patch.object(handlers, "_edit_screen", new_callable=AsyncMock),
    ):
        await handlers.enable_card_ab_hold(
            query, CardAbHoldEnable(adv_setting_original_id=7)
        )

    assert adv.card_ab_hold_mode == CardAbHoldMode.OFF.value
    start_epoch.assert_not_awaited()
    set_signal.assert_not_awaited()
    eval_stats.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_change_adv_strategy_keeps_active_hold_campaigns() -> None:
    """14.5: change_adv_strategy не фильтрует structural freeze — ACTIVE остаётся в pool."""
    from app.modules.shop_runner.service_manager.manager import CoroutinesManager

    active = SimpleNamespace(
        adv_id=1,
        bot_active=True,
        is_part_auto_setting_active=True,
        auto_update_strategy=True,
        card_ab_hold_mode=CardAbHoldMode.ACTIVE.value,
    )
    off = SimpleNamespace(
        adv_id=2,
        bot_active=True,
        is_part_auto_setting_active=True,
        auto_update_strategy=True,
        card_ab_hold_mode=CardAbHoldMode.OFF.value,
    )
    mgr = object.__new__(CoroutinesManager)
    mgr._wb_shop_data_manager = MagicMock()
    mgr._wb_shop_data_manager.get_complex_advs = AsyncMock(return_value=[active, off])
    mgr._max_workers_for = MagicMock(return_value=1)
    mgr._tasks_manager = MagicMock()
    mgr.shop_id = "shop"
    resolved: list[int] = []

    async def _resolve(complex_adv: SimpleNamespace):
        resolved.append(int(complex_adv.adv_id))
        return complex_adv, None

    mgr._resolve_strategy_selection = _resolve  # type: ignore[method-assign]

    async def _run_tasks(handlers, max_workers=None, tasks_manager=None):
        _ = max_workers, tasks_manager
        out = []
        for h in handlers:
            out.append(await h())
        return out

    with patch(
        "app.modules.shop_runner.service_manager.manager.run_tasks",
        new=_run_tasks,
    ):
        raw = CoroutinesManager.change_adv_strategy
        fn = getattr(raw, "__wrapped__", None)
        assert fn is not None
        await fn(mgr, only_bot_active=True)

    assert resolved == [1, 2]
