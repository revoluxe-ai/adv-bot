"""Experiment plan freeze and revision invariants."""

from __future__ import annotations

from app.modules.decision_experiment_memory.domain.plan import ExperimentPlan
from app.modules.decision_experiment_memory.domain.records import ExperimentRecordV1
from app.modules.decision_experiment_memory.errors import PlanInvariantError


def require_frozen_for_confirmatory_evaluation(
    experiment: ExperimentRecordV1,
    *,
    registration_kind_confirmatory: bool,
) -> None:
    """Block confirmatory outcome inspection without ``PLAN_FROZEN``."""
    if not registration_kind_confirmatory:
        return
    if experiment.frozen_plan_digest is None:
        raise PlanInvariantError(
            "PLAN_FROZEN required before confirmatory outcome inspection"
        )


def assert_plan_revision_unchanged(
    stored: ExperimentPlan,
    expected_digest: str,
) -> None:
    """Ensure a stored revision bytes are unchanged (immutable revision)."""
    if stored.plan_digest != expected_digest:
        raise PlanInvariantError("registered plan revision digest mismatch")


def freeze_plan_on_experiment(
    experiment: ExperimentRecordV1,
    plan: ExperimentPlan,
) -> ExperimentRecordV1:
    """Attach frozen digest from a registered plan revision."""
    if plan.experiment_id != experiment.experiment_id:
        raise PlanInvariantError("plan experiment_id mismatch")
    return ExperimentRecordV1(
        experiment_id=experiment.experiment_id,
        decision_id=experiment.decision_id,
        treatment_mode=experiment.treatment_mode,
        execution_state=experiment.execution_state,
        outcome=experiment.outcome,
        experiment_design=experiment.experiment_design,
        causal_evidence_level=experiment.causal_evidence_level,
        evidence_design=experiment.evidence_design,
        intervention_signature_digest=experiment.intervention_signature_digest,
        active_plan_revision=plan.plan_revision,
        frozen_plan_digest=plan.plan_digest,
        exposure=experiment.exposure,
        data_validity=experiment.data_validity,
        factual_result_ids=experiment.factual_result_ids,
        interpretation_ids=experiment.interpretation_ids,
    )
