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
    CONFOUNDER_DETECTED = "CONFOUNDER_DETECTED"


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
    apply_evidence_id: str
    evidence_digest: str | None = None
    authority_kind: str = "APPLY_AUTHORITY"


@dataclass(frozen=True, slots=True)
class OutcomeProjectedPayload:
    outcome: str
    execution_state: str


class ConfounderCategory(StrEnum):
    """Typed concurrent intervention / confounder categories."""

    PRICE_CHANGE = "PRICE_CHANGE"
    STOCK_AVAILABILITY = "STOCK_AVAILABILITY"
    BUDGET_CHANGE = "BUDGET_CHANGE"
    DRR_CPO_CHANGE = "DRR_CPO_CHANGE"
    CAMPAIGN_ACTIVATION = "CAMPAIGN_ACTIVATION"
    ASSORTMENT_CHANGE = "ASSORTMENT_CHANGE"
    OVERLAPPING_EXPERIMENT = "OVERLAPPING_EXPERIMENT"


@dataclass(frozen=True, slots=True)
class ConfounderDetectedPayload:
    """Structured confounder append payload (refs only)."""

    category: ConfounderCategory
    reason: str
    settings_state_token: str | None = None
    related_decision_id: str | None = None
    related_experiment_id: str | None = None
    external_fact_id: str | None = None
