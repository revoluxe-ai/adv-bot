"""Durable состояния режима A/B Hold (PG source of truth).

Spec: ``card-ab-hold-mode``. PENDING_SETUP/ACTIVE включают structural freeze;
bidder при этом MUST оставаться разрешённым (decision write-path ownership).

Phase (``card_ab_hold_phase``): NULL = legacy MVP-1 (§18.5); non-NULL = epoch-managed
flow (§18.4 / decisions epoch lifecycle). Migration defaults MUST keep NULL.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class CardAbHoldMode(StrEnum):
    """Режим A/B Hold на кампании (durable PG)."""

    OFF = "off"
    PENDING_SETUP = "pending_setup"
    ACTIVE = "active"


class CardAbHoldPhase(StrEnum):
    """Эпохальная фаза внутри PENDING (NULL на AdvSetting = legacy MVP-1).

    Tasks §19.5 / decision ``ab-hold-epoch-lifecycle-and-generation-ownership``.
    """

    AWAITING_KEYWORD_CONFIRM = "awaiting_keyword_confirm"
    WARM_UP = "warm_up"
    AWAITING_TP_CONFIRM = "awaiting_tp_confirm"
    AWAITING_AUTO_PARTICIPATION_CONFIRM = "awaiting_auto_participation_confirm"
    AWAITING_AUTO_BID_CONFIRM = "awaiting_auto_bid_confirm"
    PENDING_INTENT = "pending_intent"
    WB_SYNC = "wb_sync"
    READY_ACTIVE = "ready_active"


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


def normalize_card_ab_hold_phase(
    raw: str | CardAbHoldPhase | None,
) -> CardAbHoldPhase | None:
    """Нормализовать PG ``card_ab_hold_phase``; ``None``/пусто = legacy MVP-1.

    Args:
        raw: сырое значение колонки или enum.

    Returns:
        ``CardAbHoldPhase`` либо ``None`` (legacy / OFF).
    """
    if raw is None:
        return None
    if isinstance(raw, CardAbHoldPhase):
        return raw
    text = str(raw).strip().lower()
    if not text:
        return None
    try:
        return CardAbHoldPhase(text)
    except ValueError:
        return None


def is_epoch_managed_ab_hold(adv_setting: Any | None = None, *, phase: Any = None) -> bool:
    """True, если кампания на epoch-managed flow (phase non-NULL).

    Spec/tasks §18.4–§18.5: ``card_ab_hold_phase IS NULL`` → legacy MVP-1
    (``process_ab_setup`` MAY → ACTIVE). Non-NULL phase → legacy auto-ACTIVE и
    ENTER TP-write Forbidden; ACTIVE только через intent → WB sync.
    """
    if phase is not None:
        return normalize_card_ab_hold_phase(phase) is not None
    if adv_setting is None:
        return False
    return normalize_card_ab_hold_phase(
        getattr(adv_setting, "card_ab_hold_phase", None)
    ) is not None


def is_ab_hold_structural_freeze(mode: CardAbHoldMode | str | None) -> bool:
    """True, если структурные ACT (БС/ЦП/enable) MUST NOT выполняться.

    Spec: ordinary structural auto-update suspended during preparation and hold.
    """
    m = normalize_card_ab_hold_mode(mode)
    return m in (CardAbHoldMode.PENDING_SETUP, CardAbHoldMode.ACTIVE)
