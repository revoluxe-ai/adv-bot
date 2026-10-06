"""Pipeline dry-run integration with in-memory ports."""

from __future__ import annotations

from collections.abc import Mapping
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.wb_sky_control_plane.kernel.pipeline import dry_run
from app.modules.wb_sky_control_plane.models.changeset import (
    BudgetPolicyPayload,
    CampaignResourceRef,
    ChangeSetV1,
    LogicalScopeV1,
    SetBudgetPolicyOperation,
)
from app.modules.wb_sky_control_plane.models.enums import DryRunStatus
from app.modules.wb_sky_control_plane.registry.model import WbSkyCampaignResourceRegistry

pytestmark = pytest.mark.unit

_SHOP_ID = "shop-test-5"
_WB_CABINET_ID = 5


class _FakeWbReader:
    async def fetch_adverts_raw_by_ids(
        self, adv_ids: list[int]
    ) -> list[Mapping[str, object]]:
        out: list[Mapping[str, object]] = []
        for adv_id in adv_ids:
            row: dict[str, object] = {
                "id": adv_id,
                "bid_type": "unified" if adv_id == 100 else "manual",
                "status": 9,
                "settings": {
                    "payment_type": "cpm",
                    "placements": {"search": False, "recommendations": True},
                    "name": f"c-{adv_id}",
                },
                "nm_settings": [{"nm_id": 777}],
            }
            out.append(row)
        return out


def _session_with_registry(registry_row: WbSkyCampaignResourceRegistry) -> MagicMock:
    cabinet_result = MagicMock()
    cabinet_result.scalar_one_or_none.return_value = _WB_CABINET_ID

    registry_result = MagicMock()
    registry_result.scalars.return_value.all.return_value = [registry_row]

    session = MagicMock()
    session.execute = AsyncMock(side_effect=[cabinet_result, registry_result])
    return session


@pytest.mark.asyncio
async def test_dry_run_ok_with_semantic_plan() -> None:
    """Happy path: resolve → capabilities → plan semantic diff."""
    resource_id = "cmp_deadbeef"
    registry_row = WbSkyCampaignResourceRegistry(
        resource_id=resource_id,
        wb_cabinet_id=_WB_CABINET_ID,
        adv_setting_id=99,
        auto_adv_id=100,
        search_adv_id=200,
        anchor_fingerprint="fp",
    )
    adv_row = SimpleNamespace(
        auto_budget_watchdog_enabled=False,
        auto_budget_daily_limit=50,
        search_auto_budget_daily_limit=0,
        use_common_budget=True,
        common_budget_daily_limit=0,
        auto_budget_total_limit=500,
        search_auto_budget_total_limit=500,
        common_budget_total_limit=500,
        orders_source_for_auto_mode=SimpleNamespace(value="COMMON_STATISTIC"),
        plan_for_sales_for_day=None,
        target_price_for_order=None,
        max_price_for_order=None,
        sales_predict_method=SimpleNamespace(value="FACT"),
        strategy=SimpleNamespace(value="MIN_CPO"),
        auto_update_strategy=False,
        auto_shelf_bid_control_enabled=False,
        auto_shelf_bid_control_strategy=None,
    )
    session = _session_with_registry(registry_row)
    session.get = AsyncMock(return_value=adv_row)

    changeset = ChangeSetV1(
        changeset_id="cs-ok",
        scope=LogicalScopeV1(shop_id=_SHOP_ID),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op-budget-1",
                resource=CampaignResourceRef(resource_id=resource_id),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=100),
            )
        ],
    )
    result = await dry_run(
        changeset,
        session=session,
        wb_reader=_FakeWbReader(),
    )
    assert result.status == DryRunStatus.OK
    assert result.plan is not None
    assert result.plan.is_no_op is False
    assert len(result.plan.effects[0].semantic_changes) == 1


@pytest.mark.asyncio
async def test_dry_run_no_op_when_payload_matches_current() -> None:
    """Explicit no-op when desired equals current local policy."""
    resource_id = "cmp_noop"
    registry_row = WbSkyCampaignResourceRegistry(
        resource_id=resource_id,
        wb_cabinet_id=_WB_CABINET_ID,
        adv_setting_id=99,
        auto_adv_id=100,
        search_adv_id=None,
        anchor_fingerprint="fp2",
    )
    adv_row = SimpleNamespace(
        auto_budget_watchdog_enabled=False,
        auto_budget_daily_limit=100,
        search_auto_budget_daily_limit=0,
        use_common_budget=True,
        common_budget_daily_limit=0,
        auto_budget_total_limit=500,
        search_auto_budget_total_limit=500,
        common_budget_total_limit=500,
        orders_source_for_auto_mode=SimpleNamespace(value="COMMON_STATISTIC"),
        plan_for_sales_for_day=None,
        target_price_for_order=None,
        max_price_for_order=None,
        sales_predict_method=SimpleNamespace(value="FACT"),
        strategy=SimpleNamespace(value="MIN_CPO"),
        auto_update_strategy=False,
        auto_shelf_bid_control_enabled=False,
        auto_shelf_bid_control_strategy=None,
    )
    session = _session_with_registry(registry_row)
    session.get = AsyncMock(return_value=adv_row)

    changeset = ChangeSetV1(
        changeset_id="cs-noop",
        scope=LogicalScopeV1(shop_id=_SHOP_ID),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op-budget-1",
                resource=CampaignResourceRef(resource_id=resource_id),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=100),
            )
        ],
    )
    result = await dry_run(
        changeset,
        session=session,
        wb_reader=_FakeWbReader(),
    )
    assert result.status == DryRunStatus.NO_OP
    assert result.plan is not None
    assert result.plan.is_no_op is True
