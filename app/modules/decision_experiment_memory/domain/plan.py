"""ExperimentPlan immutable revisions and digest computation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.modules.decision_experiment_memory.domain.enums import (
    CausalEvidenceLevel,
    ExperimentDesign,
    RegistrationKind,
    TreatmentMode,
    causal_evidence_level_for_design,
)
from app.modules.decision_experiment_memory.domain.plan_body_types import (
    ControlDefinition,
    ExperimentPlanBody,
    TreatmentDefinition,
)

__all__ = [
    "ControlDefinition",
    "ExperimentPlan",
    "ExperimentPlanBody",
    "TreatmentDefinition",
    "build_plan",
]


@dataclass(frozen=True, slots=True)
class ExperimentPlan:
    """Registered immutable experiment plan revision."""

    experiment_id: str
    plan_revision: int
    plan_digest: str
    registered_at: datetime
    registration_kind: RegistrationKind
    body: ExperimentPlanBody

    @property
    def experiment_design(self) -> ExperimentDesign:
        return self.body.experiment_design

    @property
    def treatment_mode(self) -> TreatmentMode:
        return self.body.treatment_mode

    @property
    def causal_evidence_level(self) -> CausalEvidenceLevel:
        return causal_evidence_level_for_design(self.body.experiment_design)


def build_plan(
    *,
    experiment_id: str,
    plan_revision: int,
    registered_at: datetime,
    registration_kind: RegistrationKind,
    body: ExperimentPlanBody,
) -> ExperimentPlan:
    """Construct plan with digest derived from body."""
    from app.modules.decision_experiment_memory.domain.plan_serialization import (
        plan_body_digest,
    )

    digest = plan_body_digest(body)
    return ExperimentPlan(
        experiment_id=experiment_id,
        plan_revision=plan_revision,
        plan_digest=digest,
        registered_at=registered_at,
        registration_kind=registration_kind,
        body=body,
    )
