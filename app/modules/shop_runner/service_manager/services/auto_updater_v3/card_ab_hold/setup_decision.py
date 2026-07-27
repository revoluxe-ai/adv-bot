"""ENTER setup decision: pay_for_order ≤ max CPO и views ≥ порога.

Spec: ``card-ab-hold-mode`` — Requirement ENTER setup classifies keywords.
Pure function без I/O: тесты вызывают без моков decision logic.
"""

from __future__ import annotations

from enum import StrEnum

AB_HOLD_MIN_VIEWS = 100


class AbHoldSetupAction(StrEnum):
    """Результат классификации ключа на ENTER."""

    PASS_FIX_TARGET = "pass_fix_target"
    FAIL_OFF = "fail_off"


def classify_ab_hold_setup_keyword(
    *,
    pay_for_order: float | None,
    views: int,
    max_pay_for_order: float,
    min_views: int = AB_HOLD_MIN_VIEWS,
) -> AbHoldSetupAction:
    """Классифицировать ключ для A/B Hold ENTER.

    PASS: ``pay_for_order`` не None, ``views >= min_views``, ``pay_for_order <= max``.
    Иначе FAIL_OFF (в т.ч. отсутствие pay_for_order).

    Args:
        pay_for_order: себестоимость ключа (как в карточке).
        views: показы из окна статистики карточки ключа.
        max_pay_for_order: потолок плана (не resolve).
        min_views: порог показов (default 100).

    Returns:
        PASS_FIX_TARGET или FAIL_OFF.
    """
    if pay_for_order is None:
        return AbHoldSetupAction.FAIL_OFF
    if int(views) < int(min_views):
        return AbHoldSetupAction.FAIL_OFF
    if float(pay_for_order) > float(max_pay_for_order):
        return AbHoldSetupAction.FAIL_OFF
    return AbHoldSetupAction.PASS_FIX_TARGET
