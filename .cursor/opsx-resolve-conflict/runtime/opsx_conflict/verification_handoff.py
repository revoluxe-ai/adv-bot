"""Candidate identity и verification handoff — не дублирует /opsx-test."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from opsx_conflict.git_capture import (
    compute_candidate_tree_oid,
    GitCaptureError,
    has_unmerged_entries,
    list_staged_paths,
)
from opsx_conflict.models import ConflictManifest, ResolutionLedgerEntry


@dataclass
class VerificationHandoff:
    """Machine-readable handoff после RESOLVED_PENDING_VERIFICATION."""

    candidate_identity: str
    candidate_tree_oid: str
    operation_fingerprint: str
    operation_identity: str
    resolved_paths: list[str]
    staged_paths: list[str]
    affected_clusters: list[str]
    invalidated_evidence: list[str]
    required_verification_classes: list[str]
    verification_entrypoints: list[str]
    ledger_role: str = "RECOVERY_CACHE"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "opsx-resolve-conflict/verification-handoff/v2",
            "candidate_identity": self.candidate_identity,
            "candidate_tree_oid": self.candidate_tree_oid,
            "operation_fingerprint": self.operation_fingerprint,
            "operation_identity": self.operation_identity,
            "resolved_paths": self.resolved_paths,
            "staged_paths": self.staged_paths,
            "affected_clusters": self.affected_clusters,
            "invalidated_evidence": self.invalidated_evidence,
            "required_verification_classes": self.required_verification_classes,
            "verification_entrypoints": self.verification_entrypoints,
            "ledger_role": self.ledger_role,
        }


def compute_full_candidate_identity(repo_root: Path) -> tuple[str, str, list[str]]:
    """
    Canonical identity = git write-tree over full staged index.

    Returns (candidate_identity, candidate_tree_oid, staged_paths).

    Raises GitCaptureError if unmerged entries remain.
    """

    if has_unmerged_entries(repo_root):
        raise GitCaptureError("unmerged_entries_present")
    tree_oid = compute_candidate_tree_oid(repo_root)
    staged = list_staged_paths(repo_root)
    return tree_oid, tree_oid, staged


def compute_resolved_paths_digest(
    repo_root: Path,
    resolved_paths: list[str],
) -> str:
    """Supplementary digest — not used for terminal gate."""

    parts: list[str] = []
    for path in sorted(resolved_paths):
        p = repo_root / path
        if p.is_file():
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            parts.append(f"path:{path}:{h}")
        else:
            parts.append(f"path:{path}:MISSING")
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


def build_verification_handoff(
    repo_root: Path,
    manifest: ConflictManifest,
    ledger: list[ResolutionLedgerEntry],
    resolved_paths: list[str],
    operation_identity: str,
) -> VerificationHandoff:
    """Handoff contract для external verification."""

    candidate_id, tree_oid, staged = compute_full_candidate_identity(repo_root)
    clusters = sorted({e.cluster_id for e in ledger if e.cluster_id})
    invalidated = [f"pre_resolution:{p}" for p in resolved_paths]

    required_classes = ["RESOLUTION_VERIFICATION", "CANDIDATE_BINDING"]
    if any(p.endswith(".py") for p in resolved_paths):
        required_classes.append("PYTHON_SYNTAX")
    required_classes.append("PROJECT_VERIFICATION_EXTERNAL")

    entrypoints = [
        "/opsx-test",
        "poetry run pytest <affected-tests>",
    ]

    return VerificationHandoff(
        candidate_identity=candidate_id,
        candidate_tree_oid=tree_oid,
        operation_fingerprint=manifest.fingerprint,
        operation_identity=operation_identity,
        resolved_paths=resolved_paths,
        staged_paths=staged,
        affected_clusters=clusters,
        invalidated_evidence=invalidated,
        required_verification_classes=required_classes,
        verification_entrypoints=entrypoints,
    )


def validate_external_verification_packet(
    handoff: VerificationHandoff,
    evidence_packet: dict[str, Any],
    repo_root: Path | None = None,
) -> tuple[bool, list[str]]:
    """Проверка evidence; recompute full tree OID when repo_root supplied."""

    refs: list[str] = []
    packet_id = evidence_packet.get("candidate_identity")

    if repo_root is not None:
        try:
            current_id, current_tree, _ = compute_full_candidate_identity(repo_root)
        except GitCaptureError as exc:
            return False, [f"verification_candidate_recompute_failed:{exc.reason}"]

        if packet_id != current_id:
            return False, [
                f"verification_candidate_tree_mismatch:"
                f"expected:{packet_id}:actual:{current_id}"
            ]
        if current_tree != handoff.candidate_tree_oid:
            return False, [
                f"verification_candidate_tree_oid_mismatch:"
                f"expected:{handoff.candidate_tree_oid}:actual:{current_tree}"
            ]
        refs.append("verification:current_tree_match")
    elif packet_id != handoff.candidate_identity:
        return False, ["verification_candidate_identity_mismatch"]

    if packet_id != handoff.candidate_identity:
        return False, ["verification_candidate_identity_mismatch"]

    refs.append("verification:packet_identity_match")

    completed = set(evidence_packet.get("completed_classes") or [])
    required = set(handoff.required_verification_classes)
    mandatory = required - {"PROJECT_VERIFICATION_EXTERNAL"}
    if not mandatory.issubset(completed):
        missing = mandatory - completed
        return False, [f"verification_missing_classes:{','.join(sorted(missing))}"]

    refs.append("verification:mandatory_classes_complete")
    if "PROJECT_VERIFICATION_EXTERNAL" in completed:
        refs.append("verification:project_external_complete")

    return True, refs
