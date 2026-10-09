"""ApplyOutcomeV1 — client-visible apply result."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.modules.wb_sky_control_plane.apply.enums import (
    ApplyReasonCode,
    ApplyTerminalStatus,
)
from app.modules.wb_sky_control_plane.apply.models.evidence import ApplyEvidenceV1

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class ApplyOutcomeV1(BaseModel):
    """Terminal or in-progress apply outcome (service layer in later slices)."""

    model_config = _FROZEN

    status: ApplyTerminalStatus
    reason_code: ApplyReasonCode | None = None
    evidence: ApplyEvidenceV1 | None = None
