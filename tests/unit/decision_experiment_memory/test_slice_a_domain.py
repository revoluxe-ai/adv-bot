"""Slice A unit tests for decision-experiment-memory domain invariants."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.modules.decision_experiment_memory.domain.enums import (
    ControlDefinitionKind,
    DataValidityStatus,
    DecisionStatus,
    ExecutionState,
    ExperimentDesign,
    Outcome,
    RegistrationKind,
    TreatmentMode,
    ValidityReasonCode,
)
from app.modules.decision_experiment_memory.domain.plan import (
    ControlDefinition,
    ExperimentPlanBody,
    TreatmentDefinition,
    build_plan,
)
from app.modules.decision_experiment_memory.domain.plan_serialization import (
    plan_body_digest,
)
from app.modules.decision_experiment_memory.domain.records import (
    DecisionMemoryRecord,
    assert_distinct_experiment_identity,
    new_experiment_shell,
)
from app.modules.decision_experiment_memory.domain.refs import (
    ApplyEvidenceRef,
    MetricSpecRef,
)
from app.modules.decision_experiment_memory.domain.validity import (
    ValiditySnapshot,
    abort_execution_outcome,
    project_outcome_from_validity,
)
from app.modules.decision_experiment_memory.domain.window import (
    ExperimentWindowModel,
    compute_observation_start,
    with_observation_start_from_exposure,
)
from app.modules.decision_experiment_memory.errors import (
    IdentityInvariantError,
    PlanInvariantError,
)
from app.modules.decision_experiment_memory.intervention_signature import (
    intervention_signature_digest,
)
from app.modules.decision_experiment_memory.plan_freeze import (
    require_frozen_for_confirmatory_evaluation,
)
from app.modules.decision_experiment_memory.projections import with_aborted_execution
from app.modules.decision_experiment_memory.testing.in_memory_repository import (
    InMemoryDecisionMemoryRepository,
)

pytestmark = pytest.mark.unit


def _metric() -> MetricSpecRef:
    return MetricSpecRef(
        metric_id="orders",
        metric_definition_version="1",
        source_family="CH",
        grain="day",
        scope="shop",
        numerator_semantics="orders",
    )


def _plan_body(experiment_id: str) -> ExperimentPlanBody:
    treatment = TreatmentDefinition(
        setting_keys=("bid",),
        old_values={"bid": 10},
        new_values={"bid": 12},
        scope_shop_id="shop-1",
    )
    return ExperimentPlanBody(
        experiment_id=experiment_id,
        hypothesis={"statement": "bid lift"},
        treatment_definition=treatment,
        control_definition=ControlDefinition(
            kind=ControlDefinitionKind.PRIOR_CONFIGURATION,
            state_token="st1",
        ),
        experiment_design=ExperimentDesign.BEFORE_AFTER_OBSERVATIONAL,
        treatment_mode=TreatmentMode.SHADOW,
        primary_metrics=(_metric(),),
    )


def test_decision_without_experiment() -> None:
    repo = InMemoryDecisionMemoryRepository()
    created = datetime(2026, 1, 1, tzinfo=timezone.utc)
    repo.record_decision(
        DecisionMemoryRecord(
            decision_id="d-1",
            shop_id="shop-1",
            status=DecisionStatus.RECORDED,
            created_at=created,
            observation="obs",
            rationale="why",
            intended_action="act",
        )
    )
    assert repo.get_decision("d-1") is not None
    assert repo.list_experiments_for_decision("d-1") == ()


def test_distinct_experiment_and_decision_ids() -> None:
    assert_distinct_experiment_identity(
        decision_id="d-1",
        experiment_id="e-1",
    )
    with pytest.raises(IdentityInvariantError):
        assert_distinct_experiment_identity(
            decision_id="same",
            experiment_id="same",
        )


def test_two_experiments_one_decision() -> None:
    repo = InMemoryDecisionMemoryRepository()
    created = datetime(2026, 1, 1, tzinfo=timezone.utc)
    repo.record_decision(
        DecisionMemoryRecord(
            decision_id="d-parent",
            shop_id="shop-1",
            status=DecisionStatus.RECORDED,
            created_at=created,
            observation="o",
            rationale="r",
            intended_action="a",
        )
    )
    treatment = TreatmentDefinition(
        setting_keys=("k",),
        old_values={},
        new_values={},
    )
    sig = intervention_signature_digest(treatment)
    repo.register_experiment_with_plan(
        decision_id="d-parent",
        experiment_id="e-a",
        plan_body=_plan_body("e-a"),
        registration_kind=RegistrationKind.PREREGISTERED_CONFIRMATORY,
        intervention_signature_digest=sig,
    )
    repo.register_experiment_with_plan(
        decision_id="d-parent",
        experiment_id="e-b",
        plan_body=_plan_body("e-b"),
        registration_kind=RegistrationKind.PREREGISTERED_CONFIRMATORY,
        intervention_signature_digest=sig,
    )
    assert len(repo.list_experiments_for_decision("d-parent")) == 2


def test_plan_freeze_and_revision_digest_stable() -> None:
    body_v1 = _plan_body("e-1")
    when = datetime(2026, 1, 2, tzinfo=timezone.utc)
    plan1 = build_plan(
        experiment_id="e-1",
        plan_revision=1,
        registered_at=when,
        registration_kind=RegistrationKind.PREREGISTERED_CONFIRMATORY,
        body=body_v1,
    )
    digest1 = plan1.plan_digest
    plan2 = build_plan(
        experiment_id="e-1",
        plan_revision=2,
        registered_at=when,
        registration_kind=RegistrationKind.PREREGISTERED_CONFIRMATORY,
        body=_plan_body("e-1"),
    )
    assert plan2.plan_revision == 2
    assert plan_body_digest(body_v1) == digest1
    repo = InMemoryDecisionMemoryRepository()
    repo.record_decision(
        DecisionMemoryRecord(
            decision_id="d-1",
            shop_id="s",
            status=DecisionStatus.RECORDED,
            created_at=when,
            observation="o",
            rationale="r",
            intended_action="a",
        )
    )
    sig = intervention_signature_digest(body_v1.treatment_definition)
    repo.register_experiment_with_plan(
        decision_id="d-1",
        experiment_id="e-1",
        plan_body=body_v1,
        registration_kind=RegistrationKind.PREREGISTERED_CONFIRMATORY,
        intervention_signature_digest=sig,
    )
    frozen = repo.freeze_plan("e-1", 1)
    assert frozen.frozen_plan_digest == digest1
    still_v1 = repo.get_plan_revision("e-1", 1)
    assert still_v1 is not None
    assert still_v1.plan_digest == digest1


def test_confirmatory_evaluation_requires_freeze() -> None:
    shell = new_experiment_shell(
        experiment_id="e-1",
        decision_id="d-1",
        treatment_mode=TreatmentMode.LIVE,
        experiment_design=ExperimentDesign.RANDOMIZED_AB,
        intervention_signature_digest="sig",
        active_plan_revision=1,
    )
    with pytest.raises(PlanInvariantError):
        require_frozen_for_confirmatory_evaluation(
            shell,
            registration_kind_confirmatory=True,
        )


def test_protocol_deviation_append_only() -> None:
    repo = InMemoryDecisionMemoryRepository()
    when = datetime(2026, 1, 3, tzinfo=timezone.utc)
    repo.record_decision(
        DecisionMemoryRecord(
            decision_id="d-1",
            shop_id="s",
            status=DecisionStatus.RECORDED,
            created_at=when,
            observation="o",
            rationale="r",
            intended_action="a",
        )
    )
    body = _plan_body("e-1")
    sig = intervention_signature_digest(body.treatment_definition)
    repo.register_experiment_with_plan(
        decision_id="d-1",
        experiment_id="e-1",
        plan_body=body,
        registration_kind=RegistrationKind.PREREGISTERED_CONFIRMATORY,
        intervention_signature_digest=sig,
    )
    frozen = repo.freeze_plan("e-1", 1)
    repo.append_protocol_deviation("e-1", plan_revision=1, reason="late metric")
    after = repo.get_experiment("e-1")
    assert after is not None
    assert after.frozen_plan_digest == frozen.frozen_plan_digest
    deviations = [
        e
        for e in repo.list_events(experiment_id="e-1")
        if e.event_type.value == "PROTOCOL_DEVIATION"
    ]
    assert len(deviations) == 1


def test_shadow_mode_not_experiment_design() -> None:
    body = _plan_body("e-1")
    assert body.treatment_mode == TreatmentMode.SHADOW
    assert body.experiment_design == ExperimentDesign.BEFORE_AFTER_OBSERVATIONAL
    assert TreatmentMode.SHADOW not in ExperimentDesign


def test_no_apply_evidence_no_apply_confirmed() -> None:
    repo = InMemoryDecisionMemoryRepository()
    when = datetime(2026, 1, 1, tzinfo=timezone.utc)
    repo.record_decision(
        DecisionMemoryRecord(
            decision_id="d-1",
            shop_id="s",
            status=DecisionStatus.RECORDED,
            created_at=when,
            observation="o",
            rationale="r",
            intended_action="a",
        )
    )
    with pytest.raises(ValueError):
        repo.link_decision_status("d-1", DecisionStatus.APPLY_CONFIRMED)
    repo.save_decision(
        DecisionMemoryRecord(
            decision_id="d-1",
            shop_id="s",
            status=DecisionStatus.RECORDED,
            created_at=when,
            observation="o",
            rationale="r",
            intended_action="a",
            apply_evidence_ref=ApplyEvidenceRef("apply-1"),
        )
    )
    confirmed = repo.link_decision_status("d-1", DecisionStatus.APPLY_CONFIRMED)
    assert confirmed.status == DecisionStatus.APPLY_CONFIRMED


def test_observation_start_from_exposure_not_decision_time() -> None:
    effective = datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc)
    decision_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    window = ExperimentWindowModel(timezone="UTC")
    updated = with_observation_start_from_exposure(
        window,
        effective_from=effective,
        burn_in=timedelta(days=1),
    )
    assert updated.observation_start == compute_observation_start(
        effective_from=effective,
        burn_in=timedelta(days=1),
    )
    assert updated.observation_start != decision_time


def test_abort_execution_outcome_pending() -> None:
    shell = new_experiment_shell(
        experiment_id="e-1",
        decision_id="d-1",
        treatment_mode=TreatmentMode.LIVE,
        experiment_design=ExperimentDesign.RANDOMIZED_AB,
        intervention_signature_digest="sig",
        active_plan_revision=1,
    )
    aborted = with_aborted_execution(shell)
    assert aborted.execution_state == ExecutionState.ABORTED
    assert aborted.outcome == Outcome.PENDING
    assert aborted.outcome == abort_execution_outcome()


def test_outcome_mapping_invalid_vs_inconclusive() -> None:
    invalid = project_outcome_from_validity(
        validity=ValiditySnapshot(
            status=DataValidityStatus.INVALID,
            reason_codes=(ValidityReasonCode.EXPOSURE_INTEGRITY_FAIL,),
        ),
        criteria_met=None,
        criteria_failed=None,
    )
    assert invalid == Outcome.INVALID
    inconclusive = project_outcome_from_validity(
        validity=ValiditySnapshot(
            status=DataValidityStatus.PARTIAL,
            reason_codes=(ValidityReasonCode.OBSERVATION_WINDOW_INCOMPLETE,),
        ),
        criteria_met=None,
        criteria_failed=None,
    )
    assert inconclusive == Outcome.INCONCLUSIVE


def test_confirmatory_outcome_stays_pending_without_freeze() -> None:
    outcome = project_outcome_from_validity(
        validity=ValiditySnapshot(status=DataValidityStatus.VALID),
        criteria_met=True,
        criteria_failed=False,
        frozen_plan_digest=None,
        registration_kind_confirmatory=True,
    )
    assert outcome == Outcome.PENDING


def test_plan_revision_immutable_on_save() -> None:
    body = _plan_body("e-1")
    when = datetime(2026, 1, 1, tzinfo=timezone.utc)
    plan = build_plan(
        experiment_id="e-1",
        plan_revision=1,
        registered_at=when,
        registration_kind=RegistrationKind.PREREGISTERED_CONFIRMATORY,
        body=body,
    )
    repo = InMemoryDecisionMemoryRepository()
    repo.save_plan(plan)
    mutated_body = ExperimentPlanBody(
        experiment_id="e-1",
        hypothesis={"statement": "changed"},
        treatment_definition=body.treatment_definition,
        control_definition=body.control_definition,
        experiment_design=body.experiment_design,
        treatment_mode=body.treatment_mode,
        primary_metrics=body.primary_metrics,
    )
    plan2 = build_plan(
        experiment_id="e-1",
        plan_revision=1,
        registered_at=when,
        registration_kind=RegistrationKind.PREREGISTERED_CONFIRMATORY,
        body=mutated_body,
    )
    with pytest.raises(PlanInvariantError):
        repo.save_plan(plan2)


def test_evaluated_succeeded_when_valid() -> None:
    outcome = project_outcome_from_validity(
        validity=ValiditySnapshot(status=DataValidityStatus.VALID),
        criteria_met=True,
        criteria_failed=False,
    )
    assert outcome == Outcome.SUCCEEDED


def test_live_without_exposure_not_observing() -> None:
    shell = new_experiment_shell(
        experiment_id="e-1",
        decision_id="d-1",
        treatment_mode=TreatmentMode.LIVE,
        experiment_design=ExperimentDesign.RANDOMIZED_AB,
        intervention_signature_digest="sig",
        active_plan_revision=1,
    )
    assert shell.exposure.exposure_confirmed is False
    assert shell.execution_state != ExecutionState.OBSERVING
