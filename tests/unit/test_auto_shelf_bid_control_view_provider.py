"""Unit tests for the Auto Shelf Bid Control view provider."""

from __future__ import annotations

from unittest.mock import ANY, AsyncMock, MagicMock, patch

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
    analytics.get_best_bid_by_ctr = AsyncMock(return_value=None)
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
    assert view.best_plan_bid_minor is None
    assert "settings_missing" not in view.warnings


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
