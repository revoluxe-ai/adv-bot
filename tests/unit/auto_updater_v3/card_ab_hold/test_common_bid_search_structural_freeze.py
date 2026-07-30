"""FINDING-PBH-004: Search common-bid applies structural A/B Hold freeze.

Writer inventory (``card-ab-hold-write-path-ownership`` OP-008):
``CoroutinesManager.update_common_bid_in_search_adv`` +
``UpdateCommotBidInSearchAdvsManager.update_common_bid_in_search_adv`` —
Allowed ``OFF``; Forbidden ``PENDING_SETUP``, ``ACTIVE``.

Decision §3 / §17: ordinary Search common-bid writes are Forbidden under
structural hold; bidder/cluster is the allowed Search bid holder.

Post-fix production path calls ``filter_structural_act_candidates`` before
freshness / stale-mutation filters and the WB write. This suite is the
post-fix regression: selection helper mirrors the fixed manager path;
predicate tests cover PENDING_SETUP / ACTIVE freeze.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    is_ab_hold_structural_freeze,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.scheduling import (
    filter_structural_act_candidates,
    should_allow_structural_act,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.stale_stats_freeze import (
    filter_ab_hold_stale_mutation_candidates,
)


def _common_bid_ready_adv(
    adv_id: int,
    *,
    mode: str,
) -> SimpleNamespace:
    """Кампания, проходящая флаги update_common_bid_in_search_adv (до mode-gate)."""
    return SimpleNamespace(
        adv_id=adv_id,
        card_ab_hold_mode=mode,
        bot_active=True,
        bidder_active=True,
        updater_common_bid_in_search_adv_active_status=True,
        search_adv_active_status=True,
        # stale_stats_freeze читает phase с adv_setting (ComplexAdv shape).
        adv_setting=SimpleNamespace(card_ab_hold_phase=None),
    )


def _production_like_common_bid_candidates(
    advs: list[SimpleNamespace],
    *,
    fresh_ids: set[int],
) -> list[SimpleNamespace]:
    """Воспроизводит post-fix selection path manager (со structural freeze).

    Зеркалит ``CoroutinesManager.update_common_bid_in_search_adv``:
    bot/bidder/common-bid/search flags → ``filter_structural_act_candidates``
    → freshness set → stale-mutation filter.
    """
    flagged = [
        adv
        for adv in advs
        if adv.bot_active
        and adv.bidder_active
        and adv.updater_common_bid_in_search_adv_active_status
        and adv.search_adv_active_status is True
    ]
    structurally_allowed = filter_structural_act_candidates(flagged)
    fresh = [
        adv for adv in structurally_allowed if int(adv.adv_id) in fresh_ids
    ]
    return filter_ab_hold_stale_mutation_candidates(fresh, fresh_ids)


@pytest.mark.unit
def test_common_bid_structural_freeze_predicates_forbid_pending_and_active() -> None:
    """Инвентарь Forbidden: PENDING_SETUP/ACTIVE → structural freeze True."""
    assert is_ab_hold_structural_freeze(CardAbHoldMode.PENDING_SETUP) is True
    assert is_ab_hold_structural_freeze(CardAbHoldMode.ACTIVE) is True
    assert should_allow_structural_act(CardAbHoldMode.PENDING_SETUP) is False
    assert should_allow_structural_act(CardAbHoldMode.ACTIVE) is False
    assert is_ab_hold_structural_freeze(CardAbHoldMode.OFF) is False
    assert should_allow_structural_act(CardAbHoldMode.OFF) is True


@pytest.mark.unit
def test_production_like_common_bid_candidates_drop_hold_modes() -> None:
    """FINDING-PBH-004: production-like selection drops PENDING/ACTIVE before WB write.

    Когда кампании в PENDING_SETUP/ACTIVE имеют common-bid updater active и fresh
    stats, production-like path (flags → structural → freshness → stale) обязан
    оставить только OFF перед ordinary Search common-bid WB write.
    """
    pool = [
        _common_bid_ready_adv(1, mode=CardAbHoldMode.OFF.value),
        _common_bid_ready_adv(2, mode=CardAbHoldMode.PENDING_SETUP.value),
        _common_bid_ready_adv(3, mode=CardAbHoldMode.ACTIVE.value),
    ]
    fresh_ids = {1, 2, 3}

    production_selected = _production_like_common_bid_candidates(
        pool, fresh_ids=fresh_ids
    )

    assert [a.adv_id for a in production_selected] == [1], (
        "FINDING-PBH-004: update_common_bid_in_search_adv write set must drop "
        "PENDING_SETUP/ACTIVE before ordinary Search common-bid WB write "
        f"(got {[a.adv_id for a in production_selected]})"
    )
    assert all(
        a.card_ab_hold_mode == CardAbHoldMode.OFF.value for a in production_selected
    )
