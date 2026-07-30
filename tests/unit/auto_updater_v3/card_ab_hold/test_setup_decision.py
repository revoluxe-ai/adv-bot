"""Unit-тесты ENTER setup decision (spec ``card-ab-hold-mode``).

Проверяют classify_ab_hold_setup_keyword без мока decision-функции —
чтобы регрессия критерия PASS/FAIL ломала тест.
"""

from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    is_ab_hold_structural_freeze,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.setup_decision import (
    AB_HOLD_MIN_VIEWS,
    AbHoldSetupAction,
    classify_ab_hold_setup_keyword,
)


@pytest.mark.unit
def test_ab_hold_setup_pass_when_pfo_le_max_and_views_ok() -> None:
    """Spec card-ab-hold-mode: PASS при pay_for_order ≤ max и views ≥ 100."""
    action = classify_ab_hold_setup_keyword(
        pay_for_order=100.0,
        views=AB_HOLD_MIN_VIEWS,
        max_pay_for_order=100.0,
    )
    assert action == AbHoldSetupAction.PASS_FIX_TARGET


@pytest.mark.unit
def test_ab_hold_setup_fail_when_pfo_over_max() -> None:
    """Spec card-ab-hold-mode: FAIL→OFF при pay_for_order > max CPO."""
    action = classify_ab_hold_setup_keyword(
        pay_for_order=100.01,
        views=500,
        max_pay_for_order=100.0,
    )
    assert action == AbHoldSetupAction.FAIL_OFF


@pytest.mark.unit
def test_ab_hold_setup_fail_when_views_below_threshold() -> None:
    """Spec card-ab-hold-mode: FAIL→OFF при views < 100."""
    action = classify_ab_hold_setup_keyword(
        pay_for_order=50.0,
        views=AB_HOLD_MIN_VIEWS - 1,
        max_pay_for_order=200.0,
    )
    assert action == AbHoldSetupAction.FAIL_OFF


@pytest.mark.unit
def test_ab_hold_setup_fail_when_pay_for_order_missing() -> None:
    """Spec card-ab-hold-mode: FAIL→OFF при отсутствии pay_for_order."""
    action = classify_ab_hold_setup_keyword(
        pay_for_order=None,
        views=500,
        max_pay_for_order=200.0,
    )
    assert action == AbHoldSetupAction.FAIL_OFF


@pytest.mark.unit
@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (CardAbHoldMode.OFF, False),
        (CardAbHoldMode.PENDING_SETUP, True),
        (CardAbHoldMode.ACTIVE, True),
        ("off", False),
        ("pending_setup", True),
        ("active", True),
        (" PENDING_SETUP ", True),
        ("Active", True),
        (None, False),
        ("", False),
        ("unknown_mode", False),
    ],
)
def test_ab_hold_structural_freeze_modes(
    mode: CardAbHoldMode | str | None,
    expected: bool,
) -> None:
    """Spec card-ab-hold-mode: freeze только PENDING_SETUP и ACTIVE.

    Защищает ``is_ab_hold_structural_freeze``: enum, PG/UI-строки (normalize),
    None/пустые/неизвестные → OFF → no freeze. Без этого ordinary structural
    ACT (БС/ЦП/enable) могли бы пропускаться или блокироваться ошибочно.
    """
    assert is_ab_hold_structural_freeze(mode) is expected
