"""Гейт свежести на enable и post-enter schedule (spec card-ab-hold-mode § freshness)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.client_bot import const
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.scheduling import (
    can_apply_card_ab_hold_mode_via_excel,
    filter_ab_hold_pipeline_candidates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.stats_enable_gate import (
    allows_ab_hold_enable_for_stats_state,
    build_ab_hold_enable_blocked_alert,
    build_ab_hold_enable_blocked_by_stats_message,
    user_facing_stats_block_reason,
)
from app.modules.shop_runner.service_manager.services.stats_freshness_guard import (
    StatsFreshnessState,
)


@pytest.mark.unit
def test_enable_allowed_when_stats_fresh() -> None:
    """7.1: fresh state → enable ok."""
    state = StatsFreshnessState(is_fresh=True, is_stale_over_6h=False)
    assert allows_ab_hold_enable_for_stats_state(state, guard_enabled=True) is True


@pytest.mark.unit
def test_enable_blocked_when_stats_stale() -> None:
    """7.1: not fresh → enable blocked."""
    state = StatsFreshnessState(
        is_fresh=False,
        is_stale_over_6h=False,
        reason="full_adv_stat_update stale for adv_id=1",
    )
    assert allows_ab_hold_enable_for_stats_state(state, guard_enabled=True) is False


@pytest.mark.unit
def test_enable_allowed_when_guard_disabled() -> None:
    """При выключенном STATS_FRESHNESS_GUARD enable не режется."""
    state = StatsFreshnessState(is_fresh=False, is_stale_over_6h=True, reason="x")
    assert allows_ab_hold_enable_for_stats_state(state, guard_enabled=False) is True


@pytest.mark.unit
def test_enable_blocked_when_state_missing_fail_closed() -> None:
    """Без state при активном guard — fail-closed (не стартуем тест вслепую)."""
    assert allows_ab_hold_enable_for_stats_state(None, guard_enabled=True) is False


@pytest.mark.unit
def test_blocked_message_has_reason_restriction_and_support_link() -> None:
    """7.2: сообщение содержит причину, ограничение и SUPPORT_LINK."""
    raw = "cluster_stat_update not yet collected for adv_id=9"
    text = build_ab_hold_enable_blocked_by_stats_message(raw)
    assert "ограничен" in text.lower()
    assert "Включение режима A/B" in text
    assert user_facing_stats_block_reason(raw) in text
    assert const.SUPPORT_LINK in text
    assert "{" not in text and "}" not in text
    assert len(text) <= 4096
    alert = build_ab_hold_enable_blocked_alert(raw)
    assert len(alert) <= 200
    assert const.SUPPORT_LINK in alert or "статой" in alert.lower()


@pytest.mark.unit
def test_excel_enable_rejects_stale_stats() -> None:
    """7.1 Excel: non-OFF при stale → False; OFF ok; bot_active False → False."""
    assert (
        can_apply_card_ab_hold_mode_via_excel(
            bot_active=True,
            requested_mode=CardAbHoldMode.PENDING_SETUP,
            stats_fresh_enough=False,
        )
        is False
    )
    assert (
        can_apply_card_ab_hold_mode_via_excel(
            bot_active=True,
            requested_mode=CardAbHoldMode.PENDING_SETUP,
            stats_fresh_enough=True,
        )
        is True
    )
    assert (
        can_apply_card_ab_hold_mode_via_excel(
            bot_active=False,
            requested_mode=CardAbHoldMode.ACTIVE,
            stats_fresh_enough=True,
        )
        is False
    )
    assert (
        can_apply_card_ab_hold_mode_via_excel(
            bot_active=False,
            requested_mode=CardAbHoldMode.OFF,
            stats_fresh_enough=False,
        )
        is True
    )


@pytest.mark.unit
def test_ab_hold_pipeline_candidates_from_full_list_not_only_fresh() -> None:
    """7.3/7.4: PENDING/ACTIVE из полного списка; OFF не попадает в pipeline."""
    pending = SimpleNamespace(card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value)
    active = SimpleNamespace(card_ab_hold_mode=CardAbHoldMode.ACTIVE.value)
    off = SimpleNamespace(card_ab_hold_mode=CardAbHoldMode.OFF.value)
    # "полный" список включает stale-кампании (мы не фильтруем здесь)
    full = [pending, off, active]
    pairs = filter_ab_hold_pipeline_candidates(full)  # type: ignore[arg-type]
    modes = [m for _, m in pairs]
    assert CardAbHoldMode.PENDING_SETUP in modes
    assert CardAbHoldMode.ACTIVE in modes
    assert CardAbHoldMode.OFF not in modes
    assert len(pairs) == 2
