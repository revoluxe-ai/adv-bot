"""Перечисления Apply Authority (lifecycle, outcomes, reasons)."""

from __future__ import annotations

from enum import Enum


class DryRunReceiptLifecycleState(str, Enum):
    """Состояние server-issued dry-run receipt (non-terminal + terminal)."""

    ISSUED = "issued"
    CLAIMED = "claimed"
    CONSUMED = "consumed"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"
    BLOCKED_RECONCILIATION = "blocked_reconciliation"


class ApplyAttemptLifecycleState(str, Enum):
    """Mutable attempt lifecycle (Slice B+ persistence; vocabulary in Slice A)."""

    RECEIVED = "received"
    VALIDATING = "validating"
    CLAIMING = "claiming"
    APPLYING = "applying"
    VERIFYING = "verifying"
    TERMINAL = "terminal"


class ApplyTerminalStatus(str, Enum):
    """Terminal apply outcome status."""

    VERIFIED = "verified"
    REJECTED = "rejected"
    FAILED = "failed"
    UNKNOWN_INTERNAL_COMMIT = "unknown_internal_commit"
    UNKNOWN_EXTERNAL_STATE = "unknown_external_state"


class ApplyReasonCode(str, Enum):
    """Stable reason codes for REJECTED / FAILED / blocking states."""

    VALIDATION_REJECTED = "validation_rejected"
    UNAUTHORIZED = "unauthorized"
    STALE_STATE = "stale_state"
    CHANGESET_DIGEST_MISMATCH = "changeset_digest_mismatch"
    PREVIEW_DIGEST_MISMATCH = "preview_digest_mismatch"
    CAPABILITY_DRIFT = "capability_drift"
    RECEIPT_INVALID = "receipt_invalid"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    RECEIPT_BLOCKED_RECONCILIATION = "receipt_blocked_reconciliation"
    APPLY_IN_PROGRESS = "apply_in_progress"
    WRITER_REJECTED = "writer_rejected"
    VERIFICATION_MISMATCH = "verification_mismatch"
    TRANSACTION_ROLLED_BACK = "transaction_rolled_back"
    UNSUPPORTED_OPERATION = "unsupported_operation"


class TransportChannel(str, Enum):
    """Audit label for apply invocation transport."""

    UI = "ui"
    TELEGRAM = "telegram"
    MCP = "mcp"
    API = "api"
    INTERNAL = "internal"


class IdempotencyDecisionKind(str, Enum):
    """Pure idempotency decision without I/O."""

    FRESH = "fresh"
    REPLAY_CANDIDATE = "replay_candidate"
    CONFLICT = "conflict"
    IN_PROGRESS = "in_progress"


class ReceiptLifecycleEventKind(str, Enum):
    """Explicit receipt lifecycle events (claim, TTL, outcome hooks)."""

    CLAIM = "claim"
    RELEASE_CLAIM = "release_claim"
    TTL_ELAPSED = "ttl_elapsed"
    APPLY_OUTCOME = "apply_outcome"
