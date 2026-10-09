"""ApplyAuthorityService — single-PG-transaction campaign settings apply (Slice C)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TypeAlias

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.wb_sky_control_plane.apply.binding import binding_hint_mismatches
from app.modules.wb_sky_control_plane.apply.constants import APPLY_CONTRACT_VERSION
from app.modules.wb_sky_control_plane.apply.enums import (
    ApplyAttemptLifecycleState,
    ApplyReasonCode,
    ApplyTerminalStatus,
    DryRunReceiptLifecycleState,
    IdempotencyDecisionKind,
)
from app.modules.wb_sky_control_plane.apply.idempotency import (
    IdempotencyKey,
    build_idempotency_fingerprint,
    decide_idempotency,
)
from app.modules.wb_sky_control_plane.apply.models.context import ApplyInvocationContext
from app.modules.wb_sky_control_plane.apply.models.evidence import ApplyEvidenceV1
from app.modules.wb_sky_control_plane.apply.models.outcomes import ApplyOutcomeV1
from app.modules.wb_sky_control_plane.apply.models.request import ApplyRequestV1
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
from app.modules.wb_sky_control_plane.apply.receipt_lifecycle import (
    receipt_outcome_transition,
)
from app.modules.wb_sky_control_plane.apply.service.exceptions import (
    AmbiguousCommitAcknowledgementError,
    ApplyOutcomeRollback,
)
from app.modules.wb_sky_control_plane.apply.service.locking import lock_touched_adv_settings
from app.modules.wb_sky_control_plane.apply.service.post_write_verify import (
    reread_adv_settings_by_id,
    verify_plan_against_db_reread,
)
from app.modules.wb_sky_control_plane.apply.service.receipt_binding import (
    invalidate_on_binding_mismatch,
    receipt_binding_mismatch,
)
from app.modules.wb_sky_control_plane.apply.service.revalidation import (
    ApplyBindingMaterial,
    project_apply_binding_material,
)
from app.modules.wb_sky_control_plane.apply.service.test_hooks import ApplyServiceTestHooks
from app.modules.wb_sky_control_plane.apply.validation import unsupported_contract_version
from app.modules.wb_sky_control_plane.apply.writer.pg_campaign_settings_policy_v1 import (
    apply_plan_to_adv_settings,
)
from app.modules.wb_sky_control_plane.kernel.semantic_digest import compute_semantic_digest
from app.modules.wb_sky_control_plane.kernel.state_token import compute_state_token
from app.modules.wb_sky_control_plane.models.enums import DryRunStatus
from app.modules.wb_sky_control_plane.models.errors import ControlPlaneError
from app.modules.wb_sky_control_plane.models.plan import PlanV1
from app.modules.wb_sky_control_plane.ports.wb_read_port import WbPromotionV2ReadPort
from app.modules.wb_sky_control_plane.read.local_policy import (
    project_local_policy_from_adv_setting,
)

ApplySessionFactory: TypeAlias = async_sessionmaker[AsyncSession]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _reason_from_validation_errors(errors: list[ControlPlaneError]) -> ApplyReasonCode:
    codes = {err.code for err in errors}
    if "STATE_TOKEN_STALE" in codes or "STATE_TOKEN_MISSING" in codes:
        return ApplyReasonCode.STALE_STATE
    if "CAPABILITY_NOT_ELIGIBLE" in codes:
        return ApplyReasonCode.CAPABILITY_DRIFT
    return ApplyReasonCode.VALIDATION_REJECTED


def _rejected(
    *,
    reason: ApplyReasonCode,
    evidence: ApplyEvidenceV1 | None = None,
) -> ApplyOutcomeV1:
    return ApplyOutcomeV1(
        status=ApplyTerminalStatus.REJECTED,
        reason_code=reason,
        evidence=evidence,
    )


def _failed(reason: ApplyReasonCode) -> ApplyOutcomeV1:
    return ApplyOutcomeV1(
        status=ApplyTerminalStatus.FAILED,
        reason_code=reason,
        evidence=None,
    )


def _verified(evidence: ApplyEvidenceV1) -> ApplyOutcomeV1:
    return ApplyOutcomeV1(
        status=ApplyTerminalStatus.VERIFIED,
        reason_code=None,
        evidence=evidence,
    )


def _unknown_internal_commit() -> ApplyOutcomeV1:
    return ApplyOutcomeV1(
        status=ApplyTerminalStatus.UNKNOWN_INTERNAL_COMMIT,
        reason_code=None,
        evidence=None,
    )


async def _post_state_tokens_from_reread(
    request: ApplyRequestV1,
    material: ApplyBindingMaterial,
    adv_by_resource: dict[str, AdvSetting],
    session: AsyncSession,
) -> dict[str, str]:
    ops_by_resource: dict[str, set[str]] = {}
    for operation in request.changeset.operations:
        ops_by_resource.setdefault(operation.resource.resource_id, set()).add(
            operation.op
        )
    fresh_by_id = await reread_adv_settings_by_id(
        session, [row.id for row in adv_by_resource.values()]
    )
    tokens: dict[str, str] = {}
    for resource_id, snapshot in material.snapshots.items():
        row = adv_by_resource.get(resource_id)
        if row is None:
            continue
        fresh = fresh_by_id.get(row.id, row)
        snapshot = snapshot.model_copy(
            update={"local_policy": project_local_policy_from_adv_setting(fresh)}
        )
        target_ops = frozenset(ops_by_resource.get(resource_id, set()))
        token = compute_state_token(snapshot, target_op_kinds=target_ops)
        if token:
            tokens[resource_id] = token
    return tokens


class ApplyAuthorityService:
    """PG-only apply orchestration for bounded ChangeSetV1 policy operations."""

    def __init__(
        self,
        *,
        session_factory: ApplySessionFactory,
        wb_reader: WbPromotionV2ReadPort,
        test_hooks: ApplyServiceTestHooks | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._wb_reader = wb_reader
        self._hooks = test_hooks or ApplyServiceTestHooks()

    async def apply(
        self,
        request: ApplyRequestV1,
        context: ApplyInvocationContext,
    ) -> ApplyOutcomeV1:
        shop_id = request.scope_shop_id()
        authorized = context.is_authorized_for_shop(shop_id)
        if not authorized:
            return _rejected(reason=ApplyReasonCode.UNAUTHORIZED)

        if unsupported_contract_version(request) is not None:
            return _rejected(reason=ApplyReasonCode.VALIDATION_REJECTED)

        replay_outcome = await self._try_idempotent_replay(
            request,
            caller_authorized=True,
        )
        if replay_outcome is not None:
            return replay_outcome

        attempt_id = f"att_{uuid.uuid4().hex}"
        now = _utc_now()

        pre_claim = await self._pre_claim_committed(request, now=now)
        if pre_claim is not None:
            return pre_claim

        pending: ApplyOutcomeV1
        try:
            async with self._session_factory() as session:
                async with session.begin():
                    pending = await self._apply_fresh_in_authoritative_transaction(
                        session=session,
                        request=request,
                        context=context,
                        attempt_id=attempt_id,
                        now=now,
                    )
                    if pending.status != ApplyTerminalStatus.VERIFIED:
                        raise ApplyOutcomeRollback(pending)
                    if self._hooks.force_ambiguous_commit:
                        raise AmbiguousCommitAcknowledgementError()
        except ApplyOutcomeRollback as rollback:
            await self._post_authoritative_rollback_persistence(
                request=request,
                attempt_id=attempt_id,
                outcome=rollback.outcome,
            )
            return rollback.outcome
        except AmbiguousCommitAcknowledgementError:
            return await self._handle_ambiguous_commit(
                request=request,
                attempt_id=attempt_id,
            )

        return pending

    async def _try_idempotent_replay(
        self,
        request: ApplyRequestV1,
        *,
        caller_authorized: bool,
    ) -> ApplyOutcomeV1 | None:
        """Replay path: no WB reads, no capability/state-token revalidation."""
        shop_id = request.scope_shop_id()
        semantic_digest = compute_semantic_digest(request.changeset)

        async with self._session_factory() as session:
            receipt_store = PostgresDryRunReceiptStore(session)
            idem_store = PostgresIdempotencyStore(session)
            receipt = await receipt_store.get_by_id(request.dry_run_receipt_id)
            if receipt is None:
                return None

            if receipt.binding.scope.shop_id != shop_id:
                return _rejected(reason=ApplyReasonCode.RECEIPT_INVALID)
            if receipt.binding.changeset_id != request.changeset.changeset_id:
                return _rejected(reason=ApplyReasonCode.RECEIPT_INVALID)
            if receipt.binding.semantic_digest != semantic_digest:
                return _rejected(reason=ApplyReasonCode.CHANGESET_DIGEST_MISMATCH)

            hint_reason = binding_hint_mismatches(
                request.binding_hints,
                semantic_digest=receipt.binding.semantic_digest,
                preview_digest=receipt.binding.preview_digest,
            )
            if hint_reason is not None:
                return _rejected(reason=hint_reason)

            fingerprint = build_idempotency_fingerprint(
                apply_contract_version=request.contract_version,
                semantic_digest=receipt.binding.semantic_digest,
                preview_digest=receipt.binding.preview_digest,
            )
            idem_key = IdempotencyKey(
                shop_id=shop_id,
                idempotency_key=request.idempotency_key,
            )
            record_view = await idem_store.get_record_view(idem_key)
            decision = decide_idempotency(
                fingerprint=fingerprint,
                record=record_view,
                caller_authorized=caller_authorized,
            )
            if decision.kind == IdempotencyDecisionKind.REPLAY_CANDIDATE:
                if decision.reason_code == ApplyReasonCode.UNAUTHORIZED:
                    return _rejected(reason=ApplyReasonCode.UNAUTHORIZED)
                if decision.evidence is not None:
                    return _verified(decision.evidence)
            if decision.kind == IdempotencyDecisionKind.IN_PROGRESS:
                return _rejected(reason=ApplyReasonCode.APPLY_IN_PROGRESS)
            if decision.kind == IdempotencyDecisionKind.CONFLICT:
                return _rejected(reason=ApplyReasonCode.IDEMPOTENCY_CONFLICT)

        return None

    async def _pre_claim_committed(
        self,
        request: ApplyRequestV1,
        *,
        now: datetime,
    ) -> ApplyOutcomeV1 | None:
        """Committed gate: binding validation + durable receipt invalidation."""
        shop_id = request.scope_shop_id()
        async with self._session_factory() as session:
            async with session.begin():
                receipt_store = PostgresDryRunReceiptStore(session)
                material = await project_apply_binding_material(
                    request.changeset,
                    session=session,
                    wb_reader=self._wb_reader,
                )
                receipt = await receipt_store.get_by_id(request.dry_run_receipt_id)
                if receipt is None:
                    return _rejected(reason=ApplyReasonCode.RECEIPT_INVALID)
                if (
                    receipt.lifecycle_state
                    == DryRunReceiptLifecycleState.BLOCKED_RECONCILIATION
                ):
                    return _rejected(
                        reason=ApplyReasonCode.RECEIPT_BLOCKED_RECONCILIATION
                    )
                if receipt.binding.scope.shop_id != shop_id:
                    return _rejected(reason=ApplyReasonCode.RECEIPT_INVALID)
                if receipt.binding.changeset_id != request.changeset.changeset_id:
                    return _rejected(reason=ApplyReasonCode.RECEIPT_INVALID)
                if receipt.binding.semantic_digest != material.semantic_digest:
                    return _rejected(reason=ApplyReasonCode.CHANGESET_DIGEST_MISMATCH)
                if receipt.binding.dry_run_status != DryRunStatus.OK:
                    return _rejected(reason=ApplyReasonCode.RECEIPT_INVALID)
                if receipt.is_terminal() or not receipt.is_usable_for_apply(now=now):
                    return _rejected(reason=ApplyReasonCode.RECEIPT_INVALID)

                mismatch = receipt_binding_mismatch(receipt, material)
                if mismatch is not None:
                    if invalidate_on_binding_mismatch(mismatch):
                        _ = await receipt_store.transition_lifecycle(
                            request.dry_run_receipt_id,
                            DryRunReceiptLifecycleState.INVALIDATED,
                        )
                    if mismatch in {
                        ApplyReasonCode.WRITER_REJECTED,
                        ApplyReasonCode.VERIFICATION_MISMATCH,
                    }:
                        return _failed(mismatch)
                    return _rejected(reason=mismatch)
        return None

    async def _post_authoritative_rollback_persistence(
        self,
        *,
        request: ApplyRequestV1,
        attempt_id: str,
        outcome: ApplyOutcomeV1,
    ) -> None:
        """Durable receipt/idempotency effects after authoritative txn rollback."""
        if outcome.reason_code is None:
            return
        shop_id = request.scope_shop_id()
        idem_key = IdempotencyKey(
            shop_id=shop_id,
            idempotency_key=request.idempotency_key,
        )
        async with self._session_factory() as session:
            async with session.begin():
                receipt_store = PostgresDryRunReceiptStore(session)
                idempotency_store = PostgresIdempotencyStore(session)
                receipt = await receipt_store.get_by_id(request.dry_run_receipt_id)
                if receipt is None:
                    return
                receipt_state = receipt.lifecycle_state
                terminal = outcome.status
                reason = outcome.reason_code
                new_receipt_state = receipt_outcome_transition(
                    receipt_state,
                    terminal_status=terminal,
                    reason_code=reason,
                )
                if invalidate_on_binding_mismatch(reason):
                    _ = await receipt_store.transition_lifecycle(
                        request.dry_run_receipt_id,
                        DryRunReceiptLifecycleState.INVALIDATED,
                    )
                elif new_receipt_state == DryRunReceiptLifecycleState.ISSUED:
                    _ = await receipt_store.release_claim(request.dry_run_receipt_id)
                elif new_receipt_state != receipt_state:
                    _ = await receipt_store.transition_lifecycle(
                        request.dry_run_receipt_id,
                        new_receipt_state,
                    )
                await idempotency_store.release_in_flight(
                    idem_key, attempt_id=attempt_id
                )

    async def _apply_fresh_in_authoritative_transaction(
        self,
        *,
        session: AsyncSession,
        request: ApplyRequestV1,
        context: ApplyInvocationContext,
        attempt_id: str,
        now: datetime,
    ) -> ApplyOutcomeV1:
        receipt_store = PostgresDryRunReceiptStore(session)
        idempotency_store = PostgresIdempotencyStore(session)
        evidence_store = PostgresApplyEvidenceStore(session)
        attempt_store = PostgresApplyAttemptStore(session)

        shop_id = request.scope_shop_id()
        receipt_id = request.dry_run_receipt_id
        receipt = await receipt_store.get_by_id(receipt_id)
        if receipt is None:
            return _rejected(reason=ApplyReasonCode.RECEIPT_INVALID)

        fingerprint = build_idempotency_fingerprint(
            apply_contract_version=request.contract_version,
            semantic_digest=receipt.binding.semantic_digest,
            preview_digest=receipt.binding.preview_digest,
        )
        idem_key = IdempotencyKey(
            shop_id=shop_id,
            idempotency_key=request.idempotency_key,
        )

        if receipt.binding.dry_run_status != DryRunStatus.OK:
            return _rejected(reason=ApplyReasonCode.RECEIPT_INVALID)
        if receipt.is_terminal() or not receipt.is_usable_for_apply(now=now):
            return _rejected(reason=ApplyReasonCode.RECEIPT_INVALID)

        _ = await attempt_store.insert(
            attempt_id=attempt_id,
            shop_id=idem_key.shop_id,
            idempotency_key=idem_key.idempotency_key,
            dry_run_receipt_id=receipt_id,
            principal_kind=context.principal_ref.kind,
            principal_id=context.principal_ref.principal_id,
            transport_channel=context.transport_channel,
            lifecycle_state=ApplyAttemptLifecycleState.CLAIMING,
        )

        claim_idem = await idempotency_store.try_claim(
            idem_key,
            fingerprint=fingerprint,
            attempt_id=attempt_id,
        )
        if claim_idem == IdempotencyClaimResult.CONFLICT:
            return _rejected(reason=ApplyReasonCode.IDEMPOTENCY_CONFLICT)
        if claim_idem == IdempotencyClaimResult.IN_PROGRESS:
            return _rejected(reason=ApplyReasonCode.APPLY_IN_PROGRESS)
        if claim_idem == IdempotencyClaimResult.REPLAY_READY:
            view = await idempotency_store.get_record_view(idem_key)
            if view and view.evidence is not None:
                return _verified(view.evidence)

        claim_receipt = await receipt_store.claim(receipt_id, now=now)
        if claim_receipt != ReceiptClaimResult.CLAIMED:
            return _rejected(reason=ApplyReasonCode.RECEIPT_INVALID)

        adv_by_resource, _registry = await lock_touched_adv_settings(
            request.changeset,
            session=session,
        )
        if len(adv_by_resource) != len(
            {op.resource.resource_id for op in request.changeset.operations}
        ):
            return _rejected(reason=ApplyReasonCode.VALIDATION_REJECTED)

        locked_material = await project_apply_binding_material(
            request.changeset,
            session=session,
            wb_reader=self._wb_reader,
        )
        locked_mismatch = receipt_binding_mismatch(receipt, locked_material)
        if locked_mismatch is not None:
            if locked_mismatch in {
                ApplyReasonCode.WRITER_REJECTED,
                ApplyReasonCode.VERIFICATION_MISMATCH,
            }:
                return _failed(locked_mismatch)
            return _rejected(reason=locked_mismatch)

        plan = locked_material.plan
        assert plan is not None
        try:
            apply_plan_to_adv_settings(
                plan,
                adv_by_resource=adv_by_resource,
            )
        except (ValueError, LookupError):
            return _failed(ApplyReasonCode.WRITER_REJECTED)

        await session.flush()

        verified_ok = await self._run_post_write_verify(session, plan, adv_by_resource)
        if not verified_ok:
            return _failed(ApplyReasonCode.VERIFICATION_MISMATCH)

        post_tokens = await _post_state_tokens_from_reread(
            request,
            locked_material,
            adv_by_resource,
            session,
        )
        evidence_id = f"ev_{uuid.uuid4().hex}"
        evidence = ApplyEvidenceV1(
            evidence_id=evidence_id,
            scope=request.changeset.scope,
            changeset_id=request.changeset.changeset_id,
            dry_run_receipt_id=receipt_id,
            idempotency_key=request.idempotency_key,
            apply_contract_version=APPLY_CONTRACT_VERSION,
            semantic_digest=receipt.binding.semantic_digest,
            preview_digest=receipt.binding.preview_digest,
            post_state_tokens=post_tokens,
            terminal_status=ApplyTerminalStatus.VERIFIED,
            committed_at=now,
        )
        try:
            if self._hooks.evidence_insert_override is not None:
                _ = await self._hooks.evidence_insert_override(evidence)
            elif self._hooks.force_evidence_insert_fail:
                raise RuntimeError("evidence insert forced failure")
            else:
                _ = await evidence_store.insert(evidence)
        except Exception:
            return _failed(ApplyReasonCode.TRANSACTION_ROLLED_BACK)

        await idempotency_store.finalize_verified(
            idem_key,
            evidence_id=evidence_id,
            attempt_id=attempt_id,
        )
        _ = await receipt_store.transition_lifecycle(
            receipt_id,
            DryRunReceiptLifecycleState.CONSUMED,
        )
        _ = await attempt_store.update_lifecycle(
            attempt_id,
            lifecycle_state=ApplyAttemptLifecycleState.TERMINAL,
            terminal_status=ApplyTerminalStatus.VERIFIED,
        )
        return _verified(evidence)

    async def _run_post_write_verify(
        self,
        session: AsyncSession,
        plan: PlanV1,
        adv_by_resource: dict[str, AdvSetting],
    ) -> bool:
        if self._hooks.force_post_write_verify_fail:
            return False
        if self._hooks.post_write_verify_override is not None:
            return await self._hooks.post_write_verify_override(
                session, plan, adv_by_resource
            )
        return await verify_plan_against_db_reread(
            session, plan, adv_by_resource=adv_by_resource
        )

    async def _handle_ambiguous_commit(
        self,
        *,
        request: ApplyRequestV1,
        attempt_id: str,
    ) -> ApplyOutcomeV1:
        """Reconcile unknown COMMIT: never return VERIFIED without durable proof."""
        shop_id = request.scope_shop_id()
        idem_key = IdempotencyKey(
            shop_id=shop_id,
            idempotency_key=request.idempotency_key,
        )
        async with self._session_factory() as session:
            async with session.begin():
                idem_store = PostgresIdempotencyStore(session)
                receipt_store = PostgresDryRunReceiptStore(session)
                view = await idem_store.get_record_view(idem_key)
                if (
                    view is not None
                    and view.terminal_status == ApplyTerminalStatus.VERIFIED
                    and view.evidence is not None
                ):
                    _ = await receipt_store.transition_lifecycle(
                        request.dry_run_receipt_id,
                        DryRunReceiptLifecycleState.BLOCKED_RECONCILIATION,
                    )
                    return _unknown_internal_commit()
                _ = await receipt_store.transition_lifecycle(
                    request.dry_run_receipt_id,
                    DryRunReceiptLifecycleState.BLOCKED_RECONCILIATION,
                )
        return _unknown_internal_commit()
