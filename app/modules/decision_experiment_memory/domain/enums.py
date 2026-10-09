"""Enumerations for decision-experiment memory domain vocabulary."""

from __future__ import annotations

from enum import StrEnum


class DecisionStatus(StrEnum):
    """Decision lifecycle (orthogonal to experiment execution)."""

    RECORDED = "RECORDED"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    APPLY_CONFIRMED = "APPLY_CONFIRMED"
    APPLY_FAILED = "APPLY_FAILED"
    WITHDRAWN = "WITHDRAWN"
    SUPERSEDED = "SUPERSEDED"


class TreatmentMode(StrEnum):
    """How treatment is applied relative to production authority."""

    LIVE = "LIVE"
    SHADOW = "SHADOW"


class ExperimentDesign(StrEnum):
    """Preregistered experiment design (not treatment mode)."""

    RANDOMIZED_AB = "RANDOMIZED_AB"
    SWITCHBACK = "SWITCHBACK"
    CONTROLLED_BEFORE_AFTER = "CONTROLLED_BEFORE_AFTER"
    BEFORE_AFTER_OBSERVATIONAL = "BEFORE_AFTER_OBSERVATIONAL"


class CausalEvidenceLevel(StrEnum):
    """Ordered causal strength derived from ``experiment_design``."""

    HIGH_RANDOMIZED = "HIGH_RANDOMIZED"
    MEDIUM_SWITCHBACK = "MEDIUM_SWITCHBACK"
    MEDIUM_CONTROLLED = "MEDIUM_CONTROLLED"
    LOW_OBSERVATIONAL = "LOW_OBSERVATIONAL"


class RegistrationKind(StrEnum):
    """Whether a plan is confirmatory or exploratory."""

    PREREGISTERED_CONFIRMATORY = "PREREGISTERED_CONFIRMATORY"
    POST_HOC_EXPLORATORY = "POST_HOC_EXPLORATORY"


class PostHocAnalysisKind(StrEnum):
    """Post-hoc analysis classification (cannot rewrite preregistered plan)."""

    EXPLORATORY = "EXPLORATORY"
    POST_HOC = "POST_HOC"


class ExecutionState(StrEnum):
    """Experiment execution machine (orthogonal to outcome)."""

    PLANNED = "PLANNED"
    REGISTERED = "REGISTERED"
    APPLY_PENDING = "APPLY_PENDING"
    APPLIED = "APPLIED"
    OBSERVING = "OBSERVING"
    EVALUATABLE = "EVALUATABLE"
    EVALUATED = "EVALUATED"
    ABORTED = "ABORTED"


class Outcome(StrEnum):
    """Terminal evaluation outcome (no ``ABORTED`` — use execution_state)."""

    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    INCONCLUSIVE = "INCONCLUSIVE"
    INVALID = "INVALID"


class DataValidityStatus(StrEnum):
    """Snapshot validity for an evaluation run."""

    VALID = "VALID"
    PARTIAL = "PARTIAL"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"


class ValidityReasonCode(StrEnum):
    """Multi-valued validity reason codes (``demem_outcome_v1`` input)."""

    SOURCE_INCOMPLETE = "SOURCE_INCOMPLETE"
    SOURCE_COMPLETE_THROUGH_GAP = "SOURCE_COMPLETE_THROUGH_GAP"
    ATTRIBUTION_COVERAGE_LOW = "ATTRIBUTION_COVERAGE_LOW"
    RECONCILIATION_FAILED = "RECONCILIATION_FAILED"
    METRIC_DEFINITION_MISMATCH = "METRIC_DEFINITION_MISMATCH"
    EXPOSURE_INTEGRITY_FAIL = "EXPOSURE_INTEGRITY_FAIL"
    MISSING_REQUIRED_INPUT = "MISSING_REQUIRED_INPUT"
    OBSERVATION_WINDOW_INCOMPLETE = "OBSERVATION_WINDOW_INCOMPLETE"
    CONCURRENT_INTERVENTION = "CONCURRENT_INTERVENTION"
    STALE_OR_REVISED_SOURCE = "STALE_OR_REVISED_SOURCE"


class ControlDefinitionKind(StrEnum):
    """Explicit counterfactual mode for ``ExperimentPlan``."""

    RANDOMIZED_CONTROL_ARM = "RANDOMIZED_CONTROL_ARM"
    PRIOR_CONFIGURATION = "PRIOR_CONFIGURATION"
    MATCHED_ENTITY = "MATCHED_ENTITY"
    HISTORICAL_BASELINE = "HISTORICAL_BASELINE"
    SWITCHBACK_CONTROL_WINDOW = "SWITCHBACK_CONTROL_WINDOW"


class StoppingRule(StrEnum):
    """Frozen stopping rule on the plan."""

    FIXED_HORIZON = "FIXED_HORIZON"
    FIXED_SAMPLE = "FIXED_SAMPLE"
    SEQUENTIAL_RESERVED = "SEQUENTIAL_RESERVED"


class AnalysisMethod(StrEnum):
    """Frozen analysis method identifier."""

    FIXED_HORIZON_DIFF = "FIXED_HORIZON_DIFF"
    RATIO_VS_BASELINE = "RATIO_VS_BASELINE"


DESIGN_TO_CAUSAL_LEVEL: dict[ExperimentDesign, CausalEvidenceLevel] = {
    ExperimentDesign.RANDOMIZED_AB: CausalEvidenceLevel.HIGH_RANDOMIZED,
    ExperimentDesign.SWITCHBACK: CausalEvidenceLevel.MEDIUM_SWITCHBACK,
    ExperimentDesign.CONTROLLED_BEFORE_AFTER: CausalEvidenceLevel.MEDIUM_CONTROLLED,
    ExperimentDesign.BEFORE_AFTER_OBSERVATIONAL: CausalEvidenceLevel.LOW_OBSERVATIONAL,
}


def causal_evidence_level_for_design(design: ExperimentDesign) -> CausalEvidenceLevel:
    """Map ``experiment_design`` to ``causal_evidence_level``."""
    return DESIGN_TO_CAUSAL_LEVEL[design]
