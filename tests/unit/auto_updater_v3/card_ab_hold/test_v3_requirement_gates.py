"""Gate-тесты A/B Hold V3-only + взаимоисключение с V2 (spec ``card-ab-hold-mode``, decision §12).

Проверяют:
- enable A/B Hold только при ``automatic_version == 3`` (иначе OFF + причина);
- запрет downgrade на V2, пока mode PENDING_SETUP / ACTIVE (сначала EXIT → OFF);
- ``change_adv_strategy`` остаётся V2-scope: A/B Hold НЕ добавляет freeze-гард на этот путь
  (полная развязка ``strategy_mode`` ← ``AdvSetting.strategy`` — отдельная задача вне change).
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace

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
def test_enable_handler_runs_v3_gate_before_pending_and_enter_write() -> None:
    """14.1/14.3 wiring: V3-gate стоит до записи PENDING_SETUP и Redis ENTER.

    Гарантирует «на не-V3 mode остаётся OFF, ENTER не пишется»: ранний return
    gate'а расположен строго раньше PG-write и `set_signal(ENTER)`.
    """
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
        handlers,
    )

    src = inspect.getsource(handlers.enable_card_ab_hold)
    gate_at = src.find("can_enable_card_ab_hold_on_version")
    pending_write_at = src.find("PENDING_SETUP.value")
    enter_write_at = src.find("set_signal")
    assert gate_at != -1
    assert pending_write_at != -1 and gate_at < pending_write_at
    assert enter_write_at != -1 and gate_at < enter_write_at


@pytest.mark.unit
def test_version_toggle_runs_downgrade_block_before_automatic_version_write() -> None:
    """14.2/14.4 wiring: downgrade-block стоит до PG-write `automatic_version`.

    Гарантирует «downgrade на V2 при активном A/B Hold не меняет automatic_version»:
    ранний return блока расположен строго раньше `update(...).values` записи.
    """
    from app.modules.shop_runner.service_manager.auto_updater_version_toggle.telegram import (
        handlers,
    )

    src = inspect.getsource(handlers.toggle_auto_updater_version)
    block_at = src.find("is_switch_to_version_blocked_by_ab_hold")
    write_at = src.find('"automatic_version": new_version')
    assert block_at != -1
    assert write_at != -1 and block_at < write_at


@pytest.mark.unit
def test_change_adv_strategy_stays_v2_scope_no_ab_hold_freeze_gate() -> None:
    """14.5 regression: change_adv_strategy — V2-scope, A/B Hold НЕ добавляет freeze-гард.

    Осознанно противоположно 6 structural ACT-корутинам: strategy (MIN_CPO/MAX_CONV)
    вынесен из scope freeze A/B Hold (spec «A/B Hold requires V3…» + decision §12).
    Полная гарантия «strategy не влияет на V3 held-профиль» зависит от отдельной
    развязки V3 keyword ``strategy_mode`` ← ``AdvSetting.strategy`` (вне этого change).
    """
    from app.modules.shop_runner.service_manager.manager import CoroutinesManager

    src = inspect.getsource(CoroutinesManager.change_adv_strategy)
    assert "filter_structural_act_candidates" not in src
    assert "card_ab_hold_mode" not in src
