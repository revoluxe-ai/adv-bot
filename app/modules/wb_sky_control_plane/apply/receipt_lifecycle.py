"""Pure deterministic dry-run receipt lifecycle transitions."""

from __future__ import annotations

from app.modules.wb_sky_control_plane.apply.enums import (
    ApplyReasonCode,
    ApplyTerminalStatus,
    DryRunReceiptLifecycleState,
    ReceiptLifecycleEventKind,
)

_TERMINAL_RECEIPT_STATES = frozenset(
    {
        DryRunReceiptLifecycleState.CONSUMED,
        DryRunReceiptLifecycleState.EXPIRED,
        DryRunReceiptLifecycleState.INVALIDATED,
        DryRunReceiptLifecycleState.BLOCKED_RECONCILIATION,
    }
)

_INVALIDATING_REASONS = frozenset(
    {
        ApplyReasonCode.STALE_STATE,
        ApplyReasonCode.PREVIEW_DIGEST_MISMATCH,
        ApplyReasonCode.CAPABILITY_DRIFT,
    }
)

_RECEIPT_PRESERVING_REASONS = frozenset(
    {
        ApplyReasonCode.UNAUTHORIZED,
        ApplyReasonCode.CHANGESET_DIGEST_MISMATCH,
    }
)


def _aba_guard(
    current: DryRunReceiptLifecycleState,
    proposed: DryRunReceiptLifecycleState,
) -> DryRunReceiptLifecycleState:
    """INVALIDATED never resurrects (A→B→A safety)."""
    if current == DryRunReceiptLifecycleState.INVALIDATED:
        return DryRunReceiptLifecycleState.INVALIDATED
    if current in _TERMINAL_RECEIPT_STATES and current != proposed:
        return current
    return proposed


def apply_receipt_lifecycle_event(
    current: DryRunReceiptLifecycleState,
    event: ReceiptLifecycleEventKind,
) -> DryRunReceiptLifecycleState:
    """Explicit claim/TTL transitions."""
    if current == DryRunReceiptLifecycleState.INVALIDATED:
        return DryRunReceiptLifecycleState.INVALIDATED

    if event == ReceiptLifecycleEventKind.CLAIM:
        if current == DryRunReceiptLifecycleState.ISSUED:
            return DryRunReceiptLifecycleState.CLAIMED
        return current

    if event == ReceiptLifecycleEventKind.RELEASE_CLAIM:
        if current == DryRunReceiptLifecycleState.CLAIMED:
            return DryRunReceiptLifecycleState.ISSUED
        return current

    if event == ReceiptLifecycleEventKind.TTL_ELAPSED:
        if current in {
            DryRunReceiptLifecycleState.ISSUED,
            DryRunReceiptLifecycleState.CLAIMED,
        }:
            return DryRunReceiptLifecycleState.EXPIRED
        return current

    return current


def receipt_outcome_transition(
    current: DryRunReceiptLifecycleState,
    *,
    terminal_status: ApplyTerminalStatus,
    reason_code: ApplyReasonCode | None,
) -> DryRunReceiptLifecycleState:
    """Map apply terminal outcome to receipt lifecycle delta."""
    if current == DryRunReceiptLifecycleState.INVALIDATED:
        return DryRunReceiptLifecycleState.INVALIDATED

    if reason_code in _RECEIPT_PRESERVING_REASONS:
        return current

    if terminal_status == ApplyTerminalStatus.VERIFIED:
        return _aba_guard(current, DryRunReceiptLifecycleState.CONSUMED)

    if terminal_status in {
        ApplyTerminalStatus.UNKNOWN_INTERNAL_COMMIT,
        ApplyTerminalStatus.UNKNOWN_EXTERNAL_STATE,
    }:
        return _aba_guard(
            current, DryRunReceiptLifecycleState.BLOCKED_RECONCILIATION
        )

    if reason_code in _INVALIDATING_REASONS:
        return _aba_guard(current, DryRunReceiptLifecycleState.INVALIDATED)

    if (
        terminal_status in {ApplyTerminalStatus.REJECTED, ApplyTerminalStatus.FAILED}
        and reason_code not in _INVALIDATING_REASONS
        and reason_code not in _RECEIPT_PRESERVING_REASONS
        and current == DryRunReceiptLifecycleState.CLAIMED
    ):
        return DryRunReceiptLifecycleState.ISSUED

    return current
