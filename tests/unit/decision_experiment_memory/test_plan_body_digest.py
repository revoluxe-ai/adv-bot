"""Plan digest must cover full ExperimentPlanBody **B**."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.modules.decision_experiment_memory.domain.enums import (
    AnalysisMethod,
    ControlDefinitionKind,
    ExperimentDesign,
    StoppingRule,
    TreatmentMode,
)
from app.modules.decision_experiment_memory.domain.plan import (
    ControlDefinition,
    ExperimentPlanBody,
    TreatmentDefinition,
)
from app.modules.decision_experiment_memory.domain.plan_serialization import (
    plan_body_canonical_projection,
    plan_body_digest,
)
from app.modules.decision_experiment_memory.domain.refs import (
    MetricAnalysisWindowRef,
    MetricSpecRef,
)
from app.modules.decision_experiment_memory.domain.switchback_schedule import (
    SwitchbackScheduleV1,
)
from app.modules.decision_experiment_memory.domain.window import ExperimentWindowModel

pytestmark = pytest.mark.unit

BodyMutator = Callable[[ExperimentPlanBody], ExperimentPlanBody]


def sample_experiment_plan_body() -> ExperimentPlanBody:
    treatment = TreatmentDefinition(
        setting_keys=("bid",),
        old_values={"bid": 10},
        new_values={"bid": 12},
        scope_shop_id="shop-1",
    )
    metric = MetricSpecRef(
        metric_id="orders",
        metric_definition_version="1",
        source_family="CH",
        grain="day",
        scope="shop",
        numerator_semantics="orders",
        coverage_requirements=("complete_through",),
        analysis_window=MetricAnalysisWindowRef(
            analysis_window_label="post",
            evaluation_cutoff=datetime(2026, 1, 10, tzinfo=timezone.utc),
            source_complete_through=datetime(2026, 1, 9, tzinfo=timezone.utc),
        ),
    )
    return ExperimentPlanBody(
        experiment_id="e-1",
        hypothesis={"statement": "lift"},
        treatment_definition=treatment,
        control_definition=ControlDefinition(
            kind=ControlDefinitionKind.PRIOR_CONFIGURATION,
            state_token="st1",
        ),
        experiment_design=ExperimentDesign.RANDOMIZED_AB,
        treatment_mode=TreatmentMode.LIVE,
        primary_metrics=(metric,),
        secondary_metrics=(
            MetricSpecRef(
                metric_id="secondary",
                metric_definition_version="1",
                source_family="CH",
                grain="day",
                scope="shop",
                numerator_semantics="clicks",
            ),
        ),
        guardrail_metrics=(
            MetricSpecRef(
                metric_id="guard",
                metric_definition_version="1",
                source_family="CH",
                grain="day",
                scope="shop",
                numerator_semantics="spend",
            ),
        ),
        window_model=ExperimentWindowModel(
            timezone="UTC",
            observation_start=datetime(2026, 1, 5, tzinfo=timezone.utc),
        ),
        minimum_meaningful_effect={"relative": Decimal("0.05")},
        success_criteria={"op": "gt", "threshold": 0.1},
        failure_criteria={"op": "lt", "threshold": -0.1},
        analysis_method=AnalysisMethod.FIXED_HORIZON_DIFF,
        analysis_config_version="cfg-v2",
        stopping_rule=StoppingRule.FIXED_SAMPLE,
        required_data_validity_conditions=("reconciliation_ok",),
    )


def _mutate_hypothesis(body: ExperimentPlanBody) -> ExperimentPlanBody:
    return replace(body, hypothesis={"x": 2})


def _mutate_treatment(body: ExperimentPlanBody) -> ExperimentPlanBody:
    return replace(
        body,
        treatment_definition=TreatmentDefinition(
            setting_keys=("bid", "cpm"),
            old_values=body.treatment_definition.old_values,
            new_values=body.treatment_definition.new_values,
        ),
    )


def _mutate_control(body: ExperimentPlanBody) -> ExperimentPlanBody:
    return replace(
        body,
        control_definition=ControlDefinition(
            kind=ControlDefinitionKind.HISTORICAL_BASELINE,
        ),
    )


def _mutate_experiment_design(body: ExperimentPlanBody) -> ExperimentPlanBody:
    return replace(body, experiment_design=ExperimentDesign.SWITCHBACK)


def _mutate_treatment_mode(body: ExperimentPlanBody) -> ExperimentPlanBody:
    return replace(body, treatment_mode=TreatmentMode.SHADOW)


def _mutate_primary_metric(body: ExperimentPlanBody) -> ExperimentPlanBody:
    return replace(
        body,
        primary_metrics=(
            MetricSpecRef(
                metric_id="orders-changed",
                metric_definition_version="1",
                source_family="CH",
                grain="day",
                scope="shop",
                numerator_semantics="orders",
            ),
        ),
    )


def _mutate_secondary_metric(body: ExperimentPlanBody) -> ExperimentPlanBody:
    return replace(
        body,
        secondary_metrics=(
            MetricSpecRef(
                metric_id="secondary-2",
                metric_definition_version="1",
                source_family="CH",
                grain="day",
                scope="shop",
                numerator_semantics="x",
            ),
        ),
    )


def _mutate_guardrail_metric(body: ExperimentPlanBody) -> ExperimentPlanBody:
    return replace(
        body,
        guardrail_metrics=(
            MetricSpecRef(
                metric_id="guard-2",
                metric_definition_version="1",
                source_family="CH",
                grain="day",
                scope="shop",
                numerator_semantics="x",
            ),
        ),
    )


def _mutate_window_model(body: ExperimentPlanBody) -> ExperimentPlanBody:
    return replace(
        body,
        window_model=ExperimentWindowModel(timezone="Europe/Moscow"),
    )


def _mutate_minimum_meaningful_effect(body: ExperimentPlanBody) -> ExperimentPlanBody:
    return replace(body, minimum_meaningful_effect={"relative": "0.06"})


def _mutate_success_criteria(body: ExperimentPlanBody) -> ExperimentPlanBody:
    return replace(body, success_criteria={"op": "gte", "threshold": 0.2})


def _mutate_failure_criteria(body: ExperimentPlanBody) -> ExperimentPlanBody:
    return replace(body, failure_criteria={"op": "lte", "threshold": -0.2})


def _mutate_analysis_method(body: ExperimentPlanBody) -> ExperimentPlanBody:
    return replace(body, analysis_method=AnalysisMethod.RATIO_VS_BASELINE)


def _mutate_analysis_config_version(body: ExperimentPlanBody) -> ExperimentPlanBody:
    return replace(body, analysis_config_version="cfg-v3")


def _mutate_stopping_rule(body: ExperimentPlanBody) -> ExperimentPlanBody:
    return replace(body, stopping_rule=StoppingRule.SEQUENTIAL_RESERVED)


def _mutate_required_validity_conditions(body: ExperimentPlanBody) -> ExperimentPlanBody:
    return replace(body, required_data_validity_conditions=("extra",))


def _mutate_switchback_schedule(body: ExperimentPlanBody) -> ExperimentPlanBody:
    return replace(
        body,
        switchback_schedule=SwitchbackScheduleV1(
            schedule="weekly",
            timezone="UTC",
        ),
    )


_DIGEST_MUTATORS: list[tuple[str, BodyMutator]] = [
    ("hypothesis", _mutate_hypothesis),
    ("treatment", _mutate_treatment),
    ("control", _mutate_control),
    ("experiment_design", _mutate_experiment_design),
    ("treatment_mode", _mutate_treatment_mode),
    ("primary_metric", _mutate_primary_metric),
    ("secondary_metric", _mutate_secondary_metric),
    ("guardrail_metric", _mutate_guardrail_metric),
    ("window_model", _mutate_window_model),
    ("minimum_meaningful_effect", _mutate_minimum_meaningful_effect),
    ("success_criteria", _mutate_success_criteria),
    ("failure_criteria", _mutate_failure_criteria),
    ("analysis_method", _mutate_analysis_method),
    ("analysis_config_version", _mutate_analysis_config_version),
    ("stopping_rule", _mutate_stopping_rule),
    ("required_validity_conditions", _mutate_required_validity_conditions),
    ("switchback_schedule", _mutate_switchback_schedule),
]


def test_hypothesis_key_order_invariant() -> None:
    body_a = replace(sample_experiment_plan_body(), hypothesis={"z": 1, "a": 2})
    body_b = replace(sample_experiment_plan_body(), hypothesis={"a": 2, "z": 1})
    assert plan_body_digest(body_a) == plan_body_digest(body_b)


@pytest.mark.parametrize(("mutator_name", "mutator"), _DIGEST_MUTATORS)
def test_plan_digest_changes_on_field(
    mutator_name: str,
    mutator: BodyMutator,
) -> None:
    base = sample_experiment_plan_body()
    mutated = mutator(base)
    assert plan_body_digest(base) != plan_body_digest(mutated), mutator_name


def test_canonical_projection_includes_all_body_fields() -> None:
    body = sample_experiment_plan_body()
    projection = plan_body_canonical_projection(body)
    for key in (
        "secondary_metrics",
        "guardrail_metrics",
        "window_model",
        "minimum_meaningful_effect",
        "success_criteria",
        "failure_criteria",
    ):
        assert projection[key] is not None
