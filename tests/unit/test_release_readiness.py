"""Тесты spec stage-landing-readiness для scope и provenance gates."""

from __future__ import annotations

import pytest

from scripts.release_readiness import (
    CandidateSnapshot,
    CohortBaseline,
    EvidencePhase,
    EvidenceReceipt,
    MigrationRoute,
    ProvenanceMatrix,
    RecoveryAction,
    ReadinessStatus,
    DbRecoveryEvidence,
    choose_migration_route,
    compare_compatibility_baselines,
    compare_snapshots,
    evaluate_final_compatibility,
    evaluate_required_gates,
    validate_release_receipts,
    validate_test_db_recovery,
)

pytestmark = pytest.mark.unit


def _snapshot(candidate_sha: str = "candidate") -> CandidateSnapshot:
    """Создаёт минимальный declared snapshot для characterization tests."""
    return CandidateSnapshot(
        base_ref="stage",
        base_sha="base",
        candidate_sha=candidate_sha,
        in_scope_paths=("alembic_/versions/d1.py",),
        excluded_dirty_paths=("unrelated.txt",),
    )


def test_unrelated_dirty_state_is_excluded_from_verdict() -> None:
    """Spec stage-landing-readiness: unrelated dirty state не меняет verdict."""
    result = compare_snapshots(_snapshot(), _snapshot())

    assert result.status is ReadinessStatus.GO
    assert result.excluded_dirty_paths == ("unrelated.txt",)


def test_candidate_change_invalidates_previous_evidence() -> None:
    """Spec stage-landing-readiness: смена candidate требует повторной проверки."""
    result = compare_snapshots(_snapshot(), _snapshot(candidate_sha="new"))

    assert result.status is ReadinessStatus.NO_GO
    assert "repeat verification" in result.reason


@pytest.mark.parametrize(
    ("provenance", "route", "status"),
    [
        (
            ProvenanceMatrix(True, False, False, False),
            MigrationRoute.REWRITE_BEFORE_LANDING,
            ReadinessStatus.GO,
        ),
        (
            ProvenanceMatrix(True, True, True, True),
            MigrationRoute.FORWARD_REPAIR,
            ReadinessStatus.GO,
        ),
        (
            ProvenanceMatrix(True, False, None, False),
            MigrationRoute.NO_GO,
            ReadinessStatus.NO_GO,
        ),
        (
            ProvenanceMatrix(True, False, False, False, conflicting_evidence=True),
            MigrationRoute.NO_GO,
            ReadinessStatus.NO_GO,
        ),
    ],
)
def test_provenance_matrix_selects_one_route_or_evidence_gap(
    provenance: ProvenanceMatrix,
    route: MigrationRoute,
    status: ReadinessStatus,
) -> None:
    """Spec stage-landing-readiness: unknown/conflicting provenance даёт NO_GO."""
    decision = choose_migration_route(provenance)

    assert decision.route is route
    assert decision.status is status
    if status is ReadinessStatus.NO_GO:
        assert "EVIDENCE_GAP" in decision.reason


def test_failed_gate_is_actionable_and_fail_closed() -> None:
    """Spec stage-landing-readiness: missing quality gate блокирует readiness."""
    snapshot_result = compare_snapshots(_snapshot(), _snapshot())
    route = choose_migration_route(ProvenanceMatrix(True, False, False, False))

    result = evaluate_required_gates(
        snapshot_result,
        route,
        {"migration_safety": True, "compatibility": False},
    )

    assert result.status is ReadinessStatus.NO_GO
    assert result.failed_gates == ("compatibility",)


def test_paid_and_free_compatibility_baselines_are_compared_separately() -> None:
    """Spec stage-landing-readiness: paid/free drift блокирует release."""
    paid = CohortBaseline("paid", (True,), ("active",), 3, ("started",))
    free = CohortBaseline("free", (False,), ("trial",), 0, ("stopped",))

    result = compare_compatibility_baselines(
        (paid, free),
        (CohortBaseline("paid", (False,), ("active",), 3, ("started",)), free),
    )

    assert result.status is ReadinessStatus.NO_GO
    assert result.changed_cohorts == ("paid",)


def test_compatibility_drift_requires_explicit_product_approval() -> None:
    """Spec stage-landing-readiness: intentional drift требует accepted decision."""
    before = (CohortBaseline("paid", (False,), ("active",), 0, ("started",)),)
    after = (CohortBaseline("paid", (True,), ("active",), 1, ("started",)),)

    result = compare_compatibility_baselines(
        before,
        after,
        intentional_change_approved=True,
    )

    assert result.status is ReadinessStatus.GO
    assert result.changed_cohorts == ("paid",)


def _receipt(phase: EvidencePhase, candidate_sha: str = "candidate") -> EvidenceReceipt:
    """Создаёт receipt одной фазы для release-evidence tests."""
    return EvidenceReceipt(
        release_id="release-1",
        candidate_sha=candidate_sha,
        phase=phase,
        started_at="2026-08-17T10:00:00Z",
        completed_at="2026-08-17T10:01:00Z",
        outcome="PASS",
        migration_target="8c541a39b7e2",
        backfill_kind="auto_update_minus_phrases_v1",
        affected_record_preview="preview-1",
        compatibility_baseline_ref="baseline-1",
        recovery_action_ref="recovery-1",
    )


def test_release_receipts_keep_readiness_and_rollout_states_separate() -> None:
    """Spec stage-landing-readiness: каждая release-фаза имеет свой receipt."""
    receipts = tuple(_receipt(phase) for phase in EvidencePhase)

    result = validate_release_receipts(receipts, candidate_sha="candidate")

    assert result.status is ReadinessStatus.GO
    assert result.missing_phases == ()


def test_missing_database_receipt_blocks_release() -> None:
    """Spec stage-landing-readiness: database application без receipt даёт NO_GO."""
    receipts = tuple(
        _receipt(phase)
        for phase in EvidencePhase
        if phase is not EvidencePhase.DATABASE_APPLICATION
    )

    result = validate_release_receipts(receipts, candidate_sha="candidate")

    assert result.status is ReadinessStatus.NO_GO
    assert EvidencePhase.DATABASE_APPLICATION in result.missing_phases


def test_test_db_forward_recovery_evidence_is_fail_closed() -> None:
    """Spec stage-landing-readiness: recovery только через forward action."""
    evidence = DbRecoveryEvidence(
        candidate_sha="candidate",
        action=RecoveryAction.FORWARD_COMPENSATING_ACTION,
        outcome="PASS",
        proof_ref="tests/migrations/test_auto_update_minus_phrases_backfill.py::"
        "test_retry_after_interrupted_constraint_transition_is_idempotent",
    )

    result = validate_test_db_recovery(evidence, candidate_sha="candidate")

    assert result.status is ReadinessStatus.GO


def test_destructive_downgrade_cannot_be_recovery_evidence() -> None:
    """Spec stage-landing-readiness: destructive downgrade не закрывает recovery gap."""
    evidence = DbRecoveryEvidence(
        candidate_sha="candidate",
        action=RecoveryAction.BACKUP_RESTORE,
        outcome="PASS",
        proof_ref="operator-note",
        destructive_downgrade_used=True,
    )

    result = validate_test_db_recovery(evidence, candidate_sha="candidate")

    assert result.status is ReadinessStatus.NO_GO
    assert "destructive" in result.invalid_receipts[0]


def test_final_compatibility_requires_same_candidate_snapshot() -> None:
    """Spec stage-landing-readiness: baseline другого SHA даёт NO_GO."""
    baseline = (CohortBaseline("paid", (True,), ("active",), 1, ("started",)),)

    result = evaluate_final_compatibility(
        baseline,
        baseline,
        candidate_sha="candidate",
        evidence_candidate_sha="other",
    )

    assert result.status is ReadinessStatus.NO_GO
    assert "different candidate SHA" in result.reason
