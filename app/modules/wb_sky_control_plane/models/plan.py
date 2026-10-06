"""Plan и DryRunResult (semantic effects, not WB API steps)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.modules.wb_sky_control_plane.models.errors import (
    ControlPlaneError,
    ControlPlaneWarning,
)
from app.modules.wb_sky_control_plane.models.enums import DryRunStatus


class SemanticDiffEntryV1(BaseModel):
    """Семантический diff одного поля. Не является командой записи.

    ``old`` / ``current`` — значение поколения ``state_token``.
    ``requested`` — форма из операции до ``normalize_value``.
    ``normalized`` / ``desired`` — каноническое значение.
    ``resource_id`` и ``field_path`` связывают diff с ``cmp_*``, без
    параллельного ключа ``adv_setting_id`` / ``leg_role``.
    """

    field_path: str
    current: object | None
    desired: object | None
    intent: str
    resource_id: str | None = None
    old: str | int | float | bool | None = None
    requested: str | int | float | bool | None = None
    normalized: str | int | float | bool | None = None


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


class PriorChangeSetRecord(BaseModel):
    """Внедрённое наблюдение идемпотентности. Валидатор его не сохраняет."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    changeset_id: str
    canonical_hash: str
    status: DryRunStatus


class ChangeSetValidationResult(BaseModel):
    """Итог dry-run ``validate_changeset``: NO_OP, OK или REJECTED, без записи."""

    status: DryRunStatus
    changeset_id: str
    semantic_digest: str
    diffs: list[SemanticDiffEntryV1] = Field(default_factory=list)
    errors: list[ControlPlaneError] = Field(default_factory=list)
    plan: PlanV1 | None = None


class DryRunResultV1(BaseModel):
    """Read-only dry-run output."""

    status: DryRunStatus
    changeset_id: str
    semantic_digest: str
    plan: PlanV1 | None = None
    state_tokens: dict[str, str] = Field(default_factory=dict)
    errors: list[ControlPlaneError] = Field(default_factory=list)
    warnings: list[ControlPlaneWarning] = Field(default_factory=list)
