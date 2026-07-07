"""Unit tests for the selected/current/applied Auto Shelf CPO contract."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_view_provider import (
    AutoShelfBidControlViewProvider,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto.selected_cpo_contract import (
    AutoShelfBidSelectedCpoResolverInput,
    resolve_selected_cpo_contract,
    resolve_selected_cpo_contract_from_view,
)

pytestmark = pytest.mark.unit


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
