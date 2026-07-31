"""Чистая доменная логика epoch lifecycle A/B Hold (§19 / §22).

Spec ``card-ab-hold-mode`` / decision ``ab-hold-epoch-lifecycle-and-generation-ownership``:
WARM_UP-таймер, generation, idempotency key, PENDING intent payload и сброс полей на EXIT.
Без PG/WB side-effects — write-path в ``epoch_write.py``.
"""

from __future__ import annotations

import datetime
import math
from enum import StrEnum
from typing import Any

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldPhase,
    normalize_card_ab_hold_phase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.not_full_target_place import (
    clamp_not_full_target_place,
)

DEFAULT_WARMUP_HOURS = 24
MIN_WARMUP_HOURS = 24


class CardAbHoldSyncStatus(StrEnum):
    """Статус WB-синхронизации эпохи (durable PG ``card_ab_hold_sync_status``)."""

    NONE = "none"
    PENDING = "pending"
    PARTIAL = "partial"
    COMPLETE = "complete"


def normalize_card_ab_hold_sync_status(
    raw: str | CardAbHoldSyncStatus | None,
) -> CardAbHoldSyncStatus:
    """Нормализовать сырое значение sync_status (unknown → ``none``)."""
    if raw is None:
        return CardAbHoldSyncStatus.NONE
    if isinstance(raw, CardAbHoldSyncStatus):
        return raw
    text = str(raw).strip().lower()
    if not text:
        return CardAbHoldSyncStatus.NONE
    try:
        return CardAbHoldSyncStatus(text)
    except ValueError:
        return CardAbHoldSyncStatus.NONE


def clamp_warmup_duration_hours(hours: int) -> int:
    """Склеить длительность WARM_UP: минимум 24 часа (§19).

    Args:
        hours: запрошенная длительность.

    Returns:
        ``max(hours, MIN_WARMUP_HOURS)``.

    Raises:
        ValueError: если ``hours < MIN_WARMUP_HOURS`` (reject below 24).
    """
    if hours < MIN_WARMUP_HOURS:
        raise ValueError(
            f"WARM_UP duration MUST NOT be below {MIN_WARMUP_HOURS} hours, got {hours}"
        )
    return max(int(hours), MIN_WARMUP_HOURS)


def is_warmup_elapsed(
    started_at: datetime.datetime | None,
    duration_hours: int,
    *,
    now: datetime.datetime | None = None,
) -> bool:
    """True, если WARM_UP-таймер истёк (started_at + duration_hours).

    Args:
        started_at: момент старта WARM_UP (timezone-aware).
        duration_hours: durable длительность эпохи (≥24).
        now: опциональный «текущий» момент для тестов.
    """
    if started_at is None:
        return False
    if now is None:
        now = datetime.datetime.now(datetime.timezone.utc)
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=datetime.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=datetime.timezone.utc)
    delta = now - started_at
    return delta >= datetime.timedelta(hours=int(duration_hours))


def target_place_from_factual_position(position: float) -> int | None:
    """Предложенная ЦП из фактической позиции (чистая математика, без PG).

    Эквивалент ``ab_hold_target_place_from_keyword`` из ``setup_apply.py``.
    """
    pos = float(position)
    if pos <= 0:
        return None
    return clamp_not_full_target_place(int(math.floor(pos + 0.5)))


def propose_target_places_from_positions(
    positions: dict[str, float],
) -> dict[str, int]:
    """Предложить target places по факт-позициям ключей (post-WARM_UP UI).

    Args:
        positions: keyword text → factual position.

    Returns:
        keyword text → proposed target place (только для pos > 0).
    """
    out: dict[str, int] = {}
    for keyword, pos in positions.items():
        place = target_place_from_factual_position(pos)
        if place is not None:
            out[keyword] = place
    return out


def build_pending_intent_payload(
    *,
    generation: int,
    keywords: list[str],
    target_places: dict[str, int],
    auto_participation: bool,
    auto_bid: float,
) -> dict[str, Any]:
    """Собрать durable PENDING intent snapshot (§22.5).

    Записывается в ``card_ab_hold_pending_intent_json`` до первой WB-мутации эпохи.
    """
    return {
        "generation": int(generation),
        "keywords": list(keywords),
        "target_places": dict(target_places),
        "auto_participation": bool(auto_participation),
        "auto_bid": float(auto_bid),
    }


def build_wb_sync_idempotency_key(adv_id: int, generation: int) -> str:
    """Формат idempotency key: ``{adv_id}:{generation}`` (§22.5)."""
    return f"{int(adv_id)}:{int(generation)}"


def clear_epoch_fields_values() -> dict[str, Any]:
    """Значения полей epoch для EXIT-reset (§22.5 / tasks §22).

    Generation сбрасывается в 0; warmup duration — default 24.
    """
    return {
        "card_ab_hold_phase": None,
        "card_ab_hold_warmup_started_at": None,
        "card_ab_hold_warmup_duration_hours": DEFAULT_WARMUP_HOURS,
        "card_ab_hold_generation": 0,
        "card_ab_hold_wb_sync_idempotency_key": None,
        "card_ab_hold_pending_intent_json": None,
        "card_ab_hold_sync_status": CardAbHoldSyncStatus.NONE.value,
        "card_ab_hold_confirmed_keywords_json": None,
        "card_ab_hold_confirmed_target_places_json": None,
        "card_ab_hold_confirmed_auto_participation": None,
        "card_ab_hold_confirmed_auto_bid": None,
    }


def all_confirms_complete(adv_setting: Any) -> bool:
    """True, если все confirmed epoch-параметры заполнены (§22 intent precondition).

    Args:
        adv_setting: объект с полями ``card_ab_hold_confirmed_*`` (AdvSetting-like).
    """
    keywords_raw = getattr(adv_setting, "card_ab_hold_confirmed_keywords_json", None)
    target_places_raw = getattr(
        adv_setting, "card_ab_hold_confirmed_target_places_json", None
    )
    auto_participation = getattr(
        adv_setting, "card_ab_hold_confirmed_auto_participation", None
    )
    auto_bid = getattr(adv_setting, "card_ab_hold_confirmed_auto_bid", None)
    if not isinstance(keywords_raw, list) or not keywords_raw:
        return False
    if not isinstance(target_places_raw, dict) or not target_places_raw:
        return False
    if auto_participation is None:
        return False
    if auto_bid is None:
        return False
    return True


def is_legacy_mvp1_phase(phase: Any) -> bool:
    """True, если ``card_ab_hold_phase IS NULL`` (legacy MVP-1, §18.5)."""
    return normalize_card_ab_hold_phase(phase) is None


def is_awaiting_confirm_phase(phase: CardAbHoldPhase | str | None) -> bool:
    """True для фаз awaiting_* и WARM_UP (pre-ACTIVE confirm path)."""
    p = normalize_card_ab_hold_phase(phase)
    if p is None:
        return False
    return p in (
        CardAbHoldPhase.AWAITING_KEYWORD_CONFIRM,
        CardAbHoldPhase.WARM_UP,
        CardAbHoldPhase.AWAITING_TP_CONFIRM,
        CardAbHoldPhase.AWAITING_AUTO_PARTICIPATION_CONFIRM,
        CardAbHoldPhase.AWAITING_AUTO_BID_CONFIRM,
        CardAbHoldPhase.PENDING_INTENT,
        CardAbHoldPhase.WB_SYNC,
    )
