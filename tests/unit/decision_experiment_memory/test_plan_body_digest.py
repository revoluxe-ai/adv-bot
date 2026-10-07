"""Plan digest must cover full ExperimentPlanBody **B**."""

from __future__ import annotations

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
from app.modules.decision_experiment_memory.domain.window import ExperimentWindowModel

pytestmark = pytest.mark.unit


def _base_body() -> ExperimentPlanBody:
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


def test_hypothesis_key_order_invariant() -> None:
    body_a = replace(_base_body(), hypothesis={"z": 1, "a": 2})
    body_b = replace(_base_body(), hypothesis={"a": 2, "z": 1})
    assert plan_body_digest(body_a) == plan_body_digest(body_b)


@pytest.mark.parametrize(
    ("mutator_name", "mutator"),
    [
        ("hypothesis", lambda b: replace(b, hypothesis={"x": 2})),
        (
            "treatment",
            lambda b: replace(
                b,
                treatment_definition=TreatmentDefinition(
                    setting_keys=("bid", "cpm"),
                    old_values=b.treatment_definition.old_values,
                    new_values=b.treatment_definition.new_values,
                ),
            ),
        ),
        (
            "control",
            lambda b: replace(
                b,
                control_definition=ControlDefinition(
                    kind=ControlDefinitionKind.HISTORICAL_BASELINE,
                ),
            ),
        ),
        ("experiment_design", lambda b: replace(b, experiment_design=ExperimentDesign.SWITCHBACK)),
        ("treatment_mode", lambda b: replace(b, treatment_mode=TreatmentMode.SHADOW)),
        (
            "primary_metric",
            lambda b: replace(
                b,
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
            ),
        ),
        (
            "secondary_metric",
            lambda b: replace(
                b,
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
            ),
        ),
        (
            "guardrail_metric",
            lambda b: replace(
                b,
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
            ),
        ),
        (
            "window_model",
            lambda b: replace(
                b,
                window_model=ExperimentWindowModel(timezone="Europe/Moscow"),
            ),
        ),
        (
            "minimum_meaningful_effect",
            lambda b: replace(b, minimum_meaningful_effect={"relative": "0.06"}),
        ),
        (
            "success_criteria",
            lambda b: replace(b, success_criteria={"op": "gte", "threshold": 0.2}),
        ),
        (
            "failure_criteria",
            lambda b: replace(b, failure_criteria={"op": "lte", "threshold": -0.2}),
        ),
        (
            "analysis_method",
            lambda b: replace(b, analysis_method=AnalysisMethod.RATIO_VS_BASELINE),
        ),
        ("analysis_config_version", lambda b: replace(b, analysis_config_version="cfg-v3")),
        ("stopping_rule", lambda b: replace(b, stopping_rule=StoppingRule.SEQUENTIAL_RESERVED)),
        (
            "required_validity_conditions",
            lambda b: replace(b, required_data_validity_conditions=("extra",)),
        ),
    ],
)
def test_plan_digest_changes_on_field(mutator_name: str, mutator) -> None:
    base = _base_body()
    mutated = mutator(base)
    assert plan_body_digest(base) != plan_body_digest(mutated), mutator_name


def test_canonical_projection_includes_all_body_fields() -> None:
    body = _base_body()
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
