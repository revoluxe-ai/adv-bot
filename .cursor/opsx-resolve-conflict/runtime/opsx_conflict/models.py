"""Datamodels для conflict manifest, partition lanes и resolution ledger."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class OperationType(str, Enum):
    """Активная Git sequencer operation."""

    MERGE = "merge"
    REBASE = "rebase"
    CHERRY_PICK = "cherry_pick"
    NONE = "none"


class AuthorityLane(str, Enum):
    """Authority partition lane — не глобальный OPSX State."""

    PROCESS = "process"
    PRODUCT = "product"
    SPEC_GOVERNANCE = "spec_governance"
    PROJECT_CONFIG = "project_config"
    UNKNOWN = "unknown"


class ConflictKind(str, Enum):
    """Git unmerged status / topology."""

    BOTH_MODIFIED = "both_modified"
    BOTH_ADDED = "both_added"
    DELETED_BY_US = "deleted_by_us"
    DELETED_BY_THEM = "deleted_by_them"
    BOTH_DELETED = "both_deleted"
    ADDED_BY_US = "added_by_us"
    ADDED_BY_THEM = "added_by_them"
    OTHER = "other"


class ResolutionClass(str, Enum):
    """Operational resolution class."""

    AUTO_SAFE = "AUTO_SAFE"
    AI_SEMANTIC = "AI_SEMANTIC"
    OWNER_REQUIRED = "OWNER_REQUIRED"


class ResolutionKind(str, Enum):
    """Как был получен итог."""

    KEEP_SIDE_A = "KEEP_SIDE_A"
    KEEP_SIDE_B = "KEEP_SIDE_B"
    UNION = "UNION"
    SYNTHESIS = "SYNTHESIS"
    DELETE = "DELETE"
    REGENERATE = "REGENERATE"
    UNRESOLVED = "UNRESOLVED"


class PipelineStage(str, Enum):
    """Локальные execution stages conflict pipeline."""

    CAPTURE = "CAPTURE"
    PARTITION = "PARTITION"
    CLASSIFY = "CLASSIFY"
    RESOLVE = "RESOLVE"
    VERIFY_RESOLUTION = "VERIFY_RESOLUTION"
    VERIFY_CANDIDATE = "VERIFY_CANDIDATE"
    RESOLVED_PENDING_VERIFICATION = "RESOLVED_PENDING_VERIFICATION"
    VERIFIED_READY_FOR_CONTINUE = "VERIFIED_READY_FOR_CONTINUE"
    PAUSED = "PAUSED"
    FAILED = "FAILED"


@dataclass
class StageBlob:
    """Blob одной Git stage с normative role."""

    stage: int
    role: str
    oid: str | None
    mode: str | None


@dataclass
class UnmergedPath:
    """Один unmerged path в active operation."""

    path: str
    kind: ConflictKind
    stages: list[StageBlob] = field(default_factory=list)
    worktree_has_markers: bool = False


@dataclass
class OperationIdentity:
    """Immutable identity активной Git operation."""

    operation_type: OperationType
    head_oid: str
    orig_head_oid: str | None
    operation_head_oid: str | None
    base_oid: str | None
    side_a_label: str
    side_b_label: str
    side_a_oid: str | None
    side_b_oid: str | None


@dataclass
class ConflictManifest:
    """Whole-operation capture — полный inventory conflict set."""

    operation: OperationIdentity
    unmerged_paths: list[UnmergedPath]
    auto_merged_paths: list[str] = field(default_factory=list)
    fingerprint: str = ""
    repo_root: str = ""

    def path_inventory(self) -> list[str]:
        return [p.path for p in self.unmerged_paths]


@dataclass
class PartitionedPath:
    """Path после authority partition."""

    path: str
    lane: AuthorityLane
    inventory_class: str
    unmerged: UnmergedPath


@dataclass
class SemanticCluster:
    """Cluster связанных изменений с evidence.

    ``lane`` задан только при ``authority_homogeneous``; для mixed cluster
    authority берётся из ``member_lanes`` per path, не из cluster lane.
    """

    cluster_id: str
    paths: list[str]
    member_lanes: dict[str, str] = field(default_factory=dict)
    authority_homogeneous: bool = True
    lane: AuthorityLane | None = None
    evidence: list[str] = field(default_factory=list)


@dataclass
class ClassifiedConflict:
    """Conflict/cluster после classify."""

    conflict_id: str
    cluster_id: str | None
    path: str
    lane: AuthorityLane
    resolution_class: ResolutionClass
    resolution_kind: ResolutionKind
    reason: str
    owner_options: list[dict[str, Any]] = field(default_factory=list)
    semantic_authority_refs: list[str] = field(default_factory=list)
    side_a_intent_refs: list[str] = field(default_factory=list)
    side_b_intent_refs: list[str] = field(default_factory=list)
    preserved_invariants: list[str] = field(default_factory=list)
    applied_policy_id: str | None = None
    policy_compatibility_reason: str = ""


@dataclass
class ResolutionLedgerEntry:
    """Machine-readable receipt одного resolution unit."""

    conflict_id: str
    cluster_id: str | None
    path: str
    operation_identity: str
    base_oid: str | None
    side_a_oid: str | None
    side_b_oid: str | None
    authority_refs: list[str]
    lane: str
    resolution_class: str
    resolution_kind: str
    reason: str
    result_blob_oid: str | None
    result_worktree_sha256: str | None
    verification_refs: list[str] = field(default_factory=list)
    side_a_intent_refs: list[str] = field(default_factory=list)
    side_b_intent_refs: list[str] = field(default_factory=list)
    preserved_invariants: list[str] = field(default_factory=list)
    reason_not_new_decision: str = ""
    verification_requirements: list[str] = field(default_factory=list)
    policy_id: str | None = None
    policy_compatibility_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "cluster_id": self.cluster_id,
            "path": self.path,
            "operation_identity": self.operation_identity,
            "base_oid": self.base_oid,
            "side_a_oid": self.side_a_oid,
            "side_b_oid": self.side_b_oid,
            "authority_refs": self.authority_refs,
            "lane": self.lane,
            "resolution_class": self.resolution_class,
            "resolution_kind": self.resolution_kind,
            "reason": self.reason,
            "result_blob_or_tree_identity": self.result_blob_oid,
            "result_worktree_sha256": self.result_worktree_sha256,
            "verification_refs": self.verification_refs,
            "side_a_intent_refs": self.side_a_intent_refs,
            "side_b_intent_refs": self.side_b_intent_refs,
            "preserved_invariants": self.preserved_invariants,
            "reason_not_new_decision": self.reason_not_new_decision,
            "verification_requirements": self.verification_requirements,
            "policy_id": self.policy_id,
            "policy_compatibility_reason": self.policy_compatibility_reason,
        }


@dataclass
class OwnerDecisionPacket:
    """Агрегированный Owner gate."""

    decision_id: str
    cluster_id: str | None
    paths: list[str]
    conflicting_intents: list[str]
    authority_evidence: list[str]
    options: list[dict[str, Any]]
    recommended_option: str | None
    affected_tests: list[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    """Terminal pipeline output."""

    status: str
    stage: PipelineStage
    manifest: ConflictManifest | None = None
    partitions: list[PartitionedPath] = field(default_factory=list)
    clusters: list[SemanticCluster] = field(default_factory=list)
    classified: list[ClassifiedConflict] = field(default_factory=list)
    ledger: list[ResolutionLedgerEntry] = field(default_factory=list)
    owner_packets: list[OwnerDecisionPacket] = field(default_factory=list)
    authority_policy_packets: list[Any] = field(default_factory=list)
    approved_policies: list[Any] = field(default_factory=list)
    stop_reason: str | None = None
    fingerprint: str = ""
    staged_paths: list[str] = field(default_factory=list)
    run_id: str = ""
    candidate_identity: str = ""
    verification_handoff: dict[str, Any] | None = None
    execution_state: dict[str, Any] | None = None
    drill_down_path: str | None = None
    path_detail: dict[str, Any] | None = None
    runtime_source_revision: str = ""
    bootstrap_source_revision: str = ""
