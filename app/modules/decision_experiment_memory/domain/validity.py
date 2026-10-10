"""Validity snapshots and outcome projection (``demem_outcome_v1``)."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.decision_experiment_memory.domain.enums import (
    DataValidityStatus,
    Outcome,
    ValidityReasonCode,
)

OUTCOME_MAPPING_VERSION = "demem_outcome_v1"

_INVALID_REASONS: frozenset[ValidityReasonCode] = frozenset(
    {
        ValidityReasonCode.SOURCE_INCOMPLETE,
        ValidityReasonCode.EXPOSURE_INTEGRITY_FAIL,
        ValidityReasonCode.RECONCILIATION_FAILED,
        ValidityReasonCode.METRIC_DEFINITION_MISMATCH,
        ValidityReasonCode.MISSING_REQUIRED_INPUT,
        ValidityReasonCode.STALE_OR_REVISED_SOURCE,
    }
)

_INCONCLUSIVE_REASONS: frozenset[ValidityReasonCode] = frozenset(
    {
        ValidityReasonCode.OBSERVATION_WINDOW_INCOMPLETE,
        ValidityReasonCode.SOURCE_COMPLETE_THROUGH_GAP,
        ValidityReasonCode.ATTRIBUTION_COVERAGE_LOW,
        ValidityReasonCode.CONCURRENT_INTERVENTION,
    }
)


@dataclass(frozen=True, slots=True)
class ValiditySnapshot:
    """Validity projection attached to an evaluation or experiment shell."""

    status: DataValidityStatus
    reason_codes: tuple[ValidityReasonCode, ...] = ()
    hard_fail_required_conditions: bool = False


def project_outcome_from_validity(
    *,
    validity: ValiditySnapshot,
    criteria_met: bool | None,
    criteria_failed: bool | None,
    frozen_plan_digest: str | None = None,
    registration_kind_confirmatory: bool = False,
) -> Outcome:
    """Map validity + criteria to outcome per ``demem_outcome_v1``."""
    if registration_kind_confirmatory and frozen_plan_digest is None:
        return Outcome.PENDING
    if validity.hard_fail_required_conditions:
        return Outcome.INVALID
    if validity.status == DataValidityStatus.INVALID:
        return Outcome.INVALID
    for code in validity.reason_codes:
        if code in _INVALID_REASONS:
            return Outcome.INVALID
    for code in validity.reason_codes:
        if code in _INCONCLUSIVE_REASONS:
            return Outcome.INCONCLUSIVE
    if validity.status in (DataValidityStatus.UNKNOWN, DataValidityStatus.PARTIAL):
        return Outcome.INCONCLUSIVE
    if criteria_met is True:
        return Outcome.SUCCEEDED
    if criteria_failed is True:
        return Outcome.FAILED
    return Outcome.INCONCLUSIVE


def abort_execution_outcome() -> Outcome:
    """V1 abort projection: ``ABORTED`` execution keeps ``outcome=PENDING``."""
    return Outcome.PENDING
