"""PostgreSQL repositories — session passed in for Slice C single-txn apply."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.wb_sky_control_plane.apply.enums import (
    ApplyAttemptLifecycleState,
    ApplyReasonCode,
    ApplyTerminalStatus,
    DryRunReceiptLifecycleState,
    TransportChannel,
)
from app.modules.wb_sky_control_plane.apply.idempotency import (
    IdempotencyKey,
    IdempotencyRecordView,
)
from app.modules.wb_sky_control_plane.apply.models.attempt import ApplyAttemptRecordV1
from app.modules.wb_sky_control_plane.apply.models.evidence import ApplyEvidenceV1
from app.modules.wb_sky_control_plane.apply.models.receipt import (
    DryRunReceiptBindingV1,
    DryRunReceiptV1,
)
from app.modules.wb_sky_control_plane.apply.persistence.mappers import (
    attempt_row_to_domain,
    evidence_row_to_domain,
    receipt_row_to_domain,
)
from app.modules.wb_sky_control_plane.apply.persistence.models import (
    WbSkyApplyAttemptRecord,
    WbSkyApplyDryRunReceipt,
    WbSkyApplyEvidence,
    WbSkyApplyIdempotencyLedger,
)
from app.modules.wb_sky_control_plane.apply.persistence.results import (
    IdempotencyClaimResult,
    ReceiptClaimResult,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PostgresDryRunReceiptStore:
    """Durable dry-run receipt store with conditional claim."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_issued(
        self,
        binding: DryRunReceiptBindingV1,
        *,
        lifecycle_state: DryRunReceiptLifecycleState = DryRunReceiptLifecycleState.ISSUED,
    ) -> DryRunReceiptV1:
        """Insert server-issued receipt; binding fields immutable thereafter."""
        row = WbSkyApplyDryRunReceipt(
            receipt_id=binding.receipt_id,
            lifecycle_state=lifecycle_state.value,
            issued_at=binding.issued_at,
            expires_at=binding.expires_at,
            scope_provider=binding.scope.provider,
            shop_id=binding.scope.shop_id,
            changeset_id=binding.changeset_id,
            semantic_digest=binding.semantic_digest,
            preview_digest=binding.preview_digest,
            state_tokens=dict(binding.state_tokens),
            capability_projection_digest=binding.capability_projection_digest,
            dry_run_status=binding.dry_run_status.value,
        )
        self._session.add(row)
        await self._session.flush()
        return receipt_row_to_domain(row)

    async def get_by_id(self, receipt_id: str) -> DryRunReceiptV1 | None:
        result = await self._session.execute(
            select(WbSkyApplyDryRunReceipt).where(
                WbSkyApplyDryRunReceipt.receipt_id == receipt_id
            )
        )
        row = result.scalar_one_or_none()
        return receipt_row_to_domain(row) if row else None

    async def claim(
        self,
        receipt_id: str,
        *,
        now: datetime,
    ) -> ReceiptClaimResult:
        """ISSUED → CLAIMED when not expired (row-level conditional update)."""
        row = await self._load_row(receipt_id)
        if row is None:
            return ReceiptClaimResult.NOT_FOUND
        state = DryRunReceiptLifecycleState(row.lifecycle_state)
        if state == DryRunReceiptLifecycleState.BLOCKED_RECONCILIATION:
            return ReceiptClaimResult.BLOCKED_RECONCILIATION
        if state in {
            DryRunReceiptLifecycleState.INVALIDATED,
            DryRunReceiptLifecycleState.CONSUMED,
            DryRunReceiptLifecycleState.EXPIRED,
        }:
            return ReceiptClaimResult.TERMINAL
        if now >= row.expires_at:
            row.lifecycle_state = DryRunReceiptLifecycleState.EXPIRED.value
            await self._session.flush()
            return ReceiptClaimResult.EXPIRED
        if state == DryRunReceiptLifecycleState.CLAIMED:
            return ReceiptClaimResult.ALREADY_CLAIMED
        if state != DryRunReceiptLifecycleState.ISSUED:
            return ReceiptClaimResult.TERMINAL

        row.lifecycle_state = DryRunReceiptLifecycleState.CLAIMED.value
        await self._session.flush()
        return ReceiptClaimResult.CLAIMED

    async def transition_lifecycle(
        self,
        receipt_id: str,
        new_state: DryRunReceiptLifecycleState,
    ) -> DryRunReceiptV1 | None:
        """Lifecycle-only mutation; ABA: INVALIDATED is sticky.

        Receipt claim (ISSUED→CLAIMED) MUST use ``claim()`` so expiry is enforced.
        """
        if new_state == DryRunReceiptLifecycleState.CLAIMED:
            raise ValueError("receipt claim must use claim()")
        row = await self._load_row(receipt_id)
        if row is None:
            return None
        current = DryRunReceiptLifecycleState(row.lifecycle_state)
        if current == DryRunReceiptLifecycleState.INVALIDATED:
            return receipt_row_to_domain(row)
        if current in {
            DryRunReceiptLifecycleState.CONSUMED,
            DryRunReceiptLifecycleState.EXPIRED,
            DryRunReceiptLifecycleState.BLOCKED_RECONCILIATION,
        } and new_state != current:
            return receipt_row_to_domain(row)
        row.lifecycle_state = new_state.value
        await self._session.flush()
        return receipt_row_to_domain(row)

    async def _load_row(self, receipt_id: str) -> WbSkyApplyDryRunReceipt | None:
        result = await self._session.execute(
            select(WbSkyApplyDryRunReceipt)
            .where(WbSkyApplyDryRunReceipt.receipt_id == receipt_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()


class PostgresIdempotencyStore:
    """Durable idempotency ledger with unique (shop_id, idempotency_key)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_record_view(self, key: IdempotencyKey) -> IdempotencyRecordView | None:
        row = await self._get_row(key)
        if row is None:
            return None
        evidence = None
        if row.evidence_id:
            ev_row = await self._session.execute(
                select(WbSkyApplyEvidence).where(
                    WbSkyApplyEvidence.evidence_id == row.evidence_id
                )
            )
            ev = ev_row.scalar_one_or_none()
            if ev is not None:
                evidence = evidence_row_to_domain(ev)
        terminal = (
            ApplyTerminalStatus(row.terminal_status) if row.terminal_status else None
        )
        return IdempotencyRecordView(
            fingerprint=row.fingerprint,
            terminal_status=terminal,
            in_flight=row.in_flight,
            evidence=evidence,
        )

    async def try_claim(
        self,
        key: IdempotencyKey,
        *,
        fingerprint: str,
        attempt_id: str,
    ) -> IdempotencyClaimResult:
        row = await self._get_row_for_update(key)
        if row is None:
            ledger = WbSkyApplyIdempotencyLedger(
                shop_id=key.shop_id,
                idempotency_key=key.idempotency_key,
                fingerprint=fingerprint,
                in_flight=True,
                attempt_id=attempt_id,
            )
            try:
                async with self._session.begin_nested():
                    self._session.add(ledger)
                    await self._session.flush()
                return IdempotencyClaimResult.CLAIMED
            except IntegrityError:
                row = await self._get_row_for_update(key)
                if row is None:
                    raise

        if row.in_flight:
            if row.fingerprint == fingerprint:
                return IdempotencyClaimResult.IN_PROGRESS
            return IdempotencyClaimResult.CONFLICT
        if row.fingerprint != fingerprint:
            return IdempotencyClaimResult.CONFLICT
        if row.terminal_status == ApplyTerminalStatus.VERIFIED.value:
            return IdempotencyClaimResult.REPLAY_READY
        row.in_flight = True
        row.attempt_id = attempt_id
        await self._session.flush()
        return IdempotencyClaimResult.CLAIMED

    async def finalize_verified(
        self,
        key: IdempotencyKey,
        *,
        evidence_id: str,
    ) -> None:
        row = await self._get_row_for_update(key)
        if row is None:
            raise LookupError("idempotency row missing on finalize")
        row.in_flight = False
        row.terminal_status = ApplyTerminalStatus.VERIFIED.value
        row.evidence_id = evidence_id
        await self._session.flush()

    async def release_in_flight(self, key: IdempotencyKey) -> None:
        row = await self._get_row_for_update(key)
        if row is None:
            return
        row.in_flight = False
        await self._session.flush()

    async def _get_row(self, key: IdempotencyKey) -> WbSkyApplyIdempotencyLedger | None:
        result = await self._session.execute(
            select(WbSkyApplyIdempotencyLedger).where(
                WbSkyApplyIdempotencyLedger.shop_id == key.shop_id,
                WbSkyApplyIdempotencyLedger.idempotency_key == key.idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def _get_row_for_update(
        self, key: IdempotencyKey
    ) -> WbSkyApplyIdempotencyLedger | None:
        result = await self._session.execute(
            select(WbSkyApplyIdempotencyLedger)
            .where(
                WbSkyApplyIdempotencyLedger.shop_id == key.shop_id,
                WbSkyApplyIdempotencyLedger.idempotency_key == key.idempotency_key,
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()


class PostgresApplyEvidenceStore:
    """Insert-only evidence persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(self, evidence: ApplyEvidenceV1) -> ApplyEvidenceV1:
        row = WbSkyApplyEvidence(
            evidence_id=evidence.evidence_id,
            scope_provider=evidence.scope.provider,
            shop_id=evidence.scope.shop_id,
            changeset_id=evidence.changeset_id,
            dry_run_receipt_id=evidence.dry_run_receipt_id,
            idempotency_key=evidence.idempotency_key,
            apply_contract_version=evidence.apply_contract_version,
            semantic_digest=evidence.semantic_digest,
            preview_digest=evidence.preview_digest,
            post_state_tokens=dict(evidence.post_state_tokens),
            terminal_status=evidence.terminal_status.value,
            committed_at=evidence.committed_at,
        )
        self._session.add(row)
        await self._session.flush()
        return evidence

    async def get_by_id(self, evidence_id: str) -> ApplyEvidenceV1 | None:
        result = await self._session.execute(
            select(WbSkyApplyEvidence).where(
                WbSkyApplyEvidence.evidence_id == evidence_id
            )
        )
        row = result.scalar_one_or_none()
        return evidence_row_to_domain(row) if row else None


class PostgresApplyAttemptStore:
    """Mutable attempt lifecycle rows."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(
        self,
        *,
        attempt_id: str,
        shop_id: str,
        idempotency_key: str,
        dry_run_receipt_id: str,
        principal_kind: str,
        principal_id: str,
        transport_channel: TransportChannel,
        lifecycle_state: ApplyAttemptLifecycleState = ApplyAttemptLifecycleState.RECEIVED,
    ) -> ApplyAttemptRecordV1:
        now = _utc_now()
        row = WbSkyApplyAttemptRecord(
            attempt_id=attempt_id,
            shop_id=shop_id,
            idempotency_key=idempotency_key,
            dry_run_receipt_id=dry_run_receipt_id,
            principal_kind=principal_kind,
            principal_id=principal_id,
            transport_channel=transport_channel.value,
            lifecycle_state=lifecycle_state.value,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return attempt_row_to_domain(row)

    async def update_lifecycle(
        self,
        attempt_id: str,
        *,
        lifecycle_state: ApplyAttemptLifecycleState,
        terminal_status: ApplyTerminalStatus | None = None,
        reason_code: ApplyReasonCode | None = None,
    ) -> ApplyAttemptRecordV1 | None:
        result = await self._session.execute(
            select(WbSkyApplyAttemptRecord)
            .where(WbSkyApplyAttemptRecord.attempt_id == attempt_id)
            .with_for_update()
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.lifecycle_state = lifecycle_state.value
        row.terminal_status = terminal_status.value if terminal_status else None
        row.reason_code = reason_code.value if reason_code else None
        row.updated_at = _utc_now()
        await self._session.flush()
        return attempt_row_to_domain(row)
