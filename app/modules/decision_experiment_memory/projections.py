"""Pure projection helpers for decision status and experiment lifecycle."""

from __future__ import annotations

from app.modules.decision_experiment_memory.domain.enums import (
    DecisionStatus,
    ExecutionState,
    TreatmentMode,
)
from app.modules.decision_experiment_memory.domain.records import (
    DecisionMemoryRecord,
    ExperimentRecordV1,
    ExposureModel,
)
from app.modules.decision_experiment_memory.domain.validity import (
    abort_execution_outcome,
)
from app.modules.decision_experiment_memory.errors import ExposureInvariantError


def project_decision_status(record: DecisionMemoryRecord) -> DecisionStatus:
    """Project decision status without inferring Apply truth from missing refs."""
    if record.apply_evidence_ref is None:
        if record.status == DecisionStatus.APPLY_CONFIRMED:
            raise ExposureInvariantError(
                "APPLY_CONFIRMED requires ApplyEvidenceRef"
            )
        return record.status
    return record.status


def can_confirm_apply(record: DecisionMemoryRecord) -> bool:
    """Return whether decision may transition to APPLY_CONFIRMED."""
    return record.apply_evidence_ref is not None


def project_live_observing(
    experiment: ExperimentRecordV1,
) -> ExecutionState:
    """LIVE experiments require confirmed exposure before OBSERVING."""
    if experiment.treatment_mode != TreatmentMode.LIVE:
        return experiment.execution_state
    if not experiment.exposure.exposure_confirmed:
        if experiment.execution_state == ExecutionState.OBSERVING:
            raise ExposureInvariantError(
                "LIVE OBSERVING requires EXPOSURE_CONFIRMED"
            )
        return experiment.execution_state
    return experiment.execution_state


def with_aborted_execution(experiment: ExperimentRecordV1) -> ExperimentRecordV1:
    """Apply V1 abort projection (outcome stays PENDING)."""
    return ExperimentRecordV1(
        experiment_id=experiment.experiment_id,
        decision_id=experiment.decision_id,
        treatment_mode=experiment.treatment_mode,
        execution_state=ExecutionState.ABORTED,
        outcome=abort_execution_outcome(),
        experiment_design=experiment.experiment_design,
        causal_evidence_level=experiment.causal_evidence_level,
        evidence_design=experiment.evidence_design,
        intervention_signature_digest=experiment.intervention_signature_digest,
        active_plan_revision=experiment.active_plan_revision,
        frozen_plan_digest=experiment.frozen_plan_digest,
        exposure=experiment.exposure,
        data_validity=experiment.data_validity,
        factual_result_ids=experiment.factual_result_ids,
        interpretation_ids=experiment.interpretation_ids,
    )


def with_exposure_confirmed(
    experiment: ExperimentRecordV1,
    *,
    exposure: ExposureModel,
) -> ExperimentRecordV1:
    """Update experiment exposure anchors."""
    new_state = experiment.execution_state
    if (
        experiment.treatment_mode == TreatmentMode.LIVE
        and exposure.exposure_confirmed
    ):
        new_state = ExecutionState.OBSERVING
    return ExperimentRecordV1(
        experiment_id=experiment.experiment_id,
        decision_id=experiment.decision_id,
        treatment_mode=experiment.treatment_mode,
        execution_state=new_state,
        outcome=experiment.outcome,
        experiment_design=experiment.experiment_design,
        causal_evidence_level=experiment.causal_evidence_level,
        evidence_design=experiment.evidence_design,
        intervention_signature_digest=experiment.intervention_signature_digest,
        active_plan_revision=experiment.active_plan_revision,
        frozen_plan_digest=experiment.frozen_plan_digest,
        exposure=exposure,
        data_validity=experiment.data_validity,
        factual_result_ids=experiment.factual_result_ids,
        interpretation_ids=experiment.interpretation_ids,
    )
