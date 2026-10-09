"""Core ApplyAuthorityService disposable-PG tests (Slice C)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from app.modules.wb_sky_control_plane.apply.constants import APPLY_CONTRACT_VERSION
from app.modules.wb_sky_control_plane.apply.enums import (
    ApplyReasonCode,
    ApplyTerminalStatus,
)
from app.modules.wb_sky_control_plane.apply.models.request import ApplyRequestV1
from app.modules.wb_sky_control_plane.models.changeset import (
    BudgetPolicyPayload,
    CampaignResourceRef,
    ChangeSetV1,
    LogicalScopeV1,
    OperationPreconditionV1,
    SalesPolicyPayload,
    SetBudgetPolicyOperation,
    SetSalesPolicyOperation,
)
from tests.integration.wb_sky_control_plane.apply.apply_service_harness import (
    FakeWbReader,
    auth_context,
    issue_receipt_committed,
    load_adv,
    make_service,
    prepare_bound_changeset,
    seed_campaign_committed,
    session_factory,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.destructive_local]


@pytest.mark.destructive_local
async def test_apply_s01_verified_after_real_commit(async_engine: AsyncEngine) -> None:
    reader = FakeWbReader()
    shop_id, resource_id, adv_id = await seed_campaign_committed(async_engine)
    changeset = ChangeSetV1(
        changeset_id=f"cs_{uuid.uuid4().hex[:8]}",
        scope=LogicalScopeV1(shop_id=shop_id),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op1",
                resource=CampaignResourceRef(resource_id=resource_id),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=120),
            )
        ],
    )
    bound = await prepare_bound_changeset(async_engine, reader, changeset)
    rid = f"rcpt_{uuid.uuid4().hex}"
    await issue_receipt_committed(
        async_engine, changeset=bound, reader=reader, receipt_id=rid
    )
    request = ApplyRequestV1(
        contract_version=APPLY_CONTRACT_VERSION,
        idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
        changeset=bound,
        dry_run_receipt_id=rid,
    )
    service = make_service(async_engine, reader)
    outcome = await service.apply(request, auth_context(shop_id))
    assert outcome.status == ApplyTerminalStatus.VERIFIED
    adv = await load_adv(async_engine, adv_id)
    assert adv.auto_budget_daily_limit == 120


@pytest.mark.destructive_local
async def test_commit_visibility_fresh_session(async_engine: AsyncEngine) -> None:
    reader = FakeWbReader()
    shop_id, resource_id, adv_id = await seed_campaign_committed(async_engine)
    changeset = ChangeSetV1(
        changeset_id=f"cs_{uuid.uuid4().hex[:8]}",
        scope=LogicalScopeV1(shop_id=shop_id),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op1",
                resource=CampaignResourceRef(resource_id=resource_id),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=131),
            )
        ],
    )
    bound = await prepare_bound_changeset(async_engine, reader, changeset)
    rid = f"rcpt_{uuid.uuid4().hex}"
    await issue_receipt_committed(
        async_engine, changeset=bound, reader=reader, receipt_id=rid
    )
    request = ApplyRequestV1(
        contract_version=APPLY_CONTRACT_VERSION,
        idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
        changeset=bound,
        dry_run_receipt_id=rid,
    )
    before = await load_adv(async_engine, adv_id)
    assert before.auto_budget_daily_limit == 50
    service = make_service(async_engine, reader)
    outcome = await service.apply(request, auth_context(shop_id))
    assert outcome.status == ApplyTerminalStatus.VERIFIED
    after = await load_adv(async_engine, adv_id)
    assert after.auto_budget_daily_limit == 131


@pytest.mark.destructive_local
async def test_apply_s08_two_operations_atomic(async_engine: AsyncEngine) -> None:
    reader = FakeWbReader()
    shop_id, resource_id, adv_id = await seed_campaign_committed(async_engine)
    changeset = ChangeSetV1(
        changeset_id=f"cs_{uuid.uuid4().hex[:8]}",
        scope=LogicalScopeV1(shop_id=shop_id),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op_b",
                resource=CampaignResourceRef(resource_id=resource_id),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=77),
            ),
            SetSalesPolicyOperation(
                operation_id="op_s",
                resource=CampaignResourceRef(resource_id=resource_id),
                payload=SalesPolicyPayload(plan_for_sales_for_day=10),
            ),
        ],
    )
    bound = await prepare_bound_changeset(async_engine, reader, changeset)
    rid = f"rcpt_{uuid.uuid4().hex}"
    await issue_receipt_committed(
        async_engine, changeset=bound, reader=reader, receipt_id=rid
    )
    request = ApplyRequestV1(
        contract_version=APPLY_CONTRACT_VERSION,
        idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
        changeset=bound,
        dry_run_receipt_id=rid,
    )
    outcome = await make_service(async_engine, reader).apply(
        request, auth_context(shop_id)
    )
    assert outcome.status == ApplyTerminalStatus.VERIFIED
    adv = await load_adv(async_engine, adv_id)
    assert adv.auto_budget_daily_limit == 77
    assert adv.plan_for_sales_for_day == 10
