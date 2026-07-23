"""Unit-тесты stale stats freeze keyword/bid мутаций (§23)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    CardAbHoldPhase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.stale_stats_freeze import (
    filter_ab_hold_stale_mutation_candidates,
    should_freeze_keyword_and_bid_mutations,
)


def _adv(
    adv_id: int,
    *,
    mode: str,
    phase: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        adv_id=adv_id,
        card_ab_hold_mode=mode,
        adv_setting=SimpleNamespace(card_ab_hold_phase=phase),
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("mode", "phase", "stats_fresh", "expected"),
    [
        (CardAbHoldMode.OFF, None, False, False),
        (CardAbHoldMode.PENDING_SETUP, None, False, True),
        (CardAbHoldMode.ACTIVE, CardAbHoldPhase.READY_ACTIVE.value, False, True),
        (CardAbHoldMode.ACTIVE, CardAbHoldPhase.READY_ACTIVE.value, True, False),
        (CardAbHoldMode.PENDING_SETUP, CardAbHoldPhase.WARM_UP.value, False, True),
        (CardAbHoldMode.PENDING_SETUP, CardAbHoldPhase.WARM_UP.value, True, False),
    ],
)
def test_should_freeze_keyword_and_bid_mutations(
    mode: CardAbHoldMode | str,
    phase: str | None,
    stats_fresh: bool,
    expected: bool,
) -> None:
    """§23.1–23.2: freeze при stale в hold-контексте; fresh → no freeze."""
    assert (
        should_freeze_keyword_and_bid_mutations(
            mode=mode,
            phase=phase,
            stats_fresh=stats_fresh,
        )
        is expected
    )


@pytest.mark.unit
def test_filter_ab_hold_stale_mutation_candidates() -> None:
    """Stale hold ACTIVE исключается; OFF и fresh ACTIVE остаются."""
    pool = [
        _adv(1, mode=CardAbHoldMode.OFF.value),
        _adv(2, mode=CardAbHoldMode.ACTIVE.value, phase=CardAbHoldPhase.READY_ACTIVE.value),
        _adv(3, mode=CardAbHoldMode.ACTIVE.value, phase=CardAbHoldPhase.READY_ACTIVE.value),
        _adv(4, mode=CardAbHoldMode.PENDING_SETUP.value, phase=CardAbHoldPhase.WARM_UP.value),
    ]
    fresh_ids = {1, 3}
    filtered = filter_ab_hold_stale_mutation_candidates(pool, fresh_ids)
    assert [a.adv_id for a in filtered] == [1, 3]


@pytest.mark.unit
def test_freeze_does_not_imply_stop_campaign() -> None:
    """§23.3: freeze — predicate на мутации, не вызов stop-path."""
    from app.modules.shop_runner.service_manager.manager import CoroutinesManager

    assert not hasattr(
        CoroutinesManager,
        "stop_campaign_for_stale_ab_hold",
    )
    assert should_freeze_keyword_and_bid_mutations(
        mode=CardAbHoldMode.ACTIVE,
        phase=CardAbHoldPhase.READY_ACTIVE.value,
        stats_fresh=False,
    )
    # freeze=True не означает mode OFF — hold может оставаться ACTIVE
