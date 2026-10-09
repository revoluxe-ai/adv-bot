"""Disposable PG integration tests for Apply Authority ledger (Slice B)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.wb_sky_control_plane.apply.constants import APPLY_CONTRACT_VERSION
from app.modules.wb_sky_control_plane.apply.enums import (
    ApplyAttemptLifecycleState,
    ApplyTerminalStatus,
    DryRunReceiptLifecycleState,
    TransportChannel,
)
from app.modules.wb_sky_control_plane.apply.idempotency import IdempotencyKey
from app.modules.wb_sky_control_plane.apply.models.evidence import ApplyEvidenceV1
from app.modules.wb_sky_control_plane.apply.models.receipt import DryRunReceiptBindingV1
from app.modules.wb_sky_control_plane.apply.persistence.postgres_stores import (
    PostgresApplyAttemptStore,
    PostgresApplyEvidenceStore,
    PostgresDryRunReceiptStore,
    PostgresIdempotencyStore,
)
from app.modules.wb_sky_control_plane.apply.persistence.results import (
    IdempotencyClaimResult,
    ReceiptClaimResult,
)
from app.modules.wb_sky_control_plane.models.changeset import LogicalScopeV1
from app.modules.wb_sky_control_plane.models.enums import DryRunStatus

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


def _binding(receipt_id: str, *, expires_at: datetime) -> DryRunReceiptBindingV1:
    now = datetime.now(timezone.utc)
    return DryRunReceiptBindingV1(
        receipt_id=receipt_id,
        issued_at=now,
        expires_at=expires_at,
        scope=LogicalScopeV1(shop_id=f"shop_{uuid.uuid4().hex[:8]}"),
        changeset_id="cs_1",
        semantic_digest="sd1_x",
        preview_digest="pd1_x",
        state_tokens={"cmp_a": "st1_a"},
        capability_projection_digest="cpd1_x",
        dry_run_status=DryRunStatus.OK,
    )


@pytest.mark.destructive_local
async def test_receipt_insert_claim_and_invalidate(async_session: AsyncSession) -> None:
    store = PostgresDryRunReceiptStore(async_session)
    rid = f"rcpt_{uuid.uuid4().hex}"
    binding = _binding(rid, expires_at=datetime.now(timezone.utc) + timedelta(hours=1))
    issued = await store.insert_issued(binding)
    assert issued.lifecycle_state == DryRunReceiptLifecycleState.ISSUED

    claim = await store.claim(rid, now=datetime.now(timezone.utc))
    assert claim == ReceiptClaimResult.CLAIMED

    invalidated = await store.transition_lifecycle(
        rid, DryRunReceiptLifecycleState.INVALIDATED
    )
    assert invalidated is not None
    assert invalidated.lifecycle_state == DryRunReceiptLifecycleState.INVALIDATED

    again = await store.transition_lifecycle(rid, DryRunReceiptLifecycleState.ISSUED)
    assert again is not None
    assert again.lifecycle_state == DryRunReceiptLifecycleState.INVALIDATED


@pytest.mark.destructive_local
async def test_receipt_blocked_reconciliation_persists(async_session: AsyncSession) -> None:
    store = PostgresDryRunReceiptStore(async_session)
    rid = f"rcpt_{uuid.uuid4().hex}"
    binding = _binding(rid, expires_at=datetime.now(timezone.utc) + timedelta(hours=1))
    await store.insert_issued(binding)
    blocked = await store.transition_lifecycle(
        rid, DryRunReceiptLifecycleState.BLOCKED_RECONCILIATION
    )
    assert blocked is not None
    assert (
        blocked.lifecycle_state == DryRunReceiptLifecycleState.BLOCKED_RECONCILIATION
    )
    claim = await store.claim(rid, now=datetime.now(timezone.utc))
    assert claim == ReceiptClaimResult.BLOCKED_RECONCILIATION


@pytest.mark.destructive_local
async def test_idempotency_unique_key_and_conflict(async_session: AsyncSession) -> None:
    store = PostgresIdempotencyStore(async_session)
    key = IdempotencyKey(shop_id="shop_a", idempotency_key="key_1")
    first = await store.try_claim(
        key, fingerprint="fp1", attempt_id="att_1"
    )
    assert first == IdempotencyClaimResult.CLAIMED

    second = await store.try_claim(
        key, fingerprint="fp2", attempt_id="att_2"
    )
    assert second == IdempotencyClaimResult.CONFLICT


@pytest.mark.destructive_local
async def test_evidence_insert_only_immutable(async_session: AsyncSession) -> None:
    ev_store = PostgresApplyEvidenceStore(async_session)
    eid = f"ev_{uuid.uuid4().hex}"
    evidence = ApplyEvidenceV1(
        evidence_id=eid,
        scope=LogicalScopeV1(shop_id="shop_ev"),
        changeset_id="cs_1",
        dry_run_receipt_id="rcpt_1",
        idempotency_key="k1",
        apply_contract_version=APPLY_CONTRACT_VERSION,
        semantic_digest="sd1_x",
        preview_digest="pd1_x",
        terminal_status=ApplyTerminalStatus.VERIFIED,
        committed_at=datetime.now(timezone.utc),
    )
    await ev_store.insert(evidence)
    loaded = await ev_store.get_by_id(eid)
    assert loaded is not None
    assert loaded.evidence_id == eid

    with pytest.raises(IntegrityError):
        await ev_store.insert(evidence)


@pytest.mark.destructive_local
async def test_attempt_lifecycle_separate_from_evidence(
    async_session: AsyncSession,
) -> None:
    attempt_store = PostgresApplyAttemptStore(async_session)
    attempt = await attempt_store.insert(
        attempt_id=f"att_{uuid.uuid4().hex}",
        shop_id="shop_1",
        idempotency_key="k1",
        dry_run_receipt_id="rcpt_1",
        principal_kind="wb_user",
        principal_id="u1",
        transport_channel=TransportChannel.API,
    )
    updated = await attempt_store.update_lifecycle(
        attempt.attempt_id,
        lifecycle_state=ApplyAttemptLifecycleState.TERMINAL,
        terminal_status=ApplyTerminalStatus.VERIFIED,
    )
    assert updated is not None
    assert updated.lifecycle_state == ApplyAttemptLifecycleState.TERMINAL
