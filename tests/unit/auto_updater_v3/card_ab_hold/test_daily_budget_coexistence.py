"""Daily-budget coexistence со stale-freeze (§18.5.7 / §23.6).

Freeze keyword/bid мутаций MUST NOT блокировать ``ensure_campaigns_active``;
freeze ≠ stop campaign.
"""

from __future__ import annotations

import inspect
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


def _active_adv(
    adv_id: int,
    *,
    phase: str = CardAbHoldPhase.READY_ACTIVE.value,
    intent: dict[str, object] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        adv_id=adv_id,
        card_ab_hold_mode=CardAbHoldMode.ACTIVE.value,
        adv_setting=SimpleNamespace(
            card_ab_hold_phase=phase,
            card_ab_hold_pending_intent_json=intent or {"generation": 1},
            card_ab_hold_confirmed_target_places_json={"kw": 10},
            card_ab_hold_confirmed_keywords_json=["kw"],
        ),
    )


@pytest.mark.unit
def test_active_fresh_not_frozen_for_keyword_bid_mutations() -> None:
    """A: ACTIVE + fresh stats → freeze=False; кампания остаётся в mutation pool."""
    assert (
        should_freeze_keyword_and_bid_mutations(
            mode=CardAbHoldMode.ACTIVE,
            phase=CardAbHoldPhase.READY_ACTIVE.value,
            stats_fresh=True,
        )
        is False
    )
    pool = [_active_adv(101), _active_adv(102)]
    fresh_ids = {101, 102}
    filtered = filter_ab_hold_stale_mutation_candidates(pool, fresh_ids)
    assert [a.adv_id for a in filtered] == [101, 102]


@pytest.mark.unit
def test_freeze_helpers_do_not_clear_epoch_intent_on_simulated_budget_pause() -> None:
    """A: stale-freeze filter read-only — intent/confirmed TP не мутируются."""
    adv = _active_adv(
        201,
        intent={"generation": 3, "keywords": ["kw"]},
    )
    before_intent = adv.adv_setting.card_ab_hold_pending_intent_json
    before_tp = adv.adv_setting.card_ab_hold_confirmed_target_places_json

    # stale ACTIVE исключается из keyword/bid handlers, но объект не трогается
    filtered = filter_ab_hold_stale_mutation_candidates([adv], fresh_ids=set())
    assert filtered == []
    assert adv.adv_setting.card_ab_hold_pending_intent_json == before_intent
    assert adv.adv_setting.card_ab_hold_confirmed_target_places_json == before_tp


@pytest.mark.unit
def test_active_stale_freezes_mutations_but_not_stop() -> None:
    """B: ACTIVE + stale → freeze=True; freeze predicate ≠ stop-path."""
    from app.modules.shop_runner.service_manager.manager import CoroutinesManager

    assert (
        should_freeze_keyword_and_bid_mutations(
            mode=CardAbHoldMode.ACTIVE,
            phase=CardAbHoldPhase.READY_ACTIVE.value,
            stats_fresh=False,
        )
        is True
    )
    assert not hasattr(CoroutinesManager, "stop_campaign_for_stale_ab_hold")
    pool = [_active_adv(301)]
    assert filter_ab_hold_stale_mutation_candidates(pool, fresh_ids=set()) == []


@pytest.mark.unit
def test_ensure_campaigns_active_not_gated_by_stale_mutation_filter() -> None:
    """B: ``ensure_campaigns_active`` получает полный advs pool без stale filter."""
    from app.modules.shop_runner.service_manager.manager import CoroutinesManager

    watchdog_src = inspect.getsource(CoroutinesManager.auto_budget_watchdog)
    assert "_run_auto_adv_active_control(advs)" in watchdog_src
    assert "filter_ab_hold_stale_mutation_candidates" not in watchdog_src

    active_control_src = inspect.getsource(CoroutinesManager._run_auto_adv_active_control)
    assert "ensure_campaigns_active" in active_control_src
    assert "filter_ab_hold_stale_mutation_candidates" not in active_control_src

    reset_src = inspect.getsource(CoroutinesManager.auto_reset_bid_for_auto_adv)
    assert "filter_ab_hold_stale_mutation_candidates" in reset_src
