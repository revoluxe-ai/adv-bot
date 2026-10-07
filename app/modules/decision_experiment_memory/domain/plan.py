"""ExperimentPlan immutable revisions and digest computation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.modules.decision_experiment_memory.canonical_json import canonical_sha256
from app.modules.decision_experiment_memory.domain.enums import (
    AnalysisMethod,
    CausalEvidenceLevel,
    ControlDefinitionKind,
    ExperimentDesign,
    RegistrationKind,
    StoppingRule,
    TreatmentMode,
    causal_evidence_level_for_design,
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


@dataclass(frozen=True, slots=True)
class ExperimentPlan:
    """Registered immutable experiment plan revision."""

    experiment_id: str
    plan_revision: int
    plan_digest: str
    registered_at: datetime
    registration_kind: RegistrationKind
    body: ExperimentPlanBody

    @property
    def experiment_design(self) -> ExperimentDesign:
        return self.body.experiment_design

    @property
    def treatment_mode(self) -> TreatmentMode:
        return self.body.treatment_mode

    @property
    def causal_evidence_level(self) -> CausalEvidenceLevel:
        return causal_evidence_level_for_design(self.body.experiment_design)


def plan_body_digest(body: ExperimentPlanBody) -> str:
    """Compute ``plan_digest`` from canonical plan body JSON."""
    payload = {
        "experiment_id": body.experiment_id,
        "hypothesis": body.hypothesis,
        "treatment_definition": {
            "setting_keys": list(body.treatment_definition.setting_keys),
            "old_values": body.treatment_definition.old_values,
            "new_values": body.treatment_definition.new_values,
            "scope_shop_id": body.treatment_definition.scope_shop_id,
            "scope_cmp_ids": list(body.treatment_definition.scope_cmp_ids),
            "scope_nm_ids": list(body.treatment_definition.scope_nm_ids),
        },
        "control_definition": {
            "kind": body.control_definition.kind.value,
            "state_token": body.control_definition.state_token,
            "match_rule_id": body.control_definition.match_rule_id,
            "entity_ids": list(body.control_definition.entity_ids),
        },
        "experiment_design": body.experiment_design.value,
        "treatment_mode": body.treatment_mode.value,
        "primary_metrics": [
            {
                "metric_id": m.metric_id,
                "metric_definition_version": m.metric_definition_version,
                "source_family": m.source_family,
                "grain": m.grain,
                "scope": m.scope,
                "numerator_semantics": m.numerator_semantics,
                "denominator_semantics": m.denominator_semantics,
            }
            for m in body.primary_metrics
        ],
        "analysis_method": body.analysis_method.value,
        "analysis_config_version": body.analysis_config_version,
        "stopping_rule": body.stopping_rule.value,
        "required_data_validity_conditions": list(body.required_data_validity_conditions),
    }
    return canonical_sha256(payload)


def build_plan(
    *,
    experiment_id: str,
    plan_revision: int,
    registered_at: datetime,
    registration_kind: RegistrationKind,
    body: ExperimentPlanBody,
) -> ExperimentPlan:
    """Construct plan with digest derived from body."""
    digest = plan_body_digest(body)
    return ExperimentPlan(
        experiment_id=experiment_id,
        plan_revision=plan_revision,
        plan_digest=digest,
        registered_at=registered_at,
        registration_kind=registration_kind,
        body=body,
    )
