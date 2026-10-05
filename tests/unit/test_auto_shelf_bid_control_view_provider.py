"""Unit tests for the Auto Shelf Bid Control view provider."""

from __future__ import annotations

from datetime import datetime, UTC
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from app.modules.auto_budget_manager.redis_promo_state_manager import (
    CachedCampaignPromoState,
    CachedShopPromoState,
    RedisPromoStateManager,
)
from app.modules.plan_fact.provider import PlanFactProvider

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider import (
    AutoShelfBidControlViewProvider,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager import (
    AutoShelfBidControlManager,
)
from app.modules.common_slaves.wildberries.models.enums.auto_shelf_bid_control_strategy import (
    AutoShelfBidControlStrategy,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto import (
    OptimizationMetric,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.bid_coverage_selector import (
    BidCoverage,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.exhausted_pause.decision import (
    coverage_date_from_for_epoch,
)


pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _stub_leg_cpo_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unit provider tests не должны ходить в реальный ClickHouse."""
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services."
        "auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider."
        "load_leg_cpo_snapshot",
        AsyncMock(return_value=SimpleNamespace(auto_cpo=None)),
    )


def assert_cycle_state_valid(state: object) -> None:
    current_cycle_started_at = getattr(state, "current_cycle_started_at", None)
    test_started_at = getattr(state, "test_started_at", None)
    if current_cycle_started_at and test_started_at:
        assert current_cycle_started_at <= test_started_at


@pytest.mark.asyncio
async def test_build_view_returns_warning_when_adv_setting_not_found() -> None:
    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=None)
    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=MagicMock(),
    )

    view = await provider.build_view(adv_setting_original_id=999)

    assert view.has_settings is False
    assert view.has_state is False
    assert "adv_setting_not_found" in view.warnings


@pytest.mark.asyncio
async def test_build_view_auto_creates_default_settings_for_single_nmid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = 12345
    adv.auto_shelf_bid_control_enabled = False
    adv.plan_for_sales_for_day = None
    adv.target_price_for_order = None
    adv.max_price_for_order = None
    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 500
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 500
    settings_obj.min_bid_distance_minor = 1
    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=None)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)
    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=[])
    analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)
    analytics.get_impressions = AsyncMock(return_value=0)
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(return_value={})
    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=None)  # type: ignore[method-assign]

    # Mock PlanFactReader to avoid CH connection
    mock_plan_fact_reader = MagicMock()
    mock_plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: mock_plan_fact_reader,
    )

    view = await provider.build_view(adv_setting_original_id=1)

    repository.get_or_create_default_settings.assert_awaited_once_with(111)
    assert view.has_settings is True
    assert view.best_plan_bid_minor is None
    assert "settings_missing" not in view.warnings


@pytest.mark.asyncio
async def test_build_view_builds_coverage_layer_payload_without_actual_bid_price_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
        current_cycle_started_at=datetime(2026, 6, 10, 23, 27, 51, tzinfo=UTC),
        previous_cycle_started_at=datetime(2026, 6, 10, 13, 20, 53, tzinfo=UTC),
        main_started_at=None,
        test_started_at=datetime(2026, 6, 10, 23, 27, 51, tzinfo=UTC),
        last_reason="test_waiting_observation_time",
    )

    first_bucket_start = datetime(2026, 5, 24, 21, 15, tzinfo=UTC)

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=state)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)
    repository.update_settings = AsyncMock(return_value=settings_obj)
    repository.save_state = AsyncMock(return_value=state)
    repository.update_settings = AsyncMock(return_value=settings_obj)
    repository.save_state = AsyncMock(return_value=state)
    repository.save_state = AsyncMock(side_effect=lambda saved_state: saved_state)

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=_two_qualified_cycle_bid_stats())
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)
    analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)
    analytics.get_impressions = AsyncMock(return_value=0)
    analytics.get_first_available_bid_bucket_start = AsyncMock(
        return_value=first_bucket_start
    )
    analytics.get_bid_coverages = AsyncMock(
        return_value=[
            BidCoverage(bid_minor=20_500, impressions=184_393, valid_hours=184),
            BidCoverage(bid_minor=37_500, impressions=0, valid_hours=0),
        ]
    )
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(return_value={})
    analytics.fetch_rec_bid_click_to_order_cr_7d_for_nmid = AsyncMock(return_value=None)

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=MagicMock(bid_minor=20_500))  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=12_000)  # type: ignore[method-assign]
    selector_mock = MagicMock(return_value=37_500)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.bid_coverage_selector.choose_next_test_bid_by_coverage_layers",
        selector_mock,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.choose_next_test_bid_by_coverage_layers",
        selector_mock,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager.choose_next_test_bid_by_coverage_layers",
        selector_mock,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: MagicMock(get_latest_plan_fact=AsyncMock(return_value=None)),
    )

    view = await provider.build_view(adv_setting_original_id=1)

    assert view.coverage_first_available_bucket_start == first_bucket_start
    assert view.next_test_bid_minor == 37_500
    assert view.coverage_selected_next_test_bid_minor == 37_500
    assert view.legacy_cycle_next_test_bid_minor == 36_000
    assert view.coverage_current_layer == 0
    assert view.coverage_undercovered_count == 480
    assert len(view.coverage_bid_rows) == 481
    assert all(row.closed_layers == 0 for row in view.coverage_bid_rows if row.bid_minor in {37_500, 60_000, 12_000})
    missing_row = next(row for row in view.coverage_bid_rows if row.bid_minor == 12_100)
    assert missing_row.impressions == 0
    assert missing_row.valid_hours == 0
    assert missing_row.closed_layers == 0
    selected_row = next(row for row in view.coverage_bid_rows if row.bid_minor == 37_500)
    assert selected_row.is_selected_next_test is True
    analytics.get_first_available_bid_bucket_start.assert_any_await(
        nmid=111,
        currency="RUB",
        price_minor=None,
        mode=None,
    )
    assert analytics.get_first_available_bid_bucket_start.await_count == 2
    coverage_calls = [
        call.kwargs for call in analytics.get_bid_coverages.await_args_list
    ]
    assert len(coverage_calls) == 2
    for coverage_call in coverage_calls:
        expected_date_from = max(
            first_bucket_start,
            coverage_date_from_for_epoch(
                now=coverage_call["date_to"],
                epoch_start=None,
            ),
        )
        assert coverage_call == {
            "nmid": 111,
            "date_from": expected_date_from,
            "date_to": coverage_call["date_to"],
            "currency": "RUB",
            "price_minor": None,
            "mode": None,
        }
    assert selector_mock.call_count == 2


@pytest.mark.asyncio
async def test_build_view_handles_missing_coverage_as_zero_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = 12345
    adv.auto_shelf_bid_control_enabled = True
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

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=None)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=_two_qualified_cycle_bid_stats())
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)
    analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)
    analytics.get_impressions = AsyncMock(return_value=0)
    analytics.get_first_available_bid_bucket_start = AsyncMock(return_value=None)
    analytics.get_bid_coverages = AsyncMock(return_value=[])
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(return_value={})

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=MagicMock(bid_minor=20_500))  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=12_000)  # type: ignore[method-assign]
    selector_mock = MagicMock(return_value=33_900)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.choose_next_test_bid_by_coverage_layers",
        selector_mock,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: MagicMock(get_latest_plan_fact=AsyncMock(return_value=None)),
    )

    view = await provider.build_view(adv_setting_original_id=1)

    assert view.coverage_first_available_bucket_start is None
    assert view.coverage_current_layer == 0
    assert view.coverage_undercovered_count == 481
    assert view.coverage_selected_next_test_bid_minor == 33_900
    assert len(view.coverage_bid_rows) == 481
    assert any(row.bid_minor == 33_900 and row.is_selected_next_test for row in view.coverage_bid_rows)
    assert all(row.impressions == 0 for row in view.coverage_bid_rows)
    assert all(row.valid_hours == 0 for row in view.coverage_bid_rows)
    analytics.get_first_available_bid_bucket_start.assert_awaited_once_with(
        nmid=111,
        currency="RUB",
        price_minor=None,
        mode=None,
    )
    analytics.get_bid_coverages.assert_not_awaited()


@pytest.mark.asyncio
async def test_build_view_plan_distance_matches_manager_selected_next_bid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    settings_obj.max_bid_minor = 50_000
    settings_obj.min_bid_distance_minor = 100

    state = MagicMock(
        current_mode="main",
        current_main_bid_minor=20_500,
        current_test_bid_minor=60_000,
        current_cycle_started_at=datetime(2026, 6, 10, 23, 27, 51, tzinfo=UTC),
        previous_cycle_started_at=datetime(2026, 6, 10, 13, 20, 53, tzinfo=UTC),
        main_started_at=None,
        test_started_at=datetime(2026, 6, 10, 23, 27, 51, tzinfo=UTC),
        last_reason="test_waiting_observation_time",
    )

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=state)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)
    repository.save_state = AsyncMock(side_effect=lambda saved_state: saved_state)

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=_two_qualified_cycle_bid_stats())
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)
    analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)
    analytics.get_impressions = AsyncMock(return_value=0)
    analytics.get_first_available_bid_bucket_start = AsyncMock(
        return_value=datetime(2026, 5, 24, 21, 15, tzinfo=UTC)
    )
    analytics.get_bid_coverages = AsyncMock(
        return_value=[
            BidCoverage(bid_minor=20_500, impressions=184_393, valid_hours=184),
            BidCoverage(bid_minor=37_500, impressions=0, valid_hours=0),
        ]
    )

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=MagicMock(bid_minor=20_500))  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=12_000)  # type: ignore[method-assign]
    selector_mock = MagicMock(return_value=33_000)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.choose_next_test_bid_by_coverage_layers",
        selector_mock,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: MagicMock(get_latest_plan_fact=AsyncMock(return_value=None)),
    )

    view = await provider.build_view(adv_setting_original_id=1)

    assert view.next_test_bid_minor == 33_000
    assert view.coverage_selected_next_test_bid_minor == 33_000
    assert view.legacy_cycle_next_test_bid_minor == 31_000
    selector_mock.assert_called_once()


@pytest.mark.asyncio
async def test_build_view_sorts_coverage_rows_by_plan_ranked_then_selected_then_important(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    settings_obj.max_bid_minor = 12_300
    settings_obj.min_bid_distance_minor = 100

    state = MagicMock(
        current_mode="main",
        current_main_bid_minor=12_000,
        current_test_bid_minor=12_100,
        current_cycle_started_at=datetime(2026, 6, 10, 23, 27, 51, tzinfo=UTC),
        previous_cycle_started_at=datetime(2026, 6, 10, 13, 20, 53, tzinfo=UTC),
        main_started_at=None,
        test_started_at=datetime(2026, 6, 10, 23, 27, 51, tzinfo=UTC),
        last_reason="test_waiting_observation_time",
    )

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=state)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)
    repository.save_state = AsyncMock(side_effect=lambda saved_state: saved_state)

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=_two_qualified_cycle_bid_stats())
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)
    analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)
    analytics.get_impressions = AsyncMock(return_value=0)
    analytics.get_first_available_bid_bucket_start = AsyncMock(
        return_value=datetime(2026, 5, 24, 21, 15, tzinfo=UTC)
    )
    analytics.get_bid_coverages = AsyncMock(
        return_value=[BidCoverage(bid_minor=12_000, impressions=2_000, valid_hours=1)]
    )
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(return_value={111: 0.1})
    analytics.fetch_rec_bid_click_to_order_cr_7d_for_nmid = AsyncMock(return_value=0.05)

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=MagicMock(bid_minor=12_000))  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=12_000)  # type: ignore[method-assign]
    provider._rec_bid_recommendation_service.get_rec_bid_recommendations = AsyncMock(  # type: ignore[attr-defined]
        return_value={
            "view": {
                "best_plan_bid": 12_300,
                "plan_ranked": [
                    {
                        "bid": 12_300,
                        "expected_daily_impressions": 1_000.0,
                        "expected_daily_clicks": 100.0,
                        "expected_daily_orders": 10.0,
                        "cpo_rub": 99.0,
                        "plan_distance_score": 0.1,
                    },
                    {
                        "bid": 12_200,
                        "expected_daily_impressions": 800.0,
                        "expected_daily_clicks": 80.0,
                        "expected_daily_orders": 8.0,
                        "cpo_rub": 120.0,
                        "plan_distance_score": 0.2,
                    },
                ],
            }
        }
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.choose_next_test_bid_by_coverage_layers",
        MagicMock(return_value=12_100),
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: MagicMock(get_latest_plan_fact=AsyncMock(return_value=None)),
    )

    view = await provider.build_view(adv_setting_original_id=1)

    assert len(view.coverage_bid_rows) == 4
    assert [row.bid_minor for row in view.coverage_bid_rows] == [12_300, 12_200, 12_100, 12_000]
    assert view.coverage_bid_rows[0].is_best_plan is True
    assert view.coverage_bid_rows[2].is_selected_next_test is True
    assert view.coverage_bid_rows[3].is_current_main is True
    assert view.coverage_bid_rows[0].expected_daily_impressions == 1_000.0
    assert view.coverage_bid_rows[0].expected_daily_clicks == 100.0
    assert view.coverage_bid_rows[0].expected_daily_orders == 10.0
    assert view.coverage_bid_rows[0].expected_order_cost_rub == 99.0
    assert view.coverage_bid_rows[0].plan_distance_score == 0.1


@pytest.mark.asyncio
async def test_build_view_handles_nullable_target_test_observation_minutes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = 12345
    adv.auto_shelf_bid_control_enabled = True
    adv.plan_for_sales_for_day = 10
    adv.target_price_for_order = 100
    adv.max_price_for_order = 200

    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 500
    settings_obj.target_test_observation_minutes = None
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 500
    settings_obj.min_bid_distance_minor = 1

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=None)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=[])
    analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)
    analytics.get_impressions = AsyncMock(return_value=0)

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=None)  # type: ignore[method-assign]

    mock_plan_fact_reader = MagicMock()
    mock_plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: mock_plan_fact_reader,
    )

    view = await provider.build_view(adv_setting_original_id=1)

    assert view.target_test_observation_minutes == 60
    assert view.target_main_observation_minutes == 540


@pytest.mark.asyncio
async def test_build_view_contains_gate_dry_run_and_missing_state_warnings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = 12345
    adv.auto_shelf_bid_control_enabled = True
    adv.plan_for_sales_for_day = None
    adv.target_price_for_order = None
    adv.max_price_for_order = None
    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 500
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 500
    settings_obj.min_bid_distance_minor = 1
    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=None)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)
    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=[])
    analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)
    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=None)  # type: ignore[method-assign]
    provider._app_dry_run = lambda: True  # type: ignore[method-assign]
    monkeypatch.setenv("AUTO_SHELF_BID_CONTROL_BID_UNITS_CONFIRMED", "false")

    # Mock PlanFactReader to avoid CH connection
    mock_plan_fact_reader = MagicMock()
    mock_plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: mock_plan_fact_reader,
    )

    view = await provider.build_view(adv_setting_original_id=1)

    assert "state_missing" in view.warnings
    assert "dry_run_enabled" in view.warnings
    assert "bid_units_gate_not_confirmed" in view.warnings
    assert view.dry_run is True


@pytest.mark.asyncio
async def test_build_view_uses_wb_min_bid_not_actual_bid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """min_bid_minor — минимум WB из кэша, не текущая ставка и не CH."""
    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = 12345
    adv.auto_shelf_bid_control_enabled = True
    adv.plan_for_sales_for_day = None
    adv.target_price_for_order = None
    adv.max_price_for_order = None
    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 500
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 50_000
    settings_obj.min_bid_distance_minor = 100
    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=None)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)
    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=_two_qualified_cycle_bid_stats())
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)
    analytics.get_impressions = AsyncMock(return_value=0)
    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    bid_cache_value = MagicMock()
    bid_cache_value.bid_minor = 20_000
    provider._bid_cache.get_bid = AsyncMock(return_value=bid_cache_value)  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=15_000)  # type: ignore[method-assign]

    # Mock PlanFactReader to avoid CH connection
    mock_plan_fact_reader = MagicMock()
    mock_plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: mock_plan_fact_reader,
    )

    view = await provider.build_view(adv_setting_original_id=1)

    assert view.actual_bid_minor == 20_000
    assert view.min_bid_minor == 15_000
    assert "range_floor_from_actual_bid" not in view.warnings


@pytest.mark.asyncio
async def test_build_view_repairs_corrupted_cycle_before_fetching_cycle_stats(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = 12345
    adv.auto_shelf_bid_control_enabled = True
    adv.plan_for_sales_for_day = None
    adv.target_price_for_order = None
    adv.max_price_for_order = None

    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 500
    settings_obj.target_test_observation_minutes = 60
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 500
    settings_obj.min_bid_distance_minor = 1

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(
        return_value=MagicMock(
            current_cycle_started_at=datetime(2026, 6, 9, 6, 26, 23, tzinfo=UTC),
            previous_cycle_started_at=datetime(2026, 5, 26, 3, 29, 0, tzinfo=UTC),
            test_started_at=datetime(2026, 6, 8, 15, 56, 56, tzinfo=UTC),
            current_test_bid_minor=45_000,
            current_main_bid_minor=24_000,
            current_mode="main",
            main_started_at=datetime(2026, 6, 9, 6, 26, 23, tzinfo=UTC),
            last_reason=None,
        )
    )
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)
    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=[])
    analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)
    analytics.get_impressions = AsyncMock(return_value=0)
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(return_value={111: 0.1})
    analytics.fetch_rec_bid_click_to_order_cr_7d_for_nmid = AsyncMock(
        return_value=0.05
    )

    repository.save_state = AsyncMock(side_effect=lambda saved_state: saved_state)

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=None)  # type: ignore[method-assign]

    mock_plan_fact_reader = MagicMock()
    mock_plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: mock_plan_fact_reader,
    )
    provider._rec_bid_recommendation_service.get_rec_bid_recommendations = AsyncMock(
        return_value={"view": {"best_expected_bid": 111}}
    )  # type: ignore[attr-defined]

    await provider.build_view(adv_setting_original_id=1)

    repository.save_state.assert_awaited_once()
    analytics.get_bid_stats.assert_any_await(
        nmid=111,
        from_ts=datetime(2026, 5, 26, 3, 29, 0, tzinfo=UTC),
        currency="RUB",
    )
    assert_cycle_state_valid(repository.save_state.await_args.args[0])


@pytest.mark.asyncio
async def test_build_view_repaired_cycle_state_is_not_saved_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = 12345
    adv.auto_shelf_bid_control_enabled = True
    adv.plan_for_sales_for_day = None
    adv.target_price_for_order = None
    adv.max_price_for_order = None

    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 500
    settings_obj.target_test_observation_minutes = 60
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 500
    settings_obj.min_bid_distance_minor = 1

    repaired_state = MagicMock(
        current_cycle_started_at=datetime(2026, 6, 9, 6, 26, 23, tzinfo=UTC),
        previous_cycle_started_at=datetime(2026, 5, 26, 3, 29, 0, tzinfo=UTC),
        test_started_at=datetime(2026, 6, 8, 15, 56, 56, tzinfo=UTC),
        current_test_bid_minor=45_000,
        current_main_bid_minor=24_000,
        current_mode="main",
        main_started_at=datetime(2026, 6, 9, 6, 26, 23, tzinfo=UTC),
        last_reason=None,
    )

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=repaired_state)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)
    repository.save_state = AsyncMock(side_effect=lambda saved_state: saved_state)

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=[])
    analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)
    analytics.get_impressions = AsyncMock(return_value=0)
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(return_value={111: 0.1})
    analytics.fetch_rec_bid_click_to_order_cr_7d_for_nmid = AsyncMock(
        return_value=0.05
    )

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=None)  # type: ignore[method-assign]
    provider._rec_bid_recommendation_service.get_rec_bid_recommendations = AsyncMock(
        return_value={"view": {"best_expected_bid": 111}}
    )  # type: ignore[attr-defined]

    mock_plan_fact_reader = MagicMock()
    mock_plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: mock_plan_fact_reader,
    )

    await provider.build_view(adv_setting_original_id=1)
    await provider.build_view(adv_setting_original_id=1)

    assert repository.save_state.await_count == 1
    assert repaired_state.current_cycle_started_at == datetime(
        2026, 5, 26, 3, 29, 0, tzinfo=UTC
    )
    assert_cycle_state_valid(repaired_state)


@pytest.mark.asyncio
async def test_build_view_repairs_then_stays_idempotent_with_fresh_state_copy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = 12345
    adv.auto_shelf_bid_control_enabled = True
    adv.plan_for_sales_for_day = None
    adv.target_price_for_order = None
    adv.max_price_for_order = None

    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 500
    settings_obj.target_test_observation_minutes = 60
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 500
    settings_obj.min_bid_distance_minor = 1

    corrupted_state = MagicMock(
        current_cycle_started_at=datetime(2026, 6, 9, 6, 26, 23, tzinfo=UTC),
        previous_cycle_started_at=datetime(2026, 5, 26, 3, 29, 0, tzinfo=UTC),
        test_started_at=datetime(2026, 6, 8, 15, 56, 56, tzinfo=UTC),
        current_test_bid_minor=45_000,
        current_main_bid_minor=24_000,
        current_mode="main",
        main_started_at=datetime(2026, 6, 9, 6, 26, 23, tzinfo=UTC),
        last_reason=None,
    )
    repaired_state_copy = MagicMock(
        current_cycle_started_at=datetime(2026, 5, 26, 3, 29, 0, tzinfo=UTC),
        previous_cycle_started_at=datetime(2026, 5, 26, 3, 29, 0, tzinfo=UTC),
        test_started_at=datetime(2026, 6, 8, 15, 56, 56, tzinfo=UTC),
        current_test_bid_minor=45_000,
        current_main_bid_minor=24_000,
        current_mode="main",
        main_started_at=datetime(2026, 6, 9, 6, 26, 23, tzinfo=UTC),
        last_reason=None,
    )

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(side_effect=[corrupted_state, repaired_state_copy])
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)
    repository.save_state = AsyncMock(side_effect=lambda saved_state: saved_state)

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=[])
    analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)
    analytics.get_impressions = AsyncMock(return_value=0)
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(return_value={111: 0.1})
    analytics.fetch_rec_bid_click_to_order_cr_7d_for_nmid = AsyncMock(
        return_value=0.05
    )

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=None)  # type: ignore[method-assign]

    mock_plan_fact_reader = MagicMock()
    mock_plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: mock_plan_fact_reader,
    )
    provider._rec_bid_recommendation_service.get_rec_bid_recommendations = AsyncMock(
        return_value={"view": {"best_expected_bid": 111}}
    )  # type: ignore[attr-defined]

    await provider.build_view(adv_setting_original_id=1)
    await provider.build_view(adv_setting_original_id=1)

    assert repository.save_state.await_count == 1
    assert any(
        call.kwargs["from_ts"] == datetime(2026, 5, 26, 3, 29, 0, tzinfo=UTC)
        for call in analytics.get_bid_stats.await_args_list
    )
    assert repaired_state_copy.current_cycle_started_at == datetime(
        2026, 5, 26, 3, 29, 0, tzinfo=UTC
    )
    assert_cycle_state_valid(repaired_state_copy)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("strategy", "expected_metric", "expected_method", "unexpected_method"),
    [
        (
            AutoShelfBidControlStrategy.CTR,
            OptimizationMetric.CTR,
            "get_best_bid_by_ctr",
            "get_best_bid_by_cart_cpa",
        ),
        (
            AutoShelfBidControlStrategy.CPC,
            OptimizationMetric.CPC,
            "get_best_bid_by_cart_cpa",
            "get_best_bid_by_ctr",
        ),
    ],
)
async def test_build_view_uses_best_bid_method_for_optimization_metric(
    monkeypatch: pytest.MonkeyPatch,
    strategy: AutoShelfBidControlStrategy,
    expected_metric: OptimizationMetric,
    expected_method: str,
    unexpected_method: str,
) -> None:
    """Select the report-day best bid with the active optimization metric."""
    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = 12345
    adv.auto_shelf_bid_control_enabled = False
    adv.auto_shelf_bid_control_strategy = strategy
    adv.plan_for_sales_for_day = None
    adv.target_price_for_order = None
    adv.max_price_for_order = None

    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 500
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 500
    settings_obj.min_bid_distance_minor = 1

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=None)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=[])
    analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=None)  # type: ignore[method-assign]

    mock_plan_fact_reader = MagicMock()
    mock_plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: mock_plan_fact_reader,
    )

    view = await provider.build_view(adv_setting_original_id=1)

    getattr(analytics, expected_method).assert_awaited_once()
    getattr(analytics, unexpected_method).assert_not_awaited()
    assert view.optimization_metric == expected_metric


@pytest.mark.asyncio
async def test_build_view_cycle_metric_maps_to_cpc_for_backward_compatibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = 12345
    adv.auto_shelf_bid_control_enabled = False
    adv.auto_shelf_bid_control_strategy = AutoShelfBidControlStrategy.CYCLE_METRIC
    adv.plan_for_sales_for_day = None
    adv.target_price_for_order = None
    adv.max_price_for_order = None

    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 500
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 500
    settings_obj.min_bid_distance_minor = 1

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=None)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=[])
    analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=None)  # type: ignore[method-assign]

    mock_plan_fact_reader = MagicMock()
    mock_plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: mock_plan_fact_reader,
    )

    view = await provider.build_view(adv_setting_original_id=1)

    analytics.get_best_bid_by_ctr.assert_not_awaited()
    analytics.get_best_bid_by_cart_cpa.assert_awaited_once()
    assert view.optimization_metric == OptimizationMetric.CPC


@pytest.mark.asyncio
async def test_build_view_normalizes_legacy_cycle_metric_before_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = 12345
    adv.auto_shelf_bid_control_enabled = True
    adv.auto_shelf_bid_control_strategy = AutoShelfBidControlStrategy.CYCLE_METRIC
    adv.bot_active = True
    adv.auto_adv_active_status = True
    adv.plan_for_sales_for_day = 10
    adv.target_price_for_order = 100
    adv.max_price_for_order = 200

    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 500
    settings_obj.target_test_observation_minutes = 60
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 500
    settings_obj.min_bid_distance_minor = 1

    state = MagicMock()
    state.current_mode = "main"
    state.currency = "RUB"
    state.current_cycle_started_at = datetime(2026, 5, 25, tzinfo=UTC)
    state.previous_cycle_started_at = None
    state.current_main_bid_minor = 20_000
    state.current_test_bid_minor = 10_000

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=state)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)
    repository.update_settings = AsyncMock(return_value=settings_obj)
    repository.save_state = AsyncMock(return_value=state)

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=[])
    analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(return_value={111: 0.1})
    analytics.fetch_rec_bid_click_to_order_cr_7d_for_nmid = AsyncMock(return_value=0.05)
    analytics.get_impressions = AsyncMock(return_value=0)

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=10_000)  # type: ignore[method-assign]
    provider._rec_bid_recommendation_service.get_rec_bid_recommendations = AsyncMock(
        return_value={"view": {"plan_ranked": []}}
    )  # type: ignore[attr-defined]

    mock_plan_fact_reader = MagicMock()
    mock_plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: mock_plan_fact_reader,
    )

    from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto.decision_snapshot_dto import (
        AutoShelfBidControlDecisionSnapshot,
        BidSyncStatus,
    )

    async def _build_snapshot(self: object, complex_adv: object, **_: object) -> AutoShelfBidControlDecisionSnapshot:
        assert (
            getattr(complex_adv, "auto_shelf_bid_control_strategy")
            == AutoShelfBidControlStrategy.CPC
        )
        return AutoShelfBidControlDecisionSnapshot(
            nmid=111,
            auto_adv_id=12345,
            current_mode="main",
            actual_bid_minor=None,
            min_bid_minor=10_000,
            max_bid_minor=50_000,
            fresh_best_main_bid_minor=None,
            fresh_next_test_bid_minor=None,
            expected_bid_minor=None,
            bid_sync_status=BidSyncStatus.SYNCED,
            can_count_progress=False,
        )

    monkeypatch.setattr(
        AutoShelfBidControlManager,
        "build_decision_snapshot",
        _build_snapshot,
    )

    view = await provider.build_view(adv_setting_original_id=1)

    assert view.auto_shelf_bid_control_strategy == AutoShelfBidControlStrategy.CPC


@pytest.mark.asyncio
async def test_build_view_uses_fact_predict_orders_for_optimization_metric(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use predicted orders to select resolve CPO and the UI metric."""
    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = 12345
    adv.auto_shelf_bid_control_enabled = True
    adv.plan_for_sales_for_day = 10
    adv.target_price_for_order = 100
    adv.max_price_for_order = 200

    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 500
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 500
    settings_obj.min_bid_distance_minor = 1

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=None)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=[])
    analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=None)  # type: ignore[method-assign]

    plan_fact_summary = MagicMock()
    plan_fact_summary.fact_predict_orders = 10.0
    plan_fact_summary.fact_pay_for_order = 150.0

    mock_plan_fact_reader = MagicMock()
    mock_plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=plan_fact_summary)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: mock_plan_fact_reader,
    )

    view = await provider.build_view(adv_setting_original_id=1)

    assert view.resolve_cpo == 100.0
    assert view.optimization_metric == OptimizationMetric.CPC


@pytest.mark.asyncio
async def test_build_view_uses_auto_leg_cpo_not_aggregate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spec leg-cpo-economics: Auto Shelf view обязан показывать и использовать Auto CPO."""
    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = 12345
    adv.search_adv_id = 67890
    adv.auto_shelf_bid_control_enabled = True
    adv.auto_shelf_bid_control_strategy = None
    adv.plan_for_sales_for_day = 10
    adv.target_price_for_order = 100
    adv.max_price_for_order = 200

    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 500
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 500
    settings_obj.min_bid_distance_minor = 1

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=None)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=[])
    analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=None)  # type: ignore[method-assign]

    plan_fact_summary = MagicMock()
    plan_fact_summary.fact_predict_orders = 10.0
    plan_fact_summary.fact_pay_for_order = 999.0

    mock_plan_fact_reader = MagicMock()
    mock_plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=plan_fact_summary)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager."
        "auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: mock_plan_fact_reader,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager."
        "auto_shelf_bid_control_view_provider.load_leg_cpo_snapshot",
        AsyncMock(return_value=SimpleNamespace(auto_cpo=80.0)),
    )

    view = await provider.build_view(adv_setting_original_id=1)

    assert view.fact_cpo == pytest.approx(80.0)
    assert view.resolve_cpo == pytest.approx(100.0)
    assert view.optimization_metric == OptimizationMetric.CTR
    analytics.get_best_bid_by_ctr.assert_awaited_once()
    analytics.get_best_bid_by_cart_cpa.assert_not_awaited()


@pytest.mark.asyncio
async def test_build_view_keeps_resolve_cpo_none_when_resolver_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Old UI resolve_cpo must stay None if cost resolver cannot resolve it."""
    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = 12345
    adv.auto_shelf_bid_control_enabled = True
    adv.plan_for_sales_for_day = 10
    adv.target_price_for_order = 100
    adv.max_price_for_order = 200

    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 500
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 500
    settings_obj.min_bid_distance_minor = 1

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=None)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=[])
    analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=None)  # type: ignore[method-assign]

    plan_fact_summary = MagicMock()
    plan_fact_summary.fact_predict_orders = None
    plan_fact_summary.fact_pay_for_order = 150.0

    mock_plan_fact_reader = MagicMock()
    mock_plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=plan_fact_summary)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: mock_plan_fact_reader,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.resolve_target_cost",
        lambda *_args, **_kwargs: None,
    )

    view = await provider.build_view(adv_setting_original_id=1)

    assert view.resolve_cpo is None
    assert view.optimization_metric == OptimizationMetric.CPC


@pytest.mark.asyncio
async def test_build_view_includes_rec_bid_recommendation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DTO должен получать read-only rec bid recommendation из provider."""
    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = 12345
    adv.auto_shelf_bid_control_enabled = True
    adv.plan_for_sales_for_day = 10
    adv.target_price_for_order = 100
    adv.max_price_for_order = 200

    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 500
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 500
    settings_obj.min_bid_distance_minor = 1

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=None)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=[])
    analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(return_value={111: 0.1})
    analytics.fetch_rec_bid_click_to_order_cr_7d_for_nmid = AsyncMock(
        return_value=0.05
    )

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=None)  # type: ignore[method-assign]
    provider._rec_bid_recommendation_service.get_rec_bid_recommendations = AsyncMock(
        return_value={"view": {"best_expected_bid": 111}}
    )  # type: ignore[attr-defined]

    plan_fact_summary = MagicMock()
    plan_fact_summary.fact_predict_orders = 10.0
    plan_fact_summary.fact_pay_for_order = 150.0

    mock_plan_fact_reader = MagicMock()
    mock_plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=plan_fact_summary)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: mock_plan_fact_reader,
    )

    view = await provider.build_view(adv_setting_original_id=1)

    assert view.rec_bid_recommendation == {"best_expected_bid": 111}
    assert (
        provider._rec_bid_recommendation_service.get_rec_bid_recommendations.await_args.kwargs[
            "plan_context"
        ].target_order_cost
        == 100.0
    )
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid.assert_awaited_once_with(
        nmid=111,
        mode=None,
        date_from=ANY,
        date_to=ANY,
    )
    analytics.fetch_rec_bid_click_to_order_cr_7d_for_nmid.assert_awaited_once_with(
        nmid=111,
        mode=None,
        date_from=ANY,
        date_to=ANY,
    )


@pytest.mark.asyncio
async def test_build_view_preserves_zero_plan_ranked_cpo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = 12345
    adv.auto_shelf_bid_control_enabled = True
    adv.plan_for_sales_for_day = 10
    adv.target_price_for_order = 100
    adv.max_price_for_order = 200

    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 500
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 500
    settings_obj.min_bid_distance_minor = 1

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=None)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=[])
    analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(return_value={111: 0.1})
    analytics.fetch_rec_bid_click_to_order_cr_7d_for_nmid = AsyncMock(
        return_value=0.05
    )

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=None)  # type: ignore[method-assign]
    provider._rec_bid_recommendation_service.get_rec_bid_recommendations = AsyncMock(
        return_value={
            "view": {
                "plan_ranked": [
                    {"bid": 12300, "cpo_rub": 0.0, "expected_order_cost_rub": 259.23}
                ]
            }
        }
    )  # type: ignore[attr-defined]

    plan_fact_summary = MagicMock()
    plan_fact_summary.fact_predict_orders = 10.0
    plan_fact_summary.fact_pay_for_order = 150.0

    mock_plan_fact_reader = MagicMock()
    mock_plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=plan_fact_summary)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: mock_plan_fact_reader,
    )

    view = await provider.build_view(adv_setting_original_id=1)

    assert view.best_cpo_bid_rub == 0.0


@pytest.mark.asyncio
async def test_build_view_best_cpo_falls_back_when_cpo_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = 12345
    adv.auto_shelf_bid_control_enabled = True
    adv.plan_for_sales_for_day = 10
    adv.target_price_for_order = 100
    adv.max_price_for_order = 200

    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 500
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 500
    settings_obj.min_bid_distance_minor = 1

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=None)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=[])
    analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(return_value={111: 0.1})
    analytics.fetch_rec_bid_click_to_order_cr_7d_for_nmid = AsyncMock(
        return_value=0.05
    )

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=None)  # type: ignore[method-assign]
    provider._rec_bid_recommendation_service.get_rec_bid_recommendations = AsyncMock(
        return_value={
            "view": {
                "plan_ranked": [
                    {
                        "bid": 12300,
                        "cpo_rub": None,
                        "expected_order_cost_rub": 259.23,
                    }
                ]
            }
        }
    )  # type: ignore[attr-defined]

    plan_fact_summary = MagicMock()
    plan_fact_summary.fact_predict_orders = 10.0
    plan_fact_summary.fact_pay_for_order = 150.0

    mock_plan_fact_reader = MagicMock()
    mock_plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=plan_fact_summary)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: mock_plan_fact_reader,
    )

    view = await provider.build_view(adv_setting_original_id=1)

    assert view.best_cpo_bid_rub == 259.23


@pytest.mark.asyncio
async def test_build_view_rec_bid_plan_context_uses_max_cost_when_plan_not_met(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When forecast is below plan, view-provider must pass max price as target CPO."""
    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = 12345
    adv.auto_shelf_bid_control_enabled = True
    adv.plan_for_sales_for_day = 10
    adv.target_price_for_order = 100
    adv.max_price_for_order = 200

    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 500
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 500
    settings_obj.min_bid_distance_minor = 1

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=None)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=[])
    analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(return_value={111: 0.1})
    analytics.fetch_rec_bid_click_to_order_cr_7d_for_nmid = AsyncMock(
        return_value=0.05
    )

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=None)  # type: ignore[method-assign]
    provider._rec_bid_recommendation_service.get_rec_bid_recommendations = AsyncMock(
        return_value={"view": {"best_expected_bid": 111}}
    )  # type: ignore[attr-defined]

    plan_fact_summary = MagicMock()
    plan_fact_summary.fact_predict_orders = 1.0
    plan_fact_summary.fact_pay_for_order = 150.0

    mock_plan_fact_reader = MagicMock()
    mock_plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=plan_fact_summary)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: mock_plan_fact_reader,
    )

    await provider.build_view(adv_setting_original_id=1)

    assert (
        provider._rec_bid_recommendation_service.get_rec_bid_recommendations.await_args.kwargs[
            "plan_context"
        ].target_order_cost
        == 200.0
    )


def test_shop_id_from_adv_uses_wb_cabinet_not_adv_setting_column() -> None:
    """AdvSetting Redis overlay key is WBCabinet.shop_id, not a missing AdvSetting.shop_id."""
    adv = SimpleNamespace(shop_id=None, wb_cabinet=SimpleNamespace(shop_id="cab-1"))
    assert AutoShelfBidControlViewProvider._shop_id_from_adv(adv) == "cab-1"
    assert AutoShelfBidControlViewProvider._shop_id_from_adv(SimpleNamespace(adv_id=1)) is None
    complex_like = SimpleNamespace(shop_id="dto-shop", wb_cabinet=None)
    assert AutoShelfBidControlViewProvider._shop_id_from_adv(complex_like) == "dto-shop"


def _fresh_cached_promo_state(
    *,
    adv_id: int,
    fraction: Decimal,
) -> CachedShopPromoState:
    """Свежий Redis overlay-кэш с usable promo_fraction > 0 для кампании."""
    return CachedShopPromoState(
        updated_at=datetime.now(UTC),
        topup_amount=1000,
        pool_usable=False,
        pool_amount=0,
        pool_fraction=Decimal("0"),
        campaigns={
            adv_id: CachedCampaignPromoState(
                remaining=200,
                fraction=fraction,
                expires_at=None,
                usable=True,
                effective_fraction=fraction,
                pool_usable=False,
                campaign_usable=True,
            ),
        },
    )


@pytest.mark.asyncio
async def test_build_view_rec_bid_plan_context_uses_promo_overlay_when_fraction_positive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Telegram rec-bid обязан кормить plan_context scaled overlay CPO при f>0.

    AdvSetting не хранит live promo_fraction и не имеет колонки shop_id:
    f и ключ Redis живут на WBCabinet / overlay-кэше.
    get_effective_promo_plan нельзя подменять: spy только проксирует реальный overlay.
    """
    live_fraction = Decimal("0.2")
    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = 12345
    # Production AdvSetting has no shop_id column; Redis key lives on WBCabinet.
    adv.shop_id = None
    adv.wb_cabinet = SimpleNamespace(shop_id="shop-promo-red")
    adv.search_adv_id = None
    adv.auto_shelf_bid_control_enabled = True
    adv.plan_for_sales_for_day = 10
    adv.target_price_for_order = 100
    adv.max_price_for_order = 200
    adv.raise_plan_on_promobonuses = True
    adv.promo_fraction = None
    adv.auto_budget_daily_limit = 0
    adv.search_auto_budget_daily_limit = 0
    adv.common_budget_daily_limit = None

    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 500
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 500
    settings_obj.min_bid_distance_minor = 1

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=None)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=[])
    analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(return_value={111: 0.1})
    analytics.fetch_rec_bid_click_to_order_cr_7d_for_nmid = AsyncMock(
        return_value=0.05
    )

    redis_client = MagicMock()
    provider = AutoShelfBidControlViewProvider(
        redis_client=redis_client,
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=None)  # type: ignore[method-assign]
    provider._rec_bid_recommendation_service.get_rec_bid_recommendations = AsyncMock(
        return_value={"view": {"best_expected_bid": 111}}
    )  # type: ignore[attr-defined]

    plan_fact_summary = MagicMock()
    plan_fact_summary.fact_predict_orders = 10.0
    plan_fact_summary.fact_pay_for_order = 150.0

    mock_plan_fact_reader = MagicMock()
    mock_plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=plan_fact_summary)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: mock_plan_fact_reader,
    )

    cached_state = _fresh_cached_promo_state(adv_id=12345, fraction=live_fraction)
    redis_get = AsyncMock(return_value=cached_state)
    monkeypatch.setattr(RedisPromoStateManager, "get", redis_get)

    real_get_effective_promo_plan = PlanFactProvider.get_effective_promo_plan
    overlay_calls: list[object] = []

    def _spy_get_effective_promo_plan(
        adv_arg: object,
        *,
        fraction: object | None = None,
        complex_adv: object | None = None,
    ) -> object:
        overlay = real_get_effective_promo_plan(
            adv_arg,
            fraction=fraction,
            complex_adv=complex_adv,
        )
        overlay_calls.append(overlay)
        return overlay

    monkeypatch.setattr(
        PlanFactProvider,
        "get_effective_promo_plan",
        _spy_get_effective_promo_plan,
    )

    expected_overlay = real_get_effective_promo_plan(adv, fraction=live_fraction)
    assert expected_overlay.plan is not None
    expected_target = float(expected_overlay.plan.target_pay_for_order)
    expected_max = float(expected_overlay.plan.max_pay_for_order)
    assert expected_target == 125.0
    assert expected_max == 250.0

    view = await provider.build_view(adv_setting_original_id=1)

    assert overlay_calls, "build_view must call real get_effective_promo_plan"
    redis_get.assert_awaited()
    assert redis_get.await_args.args[-1] == "shop-promo-red"
    rec_call = provider._rec_bid_recommendation_service.get_rec_bid_recommendations
    plan_context = rec_call.await_args.kwargs["plan_context"]
    assert plan_context.target_order_cost == expected_target
    assert plan_context.max_order_cost == expected_max
    assert view.rec_bid_recommendation == {"best_expected_bid": 111}


@pytest.mark.asyncio
async def test_build_view_rec_bid_recommendation_fail_soft(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Recommendation errors must not break build_view."""
    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = 12345
    adv.auto_shelf_bid_control_enabled = True
    adv.plan_for_sales_for_day = 10
    adv.target_price_for_order = 100
    adv.max_price_for_order = 200

    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 500
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 500
    settings_obj.min_bid_distance_minor = 1

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=None)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=_two_qualified_cycle_bid_stats())
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(return_value={111: 0.1})
    analytics.fetch_rec_bid_click_to_order_cr_7d_for_nmid = AsyncMock(
        return_value=0.05
    )

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=None)  # type: ignore[method-assign]
    provider._rec_bid_recommendation_service.get_rec_bid_recommendations = AsyncMock(
        side_effect=RuntimeError("boom")
    )  # type: ignore[attr-defined]

    plan_fact_summary = MagicMock()
    plan_fact_summary.fact_predict_orders = 10.0
    plan_fact_summary.fact_pay_for_order = 150.0

    mock_plan_fact_reader = MagicMock()
    mock_plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=plan_fact_summary)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: mock_plan_fact_reader,
    )
    caplog.set_level("WARNING")

    view = await provider.build_view(adv_setting_original_id=1)

    assert view.rec_bid_recommendation is None
    assert "rec_bid_recommendation_failed" in caplog.text
    assert view.has_settings is True


@pytest.mark.asyncio
@pytest.mark.parametrize("best_plan_bid", [True, False, 0, 1, 40250])
async def test_build_view_rejects_invalid_best_plan_bid_values(
    monkeypatch: pytest.MonkeyPatch,
    best_plan_bid: object,
) -> None:
    """Invalid best-plan bids must not leak into DTO or recommendation payload."""
    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = 12345
    adv.auto_shelf_bid_control_enabled = True
    adv.plan_for_sales_for_day = 10
    adv.target_price_for_order = 100
    adv.max_price_for_order = 200

    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 500
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 500
    settings_obj.min_bid_distance_minor = 1

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=None)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=[])
    analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(return_value={111: 0.1})
    analytics.fetch_rec_bid_click_to_order_cr_7d_for_nmid = AsyncMock(
        return_value=0.05
    )

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=None)  # type: ignore[method-assign]
    provider._rec_bid_recommendation_service.get_rec_bid_recommendations = AsyncMock(
        return_value={
            "view": {
                "best_expected_bid": 35000,
                "best_plan_bid": best_plan_bid,
                "plan_ranked": [{"bid": 20500}],
            }
        }
    )  # type: ignore[attr-defined]

    plan_fact_summary = MagicMock()
    plan_fact_summary.fact_predict_orders = 10.0
    plan_fact_summary.fact_pay_for_order = 150.0

    mock_plan_fact_reader = MagicMock()
    mock_plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=plan_fact_summary)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: mock_plan_fact_reader,
    )

    view = await provider.build_view(adv_setting_original_id=1)

    assert view.best_plan_bid_minor is None
    assert view.rec_bid_recommendation is not None
    assert view.rec_bid_recommendation["best_plan_bid"] is None


@pytest.mark.asyncio
async def test_build_view_keeps_valid_integer_best_plan_bid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Aligned positive integer best-plan bid must remain available in DTO and payload."""
    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = 12345
    adv.auto_shelf_bid_control_enabled = True
    adv.plan_for_sales_for_day = 10
    adv.target_price_for_order = 100
    adv.max_price_for_order = 200

    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 500
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 500
    settings_obj.min_bid_distance_minor = 1

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=None)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=[])
    analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(return_value={111: 0.1})
    analytics.fetch_rec_bid_click_to_order_cr_7d_for_nmid = AsyncMock(
        return_value=0.05
    )

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=None)  # type: ignore[method-assign]
    provider._rec_bid_recommendation_service.get_rec_bid_recommendations = AsyncMock(
        return_value={
            "view": {
                "best_expected_bid": 35000,
                "best_plan_bid": 20500,
            }
        }
    )  # type: ignore[attr-defined]

    plan_fact_summary = MagicMock()
    plan_fact_summary.fact_predict_orders = 10.0
    plan_fact_summary.fact_pay_for_order = 150.0

    mock_plan_fact_reader = MagicMock()
    mock_plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=plan_fact_summary)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: mock_plan_fact_reader,
    )

    view = await provider.build_view(adv_setting_original_id=1)

    assert view.best_plan_bid_minor == 20500
    assert view.rec_bid_recommendation is not None
    assert view.rec_bid_recommendation["best_plan_bid"] == 20500


def _plan_ranked_rec_view() -> dict[str, object]:
    return {
        "plan_ranked": [
            {"bid": 57_000, "plan_distance_score": 0.1},
            {"bid": 54_000, "plan_distance_score": 0.2},
            {"bid": 48_000, "plan_distance_score": 0.3},
        ],
        "best_plan_bid": 48_000,
    }


def _two_qualified_cycle_bid_stats() -> list[object]:
    from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto.bid_stats_dto import (
        BidStatsDTO,
    )

    return [
        BidStatsDTO(
            bid_minor=57_000,
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
            bid_minor=48_000,
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


def _patch_plan_distance_rec_for_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    *,
    rec_view: dict[str, object] | None = None,
) -> None:
    """Изолировать snapshot build от ClickHouse и rec-bid read service."""
    from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_manager import (
        AutoShelfBidControlManager,
    )

    view = rec_view or _plan_ranked_rec_view()
    monkeypatch.setattr(
        AutoShelfBidControlManager,
        "_fetch_plan_distance_rec_result",
        AsyncMock(return_value={"view": view, "best_plan_bid": view.get("best_plan_bid")}),
    )
    mock_plan_fact_reader = MagicMock()
    mock_plan_fact_reader.get_latest_plan_fact = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_decision_snapshot_builder.PlanFactReader",
        lambda: mock_plan_fact_reader,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.PlanFactReader",
        lambda: mock_plan_fact_reader,
    )


@pytest.mark.asyncio
async def test_build_view_disabled_keeps_recommended_main_without_actual_or_min_bid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = 12345
    adv.auto_shelf_bid_control_enabled = False
    adv.auto_shelf_bid_control_strategy = AutoShelfBidControlStrategy.PLAN_DISTANCE
    adv.plan_for_sales_for_day = 10
    adv.target_price_for_order = 100
    adv.max_price_for_order = 200

    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 500
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 80_000
    settings_obj.min_bid_distance_minor = 100

    state = MagicMock(
        current_mode="main",
        current_main_bid_minor=48_000,
        current_test_bid_minor=None,
        current_cycle_started_at=datetime(2026, 6, 10, 23, 27, 51, tzinfo=UTC),
        previous_cycle_started_at=None,
        main_started_at=datetime(2026, 6, 10, 23, 27, 51, tzinfo=UTC),
        test_started_at=None,
        last_reason="main_waiting_observation_time",
    )

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=state)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=_two_qualified_cycle_bid_stats())
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)
    analytics.get_impressions = AsyncMock(return_value=0)
    analytics.get_first_available_bid_bucket_start = AsyncMock(return_value=None)
    analytics.get_bid_coverages = AsyncMock(return_value=[])
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(return_value={111: 0.1})
    analytics.fetch_rec_bid_click_to_order_cr_7d_for_nmid = AsyncMock(return_value=0.05)

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=None)  # type: ignore[method-assign]
    provider._rec_bid_recommendation_service.get_rec_bid_recommendations = AsyncMock(
        return_value={"view": _plan_ranked_rec_view()}
    )  # type: ignore[attr-defined]

    _patch_plan_distance_rec_for_snapshot(monkeypatch)

    view = await provider.build_view(adv_setting_original_id=1)

    assert view.recommended_main_bid_minor == 57_000
    assert view.fresh_best_main_bid_minor == 57_000
    assert view.expected_enforced_bid_minor is None
    assert view.primary_status == "disabled"
    assert "no_actual_bid" in view.warnings
    assert "no_min_bid" in view.warnings
    assert view.current_main_bid_minor == 48_000


@pytest.mark.asyncio
async def test_build_view_enabled_main_keeps_recommended_without_actual_bid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = 12345
    adv.auto_shelf_bid_control_enabled = True
    adv.auto_shelf_bid_control_strategy = AutoShelfBidControlStrategy.PLAN_DISTANCE
    adv.plan_for_sales_for_day = 10
    adv.target_price_for_order = 100
    adv.max_price_for_order = 200

    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 500
    settings_obj.target_test_observation_minutes = 60
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 80_000
    settings_obj.min_bid_distance_minor = 100

    state = MagicMock(
        current_mode="main",
        current_main_bid_minor=48_000,
        current_test_bid_minor=None,
        current_cycle_started_at=datetime(2026, 6, 10, 23, 27, 51, tzinfo=UTC),
        previous_cycle_started_at=None,
        main_started_at=None,
        test_started_at=None,
        last_reason=None,
    )

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=state)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=_two_qualified_cycle_bid_stats())
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)
    analytics.get_impressions = AsyncMock(return_value=0)
    analytics.get_first_available_bid_bucket_start = AsyncMock(return_value=None)
    analytics.get_bid_coverages = AsyncMock(return_value=[])
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(return_value={111: 0.1})
    analytics.fetch_rec_bid_click_to_order_cr_7d_for_nmid = AsyncMock(return_value=0.05)

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=12_000)  # type: ignore[method-assign]
    provider._rec_bid_recommendation_service.get_rec_bid_recommendations = AsyncMock(
        return_value={"view": _plan_ranked_rec_view()}
    )  # type: ignore[attr-defined]

    _patch_plan_distance_rec_for_snapshot(monkeypatch)

    view = await provider.build_view(adv_setting_original_id=1)

    assert view.recommended_main_bid_minor == 57_000
    assert view.expected_enforced_bid_minor == 57_000
    assert view.bid_sync_detail == "no_actual_bid"
    assert view.can_count_progress is False
    assert "no_actual_bid" in view.warnings


@pytest.mark.asyncio
async def test_view_provider_expected_none_can_count_progress_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """enabled main + <2 qualified: snapshot expected None -> can_count_progress False."""
    adv = MagicMock()
    adv.nmids = [111]
    adv.adv_id = 12345
    adv.auto_shelf_bid_control_enabled = True
    adv.auto_shelf_bid_control_strategy = AutoShelfBidControlStrategy.PLAN_DISTANCE
    adv.plan_for_sales_for_day = 10
    adv.target_price_for_order = 100
    adv.max_price_for_order = 200

    settings_obj = MagicMock()
    settings_obj.currency = "RUB"
    settings_obj.target_test_impressions = 500
    settings_obj.target_test_observation_minutes = 60
    settings_obj.test_share = 0.1
    settings_obj.max_bid_minor = 80_000
    settings_obj.min_bid_distance_minor = 100

    state = MagicMock(
        current_mode="main",
        current_main_bid_minor=48_000,
        current_test_bid_minor=41_000,
        current_cycle_started_at=datetime(2026, 6, 10, 23, 27, 51, tzinfo=UTC),
        previous_cycle_started_at=None,
        main_started_at=datetime(2026, 6, 10, 23, 27, 51, tzinfo=UTC),
        test_started_at=None,
        last_reason="main_waiting_observation_time",
    )

    repository = MagicMock()
    repository.get_adv_setting_by_original_id = AsyncMock(return_value=adv)
    repository.get_state = AsyncMock(return_value=state)
    repository.get_or_create_default_settings = AsyncMock(return_value=settings_obj)

    from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto.bid_stats_dto import (
        BidStatsDTO,
    )

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(
        return_value=[
            BidStatsDTO(
                bid_minor=48_000,
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
            )
        ]
    )
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)
    analytics.get_impressions = AsyncMock(return_value=0)
    analytics.get_first_available_bid_bucket_start = AsyncMock(return_value=None)
    analytics.get_bid_coverages = AsyncMock(return_value=[])
    analytics.fetch_rec_bid_ctr_by_bid_for_nmid = AsyncMock(return_value={111: 0.1})
    analytics.fetch_rec_bid_click_to_order_cr_7d_for_nmid = AsyncMock(return_value=0.05)

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(
        return_value=SimpleNamespace(bid_minor=48_000)
    )  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=12_000)  # type: ignore[method-assign]
    provider._rec_bid_recommendation_service.get_rec_bid_recommendations = AsyncMock(
        return_value={"view": _plan_ranked_rec_view()}
    )  # type: ignore[attr-defined]

    _patch_plan_distance_rec_for_snapshot(monkeypatch)

    view = await provider.build_view(adv_setting_original_id=1)

    assert view.expected_enforced_bid_minor is None
    assert view.fresh_best_main_bid_minor is None
    assert view.qualified_tested_bids_count == 1
    assert view.can_count_progress is False


@pytest.mark.asyncio
async def test_parse_plan_ranked_preserves_zero_cpo() -> None:
    """Zero `cpo_rub` in plan_ranked must be preserved (not treated as falsy)."""
    rec_view = {
        "plan_ranked": [
            {"bid": 12300, "cpo_rub": 0.0, "expected_order_cost_rub": 259.23}
        ]
    }

    forecasts = AutoShelfBidControlViewProvider._parse_plan_ranked_forecasts(
        rec_view
    )
    assert 12300 in forecasts
    assert forecasts[12300]["expected_order_cost_rub"] == 0.0
