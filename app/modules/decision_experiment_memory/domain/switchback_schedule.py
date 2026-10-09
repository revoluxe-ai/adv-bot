"""Reserved switchback schedule vocabulary (no engine in Slice A)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SwitchbackScheduleV1:
    """Optional reserved struct on ``ExperimentPlan`` (execution deferred)."""

    schedule: str | None = None
    assignment_time_bucket: str | None = None
    timezone: str | None = None
    burn_in: str | None = None
    burn_out: str | None = None
    carryover_policy: str | None = None
