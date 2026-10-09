"""Compare authoritative projection material to server-issued receipt binding."""

from __future__ import annotations

from app.modules.wb_sky_control_plane.apply.enums import ApplyReasonCode
from app.modules.wb_sky_control_plane.apply.models.receipt import DryRunReceiptV1
from app.modules.wb_sky_control_plane.apply.service.revalidation import ApplyBindingMaterial
from app.modules.wb_sky_control_plane.models.enums import DryRunStatus


def receipt_binding_mismatch(
    receipt: DryRunReceiptV1,
    material: ApplyBindingMaterial,
) -> ApplyReasonCode | None:
    """Return reason when locked/fresh material disagrees with receipt binding."""
    if material.semantic_digest != receipt.binding.semantic_digest:
        return ApplyReasonCode.CHANGESET_DIGEST_MISMATCH
    if material.status != DryRunStatus.OK:
        return ApplyReasonCode.VALIDATION_REJECTED
    if material.preview_digest != receipt.binding.preview_digest:
        return ApplyReasonCode.PREVIEW_DIGEST_MISMATCH
    if (
        material.capability_projection_digest
        != receipt.binding.capability_projection_digest
    ):
        return ApplyReasonCode.CAPABILITY_DRIFT
    for rid, bound_token in receipt.binding.state_tokens.items():
        if material.state_tokens.get(rid) != bound_token:
            return ApplyReasonCode.STALE_STATE
    if receipt.binding.dry_run_status != DryRunStatus.OK:
        return ApplyReasonCode.RECEIPT_INVALID
    if material.plan is None:
        return ApplyReasonCode.VALIDATION_REJECTED
    if material.plan.is_no_op:
        return ApplyReasonCode.VALIDATION_REJECTED
    return None


def invalidate_on_binding_mismatch(reason: ApplyReasonCode) -> bool:
    """Receipt INVALIDATED for preview/capability/stale drift."""
    return reason in {
        ApplyReasonCode.PREVIEW_DIGEST_MISMATCH,
        ApplyReasonCode.CAPABILITY_DRIFT,
        ApplyReasonCode.STALE_STATE,
    }
