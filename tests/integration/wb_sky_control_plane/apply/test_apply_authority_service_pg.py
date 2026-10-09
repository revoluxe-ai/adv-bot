"""Disposable PG integration tests for ApplyAuthorityService (Slice C)."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.wb_sky_control_plane.apply.enums import (
    ApplyReasonCode,
    ApplyTerminalStatus,
    DryRunReceiptLifecycleState,
    TransportChannel,
)
from app.modules.wb_sky_control_plane.apply.models.context import (
    ApplyInvocationContext,
    PermissionGrantsV1,
    PrincipalRefV1,
    ShopAuthorizationV1,
)
from app.modules.wb_sky_control_plane.apply.models.request import ApplyRequestV1
from app.modules.wb_sky_control_plane.apply.persistence.postgres_stores import (
    PostgresDryRunReceiptStore,
)
from app.modules.wb_sky_control_plane.apply.service.apply_authority_service import (
    ApplyAuthorityService,
)
from app.modules.wb_sky_control_plane.apply.service.revalidation import (
    project_apply_binding_material,
)
from app.modules.wb_sky_control_plane.apply.constants import APPLY_CONTRACT_VERSION
from app.modules.wb_sky_control_plane.models.changeset import (
    BudgetPolicyPayload,
    CampaignOperationV1,
    CampaignResourceRef,
    ChangeSetV1,
    LogicalScopeV1,
    OperationPreconditionV1,
    SalesPolicyPayload,
    SetBudgetPolicyOperation,
    SetSalesPolicyOperation,
)
from app.modules.wb_sky_control_plane.models.enums import DryRunStatus
from app.modules.wb_sky_control_plane.apply.models.receipt import DryRunReceiptBindingV1
from app.modules.wb_sky_control_plane.read.resolver import resolve_changeset_snapshots
from app.modules.wb_sky_control_plane.registry.model import WbSkyCampaignResourceRegistry

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class _FakeWbReader:
    async def fetch_adverts_raw_by_ids(
        self, adv_ids: list[int]
    ) -> list[Mapping[str, object]]:
        out: list[Mapping[str, object]] = []
        for adv_id in adv_ids:
            out.append(
                {
                    "id": adv_id,
                    "bid_type": "unified" if adv_id % 2 == 0 else "manual",
                    "status": 9,
                    "settings": {
                        "payment_type": "cpm",
                        "placements": {"search": False, "recommendations": True},
                        "name": f"c-{adv_id}",
                    },
                    "nm_settings": [{"nm_id": 777}],
                }
            )
        return out


async def _bind_state_token(
    changeset: ChangeSetV1,
    *,
    session: AsyncSession,
    reader: _FakeWbReader,
) -> ChangeSetV1:
    snapshots, errors = await resolve_changeset_snapshots(
        changeset,
        session=session,
        wb_reader=reader,
    )
    assert errors == []
    operations: list[CampaignOperationV1] = []
    for operation in changeset.operations:
        token = snapshots[operation.resource.resource_id].state_token
        assert token
        operations.append(
            operation.model_copy(
                update={"preconditions": OperationPreconditionV1(state_token=token)}
            )
        )
    return changeset.model_copy(update={"operations": operations})


def _auth_context(shop_id: str) -> ApplyInvocationContext:
    return ApplyInvocationContext(
        principal_ref=PrincipalRefV1(kind="wb_user", principal_id="u_test"),
        shop_authorization=ShopAuthorizationV1(shop_id=shop_id, authorized=True),
        permission_grants=PermissionGrantsV1(apply_campaign_settings=True),
        transport_channel=TransportChannel.INTERNAL,
        auth_proof_ref="sess_test",
    )


async def _seed_campaign(
    session: AsyncSession,
    *,
    auto_budget_daily_limit: int = 50,
) -> tuple[str, str, AdvSetting, str]:
    shop_id = f"shop_{uuid.uuid4().hex[:10]}"
    resource_id = f"cmp_{uuid.uuid4().hex[:12]}"
    cab = WBCabinet(
        shop_id=shop_id,
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
    )
    session.add(cab)
    await session.flush()
    adv = AdvSetting(
        name="apply-test",
        wb_cabinet_id=cab.id,
        adv_id=100_000 + (cab.id or 0),
        active_status="done",
        auto_budget_watchdog_enabled=False,
        auto_budget_daily_limit=auto_budget_daily_limit,
    )
    session.add(adv)
    await session.flush()
    reg = WbSkyCampaignResourceRegistry(
        resource_id=resource_id,
        wb_cabinet_id=cab.id,
        adv_setting_id=adv.id,
        auto_adv_id=100,
        search_adv_id=200,
        anchor_fingerprint=f"fp_{uuid.uuid4().hex}",
    )
    session.add(reg)
    await session.flush()
    return shop_id, resource_id, adv, str(cab.id)


async def _issue_receipt(
    session: AsyncSession,
    *,
    changeset: ChangeSetV1,
    reader: _FakeWbReader,
    receipt_id: str,
) -> DryRunReceiptBindingV1:
    material = await project_apply_binding_material(
        changeset,
        session=session,
        wb_reader=reader,
    )
    assert material.status == DryRunStatus.OK
    now = datetime.now(timezone.utc)
    binding = DryRunReceiptBindingV1(
        receipt_id=receipt_id,
        issued_at=now,
        expires_at=now + timedelta(hours=2),
        scope=changeset.scope,
        changeset_id=changeset.changeset_id,
        semantic_digest=material.semantic_digest,
        preview_digest=material.preview_digest,
        state_tokens=material.state_tokens,
        capability_projection_digest=material.capability_projection_digest,
        dry_run_status=DryRunStatus.OK,
    )
    await PostgresDryRunReceiptStore(session).insert_issued(binding)
    return binding


@pytest.mark.destructive_local
async def test_apply_s01_verified_mutates_adv_setting(async_session: AsyncSession) -> None:
    reader = _FakeWbReader()
    shop_id, resource_id, adv, _cab = await _seed_campaign(async_session)
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
    bound = await _bind_state_token(changeset, session=async_session, reader=reader)
    rid = f"rcpt_{uuid.uuid4().hex}"
    await _issue_receipt(
        async_session, changeset=bound, reader=reader, receipt_id=rid
    )
    request = ApplyRequestV1(
        contract_version=APPLY_CONTRACT_VERSION,
        idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
        changeset=bound,
        dry_run_receipt_id=rid,
    )
    service = ApplyAuthorityService(session=async_session, wb_reader=reader)
    outcome = await service.apply(request, _auth_context(shop_id))
    assert outcome.status == ApplyTerminalStatus.VERIFIED
    assert outcome.evidence is not None
    await async_session.refresh(adv)
    assert adv.auto_budget_daily_limit == 120


@pytest.mark.destructive_local
async def test_apply_s02_stale_state_zero_mutation(async_session: AsyncSession) -> None:
    reader = _FakeWbReader()
    shop_id, resource_id, adv, _cab = await _seed_campaign(async_session)
    changeset = ChangeSetV1(
        changeset_id=f"cs_{uuid.uuid4().hex[:8]}",
        scope=LogicalScopeV1(shop_id=shop_id),
        operations=[
            SetBudgetPolicyOperation(
                operation_id="op1",
                resource=CampaignResourceRef(resource_id=resource_id),
                payload=BudgetPolicyPayload(auto_budget_daily_limit=200),
                preconditions=OperationPreconditionV1(state_token="st1_stale_wrong"),
            )
        ],
    )
    rid = f"rcpt_{uuid.uuid4().hex}"
    material = await project_apply_binding_material(
        changeset, session=async_session, wb_reader=reader
    )
    now = datetime.now(timezone.utc)
    binding = DryRunReceiptBindingV1(
        receipt_id=rid,
        issued_at=now,
        expires_at=now + timedelta(hours=2),
        scope=changeset.scope,
        changeset_id=changeset.changeset_id,
        semantic_digest=material.semantic_digest,
        preview_digest=material.preview_digest,
        state_tokens={"st1_fake": "st1_fake"},
        capability_projection_digest=material.capability_projection_digest,
        dry_run_status=DryRunStatus.OK,
    )
    await PostgresDryRunReceiptStore(async_session).insert_issued(binding)
    request = ApplyRequestV1(
        contract_version=APPLY_CONTRACT_VERSION,
        idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
        changeset=changeset,
        dry_run_receipt_id=rid,
    )
    service = ApplyAuthorityService(session=async_session, wb_reader=reader)
    outcome = await service.apply(request, _auth_context(shop_id))
    assert outcome.status == ApplyTerminalStatus.REJECTED
    assert outcome.reason_code == ApplyReasonCode.STALE_STATE
    await async_session.refresh(adv)
    assert adv.auto_budget_daily_limit == 50


@pytest.mark.destructive_local
async def test_apply_s03_replay_without_second_mutation(
    async_session: AsyncSession,
) -> None:
    reader = _FakeWbReader()
    shop_id, resource_id, adv, _cab = await _seed_campaign(async_session)
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
    bound = await _bind_state_token(changeset, session=async_session, reader=reader)
    rid = f"rcpt_{uuid.uuid4().hex}"
    await _issue_receipt(
        async_session, changeset=bound, reader=reader, receipt_id=rid
    )
    idem = f"idem_{uuid.uuid4().hex[:8]}"
    request = ApplyRequestV1(
        contract_version=APPLY_CONTRACT_VERSION,
        idempotency_key=idem,
        changeset=bound,
        dry_run_receipt_id=rid,
    )
    service = ApplyAuthorityService(session=async_session, wb_reader=reader)
    first = await service.apply(request, _auth_context(shop_id))
    assert first.status == ApplyTerminalStatus.VERIFIED
    await async_session.refresh(adv)
    assert adv.auto_budget_daily_limit == 88

    second = await service.apply(request, _auth_context(shop_id))
    assert second.status == ApplyTerminalStatus.VERIFIED
    assert second.evidence is not None
    assert second.evidence.evidence_id == first.evidence.evidence_id
    await async_session.refresh(adv)
    assert adv.auto_budget_daily_limit == 88


@pytest.mark.destructive_local
async def test_apply_s06_unauthorized_zero_mutation(async_session: AsyncSession) -> None:
    reader = _FakeWbReader()
    shop_id, resource_id, adv, _cab = await _seed_campaign(async_session)
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
    bound = await _bind_state_token(changeset, session=async_session, reader=reader)
    rid = f"rcpt_{uuid.uuid4().hex}"
    await _issue_receipt(
        async_session, changeset=bound, reader=reader, receipt_id=rid
    )
    request = ApplyRequestV1(
        contract_version=APPLY_CONTRACT_VERSION,
        idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
        changeset=bound,
        dry_run_receipt_id=rid,
    )
    denied = ApplyInvocationContext(
        principal_ref=PrincipalRefV1(kind="wb_user", principal_id="u_denied"),
        shop_authorization=ShopAuthorizationV1(shop_id=shop_id, authorized=False),
        permission_grants=PermissionGrantsV1(apply_campaign_settings=True),
        transport_channel=TransportChannel.API,
        auth_proof_ref="sess_denied",
    )
    service = ApplyAuthorityService(session=async_session, wb_reader=reader)
    outcome = await service.apply(request, denied)
    assert outcome.status == ApplyTerminalStatus.REJECTED
    assert outcome.reason_code == ApplyReasonCode.UNAUTHORIZED
    await async_session.refresh(adv)
    assert adv.auto_budget_daily_limit == 50


@pytest.mark.destructive_local
async def test_apply_s08_two_operations_atomic(async_session: AsyncSession) -> None:
    reader = _FakeWbReader()
    shop_id, resource_id, adv, _cab = await _seed_campaign(async_session)
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
    bound = await _bind_state_token(changeset, session=async_session, reader=reader)
    rid = f"rcpt_{uuid.uuid4().hex}"
    await _issue_receipt(
        async_session, changeset=bound, reader=reader, receipt_id=rid
    )
    request = ApplyRequestV1(
        contract_version=APPLY_CONTRACT_VERSION,
        idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
        changeset=bound,
        dry_run_receipt_id=rid,
    )
    service = ApplyAuthorityService(session=async_session, wb_reader=reader)
    outcome = await service.apply(request, _auth_context(shop_id))
    assert outcome.status == ApplyTerminalStatus.VERIFIED
    await async_session.refresh(adv)
    assert adv.auto_budget_daily_limit == 77
    assert adv.plan_for_sales_for_day == 10
