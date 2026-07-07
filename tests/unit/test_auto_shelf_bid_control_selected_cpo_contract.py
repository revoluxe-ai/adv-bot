"""Unit tests for the selected/current/applied Auto Shelf CPO contract."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider import (
    AutoShelfBidControlViewProvider,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto import (
    resolve_selected_cpo_contract_from_view,
)

pytestmark = pytest.mark.unit


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


def test_selected_cpo_contract_uses_matched_selected_bid_not_first_plan_row() -> None:
    view = _build_view(
        selected_bid_minor=12300,
        actual_bid_minor=12300,
        bid_sync_detail="synced",
        plan_ranked=[
            {"bid": 20000, "cpo_rub": 200.0},
            {"bid": 12300, "expected_order_cost_rub": 123.45},
        ],
    )

    contract = resolve_selected_cpo_contract_from_view(view)  # type: ignore[arg-type]

    assert contract.selected_bid_minor == 12300
    assert contract.selected_cpo_rub == 123.45
    assert contract.unavailable_reason is None
    assert contract.updated_at == view.state_updated_at


def test_selected_cpo_contract_is_unavailable_when_selected_bid_is_not_synced() -> None:
    view = _build_view(
        selected_bid_minor=12300,
        actual_bid_minor=12300,
        bid_sync_detail="pending",
        plan_ranked=[{"bid": 12300, "cpo_rub": 123.45}],
    )

    contract = resolve_selected_cpo_contract_from_view(view)  # type: ignore[arg-type]

    assert contract.selected_bid_minor == 12300
    assert contract.selected_cpo_rub is None
    assert contract.unavailable_reason == "selected_bid_not_synced"


def test_selected_cpo_contract_is_unavailable_when_selected_bid_row_is_missing() -> None:
    view = _build_view(
        selected_bid_minor=12300,
        actual_bid_minor=12300,
        bid_sync_detail="synced",
        plan_ranked=[{"bid": 20000, "cpo_rub": 200.0}],
    )

    contract = resolve_selected_cpo_contract_from_view(view)  # type: ignore[arg-type]

    assert contract.selected_bid_minor == 12300
    assert contract.selected_cpo_rub is None
    assert contract.unavailable_reason == "selected_bid_not_found_in_plan_ranked"


@pytest.mark.asyncio
async def test_view_provider_builds_selected_cpo_contract_from_view() -> None:
    provider = AutoShelfBidControlViewProvider(
        redis_client=MagicMock(),
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
