"""Pure idempotency fingerprint and decision logic (no durable store)."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.wb_sky_control_plane.apply.enums import (
    ApplyReasonCode,
    ApplyTerminalStatus,
    IdempotencyDecisionKind,
)
from app.modules.wb_sky_control_plane.apply.models.evidence import ApplyEvidenceV1
from app.modules.wb_sky_control_plane.kernel.canonical_json import canonical_sha256


@dataclass(frozen=True, slots=True)
class IdempotencyKey:
    """Store key vocabulary: (shop_id, idempotency_key)."""

    shop_id: str
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class IdempotencyRecordView:
    """Read-only view of a persisted idempotency row (Slice B+)."""

    fingerprint: str
    terminal_status: ApplyTerminalStatus | None
    in_flight: bool
    evidence: ApplyEvidenceV1 | None


@dataclass(frozen=True, slots=True)
class IdempotencyDecision:
    """Result of pure idempotency evaluation."""

    kind: IdempotencyDecisionKind
    reason_code: ApplyReasonCode | None = None
    evidence: ApplyEvidenceV1 | None = None


def build_idempotency_fingerprint(
    *,
    apply_contract_version: str,
    semantic_digest: str,
    preview_digest: str,
) -> str:
    """Fingerprint = contract + sd1 + pd1 (canonical JSON hash)."""
    return canonical_sha256(
        {
            "apply_contract_version": apply_contract_version,
            "semantic_digest": semantic_digest,
            "preview_digest": preview_digest,
        },
        prefix="idf1_",
    )


def decide_idempotency(
    *,
    fingerprint: str,
    record: IdempotencyRecordView | None,
    caller_authorized: bool,
) -> IdempotencyDecision:
    """Pure idempotency rules without storage I/O.

    Unauthorized replay candidate MUST NOT disclose evidence.
    """
    if record is None:
        return IdempotencyDecision(kind=IdempotencyDecisionKind.FRESH)

    if record.in_flight:
        return IdempotencyDecision(
            kind=IdempotencyDecisionKind.IN_PROGRESS,
            reason_code=ApplyReasonCode.APPLY_IN_PROGRESS,
        )

    if record.fingerprint != fingerprint:
        return IdempotencyDecision(
            kind=IdempotencyDecisionKind.CONFLICT,
            reason_code=ApplyReasonCode.IDEMPOTENCY_CONFLICT,
        )

    if record.terminal_status == ApplyTerminalStatus.VERIFIED and record.evidence:
        if not caller_authorized:
            return IdempotencyDecision(
                kind=IdempotencyDecisionKind.REPLAY_CANDIDATE,
                reason_code=ApplyReasonCode.UNAUTHORIZED,
                evidence=None,
            )
        return IdempotencyDecision(
            kind=IdempotencyDecisionKind.REPLAY_CANDIDATE,
            evidence=record.evidence,
        )

    return IdempotencyDecision(kind=IdempotencyDecisionKind.FRESH)
