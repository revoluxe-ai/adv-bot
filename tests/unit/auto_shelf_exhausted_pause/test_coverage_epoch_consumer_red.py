"""RED regression: coverage window MUST clamp date_from to shelf_exhausted_epoch_start.

Bug ROOT-001 / BUGCASE-ASEP-EPOCH: ``shelf_exhausted_epoch_start`` is written after
real Auto start, but ``AutoShelfBidControlViewProvider`` passes
``get_first_available_bid_bucket_start`` straight into ``get_bid_coverages`` with
no epoch consume. Helper ``coverage_date_from_for_epoch`` is orphan (not enough
for RED).

Invariant: after epoch_start, coverage ``date_from`` MUST be
``max(window_start, epoch_start)`` (equivalently ≥ epoch when epoch is inside
the ≤7d window) so pre-epoch CH history alone cannot close bids for the new
epoch.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.common_slaves.wildberries.models.enums.auto_shelf_bid_control_strategy import (
    AutoShelfBidControlStrategy,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider import (
    AutoShelfBidControlViewProvider,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.bid_coverage_selector import (
    BidCoverage,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.exhausted_pause.decision import (
    coverage_date_from_for_epoch,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto.bid_stats_dto import (
    BidStatsDTO,
)

pytestmark = pytest.mark.unit


def _cycle_bid_stats() -> list[BidStatsDTO]:
    """Minimal qualified cycle stats so view_provider coverage branch runs."""
    return [
        BidStatsDTO(
            bid_minor=20_500,
            currency="RUB",
            mode=None,
            last_interval_at=None,
            impressions=500,
            clicks=20,
            carts=2,
            orders=1,
            spend=100.0,
            cart_cpa=5.0,
            ctr=0.04,
            cart_cr=0.1,
        ),
        BidStatsDTO(
            bid_minor=37_500,
            currency="RUB",
            mode=None,
            last_interval_at=None,
            impressions=500,
            clicks=15,
            carts=1,
            orders=0,
            spend=90.0,
            cart_cpa=6.0,
            ctr=0.03,
            cart_cr=0.05,
        ),
    ]


@pytest.mark.asyncio
async def test_view_provider_get_bid_coverages_date_from_clamps_to_epoch_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production consumer: get_bid_coverages date_from must honor epoch_start.

    Fails on unrepaired production because view_provider wires
    date_from=first_available_bucket with no shelf_exhausted_epoch_start read.
    """
    now = datetime.now(UTC)
    # Epoch opened by real Auto start — inside the 7d stats window.
    epoch_start = now - timedelta(days=1)
    # CH has pre-epoch buckets; unclamped path would let that history close
    # new-epoch bids.
    first_bucket_pre_epoch = now - timedelta(days=6)

    # Sanity: helper clamp is epoch when epoch is newer than now-7d.
    assert (
        coverage_date_from_for_epoch(now=now, epoch_start=epoch_start) == epoch_start
    )
    assert first_bucket_pre_epoch < epoch_start

    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = 12345
    adv.auto_shelf_bid_control_enabled = True
    adv.auto_shelf_bid_control_strategy = AutoShelfBidControlStrategy.PLAN_DISTANCE
    adv.plan_for_sales_for_day = None
    adv.target_price_for_order = None
    adv.max_price_for_order = None

    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 2000
    settings_obj.target_test_observation_minutes = 60
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 60_000
    settings_obj.min_bid_distance_minor = 100

    state = MagicMock(
        current_mode="main",
        current_main_bid_minor=20_500,
        current_test_bid_minor=60_000,
        current_cycle_started_at=now - timedelta(hours=2),
        previous_cycle_started_at=now - timedelta(hours=10),
        main_started_at=None,
        test_started_at=now - timedelta(hours=2),
        last_reason="test_waiting_observation_time",
        shelf_exhausted_epoch_start=epoch_start,
        shelf_exhausted_epoch_pending=False,
    )

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=state)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)
    repository.update_settings = AsyncMock(return_value=settings_obj)
    repository.save_state = AsyncMock(side_effect=lambda saved_state: saved_state)

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=_cycle_bid_stats())
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)
    analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)
    analytics.get_impressions = AsyncMock(return_value=0)
    analytics.get_first_available_bid_bucket_start = AsyncMock(
        return_value=first_bucket_pre_epoch
    )
    # Pre-epoch-only coverages: if date_from is not clamped, selector can treat
    # the new epoch as already covered by history before epoch_start.
    analytics.get_bid_coverages = AsyncMock(
        return_value=[
            BidCoverage(bid_minor=20_500, impressions=184_393, valid_hours=184),
            BidCoverage(bid_minor=37_500, impressions=184_393, valid_hours=184),
        ]
    )
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(return_value={})

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(  # type: ignore[attr-defined]
        return_value=MagicMock(bid_minor=20_500)
    )
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=12_000)  # type: ignore[method-assign]
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager."
        "auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: MagicMock(get_latest_plan_fact=AsyncMock(return_value=None)),
    )

    await provider.build_view(adv_setting_original_id=1)

    analytics.get_first_available_bid_bucket_start.assert_awaited()
    analytics.get_bid_coverages.assert_awaited()
    call_kwargs = analytics.get_bid_coverages.await_args.kwargs
    date_to = call_kwargs["date_to"]
    assert isinstance(date_to, datetime)
    window_clamped = coverage_date_from_for_epoch(
        now=date_to,
        epoch_start=epoch_start,
    )
    # Consumer must not use bare first_bucket when epoch_start is later.
    expected_date_from = max(first_bucket_pre_epoch, window_clamped)
    assert expected_date_from == epoch_start
    assert call_kwargs["date_from"] == expected_date_from, (
        "coverage get_bid_coverages date_from must clamp to shelf_exhausted_epoch_start; "
        f"got {call_kwargs['date_from']!r}, first_bucket={first_bucket_pre_epoch!r}, "
        f"epoch_start={epoch_start!r}"
    )
    assert call_kwargs["date_from"] != first_bucket_pre_epoch
    assert call_kwargs["nmid"] == 111
    assert call_kwargs["currency"] == "RUB"
    assert call_kwargs["price_minor"] is None
    assert call_kwargs["mode"] is None
