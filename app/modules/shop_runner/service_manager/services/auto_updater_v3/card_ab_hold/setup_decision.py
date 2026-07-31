"""ENTER setup decision: pay_for_order ≤ max CPO и views ≥ порога.

Spec: ``card-ab-hold-mode`` — Requirement ENTER setup classifies keywords.
Pure function без I/O: тесты вызывают без моков decision logic.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Sequence

from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
)

AB_HOLD_MIN_VIEWS = 100

# Transient attr на AdvSetting: CalculatedKeyword-like source для S1 pre-confirm.
AB_HOLD_S1_SOURCE_KEYWORDS_ATTR = "_ab_hold_s1_source_keywords"


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


def eligible_keyword_texts_for_confirm(
    keywords: Sequence[Any],
    *,
    max_pay_for_order: float,
    min_views: int = AB_HOLD_MIN_VIEWS,
) -> list[str]:
    """Тексты eligible-кандидатов для S1 (явный select, без auto-confirm).

    Критерий тот же, что setup classifier PASS (``pay_for_order ≤ max CPO``,
    ``views ≥ min_views``); ключи со статусом ``BAD`` исключаются.
    Read-model до confirm: не пишет allowed-set snapshot и не фиксирует
    confirmed keyword set (decision ``ab-hold-confirmed-epoch-parameters-sot`` §1).

    Args:
        keywords: ``CalculatedKeyword``-подобные объекты (``.text``, ``.views``,
            ``.pay_for_order``, опционально ``.status``).
        max_pay_for_order: потолок плана кампании.
        min_views: порог показов (default 100).

    Returns:
        Упорядоченный список текстов PASS-ключей (пустые тексты отброшены).
    """
    if float(max_pay_for_order) <= 0:
        return []
    out: list[str] = []
    for kw in keywords:
        if getattr(kw, "status", None) == KeywordStatus.BAD:
            continue
        action = classify_ab_hold_setup_keyword(
            pay_for_order=getattr(kw, "pay_for_order", None),
            views=int(getattr(kw, "views", 0) or 0),
            max_pay_for_order=max_pay_for_order,
            min_views=min_views,
        )
        if action != AbHoldSetupAction.PASS_FIX_TARGET:
            continue
        text = str(getattr(kw, "text", None) or "")
        if text:
            out.append(text)
    return out
