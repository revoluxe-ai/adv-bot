"""Observation window model (anchored to exposure, not decision time)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True, slots=True)
class ExperimentWindowModel:
    """Timezone-aware observation windows for an experiment plan."""

    timezone: str
    baseline_start: datetime | None = None
    baseline_end: datetime | None = None
    treatment_effective_from: datetime | None = None
    burn_in_end: datetime | None = None
    burn_out_start: datetime | None = None
    observation_start: datetime | None = None
    observation_end: datetime | None = None
    evaluation_cutoff: datetime | None = None
    source_complete_through: datetime | None = None
    evaluated_at: datetime | None = None


def compute_observation_start(
    *,
    effective_from: datetime,
    burn_in: timedelta | None = None,
) -> datetime:
    """Compute ``observation_start`` from exposure anchor and optional burn-in."""
    if burn_in is None:
        return effective_from
    return effective_from + burn_in


def with_observation_start_from_exposure(
    window: ExperimentWindowModel,
    *,
    effective_from: datetime,
    burn_in: timedelta | None = None,
) -> ExperimentWindowModel:
    """Return window with ``observation_start`` derived from exposure (not decision time)."""
    obs_start = compute_observation_start(
        effective_from=effective_from,
        burn_in=burn_in,
    )
    return ExperimentWindowModel(
        timezone=window.timezone,
        baseline_start=window.baseline_start,
        baseline_end=window.baseline_end,
        treatment_effective_from=effective_from,
        burn_in_end=window.burn_in_end,
        burn_out_start=window.burn_out_start,
        observation_start=obs_start,
        observation_end=window.observation_end,
        evaluation_cutoff=window.evaluation_cutoff,
        source_complete_through=window.source_complete_through,
        evaluated_at=window.evaluated_at,
    )
