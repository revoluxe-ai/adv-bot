"""Authority resolution policy — bounded synthesis under Owner-approved contract."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opsx_conflict.classify import _is_trivial_textual
from opsx_conflict.models import (
    AuthorityLane,
    ClassifiedConflict,
    PartitionedPath,
    ResolutionClass,
    ResolutionKind,
    SemanticCluster,
)
from opsx_conflict.semantic_authority import (
    _arch_choices,
    _business_choices,
    _authority_from_markers,
    path_verification_available,
)

_POLICY_ELIGIBLE_REASONS = frozenset(
    {
        "authority_token_divergence",
    }
)

_OBSOLETE_LINE = re.compile(r"^#\s*OBSOLETE(?:_CONTRACT)?:", re.IGNORECASE)


@dataclass
class AuthorityResolutionPolicy:
    """Owner-approved bounded resolution policy over compatible path set."""

    policy_id: str
    lane: AuthorityLane
    covered_paths: list[str]
    covered_cluster_ids: list[str]
    authority_refs: list[str]
    authoritative_contract: str
    preserved_invariants: list[str]
    incoming_delta_policy: str
    forbidden_changes: list[str]
    verification_requirements: list[str]
    owner_decision_ref: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "lane": self.lane.value,
            "covered_paths": self.covered_paths,
            "covered_cluster_ids": self.covered_cluster_ids,
            "authority_refs": self.authority_refs,
            "authoritative_contract": self.authoritative_contract,
            "preserved_invariants": self.preserved_invariants,
            "incoming_delta_policy": self.incoming_delta_policy,
            "forbidden_changes": self.forbidden_changes,
            "verification_requirements": self.verification_requirements,
            "owner_decision_ref": self.owner_decision_ref,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuthorityResolutionPolicy:
        return cls(
            policy_id=data["policy_id"],
            lane=AuthorityLane(data["lane"]),
            covered_paths=list(data.get("covered_paths") or []),
            covered_cluster_ids=list(data.get("covered_cluster_ids") or []),
            authority_refs=list(data.get("authority_refs") or []),
            authoritative_contract=data.get("authoritative_contract", "target"),
            preserved_invariants=list(data.get("preserved_invariants") or []),
            incoming_delta_policy=data.get(
                "incoming_delta_policy", "incorporate_compatible_reject_obsolete"
            ),
            forbidden_changes=list(data.get("forbidden_changes") or []),
            verification_requirements=list(
                data.get("verification_requirements") or []
            ),
            owner_decision_ref=data.get("owner_decision_ref", ""),
        )


@dataclass
class AuthorityPolicyPacket:
    """Policy-level Owner question — не per-file gate."""

    policy_id: str
    cluster_id: str | None
    lane: str
    covered_paths: list[str]
    question_type: str
    options: list[dict[str, Any]]
    authority_evidence: list[str]
    conflicting_reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "cluster_id": self.cluster_id,
            "lane": self.lane,
            "covered_paths": self.covered_paths,
            "question_type": self.question_type,
            "options": self.options,
            "authority_evidence": self.authority_evidence,
            "conflicting_reasons": self.conflicting_reasons,
        }


@dataclass
class PolicyEvalResult:
    """Per-path reclassification under approved policy."""

    resolution_class: ResolutionClass
    resolution_kind: ResolutionKind
    reason: str
    allowed: bool
    authority_refs: list[str] = field(default_factory=list)
    preserved_invariants: list[str] = field(default_factory=list)
    side_a_intent_refs: list[str] = field(default_factory=list)
    side_b_intent_refs: list[str] = field(default_factory=list)
    reason_not_new_decision: str = ""
    verification_requirements: list[str] = field(default_factory=list)
    compatibility_reason: str = ""


def is_policy_eligible(item: ClassifiedConflict, part: PartitionedPath) -> bool:
    """Path может войти в authority policy packet."""

    if part.lane != AuthorityLane.PROCESS or part.inventory_class != "A_IN_SCOPE":
        return False
    if item.resolution_class != ResolutionClass.OWNER_REQUIRED:
        return False
    if item.reason in _POLICY_ELIGIBLE_REASONS:
        return True
    if item.reason.startswith("ai_semantic_downgrade:"):
        return True
    return False


def synthesize_under_target_authority(side_a: str, side_b: str) -> str:
    """
    TARGET (side_a) authoritative — incorporate compatible incoming deltas.

    Rejects obsolete incoming semantics; does not blind keep_ours.
    """

    if side_a == side_b:
        return side_a
    if _is_trivial_textual(side_a, side_b):
        return _synthesis_union_target(side_a, side_b)

    a_lines = side_a.splitlines(keepends=True)
    b_lines = side_b.splitlines(keepends=True)
    common = 0
    for la, lb in zip(a_lines, b_lines, strict=False):
        if la != lb:
            break
        common += 1

    result = "".join(a_lines[:common])
    tail_a = a_lines[common:]
    tail_b = b_lines[common:]
    result += "".join(tail_a)

    a_stripped = {ln.strip() for ln in tail_a if ln.strip()}
    for line in tail_b:
        stripped = line.strip()
        if not stripped:
            continue
        if _OBSOLETE_LINE.match(stripped):
            continue
        if stripped.startswith("# ARCHITECTURE_CHOICE:"):
            continue
        if stripped.startswith("# BUSINESS_CHOICE:"):
            if any(
                stripped == ba.strip()
                for ba in tail_a
                if ba.strip().startswith("# BUSINESS_CHOICE:")
            ):
                continue
        if line not in tail_a and stripped not in a_stripped:
            result += line
    return result


def _synthesis_union_target(side_a: str, side_b: str) -> str:
    """Union biased to target with compatible incoming tail."""

    a_lines = side_a.splitlines(keepends=True)
    b_lines = side_b.splitlines(keepends=True)
    common = 0
    for la, lb in zip(a_lines, b_lines, strict=False):
        if la != lb:
            break
        common += 1
    merged = "".join(a_lines[:common])
    tail_a = a_lines[common:]
    tail_b = b_lines[common:]
    merged += "".join(tail_a)
    a_stripped = {ln.strip() for ln in tail_a if ln.strip()}
    for line in tail_b:
        stripped = line.strip()
        if not stripped or _OBSOLETE_LINE.match(stripped):
            continue
        if stripped not in a_stripped:
            merged += line
    return merged


def evaluate_under_target_policy(
    part: PartitionedPath,
    side_a: str | None,
    side_b: str | None,
    policy: AuthorityResolutionPolicy,
) -> PolicyEvalResult:
    """Per-path evidence under TARGET-authoritative policy."""

    side_a = side_a or ""
    side_b = side_b or ""
    refs = list(policy.authority_refs) + [f"policy:{policy.policy_id}"]

    arch_a = _arch_choices(side_a)
    arch_b = _arch_choices(side_b)
    if arch_b and arch_a:
        new_arch = [b for b in arch_b if b not in arch_a]
        if new_arch:
            return PolicyEvalResult(
                resolution_class=ResolutionClass.OWNER_REQUIRED,
                resolution_kind=ResolutionKind.UNRESOLVED,
                reason="policy_residual:incoming_redefines_target_architecture",
                allowed=False,
                authority_refs=refs,
                compatibility_reason="incoming_architecture_choice_conflicts_with_target",
            )

    biz_a = _business_choices(side_a)
    biz_b = _business_choices(side_b)
    if biz_b and biz_a:
        new_biz = [b for b in biz_b if b not in biz_a]
        if new_biz:
            return PolicyEvalResult(
                resolution_class=ResolutionClass.OWNER_REQUIRED,
                resolution_kind=ResolutionKind.UNRESOLVED,
                reason="policy_residual:incoming_redefines_target_business",
                allowed=False,
                authority_refs=refs,
                compatibility_reason="incoming_business_choice_conflicts_with_target",
            )

    markers = _authority_from_markers(side_a)
    preserved = list(policy.preserved_invariants) + markers
    ver_req = list(policy.verification_requirements)
    if part.path.endswith(".py"):
        ver_req.append("resolution:python_syntax_ok")
    ver_req.append("candidate:bound:post_resolution")

    if _is_trivial_textual(side_a, side_b):
        return PolicyEvalResult(
            resolution_class=ResolutionClass.AUTO_SAFE,
            resolution_kind=ResolutionKind.UNION,
            reason="policy_target_trivial_union",
            allowed=True,
            authority_refs=refs,
            preserved_invariants=preserved,
            reason_not_new_decision="trivial_under_target_policy",
            verification_requirements=ver_req,
            compatibility_reason="trivial_textual_compatible_with_target",
        )

    if not path_verification_available(part.path):
        return PolicyEvalResult(
            resolution_class=ResolutionClass.OWNER_REQUIRED,
            resolution_kind=ResolutionKind.UNRESOLVED,
            reason="policy_residual:bounded_verification_unavailable",
            allowed=False,
            authority_refs=refs,
            compatibility_reason="verification_not_bounded",
        )

    synthesized = synthesize_under_target_authority(side_a, side_b)
    incoming_preserved = any(
        ln.strip()
        for ln in side_b.splitlines()
        if ln.strip()
        and not _OBSOLETE_LINE.match(ln.strip())
        and ln.strip() not in {x.strip() for x in side_a.splitlines()}
        and ln.strip() in synthesized
    )
    obsolete_rejected = any(
        _OBSOLETE_LINE.match(ln.strip()) for ln in side_b.splitlines() if ln.strip()
    )

    return PolicyEvalResult(
        resolution_class=ResolutionClass.AI_SEMANTIC,
        resolution_kind=ResolutionKind.SYNTHESIS,
        reason="policy_target_synthesis",
        allowed=True,
        authority_refs=refs + ["incoming_delta:incorporate_compatible"],
        preserved_invariants=preserved,
        side_a_intent_refs=[f"target_line:{i}" for i in range(len(side_a.splitlines()))],
        side_b_intent_refs=[
            f"incoming_line:{i}" for i in range(len(side_b.splitlines()))
        ],
        reason_not_new_decision=(
            "target_authoritative_with_compatible_incoming_deltas"
            if incoming_preserved or obsolete_rejected
            else "target_authoritative_no_additive_incoming"
        ),
        verification_requirements=ver_req,
        compatibility_reason=(
            "compatible_incoming_synthesized_under_target"
            if incoming_preserved
            else "target_preserved_no_compatible_incoming"
        ),
    )


def build_policy_from_owner_choice(
    choice: str,
    lane: AuthorityLane,
    covered_paths: list[str],
    cluster_ids: list[str | None],
    owner_decision_ref: str,
    policy_id: str | None = None,
) -> AuthorityResolutionPolicy | None:
    """Materialize policy from Owner policy-level choice."""

    if choice == "new_synthesis":
        return None

    pid = policy_id or hashlib.sha256(
        f"{choice}:{lane.value}:{','.join(sorted(covered_paths))}".encode()
    ).hexdigest()[:16]

    contract = "target" if choice == "target_authoritative" else "incoming"
    refs = ["sources.yaml:allowlist:A_IN_SCOPE", f"owner_decision:{choice}"]
    preserved = ["process_lane_class_a"]
    if contract == "target":
        preserved.append("target_contract_authoritative")

    return AuthorityResolutionPolicy(
        policy_id=pid,
        lane=lane,
        covered_paths=sorted(covered_paths),
        covered_cluster_ids=[c for c in cluster_ids if c],
        authority_refs=refs,
        authoritative_contract=contract,
        preserved_invariants=preserved,
        incoming_delta_policy="incorporate_compatible_reject_obsolete",
        forbidden_changes=[
            "resurrect_obsolete_incoming_contract",
            "silent_target_authority_change",
            "cross_lane_write",
        ],
        verification_requirements=[
            "resolution:bound:per_path",
            "candidate:bound:post_resolution",
        ],
        owner_decision_ref=owner_decision_ref,
    )


def aggregate_authority_policy_packets(
    classified: list[ClassifiedConflict],
    partitions: list[PartitionedPath],
    clusters: list[SemanticCluster],
) -> list[AuthorityPolicyPacket]:
    """Policy-level Owner questions for compatible process authority domains."""

    part_by_path = {p.path: p for p in partitions}
    eligible: list[ClassifiedConflict] = []
    for item in classified:
        part = part_by_path.get(item.path)
        if part and is_policy_eligible(item, part):
            eligible.append(item)

    if len(eligible) < 2:
        return []

    by_cluster_lane: dict[tuple[str | None, str], list[ClassifiedConflict]] = {}
    for item in eligible:
        key = (item.cluster_id, item.lane.value)
        by_cluster_lane.setdefault(key, []).append(item)

    packets: list[AuthorityPolicyPacket] = []
    for cluster_id, lane_key in sorted(by_cluster_lane.keys(), key=lambda k: (k[1], k[0] or "")):
        items = by_cluster_lane[(cluster_id, lane_key)]
        if len(items) < 2:
            continue
        paths = sorted({i.path for i in items})
        reasons = sorted({i.reason for i in items})
        policy_id = hashlib.sha256(
            f"policy_packet:{cluster_id}:{lane_key}:{','.join(paths)}".encode()
        ).hexdigest()[:16]
        packets.append(
            AuthorityPolicyPacket(
                policy_id=policy_id,
                cluster_id=cluster_id,
                lane=lane_key,
                covered_paths=paths,
                question_type="process_authority_conflict",
                options=[
                    {
                        "id": "target_authoritative",
                        "label": "TARGET contract authoritative",
                    },
                    {
                        "id": "incoming_authoritative",
                        "label": "INCOMING contract authoritative",
                    },
                    {
                        "id": "new_synthesis",
                        "label": "New synthesis / architecture decision",
                    },
                ],
                authority_evidence=[
                    "lane:process",
                    "inventory:A_IN_SCOPE",
                    f"owner_required_count:{len(items)}",
                ],
                conflicting_reasons=reasons,
            )
        )
    return packets


_SUPPORTED_POLICY_CHOICES = frozenset(
    {"target_authoritative", "incoming_authoritative", "new_synthesis"}
)


def materialize_policies_from_choices(
    policy_choices: dict[str, str],
    policy_packets: list[AuthorityPolicyPacket],
) -> tuple[list[AuthorityResolutionPolicy], str | None]:
    """
    Validate Owner policy choices against current PREVIEW packets.

    Returns materialized policies or fail-closed stop_reason.
    """

    if not policy_choices:
        return [], None

    pkt_by_id = {p.policy_id: p for p in policy_packets}
    resolved: dict[str, str] = {}
    for pid, choice in policy_choices.items():
        if not pid or "=" in pid or not choice:
            return [], f"POLICY_CHOICE_INVALID:malformed:{pid!r}={choice!r}"
        if pid in resolved and resolved[pid] != choice:
            return [], f"POLICY_CHOICE_CONFLICT:duplicate:{pid}"
        resolved[pid] = choice

    policies: list[AuthorityResolutionPolicy] = []
    for pid, choice in resolved.items():
        if pid not in pkt_by_id:
            return [], f"POLICY_CHOICE_INVALID:unknown_policy_id:{pid}"
        if choice not in _SUPPORTED_POLICY_CHOICES:
            return [], f"POLICY_CHOICE_INVALID:unsupported_choice:{pid}:{choice}"
        pkt = pkt_by_id[pid]
        if choice == "new_synthesis":
            continue
        built = build_policy_from_owner_choice(
            choice=choice,
            lane=AuthorityLane(pkt.lane),
            covered_paths=pkt.covered_paths,
            cluster_ids=[pkt.cluster_id],
            owner_decision_ref=f"{pid}:{choice}",
            policy_id=pid,
        )
        if built:
            policies.append(built)

    return policies, None


def apply_policies_to_classified(
    classified: list[ClassifiedConflict],
    partitions: list[PartitionedPath],
    stage_texts: dict[str, tuple[str | None, str | None, str | None]],
    policies: list[AuthorityResolutionPolicy],
) -> list[ClassifiedConflict]:
    """Reclassify covered paths under approved Owner policies."""

    if not policies:
        return classified

    part_by_path = {p.path: p for p in partitions}
    policy_by_path: dict[str, AuthorityResolutionPolicy] = {}
    for policy in policies:
        for path in policy.covered_paths:
            if path in part_by_path and part_by_path[path].lane == policy.lane:
                policy_by_path[path] = policy

    updated: list[ClassifiedConflict] = []
    for item in classified:
        policy = policy_by_path.get(item.path)
        if not policy or item.resolution_class != ResolutionClass.OWNER_REQUIRED:
            updated.append(item)
            continue

        part = part_by_path[item.path]
        base, side_a, side_b = stage_texts.get(item.path, (None, None, None))

        if policy.authoritative_contract == "target":
            eval_result = evaluate_under_target_policy(part, side_a, side_b, policy)
        elif policy.authoritative_contract == "incoming":
            eval_result = evaluate_under_target_policy(
                part, side_b, side_a, policy
            )
        else:
            updated.append(item)
            continue

        updated.append(
            ClassifiedConflict(
                conflict_id=item.conflict_id,
                cluster_id=item.cluster_id,
                path=item.path,
                lane=item.lane,
                resolution_class=eval_result.resolution_class,
                resolution_kind=eval_result.resolution_kind,
                reason=eval_result.reason,
                owner_options=item.owner_options if not eval_result.allowed else [],
                semantic_authority_refs=eval_result.authority_refs,
                side_a_intent_refs=eval_result.side_a_intent_refs,
                side_b_intent_refs=eval_result.side_b_intent_refs,
                preserved_invariants=eval_result.preserved_invariants,
                applied_policy_id=policy.policy_id,
                policy_compatibility_reason=eval_result.compatibility_reason,
            )
        )
    return updated


def _policy_store_root(repo_root: Path) -> Path:
    repo_id = repo_root.resolve().name
    return Path.home() / ".opsx" / "resolve-conflict" / "policies" / repo_id


def save_approved_policies(
    repo_root: Path,
    fingerprint: str,
    policies: list[AuthorityResolutionPolicy],
) -> Path:
    """Persist approved policies with execution evidence."""

    root = _policy_store_root(repo_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{fingerprint[:16]}.json"
    payload = {
        "schema": "opsx-resolve-conflict/authority-policy/v1",
        "fingerprint": fingerprint,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "policies": [p.to_dict() for p in policies],
    }
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


def load_approved_policies(repo_root: Path, fingerprint: str) -> list[AuthorityResolutionPolicy]:
    path = _policy_store_root(repo_root) / f"{fingerprint[:16]}.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [AuthorityResolutionPolicy.from_dict(p) for p in data.get("policies") or []]
