"""Plan и DryRunResult (semantic effects, not WB API steps)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.modules.wb_sky_control_plane.models.errors import (
    ControlPlaneError,
    ControlPlaneWarning,
)
from app.modules.wb_sky_control_plane.models.enums import DryRunStatus


class SemanticDiffEntryV1(BaseModel):
    """Semantic diff field between current and desired policy projection."""

    field_path: str
    current: object | None
    desired: object | None
    intent: str


class PlanEffectV1(BaseModel):
    """Semantic plan effect for one operation (not raw WB API step)."""

    resource_id: str
    operation: str
    operation_index: int
    semantic_changes: list[SemanticDiffEntryV1] = Field(default_factory=list)
    is_no_op: bool = False


class PlanV1(BaseModel):
    """Semantic plan over bounded operations."""

    effects: list[PlanEffectV1] = Field(default_factory=list)
    is_no_op: bool = False


class DryRunResultV1(BaseModel):
    """Read-only dry-run output."""

    status: DryRunStatus
    changeset_id: str
    semantic_digest: str
    plan: PlanV1 | None = None
    state_tokens: dict[str, str] = Field(default_factory=dict)
    errors: list[ControlPlaneError] = Field(default_factory=list)
    warnings: list[ControlPlaneWarning] = Field(default_factory=list)
