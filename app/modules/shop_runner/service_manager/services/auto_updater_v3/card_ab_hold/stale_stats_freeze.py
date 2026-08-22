"""Freeze keyword/bid мутаций при stale stats без остановки кампании (§17 / tasks §23).

Decision ``card-ab-hold-write-path-ownership`` §17: во время WARM_UP, PENDING или
ACTIVE при stale/missing статистике **decide-class** решения о включении/исключении
ключей (включая ENTER/setup FAIL→OFF / PBH-001) и мутации Search/Auto ставок MUST
замереть; это MUST NOT быть самостоятельной причиной stop кампании (orthogonal к
``ensure_campaigns_active`` / daily budget).

**PBH-005 carve-out:** apply snapshot уже записанного durable PENDING intent
(``apply_confirmed_intent_to_pg`` / ``sync_intent_to_wb`` в ``process_ab_epoch``)
НЕ входит в этот freeze — не вызывать этот модуль как gate перед apply/sync.

Дополнение к ``filter_structural_act_candidates`` (structural freeze по mode):
stale-freeze — отдельный слой для hold-tick / AutoReset / ordinary common bid /
hold enforcement / epoch-managed setup FAIL→OFF, когда freshness-класс stale, но
кампания остаётся в eligible pool (§2a PENDING liveness).
"""

from __future__ import annotations

from typing import Protocol, Sequence, TypeVar

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_lifecycle import (
    is_awaiting_confirm_phase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    normalize_card_ab_hold_mode,
    normalize_card_ab_hold_phase,
)


class _HasAbHoldContext(Protocol):
    """Минимальный контракт adv для stale-freeze filter.

    ``adv_id`` — property (не mutable attribute), чтобы ComplexAdv и
    SimpleNamespace-тесты удовлетворяли Protocol без invariance ошибок.
    """

    @property
    def adv_id(self) -> int: ...

    @property
    def card_ab_hold_mode(self) -> str | CardAbHoldMode | None: ...

    @property
    def adv_setting(self) -> object: ...


TAdv = TypeVar("TAdv", bound=_HasAbHoldContext)


def should_freeze_keyword_and_bid_mutations(
    *,
    mode: CardAbHoldMode | str | None,
    phase: str | None,
    stats_fresh: bool,
) -> bool:
    """True — keyword inclusion/exclusion и Search/Auto bid-мутации MUST NOT выполняться.

    Args:
        mode: durable ``card_ab_hold_mode``.
        phase: ``card_ab_hold_phase`` (NULL = legacy MVP-1 без epoch confirms).
        stats_fresh: True, если кампания/ключ проходит freshness-класс ordinary automation.

    Returns:
        True, если мутации должны быть заморожены (stale/missing stats + hold context).
        False при fresh stats или вне hold-контекста.
    """
    if stats_fresh:
        return False
    normalized_mode = normalize_card_ab_hold_mode(mode)
    if normalized_mode in (CardAbHoldMode.PENDING_SETUP, CardAbHoldMode.ACTIVE):
        return True
    normalized_phase = normalize_card_ab_hold_phase(phase)
    if is_awaiting_confirm_phase(normalized_phase):
        return True
    return False


def filter_ab_hold_stale_mutation_candidates(
    advs: Sequence[TAdv],
    fresh_ids: set[int],
) -> list[TAdv]:
    """Исключить hold-context кампании со stale stats из keyword/bid handlers (§23).

    ``filter_structural_act_candidates`` блокирует structural ACT по mode
    (PENDING/ACTIVE). Этот filter — дополнительный слой: при stale stats
    keyword inclusion/exclusion и Search/Auto bid мутации MUST NOT выполняться,
    но кампания остаётся eligible для setup/hold/epoch tick (freeze ≠ stop).

    Args:
        advs: кандидаты handler pool (после или без freshness split).
        fresh_ids: ``adv_id`` кампаний с fresh stats (из ``_split_advs_by_stats_freshness``).

    Returns:
        Подмножество ``advs``, для которых keyword/bid мутации разрешены.
    """
    out: list[TAdv] = []
    for adv in advs:
        stats_fresh = int(adv.adv_id) in fresh_ids
        phase = getattr(adv.adv_setting, "card_ab_hold_phase", None)
        if should_freeze_keyword_and_bid_mutations(
            mode=adv.card_ab_hold_mode,
            phase=phase,
            stats_fresh=stats_fresh,
        ):
            continue
        out.append(adv)
    return out
