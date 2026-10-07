"""Append-only event taxonomy for Slice A projections."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from app.modules.decision_experiment_memory.domain.plan import ExperimentPlan
from app.modules.decision_experiment_memory.domain.records import (
    DecisionMemoryRecord,
)
from app.modules.decision_experiment_memory.domain.refs import (
    ApplyEvidenceRef,
    ChangeSetRef,
)


class MemoryEventType(StrEnum):
    """Event types for in-memory event log (Slice A)."""

    DECISION_RECORDED = "DECISION_RECORDED"
    PLAN_REGISTERED = "PLAN_REGISTERED"
    PLAN_FROZEN = "PLAN_FROZEN"
    PROTOCOL_DEVIATION = "PROTOCOL_DEVIATION"
    CHANGESET_LINKED = "CHANGESET_LINKED"
    APPLY_LINKED = "APPLY_LINKED"
    EXPOSURE_CONFIRMED = "EXPOSURE_CONFIRMED"
    EXECUTION_ABORTED = "EXECUTION_ABORTED"
    OUTCOME_PROJECTED = "OUTCOME_PROJECTED"


@dataclass(frozen=True, slots=True)
class MemoryEvent:
    """Single append-only memory event."""

    event_id: str
    event_type: MemoryEventType
    occurred_at: datetime
    decision_id: str | None = None
    experiment_id: str | None = None
    payload: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class PlanRegisteredPayload:
    plan: ExperimentPlan


@dataclass(frozen=True, slots=True)
class PlanFrozenPayload:
    plan_revision: int
    plan_digest: str


@dataclass(frozen=True, slots=True)
class ProtocolDeviationPayload:
    plan_revision: int
    frozen_plan_digest: str
    reason: str


@dataclass(frozen=True, slots=True)
class DecisionRecordedPayload:
    record: DecisionMemoryRecord


@dataclass(frozen=True, slots=True)
class ChangeSetLinkedPayload:
    changeset_ref: ChangeSetRef


@dataclass(frozen=True, slots=True)
class ApplyLinkedPayload:
    apply_evidence_ref: ApplyEvidenceRef


@dataclass(frozen=True, slots=True)
class ExposureConfirmedPayload:
    effective_from: datetime
    observation_start: datetime
    resulting_state_token: str


@dataclass(frozen=True, slots=True)
class OutcomeProjectedPayload:
    outcome: str
    execution_state: str
