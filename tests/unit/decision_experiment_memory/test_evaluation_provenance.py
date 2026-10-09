"""EvaluationProvenance vocabulary matches design § provenance."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.modules.decision_experiment_memory.domain.factual import (
    EvaluationProvenance,
    Interpretation,
)
from app.modules.decision_experiment_memory.domain.refs import (
    ApplyEvidenceRef,
    DryRunReceiptRef,
)

pytestmark = pytest.mark.unit


def test_dry_run_receipt_ref_not_apply_evidence_ref() -> None:
    dry = DryRunReceiptRef(dry_run_receipt_id="receipt-1", preview_digest="prev")
    apply = ApplyEvidenceRef(apply_evidence_id="evidence-1", evidence_digest="dig")
    assert type(dry) is not type(apply)
    provenance = EvaluationProvenance(
        schema_version="demem_outcome_v1",
        frozen_plan_digest="plan-dig",
        settings_state_ref=None,
        changeset_semantic_digest=None,
        apply_evidence_ref=apply,
        metric_spec_versions=("orders@1",),
        analysis_config_version="cfg-v1",
        evaluation_input_refs=("slice-1",),
        producer="unit",
        producer_version="0",
        evaluation_run_digest="run-dig",
        dry_run_receipt_ref=dry,
    )
    assert provenance.dry_run_receipt_ref is dry
    assert provenance.apply_evidence_ref is apply
    assert provenance.dry_run_receipt_ref is not provenance.apply_evidence_ref


def test_evaluation_provenance_optional_ai_package_refs() -> None:
    provenance = EvaluationProvenance(
        schema_version="demem_outcome_v1",
        frozen_plan_digest="plan-dig",
        settings_state_ref=None,
        changeset_semantic_digest=None,
        apply_evidence_ref=None,
        metric_spec_versions=("orders@1",),
        analysis_config_version="cfg-v1",
        evaluation_input_refs=("slice-1",),
        producer="unit",
        producer_version="0",
        evaluation_run_digest="run-dig",
        ai_package_id="pkg-1",
        ai_package_digest="pkg-dig",
    )
    assert provenance.ai_package_id == "pkg-1"


def test_interpretation_post_hoc_flag_defaults_false() -> None:
    interpretation = Interpretation(
        interpretation_id="i-1",
        experiment_id="e-1",
        factual_result_id=None,
        narrative="n",
        recorded_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert interpretation.is_post_hoc is False
