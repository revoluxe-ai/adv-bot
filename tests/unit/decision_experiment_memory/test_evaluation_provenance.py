"""EvaluationProvenance vocabulary matches design § provenance."""

from __future__ import annotations

from app.modules.decision_experiment_memory.domain.factual import (
    EvaluationProvenance,
    Interpretation,
)
from app.modules.decision_experiment_memory.domain.refs import ApplyEvidenceRef
import pytest

pytestmark = pytest.mark.unit


def test_evaluation_provenance_optional_ai_and_dry_run_refs() -> None:
    apply_ref = ApplyEvidenceRef(
        apply_evidence_id="apply-1",
        evidence_digest="dig",
    )
    provenance = EvaluationProvenance(
        schema_version="demem_outcome_v1",
        frozen_plan_digest="plan-dig",
        settings_state_ref=None,
        changeset_semantic_digest=None,
        apply_evidence_ref=apply_ref,
        metric_spec_versions=("orders@1",),
        analysis_config_version="cfg-v1",
        evaluation_input_refs=("slice-1",),
        producer="unit",
        producer_version="0",
        evaluation_run_digest="run-dig",
        ai_package_id="pkg-1",
        ai_package_digest="pkg-dig",
        dry_run_evidence_ref=apply_ref,
    )
    assert provenance.ai_package_id == "pkg-1"
    assert provenance.dry_run_evidence_ref is apply_ref


def test_interpretation_post_hoc_flag_defaults_false() -> None:
    from datetime import datetime, timezone

    interpretation = Interpretation(
        interpretation_id="i-1",
        experiment_id="e-1",
        factual_result_id=None,
        narrative="n",
        recorded_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert interpretation.is_post_hoc is False
