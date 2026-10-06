"""Dry-run pipeline: фаза A не вызывает authoritative I/O."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.wb_sky_control_plane.kernel.pipeline import dry_run
from app.modules.wb_sky_control_plane.models.changeset import (
    BudgetPolicyPayload,
    CampaignResourceRef,
    ChangeSetV1,
    LogicalScopeV1,
    OperationPreconditionV1,
    SetBudgetPolicyOperation,
)
from app.modules.wb_sky_control_plane.models.enums import DryRunStatus
from app.modules.wb_sky_control_plane.models.plan import PriorChangeSetRecord

pytestmark = pytest.mark.unit

_RESOURCE = "cmp_preflight001"


def _budget_op(
    *,
    operation_id: str = "op-a",
    limit: int = 100,
    token: str | None = "tok-present",
) -> SetBudgetPolicyOperation:
    pre: OperationPreconditionV1 | None = None
    if token is not None:
        pre = OperationPreconditionV1(state_token=token)
    return SetBudgetPolicyOperation(
        operation_id=operation_id,
        resource=CampaignResourceRef(resource_id=_RESOURCE),
        payload=BudgetPolicyPayload(auto_budget_daily_limit=limit),
        preconditions=pre,
    )


@pytest.mark.asyncio
async def test_dry_run_duplicate_target_skips_resolver_io() -> None:
    """Два budget-op на один resource → DUPLICATE_TARGET без PG/WB."""
    session = MagicMock()
    session.execute = AsyncMock()
    reader = MagicMock()
    reader.fetch_adverts_raw_by_ids = AsyncMock()

    changeset = ChangeSetV1(
        changeset_id="cs-dup-slot",
        scope=LogicalScopeV1(shop_id="shop-a"),
        operations=[
            _budget_op(operation_id="op-1"),
            _budget_op(operation_id="op-2", limit=200),
        ],
    )
    result = await dry_run(changeset, session=session, wb_reader=reader)
    assert result.status == DryRunStatus.REJECTED
    assert any(error.code == "DUPLICATE_TARGET" for error in result.errors)
    session.execute.assert_not_called()
    reader.fetch_adverts_raw_by_ids.assert_not_called()


@pytest.mark.asyncio
async def test_dry_run_missing_state_token_skips_resolver_io() -> None:
    session = MagicMock()
    session.execute = AsyncMock()
    reader = MagicMock()
    reader.fetch_adverts_raw_by_ids = AsyncMock()

    changeset = ChangeSetV1(
        changeset_id="cs-missing-token",
        scope=LogicalScopeV1(shop_id="shop-a"),
        operations=[_budget_op(token=None)],
    )
    result = await dry_run(changeset, session=session, wb_reader=reader)
    assert result.status == DryRunStatus.REJECTED
    assert result.errors[0].code == "STATE_TOKEN_MISSING"
    session.execute.assert_not_called()
    reader.fetch_adverts_raw_by_ids.assert_not_called()


@pytest.mark.asyncio
async def test_dry_run_idempotency_conflict_skips_resolver_io() -> None:
    session = MagicMock()
    session.execute = AsyncMock()
    reader = MagicMock()
    reader.fetch_adverts_raw_by_ids = AsyncMock()

    changeset = ChangeSetV1(
        changeset_id="cs-replay",
        scope=LogicalScopeV1(shop_id="shop-a"),
        operations=[_budget_op()],
    )
    prior = PriorChangeSetRecord(
        changeset_id="cs-replay",
        canonical_hash="different-body-hash",
        status=DryRunStatus.OK,
    )
    result = await dry_run(
        changeset,
        session=session,
        wb_reader=reader,
        prior=prior,
    )
    assert result.status == DryRunStatus.REJECTED
    assert result.errors[0].code == "CHANGESET_ID_CONFLICT"
    session.execute.assert_not_called()
    reader.fetch_adverts_raw_by_ids.assert_not_called()
