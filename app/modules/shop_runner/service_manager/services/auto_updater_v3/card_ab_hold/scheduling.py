"""Scheduling / ACT candidate filters A/B Hold (spec ``card-ab-hold-mode``).

Чистые предикати и фильтры списков кампаний **до** handler/write boundary —
те же функции использует ``manager`` (не только unit-хелперы).
"""

from __future__ import annotations

from typing import Protocol, Sequence, TypeVar

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    is_ab_hold_structural_freeze,
    is_epoch_managed_ab_hold,
    normalize_card_ab_hold_mode,
)


class _HasCardAbHoldMode(Protocol):
    """Минимальный контракт adv для structural/bidder filters."""

    @property
    def card_ab_hold_mode(self) -> str | CardAbHoldMode | None: ...


TAdv = TypeVar("TAdv", bound=_HasCardAbHoldMode)


def should_run_ab_setup(mode: CardAbHoldMode | str | None) -> bool:
    """PENDING_SETUP → только setup entrypoint."""
    return normalize_card_ab_hold_mode(mode) == CardAbHoldMode.PENDING_SETUP


def should_run_ab_hold(mode: CardAbHoldMode | str | None) -> bool:
    """ACTIVE → только hold entrypoint."""
    return normalize_card_ab_hold_mode(mode) == CardAbHoldMode.ACTIVE


def should_run_ab_epoch(
    mode: CardAbHoldMode | str | None,
    phase: str | None,
) -> bool:
    """``PENDING_SETUP`` + non-NULL phase → epoch tick (§19–§22), не legacy setup.

    Legacy MVP-1 (``phase IS NULL``) MUST продолжать ``process_ab_setup``.
    """
    if normalize_card_ab_hold_mode(mode) != CardAbHoldMode.PENDING_SETUP:
        return False
    return is_epoch_managed_ab_hold(phase=phase)


def should_schedule_ordinary_updater(mode: CardAbHoldMode | str | None) -> bool:
    """Ordinary V2/V3 structural только при OFF."""
    return normalize_card_ab_hold_mode(mode) == CardAbHoldMode.OFF


def should_allow_structural_act(mode: CardAbHoldMode | str | None) -> bool:
    """WL / individual TP / trim / emergency — только если нет structural freeze."""
    return not is_ab_hold_structural_freeze(mode)


def should_allow_bidder_on_ab_hold(mode: CardAbHoldMode | str | None) -> bool:
    """Bidder MUST оставаться допустим при PENDING/ACTIVE (и при OFF).

    Spec/decision: hold ≠ остановка биддера. Guard не фильтрует bidder candidates.
    """
    _ = mode
    return True


def filter_structural_act_candidates(advs: Sequence[TAdv]) -> list[TAdv]:
    """Оставить только кампании, которым разрешён structural ACT write.

    Вызывается в ``manager`` **до** создания handlers / WB write.
    PENDING_SETUP и ACTIVE отфильтровываются (freeze).
    """
    return [adv for adv in advs if should_allow_structural_act(adv.card_ab_hold_mode)]


def filter_bidder_eligible_by_ab_hold(advs: Sequence[TAdv]) -> list[TAdv]:
    """A/B Hold НЕ исключает кампании из bidder/cluster-bids eligibility.

    Decision ``card-ab-hold-write-path-ownership``: bidder MUST remain allowed.
    """
    return [adv for adv in advs if should_allow_bidder_on_ab_hold(adv.card_ab_hold_mode)]


def filter_ab_hold_pipeline_candidates(
    advs: Sequence[TAdv],
) -> list[tuple[TAdv, CardAbHoldMode]]:
    """Кампании для setup/hold из **полного** списка (не ``advs_filtred``).

    Decision §2a: PENDING→setup, ACTIVE→hold; stale не отсекает post-enter.
    Returns:
        Пары (adv, mode) только для PENDING_SETUP / ACTIVE.
    """
    out: list[tuple[TAdv, CardAbHoldMode]] = []
    for adv in advs:
        mode = normalize_card_ab_hold_mode(adv.card_ab_hold_mode)
        if mode in (CardAbHoldMode.PENDING_SETUP, CardAbHoldMode.ACTIVE):
            out.append((adv, mode))
    return out


def can_apply_card_ab_hold_mode_via_excel(
    *,
    bot_active: bool,
    requested_mode: CardAbHoldMode | str | None,
    stats_fresh_enough: bool = True,
) -> bool:
    """Excel MUST NOT apply A/B Hold mode (decision §9 / MVP out).

    Always returns False. Enable/disable — только paid Telegram UI.
    Leftover Excel payload is ignored by schema (no EDIT column) / import_apply.
    Args kept for call-site compatibility until callers are fully removed.
    """
    _ = (bot_active, requested_mode, stats_fresh_enough)
    return False
