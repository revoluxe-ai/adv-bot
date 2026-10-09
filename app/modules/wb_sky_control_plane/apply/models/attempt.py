"""ApplyAttemptRecord — mutable durable attempt lifecycle (Slice B+)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.wb_sky_control_plane.apply.enums import (
    ApplyAttemptLifecycleState,
    ApplyReasonCode,
    ApplyTerminalStatus,
    TransportChannel,
)

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class ApplyAttemptRecordV1(BaseModel):
    """Durable attempt row; distinct from immutable ApplyEvidenceV1."""

    model_config = _FROZEN

    attempt_id: str
    shop_id: str
    idempotency_key: str
    dry_run_receipt_id: str
    principal_kind: str
    principal_id: str
    transport_channel: TransportChannel
    lifecycle_state: ApplyAttemptLifecycleState
    terminal_status: ApplyTerminalStatus | None = None
    reason_code: ApplyReasonCode | None = None
    created_at: datetime
    updated_at: datetime
