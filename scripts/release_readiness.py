"""Fail-closed evaluation of one branch-to-base release evidence snapshot.

Модуль принадлежит release-evidence layer, а не application runtime. Он
принимает уже собранные identity/provenance/gate facts, не вызывает git,
Alembic или production DB и возвращает детерминированный readiness verdict.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


class ReadinessStatus(StrEnum):
    """Допустимые статусы отдельного readiness evaluation."""

    GO = "GO"
    NO_GO = "NO_GO"


class MigrationRoute(StrEnum):
    """Маршруты исправления migration по provenance."""

    REWRITE_BEFORE_LANDING = "rewrite-before-landing"
    FORWARD_REPAIR = "forward-repair"
    NO_GO = "NO_GO"


@dataclass(frozen=True)
class CandidateSnapshot:
    """Идентичность candidate и ограничение набора файлов проверки."""

    base_ref: str
    base_sha: str
    candidate_sha: str
    in_scope_paths: tuple[str, ...]
    excluded_dirty_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProvenanceMatrix:
    """Независимые facts о публикации и применении migration."""

    remote_branch_reachable: bool
    base_reachable: bool
    database_applied: bool | None
    deployment_receipt: bool
    conflicting_evidence: bool = False


@dataclass(frozen=True)
class RouteDecision:
    """Выбор migration route или fail-closed gap."""

    route: MigrationRoute
    status: ReadinessStatus
    reason: str


@dataclass(frozen=True)
class CohortBaseline:
    """Observable baseline representative paid/free cohort."""

    cohort: str
    automation_flags: tuple[bool, ...]
    billing_states: tuple[str, ...]
    wb_write_count: int
    campaign_lifecycle: tuple[str, ...]


@dataclass(frozen=True)
class CompatibilityResult:
    """Сравнение before/after без смешения paid и free cohort."""

    status: ReadinessStatus
    changed_cohorts: tuple[str, ...]
    reason: str


class EvidencePhase(StrEnum):
    """Независимые состояния одного release evidence package."""

    READINESS = "readiness"
    STAGE_DEPLOYMENT = "stage_deployment"
    DATABASE_APPLICATION = "database_application"
    PRODUCTION_ROLLOUT = "production_rollout"
    PRODUCTION_VERIFICATION = "production_verification"


class RecoveryAction(StrEnum):
    """Допустимые безопасные действия восстановления test DB/rollout."""

    BACKUP_RESTORE = "backup_restore"
    FORWARD_COMPENSATING_ACTION = "forward_compensating_action"


@dataclass(frozen=True)
class EvidenceReceipt:
    """Receipt одной фазы, не заменяющий receipts остальных фаз."""

    release_id: str
    candidate_sha: str
    phase: EvidencePhase
    started_at: str
    completed_at: str
    outcome: str
    migration_target: str
    backfill_kind: str
    affected_record_preview: str
    compatibility_baseline_ref: str
    recovery_action_ref: str


@dataclass(frozen=True)
class DbRecoveryEvidence:
    """Доказательство безопасного восстановления тестового rollout."""

    candidate_sha: str
    action: RecoveryAction
    outcome: str
    proof_ref: str
    destructive_downgrade_used: bool = False


@dataclass(frozen=True)
class EvidenceValidationResult:
    """Результат проверки раздельных release receipts."""

    status: ReadinessStatus
    missing_phases: tuple[EvidencePhase, ...] = ()
    invalid_receipts: tuple[str, ...] = ()
    reason: str = ""


@dataclass(frozen=True)
class ReadinessResult:
    """Результат проверки candidate identity, provenance и quality gates."""

    status: ReadinessStatus
    reason: str
    excluded_dirty_paths: tuple[str, ...]
    failed_gates: tuple[str, ...] = ()


def compare_snapshots(
    declared: CandidateSnapshot,
    observed: CandidateSnapshot,
) -> ReadinessResult:
    """Инвалидирует evidence при изменении candidate или declared scope.

    Args:
        declared: Snapshot, на котором собирались прежние evidence.
        observed: Snapshot, обнаруженный перед следующим gate.

    Returns:
        ``NO_GO`` с требованием повторного прогона при любом identity/scope drift.
    """
    identity_changed = (
        declared.base_ref != observed.base_ref
        or declared.base_sha != observed.base_sha
        or declared.candidate_sha != observed.candidate_sha
        or declared.in_scope_paths != observed.in_scope_paths
    )
    if identity_changed:
        return ReadinessResult(
            status=ReadinessStatus.NO_GO,
            reason="candidate snapshot changed; repeat verification",
            excluded_dirty_paths=observed.excluded_dirty_paths,
        )
    return ReadinessResult(
        status=ReadinessStatus.GO,
        reason="candidate snapshot unchanged",
        excluded_dirty_paths=observed.excluded_dirty_paths,
    )


def choose_migration_route(provenance: ProvenanceMatrix) -> RouteDecision:
    """Выбирает ровно один migration route по provenance matrix.

    ``database_applied=None`` или конфликт источников считаются
    ``EVIDENCE_GAP`` и не превращаются в разрешение на rewrite.
    """
    if provenance.conflicting_evidence or provenance.database_applied is None:
        return RouteDecision(
            route=MigrationRoute.NO_GO,
            status=ReadinessStatus.NO_GO,
            reason="EVIDENCE_GAP: migration application provenance is unknown or conflicting",
        )
    if provenance.database_applied:
        if not provenance.deployment_receipt:
            return RouteDecision(
                route=MigrationRoute.NO_GO,
                status=ReadinessStatus.NO_GO,
                reason="EVIDENCE_GAP: applied migration has no deployment receipt",
            )
        return RouteDecision(
            route=MigrationRoute.FORWARD_REPAIR,
            status=ReadinessStatus.GO,
            reason="database application is proven; preserve immutable history",
        )
    if provenance.remote_branch_reachable and not provenance.base_reachable:
        return RouteDecision(
            route=MigrationRoute.REWRITE_BEFORE_LANDING,
            status=ReadinessStatus.GO,
            reason="revision is remote-only and database application is disproven",
        )
    return RouteDecision(
        route=MigrationRoute.NO_GO,
        status=ReadinessStatus.NO_GO,
        reason="EVIDENCE_GAP: route cannot be selected safely",
    )


def evaluate_required_gates(
    snapshot_result: ReadinessResult,
    route: RouteDecision,
    gates: dict[str, bool],
) -> ReadinessResult:
    """Собирает fail-closed verdict для одного candidate snapshot."""
    failed = tuple(sorted(name for name, passed in gates.items() if not passed))
    if snapshot_result.status is ReadinessStatus.NO_GO:
        return snapshot_result
    if route.status is ReadinessStatus.NO_GO:
        return ReadinessResult(
            status=ReadinessStatus.NO_GO,
            reason=route.reason,
            excluded_dirty_paths=snapshot_result.excluded_dirty_paths,
            failed_gates=failed,
        )
    if failed:
        return ReadinessResult(
            status=ReadinessStatus.NO_GO,
            reason="required gate failed",
            excluded_dirty_paths=snapshot_result.excluded_dirty_paths,
            failed_gates=failed,
        )
    return ReadinessResult(
        status=ReadinessStatus.GO,
        reason="all required gates passed for one candidate snapshot",
        excluded_dirty_paths=snapshot_result.excluded_dirty_paths,
    )


def compare_compatibility_baselines(
    before: tuple[CohortBaseline, ...],
    after: tuple[CohortBaseline, ...],
    *,
    intentional_change_approved: bool = False,
) -> CompatibilityResult:
    """Проверяет paid/free automation, billing, WB writes и lifecycle.

    Любой drift считается ``NO_GO`` без отдельного accepted product decision.
    """
    before_by_cohort = {item.cohort: item for item in before}
    after_by_cohort = {item.cohort: item for item in after}
    changed: list[str] = []
    for cohort, expected in before_by_cohort.items():
        actual = after_by_cohort.get(cohort)
        if actual != expected:
            changed.append(cohort)
    changed.extend(sorted(set(after_by_cohort) - set(before_by_cohort)))
    if changed and not intentional_change_approved:
        return CompatibilityResult(
            status=ReadinessStatus.NO_GO,
            changed_cohorts=tuple(sorted(set(changed))),
            reason="compatibility baseline drift requires accepted product decision",
        )
    return CompatibilityResult(
        status=ReadinessStatus.GO,
        changed_cohorts=tuple(sorted(set(changed))),
        reason="paid/free compatibility baseline preserved",
    )


def validate_release_receipts(
    receipts: tuple[EvidenceReceipt, ...],
    *,
    candidate_sha: str,
) -> EvidenceValidationResult:
    """Проверяет, что readiness и rollout states имеют отдельные receipts.

    Args:
        receipts: Собранные receipts release-фаз.
        candidate_sha: Единственный SHA, к которому должны относиться receipts.

    Returns:
        ``GO`` только при наличии ровно одного receipt каждой required-фазы и
        совпадении candidate SHA; иначе fail-closed ``NO_GO``.
    """
    required = tuple(EvidencePhase)
    by_phase: dict[EvidencePhase, list[EvidenceReceipt]] = {
        phase: [] for phase in required
    }
    invalid: list[str] = []
    for receipt in receipts:
        by_phase[receipt.phase].append(receipt)
        if receipt.candidate_sha != candidate_sha:
            invalid.append(f"{receipt.phase}: candidate SHA mismatch")
        if receipt.started_at > receipt.completed_at:
            invalid.append(f"{receipt.phase}: invalid receipt interval")
    missing = tuple(phase for phase in required if not by_phase[phase])
    invalid.extend(
        f"{phase}: duplicate receipt"
        for phase in required
        if len(by_phase[phase]) > 1
    )
    if missing or invalid:
        return EvidenceValidationResult(
            status=ReadinessStatus.NO_GO,
            missing_phases=missing,
            invalid_receipts=tuple(invalid),
            reason="separate phase evidence is incomplete or inconsistent",
        )
    return EvidenceValidationResult(
        status=ReadinessStatus.GO,
        reason="readiness, deployment and database evidence are separate",
    )


def validate_test_db_recovery(
    evidence: TestDbRecoveryEvidence,
    *,
    candidate_sha: str,
) -> EvidenceValidationResult:
    """Проверяет recovery evidence без destructive production downgrade.

    Args:
        evidence: Backup/restore или forward compensating action proof.
        candidate_sha: SHA test-DB evidence package.

    Returns:
        ``GO`` при валидном test-DB recovery proof, иначе ``NO_GO``.
    """
    invalid: list[str] = []
    if evidence.candidate_sha != candidate_sha:
        invalid.append("recovery evidence candidate SHA mismatch")
    if evidence.destructive_downgrade_used:
        invalid.append("destructive production downgrade is forbidden")
    if not evidence.proof_ref:
        invalid.append("recovery proof reference is missing")
    if evidence.outcome != "PASS":
        invalid.append("recovery outcome is not PASS")
    if invalid:
        return EvidenceValidationResult(
            status=ReadinessStatus.NO_GO,
            invalid_receipts=tuple(invalid),
            reason="test-DB recovery evidence is invalid",
        )
    return EvidenceValidationResult(
        status=ReadinessStatus.GO,
        reason=f"test-DB recovery proven by {evidence.action.value}",
    )


def evaluate_final_compatibility(
    before: tuple[CohortBaseline, ...],
    after: tuple[CohortBaseline, ...],
    *,
    candidate_sha: str,
    evidence_candidate_sha: str,
    intentional_change_approved: bool = False,
) -> CompatibilityResult:
    """Выполняет финальный compatibility gate для того же snapshot.

    Несовпадение snapshot превращается в ``NO_GO`` даже при совпадающих
    отдельных cohort values: baseline другого candidate не является evidence.
    """
    if candidate_sha != evidence_candidate_sha:
        return CompatibilityResult(
            status=ReadinessStatus.NO_GO,
            changed_cohorts=(),
            reason="compatibility evidence belongs to a different candidate SHA",
        )
    return compare_compatibility_baselines(
        before,
        after,
        intentional_change_approved=intentional_change_approved,
    )


def _load_json(path: Path) -> dict[str, Any]:
    """Читает JSON object для CLI без выполнения внешних действий."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def main() -> int:
    """CLI: печатает JSON route/readiness decision из evidence files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--gates", type=Path, required=True)
    args = parser.parse_args()

    snapshot_data = _load_json(args.snapshot)
    provenance_data = _load_json(args.provenance)
    gates_data = _load_json(args.gates)
    snapshot = CandidateSnapshot(
        base_ref=str(snapshot_data["base_ref"]),
        base_sha=str(snapshot_data["base_sha"]),
        candidate_sha=str(snapshot_data["candidate_sha"]),
        in_scope_paths=tuple(snapshot_data["in_scope_paths"]),
        excluded_dirty_paths=tuple(snapshot_data.get("excluded_dirty_paths", ())),
    )
    provenance = ProvenanceMatrix(
        remote_branch_reachable=bool(provenance_data["remote_branch_reachable"]),
        base_reachable=bool(provenance_data["base_reachable"]),
        database_applied=provenance_data["database_applied"],
        deployment_receipt=bool(provenance_data["deployment_receipt"]),
        conflicting_evidence=bool(provenance_data.get("conflicting_evidence", False)),
    )
    unchanged = compare_snapshots(snapshot, snapshot)
    route = choose_migration_route(provenance)
    result = evaluate_required_gates(unchanged, route, gates_data)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0 if result.status is ReadinessStatus.GO else 1


if __name__ == "__main__":
    raise SystemExit(main())
