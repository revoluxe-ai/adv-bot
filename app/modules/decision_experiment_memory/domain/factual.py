"""Factual results, interpretation, and evaluation provenance refs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.modules.decision_experiment_memory.domain.refs import (
    ApplyEvidenceRef,
    MetricSpecRef,
    SettingsStateRef,
)


@dataclass(frozen=True, slots=True)
class MetricValue:
    """Single metric observation keyed by spec ref identity."""

    spec: MetricSpecRef
    value: float | int | None


@dataclass(frozen=True, slots=True)
class FactualResult:
    """Immutable factual evaluation output (evaluator-owned in later slices)."""

    factual_result_id: str
    experiment_id: str
    frozen_plan_digest: str
    recorded_at: datetime
    metric_values: tuple[MetricValue, ...]
    outcome_digest: str


@dataclass(frozen=True, slots=True)
class Interpretation:
    """Non-authoritative narrative append (does not mutate factual outcome)."""

    interpretation_id: str
    experiment_id: str
    factual_result_id: str | None
    narrative: str
    recorded_at: datetime


@dataclass(frozen=True, slots=True)
class EvaluationProvenance:
    """Reproducibility refs for an evaluation run (payload-free)."""

    schema_version: str
    frozen_plan_digest: str
    settings_state_ref: SettingsStateRef | None
    changeset_semantic_digest: str | None
    apply_evidence_ref: ApplyEvidenceRef | None
    metric_spec_versions: tuple[str, ...]
    analysis_config_version: str
    evaluation_input_refs: tuple[str, ...]
    producer: str
    producer_version: str
    evaluation_run_digest: str
    extra_refs: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class PostHocAnalysisRecord:
    """Distinct post-hoc analysis linkage (Slice E runtime deferred)."""

    post_hoc_id: str
    experiment_id: str
    interpretation_id: str
    recorded_at: datetime
