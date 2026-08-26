"""Daily-budget coexistence со stale-freeze (§18.5.7 / §23.6).

Freeze keyword/bid мутаций MUST NOT блокировать ``ensure_campaigns_active``;
freeze ≠ stop campaign.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.manager import CoroutinesManager
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
    """ACTIVE Hold campaign stub for coexistence predicates."""
    return SimpleNamespace(
        adv_id=adv_id,
        bot_active=True,
        auto_budget_watchdog_enabled=False,
        use_common_budget=False,
        card_ab_hold_mode=CardAbHoldMode.ACTIVE.value,
        adv_setting=SimpleNamespace(
            id=adv_id,
            card_ab_hold_phase=phase,
            card_ab_hold_pending_intent_json=intent or {"generation": 1},
            card_ab_hold_confirmed_target_places_json={"kw": 10},
            card_ab_hold_confirmed_keywords_json=["kw"],
        ),
    )


def _manager_stub() -> CoroutinesManager:
    """Minimal CoroutinesManager instance for binding real methods."""
    mgr = object.__new__(CoroutinesManager)
    mgr._wb_manager_hub = MagicMock()
    mgr._tasks_manager = MagicMock()
    mgr._plan_fact_reader = MagicMock()
    mgr._auto_shelf_bid_control_view_provider = MagicMock()
    mgr._redis_campaign_activity_reason_manager = MagicMock()
    mgr._ensure_budget_for_campaign_start_retry = AsyncMock()
    return mgr


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

    filtered = filter_ab_hold_stale_mutation_candidates([adv], fresh_ids=set())
    assert filtered == []
    assert adv.adv_setting.card_ab_hold_pending_intent_json == before_intent
    assert adv.adv_setting.card_ab_hold_confirmed_target_places_json == before_tp


@pytest.mark.unit
def test_active_stale_freezes_mutations_but_not_stop() -> None:
    """B: ACTIVE + stale → freeze=True; freeze predicate ≠ stop-path."""
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
@pytest.mark.asyncio
async def test_ensure_campaigns_active_receives_full_advs_pool() -> None:
    """B: ``_run_auto_adv_active_control`` передаёт полный pool в ensure (без stale filter)."""
    pool = [_active_adv(301), _active_adv(302)]
    ensure = AsyncMock()
    mgr = _manager_stub()
    service = MagicMock()
    service.ensure_campaigns_active = ensure

    with patch(
        "app.modules.shop_runner.service_manager.manager.AutoAdvActiveControlService",
        return_value=service,
    ) as svc_cls:
        await CoroutinesManager._run_auto_adv_active_control(mgr, pool)  # type: ignore[arg-type]

    svc_cls.assert_called_once()
    ensure.assert_awaited_once_with(pool)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_auto_budget_watchdog_passes_unfiltered_advs_to_active_control() -> None:
    """B: watchdog finally вызывает active control с исходным advs list (не stale-filter)."""
    pool = [_active_adv(401), _active_adv(402)]
    mgr = _manager_stub()
    mgr.shop_id = "shop"
    mgr._wb_shop_data_manager = MagicMock()
    mgr._wb_shop_data_manager.get_complex_advs = AsyncMock(return_value=pool)
    mgr._auto_budget_service = MagicMock()
    control = AsyncMock()
    stale_filter = MagicMock()

    # while_coroutine_decorator wraps into an infinite loop — call __wrapped__ once.
    raw = CoroutinesManager.auto_budget_watchdog
    fn = getattr(raw, "__wrapped__", None)
    assert fn is not None, "auto_budget_watchdog must expose __wrapped__ one-shot body"

    with (
        patch.object(mgr, "_run_auto_adv_active_control", control),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.stale_stats_freeze.filter_ab_hold_stale_mutation_candidates",
            stale_filter,
        ),
    ):
        await fn(mgr, only_bot_active=True)

    control.assert_awaited_once_with(pool)
    stale_filter.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_auto_reset_bid_applies_stale_mutation_filter() -> None:
    """Contrast: keyword/bid reset path DOES gate through stale-mutation filter."""
    pool = [_active_adv(501), _active_adv(502)]
    mgr = _manager_stub()
    mgr._wb_shop_data_manager = MagicMock()
    mgr._wb_shop_data_manager.get_complex_advs = AsyncMock(return_value=pool)
    mgr._split_advs_by_stats_freshness = AsyncMock(return_value=([pool[0]], [pool[1]]))
    ensure_bids = AsyncMock()
    filter_mock = MagicMock(return_value=[pool[0]])

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.stale_stats_freeze.filter_ab_hold_stale_mutation_candidates",
            filter_mock,
        ),
        patch(
            "app.modules.shop_runner.service_manager.manager.AutoResetBidService",
            return_value=MagicMock(ensure_auto_bids_minimum=ensure_bids),
        ),
    ):
        raw = CoroutinesManager.auto_reset_bid_for_auto_adv
        fn = getattr(raw, "__wrapped__", None)
        assert fn is not None
        await fn(mgr, only_bot_active=True)

    filter_mock.assert_called_once()
    assert filter_mock.call_args.args[0] == pool
    assert filter_mock.call_args.args[1] == {501}
    ensure_bids.assert_awaited_once_with([pool[0]])
