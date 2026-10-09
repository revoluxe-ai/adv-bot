"""TEST-ONLY in-memory fake for unit tests (Slice A).

Not a production store, runtime singleton, or process-local memory tier.
Production persistence is Slice B+ (PostgreSQL); this module MUST NOT be used
outside ``tests/`` and decision-memory unit test harnesses.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

from app.modules.decision_experiment_memory.domain.enums import (
    DecisionStatus,
    ExecutionState,
    RegistrationKind,
)
from app.modules.decision_experiment_memory.domain.factual import FactualResult
from app.modules.decision_experiment_memory.domain.index import (
    ExperimentMemoryIndexEntry,
)
from app.modules.decision_experiment_memory.domain.plan import (
    ExperimentPlan,
    ExperimentPlanBody,
    build_plan,
)
from app.modules.decision_experiment_memory.domain.records import (
    DecisionMemoryRecord,
    ExperimentRecordV1,
    new_experiment_shell,
)
from app.modules.decision_experiment_memory.domain.refs import ApplyEvidenceRef
from app.modules.decision_experiment_memory.events import (
    ConfounderDetectedPayload,
    ExposureConfirmedPayload,
    MemoryEvent,
    MemoryEventType,
)
from app.modules.decision_experiment_memory.plan_freeze import (
    assert_plan_revision_unchanged,
    freeze_plan_on_experiment,
)
from app.modules.decision_experiment_memory.projections import (
    build_confirmed_exposure_model,
    with_aborted_execution,
    with_exposure_confirmed,
)
from app.modules.decision_experiment_memory.protocols import DecisionMemoryRepository


class InMemoryDecisionMemoryRepository(DecisionMemoryRepository):
    """Test-only fake: append-only events + replaceable projection snapshots."""

    def __init__(self) -> None:
        self._decisions: dict[str, DecisionMemoryRecord] = {}
        self._experiments: dict[str, ExperimentRecordV1] = {}
        self._plans: dict[tuple[str, int], ExperimentPlan] = {}
        self._factual_results: dict[str, FactualResult] = {}
        self._confounder_flags: dict[str, tuple[str, ...]] = {}
        self._events: list[MemoryEvent] = []

    def append_event(self, event: MemoryEvent) -> None:
        self._events.append(event)

    def upsert_decision_projection(self, record: DecisionMemoryRecord) -> None:
        if record.status == DecisionStatus.APPLY_CONFIRMED and record.apply_evidence_ref is None:
            raise ValueError("ApplyEvidenceRef required for APPLY_CONFIRMED")
        self._decisions[record.decision_id] = record

    def upsert_experiment_projection(self, record: ExperimentRecordV1) -> None:
        from app.modules.decision_experiment_memory.domain.records import (
            assert_distinct_experiment_identity,
        )

        assert_distinct_experiment_identity(
            decision_id=record.decision_id,
            experiment_id=record.experiment_id,
        )
        from app.modules.decision_experiment_memory.projections import (
            project_live_observing,
            validate_confirmed_exposure,
        )

        validate_confirmed_exposure(
            record,
            exposure=record.exposure,
            apply_evidence_ref=record.exposure.apply_evidence_ref,
        )
        _ = project_live_observing(record)
        self._experiments[record.experiment_id] = record

    def register_plan_revision(self, plan: ExperimentPlan) -> None:
        key = (plan.experiment_id, plan.plan_revision)
        existing = self._plans.get(key)
        if existing is not None:
            assert_plan_revision_unchanged(existing, plan.plan_digest)
            return
        self._plans[key] = plan

    def save_decision(self, record: DecisionMemoryRecord) -> None:
        """Deprecated alias for projection upsert (test ergonomics)."""
        self.upsert_decision_projection(record)

    def save_experiment(self, record: ExperimentRecordV1) -> None:
        """Deprecated alias for projection upsert (test ergonomics)."""
        self.upsert_experiment_projection(record)

    def save_plan(self, plan: ExperimentPlan) -> None:
        """Deprecated alias for immutable plan registration."""
        self.register_plan_revision(plan)

    def get_decision(self, decision_id: str) -> DecisionMemoryRecord | None:
        return self._decisions.get(decision_id)

    def list_experiments_for_decision(
        self,
        decision_id: str,
    ) -> tuple[ExperimentRecordV1, ...]:
        return tuple(
            e for e in self._experiments.values() if e.decision_id == decision_id
        )

    def get_experiment(self, experiment_id: str) -> ExperimentRecordV1 | None:
        return self._experiments.get(experiment_id)

    def get_experiment_plan(
        self,
        experiment_id: str,
        plan_revision: int | None = None,
    ) -> ExperimentPlan | None:
        if plan_revision is not None:
            return self.get_plan_revision(experiment_id, plan_revision)
        revisions = self.list_plan_revisions(experiment_id)
        if not revisions:
            return None
        return revisions[-1]

    def get_plan_revision(
        self,
        experiment_id: str,
        plan_revision: int,
    ) -> ExperimentPlan | None:
        return self._plans.get((experiment_id, plan_revision))

    def list_plan_revisions(self, experiment_id: str) -> tuple[ExperimentPlan, ...]:
        plans = [p for (eid, _), p in self._plans.items() if eid == experiment_id]
        return tuple(sorted(plans, key=lambda p: p.plan_revision))

    def get_factual_result(self, factual_result_id: str) -> FactualResult | None:
        return self._factual_results.get(factual_result_id)

    def list_factual_results_for_experiment(
        self,
        experiment_id: str,
    ) -> tuple[FactualResult, ...]:
        return tuple(
            r for r in self._factual_results.values() if r.experiment_id == experiment_id
        )

    def store_factual_result(self, result: FactualResult) -> None:
        """Projection upsert for factual results (evaluator-owned in later slices)."""
        self._factual_results[result.factual_result_id] = result
        experiment = self.get_experiment(result.experiment_id)
        if experiment is not None:
            ids = tuple(
                dict.fromkeys((*experiment.factual_result_ids, result.factual_result_id))
            )
            self.upsert_experiment_projection(
                replace(experiment, factual_result_ids=ids)
            )

    def list_observing_experiments(self, shop_id: str) -> tuple[ExperimentRecordV1, ...]:
        decision_shop = {
            d.decision_id: d.shop_id for d in self._decisions.values()
        }
        return tuple(
            e
            for e in self._experiments.values()
            if e.execution_state == ExecutionState.OBSERVING
            and decision_shop.get(e.decision_id) == shop_id
        )

    def find_similar_experiments(
        self,
        *,
        intervention_signature_digest: str,
        shop_id: str,
        limit: int = 10,
    ) -> tuple[ExperimentRecordV1, ...]:
        decision_shop = {
            d.decision_id: d.shop_id for d in self._decisions.values()
        }
        matches = [
            e
            for e in self._experiments.values()
            if e.intervention_signature_digest == intervention_signature_digest
            and decision_shop.get(e.decision_id) == shop_id
        ]
        return tuple(matches[:limit])

    def get_experiment_memory_index(
        self,
        shop_id: str,
    ) -> tuple[ExperimentMemoryIndexEntry, ...]:
        entries: list[ExperimentMemoryIndexEntry] = []
        for experiment in self._experiments.values():
            decision = self.get_decision(experiment.decision_id)
            if decision is None or decision.shop_id != shop_id:
                continue
            entries.append(
                ExperimentMemoryIndexEntry(
                    experiment_id=experiment.experiment_id,
                    decision_id=experiment.decision_id,
                    shop_id=shop_id,
                    intervention_signature_digest=experiment.intervention_signature_digest,
                    experiment_design=experiment.experiment_design.value,
                    treatment_mode=experiment.treatment_mode.value,
                    execution_state=experiment.execution_state.value,
                    outcome=experiment.outcome.value,
                    confounder_flags=self._confounder_flags.get(
                        experiment.experiment_id,
                        (),
                    ),
                )
            )
        return tuple(entries)

    def list_events(
        self,
        *,
        decision_id: str | None = None,
        experiment_id: str | None = None,
    ) -> tuple[MemoryEvent, ...]:
        out: list[MemoryEvent] = []
        for event in self._events:
            if decision_id is not None and event.decision_id != decision_id:
                continue
            if experiment_id is not None and event.experiment_id != experiment_id:
                continue
            out.append(event)
        return tuple(out)

    def record_decision(
        self,
        record: DecisionMemoryRecord,
    ) -> None:
        """Append decision and emit DECISION_RECORDED."""
        self.save_decision(record)
        self.append_event(
            MemoryEvent(
                event_id=str(uuid4()),
                event_type=MemoryEventType.DECISION_RECORDED,
                occurred_at=record.created_at,
                decision_id=record.decision_id,
                payload={"status": record.status.value},
            )
        )

    def register_experiment_with_plan(
        self,
        *,
        decision_id: str,
        experiment_id: str,
        plan_body: ExperimentPlanBody,
        registration_kind: RegistrationKind,
        intervention_signature_digest: str,
        registered_at: datetime | None = None,
    ) -> ExperimentRecordV1:
        """Create experiment shell + plan revision 1."""
        when = registered_at or datetime.now(tz=timezone.utc)
        body = plan_body
        body = replace(body, experiment_id=experiment_id)
        plan = build_plan(
            experiment_id=experiment_id,
            plan_revision=1,
            registered_at=when,
            registration_kind=registration_kind,
            body=body,
        )
        shell = new_experiment_shell(
            experiment_id=experiment_id,
            decision_id=decision_id,
            treatment_mode=plan.treatment_mode,
            experiment_design=plan.experiment_design,
            intervention_signature_digest=intervention_signature_digest,
            active_plan_revision=1,
        )
        self.save_plan(plan)
        self.save_experiment(shell)
        self.append_event(
            MemoryEvent(
                event_id=str(uuid4()),
                event_type=MemoryEventType.PLAN_REGISTERED,
                occurred_at=when,
                decision_id=decision_id,
                experiment_id=experiment_id,
                payload={"plan_revision": 1, "plan_digest": plan.plan_digest},
            )
        )
        return shell

    def freeze_plan(
        self,
        experiment_id: str,
        plan_revision: int,
        occurred_at: datetime | None = None,
    ) -> ExperimentRecordV1:
        """Emit PLAN_FROZEN and set frozen digest on experiment."""
        plan = self.get_plan_revision(experiment_id, plan_revision)
        if plan is None:
            raise KeyError(f"plan revision {plan_revision} missing")
        experiment = self.get_experiment(experiment_id)
        if experiment is None:
            raise KeyError(f"experiment {experiment_id} missing")
        frozen = freeze_plan_on_experiment(experiment, plan)
        self.save_experiment(frozen)
        when = occurred_at or datetime.now(tz=timezone.utc)
        self.append_event(
            MemoryEvent(
                event_id=str(uuid4()),
                event_type=MemoryEventType.PLAN_FROZEN,
                occurred_at=when,
                experiment_id=experiment_id,
                payload={
                    "plan_revision": plan_revision,
                    "plan_digest": plan.plan_digest,
                },
            )
        )
        return frozen

    def append_protocol_deviation(
        self,
        experiment_id: str,
        *,
        plan_revision: int,
        reason: str,
        occurred_at: datetime | None = None,
    ) -> None:
        """Append PROTOCOL_DEVIATION without mutating frozen plan bytes."""
        experiment = self.get_experiment(experiment_id)
        if experiment is None:
            raise KeyError(experiment_id)
        when = occurred_at or datetime.now(tz=timezone.utc)
        self.append_event(
            MemoryEvent(
                event_id=str(uuid4()),
                event_type=MemoryEventType.PROTOCOL_DEVIATION,
                occurred_at=when,
                experiment_id=experiment_id,
                payload={
                    "plan_revision": plan_revision,
                    "frozen_plan_digest": experiment.frozen_plan_digest,
                    "reason": reason,
                },
            )
        )

    def link_decision_status(
        self,
        decision_id: str,
        status: DecisionStatus,
    ) -> DecisionMemoryRecord:
        """Update decision status (no auto APPLY_CONFIRMED without evidence)."""
        record = self.get_decision(decision_id)
        if record is None:
            raise KeyError(decision_id)
        if status == DecisionStatus.APPLY_CONFIRMED and record.apply_evidence_ref is None:
            raise ValueError("ApplyEvidenceRef required for APPLY_CONFIRMED")
        updated = DecisionMemoryRecord(
            decision_id=record.decision_id,
            shop_id=record.shop_id,
            status=status,
            created_at=record.created_at,
            observation=record.observation,
            rationale=record.rationale,
            intended_action=record.intended_action,
            decision_fingerprint=record.decision_fingerprint,
            changeset_ref=record.changeset_ref,
            apply_evidence_ref=record.apply_evidence_ref,
            dry_run_receipt_id=record.dry_run_receipt_id,
        )
        self.save_decision(updated)
        return updated

    def confirm_exposure(
        self,
        experiment_id: str,
        *,
        apply_evidence_ref: ApplyEvidenceRef,
        effective_from: datetime,
        observation_start: datetime,
        state_token: str,
    ) -> ExperimentRecordV1:
        """Emit EXPOSURE_CONFIRMED and update exposure model (LIVE gate enforced)."""
        experiment = self.get_experiment(experiment_id)
        if experiment is None:
            raise KeyError(experiment_id)
        exposure = build_confirmed_exposure_model(
            experiment,
            apply_evidence_ref=apply_evidence_ref,
            resulting_state_token=state_token,
            effective_from=effective_from,
            observation_start=observation_start,
        )
        updated = with_exposure_confirmed(
            experiment,
            exposure=exposure,
            apply_evidence_ref=apply_evidence_ref,
        )
        self.upsert_experiment_projection(updated)
        exposure_payload = ExposureConfirmedPayload(
            effective_from=effective_from,
            observation_start=observation_start,
            resulting_state_token=state_token,
            apply_evidence_id=apply_evidence_ref.apply_evidence_id,
            evidence_digest=apply_evidence_ref.evidence_digest,
            authority_kind=apply_evidence_ref.authority_kind,
        )
        self.append_event(
            MemoryEvent(
                event_id=str(uuid4()),
                event_type=MemoryEventType.EXPOSURE_CONFIRMED,
                occurred_at=datetime.now(tz=timezone.utc),
                experiment_id=experiment_id,
                payload={
                    "effective_from": exposure_payload.effective_from.isoformat(),
                    "observation_start": exposure_payload.observation_start.isoformat(),
                    "resulting_state_token": exposure_payload.resulting_state_token,
                    "apply_evidence_id": exposure_payload.apply_evidence_id,
                    "evidence_digest": exposure_payload.evidence_digest,
                    "authority_kind": exposure_payload.authority_kind,
                },
            )
        )
        return updated

    def abort_experiment(self, experiment_id: str) -> ExperimentRecordV1:
        """Emit EXECUTION_ABORTED with V1 outcome projection."""
        experiment = self.get_experiment(experiment_id)
        if experiment is None:
            raise KeyError(experiment_id)
        aborted = with_aborted_execution(experiment)
        self.save_experiment(aborted)
        self.append_event(
            MemoryEvent(
                event_id=str(uuid4()),
                event_type=MemoryEventType.EXECUTION_ABORTED,
                occurred_at=datetime.now(tz=timezone.utc),
                experiment_id=experiment_id,
            )
        )
        return aborted

    def append_confounder_detected(
        self,
        experiment_id: str,
        payload: ConfounderDetectedPayload,
        *,
        occurred_at: datetime | None = None,
    ) -> MemoryEvent:
        """Append structured CONFOUNDER_DETECTED (detection runtime deferred)."""
        when = occurred_at or datetime.now(tz=timezone.utc)
        flags = self._confounder_flags.get(experiment_id, ())
        self._confounder_flags[experiment_id] = (*flags, payload.category.value)
        event = MemoryEvent(
            event_id=str(uuid4()),
            event_type=MemoryEventType.CONFOUNDER_DETECTED,
            occurred_at=when,
            experiment_id=experiment_id,
            payload={
                "category": payload.category.value,
                "reason": payload.reason,
                "settings_state_token": payload.settings_state_token,
                "related_decision_id": payload.related_decision_id,
                "related_experiment_id": payload.related_experiment_id,
                "external_fact_id": payload.external_fact_id,
            },
        )
        self.append_event(event)
        return event
