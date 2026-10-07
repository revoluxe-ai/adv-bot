"""Reader and repository protocols (ports)."""

from __future__ import annotations

from typing import Protocol

from app.modules.decision_experiment_memory.domain.factual import FactualResult
from app.modules.decision_experiment_memory.domain.index import (
    ExperimentMemoryIndexEntry,
)
from app.modules.decision_experiment_memory.domain.plan import ExperimentPlan
from app.modules.decision_experiment_memory.domain.records import (
    DecisionMemoryRecord,
    ExperimentRecordV1,
)
from app.modules.decision_experiment_memory.events import MemoryEvent


class DecisionMemoryReader(Protocol):
    """Transport-independent read contract for decision/experiment memory."""

    def get_decision(self, decision_id: str) -> DecisionMemoryRecord | None: ...

    def list_experiments_for_decision(
        self,
        decision_id: str,
    ) -> tuple[ExperimentRecordV1, ...]: ...

    def get_experiment(self, experiment_id: str) -> ExperimentRecordV1 | None: ...

    def list_plan_revisions(
        self,
        experiment_id: str,
    ) -> tuple[ExperimentPlan, ...]: ...

    def get_plan_revision(
        self,
        experiment_id: str,
        plan_revision: int,
    ) -> ExperimentPlan | None: ...

    def get_factual_result(
        self,
        factual_result_id: str,
    ) -> FactualResult | None: ...

    def list_factual_results_for_experiment(
        self,
        experiment_id: str,
    ) -> tuple[FactualResult, ...]: ...

    def list_observing_experiments(
        self,
        shop_id: str,
    ) -> tuple[ExperimentRecordV1, ...]: ...

    def find_similar_experiments(
        self,
        *,
        intervention_signature_digest: str,
        shop_id: str,
        limit: int = 10,
    ) -> tuple[ExperimentRecordV1, ...]: ...

    def get_experiment_memory_index(
        self,
        shop_id: str,
    ) -> tuple[ExperimentMemoryIndexEntry, ...]: ...

    def list_events(
        self,
        *,
        decision_id: str | None = None,
        experiment_id: str | None = None,
    ) -> tuple[MemoryEvent, ...]: ...


class DecisionMemoryEventAppender(Protocol):
    """Append-only immutable event log (Slice B persistence target)."""

    def append_event(self, event: MemoryEvent) -> None: ...


class DecisionMemoryProjectionWriter(Protocol):
    """Replace derived projection snapshots (NOT immutable event persistence).

    Production Slice B projectors may rebuild these from the event log. The test
    fake uses upsert methods for current-state convenience only.
    """

    def upsert_decision_projection(self, record: DecisionMemoryRecord) -> None: ...

    def upsert_experiment_projection(self, record: ExperimentRecordV1) -> None: ...

    def register_plan_revision(self, plan: ExperimentPlan) -> None: ...


class DecisionMemoryRepository(
    DecisionMemoryReader,
    DecisionMemoryEventAppender,
    DecisionMemoryProjectionWriter,
    Protocol,
):
    """Combined port for Slice A test fake (read + append events + projection upserts)."""
