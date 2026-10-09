"""Persistence-layer result enums (no I/O)."""

from __future__ import annotations

from enum import Enum


class ReceiptClaimResult(str, Enum):
    """Outcome of a conditional receipt claim."""

    CLAIMED = "claimed"
    NOT_FOUND = "not_found"
    EXPIRED = "expired"
    TERMINAL = "terminal"
    BLOCKED_RECONCILIATION = "blocked_reconciliation"
    ALREADY_CLAIMED = "already_claimed"


class IdempotencyClaimResult(str, Enum):
    """Outcome of idempotency slot claim."""

    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    CONFLICT = "conflict"
    REPLAY_READY = "replay_ready"
