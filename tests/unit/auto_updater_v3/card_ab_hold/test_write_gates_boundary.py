"""Write-gate тесты A/B Hold: filter до candidate/handler/write boundary.

Spec ``card-ab-hold-mode`` / VERIFY_POLICY: regression MUST fail if
``filter_structural_act_candidates`` убрать из manager path (те же функции).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.scheduling import (
    can_apply_card_ab_hold_mode_via_excel,
    filter_bidder_eligible_by_ab_hold,
    filter_structural_act_candidates,
    should_allow_bidder_on_ab_hold,
    should_schedule_ordinary_updater,
)


def _adv(
    adv_id: int,
    *,
    mode: str,
    auto_update_white_list: bool = True,
    individual_tp: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        adv_id=adv_id,
        card_ab_hold_mode=mode,
        auto_update_white_list=auto_update_white_list,
        individual_keywords_target_place_mode=individual_tp,
        bot_active=True,
    )


@pytest.mark.unit
def test_structural_act_filter_drops_freeze_modes_keeps_off() -> None:
    """1.4 write-gate: до FirstKey/trim/TP handler boundary только OFF остаётся.

    Имитирует candidate list manager: после filter_structural_act_candidates
    ADV/ PENDING не попадают в handlers (ids доказывают фильтрацию, не mock calls).
    """
    candidates = [
        _adv(1, mode=CardAbHoldMode.OFF.value),
        _adv(2, mode=CardAbHoldMode.PENDING_SETUP.value),
        _adv(3, mode=CardAbHoldMode.ACTIVE.value),
        _adv(4, mode=CardAbHoldMode.OFF.value, auto_update_white_list=False),
    ]
    # top-key / trim-like prefilter: whitelist flag (как в manager до freeze filter)
    wl_pool = [a for a in candidates if a.auto_update_white_list]
    before_write = filter_structural_act_candidates(wl_pool)
    assert [a.adv_id for a in before_write] == [1]
    assert all(
        should_schedule_ordinary_updater(a.card_ab_hold_mode) for a in before_write
    )


@pytest.mark.unit
def test_structural_act_filter_paired_positive_off_reaches_boundary() -> None:
    """1.4 paired positive: mode OFF проходит к write boundary."""
    off_only = [_adv(10, mode="off"), _adv(11, mode="off")]
    assert [a.adv_id for a in filter_structural_act_candidates(off_only)] == [10, 11]


@pytest.mark.unit
def test_individual_tp_and_emergency_use_same_structural_filter() -> None:
    """1.4: individual TP / emergency candidate pool — тот же filter до write."""
    pool = [
        _adv(1, mode="active", individual_tp=True),
        _adv(2, mode="off", individual_tp=True),
        _adv(3, mode="pending_setup", individual_tp=True),
    ]
    tp_pool = [a for a in pool if a.individual_keywords_target_place_mode]
    filtered = filter_structural_act_candidates(tp_pool)
    assert [a.adv_id for a in filtered] == [2]


@pytest.mark.unit
def test_bidder_eligible_keeps_active_hold_campaigns() -> None:
    """1.5: ACTIVE не исключается из bidder eligibility (freeze только structural)."""
    pool = [
        _adv(1, mode=CardAbHoldMode.ACTIVE.value),
        _adv(2, mode=CardAbHoldMode.PENDING_SETUP.value),
        _adv(3, mode=CardAbHoldMode.OFF.value),
    ]
    eligible = filter_bidder_eligible_by_ab_hold(pool)
    assert [a.adv_id for a in eligible] == [1, 2, 3]
    assert should_allow_bidder_on_ab_hold(CardAbHoldMode.ACTIVE) is True


@pytest.mark.unit
def test_excel_enable_rejected_when_bot_inactive_via_shared_gate() -> None:
    """1.8: тот же gate, что ``import_apply`` — enable при bot_active=False запрещён."""
    assert (
        can_apply_card_ab_hold_mode_via_excel(
            bot_active=False, requested_mode="active"
        )
        is False
    )
    assert (
        can_apply_card_ab_hold_mode_via_excel(
            bot_active=False, requested_mode="pending_setup"
        )
        is False
    )
    # paired: OFF всегда можно записать; enable при paid bot — ok
    assert (
        can_apply_card_ab_hold_mode_via_excel(bot_active=False, requested_mode="off")
        is True
    )
    assert (
        can_apply_card_ab_hold_mode_via_excel(
            bot_active=True, requested_mode="active"
        )
        is True
    )


@pytest.mark.unit
def test_manager_wires_structural_filter_before_act_writes() -> None:
    """Regression: manager MUST call filter_structural_act_candidates (VERIFY write-gate).

    Если убрать вызов фильтра из ACT-корутин, этот тест краснеет — в отличие от
    проверки только предикатов scheduling.py в отрыве от manager.
    """
    import inspect

    from app.modules.shop_runner.service_manager.manager import CoroutinesManager

    wired = (
        "update_top_key_in_advs",
        "white_list_tail_trimmer",
        "update_individual_keyword_target_places",
        "handle_stats_stale_emergency",
    )
    for name in wired:
        src = inspect.getsource(getattr(CoroutinesManager, name))
        assert "filter_structural_act_candidates" in src, name


@pytest.mark.unit
def test_import_apply_uses_excel_ab_hold_gate() -> None:
    """1.8 wiring: import_apply вызывает can_apply_card_ab_hold_mode_via_excel."""
    import inspect

    from app.client_bot.user_interface.services.adv_excel_roundtrip import import_apply

    src = inspect.getsource(import_apply.apply_adv_excel_rows)
    assert "can_apply_card_ab_hold_mode_via_excel" in src
    assert "evaluate_ab_hold_enable_stats" in src


@pytest.mark.unit
def test_enable_handler_checks_stats_freshness_gate() -> None:
    """7.1/7.2 wiring: enable_card_ab_hold вызывает evaluate + blocked message."""
    import inspect

    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
        handlers,
    )

    src = inspect.getsource(handlers.enable_card_ab_hold)
    assert "evaluate_ab_hold_enable_stats" in src
    assert "build_ab_hold_enable_blocked_by_stats_message" in src
    assert "SUPPORT_LINK" in inspect.getsource(
        __import__(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.stats_enable_gate",
            fromlist=["build_ab_hold_enable_blocked_by_stats_message"],
        )
    )


@pytest.mark.unit
def test_manager_schedules_ab_hold_from_full_advs_helper() -> None:
    """7.3 wiring: adv_settings_auto_update использует filter_ab_hold_pipeline_candidates."""
    import inspect

    from app.modules.shop_runner.service_manager.manager import CoroutinesManager

    src = inspect.getsource(CoroutinesManager.adv_settings_auto_update)
    assert "filter_ab_hold_pipeline_candidates" in src


@pytest.mark.unit
def test_enter_poll_status_lines_for_abort_and_pending() -> None:
    """5.2: poll status builder отражает LastAbort safe / PENDING."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.enter_status import (
        build_enter_poll_status_lines,
    )

    with_abort = build_enter_poll_status_lines(
        mode="pending_setup",
        abort_safe=True,
        abort_can_continue=True,
    )
    assert "безопасно" in with_abort
    pending = build_enter_poll_status_lines(
        mode="pending_setup",
        abort_safe=None,
        abort_can_continue=None,
    )
    assert "pending_setup" in pending
