"""Unit tests for the read-only rec bid debug entrypoint."""

from __future__ import annotations

import pytest
from unittest.mock import ANY

import run_rec_bid_recommendations_debug as entrypoint


@pytest.mark.unit
def test_run_has_no_in_app_tunnel_bootstrap() -> None:
    """Spec local-dev-db-connectivity: entrypoint MUST NOT expose in-app tunnel API."""
    assert not hasattr(entrypoint, "_ensure_dev_tunnels")
    assert not hasattr(entrypoint, "ensure_dev_tunnels")


@pytest.mark.unit
def test_run_uses_view_payload_from_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    required = {
        "REC_BID_DEBUG_NMID": "123",
        "REC_BID_DEBUG_DATE_FROM": "2026-06-07T00:00:00",
        "REC_BID_DEBUG_DATE_TO": "2026-06-08T00:00:00",
        "REC_BID_DEBUG_SALES_PLAN": "100",
        "REC_BID_DEBUG_CURRENT_FACT_SALES": "10",
        "REC_BID_DEBUG_TARGET_ORDER_COST": "100",
        "REC_BID_DEBUG_MAX_ORDER_COST": "120",
        "REC_BID_DEBUG_CLICK_TO_ORDER_CR_7D": "0.1",
        "REC_BID_DEBUG_CURRENT_SALES_FORECAST_OVERRIDE": "90",
    }

    monkeypatch.setattr(entrypoint, "_required_env", lambda name: required[name])
    monkeypatch.setattr(entrypoint.os, "getenv", lambda name, default="": required.get(name, default))

    class _FakeRepository:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, object]]] = []

        async def fetch_rec_bid_ctr_by_bid_for_nmid(self, **kwargs):
            self.calls.append(("ctr_by_bid", kwargs))
            return {100: 0.2}

        async def fetch_rec_bid_click_to_order_cr_7d_for_nmid(self, **kwargs):
            self.calls.append(("click_to_order_cr_7d", kwargs))
            return 0.05

    class _FakeService:
        def __init__(self, repository):
            self.repository = repository
            self.calls: list[dict[str, object]] = []

        async def get_rec_bid_recommendations(self, **kwargs):
            self.calls.append(kwargs)
            return {
                "bid_result": {"expected_ranked": [{"bid": 999, "drop": True}]},
                "plan_ranked": [{"bid": 999, "drop": True}],
                "best_expected_bid": 999,
                "best_plan_bid": 999,
                "diagnostics": {},
                "view": {
                    "diagnostics": {
                        "bucket_count": 4,
                        "hour_observation_count": 1,
                        "bid_count": 1,
                        "hour_count": 1,
                    },
                    "best_expected_bid": 100,
                    "best_plan_bid": 100,
                    "expected_ranked": [
                        {
                            "bid": 100,
                            "expected_daily_impressions": 1000.0,
                            "confidence": 0.9,
                            "uncertainty": 10.0,
                            "own_anchor": 0.5,
                            "main_score": 900.0,
                            "test_score": 1100.0,
                        }
                    ],
                    "plan_ranked": [
                        {
                            "bid": 100,
                            "ctr": 0.2,
                            "expected_impressions": 1000.0,
                            "expected_clicks": 200.0,
                            "expected_orders": 20.0,
                            "expected_cost_rub": 100.0,
                            "expected_order_cost_rub": 5.0,
                            "resolved_order_cost_rub": 120.0,
                            "projected_sales": 30.0,
                            "sales_gap": -70.0,
                            "abs_sales_gap": 70.0,
                            "sales_dist": 0.7,
                            "order_cost_overlimit_rub": 0.0,
                            "order_cost_overlimit_dist": 0.0,
                            "plan_distance_score": 0.7,
                        }
                    ],
                },
            }

    repository_holder: dict[str, _FakeRepository] = {}
    service_holder: dict[str, _FakeService] = {}

    def _repository_factory(wb_manager_hub=None):
        _ = wb_manager_hub
        repository = _FakeRepository()
        repository_holder["repository"] = repository
        return repository

    def _service_factory(repository):
        service = _FakeService(repository)
        service_holder["service"] = service
        return service

    monkeypatch.setattr(entrypoint, "AutoShelfBidControlAnalyticsRepository", _repository_factory)
    monkeypatch.setattr(entrypoint, "AutoShelfBidRecommendationReadService", _service_factory)

    entrypoint.asyncio.run(entrypoint._run())

    assert repository_holder["repository"].calls == [
        (
            "ctr_by_bid",
            {
                "nmid": 123,
                "mode": None,
                "date_from": ANY,
                "date_to": ANY,
            },
        ),
        (
            "click_to_order_cr_7d",
            {
                "nmid": 123,
                "mode": None,
                "date_from": ANY,
                "date_to": ANY,
            },
        ),
    ]
    assert service_holder["service"].calls == [
        {
            "nmid": 123,
            "mode": None,
            "date_from": ANY,
            "date_to": ANY,
            "plan_context": ANY,
            "ctr_by_bid": {100: 0.2},
        }
    ]


@pytest.mark.unit
def test_run_uses_optional_debug_mode_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    required = {
        "REC_BID_DEBUG_NMID": "123",
        "REC_BID_DEBUG_DATE_FROM": "2026-06-07T00:00:00",
        "REC_BID_DEBUG_DATE_TO": "2026-06-08T00:00:00",
        "REC_BID_DEBUG_MODE": "main",
        "REC_BID_DEBUG_SALES_PLAN": "100",
        "REC_BID_DEBUG_CURRENT_FACT_SALES": "10",
        "REC_BID_DEBUG_TARGET_ORDER_COST": "100",
        "REC_BID_DEBUG_MAX_ORDER_COST": "120",
        "REC_BID_DEBUG_CLICK_TO_ORDER_CR_7D": "0.1",
        "REC_BID_DEBUG_CURRENT_SALES_FORECAST_OVERRIDE": "90",
    }
    monkeypatch.setattr(entrypoint, "_required_env", lambda name: required[name])
    monkeypatch.setattr(entrypoint.os, "getenv", lambda name, default="": required.get(name, default))

    class _FakeRepository:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, object]]] = []

        async def fetch_rec_bid_ctr_by_bid_for_nmid(self, **kwargs):
            self.calls.append(("ctr_by_bid", kwargs))
            return {100: 0.2}

        async def fetch_rec_bid_click_to_order_cr_7d_for_nmid(self, **kwargs):
            self.calls.append(("click_to_order_cr_7d", kwargs))
            return 0.05

    class _FakeService:
        def __init__(self, repository):
            self.repository = repository
            self.calls: list[dict[str, object]] = []

        async def get_rec_bid_recommendations(self, **kwargs):
            self.calls.append(kwargs)
            return {
                "bid_result": {"expected_ranked": [{"bid": 999, "drop": True}]},
                "plan_ranked": [{"bid": 999, "drop": True}],
                "best_expected_bid": 999,
                "best_plan_bid": 999,
                "diagnostics": {},
                "view": {
                    "diagnostics": {
                        "bucket_count": 4,
                        "hour_observation_count": 1,
                        "bid_count": 1,
                        "hour_count": 1,
                    },
                    "best_expected_bid": 100,
                    "best_plan_bid": 100,
                    "expected_ranked": [
                        {
                            "bid": 100,
                            "expected_daily_impressions": 1000.0,
                            "confidence": 0.9,
                            "uncertainty": 10.0,
                            "own_anchor": 0.5,
                            "main_score": 900.0,
                            "test_score": 1100.0,
                        }
                    ],
                    "plan_ranked": [
                        {
                            "bid": 100,
                            "ctr": 0.2,
                            "expected_impressions": 1000.0,
                            "expected_clicks": 200.0,
                            "expected_orders": 20.0,
                            "expected_cost_rub": 100.0,
                            "expected_order_cost_rub": 5.0,
                            "resolved_order_cost_rub": 120.0,
                            "projected_sales": 30.0,
                            "sales_gap": -70.0,
                            "abs_sales_gap": 70.0,
                            "sales_dist": 0.7,
                            "order_cost_overlimit_rub": 0.0,
                            "order_cost_overlimit_dist": 0.0,
                            "plan_distance_score": 0.7,
                        }
                    ],
                },
            }

    repository_holder: dict[str, _FakeRepository] = {}
    service_holder: dict[str, _FakeService] = {}

    def _repository_factory(wb_manager_hub=None):
        _ = wb_manager_hub
        repository = _FakeRepository()
        repository_holder["repository"] = repository
        return repository

    def _service_factory(repository):
        service = _FakeService(repository)
        service_holder["service"] = service
        return service

    monkeypatch.setattr(entrypoint, "AutoShelfBidControlAnalyticsRepository", _repository_factory)
    monkeypatch.setattr(entrypoint, "AutoShelfBidRecommendationReadService", _service_factory)

    entrypoint.asyncio.run(entrypoint._run())

    assert repository_holder["repository"].calls == [
        (
            "ctr_by_bid",
            {
                "nmid": 123,
                "mode": "main",
                "date_from": ANY,
                "date_to": ANY,
            },
        ),
        (
            "click_to_order_cr_7d",
            {
                "nmid": 123,
                "mode": "main",
                "date_from": ANY,
                "date_to": ANY,
            },
        ),
    ]
    assert service_holder["service"].calls == [
        {
            "nmid": 123,
            "mode": "main",
            "date_from": ANY,
            "date_to": ANY,
            "plan_context": ANY,
            "ctr_by_bid": {100: 0.2},
        }
    ]
