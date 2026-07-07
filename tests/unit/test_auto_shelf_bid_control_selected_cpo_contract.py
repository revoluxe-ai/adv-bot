"""Unit tests for the selected/current/applied Auto Shelf CPO contract."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider import (
    AutoShelfBidControlViewProvider,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_diagnostics_cache import (
    AutoShelfBidDiagnosticsCacheManager,
    AutoShelfBidDiagnosticsDTO,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto.selected_cpo_contract import (
    AutoShelfBidSelectedCpoResolverInput,
    resolve_selected_cpo_contract,
    resolve_selected_cpo_contract_from_view,
)

pytestmark = pytest.mark.unit


class _FakeRedisClient:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.set_calls: list[tuple[str, str, int | None, int | None, bool | None]] = []

    async def set(
        self,
        key: str,
        value: str,
        ex: int | None = None,
        px: int | None = None,
        nx: bool | None = None,
    ) -> bool:
        self.set_calls.append((key, value, ex, px, nx))
        self.store[key] = value
        return True

    async def get(self, key: str) -> str | None:
        return self.store.get(key)


def _build_input(
    *,
    selected_bid_minor: int | None,
    actual_bid_minor: int | None,
    bid_sync_detail: str | None,
    recommendation_rows: list[dict[str, object]],
    enabled: bool = True,
    updated_at: datetime | None = None,
) -> AutoShelfBidSelectedCpoResolverInput:
    return AutoShelfBidSelectedCpoResolverInput(
        enabled=enabled,
        selected_bid_minor=selected_bid_minor,
        actual_bid_minor=actual_bid_minor,
        bid_sync_detail=bid_sync_detail,
        updated_at=updated_at or datetime(2026, 7, 6, tzinfo=UTC),
        recommendation_rows=recommendation_rows,
    )


def _build_view(
    *,
    selected_bid_minor: int | None,
    actual_bid_minor: int | None,
    bid_sync_detail: str | None,
    plan_ranked: list[dict[str, object]],
    state_updated_at: datetime | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        enabled=True,
        expected_enforced_bid_minor=selected_bid_minor,
        actual_bid_minor=actual_bid_minor,
        bid_sync_detail=bid_sync_detail,
        state_updated_at=state_updated_at or datetime(2026, 7, 6, tzinfo=UTC),
        rec_bid_recommendation={"plan_ranked": plan_ranked},
    )


def test_selected_cpo_contract_uses_neutral_input_and_expected_order_cost_fallback() -> None:
    contract = resolve_selected_cpo_contract(
        _build_input(
            selected_bid_minor=12300,
            actual_bid_minor=12300,
            bid_sync_detail="synced",
            recommendation_rows=[
                {"bid": 20000, "cpo_rub": 200.0},
                {"bid": 12300, "expected_order_cost_rub": 123.45},
            ],
        )
    )

    assert contract.selected_bid_minor == 12300
    assert contract.selected_cpo_rub == 123.45
    assert contract.unavailable_reason is None


def test_selected_cpo_contract_is_unavailable_when_selected_bid_is_not_synced() -> None:
    contract = resolve_selected_cpo_contract(
        _build_input(
            selected_bid_minor=12300,
            actual_bid_minor=12300,
            bid_sync_detail="pending",
            recommendation_rows=[{"bid": 12300, "cpo_rub": 123.45}],
        )
    )

    assert contract.selected_bid_minor == 12300
    assert contract.selected_cpo_rub is None
    assert contract.unavailable_reason == "selected_bid_not_synced"


def test_selected_cpo_contract_is_unavailable_when_selected_bid_row_is_missing() -> None:
    contract = resolve_selected_cpo_contract(
        _build_input(
            selected_bid_minor=12300,
            actual_bid_minor=12300,
            bid_sync_detail="synced",
            recommendation_rows=[{"bid": 20000, "cpo_rub": 200.0}],
        )
    )

    assert contract.selected_bid_minor == 12300
    assert contract.selected_cpo_rub is None
    assert contract.unavailable_reason == "selected_bid_not_found_in_plan_ranked"


def test_selected_cpo_contract_is_unavailable_when_control_is_disabled() -> None:
    contract = resolve_selected_cpo_contract(
        _build_input(
            selected_bid_minor=12300,
            actual_bid_minor=12300,
            bid_sync_detail="synced",
            recommendation_rows=[{"bid": 12300, "cpo_rub": 123.45}],
            enabled=False,
        )
    )

    assert contract.selected_bid_minor == 12300
    assert contract.selected_cpo_rub is None
    assert contract.unavailable_reason == "control_disabled"


@pytest.mark.asyncio
async def test_view_wrapper_builds_selected_cpo_contract_from_view() -> None:
    redis_client = _FakeRedisClient()
    provider = AutoShelfBidControlViewProvider(
        redis_client=redis_client,  # type: ignore[arg-type]
        repository=MagicMock(),
        analytics_repository=MagicMock(),
    )
    view = _build_view(
        selected_bid_minor=12300,
        actual_bid_minor=12300,
        bid_sync_detail="synced",
        plan_ranked=[{"bid": 12300, "cpo_rub": 123.45}],
    )
    provider.build_view = AsyncMock(return_value=view)  # type: ignore[method-assign]

    contract = await provider.build_selected_cpo_contract(1)

    assert contract.selected_bid_minor == 12300
    assert contract.selected_cpo_rub == 123.45
    assert contract.unavailable_reason is None
    assert len(redis_client.set_calls) == 1
    key, payload, ttl, px, nx = redis_client.set_calls[0]
    assert key == "auto_shelf:diagnostics:1"
    assert ttl == 300
    assert px is None
    assert nx is None
    assert json.loads(payload) == {
        "best_cpo_bid_rub": 123.0,
        "current_bid_rub": 123.0,
        "expected_bid_rub": 123.0,
        "selected_cpo_rub": 123.45,
        "updated_at": "2026-07-06T00:00:00Z",
        "source": "rec_bid_recommendation.plan_ranked[selected_bid_minor=12300]",
        "unavailable_reason": None,
    }


@pytest.mark.asyncio
async def test_view_wrapper_caches_best_bid_when_contract_is_unavailable() -> None:
    redis_client = _FakeRedisClient()
    provider = AutoShelfBidControlViewProvider(
        redis_client=redis_client,  # type: ignore[arg-type]
        repository=MagicMock(),
        analytics_repository=MagicMock(),
    )
    view = _build_view(
        selected_bid_minor=12300,
        actual_bid_minor=12000,
        bid_sync_detail="synced",
        plan_ranked=[{"bid": 12300, "cpo_rub": 123.45}],
    )
    provider.build_view = AsyncMock(return_value=view)  # type: ignore[method-assign]

    contract = await provider.build_selected_cpo_contract(1)

    assert contract.selected_bid_minor == 12300
    assert contract.selected_cpo_rub is None
    assert contract.unavailable_reason == "selected_bid_not_applied"
    assert len(redis_client.set_calls) == 1
    key, payload, ttl, px, nx = redis_client.set_calls[0]
    assert key == "auto_shelf:diagnostics:1"
    assert ttl == 300
    assert px is None
    assert nx is None
    assert json.loads(payload) == {
        "best_cpo_bid_rub": 123.0,
        "current_bid_rub": 120.0,
        "expected_bid_rub": 123.0,
        "selected_cpo_rub": None,
        "updated_at": "2026-07-06T00:00:00Z",
        "source": "auto_shelf_bid_control_view_provider.selected_cpo_contract",
        "unavailable_reason": "selected_bid_not_applied",
    }


def test_view_wrapper_matches_neutral_resolver_for_same_payload() -> None:
    view = _build_view(
        selected_bid_minor=12300,
        actual_bid_minor=12300,
        bid_sync_detail="synced",
        plan_ranked=[{"bid": 12300, "cpo_rub": 123.45}],
    )

    contract_from_view = resolve_selected_cpo_contract_from_view(view)  # type: ignore[arg-type]
    contract_from_input = resolve_selected_cpo_contract(
        _build_input(
            selected_bid_minor=12300,
            actual_bid_minor=12300,
            bid_sync_detail="synced",
            recommendation_rows=[{"bid": 12300, "cpo_rub": 123.45}],
        )
    )

    assert contract_from_view == contract_from_input


@pytest.mark.asyncio
async def test_diagnostics_cache_manager_round_trip() -> None:
    redis_client = _FakeRedisClient()
    cache = AutoShelfBidDiagnosticsCacheManager(redis_client)  # type: ignore[arg-type]
    dto = AutoShelfBidDiagnosticsDTO(
        best_cpo_bid_rub=123.0,
        current_bid_rub=120.0,
        expected_bid_rub=123.0,
        selected_cpo_rub=45.67,
        updated_at=datetime(2026, 7, 6, tzinfo=UTC),
        source="source",
        unavailable_reason="selected_bid_not_applied",
    )

    await cache.set(1, dto)
    loaded = await cache.get(1)

    assert loaded == dto
