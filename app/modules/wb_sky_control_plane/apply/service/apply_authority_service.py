"""ApplyAuthorityService — single-PG-transaction campaign settings apply (Slice C)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

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
from app.modules.wb_sky_control_plane.apply.service.locking import lock_touched_adv_settings
from app.modules.wb_sky_control_plane.apply.service.revalidation import (
    ApplyBindingMaterial,
    project_apply_binding_material,
)
from app.modules.wb_sky_control_plane.apply.validation import unsupported_contract_version
from app.modules.wb_sky_control_plane.apply.writer.pg_campaign_settings_policy_v1 import (
    apply_plan_to_adv_settings,
)
from app.modules.wb_sky_control_plane.kernel.state_token import compute_state_token
from app.modules.wb_sky_control_plane.models.enums import DryRunStatus
from app.modules.wb_sky_control_plane.models.errors import ControlPlaneError
from app.modules.wb_sky_control_plane.models.plan import PlanV1
from app.modules.wb_sky_control_plane.ports.wb_read_port import WbPromotionV2ReadPort
from app.modules.wb_sky_control_plane.read.local_policy import (
    project_local_policy_from_adv_setting,
)

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _field_from_path(field_path: str) -> str:
    return field_path.rsplit(".", maxsplit=1)[-1]


def _reason_from_validation_errors(errors: list[ControlPlaneError]) -> ApplyReasonCode:
    codes = {err.code for err in errors}
    if "STATE_TOKEN_STALE" in codes or "STATE_TOKEN_MISSING" in codes:
        return ApplyReasonCode.STALE_STATE
    if "CAPABILITY_NOT_ELIGIBLE" in codes:
        return ApplyReasonCode.CAPABILITY_DRIFT
    if any(
        c in codes
        for c in (
            "UNKNOWN_FIELD",
            "INVALID_VALUE",
            "RESOURCE_SNAPSHOT_MISSING",
            "MAPPING_NOT_OK",
            "EXPECTED_CURRENT_VALUE_MISMATCH",
        )
    ):
        return ApplyReasonCode.VALIDATION_REJECTED
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


def _post_state_tokens(
    changeset: ApplyRequestV1,
    material: ApplyBindingMaterial,
    adv_by_resource: dict[str, AdvSetting],
) -> dict[str, str]:
    ops_by_resource: dict[str, set[str]] = {}
    for operation in changeset.changeset.operations:
        ops_by_resource.setdefault(operation.resource.resource_id, set()).add(
            operation.op
        )
    tokens: dict[str, str] = {}
    for resource_id, snapshot in material.snapshots.items():
        row = adv_by_resource.get(resource_id)
        if row is not None:
            snapshot = snapshot.model_copy(
                update={
                    "local_policy": project_local_policy_from_adv_setting(row),
                }
            )
        target_ops = frozenset(ops_by_resource.get(resource_id, set()))
        token = compute_state_token(snapshot, target_op_kinds=target_ops)
        if token:
            tokens[resource_id] = token
    return tokens


def _verify_normalized_fields(
    plan: PlanV1,
    adv_by_resource: dict[str, AdvSetting],
) -> bool:
    for effect in plan.effects:
        if effect.is_no_op:
            continue
        row = adv_by_resource.get(effect.resource_id)
        if row is None:
            return False
        for change in effect.semantic_changes:
            field_name = _field_from_path(change.field_path)
            actual = getattr(row, field_name, None)
            if actual != change.normalized:
                return False
    return True


class ApplyAuthorityService:
    """PG-only apply orchestration for bounded ChangeSetV1 policy operations."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        wb_reader: WbPromotionV2ReadPort,
    ) -> None:
        self._session = session
        self._wb_reader = wb_reader
        self._receipt_store = PostgresDryRunReceiptStore(session)
        self._idempotency_store = PostgresIdempotencyStore(session)
        self._evidence_store = PostgresApplyEvidenceStore(session)
        self._attempt_store = PostgresApplyAttemptStore(session)

    async def apply(
        self,
        request: ApplyRequestV1,
        context: ApplyInvocationContext,
    ) -> ApplyOutcomeV1:
        shop_id = request.scope_shop_id()
        if not context.is_authorized_for_shop(shop_id):
            return _rejected(reason=ApplyReasonCode.UNAUTHORIZED)

        if unsupported_contract_version(request) is not None:
            return _rejected(reason=ApplyReasonCode.VALIDATION_REJECTED)

        material = await project_apply_binding_material(
            request.changeset,
            session=self._session,
            wb_reader=self._wb_reader,
        )
        hint_reason = binding_hint_mismatches(
            request.binding_hints,
            semantic_digest=material.semantic_digest,
            preview_digest=material.preview_digest,
        )
        if hint_reason is not None:
            return _rejected(reason=hint_reason)

        receipt = await self._receipt_store.get_by_id(request.dry_run_receipt_id)
        if receipt is None:
            return _rejected(reason=ApplyReasonCode.RECEIPT_INVALID)
        if receipt.binding.semantic_digest != material.semantic_digest:
            return _rejected(reason=ApplyReasonCode.CHANGESET_DIGEST_MISMATCH)

        fingerprint = build_idempotency_fingerprint(
            apply_contract_version=request.contract_version,
            semantic_digest=receipt.binding.semantic_digest,
            preview_digest=receipt.binding.preview_digest,
        )
        idem_key = IdempotencyKey(
            shop_id=shop_id,
            idempotency_key=request.idempotency_key,
        )
        record_view = await self._idempotency_store.get_record_view(idem_key)
        idem_decision = decide_idempotency(
            fingerprint=fingerprint,
            record=record_view,
            caller_authorized=True,
        )
        if idem_decision.kind == IdempotencyDecisionKind.REPLAY_CANDIDATE:
            if idem_decision.reason_code == ApplyReasonCode.UNAUTHORIZED:
                return _rejected(reason=ApplyReasonCode.UNAUTHORIZED)
            if idem_decision.evidence is not None:
                return _verified(idem_decision.evidence)
        if idem_decision.kind == IdempotencyDecisionKind.IN_PROGRESS:
            return _rejected(reason=ApplyReasonCode.APPLY_IN_PROGRESS)
        if idem_decision.kind == IdempotencyDecisionKind.CONFLICT:
            return _rejected(reason=ApplyReasonCode.IDEMPOTENCY_CONFLICT)

        attempt_id = f"att_{uuid.uuid4().hex}"
        now = _utc_now()

        txn_ctx = (
            self._session.begin_nested()
            if self._session.in_transaction()
            else self._session.begin()
        )
        async with txn_ctx:
            return await self._apply_fresh_transaction(
                request=request,
                context=context,
                material=material,
                fingerprint=fingerprint,
                idem_key=idem_key,
                attempt_id=attempt_id,
                now=now,
            )

    async def _apply_fresh_transaction(
        self,
        *,
        request: ApplyRequestV1,
        context: ApplyInvocationContext,
        material: ApplyBindingMaterial,
        fingerprint: str,
        idem_key: IdempotencyKey,
        attempt_id: str,
        now: datetime,
    ) -> ApplyOutcomeV1:
        receipt_id = request.dry_run_receipt_id
        receipt = await self._receipt_store.get_by_id(receipt_id)
        if receipt is None:
            return _rejected(reason=ApplyReasonCode.RECEIPT_INVALID)

        if (
            receipt.lifecycle_state
            == DryRunReceiptLifecycleState.BLOCKED_RECONCILIATION
        ):
            return _rejected(reason=ApplyReasonCode.RECEIPT_BLOCKED_RECONCILIATION)

        if receipt.binding.scope.shop_id != request.changeset.scope.shop_id:
            return _rejected(reason=ApplyReasonCode.RECEIPT_INVALID)
        if receipt.binding.changeset_id != request.changeset.changeset_id:
            return _rejected(reason=ApplyReasonCode.RECEIPT_INVALID)

        if material.status != DryRunStatus.OK or material.plan is None:
            reason = _reason_from_validation_errors(material.errors)
            return await self._abort_before_claim(
                receipt_id=receipt_id,
                reason=reason,
                receipt_state=receipt.lifecycle_state,
                invalidate=reason
                in {
                    ApplyReasonCode.STALE_STATE,
                    ApplyReasonCode.CAPABILITY_DRIFT,
                    ApplyReasonCode.PREVIEW_DIGEST_MISMATCH,
                },
            )

        if material.plan.is_no_op:
            return await self._abort_before_claim(
                receipt_id=receipt_id,
                reason=ApplyReasonCode.VALIDATION_REJECTED,
                receipt_state=receipt.lifecycle_state,
                invalidate=False,
            )

        if receipt.binding.preview_digest != material.preview_digest:
            return await self._abort_before_claim(
                receipt_id=receipt_id,
                reason=ApplyReasonCode.PREVIEW_DIGEST_MISMATCH,
                receipt_state=receipt.lifecycle_state,
                invalidate=True,
            )

        if (
            receipt.binding.capability_projection_digest
            != material.capability_projection_digest
        ):
            return await self._abort_before_claim(
                receipt_id=receipt_id,
                reason=ApplyReasonCode.CAPABILITY_DRIFT,
                receipt_state=receipt.lifecycle_state,
                invalidate=True,
            )

        for rid, bound_token in receipt.binding.state_tokens.items():
            if material.state_tokens.get(rid) != bound_token:
                return await self._abort_before_claim(
                    receipt_id=receipt_id,
                    reason=ApplyReasonCode.STALE_STATE,
                    receipt_state=receipt.lifecycle_state,
                    invalidate=True,
                )

        if receipt.binding.dry_run_status != DryRunStatus.OK:
            return _rejected(reason=ApplyReasonCode.RECEIPT_INVALID)

        if receipt.is_terminal() or not receipt.is_usable_for_apply(now=now):
            return _rejected(reason=ApplyReasonCode.RECEIPT_INVALID)

        _ = await self._attempt_store.insert(
            attempt_id=attempt_id,
            shop_id=idem_key.shop_id,
            idempotency_key=idem_key.idempotency_key,
            dry_run_receipt_id=receipt_id,
            principal_kind=context.principal_ref.kind,
            principal_id=context.principal_ref.principal_id,
            transport_channel=context.transport_channel,
            lifecycle_state=ApplyAttemptLifecycleState.CLAIMING,
        )

        claim_idem = await self._idempotency_store.try_claim(
            idem_key,
            fingerprint=fingerprint,
            attempt_id=attempt_id,
        )
        if claim_idem == IdempotencyClaimResult.CONFLICT:
            return await self._rollback_rejected(
                receipt_id=receipt_id,
                idem_key=idem_key,
                attempt_id=attempt_id,
                reason=ApplyReasonCode.IDEMPOTENCY_CONFLICT,
                receipt_state=receipt.lifecycle_state,
                invalidate=False,
            )
        if claim_idem == IdempotencyClaimResult.IN_PROGRESS:
            return await self._rollback_rejected(
                receipt_id=receipt_id,
                idem_key=idem_key,
                attempt_id=attempt_id,
                reason=ApplyReasonCode.APPLY_IN_PROGRESS,
                receipt_state=receipt.lifecycle_state,
                invalidate=False,
            )
        if claim_idem == IdempotencyClaimResult.REPLAY_READY:
            view = await self._idempotency_store.get_record_view(idem_key)
            if view and view.evidence is not None:
                return _verified(view.evidence)

        claim_receipt = await self._receipt_store.claim(receipt_id, now=now)
        if claim_receipt != ReceiptClaimResult.CLAIMED:
            return await self._rollback_rejected(
                receipt_id=receipt_id,
                idem_key=idem_key,
                attempt_id=attempt_id,
                reason=ApplyReasonCode.RECEIPT_INVALID,
                receipt_state=receipt.lifecycle_state,
                invalidate=False,
            )

        adv_by_resource, _registry = await lock_touched_adv_settings(
            request.changeset,
            session=self._session,
        )
        if len(adv_by_resource) != len(
            {op.resource.resource_id for op in request.changeset.operations}
        ):
            return await self._rollback_rejected(
                receipt_id=receipt_id,
                idem_key=idem_key,
                attempt_id=attempt_id,
                reason=ApplyReasonCode.VALIDATION_REJECTED,
                receipt_state=DryRunReceiptLifecycleState.CLAIMED,
                invalidate=False,
            )

        locked_material = await project_apply_binding_material(
            request.changeset,
            session=self._session,
            wb_reader=self._wb_reader,
        )
        if (
            locked_material.status != DryRunStatus.OK
            or locked_material.plan is None
            or locked_material.plan.is_no_op
        ):
            reason = _reason_from_validation_errors(locked_material.errors)
            return await self._rollback_rejected(
                receipt_id=receipt_id,
                idem_key=idem_key,
                attempt_id=attempt_id,
                reason=reason,
                receipt_state=DryRunReceiptLifecycleState.CLAIMED,
                invalidate=reason
                in {
                    ApplyReasonCode.STALE_STATE,
                    ApplyReasonCode.CAPABILITY_DRIFT,
                    ApplyReasonCode.PREVIEW_DIGEST_MISMATCH,
                },
            )

        plan = locked_material.plan
        try:
            apply_plan_to_adv_settings(
                plan,
                adv_by_resource=adv_by_resource,
            )
        except (ValueError, LookupError):
            return await self._rollback_rejected(
                receipt_id=receipt_id,
                idem_key=idem_key,
                attempt_id=attempt_id,
                reason=ApplyReasonCode.WRITER_REJECTED,
                receipt_state=DryRunReceiptLifecycleState.CLAIMED,
                invalidate=False,
            )

        await self._session.flush()

        if not _verify_normalized_fields(plan, adv_by_resource):
            return await self._rollback_rejected(
                receipt_id=receipt_id,
                idem_key=idem_key,
                attempt_id=attempt_id,
                reason=ApplyReasonCode.VERIFICATION_MISMATCH,
                receipt_state=DryRunReceiptLifecycleState.CLAIMED,
                invalidate=False,
            )

        post_tokens = _post_state_tokens(request, locked_material, adv_by_resource)
        evidence_id = f"ev_{uuid.uuid4().hex}"
        evidence = ApplyEvidenceV1(
            evidence_id=evidence_id,
            scope=request.changeset.scope,
            changeset_id=request.changeset.changeset_id,
            dry_run_receipt_id=receipt_id,
            idempotency_key=request.idempotency_key,
            apply_contract_version=APPLY_CONTRACT_VERSION,
            semantic_digest=material.semantic_digest,
            preview_digest=material.preview_digest,
            post_state_tokens=post_tokens,
            terminal_status=ApplyTerminalStatus.VERIFIED,
            committed_at=now,
        )
        _ = await self._evidence_store.insert(evidence)
        await self._idempotency_store.finalize_verified(
            idem_key,
            evidence_id=evidence_id,
            attempt_id=attempt_id,
        )
        _ = await self._receipt_store.transition_lifecycle(
            receipt_id,
            DryRunReceiptLifecycleState.CONSUMED,
        )
        _ = await self._attempt_store.update_lifecycle(
            attempt_id,
            lifecycle_state=ApplyAttemptLifecycleState.TERMINAL,
            terminal_status=ApplyTerminalStatus.VERIFIED,
        )
        return _verified(evidence)

    async def _abort_before_claim(
        self,
        *,
        receipt_id: str,
        reason: ApplyReasonCode,
        receipt_state: DryRunReceiptLifecycleState,
        invalidate: bool,
    ) -> ApplyOutcomeV1:
        _ = receipt_state
        if invalidate:
            _ = await self._receipt_store.transition_lifecycle(
                receipt_id,
                DryRunReceiptLifecycleState.INVALIDATED,
            )
        if reason in {
            ApplyReasonCode.WRITER_REJECTED,
            ApplyReasonCode.VERIFICATION_MISMATCH,
        }:
            return _failed(reason)
        return _rejected(reason=reason)

    async def _rollback_rejected(
        self,
        *,
        receipt_id: str,
        idem_key: IdempotencyKey,
        attempt_id: str,
        reason: ApplyReasonCode,
        receipt_state: DryRunReceiptLifecycleState,
        invalidate: bool,
    ) -> ApplyOutcomeV1:
        terminal = ApplyTerminalStatus.REJECTED
        if reason in {
            ApplyReasonCode.WRITER_REJECTED,
            ApplyReasonCode.VERIFICATION_MISMATCH,
        }:
            terminal = ApplyTerminalStatus.FAILED

        new_receipt_state = receipt_outcome_transition(
            receipt_state,
            terminal_status=terminal,
            reason_code=reason,
        )
        if invalidate:
            _ = await self._receipt_store.transition_lifecycle(
                receipt_id,
                DryRunReceiptLifecycleState.INVALIDATED,
            )
        elif new_receipt_state == DryRunReceiptLifecycleState.ISSUED:
            _ = await self._receipt_store.release_claim(receipt_id)
        elif new_receipt_state != receipt_state:
            _ = await self._receipt_store.transition_lifecycle(
                receipt_id,
                new_receipt_state,
            )

        await self._idempotency_store.release_in_flight(idem_key, attempt_id=attempt_id)
        _ = await self._attempt_store.update_lifecycle(
            attempt_id,
            lifecycle_state=ApplyAttemptLifecycleState.TERMINAL,
            terminal_status=terminal,
            reason_code=reason,
        )
        if terminal == ApplyTerminalStatus.FAILED:
            return _failed(reason)
        return _rejected(reason=reason)
