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
