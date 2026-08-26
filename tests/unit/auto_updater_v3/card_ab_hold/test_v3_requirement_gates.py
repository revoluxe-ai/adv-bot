"""Gate-тесты A/B Hold V3-only + взаимоисключение с V2 (spec ``card-ab-hold-mode``, decision §12).

Проверяют:
- enable A/B Hold только при ``automatic_version == 3`` (иначе OFF + причина);
- запрет downgrade на V2, пока mode PENDING_SETUP / ACTIVE (сначала EXIT → OFF);
- ``change_adv_strategy`` остаётся V2-scope: A/B Hold НЕ добавляет freeze-гард на этот путь
  (полная развязка ``strategy_mode`` ← ``AdvSetting.strategy`` — отдельная задача вне change).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.scheduling import (
    is_switch_to_version_blocked_by_ab_hold,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.ui_access import (
    can_enable_card_ab_hold_on_version,
    card_ab_hold_requires_v3_message,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    "automatic_version, expected",
    [(3, True), (2, False), (1, False), (None, False)],
)
def test_enable_version_gate_allows_only_v3(
    automatic_version: int | None, expected: bool
) -> None:
    """14.1/14.3: enable A/B Hold разрешён только для V3 auto-updater."""
    adv = SimpleNamespace(automatic_version=automatic_version)
    assert can_enable_card_ab_hold_on_version(adv) is expected


@pytest.mark.unit
def test_enable_version_gate_message_mentions_v3() -> None:
    """14.3: причина блокировки называет V3 (пользователь видит, что делать)."""
    assert "V3" in card_ab_hold_requires_v3_message()


@pytest.mark.unit
@pytest.mark.parametrize(
    "mode",
    [CardAbHoldMode.PENDING_SETUP, CardAbHoldMode.ACTIVE, "pending_setup", "active"],
)
def test_downgrade_to_v2_blocked_during_ab_hold(
    mode: CardAbHoldMode | str,
) -> None:
    """14.2/14.4: пока A/B Hold PENDING/ACTIVE — переключение на V2 запрещено."""
    assert (
        is_switch_to_version_blocked_by_ab_hold(new_version=2, mode=mode) is True
    )


@pytest.mark.unit
@pytest.mark.parametrize("mode", [CardAbHoldMode.OFF, "off", None])
def test_downgrade_to_v2_allowed_when_off(mode: CardAbHoldMode | str | None) -> None:
    """14.2 paired positive: при OFF downgrade на V2 разрешён."""
    assert (
        is_switch_to_version_blocked_by_ab_hold(new_version=2, mode=mode) is False
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "mode",
    [CardAbHoldMode.OFF, CardAbHoldMode.PENDING_SETUP, CardAbHoldMode.ACTIVE],
)
def test_switch_to_v3_never_blocked(mode: CardAbHoldMode) -> None:
    """14.2: переход на V3 всегда разрешён (взаимоисключение только про V2)."""
    assert (
        is_switch_to_version_blocked_by_ab_hold(new_version=3, mode=mode) is False
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enable_handler_runs_v3_gate_before_pending_and_enter_write() -> None:
    """14.1/14.3: non-V3 Enable → mode OFF, start_epoch/set_signal не вызываются."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
        handlers,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.callbacks import (
        CardAbHoldEnable,
    )

    adv = SimpleNamespace(
        id=7,
        adv_id=77,
        bot_active=True,
        automatic_version=2,
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
async def test_version_toggle_blocks_v2_downgrade_before_automatic_version_write() -> None:
    """14.2/14.4: ACTIVE Hold + toggle V2 → session.execute(update) не вызывается."""
    from app.modules.shop_runner.service_manager.auto_updater_version_toggle.telegram import (
        handlers as version_handlers,
    )
    from app.modules.shop_runner.service_manager.auto_updater_version_toggle.telegram.callbacks import (
        AutoUpdaterVersionToggle,
    )

    adv = SimpleNamespace(
        id=11,
        automatic_version=3,
        card_ab_hold_mode=CardAbHoldMode.ACTIVE.value,
    )
    session = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=adv)
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    bot = MagicMock()
    bot.send_message = AsyncMock()
    query = MagicMock()
    query.message = MagicMock()
    query.message.chat = SimpleNamespace(id=100)
    query.from_user = SimpleNamespace(id=1)
    state = MagicMock()
    state.get_data = AsyncMock(return_value={})

    with patch.object(version_handlers, "sm", return_value=session_cm):
        await version_handlers.toggle_auto_updater_version(
            query,
            AutoUpdaterVersionToggle(adv_setting_original_id=11, new_version=2),
            bot,
            state,
        )

    # Only the SELECT for adv_before — no UPDATE of automatic_version.
    assert session.execute.await_count == 1
    session.commit.assert_not_awaited()
    bot.send_message.assert_awaited()
    assert "A/B Hold" in bot.send_message.await_args.args[1]


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
