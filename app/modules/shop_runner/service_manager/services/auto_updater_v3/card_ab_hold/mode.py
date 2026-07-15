"""Durable состояния режима A/B Hold (PG source of truth).

Spec: ``card-ab-hold-mode``. PENDING_SETUP/ACTIVE включают structural freeze;
bidder при этом MUST оставаться разрешённым (decision write-path ownership).
"""

from __future__ import annotations

from enum import StrEnum


class CardAbHoldMode(StrEnum):
    """Режим A/B Hold на кампании (durable PG)."""

    OFF = "off"
    PENDING_SETUP = "pending_setup"
    ACTIVE = "active"


class CardAbHoldSetupBlockKind(StrEnum):
    """Детерминированная причина, по которой ENTER setup не может завершиться.

    Spec ``card-ab-hold-mode`` / decision §14b: пока mode PENDING_SETUP кампания
    исключена из ordinary automation; если setup детерминированно не прогрессирует,
    UI MUST показать конкретную причину и действие (а не generic «Подготовка…»).
    Значения — durable-safe строки для Redis-канала причины блока (без миграции PG).
    """

    EMPTY_ALLOWED_SET = "empty_allowed_set"
    MISSING_MAX_CPO = "missing_max_cpo"


def normalize_card_ab_hold_mode(raw: str | CardAbHoldMode | None) -> CardAbHoldMode:
    """Нормализовать сырое значение БД/UI к ``CardAbHoldMode`` (default OFF).

    Нужен для безопасного чтения legacy/None и Excel roundtrip без падений.
    """
    if raw is None:
        return CardAbHoldMode.OFF
    if isinstance(raw, CardAbHoldMode):
        return raw
    try:
        return CardAbHoldMode(str(raw).strip().lower())
    except ValueError:
        return CardAbHoldMode.OFF


def is_ab_hold_structural_freeze(mode: CardAbHoldMode | str | None) -> bool:
    """True, если структурные ACT (БС/ЦП/enable) MUST NOT выполняться.

    Spec: ordinary structural auto-update suspended during preparation and hold.
    """
    m = normalize_card_ab_hold_mode(mode)
    return m in (CardAbHoldMode.PENDING_SETUP, CardAbHoldMode.ACTIVE)
