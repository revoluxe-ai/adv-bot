"""Canonical plan body projection for ``plan_digest`` computation."""

from __future__ import annotations

from typing import Any

from app.modules.decision_experiment_memory.canonical_json import canonical_sha256
from app.modules.decision_experiment_memory.domain.plan_body_types import (
    ControlDefinition,
    ExperimentPlanBody,
    TreatmentDefinition,
)
from app.modules.decision_experiment_memory.domain.refs import MetricSpecRef
from app.modules.decision_experiment_memory.domain.switchback_schedule import (
    SwitchbackScheduleV1,
)
from app.modules.decision_experiment_memory.domain.window import ExperimentWindowModel


def _metric_spec_projection(metric: MetricSpecRef) -> dict[str, Any]:
    window = metric.analysis_window
    return {
        "metric_id": metric.metric_id,
        "metric_definition_version": metric.metric_definition_version,
        "source_family": metric.source_family,
        "grain": metric.grain,
        "scope": metric.scope,
        "numerator_semantics": metric.numerator_semantics,
        "denominator_semantics": metric.denominator_semantics,
        "coverage_requirements": list(metric.coverage_requirements),
        "analysis_window": (
            {
                "analysis_window_label": window.analysis_window_label,
                "evaluation_cutoff": window.evaluation_cutoff,
                "source_complete_through": window.source_complete_through,
            }
            if window is not None
            else None
        ),
    }


def _window_model_projection(window: ExperimentWindowModel | None) -> dict[str, Any] | None:
    if window is None:
        return None
    return {
        "timezone": window.timezone,
        "baseline_start": window.baseline_start,
        "baseline_end": window.baseline_end,
        "treatment_effective_from": window.treatment_effective_from,
        "burn_in_end": window.burn_in_end,
        "burn_out_start": window.burn_out_start,
        "observation_start": window.observation_start,
        "observation_end": window.observation_end,
        "evaluation_cutoff": window.evaluation_cutoff,
        "source_complete_through": window.source_complete_through,
        "evaluated_at": window.evaluated_at,
    }


def _treatment_projection(treatment: TreatmentDefinition) -> dict[str, Any]:
    return {
        "setting_keys": list(treatment.setting_keys),
        "old_values": treatment.old_values,
        "new_values": treatment.new_values,
        "scope_shop_id": treatment.scope_shop_id,
        "scope_cmp_ids": list(treatment.scope_cmp_ids),
        "scope_nm_ids": list(treatment.scope_nm_ids),
    }


def _switchback_projection(
    schedule: SwitchbackScheduleV1 | None,
) -> dict[str, Any] | None:
    if schedule is None:
        return None
    projected = {
        "schedule": schedule.schedule,
        "assignment_time_bucket": schedule.assignment_time_bucket,
        "timezone": schedule.timezone,
        "burn_in": schedule.burn_in,
        "burn_out": schedule.burn_out,
        "carryover_policy": schedule.carryover_policy,
    }
    if all(value is None for value in projected.values()):
        return None
    return projected


def _control_projection(control: ControlDefinition) -> dict[str, Any]:
    return {
        "kind": control.kind,
        "state_token": control.state_token,
        "match_rule_id": control.match_rule_id,
        "entity_ids": list(control.entity_ids),
    }


def plan_body_canonical_projection(body: ExperimentPlanBody) -> dict[str, Any]:
    """Build canonical dict **B** for ``plan_digest = sha256(canonical_json(B))``."""
    return {
        "experiment_id": body.experiment_id,
        "hypothesis": body.hypothesis,
        "treatment_definition": _treatment_projection(body.treatment_definition),
        "control_definition": _control_projection(body.control_definition),
        "experiment_design": body.experiment_design,
        "treatment_mode": body.treatment_mode,
        "primary_metrics": [_metric_spec_projection(m) for m in body.primary_metrics],
        "secondary_metrics": [_metric_spec_projection(m) for m in body.secondary_metrics],
        "guardrail_metrics": [_metric_spec_projection(m) for m in body.guardrail_metrics],
        "window_model": _window_model_projection(body.window_model),
        "minimum_meaningful_effect": body.minimum_meaningful_effect,
        "success_criteria": body.success_criteria,
        "failure_criteria": body.failure_criteria,
        "analysis_method": body.analysis_method,
        "analysis_config_version": body.analysis_config_version,
        "stopping_rule": body.stopping_rule,
        "required_data_validity_conditions": list(body.required_data_validity_conditions),
        "switchback_schedule": _switchback_projection(body.switchback_schedule),
    }


def plan_body_digest(body: ExperimentPlanBody) -> str:
    """Compute ``plan_digest`` from full immutable plan body **B**."""
    return canonical_sha256(plan_body_canonical_projection(body))
