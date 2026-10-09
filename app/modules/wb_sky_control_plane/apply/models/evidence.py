"""ApplyEvidenceV1 — immutable terminal execution receipt."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.wb_sky_control_plane.apply.enums import ApplyTerminalStatus
from app.modules.wb_sky_control_plane.models.changeset import LogicalScopeV1

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class ApplyEvidenceV1(BaseModel):
    """Insert-only evidence at terminal VERIFIED (Slice B+ persistence)."""

    model_config = _FROZEN

    evidence_id: str
    scope: LogicalScopeV1
    changeset_id: str
    dry_run_receipt_id: str
    idempotency_key: str
    apply_contract_version: str
    semantic_digest: str
    preview_digest: str
    post_state_tokens: dict[str, str] = Field(default_factory=dict)
    terminal_status: ApplyTerminalStatus
    committed_at: datetime
