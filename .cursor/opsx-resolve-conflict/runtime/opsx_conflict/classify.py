"""Classification: AUTO_SAFE | AI_SEMANTIC | OWNER_REQUIRED."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from opsx_conflict.models import (
    AuthorityLane,
    ClassifiedConflict,
    ConflictKind,
    PartitionedPath,
    ResolutionClass,
    ResolutionKind,
    SemanticCluster,
    OwnerDecisionPacket,
)
from opsx_conflict.semantic_authority import evaluate_ai_semantic_authority

_AUTHORITY_TOKENS = re.compile(
    r"(OWNER|STATUS|GATE|disposition|forbid-list|denylist|exclusive-owner|"
    r"runtime_class|ownership|NEXT_ACTION|STOP_REASON)",
    re.IGNORECASE,
)
_MARKER_BLOCK = re.compile(
    r"^<<<<<<<.*?^=======.*?^>>>>>>>.*?$",
    re.MULTILINE | re.DOTALL,
)


def _conflict_id(path: str, cluster_id: str | None) -> str:
    raw = f"{path}:{cluster_id or 'none'}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _is_trivial_textual(side_a: str, side_b: str) -> bool:
    """Non-overlapping или whitespace-only / single-hunk delta."""

    if side_a == side_b:
        return True
    a_lines = side_a.splitlines()
    b_lines = side_b.splitlines()
    if a_lines == b_lines:
        return True
    # common prefix + one differing tail line each side
    common = 0
    for la, lb in zip(a_lines, b_lines, strict=False):
        if la != lb:
            break
        common += 1
    if common > 0 and len(a_lines) - common <= 1 and len(b_lines) - common <= 1:
        return True
    if len(a_lines) == len(b_lines):
        diffs = sum(1 for i, line in enumerate(a_lines) if line != b_lines[i])
        if diffs <= 2:
            return True
    return False


def classify_path(
    part: PartitionedPath,
    cluster_id: str | None,
    side_a_text: str | None,
    side_b_text: str | None,
    worktree_text: str | None,
    base_text: str | None = None,
    repo_root: Path | None = None,
) -> ClassifiedConflict:
    """CLASSIFY один path."""

    path = part.path
    cid = _conflict_id(path, cluster_id)
    kind = part.unmerged.kind

    # Delete/modify — never AUTO from Git side naming
    if kind in (
        ConflictKind.DELETED_BY_US,
        ConflictKind.DELETED_BY_THEM,
        ConflictKind.BOTH_DELETED,
    ):
        return ClassifiedConflict(
            conflict_id=cid,
            cluster_id=cluster_id,
            path=path,
            lane=part.lane,
            resolution_class=ResolutionClass.OWNER_REQUIRED,
            resolution_kind=ResolutionKind.UNRESOLVED,
            reason="delete_modify_requires_owner",
            owner_options=[
                {"id": "keep", "label": "Retain file"},
                {"id": "delete", "label": "Delete file"},
            ],
        )

    if part.inventory_class == "B_ALLOWLIST_GAP":
        return ClassifiedConflict(
            conflict_id=cid,
            cluster_id=cluster_id,
            path=path,
            lane=part.lane,
            resolution_class=ResolutionClass.OWNER_REQUIRED,
            resolution_kind=ResolutionKind.UNRESOLVED,
            reason="allowlist_gap",
            owner_options=[{"id": "allowlist_fix", "label": "Fix allowlist first"}],
        )

    combined = (side_a_text or "") + (side_b_text or "") + (worktree_text or "")
    if _AUTHORITY_TOKENS.search(combined):
        return ClassifiedConflict(
            conflict_id=cid,
            cluster_id=cluster_id,
            path=path,
            lane=part.lane,
            resolution_class=ResolutionClass.OWNER_REQUIRED,
            resolution_kind=ResolutionKind.UNRESOLVED,
            reason="authority_token_divergence",
            owner_options=[
                {"id": "side_a", "label": f"Keep {part.unmerged.stages[1].role if part.unmerged.stages else 'side_a'}"},
                {"id": "side_b", "label": f"Keep {part.unmerged.stages[2].role if len(part.unmerged.stages) > 2 else 'side_b'}"},
                {"id": "synthesis", "label": "Manual synthesis"},
            ],
        )

    if side_a_text and side_b_text and _is_trivial_textual(side_a_text, side_b_text):
        return ClassifiedConflict(
            conflict_id=cid,
            cluster_id=cluster_id,
            path=path,
            lane=part.lane,
            resolution_class=ResolutionClass.AUTO_SAFE,
            resolution_kind=ResolutionKind.UNION,
            reason="trivial_textual_union",
        )

    if side_a_text and side_b_text and not _is_trivial_textual(side_a_text, side_b_text):
        auth_result = evaluate_ai_semantic_authority(
            part, side_a_text, side_b_text, base_text, repo_root or Path(".")
        )
        if auth_result.allowed:
            return ClassifiedConflict(
                conflict_id=cid,
                cluster_id=cluster_id,
                path=path,
                lane=part.lane,
                resolution_class=ResolutionClass.AI_SEMANTIC,
                resolution_kind=ResolutionKind.SYNTHESIS,
                reason="semantic_synthesis_authority_proven",
                semantic_authority_refs=auth_result.authority_refs,
                side_a_intent_refs=auth_result.side_a_intent_refs,
                side_b_intent_refs=auth_result.side_b_intent_refs,
                preserved_invariants=auth_result.preserved_invariants,
            )
        return ClassifiedConflict(
            conflict_id=cid,
            cluster_id=cluster_id,
            path=path,
            lane=part.lane,
            resolution_class=ResolutionClass.OWNER_REQUIRED,
            resolution_kind=ResolutionKind.UNRESOLVED,
            reason=f"ai_semantic_downgrade:{auth_result.downgrade_reason}",
            semantic_authority_refs=auth_result.authority_refs,
            owner_options=[
                {"id": "side_a", "label": "Keep side A"},
                {"id": "side_b", "label": "Keep side B"},
                {"id": "synthesis", "label": "Manual synthesis"},
            ],
        )

    return ClassifiedConflict(
        conflict_id=cid,
        cluster_id=cluster_id,
        path=path,
        lane=part.lane,
        resolution_class=ResolutionClass.OWNER_REQUIRED,
        resolution_kind=ResolutionKind.UNRESOLVED,
        reason="insufficient_evidence",
    )


def classify_all(
    partitions: list[PartitionedPath],
    clusters: list[SemanticCluster],
    stage_texts: dict[str, tuple[str | None, str | None, str | None]],
    repo_root: Path | None = None,
) -> list[ClassifiedConflict]:
    """CLASSIFY all partitioned paths."""

    cluster_by_path: dict[str, str] = {}
    for cl in clusters:
        for p in cl.paths:
            cluster_by_path[p] = cl.cluster_id

    classified: list[ClassifiedConflict] = []
    for part in partitions:
        texts = stage_texts.get(part.path, (None, None, None))
        base, side_a, side_b = texts
        worktree = texts[2]  # placeholder; worktree passed separately in pipeline
        classified.append(
            classify_path(
                part,
                cluster_by_path.get(part.path),
                side_a,
                side_b,
                worktree,
                base_text=base,
                repo_root=repo_root,
            )
        )
    return classified


def aggregate_owner_packets(
    classified: list[ClassifiedConflict],
    clusters: list[SemanticCluster],
) -> list[OwnerDecisionPacket]:
    """OWNER aggregation — один packet на cluster/decision type."""

    owner_items = [c for c in classified if c.resolution_class == ResolutionClass.OWNER_REQUIRED]
    if not owner_items:
        return []

    by_cluster: dict[str | None, list[ClassifiedConflict]] = {}
    for item in owner_items:
        by_cluster.setdefault(item.cluster_id, []).append(item)

    packets: list[OwnerDecisionPacket] = []
    for cluster_id, items in by_cluster.items():
        paths = [i.path for i in items]
        intents = [i.reason for i in items]
        options: list[dict[str, str]] = []
        for item in items:
            for opt in item.owner_options:
                options.append({"path": item.path, **opt})
        packets.append(
            OwnerDecisionPacket(
                decision_id=hashlib.sha256(
                    f"{cluster_id}:{','.join(paths)}".encode()
                ).hexdigest()[:12],
                cluster_id=cluster_id,
                paths=paths,
                conflicting_intents=intents,
                authority_evidence=[f"class:{i.resolution_class.value}" for i in items],
                options=options,
                recommended_option=None,
            )
        )
    return packets
