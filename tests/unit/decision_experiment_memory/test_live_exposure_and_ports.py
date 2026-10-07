"""LIVE exposure gate, confounder events, and reader port shape."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.modules.decision_experiment_memory.domain.enums import (
    ControlDefinitionKind,
    DecisionStatus,
    ExecutionState,
    ExperimentDesign,
    RegistrationKind,
    TreatmentMode,
)
from app.modules.decision_experiment_memory.domain.factual import (
    FactualResult,
    MetricValue,
)
from app.modules.decision_experiment_memory.domain.plan import (
    ControlDefinition,
    ExperimentPlanBody,
    TreatmentDefinition,
)
from app.modules.decision_experiment_memory.domain.records import DecisionMemoryRecord
from app.modules.decision_experiment_memory.domain.refs import (
    ApplyEvidenceRef,
    MetricSpecRef,
)
from app.modules.decision_experiment_memory.errors import ExposureInvariantError
from app.modules.decision_experiment_memory.events import (
    ConfounderCategory,
    ConfounderDetectedPayload,
    MemoryEventType,
)
from app.modules.decision_experiment_memory.intervention_signature import (
    intervention_signature_digest,
)
from app.modules.decision_experiment_memory.testing.in_memory_repository import (
    InMemoryDecisionMemoryRepository,
)

pytestmark = pytest.mark.unit


def _register_live_experiment(repo: InMemoryDecisionMemoryRepository) -> str:
    when = datetime(2026, 1, 1, tzinfo=timezone.utc)
    repo.upsert_decision_projection(
        DecisionMemoryRecord(
            decision_id="d-1",
            shop_id="shop-1",
            status=DecisionStatus.RECORDED,
            created_at=when,
            observation="o",
            rationale="r",
            intended_action="a",
        )
    )
    treatment = TreatmentDefinition(
        setting_keys=("bid",),
        old_values={"bid": 1},
        new_values={"bid": 2},
    )
    body = ExperimentPlanBody(
        experiment_id="e-1",
        hypothesis={"h": 1},
        treatment_definition=treatment,
        control_definition=ControlDefinition(
            kind=ControlDefinitionKind.PRIOR_CONFIGURATION,
            state_token="st",
        ),
        experiment_design=ExperimentDesign.RANDOMIZED_AB,
        treatment_mode=TreatmentMode.LIVE,
        primary_metrics=(
            MetricSpecRef(
                metric_id="m",
                metric_definition_version="1",
                source_family="CH",
                grain="day",
                scope="shop",
                numerator_semantics="n",
            ),
        ),
    )
    repo.register_experiment_with_plan(
        decision_id="d-1",
        experiment_id="e-1",
        plan_body=body,
        registration_kind=RegistrationKind.PREREGISTERED_CONFIRMATORY,
        intervention_signature_digest=intervention_signature_digest(treatment),
    )
    return "e-1"


def test_live_confirm_exposure_without_authoritative_state_rejected() -> None:
    repo = InMemoryDecisionMemoryRepository()
    experiment_id = _register_live_experiment(repo)
    when = datetime(2026, 1, 2, tzinfo=timezone.utc)
    with pytest.raises(ExposureInvariantError):
        repo.confirm_exposure(
            experiment_id,
            apply_evidence_ref=ApplyEvidenceRef("apply-1"),
            effective_from=when,
            observation_start=when,
            state_token="",
        )


def test_live_confirmed_exposure_requires_apply_ref() -> None:
    repo = InMemoryDecisionMemoryRepository()
    experiment_id = _register_live_experiment(repo)
    experiment = repo.get_experiment(experiment_id)
    assert experiment is not None
    from app.modules.decision_experiment_memory.domain.records import ExposureModel
    from app.modules.decision_experiment_memory.projections import (
        validate_confirmed_exposure,
    )

    with pytest.raises(ExposureInvariantError):
        validate_confirmed_exposure(
            experiment,
            exposure=ExposureModel(
                exposure_confirmed=True,
                effective_from=datetime(2026, 1, 2, tzinfo=timezone.utc),
                resulting_state_token="st",
            ),
            apply_evidence_ref=None,
        )


def test_live_confirm_exposure_with_apply_ref_succeeds() -> None:
    repo = InMemoryDecisionMemoryRepository()
    experiment_id = _register_live_experiment(repo)
    when = datetime(2026, 1, 2, tzinfo=timezone.utc)
    apply_ref = ApplyEvidenceRef(
        apply_evidence_id="apply-1",
        evidence_digest="digest-1",
        authority_kind="APPLY_AUTHORITY_V1",
    )
    updated = repo.confirm_exposure(
        experiment_id,
        apply_evidence_ref=apply_ref,
        effective_from=when,
        observation_start=when,
        state_token="st-live",
    )
    assert updated.execution_state == ExecutionState.OBSERVING
    assert updated.exposure.apply_evidence_ref == apply_ref


def test_confounder_detected_append_and_index() -> None:
    repo = InMemoryDecisionMemoryRepository()
    experiment_id = _register_live_experiment(repo)
    repo.append_confounder_detected(
        experiment_id,
        ConfounderDetectedPayload(
            category=ConfounderCategory.PRICE_CHANGE,
            reason="promo",
            settings_state_token="st-promo",
        ),
    )
    events = repo.list_events(experiment_id=experiment_id)
    assert any(e.event_type == MemoryEventType.CONFOUNDER_DETECTED for e in events)
    index = repo.get_experiment_memory_index("shop-1")
    assert index[0].confounder_flags == ("PRICE_CHANGE",)


def test_reader_ports_factual_and_similar() -> None:
    repo = InMemoryDecisionMemoryRepository()
    experiment_id = _register_live_experiment(repo)
    when = datetime(2026, 1, 3, tzinfo=timezone.utc)
    metric = MetricSpecRef(
        metric_id="m",
        metric_definition_version="1",
        source_family="CH",
        grain="day",
        scope="shop",
        numerator_semantics="n",
    )
    result = FactualResult(
        factual_result_id="fr-1",
        experiment_id=experiment_id,
        frozen_plan_digest="dig",
        recorded_at=when,
        metric_values=(MetricValue(spec=metric, value=1.0),),
        outcome_digest="od",
    )
    repo.store_factual_result(result)
    assert repo.get_factual_result("fr-1") == result
    sig = repo.get_experiment(experiment_id).intervention_signature_digest
    similar = repo.find_similar_experiments(
        intervention_signature_digest=sig,
        shop_id="shop-1",
    )
    assert len(similar) == 1
