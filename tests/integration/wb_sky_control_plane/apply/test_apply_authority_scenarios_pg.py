"""Scenario certification tests for ApplyAuthorityService (Slice C)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from app.modules.wb_sky_control_plane.apply.constants import APPLY_CONTRACT_VERSION
from app.modules.wb_sky_control_plane.apply.enums import (
    ApplyReasonCode,
    ApplyTerminalStatus,
    DryRunReceiptLifecycleState,
)
from app.modules.wb_sky_control_plane.apply.models.request import ApplyRequestV1
from app.modules.wb_sky_control_plane.apply.persistence.models import (
    WbSkyApplyDryRunReceipt,
    WbSkyApplyEvidence,
    WbSkyApplyIdempotencyLedger,
)
from app.modules.wb_sky_control_plane.apply.service.test_hooks import ApplyServiceTestHooks
from app.modules.wb_sky_control_plane.models.changeset import (
    BudgetPolicyPayload,
    CampaignResourceRef,
    ChangeSetV1,
    LogicalScopeV1,
    OperationPreconditionV1,
    SetBudgetPolicyOperation,
)
from tests.integration.wb_sky_control_plane.apply.apply_service_harness import (
    FakeWbReader,
    auth_context,
    bind_state_token,
    issue_receipt,
    issue_receipt_committed,
    load_adv,
    make_service,
    prepare_bound_changeset,
    seed_campaign,
    seed_campaign_committed,
    session_factory,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.destructive_local]


async def _receipt_state(engine: AsyncEngine, receipt_id: str) -> str:
    maker = session_factory(engine)
    async with maker() as session:
        result = await session.execute(
            select(WbSkyApplyDryRunReceipt).where(
                WbSkyApplyDryRunReceipt.receipt_id == receipt_id
            )
        )
        row = result.scalar_one()
        return row.lifecycle_state


@pytest.mark.destructive_local
async def test_s02_stale_state_invalidated(async_engine: AsyncEngine) -> None:
    reader = FakeWbReader()
    maker = session_factory(async_engine)
    async with maker() as session:
        async with session.begin():
            shop_id, resource_id, adv_id = await seed_campaign(session)
            changeset = ChangeSetV1(
                changeset_id=f"cs_{uuid.uuid4().hex[:8]}",
                scope=LogicalScopeV1(shop_id=shop_id),
                operations=[
                    SetBudgetPolicyOperation(
                        operation_id="op1",
                        resource=CampaignResourceRef(resource_id=resource_id),
                        payload=BudgetPolicyPayload(auto_budget_daily_limit=200),
                    )
                ],
            )
            bound = await bind_state_token(changeset, session=session, reader=reader)
            rid = f"rcpt_{uuid.uuid4().hex}"
            await issue_receipt(
                session,
                changeset=bound,
                reader=reader,
                receipt_id=rid,
                state_tokens={"st1_stale_wrong": "st1_stale_wrong"},
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
    assert outcome.status == ApplyTerminalStatus.REJECTED
    assert outcome.reason_code == ApplyReasonCode.STALE_STATE
    assert await _receipt_state(async_engine, rid) == DryRunReceiptLifecycleState.INVALIDATED.value
    adv = await load_adv(async_engine, adv_id)
    assert adv.auto_budget_daily_limit == 50


@pytest.mark.destructive_local
async def test_s03_replay_survives_wb_failure(async_engine: AsyncEngine) -> None:
    reader = FakeWbReader()
    shop_id, resource_id, adv_id = await seed_campaign_committed(async_engine)
    changeset = ChangeSetV1(
        changeset_id=f"cs_{uuid.uuid4().hex[:8]}",
        scope=LogicalScopeV1(shop_id=shop_id),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op1",
                resource=CampaignResourceRef(resource_id=resource_id),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=88),
            )
        ],
    )
    bound = await prepare_bound_changeset(async_engine, reader, changeset)
    rid = f"rcpt_{uuid.uuid4().hex}"
    await issue_receipt_committed(
        async_engine, changeset=bound, reader=reader, receipt_id=rid
    )
    idem = f"idem_{uuid.uuid4().hex[:8]}"
    request = ApplyRequestV1(
        contract_version=APPLY_CONTRACT_VERSION,
        idempotency_key=idem,
        changeset=bound,
        dry_run_receipt_id=rid,
    )
    service = make_service(async_engine, reader)
    first = await service.apply(request, auth_context(shop_id))
    assert first.status == ApplyTerminalStatus.VERIFIED
    fetches_after_first = reader.fetch_count
    reader.fail_fetch = True
    second = await service.apply(request, auth_context(shop_id))
    assert second.status == ApplyTerminalStatus.VERIFIED
    assert second.evidence is not None
    assert second.evidence.evidence_id == first.evidence.evidence_id
    assert reader.fetch_count == fetches_after_first
    adv = await load_adv(async_engine, adv_id)
    assert adv.auto_budget_daily_limit == 88


@pytest.mark.destructive_local
async def test_s05_capability_drift_invalidates(async_engine: AsyncEngine) -> None:
    reader = FakeWbReader()
    shop_id, resource_id, adv_id = await seed_campaign_committed(async_engine)
    changeset = ChangeSetV1(
        changeset_id=f"cs_{uuid.uuid4().hex[:8]}",
        scope=LogicalScopeV1(shop_id=shop_id),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op1",
                resource=CampaignResourceRef(resource_id=resource_id),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=60),
            )
        ],
    )
    bound = await prepare_bound_changeset(async_engine, reader, changeset)
    rid = f"rcpt_{uuid.uuid4().hex}"
    await issue_receipt_committed(
        async_engine,
        changeset=bound,
        reader=reader,
        receipt_id=rid,
        capability_projection_digest="cpd1_wrong",
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
    assert outcome.reason_code == ApplyReasonCode.CAPABILITY_DRIFT
    assert await _receipt_state(async_engine, rid) == DryRunReceiptLifecycleState.INVALIDATED.value
    adv = await load_adv(async_engine, adv_id)
    assert adv.auto_budget_daily_limit == 50


@pytest.mark.destructive_local
async def test_s06_unauthorized_zero_mutation(async_engine: AsyncEngine) -> None:
    reader = FakeWbReader()
    shop_id, resource_id, adv_id = await seed_campaign_committed(async_engine)
    changeset = ChangeSetV1(
        changeset_id=f"cs_{uuid.uuid4().hex[:8]}",
        scope=LogicalScopeV1(shop_id=shop_id),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op1",
                resource=CampaignResourceRef(resource_id=resource_id),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=99),
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
    outcome = await make_service(async_engine, reader).apply(
        request, auth_context(shop_id, authorized=False)
    )
    assert outcome.reason_code == ApplyReasonCode.UNAUTHORIZED
    adv = await load_adv(async_engine, adv_id)
    assert adv.auto_budget_daily_limit == 50


@pytest.mark.destructive_local
async def test_s09_validation_failure_zero_writes(async_engine: AsyncEngine) -> None:
    reader = FakeWbReader()
    shop_id, resource_id, adv_id = await seed_campaign_committed(async_engine)
    changeset = ChangeSetV1(
        changeset_id=f"cs_{uuid.uuid4().hex[:8]}",
        scope=LogicalScopeV1(shop_id=shop_id),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op1",
                resource=CampaignResourceRef(resource_id=resource_id),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=200),
            )
        ],
    )
    bound = await prepare_bound_changeset(async_engine, reader, changeset)
    rid = f"rcpt_{uuid.uuid4().hex}"
    await issue_receipt_committed(
        async_engine, changeset=bound, reader=reader, receipt_id=rid
    )
    maker = session_factory(async_engine)
    async with maker() as session:
        async with session.begin():
            from app.modules.wb_sky_control_plane.registry.model import (
                WbSkyCampaignResourceRegistry,
            )

            result = await session.execute(
                select(WbSkyCampaignResourceRegistry).where(
                    WbSkyCampaignResourceRegistry.resource_id == resource_id
                )
            )
            reg = result.scalar_one()
            await session.delete(reg)
    request = ApplyRequestV1(
        contract_version=APPLY_CONTRACT_VERSION,
        idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
        changeset=bound,
        dry_run_receipt_id=rid,
    )
    outcome = await make_service(async_engine, reader).apply(
        request, auth_context(shop_id)
    )
    assert outcome.status == ApplyTerminalStatus.REJECTED
    assert outcome.reason_code == ApplyReasonCode.VALIDATION_REJECTED
    adv = await load_adv(async_engine, adv_id)
    assert adv.auto_budget_daily_limit == 50


@pytest.mark.destructive_local
async def test_s13_verification_mismatch_rollback(async_engine: AsyncEngine) -> None:
    reader = FakeWbReader()
    shop_id, resource_id, adv_id = await seed_campaign_committed(async_engine)
    changeset = ChangeSetV1(
        changeset_id=f"cs_{uuid.uuid4().hex[:8]}",
        scope=LogicalScopeV1(shop_id=shop_id),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op1",
                resource=CampaignResourceRef(resource_id=resource_id),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=65),
            )
        ],
    )
    bound = await prepare_bound_changeset(async_engine, reader, changeset)
    rid = f"rcpt_{uuid.uuid4().hex}"
    await issue_receipt_committed(
        async_engine, changeset=bound, reader=reader, receipt_id=rid
    )
    hooks = ApplyServiceTestHooks(force_post_write_verify_fail=True)
    request = ApplyRequestV1(
        contract_version=APPLY_CONTRACT_VERSION,
        idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
        changeset=bound,
        dry_run_receipt_id=rid,
    )
    outcome = await make_service(async_engine, reader, hooks=hooks).apply(
        request, auth_context(shop_id)
    )
    assert outcome.status == ApplyTerminalStatus.FAILED
    assert outcome.reason_code == ApplyReasonCode.VERIFICATION_MISMATCH
    adv = await load_adv(async_engine, adv_id)
    assert adv.auto_budget_daily_limit == 50
    assert await _receipt_state(async_engine, rid) == DryRunReceiptLifecycleState.ISSUED.value


@pytest.mark.destructive_local
async def test_s14_post_state_token_changes(async_engine: AsyncEngine) -> None:
    reader = FakeWbReader()
    shop_id, resource_id, _adv_id = await seed_campaign_committed(async_engine)
    changeset = ChangeSetV1(
        changeset_id=f"cs_{uuid.uuid4().hex[:8]}",
        scope=LogicalScopeV1(shop_id=shop_id),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op1",
                resource=CampaignResourceRef(resource_id=resource_id),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=140),
            )
        ],
    )
    bound = await prepare_bound_changeset(async_engine, reader, changeset)
    rid = f"rcpt_{uuid.uuid4().hex}"
    binding = await issue_receipt_committed(
        async_engine, changeset=bound, reader=reader, receipt_id=rid
    )
    pre = binding.state_tokens[resource_id]
    request = ApplyRequestV1(
        contract_version=APPLY_CONTRACT_VERSION,
        idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
        changeset=bound,
        dry_run_receipt_id=rid,
    )
    outcome = await make_service(async_engine, reader).apply(
        request, auth_context(shop_id)
    )
    assert outcome.evidence is not None
    post = outcome.evidence.post_state_tokens[resource_id]
    assert pre != post


@pytest.mark.destructive_local
async def test_s23_consumed_receipt_blocks_fresh_apply(async_engine: AsyncEngine) -> None:
    reader = FakeWbReader()
    shop_id, resource_id, adv_id = await seed_campaign_committed(async_engine)
    changeset = ChangeSetV1(
        changeset_id=f"cs_{uuid.uuid4().hex[:8]}",
        scope=LogicalScopeV1(shop_id=shop_id),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op1",
                resource=CampaignResourceRef(resource_id=resource_id),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=70),
            )
        ],
    )
    bound = await prepare_bound_changeset(async_engine, reader, changeset)
    rid = f"rcpt_{uuid.uuid4().hex}"
    await issue_receipt_committed(
        async_engine, changeset=bound, reader=reader, receipt_id=rid
    )
    idem1 = f"idem_{uuid.uuid4().hex[:8]}"
    request1 = ApplyRequestV1(
        contract_version=APPLY_CONTRACT_VERSION,
        idempotency_key=idem1,
        changeset=bound,
        dry_run_receipt_id=rid,
    )
    service = make_service(async_engine, reader)
    first_outcome = await service.apply(request1, auth_context(shop_id))
    assert first_outcome.status == ApplyTerminalStatus.VERIFIED
    request2 = ApplyRequestV1(
        contract_version=APPLY_CONTRACT_VERSION,
        idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
        changeset=bound,
        dry_run_receipt_id=rid,
    )
    outcome = await service.apply(request2, auth_context(shop_id))
    assert outcome.reason_code == ApplyReasonCode.RECEIPT_INVALID
    adv = await load_adv(async_engine, adv_id)
    assert adv.auto_budget_daily_limit == 70


@pytest.mark.destructive_local
async def test_s24_claim_release_after_pre_write_failure(async_engine: AsyncEngine) -> None:
    reader = FakeWbReader()
    shop_id, resource_id, adv_id = await seed_campaign_committed(async_engine)
    changeset = ChangeSetV1(
        changeset_id=f"cs_{uuid.uuid4().hex[:8]}",
        scope=LogicalScopeV1(shop_id=shop_id),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op1",
                resource=CampaignResourceRef(resource_id=resource_id),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=55),
            )
        ],
    )
    bound = await prepare_bound_changeset(async_engine, reader, changeset)
    rid = f"rcpt_{uuid.uuid4().hex}"
    await issue_receipt_committed(
        async_engine,
        changeset=bound,
        reader=reader,
        receipt_id=rid,
        capability_projection_digest="cpd1_stale_for_release",
    )
    request = ApplyRequestV1(
        contract_version=APPLY_CONTRACT_VERSION,
        idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
        changeset=bound,
        dry_run_receipt_id=rid,
    )
    assert (
        await make_service(async_engine, reader).apply(request, auth_context(shop_id))
    ).reason_code == ApplyReasonCode.CAPABILITY_DRIFT
    assert await _receipt_state(async_engine, rid) == DryRunReceiptLifecycleState.INVALIDATED.value
    # re-issue new receipt for retry eligibility demonstration on fresh receipt
    rid2 = f"rcpt_{uuid.uuid4().hex}"
    await issue_receipt_committed(
        async_engine, changeset=bound, reader=reader, receipt_id=rid2
    )
    request2 = request.model_copy(
        update={"dry_run_receipt_id": rid2, "idempotency_key": f"idem_{uuid.uuid4().hex[:8]}"}
    )
    outcome = await make_service(async_engine, reader).apply(
        request2, auth_context(shop_id)
    )
    assert outcome.status == ApplyTerminalStatus.VERIFIED
    adv = await load_adv(async_engine, adv_id)
    assert adv.auto_budget_daily_limit == 55


@pytest.mark.destructive_local
async def test_s26_evidence_failure_rolls_back_settings(async_engine: AsyncEngine) -> None:
    reader = FakeWbReader()
    shop_id, resource_id, adv_id = await seed_campaign_committed(async_engine)
    changeset = ChangeSetV1(
        changeset_id=f"cs_{uuid.uuid4().hex[:8]}",
        scope=LogicalScopeV1(shop_id=shop_id),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op1",
                resource=CampaignResourceRef(resource_id=resource_id),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=91),
            )
        ],
    )
    bound = await prepare_bound_changeset(async_engine, reader, changeset)
    rid = f"rcpt_{uuid.uuid4().hex}"
    await issue_receipt_committed(
        async_engine, changeset=bound, reader=reader, receipt_id=rid
    )
    hooks = ApplyServiceTestHooks(force_evidence_insert_fail=True)
    request = ApplyRequestV1(
        contract_version=APPLY_CONTRACT_VERSION,
        idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
        changeset=bound,
        dry_run_receipt_id=rid,
    )
    outcome = await make_service(async_engine, reader, hooks=hooks).apply(
        request, auth_context(shop_id)
    )
    assert outcome.status == ApplyTerminalStatus.FAILED
    adv = await load_adv(async_engine, adv_id)
    assert adv.auto_budget_daily_limit == 50
    maker = session_factory(async_engine)
    async with maker() as session:
        ev_rows = await session.execute(select(WbSkyApplyEvidence.evidence_id).limit(1))
        assert ev_rows.first() is None
    assert await _receipt_state(async_engine, rid) == DryRunReceiptLifecycleState.ISSUED.value


@pytest.mark.destructive_local
async def test_s27_ambiguous_commit_blocked(async_engine: AsyncEngine) -> None:
    reader = FakeWbReader()
    shop_id, resource_id, adv_id = await seed_campaign_committed(async_engine)
    changeset = ChangeSetV1(
        changeset_id=f"cs_{uuid.uuid4().hex[:8]}",
        scope=LogicalScopeV1(shop_id=shop_id),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op1",
                resource=CampaignResourceRef(resource_id=resource_id),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=44),
            )
        ],
    )
    bound = await prepare_bound_changeset(async_engine, reader, changeset)
    rid = f"rcpt_{uuid.uuid4().hex}"
    await issue_receipt_committed(
        async_engine, changeset=bound, reader=reader, receipt_id=rid
    )
    hooks = ApplyServiceTestHooks(force_ambiguous_commit=True)
    request = ApplyRequestV1(
        contract_version=APPLY_CONTRACT_VERSION,
        idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
        changeset=bound,
        dry_run_receipt_id=rid,
    )
    outcome = await make_service(async_engine, reader, hooks=hooks).apply(
        request, auth_context(shop_id)
    )
    assert outcome.status == ApplyTerminalStatus.UNKNOWN_INTERNAL_COMMIT
    adv = await load_adv(async_engine, adv_id)
    assert adv.auto_budget_daily_limit == 50
    assert (
        await _receipt_state(async_engine, rid)
        == DryRunReceiptLifecycleState.BLOCKED_RECONCILIATION.value
    )


@pytest.mark.destructive_local
async def test_s28_unauthorized_vs_capability_drift(async_engine: AsyncEngine) -> None:
    reader = FakeWbReader()
    shop_id, resource_id, adv_id = await seed_campaign_committed(async_engine)
    changeset = ChangeSetV1(
        changeset_id=f"cs_{uuid.uuid4().hex[:8]}",
        scope=LogicalScopeV1(shop_id=shop_id),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op1",
                resource=CampaignResourceRef(resource_id=resource_id),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=61),
            )
        ],
    )
    bound = await prepare_bound_changeset(async_engine, reader, changeset)
    rid_u = f"rcpt_{uuid.uuid4().hex}"
    await issue_receipt_committed(
        async_engine, changeset=bound, reader=reader, receipt_id=rid_u
    )
    unauthorized = await make_service(async_engine, reader).apply(
        ApplyRequestV1(
            contract_version=APPLY_CONTRACT_VERSION,
            idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
            changeset=bound,
            dry_run_receipt_id=rid_u,
        ),
        auth_context(shop_id, authorized=False),
    )
    assert unauthorized.reason_code == ApplyReasonCode.UNAUTHORIZED
    assert await _receipt_state(async_engine, rid_u) == DryRunReceiptLifecycleState.ISSUED.value

    rid_c = f"rcpt_{uuid.uuid4().hex}"
    await issue_receipt_committed(
        async_engine,
        changeset=bound,
        reader=reader,
        receipt_id=rid_c,
        capability_projection_digest="cpd1_drift",
    )
    drift = await make_service(async_engine, reader).apply(
        ApplyRequestV1(
            contract_version=APPLY_CONTRACT_VERSION,
            idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
            changeset=bound,
            dry_run_receipt_id=rid_c,
        ),
        auth_context(shop_id),
    )
    assert drift.reason_code == ApplyReasonCode.CAPABILITY_DRIFT
    assert await _receipt_state(async_engine, rid_c) == DryRunReceiptLifecycleState.INVALIDATED.value
    adv = await load_adv(async_engine, adv_id)
    assert adv.auto_budget_daily_limit == 50


@pytest.mark.destructive_local
async def test_s32_unauthorized_does_not_burn_receipt(async_engine: AsyncEngine) -> None:
    reader = FakeWbReader()
    shop_id, resource_id, _adv_id = await seed_campaign_committed(async_engine)
    changeset = ChangeSetV1(
        changeset_id=f"cs_{uuid.uuid4().hex[:8]}",
        scope=LogicalScopeV1(shop_id=shop_id),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op1",
                resource=CampaignResourceRef(resource_id=resource_id),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=62),
            )
        ],
    )
    bound = await prepare_bound_changeset(async_engine, reader, changeset)
    rid = f"rcpt_{uuid.uuid4().hex}"
    await issue_receipt_committed(
        async_engine, changeset=bound, reader=reader, receipt_id=rid
    )
    await make_service(async_engine, reader).apply(
        ApplyRequestV1(
            contract_version=APPLY_CONTRACT_VERSION,
            idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
            changeset=bound,
            dry_run_receipt_id=rid,
        ),
        auth_context(shop_id, authorized=False),
    )
    assert await _receipt_state(async_engine, rid) == DryRunReceiptLifecycleState.ISSUED.value


@pytest.mark.destructive_local
async def test_s33_wrong_changeset_digest(async_engine: AsyncEngine) -> None:
    reader = FakeWbReader()
    shop_id, resource_id, adv_id = await seed_campaign_committed(async_engine)
    changeset = ChangeSetV1(
        changeset_id=f"cs_{uuid.uuid4().hex[:8]}",
        scope=LogicalScopeV1(shop_id=shop_id),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op1",
                resource=CampaignResourceRef(resource_id=resource_id),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=63),
            )
        ],
    )
    bound = await prepare_bound_changeset(async_engine, reader, changeset)
    rid = f"rcpt_{uuid.uuid4().hex}"
    await issue_receipt_committed(
        async_engine, changeset=bound, reader=reader, receipt_id=rid
    )
    wrong_body = bound.model_copy(
        update={
            "operations": [
                bound.operations[0].model_copy(
                    update={
                        "payload": BudgetPolicyPayload(auto_budget_daily_limit=999)
                    }
                )
            ]
        }
    )
    outcome = await make_service(async_engine, reader).apply(
        ApplyRequestV1(
            contract_version=APPLY_CONTRACT_VERSION,
            idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
            changeset=wrong_body,
            dry_run_receipt_id=rid,
        ),
        auth_context(shop_id),
    )
    assert outcome.reason_code == ApplyReasonCode.CHANGESET_DIGEST_MISMATCH
    assert await _receipt_state(async_engine, rid) == DryRunReceiptLifecycleState.ISSUED.value
    adv = await load_adv(async_engine, adv_id)
    assert adv.auto_budget_daily_limit == 50


@pytest.mark.destructive_local
async def test_s34_blocked_reconciliation(async_engine: AsyncEngine) -> None:
    reader = FakeWbReader()
    shop_id, resource_id, adv_id = await seed_campaign_committed(async_engine)
    changeset = ChangeSetV1(
        changeset_id=f"cs_{uuid.uuid4().hex[:8]}",
        scope=LogicalScopeV1(shop_id=shop_id),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op1",
                resource=CampaignResourceRef(resource_id=resource_id),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=64),
            )
        ],
    )
    bound = await prepare_bound_changeset(async_engine, reader, changeset)
    rid = f"rcpt_{uuid.uuid4().hex}"
    maker = session_factory(async_engine)
    async with maker() as session:
        async with session.begin():
            await issue_receipt(session, changeset=bound, reader=reader, receipt_id=rid)
            result = await session.execute(
                select(WbSkyApplyDryRunReceipt).where(
                    WbSkyApplyDryRunReceipt.receipt_id == rid
                )
            )
            row = result.scalar_one()
            row.lifecycle_state = DryRunReceiptLifecycleState.BLOCKED_RECONCILIATION.value
    outcome = await make_service(async_engine, reader).apply(
        ApplyRequestV1(
            contract_version=APPLY_CONTRACT_VERSION,
            idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
            changeset=bound,
            dry_run_receipt_id=rid,
        ),
        auth_context(shop_id),
    )
    assert outcome.reason_code == ApplyReasonCode.RECEIPT_BLOCKED_RECONCILIATION
    adv = await load_adv(async_engine, adv_id)
    assert adv.auto_budget_daily_limit == 50


@pytest.mark.destructive_local
async def test_s35_replay_no_second_writer(async_engine: AsyncEngine) -> None:
    reader = FakeWbReader()
    shop_id, resource_id, adv_id = await seed_campaign_committed(async_engine)
    changeset = ChangeSetV1(
        changeset_id=f"cs_{uuid.uuid4().hex[:8]}",
        scope=LogicalScopeV1(shop_id=shop_id),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op1",
                resource=CampaignResourceRef(resource_id=resource_id),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=72),
            )
        ],
    )
    bound = await prepare_bound_changeset(async_engine, reader, changeset)
    rid = f"rcpt_{uuid.uuid4().hex}"
    await issue_receipt_committed(
        async_engine, changeset=bound, reader=reader, receipt_id=rid
    )
    idem = f"idem_{uuid.uuid4().hex[:8]}"
    request = ApplyRequestV1(
        contract_version=APPLY_CONTRACT_VERSION,
        idempotency_key=idem,
        changeset=bound,
        dry_run_receipt_id=rid,
    )
    service = make_service(async_engine, reader)
    first = await service.apply(request, auth_context(shop_id))
    assert first.status == ApplyTerminalStatus.VERIFIED
    wb_after_apply = reader.fetch_count
    second = await service.apply(request, auth_context(shop_id))
    assert second.evidence is not None
    assert second.evidence.evidence_id == first.evidence.evidence_id
    assert reader.fetch_count == wb_after_apply
    maker = session_factory(async_engine)
    async with maker() as session:
        idem_row = await session.execute(
            select(WbSkyApplyIdempotencyLedger).where(
                WbSkyApplyIdempotencyLedger.idempotency_key == idem
            )
        )
        row = idem_row.scalar_one()
        assert row.terminal_status == ApplyTerminalStatus.VERIFIED.value
    adv = await load_adv(async_engine, adv_id)
    assert adv.auto_budget_daily_limit == 72
