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
    """§9: Excel gate always denies (incl. bot_active=False and active request)."""
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
    assert (
        can_apply_card_ab_hold_mode_via_excel(bot_active=False, requested_mode="off")
        is False
    )
    assert (
        can_apply_card_ab_hold_mode_via_excel(
            bot_active=True, requested_mode="active"
        )
        is False
    )


@pytest.mark.unit
def test_manager_act_coroutines_reference_structural_filter() -> None:
    """Regression: ACT-корутины manager ссылаются на filter_structural_act_candidates.

    Проверка ``co_names`` (не ``inspect.getsource``): убрать вызов фильтра из
    bytecode → красный тест. Поведенческий filter уже покрыт выше в этом файле;
    enable/excel wiring — в launch_validity / excel suite.
    """
    from app.modules.shop_runner.service_manager.manager import CoroutinesManager

    wired = (
        "handle_stats_stale_emergency",
        "update_minus_phrases_in_advs",
        "delete_keywords_from_wl_by_mean_auto_ctr",
    )
    def _unwrap(fn: object) -> object:
        """Снять while_coroutines / decorator wrappers до реального callable."""
        while hasattr(fn, "__wrapped__"):
            fn = getattr(fn, "__wrapped__")
        return fn

    for name in wired:
        code = getattr(_unwrap(getattr(CoroutinesManager, name)), "__code__")
        assert "filter_structural_act_candidates" in code.co_names, name

    auto_code = getattr(
        _unwrap(CoroutinesManager.adv_settings_auto_update), "__code__"
    )
    assert "filter_ab_hold_pipeline_candidates" in auto_code.co_names


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
    assert "можно запускать A/B" not in pending.lower()
