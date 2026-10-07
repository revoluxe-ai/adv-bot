"""Experiment plan body value types (digest input **B**)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.modules.decision_experiment_memory.domain.enums import (
    AnalysisMethod,
    ControlDefinitionKind,
    ExperimentDesign,
    StoppingRule,
    TreatmentMode,
)
from app.modules.decision_experiment_memory.domain.refs import MetricSpecRef
from app.modules.decision_experiment_memory.domain.window import ExperimentWindowModel


@dataclass(frozen=True, slots=True)
class ControlDefinition:
    """Explicit counterfactual definition (no implicit prose control)."""

    kind: ControlDefinitionKind
    state_token: str | None = None
    match_rule_id: str | None = None
    entity_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TreatmentDefinition:
    """Normalized intended treatment semantics (signature input)."""

    setting_keys: tuple[str, ...]
    old_values: dict[str, Any]
    new_values: dict[str, Any]
    scope_shop_id: str | None = None
    scope_cmp_ids: tuple[int, ...] = ()
    scope_nm_ids: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class ExperimentPlanBody:
    """Immutable plan body hashed into ``plan_digest`` (excludes revision metadata)."""

    experiment_id: str
    hypothesis: dict[str, Any]
    treatment_definition: TreatmentDefinition
    control_definition: ControlDefinition
    experiment_design: ExperimentDesign
    treatment_mode: TreatmentMode
    primary_metrics: tuple[MetricSpecRef, ...]
    secondary_metrics: tuple[MetricSpecRef, ...] = ()
    guardrail_metrics: tuple[MetricSpecRef, ...] = ()
    window_model: ExperimentWindowModel | None = None
    minimum_meaningful_effect: dict[str, Any] | None = None
    success_criteria: dict[str, Any] | None = None
    failure_criteria: dict[str, Any] | None = None
    analysis_method: AnalysisMethod = AnalysisMethod.FIXED_HORIZON_DIFF
    analysis_config_version: str = "v1"
    stopping_rule: StoppingRule = StoppingRule.FIXED_HORIZON
    required_data_validity_conditions: tuple[str, ...] = ()
