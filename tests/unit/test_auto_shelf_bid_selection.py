"""Unit-тесты выбора лучшей ставки между циклами (score=CPC или CTR)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager import (
    AutoShelfBidControlManager,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.bid_selection import (
    pick_better_bid_by_cart_cpa,
    pick_better_bid_by_ctr,
    resolve_cycle_best_bids,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto import (
    OptimizationMetric,
    resolve_optimization_metric,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.bid_units import (
    cpc_from_totals,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto import (
    BidStatsDTO,
)

pytestmark = pytest.mark.unit


def _stats(*, bid_minor: int, cpc: float) -> BidStatsDTO:
    return BidStatsDTO(
        bid_minor=bid_minor,
        currency="RUB",
        mode=None,
        last_interval_at=None,
        impressions=1000,
        clicks=10,
        carts=5,
        orders=0,
        spend=100.0,
        cart_cpa=cpc,
        ctr=0.01,
        cart_cr=0.5,
    )


def test_pick_better_bid_by_cart_cpa_prefers_lower_cpc() -> None:
    current = _stats(bid_minor=35_000, cpc=50.0)
    previous = _stats(bid_minor=20_000, cpc=30.0)
    picked = pick_better_bid_by_cart_cpa(current, previous)
    assert picked is not None
    assert picked.bid_minor == 20_000


def test_pick_better_bid_by_cart_cpa_prefers_lower_cpc_when_one_has_display_only_score() -> None:
    """SQL не отдаёт clicks=0 в best; сравнение в Python — по cart_cpa (CPC score)."""
    low_signal = _stats(bid_minor=36_000, cpc=cpc_from_totals(421.23, 0))
    stable = _stats(bid_minor=20_000, cpc=cpc_from_totals(200.0, 10))
    picked = pick_better_bid_by_cart_cpa(low_signal, stable)
    assert picked is not None
    assert picked.bid_minor == 20_000


@pytest.mark.asyncio
async def test_resolve_cycle_best_bids_uses_previous_window() -> None:
    analytics = MagicMock()
    cycle_started = datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc)
    prev_started = datetime(2026, 5, 24, 12, 0, tzinfo=timezone.utc)
    analytics.get_best_bid_by_cart_cpa = AsyncMock(
        side_effect=[
            _stats(bid_minor=35_000, cpc=40.0),
            _stats(bid_minor=20_000, cpc=25.0),
        ]
    )
    cycle_best, prev_best, global_best = await resolve_cycle_best_bids(
        analytics,
        nmid=1,
        currency="RUB",
        current_cycle_started_at=cycle_started,
        previous_cycle_started_at=prev_started,
    )
    assert cycle_best is not None and cycle_best.bid_minor == 35_000
    assert prev_best is not None and prev_best.bid_minor == 20_000
    assert global_best is not None and global_best.bid_minor == 20_000
    analytics.get_best_bid_by_cart_cpa.assert_any_call(
        nmid=1,
        from_ts=prev_started,
        to_ts=cycle_started,
        currency="RUB",
    )


@pytest.mark.asyncio
async def test_choose_best_bid_prefers_global_over_current_cycle_only() -> None:
    cycle_started = datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc)
    prev_started = datetime(2026, 5, 24, 12, 0, tzinfo=timezone.utc)
    analytics = MagicMock()
    analytics.get_best_bid_by_cart_cpa = AsyncMock(
        side_effect=[
            _stats(bid_minor=35_000, cpc=40.0),
            _stats(bid_minor=20_000, cpc=25.0),
            None,
        ]
    )
    manager = AutoShelfBidControlManager(
        bid_cache_manager=MagicMock(),
        wb_bid_setter=MagicMock(),
        analytics_repository=analytics,
    )
    result = await manager._choose_best_bid_with_fallback(
        nmid=1,
        currency="RUB",
        cycle_started_at=cycle_started,
        previous_cycle_started_at=prev_started,
        current_main_bid_minor=35_000,
        actual_bid_minor=35_000,
        min_bid_minor=12_000,
        max_bid_minor=60_000,
    )
    assert result == 20_000


def test_pick_better_bid_prefers_current_cycle_lower_cpc_over_previous() -> None:
    """Текущий цикл: 200₽ CPC 5.69; прошлый: 360₽ CPC 17 — global = 200."""
    current = _stats(bid_minor=20_000, cpc=5.69)
    previous = _stats(bid_minor=36_000, cpc=17.39)
    picked = pick_better_bid_by_cart_cpa(current, previous)
    assert picked is not None
    assert picked.bid_minor == 20_000


def _stats_with_ctr(*, bid_minor: int, cpc: float, ctr: float) -> BidStatsDTO:
    """Создать BidStatsDTO с указанным CTR для тестов сортировки."""
    return BidStatsDTO(
        bid_minor=bid_minor,
        currency="RUB",
        mode=None,
        last_interval_at=None,
        impressions=1000,
        clicks=10,
        carts=5,
        orders=0,
        spend=100.0,
        cart_cpa=cpc,
        ctr=ctr,
        cart_cr=0.5,
    )


def test_pick_better_bid_by_ctr_prefers_higher_ctr() -> None:
    """CTR mode: выбираем ставку с большим CTR."""
    high_ctr = _stats_with_ctr(bid_minor=20_000, cpc=50.0, ctr=0.05)
    low_ctr = _stats_with_ctr(bid_minor=35_000, cpc=30.0, ctr=0.02)
    picked = pick_better_bid_by_ctr(high_ctr, low_ctr)
    assert picked is not None
    assert picked.bid_minor == 20_000


def test_pick_better_bid_by_ctr_tie_prefers_lower_bid() -> None:
    """При равном CTR выбираем меньшую ставку."""
    left = _stats_with_ctr(bid_minor=20_000, cpc=50.0, ctr=0.05)
    right = _stats_with_ctr(bid_minor=25_000, cpc=30.0, ctr=0.05)
    picked = pick_better_bid_by_ctr(left, right)
    assert picked is not None
    assert picked.bid_minor == 20_000


def test_pick_better_bid_by_ctr_none_handling() -> None:
    """None CTR считается минимально возможным (-inf)."""
    no_ctr = _stats_with_ctr(bid_minor=20_000, cpc=50.0, ctr=0.0)
    has_ctr = _stats_with_ctr(bid_minor=35_000, cpc=30.0, ctr=0.02)
    picked = pick_better_bid_by_ctr(no_ctr, has_ctr)
    assert picked is not None
    assert picked.bid_minor == 35_000


def test_resolve_optimization_metric_ctr_when_fact_lt_resolve() -> None:
    """Когда fact CPO < resolve CPO → оптимизация по CTR."""
    metric = resolve_optimization_metric(fact_cpo=100.0, resolve_cpo=150.0)
    assert metric == OptimizationMetric.CTR


def test_resolve_optimization_metric_cpc_when_fact_gte_resolve() -> None:
    """Когда fact CPO >= resolve CPO → оптимизация по CPC."""
    metric = resolve_optimization_metric(fact_cpo=150.0, resolve_cpo=150.0)
    assert metric == OptimizationMetric.CPC

    metric = resolve_optimization_metric(fact_cpo=200.0, resolve_cpo=150.0)
    assert metric == OptimizationMetric.CPC


def test_resolve_optimization_metric_cpc_when_missing_cpo() -> None:
    """При отсутствии CPO данных → оптимизация по CPC (default)."""
    metric = resolve_optimization_metric(fact_cpo=None, resolve_cpo=150.0)
    assert metric == OptimizationMetric.CPC

    metric = resolve_optimization_metric(fact_cpo=100.0, resolve_cpo=None)
    assert metric == OptimizationMetric.CPC

    metric = resolve_optimization_metric(fact_cpo=None, resolve_cpo=None)
    assert metric == OptimizationMetric.CPC


@pytest.mark.asyncio
async def test_resolve_cycle_best_bids_uses_ctr_when_metric_is_ctr() -> None:
    """При метрике CTR используем get_best_bid_by_ctr."""
    analytics = MagicMock()
    cycle_started = datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc)
    analytics.get_best_bid_by_ctr = AsyncMock(
        return_value=_stats_with_ctr(bid_minor=25_000, cpc=40.0, ctr=0.03)
    )
    cycle_best, prev_best, global_best = await resolve_cycle_best_bids(
        analytics,
        nmid=1,
        currency="RUB",
        current_cycle_started_at=cycle_started,
        previous_cycle_started_at=None,
        fact_cpo=100.0,
        resolve_cpo=150.0,
    )
    assert cycle_best is not None and cycle_best.bid_minor == 25_000
    analytics.get_best_bid_by_ctr.assert_called_once()


@pytest.mark.asyncio
async def test_resolve_cycle_best_bids_uses_cpc_when_metric_is_cpc() -> None:
    """При метрике CPC используем get_best_bid_by_cart_cpa."""
    analytics = MagicMock()
    cycle_started = datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc)
    analytics.get_best_bid_by_cart_cpa = AsyncMock(
        return_value=_stats(bid_minor=20_000, cpc=25.0)
    )
    cycle_best, prev_best, global_best = await resolve_cycle_best_bids(
        analytics,
        nmid=1,
        currency="RUB",
        current_cycle_started_at=cycle_started,
        previous_cycle_started_at=None,
        fact_cpo=200.0,
        resolve_cpo=150.0,
    )
    assert cycle_best is not None and cycle_best.bid_minor == 20_000
    analytics.get_best_bid_by_cart_cpa.assert_called_once()
