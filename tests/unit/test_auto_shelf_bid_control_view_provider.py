from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider import (
    AutoShelfBidControlViewProvider,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto import (
    OptimizationMetric,
)


pytestmark = pytest.mark.unit


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
    analytics.get_best_bid_by_cart_cpa = AsyncMock(return_value=None)
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
    assert "settings_missing" not in view.warnings


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
