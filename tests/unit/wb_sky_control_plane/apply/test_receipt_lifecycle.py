"""Receipt lifecycle + ABA pure rules."""

from __future__ import annotations

import pytest

from app.modules.wb_sky_control_plane.apply.enums import (
    ApplyReasonCode,
    ApplyTerminalStatus,
    DryRunReceiptLifecycleState,
    ReceiptLifecycleEventKind,
)
from app.modules.wb_sky_control_plane.apply.receipt_lifecycle import (
    apply_receipt_lifecycle_event,
    receipt_outcome_transition,
)

pytestmark = pytest.mark.unit


def test_stale_state_invalidates_permanently_aba() -> None:
    current = DryRunReceiptLifecycleState.ISSUED
    after_stale = receipt_outcome_transition(
        current,
        terminal_status=ApplyTerminalStatus.REJECTED,
        reason_code=ApplyReasonCode.STALE_STATE,
    )
    assert after_stale == DryRunReceiptLifecycleState.INVALIDATED
    resurrect = apply_receipt_lifecycle_event(
        after_stale, ReceiptLifecycleEventKind.RELEASE_CLAIM
    )
    assert resurrect == DryRunReceiptLifecycleState.INVALIDATED


def test_unauthorized_preserves_issued() -> None:
    current = DryRunReceiptLifecycleState.ISSUED
    after = receipt_outcome_transition(
        current,
        terminal_status=ApplyTerminalStatus.REJECTED,
        reason_code=ApplyReasonCode.UNAUTHORIZED,
    )
    assert after == DryRunReceiptLifecycleState.ISSUED


def test_changeset_mismatch_preserves_receipt() -> None:
    current = DryRunReceiptLifecycleState.ISSUED
    after = receipt_outcome_transition(
        current,
        terminal_status=ApplyTerminalStatus.REJECTED,
        reason_code=ApplyReasonCode.CHANGESET_DIGEST_MISMATCH,
    )
    assert after == DryRunReceiptLifecycleState.ISSUED


def test_verified_consumes_receipt() -> None:
    current = DryRunReceiptLifecycleState.CLAIMED
    after = receipt_outcome_transition(
        current,
        terminal_status=ApplyTerminalStatus.VERIFIED,
        reason_code=None,
    )
    assert after == DryRunReceiptLifecycleState.CONSUMED


def test_unknown_external_state_blocks_reconciliation() -> None:
    current = DryRunReceiptLifecycleState.CLAIMED
    after = receipt_outcome_transition(
        current,
        terminal_status=ApplyTerminalStatus.UNKNOWN_EXTERNAL_STATE,
        reason_code=None,
    )
    assert after == DryRunReceiptLifecycleState.BLOCKED_RECONCILIATION


def test_unknown_internal_commit_blocks_reconciliation() -> None:
    current = DryRunReceiptLifecycleState.CLAIMED
    after = receipt_outcome_transition(
        current,
        terminal_status=ApplyTerminalStatus.UNKNOWN_INTERNAL_COMMIT,
        reason_code=None,
    )
    assert after == DryRunReceiptLifecycleState.BLOCKED_RECONCILIATION
