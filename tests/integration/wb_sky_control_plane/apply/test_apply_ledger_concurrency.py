"""Real PostgreSQL concurrency evidence for Apply ledger (Slice B)."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.modules.wb_sky_control_plane.apply.constants import APPLY_CONTRACT_VERSION
from app.modules.wb_sky_control_plane.apply.enums import (
    ApplyTerminalStatus,
    DryRunReceiptLifecycleState,
)
from app.modules.wb_sky_control_plane.apply.idempotency import IdempotencyKey
from app.modules.wb_sky_control_plane.apply.models.evidence import ApplyEvidenceV1
from app.modules.wb_sky_control_plane.apply.models.receipt import DryRunReceiptBindingV1
from app.modules.wb_sky_control_plane.apply.persistence.models import (
    WbSkyApplyDryRunReceipt,
    WbSkyApplyIdempotencyLedger,
)
from app.modules.wb_sky_control_plane.apply.persistence.postgres_stores import (
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


def _binding(
    receipt_id: str,
    *,
    shop_id: str,
    expires_at: datetime,
) -> DryRunReceiptBindingV1:
    now = datetime.now(timezone.utc)
    return DryRunReceiptBindingV1(
        receipt_id=receipt_id,
        issued_at=now,
        expires_at=expires_at,
        scope=LogicalScopeV1(shop_id=shop_id),
        changeset_id="cs_1",
        semantic_digest="sd1_x",
        preview_digest="pd1_x",
        state_tokens={"cmp_a": "st1_a"},
        capability_projection_digest="cpd1_x",
        dry_run_status=DryRunStatus.OK,
    )


@pytest.mark.destructive_local
async def test_receipt_concurrent_claim_exactly_one_owner(
    async_engine: AsyncEngine,
) -> None:
    maker = async_sessionmaker(async_engine, expire_on_commit=False)
    rid = f"rcpt_{uuid.uuid4().hex}"
    now = datetime.now(timezone.utc)
    async with maker() as session:
        async with session.begin():
            await PostgresDryRunReceiptStore(session).insert_issued(
                _binding(
                    rid,
                    shop_id=f"shop_{uuid.uuid4().hex[:6]}",
                    expires_at=now + timedelta(hours=1),
                )
            )

    async def contender() -> ReceiptClaimResult:
        async with maker() as session:
            async with session.begin():
                return await PostgresDryRunReceiptStore(session).claim(
                    rid, now=now
                )

    results = await asyncio.wait_for(
        asyncio.gather(contender(), contender()), timeout=30.0
    )
    assert results.count(ReceiptClaimResult.CLAIMED) == 1
    assert results.count(ReceiptClaimResult.ALREADY_CLAIMED) == 1


@pytest.mark.destructive_local
async def test_idempotency_concurrent_first_insert_same_fingerprint(
    async_engine: AsyncEngine,
) -> None:
    maker = async_sessionmaker(async_engine, expire_on_commit=False)
    shop = f"shop_{uuid.uuid4().hex[:8]}"
    key = IdempotencyKey(shop_id=shop, idempotency_key="race_key")

    async def contender(attempt_suffix: str) -> IdempotencyClaimResult:
        async with maker() as session:
            async with session.begin():
                return await PostgresIdempotencyStore(session).try_claim(
                    key,
                    fingerprint="fp_same",
                    attempt_id=f"att_{attempt_suffix}",
                )

    results = await asyncio.wait_for(
        asyncio.gather(contender("a"), contender("b")), timeout=30.0
    )
    assert results.count(IdempotencyClaimResult.CLAIMED) == 1
    assert results.count(IdempotencyClaimResult.IN_PROGRESS) == 1

    async with maker() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(WbSkyApplyIdempotencyLedger)
            .where(
                WbSkyApplyIdempotencyLedger.shop_id == shop,
                WbSkyApplyIdempotencyLedger.idempotency_key == "race_key",
            )
        )
        assert count == 1


@pytest.mark.destructive_local
async def test_idempotency_concurrent_first_insert_different_fingerprint(
    async_engine: AsyncEngine,
) -> None:
    maker = async_sessionmaker(async_engine, expire_on_commit=False)
    shop = f"shop_{uuid.uuid4().hex[:8]}"
    key = IdempotencyKey(shop_id=shop, idempotency_key="race_key2")

    async def contender(fp: str, suffix: str) -> IdempotencyClaimResult:
        async with maker() as session:
            async with session.begin():
                return await PostgresIdempotencyStore(session).try_claim(
                    key, fingerprint=fp, attempt_id=f"att_{suffix}"
                )

    results = await asyncio.wait_for(
        asyncio.gather(contender("fp_a", "a"), contender("fp_b", "b")),
        timeout=30.0,
    )
    assert results.count(IdempotencyClaimResult.CLAIMED) == 1
    assert results.count(IdempotencyClaimResult.CONFLICT) == 1


@pytest.mark.destructive_local
async def test_expired_receipt_claim_sets_expired_not_claimed(
    async_engine: AsyncEngine,
) -> None:
    maker = async_sessionmaker(async_engine, expire_on_commit=False)
    rid = f"rcpt_{uuid.uuid4().hex}"
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    async with maker() as session:
        async with session.begin():
            await PostgresDryRunReceiptStore(session).insert_issued(
                _binding(
                    rid,
                    shop_id=f"shop_{uuid.uuid4().hex[:6]}",
                    expires_at=past,
                )
            )

    async with maker() as session:
        async with session.begin():
            result = await PostgresDryRunReceiptStore(session).claim(
                rid, now=datetime.now(timezone.utc)
            )
            assert result == ReceiptClaimResult.EXPIRED

    async with maker() as session:
        async with session.begin():
            again = await PostgresDryRunReceiptStore(session).claim(
                rid, now=datetime.now(timezone.utc)
            )
            assert again == ReceiptClaimResult.TERMINAL
            loaded = await PostgresDryRunReceiptStore(session).get_by_id(rid)
            assert loaded is not None
            assert loaded.lifecycle_state == DryRunReceiptLifecycleState.EXPIRED


@pytest.mark.destructive_local
async def test_release_claim_returns_to_issued(async_engine: AsyncEngine) -> None:
    maker = async_sessionmaker(async_engine, expire_on_commit=False)
    rid = f"rcpt_{uuid.uuid4().hex}"
    now = datetime.now(timezone.utc)
    async with maker() as session:
        async with session.begin():
            store = PostgresDryRunReceiptStore(session)
            await store.insert_issued(
                _binding(
                    rid,
                    shop_id=f"shop_{uuid.uuid4().hex[:6]}",
                    expires_at=now + timedelta(hours=1),
                )
            )
            assert await store.claim(rid, now=now) == ReceiptClaimResult.CLAIMED
            released = await store.release_claim(rid)
            assert released is not None
            assert released.lifecycle_state == DryRunReceiptLifecycleState.ISSUED


@pytest.mark.destructive_local
async def test_ledger_rollback_leaves_no_terminal_state(
    async_engine: AsyncEngine,
) -> None:
    maker = async_sessionmaker(async_engine, expire_on_commit=False)
    rid = f"rcpt_{uuid.uuid4().hex}"
    shop = f"shop_{uuid.uuid4().hex[:8]}"
    key = IdempotencyKey(shop_id=shop, idempotency_key="rb_key")
    now = datetime.now(timezone.utc)

    async with maker() as session:
        trans = await session.begin()
        receipt_store = PostgresDryRunReceiptStore(session)
        idem_store = PostgresIdempotencyStore(session)
        await receipt_store.insert_issued(
            _binding(rid, shop_id=shop, expires_at=now + timedelta(hours=1))
        )
        await idem_store.try_claim(key, fingerprint="fp1", attempt_id="att_rb")
        await receipt_store.claim(rid, now=now)
        await trans.rollback()

    async with maker() as session:
        async with session.begin():
            loaded = await PostgresDryRunReceiptStore(session).get_by_id(rid)
            assert loaded is None
            count = await session.scalar(
                select(func.count())
                .select_from(WbSkyApplyIdempotencyLedger)
                .where(
                    WbSkyApplyIdempotencyLedger.shop_id == shop,
                    WbSkyApplyIdempotencyLedger.idempotency_key == "rb_key",
                )
            )
            assert count == 0


@pytest.mark.destructive_local
async def test_verified_replay_ready_after_commit(async_engine: AsyncEngine) -> None:
    maker = async_sessionmaker(async_engine, expire_on_commit=False)
    shop = f"shop_{uuid.uuid4().hex[:8]}"
    key = IdempotencyKey(shop_id=shop, idempotency_key="replay_key")
    eid = f"ev_{uuid.uuid4().hex}"

    async with maker() as session:
        async with session.begin():
            idem = PostgresIdempotencyStore(session)
            assert (
                await idem.try_claim(key, fingerprint="fp_r", attempt_id="att_1")
                == IdempotencyClaimResult.CLAIMED
            )
            await PostgresApplyEvidenceStore(session).insert(
                ApplyEvidenceV1(
                    evidence_id=eid,
                    scope=LogicalScopeV1(shop_id=shop),
                    changeset_id="cs_1",
                    dry_run_receipt_id="rcpt_1",
                    idempotency_key="replay_key",
                    apply_contract_version=APPLY_CONTRACT_VERSION,
                    semantic_digest="sd1_x",
                    preview_digest="pd1_x",
                    terminal_status=ApplyTerminalStatus.VERIFIED,
                    committed_at=datetime.now(timezone.utc),
                )
            )
            await idem.finalize_verified(
                key, evidence_id=eid, attempt_id="att_1"
            )

    async with maker() as session:
        async with session.begin():
            replay = await PostgresIdempotencyStore(session).try_claim(
                key, fingerprint="fp_r", attempt_id="att_2"
            )
            assert replay == IdempotencyClaimResult.REPLAY_READY
            view = await PostgresIdempotencyStore(session).get_record_view(key)
            assert view is not None
            assert view.evidence is not None
            assert view.evidence.evidence_id == eid


@pytest.mark.destructive_local
async def test_consumed_receipt_claim_is_terminal(async_engine: AsyncEngine) -> None:
    maker = async_sessionmaker(async_engine, expire_on_commit=False)
    rid = f"rcpt_{uuid.uuid4().hex}"
    now = datetime.now(timezone.utc)
    async with maker() as session:
        async with session.begin():
            store = PostgresDryRunReceiptStore(session)
            await store.insert_issued(
                _binding(
                    rid,
                    shop_id=f"shop_{uuid.uuid4().hex[:6]}",
                    expires_at=now + timedelta(hours=1),
                )
            )
            await store.claim(rid, now=now)
            await store.transition_lifecycle(
                rid, DryRunReceiptLifecycleState.CONSUMED
            )

    async with maker() as session:
        async with session.begin():
            result = await PostgresDryRunReceiptStore(session).claim(
                rid, now=now
            )
            assert result == ReceiptClaimResult.TERMINAL


@pytest.mark.destructive_local
async def test_idempotency_wrong_attempt_cannot_release(
    async_engine: AsyncEngine,
) -> None:
    maker = async_sessionmaker(async_engine, expire_on_commit=False)
    shop = f"shop_{uuid.uuid4().hex[:8]}"
    key = IdempotencyKey(shop_id=shop, idempotency_key="own_key")
    async with maker() as session:
        async with session.begin():
            store = PostgresIdempotencyStore(session)
            await store.try_claim(
                key, fingerprint="fp_o", attempt_id="att_owner"
            )
            with pytest.raises(PermissionError):
                await store.release_in_flight(key, attempt_id="att_intruder")
