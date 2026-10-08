"""ApplyPlanV1 — internal writer orchestration view."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.modules.wb_sky_control_plane.models.plan import PlanV1, SemanticDiffEntryV1

_FROZEN = ConfigDict(frozen=True, extra="forbid")


def _empty_actionable_diffs() -> list[SemanticDiffEntryV1]:
    return []


class ApplyPlanV1(BaseModel):
    """Semantic plan bound to reviewed receipt (not WB API steps)."""

    model_config = _FROZEN

    plan: PlanV1
    actionable_diffs: list[SemanticDiffEntryV1] = Field(
        default_factory=_empty_actionable_diffs
    )
