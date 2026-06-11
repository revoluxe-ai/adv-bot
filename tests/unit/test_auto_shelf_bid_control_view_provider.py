"""Unit tests for the Auto Shelf Bid Control view provider."""

from __future__ import annotations

from datetime import datetime, UTC
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider import (
    AutoShelfBidControlViewProvider,
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


pytestmark = pytest.mark.unit


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
    repository.save_state = AsyncMock(side_effect=lambda saved_state: saved_state)

    analytics = MagicMock()
    analytics.get_bid_stats = AsyncMock(return_value=[])
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

    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
        repository=repository,
        analytics_repository=analytics,
    )
    provider._bid_cache.get_bid = AsyncMock(return_value=MagicMock(bid_minor=20_500))  # type: ignore[attr-defined]
    provider._fetch_wb_min_bid_minor = AsyncMock(return_value=12_000)  # type: ignore[method-assign]
    selector_mock = MagicMock(return_value=37_500)
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.choose_next_test_bid_by_coverage_layers",
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
    assert all(row.closed_layers == 0 for row in view.coverage_bid_rows if row.bid_minor in {37_500, 60_000, 12_000})
    analytics.get_first_available_bid_bucket_start.assert_awaited_once_with(
        nmid=111,
        currency="RUB",
        price_minor=None,
        mode=None,
    )
    analytics.get_bid_coverages.assert_awaited_once_with(
        nmid=111,
        date_from=first_bucket_start,
        date_to=ANY,
        currency="RUB",
        price_minor=None,
        mode=None,
    )
    selector_mock.assert_called_once()


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
    analytics.get_bid_stats = AsyncMock(return_value=[])
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
    assert {row.bid_minor for row in view.coverage_bid_rows} == {33_900, 12_000, 60_000}
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
    analytics.get_bid_stats = AsyncMock(return_value=[])
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
    analytics.get_bid_stats = AsyncMock(return_value=[])
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
    ("optimization_metric", "expected_method", "unexpected_method"),
    [
        (
            OptimizationMetric.CTR,
            "get_best_bid_by_ctr",
            "get_best_bid_by_cart_cpa",
        ),
        (
            OptimizationMetric.CPC,
            "get_best_bid_by_cart_cpa",
            "get_best_bid_by_ctr",
        ),
    ],
)
async def test_build_view_uses_best_bid_method_for_optimization_metric(
    monkeypatch: pytest.MonkeyPatch,
    optimization_metric: OptimizationMetric,
    expected_method: str,
    unexpected_method: str,
) -> None:
    """Select the report-day best bid with the active optimization metric."""
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
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider.resolve_optimization_metric",
        lambda _fact_cpo, _resolve_cpo: optimization_metric,
    )

    await provider.build_view(adv_setting_original_id=1)

    getattr(analytics, expected_method).assert_awaited_once()
    getattr(analytics, unexpected_method).assert_not_awaited()


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
    analytics.get_bid_stats = AsyncMock(return_value=[])
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
