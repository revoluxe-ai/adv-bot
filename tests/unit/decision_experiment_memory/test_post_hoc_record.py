"""Post-hoc analysis vocabulary is separate from preregistered plan/outcomes."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.modules.decision_experiment_memory.domain.enums import PostHocAnalysisKind
from app.modules.decision_experiment_memory.domain.factual import PostHocAnalysisRecord
from app.modules.decision_experiment_memory.domain.plan import ExperimentPlanBody
from app.modules.decision_experiment_memory.domain.plan_serialization import (
    plan_body_digest,
)
from app.modules.decision_experiment_memory.domain.refs import MetricSpecRef
from tests.unit.decision_experiment_memory.test_plan_body_digest import _base_body

pytestmark = pytest.mark.unit


def test_post_hoc_record_carries_kind_and_exploratory_metrics() -> None:
    metric = MetricSpecRef(
        metric_id="exploratory-metric",
        metric_definition_version="1",
        source_family="CH",
        grain="day",
        scope="shop",
        numerator_semantics="clicks",
    )
    record = PostHocAnalysisRecord(
        post_hoc_id="ph-1",
        experiment_id="e-1",
        interpretation_id="i-1",
        recorded_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        analysis_kind=PostHocAnalysisKind.POST_HOC,
        exploratory_metrics=(metric,),
    )
    assert record.analysis_kind == PostHocAnalysisKind.POST_HOC
    assert record.exploratory_metrics[0].metric_id == "exploratory-metric"


def test_post_hoc_metrics_do_not_mutate_frozen_plan_digest() -> None:
    body: ExperimentPlanBody = _base_body()
    digest_before = plan_body_digest(body)
    _ = PostHocAnalysisRecord(
        post_hoc_id="ph-2",
        experiment_id=body.experiment_id,
        interpretation_id="i-2",
        recorded_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        analysis_kind=PostHocAnalysisKind.EXPLORATORY,
        exploratory_metrics=(
            MetricSpecRef(
                metric_id="not-in-plan",
                metric_definition_version="9",
                source_family="CH",
                grain="day",
                scope="shop",
                numerator_semantics="x",
            ),
        ),
    )
    assert plan_body_digest(body) == digest_before
