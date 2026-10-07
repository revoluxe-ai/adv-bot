"""Decision and experiment aggregate records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.modules.decision_experiment_memory.domain.enums import (
    CausalEvidenceLevel,
    DecisionStatus,
    ExecutionState,
    ExperimentDesign,
    Outcome,
    TreatmentMode,
)
from app.modules.decision_experiment_memory.domain.refs import (
    ApplyEvidenceRef,
    ChangeSetRef,
)
from app.modules.decision_experiment_memory.domain.validity import ValiditySnapshot
from app.modules.decision_experiment_memory.errors import IdentityInvariantError


@dataclass(frozen=True, slots=True)
class DecisionMemoryRecord:
    """Semantic decision memory (may exist without experiments)."""

    decision_id: str
    shop_id: str
    status: DecisionStatus
    created_at: datetime
    observation: str
    rationale: str
    intended_action: str
    decision_fingerprint: str | None = None
    changeset_ref: ChangeSetRef | None = None
    apply_evidence_ref: ApplyEvidenceRef | None = None
    dry_run_receipt_id: str | None = None


@dataclass(frozen=True, slots=True)
class ExposureModel:
    """Assignment / apply / exposure anchors (refs only)."""

    changeset_ref: ChangeSetRef | None = None
    apply_evidence_ref: ApplyEvidenceRef | None = None
    resulting_state_token: str | None = None
    effective_from: datetime | None = None
    observation_start: datetime | None = None
    exposure_confirmed: bool = False


@dataclass(frozen=True, slots=True)
class ExperimentRecordV1:
    """Experiment shell with orthogonal execution and outcome."""

    experiment_id: str
    decision_id: str
    treatment_mode: TreatmentMode
    execution_state: ExecutionState
    outcome: Outcome
    experiment_design: ExperimentDesign
    causal_evidence_level: CausalEvidenceLevel
    evidence_design: ExperimentDesign
    intervention_signature_digest: str
    active_plan_revision: int
    frozen_plan_digest: str | None
    exposure: ExposureModel
    data_validity: ValiditySnapshot | None = None
    factual_result_ids: tuple[str, ...] = ()
    interpretation_ids: tuple[str, ...] = ()


def assert_distinct_experiment_identity(
    *,
    decision_id: str,
    experiment_id: str,
    forbid_equal: bool = True,
) -> None:
    """Ensure experiment identity is not collapsed into decision id by default."""
    if forbid_equal and experiment_id == decision_id:
        raise IdentityInvariantError(
            "experiment_id MUST NOT equal decision_id (forbidden invariant/default)"
        )


def new_experiment_shell(
    *,
    experiment_id: str,
    decision_id: str,
    treatment_mode: TreatmentMode,
    experiment_design: ExperimentDesign,
    intervention_signature_digest: str,
    active_plan_revision: int,
) -> ExperimentRecordV1:
    """Create experiment shell after first plan registration."""
    assert_distinct_experiment_identity(
        decision_id=decision_id,
        experiment_id=experiment_id,
    )
    from app.modules.decision_experiment_memory.domain.enums import (
        causal_evidence_level_for_design,
    )

    level = causal_evidence_level_for_design(experiment_design)
    return ExperimentRecordV1(
        experiment_id=experiment_id,
        decision_id=decision_id,
        treatment_mode=treatment_mode,
        execution_state=ExecutionState.REGISTERED,
        outcome=Outcome.PENDING,
        experiment_design=experiment_design,
        causal_evidence_level=level,
        evidence_design=experiment_design,
        intervention_signature_digest=intervention_signature_digest,
        active_plan_revision=active_plan_revision,
        frozen_plan_digest=None,
        exposure=ExposureModel(),
    )
