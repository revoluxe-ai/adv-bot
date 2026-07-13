"""Scheduling helpers A/B Hold (spec ``card-ab-hold-mode``).

Чистые предикати для exclusion ordinary V3 и structural ACT —
удобно тестировать без MagicMock manager.
"""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    is_ab_hold_structural_freeze,
    normalize_card_ab_hold_mode,
)


def should_run_ab_setup(mode: CardAbHoldMode | str | None) -> bool:
    """PENDING_SETUP → только setup entrypoint."""
    return normalize_card_ab_hold_mode(mode) == CardAbHoldMode.PENDING_SETUP


def should_run_ab_hold(mode: CardAbHoldMode | str | None) -> bool:
    """ACTIVE → только hold entrypoint."""
    return normalize_card_ab_hold_mode(mode) == CardAbHoldMode.ACTIVE


def should_schedule_ordinary_updater(mode: CardAbHoldMode | str | None) -> bool:
    """Ordinary V2/V3 structural только при OFF."""
    return normalize_card_ab_hold_mode(mode) == CardAbHoldMode.OFF


def should_allow_structural_act(mode: CardAbHoldMode | str | None) -> bool:
    """WL / individual TP / trim — только если нет structural freeze."""
    return not is_ab_hold_structural_freeze(mode)


def should_allow_bidder_on_ab_hold(mode: CardAbHoldMode | str | None) -> bool:
    """Bidder MUST оставаться допустим при PENDING/ACTIVE (и при OFF).

    Spec/decision: hold ≠ остановка биддера.
    """
    _ = mode
    return True
