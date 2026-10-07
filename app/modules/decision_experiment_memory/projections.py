"""Pure projection helpers for decision status and experiment lifecycle."""

from __future__ import annotations

from datetime import datetime

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
from app.modules.decision_experiment_memory.domain.refs import ApplyEvidenceRef
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


def validate_confirmed_exposure(
    experiment: ExperimentRecordV1,
    *,
    exposure: ExposureModel,
    apply_evidence_ref: ApplyEvidenceRef | None,
) -> None:
    """Fail closed when LIVE confirmed exposure lacks authoritative evidence."""
    if not exposure.exposure_confirmed:
        return
    if experiment.treatment_mode == TreatmentMode.SHADOW:
        if exposure.effective_from is not None and apply_evidence_ref is None:
            raise ExposureInvariantError(
                "SHADOW must not invent authoritative effective_from without apply ref"
            )
        return
    if apply_evidence_ref is None:
        raise ExposureInvariantError(
            "LIVE confirmed exposure requires ApplyEvidenceRef"
        )
    if not exposure.resulting_state_token:
        raise ExposureInvariantError(
            "LIVE confirmed exposure requires resulting_state_token"
        )
    if exposure.effective_from is None:
        raise ExposureInvariantError(
            "LIVE confirmed exposure requires effective_from"
        )


def build_confirmed_exposure_model(
    experiment: ExperimentRecordV1,
    *,
    apply_evidence_ref: ApplyEvidenceRef,
    resulting_state_token: str,
    effective_from: datetime,
    observation_start: datetime,
) -> ExposureModel:
    """Construct confirmed exposure projection with LIVE gate enforcement."""
    exposure = ExposureModel(
        changeset_ref=experiment.exposure.changeset_ref,
        apply_evidence_ref=apply_evidence_ref,
        resulting_state_token=resulting_state_token,
        effective_from=effective_from,
        observation_start=observation_start,
        exposure_confirmed=True,
    )
    validate_confirmed_exposure(
        experiment,
        exposure=exposure,
        apply_evidence_ref=apply_evidence_ref,
    )
    return exposure


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
    apply_evidence_ref: ApplyEvidenceRef | None = None,
) -> ExperimentRecordV1:
    """Update experiment exposure anchors (enforces LIVE evidence gate)."""
    ref = apply_evidence_ref or exposure.apply_evidence_ref
    validate_confirmed_exposure(
        experiment,
        exposure=exposure,
        apply_evidence_ref=ref,
    )
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
