"""Reader and repository protocols (ports)."""

from __future__ import annotations

from typing import Protocol

from app.modules.decision_experiment_memory.domain.plan import ExperimentPlan
from app.modules.decision_experiment_memory.domain.records import (
    DecisionMemoryRecord,
    ExperimentRecordV1,
)
from app.modules.decision_experiment_memory.events import MemoryEvent


class DecisionMemoryReader(Protocol):
    """Read-only projection access for decision/experiment memory."""

    def get_decision(self, decision_id: str) -> DecisionMemoryRecord | None: ...

    def list_experiments_for_decision(
        self,
        decision_id: str,
    ) -> tuple[ExperimentRecordV1, ...]: ...

    def get_experiment(self, experiment_id: str) -> ExperimentRecordV1 | None: ...

    def get_plan_revision(
        self,
        experiment_id: str,
        plan_revision: int,
    ) -> ExperimentPlan | None: ...

    def list_events(
        self,
        *,
        decision_id: str | None = None,
        experiment_id: str | None = None,
    ) -> tuple[MemoryEvent, ...]: ...


class DecisionMemoryRepository(Protocol):
    """Append-only writer port (production impl deferred to Slice B)."""

    def append_event(self, event: MemoryEvent) -> None: ...

    def save_decision(self, record: DecisionMemoryRecord) -> None: ...

    def save_experiment(self, record: ExperimentRecordV1) -> None: ...

    def save_plan(self, plan: ExperimentPlan) -> None: ...
