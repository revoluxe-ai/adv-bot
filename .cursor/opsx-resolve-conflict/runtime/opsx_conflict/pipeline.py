"""Unified conflict pipeline orchestrator."""

from __future__ import annotations

import hashlib
import os
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from opsx_conflict.authority_policy import (
    aggregate_authority_policy_packets,
    apply_policies_to_classified,
    load_approved_policies,
    materialize_policies_from_choices,
    save_approved_policies,
    validate_policies_for_operation,
)
from opsx_conflict.classify import aggregate_owner_packets, classify_path
from opsx_conflict.cluster import build_clusters
from opsx_conflict.execution_state import ExecutionRunState, load_execution_state, save_execution_state
from opsx_conflict.git_capture import (
    capture_operation,
    compute_fingerprint,
    GitCaptureError,
    read_stage_content,
    stage_file,
)
from opsx_conflict.ledger import append_ledger
from opsx_conflict.models import (
    AuthorityLane,
    ClassifiedConflict,
    PipelineResult,
    PipelineStage,
    ResolutionClass,
    ResolutionLedgerEntry,
    ResolutionKind,
)
from opsx_conflict.partition import is_mixed_scope, partition_manifest
from opsx_conflict.path_cas import (
    capture_pre_write_identities,
    path_identity,
    verify_resume_cas,
)
from opsx_conflict.process_policy import process_lane_may_write
from opsx_conflict.resolve_text import (
    resolve_text,
    restore_worktree_path,
    write_resolved_file,
)
from opsx_conflict.semantic_authority import evaluate_ai_semantic_authority
from opsx_conflict.verify import (
    detect_logical_conflict_in_cluster,
    validate_synthesis_candidate,
    verify_candidate,
    verify_resolution_unit,
)
from opsx_conflict.verification_handoff import (
    build_verification_handoff,
    validate_external_verification_packet,
)


class PipelineError(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class WriteFaultInjected(PipelineError):
    """Controlled fault injection for recovery tests."""


def _operation_identity_str(manifest) -> str:
    op = manifest.operation
    return (
        f"{op.operation_type.value}:{op.head_oid}:{op.operation_head_oid or 'none'}"
    )


def _lane_may_autonomous_write(lane: AuthorityLane, path: str, repo_root: Path) -> bool:
    if lane == AuthorityLane.PROCESS:
        ok, _ = process_lane_may_write(path, repo_root)
        return ok
    return lane in (
        AuthorityLane.PROJECT_CONFIG,
        AuthorityLane.SPEC_GOVERNANCE,
        AuthorityLane.PRODUCT,
    )


def _escalate_classified_to_owner(
    classified: list[ClassifiedConflict],
    path: str,
    validation_reason: str,
) -> list[ClassifiedConflict]:
    """Downgrade path to OWNER_REQUIRED after failed synthesis validation."""

    escalated: list[ClassifiedConflict] = []
    for item in classified:
        if item.path != path:
            escalated.append(item)
            continue
        escalated.append(
            ClassifiedConflict(
                conflict_id=item.conflict_id,
                cluster_id=item.cluster_id,
                path=item.path,
                lane=item.lane,
                resolution_class=ResolutionClass.OWNER_REQUIRED,
                resolution_kind=ResolutionKind.UNRESOLVED,
                reason=f"synthesis_validation_escalation:{validation_reason}",
                owner_options=[
                    {"id": "side_a", "label": "Keep side A"},
                    {"id": "side_b", "label": "Keep side B"},
                    {"id": "synthesis", "label": "Manual synthesis"},
                ],
                semantic_authority_refs=item.semantic_authority_refs,
                side_a_intent_refs=item.side_a_intent_refs,
                side_b_intent_refs=item.side_b_intent_refs,
                preserved_invariants=item.preserved_invariants,
                applied_policy_id=item.applied_policy_id,
                policy_compatibility_reason=item.policy_compatibility_reason,
            )
        )
    return escalated


def _apply_owner_escalations(
    classified: list[ClassifiedConflict],
    escalated: dict[str, str],
) -> list[ClassifiedConflict]:
    """Overlay durable OWNER_REQUIRED escalations from execution state."""

    result = classified
    for path, reason in escalated.items():
        result = _escalate_classified_to_owner(result, path, reason)
    return result


def _collect_stage_texts(repo_root: Path, partitions) -> dict[str, tuple[str | None, str | None, str | None]]:
    texts: dict[str, tuple[str | None, str | None, str | None]] = {}
    for part in partitions:
        base = read_stage_content(repo_root, part.path, 1)
        side_a = read_stage_content(repo_root, part.path, 2)
        side_b = read_stage_content(repo_root, part.path, 3)
        texts[part.path] = (base, side_a, side_b)
    return texts


def run_preview(
    repo_root: Path,
    drill_down_path: str | None = None,
    approved_policies: list | None = None,
    owner_policy_choices: dict[str, str] | None = None,
) -> PipelineResult:
    """PREVIEW / PLAN — whole-operation capture, partition, classify."""

    runtime_revision = os.environ.get("OPSX_RESOLVER_RUNTIME_SOURCE_REVISION", "")
    bootstrap_revision = os.environ.get("OPSX_BOOTSTRAP_SOURCE_REVISION", "")

    try:
        manifest = capture_operation(repo_root)
    except GitCaptureError as exc:
        return PipelineResult(
            status="STOP_FOR_OWNER",
            stage=PipelineStage.FAILED,
            stop_reason=exc.reason,
            runtime_source_revision=runtime_revision,
            bootstrap_source_revision=bootstrap_revision,
        )

    partitions = partition_manifest(manifest, repo_root)
    unmerged_set = {p.path for p in partitions}

    if drill_down_path and drill_down_path not in unmerged_set:
        return PipelineResult(
            status="STOP_FOR_OWNER",
            stage=PipelineStage.FAILED,
            manifest=manifest,
            stop_reason=f"drill_down_path_not_unmerged:{drill_down_path}",
            fingerprint=manifest.fingerprint,
            runtime_source_revision=runtime_revision,
            bootstrap_source_revision=bootstrap_revision,
        )

    clusters = build_clusters(partitions)
    stage_texts = _collect_stage_texts(repo_root, partitions)

    worktree_texts: dict[str, str | None] = {}
    for part in partitions:
        p = repo_root / part.path
        worktree_texts[part.path] = (
            p.read_text(encoding="utf-8", errors="replace") if p.is_file() else None
        )

    classified = []
    for part in partitions:
        cluster_id = None
        for cl in clusters:
            if part.path in cl.paths:
                cluster_id = cl.cluster_id
                break
        base, side_a, side_b = stage_texts.get(part.path, (None, None, None))
        classified.append(
            classify_path(
                part,
                cluster_id,
                side_a,
                side_b,
                worktree_texts.get(part.path),
                base_text=base,
                repo_root=repo_root,
            )
        )

    policies = list(approved_policies or [])
    policy_choices = dict(owner_policy_choices or {})

    if policy_choices and not policies:
        preliminary_packets = aggregate_authority_policy_packets(
            classified, partitions, clusters
        )
        new_policies, policy_err = materialize_policies_from_choices(
            policy_choices, preliminary_packets
        )
        if policy_err:
            return PipelineResult(
                status="FAILED",
                stage=PipelineStage.FAILED,
                manifest=manifest,
                partitions=partitions,
                clusters=clusters,
                classified=classified,
                fingerprint=manifest.fingerprint,
                stop_reason=policy_err,
                runtime_source_revision=runtime_revision,
                bootstrap_source_revision=bootstrap_revision,
            )
        policies.extend(new_policies)
        if policies:
            save_approved_policies(repo_root, manifest.fingerprint, policies)

    if not policies:
        policies = load_approved_policies(repo_root, manifest.fingerprint)

    if policies:
        stale_err = validate_policies_for_operation(
            policies, partitions, unmerged_set
        )
        if stale_err:
            return PipelineResult(
                status="FAILED",
                stage=PipelineStage.FAILED,
                manifest=manifest,
                partitions=partitions,
                clusters=clusters,
                classified=classified,
                fingerprint=manifest.fingerprint,
                stop_reason=stale_err,
                runtime_source_revision=runtime_revision,
                bootstrap_source_revision=bootstrap_revision,
            )
        classified = apply_policies_to_classified(
            classified, partitions, stage_texts, policies
        )

    policy_packets = aggregate_authority_policy_packets(
        classified, partitions, clusters
    )
    pending_policy_paths = {p for pkt in policy_packets for p in pkt.covered_paths}
    owner_packets = aggregate_owner_packets(
        classified, clusters, exclude_paths=pending_policy_paths
    )
    mixed = is_mixed_scope(partitions)
    owner_count = sum(
        1 for c in classified if c.resolution_class == ResolutionClass.OWNER_REQUIRED
    )

    status = "PREVIEW_READY"
    stage = PipelineStage.CLASSIFY
    if owner_count or policy_packets:
        stage = PipelineStage.PAUSED

    path_detail: dict[str, Any] | None = None
    if drill_down_path:
        part = next((p for p in partitions if p.path == drill_down_path), None)
        cls = next((c for c in classified if c.path == drill_down_path), None)
        cluster = next((c for c in clusters if drill_down_path in c.paths), None)
        if part and cls:
            path_detail = {
                "path": drill_down_path,
                "lane": part.lane.value,
                "inventory": part.inventory_class,
                "conflict_kind": part.unmerged.kind.value,
                "cluster_id": cls.cluster_id,
                "resolution_class": cls.resolution_class.value,
                "resolution_kind": cls.resolution_kind.value,
                "reason": cls.reason,
                "cluster_paths": cluster.paths if cluster else [drill_down_path],
                "cluster_evidence": cluster.evidence if cluster else [],
                "cluster_member_lanes": cluster.member_lanes if cluster else {},
                "cluster_authority_homogeneous": (
                    cluster.authority_homogeneous if cluster else True
                ),
                "applied_policy_id": cls.applied_policy_id,
                "policy_compatibility_reason": cls.policy_compatibility_reason,
            }

    return PipelineResult(
        status=status,
        stage=stage,
        manifest=manifest,
        partitions=partitions,
        clusters=clusters,
        classified=classified,
        owner_packets=owner_packets,
        authority_policy_packets=policy_packets,
        approved_policies=policies,
        fingerprint=manifest.fingerprint,
        stop_reason="mixed_scope_partitioned" if mixed else None,
        drill_down_path=drill_down_path,
        path_detail=path_detail,
        runtime_source_revision=runtime_revision,
        bootstrap_source_revision=bootstrap_revision,
    )


def run_go(
    repo_root: Path,
    frozen_fingerprint: str | None = None,
    owner_choices: dict[str, str] | None = None,
    lanes: list[str] | None = None,
    stage_only: bool = True,
    write_fault_at_path: str | None = None,
    resume_run_id: str | None = None,
    verification_evidence: dict[str, Any] | None = None,
    authority_policies: list | None = None,
    owner_policy_choices: dict[str, str] | None = None,
) -> PipelineResult:
    """GO — resolve, stage candidate, terminal gate with verification handoff."""

    policies = list(authority_policies or [])
    owner_policy_choices = owner_policy_choices or {}

    if owner_policy_choices and not policies:
        probe = run_preview(repo_root)
        if probe.status == "FAILED" and probe.stop_reason:
            return probe
        new_policies, policy_err = materialize_policies_from_choices(
            owner_policy_choices, probe.authority_policy_packets
        )
        if policy_err:
            return PipelineResult(
                status="FAILED",
                stage=PipelineStage.FAILED,
                manifest=probe.manifest,
                fingerprint=probe.fingerprint,
                stop_reason=policy_err,
            )
        policies.extend(new_policies)
        if policies and probe.fingerprint:
            save_approved_policies(repo_root, probe.fingerprint, policies)

    preview = run_preview(
        repo_root,
        approved_policies=policies or None,
        owner_policy_choices=owner_policy_choices if not policies else None,
    )
    if preview.status == "STOP_FOR_OWNER":
        return preview

    manifest = preview.manifest
    if manifest is None:
        return PipelineResult(
            status="STOP_FOR_OWNER",
            stage=PipelineStage.FAILED,
            stop_reason="no_manifest",
        )

    current_fp = compute_fingerprint(repo_root)
    if not resume_run_id:
        if frozen_fingerprint and frozen_fingerprint != current_fp:
            return PipelineResult(
                status="STALE_EXECUTION",
                stage=PipelineStage.FAILED,
                manifest=manifest,
                stop_reason="REPLAN_REQUIRED",
                fingerprint=current_fp,
            )

    run_id = resume_run_id or uuid.uuid4().hex[:16]
    owner_choices = owner_choices or {}
    allowed_lanes = {AuthorityLane(l) for l in lanes} if lanes else None

    planned_paths = [
        c.path for c in preview.classified
        if c.resolution_class in (
            ResolutionClass.AUTO_SAFE,
            ResolutionClass.AI_SEMANTIC,
        )
        or (c.resolution_class == ResolutionClass.OWNER_REQUIRED
            and c.path in owner_choices)
        or c.path in owner_choices
    ]

    exec_state = ExecutionRunState(
        run_id=run_id,
        operation_fingerprint=current_fp,
        pending_paths=list(planned_paths),
    )

    if resume_run_id:
        loaded = load_execution_state(repo_root, resume_run_id)
        if loaded:
            exec_state = loaded
        cas_ok, cas_reason = verify_resume_cas(
            repo_root, exec_state, planned_paths
        )
        if not cas_ok:
            return PipelineResult(
                status="STALE_EXECUTION",
                stage=PipelineStage.FAILED,
                manifest=manifest,
                classified=preview.classified,
                fingerprint=current_fp,
                run_id=run_id,
                stop_reason=cas_reason or "REPLAN_REQUIRED",
                execution_state=exec_state.to_dict(),
            )
    else:
        exec_state.path_pre_write = capture_pre_write_identities(
            repo_root, planned_paths
        )
        save_execution_state(repo_root, exec_state)

    ledger_entries: list[ResolutionLedgerEntry] = []
    resolved_paths: list[str] = list(exec_state.completed_paths)
    staged_paths: list[str] = []
    prior_evidence: dict[str, str] = {}
    stage_texts = _collect_stage_texts(repo_root, preview.partitions)
    op_id = _operation_identity_str(manifest)
    active_classified = _apply_owner_escalations(
        preview.classified,
        exec_state.owner_escalated_paths,
    )

    for item in active_classified:
        if item.path in exec_state.completed_paths:
            continue

        part = next(p for p in preview.partitions if p.path == item.path)
        if allowed_lanes and part.lane not in allowed_lanes:
            continue

        if item.resolution_class == ResolutionClass.OWNER_REQUIRED:
            if item.path not in owner_choices:
                continue
        elif item.resolution_class not in (
            ResolutionClass.AUTO_SAFE,
            ResolutionClass.AI_SEMANTIC,
        ):
            continue

        if item.path in exec_state.owner_escalated_paths:
            if item.path not in owner_choices:
                continue

        if not _lane_may_autonomous_write(part.lane, item.path, repo_root):
            if (
                item.resolution_class != ResolutionClass.OWNER_REQUIRED
                and item.path not in owner_choices
            ):
                continue

        if write_fault_at_path and item.path == write_fault_at_path:
            exec_state.failed_path = item.path
            exec_state.status = "FAILED_PARTIAL"
            save_execution_state(repo_root, exec_state)
            return PipelineResult(
                status="FAILED",
                stage=PipelineStage.FAILED,
                manifest=manifest,
                classified=preview.classified,
                ledger=ledger_entries,
                fingerprint=current_fp,
                run_id=run_id,
                stop_reason=f"write_fault_injected:{item.path}",
                execution_state=exec_state.to_dict(),
            )

        base, side_a, side_b = stage_texts.get(item.path, (None, None, None))
        worktree_path = repo_root / item.path
        worktree = (
            worktree_path.read_text(encoding="utf-8", errors="replace")
            if worktree_path.is_file()
            else None
        )

        choice = owner_choices.get(item.path)
        resolved_text, kind = resolve_text(
            item, side_a, side_b, worktree, owner_choice=choice
        )
        if kind == ResolutionKind.UNRESOLVED:
            continue

        valid, val_refs = validate_synthesis_candidate(
            item.path,
            resolved_text,
            allow_delete=kind == ResolutionKind.DELETE,
        )
        if not valid:
            reason = val_refs[0] if val_refs else "validation_failed"
            exec_state.failed_path = item.path
            exec_state.status = "PAUSED_OWNER_REQUIRED"
            exec_state.owner_escalated_paths[item.path] = reason
            save_execution_state(repo_root, exec_state)
            escalated = _escalate_classified_to_owner(
                active_classified,
                item.path,
                reason,
            )
            return PipelineResult(
                status="PAUSED",
                stage=PipelineStage.PAUSED,
                manifest=manifest,
                partitions=preview.partitions,
                clusters=preview.clusters,
                classified=escalated,
                ledger=ledger_entries,
                owner_packets=aggregate_owner_packets(escalated, preview.clusters),
                staged_paths=staged_paths,
                fingerprint=current_fp,
                run_id=run_id,
                stop_reason=f"synthesis_validation_failed:{item.path}:{reason}",
                execution_state=exec_state.to_dict(),
            )

        wt_hash = write_resolved_file(repo_root, item.path, resolved_text)
        exec_state.path_post_write[item.path] = path_identity(repo_root, item.path)
        ok, verify_refs = verify_resolution_unit(
            repo_root, item.path, item, resolution_kind=kind.value
        )
        if not ok:
            restore_worktree_path(repo_root, item.path, worktree)
            exec_state.path_post_write.pop(item.path, None)
            exec_state.failed_path = item.path
            exec_state.status = "PAUSED_OWNER_REQUIRED"
            verify_reason = verify_refs[0] if verify_refs else "verification_failed"
            exec_state.owner_escalated_paths[item.path] = verify_reason
            save_execution_state(repo_root, exec_state)
            escalated = _escalate_classified_to_owner(
                active_classified,
                item.path,
                verify_reason,
            )
            return PipelineResult(
                status="PAUSED",
                stage=PipelineStage.PAUSED,
                manifest=manifest,
                partitions=preview.partitions,
                clusters=preview.clusters,
                classified=escalated,
                ledger=ledger_entries,
                owner_packets=aggregate_owner_packets(escalated, preview.clusters),
                staged_paths=staged_paths,
                fingerprint=current_fp,
                run_id=run_id,
                stop_reason=f"synthesis_validation_failed:{item.path}:{verify_reason}",
                execution_state=exec_state.to_dict(),
            )

        auth_refs = list(item.semantic_authority_refs)
        sa_intent = list(item.side_a_intent_refs)
        sb_intent = list(item.side_b_intent_refs)
        preserved = list(item.preserved_invariants)
        reason_not_new = ""
        ver_req: list[str] = []

        if (
            item.resolution_class == ResolutionClass.AI_SEMANTIC
            and not item.applied_policy_id
            and kind == ResolutionKind.SYNTHESIS
        ):
            auth_eval = evaluate_ai_semantic_authority(
                part, side_a, side_b, base, repo_root
            )
            auth_refs = auth_eval.authority_refs
            sa_intent = auth_eval.side_a_intent_refs
            sb_intent = auth_eval.side_b_intent_refs
            preserved = auth_eval.preserved_invariants
            reason_not_new = auth_eval.reason_not_new_decision
            ver_req = auth_eval.verification_requirements
        elif item.applied_policy_id:
            reason_not_new = item.policy_compatibility_reason
            ver_req = [
                "resolution:bound:per_path",
                "candidate:bound:post_resolution",
            ]

        entry = ResolutionLedgerEntry(
            conflict_id=item.conflict_id,
            cluster_id=item.cluster_id,
            path=item.path,
            operation_identity=op_id,
            base_oid=manifest.operation.base_oid,
            side_a_oid=manifest.operation.side_a_oid,
            side_b_oid=manifest.operation.side_b_oid,
            authority_refs=auth_refs + [f"lane:{part.lane.value}"],
            lane=part.lane.value,
            resolution_class=item.resolution_class.value,
            resolution_kind=kind.value,
            reason=item.reason,
            result_blob_oid=None,
            result_worktree_sha256=wt_hash,
            verification_refs=verify_refs,
            side_a_intent_refs=sa_intent,
            side_b_intent_refs=sb_intent,
            preserved_invariants=preserved,
            reason_not_new_decision=reason_not_new or item.policy_compatibility_reason,
            verification_requirements=ver_req,
            policy_id=item.applied_policy_id,
            policy_compatibility_reason=item.policy_compatibility_reason,
        )
        ledger_entries.append(entry)
        resolved_paths.append(item.path)
        exec_state.completed_paths.append(item.path)
        exec_state.owner_escalated_paths.pop(item.path, None)
        exec_state.pending_paths = [
            p for p in exec_state.pending_paths if p != item.path
        ]
        save_execution_state(repo_root, exec_state)

        if stage_only:
            try:
                stage_file(repo_root, item.path)
                staged_paths.append(item.path)
            except GitCaptureError as exc:
                exec_state.status = "FAILED_PARTIAL"
                save_execution_state(repo_root, exec_state)
                return PipelineResult(
                    status="FAILED",
                    stage=PipelineStage.FAILED,
                    stop_reason=exc.reason,
                    fingerprint=current_fp,
                    run_id=run_id,
                    execution_state=exec_state.to_dict(),
                )

    append_ledger(repo_root, run_id, ledger_entries)

    for cl in preview.clusters:
        found, reason = detect_logical_conflict_in_cluster(
            repo_root, cl.paths, manifest.auto_merged_paths
        )
        if found:
            exec_state.status = "FAILED_LOGICAL"
            save_execution_state(repo_root, exec_state)
            return PipelineResult(
                status="FAILED",
                stage=PipelineStage.FAILED,
                stop_reason=reason,
                manifest=manifest,
                ledger=ledger_entries,
                fingerprint=current_fp,
                run_id=run_id,
                execution_state=exec_state.to_dict(),
            )

    cand_ok, cand_refs, new_evidence = verify_candidate(
        repo_root,
        manifest,
        resolved_paths,
        ledger_entries,
        prior_evidence,
    )

    remaining_owner = [
        c
        for c in active_classified
        if c.resolution_class == ResolutionClass.OWNER_REQUIRED
        and c.path not in owner_choices
    ]

    if remaining_owner:
        exec_state.status = "PAUSED_OWNER_REQUIRED"
        save_execution_state(repo_root, exec_state)
        return PipelineResult(
            status="PAUSED",
            stage=PipelineStage.PAUSED,
            manifest=manifest,
            partitions=preview.partitions,
            clusters=preview.clusters,
            classified=active_classified,
            ledger=ledger_entries,
            owner_packets=aggregate_owner_packets(active_classified, preview.clusters),
            staged_paths=staged_paths,
            fingerprint=current_fp,
            run_id=run_id,
            stop_reason="owner_decisions_pending",
            execution_state=exec_state.to_dict(),
        )

    if not cand_ok:
        return PipelineResult(
            status="FAILED",
            stage=PipelineStage.FAILED,
            stop_reason=f"candidate_verification_failed:{cand_refs}",
            ledger=ledger_entries,
            fingerprint=current_fp,
            run_id=run_id,
        )

    if not resolved_paths:
        return PipelineResult(
            status="PAUSED",
            stage=PipelineStage.PAUSED,
            manifest=manifest,
            fingerprint=current_fp,
            stop_reason="no_resolvable_paths_in_scope",
        )

    handoff = build_verification_handoff(
        repo_root, manifest, ledger_entries, resolved_paths, op_id
    )
    candidate_id = handoff.candidate_identity
    exec_state.status = "RESOLVED_PENDING_VERIFICATION"
    save_execution_state(repo_root, exec_state)

    # Terminal gate: VERIFIED only with external evidence packet
    verification_stop: str | None = None
    if verification_evidence:
        valid, ver_refs = validate_external_verification_packet(
            handoff, verification_evidence, repo_root=repo_root
        )
        if valid:
            exec_state.status = "VERIFIED_READY_FOR_CONTINUE"
            save_execution_state(repo_root, exec_state)
            return PipelineResult(
                status="VERIFIED_READY_FOR_CONTINUE",
                stage=PipelineStage.VERIFIED_READY_FOR_CONTINUE,
                manifest=manifest,
                partitions=preview.partitions,
                clusters=preview.clusters,
                classified=preview.classified,
                ledger=ledger_entries,
                staged_paths=staged_paths,
                fingerprint=current_fp,
                run_id=run_id,
                candidate_identity=candidate_id,
                verification_handoff=handoff.to_dict(),
                execution_state=exec_state.to_dict(),
            )
        verification_stop = (
            ver_refs[0] if ver_refs else "verification_packet_invalid"
        )

    return PipelineResult(
        status="RESOLVED_PENDING_VERIFICATION",
        stage=PipelineStage.RESOLVED_PENDING_VERIFICATION,
        manifest=manifest,
        partitions=preview.partitions,
        clusters=preview.clusters,
        classified=preview.classified,
        ledger=ledger_entries,
        staged_paths=staged_paths,
        fingerprint=current_fp,
        run_id=run_id,
        candidate_identity=candidate_id,
        verification_handoff=handoff.to_dict(),
        execution_state=exec_state.to_dict(),
        stop_reason=verification_stop,
    )


def result_to_report(result: PipelineResult) -> dict:
    """Machine JSON report."""

    report = {
        "STATUS": result.status,
        "STAGE": result.stage.value,
        "STOP_REASON": result.stop_reason,
        "FINGERPRINT": result.fingerprint,
        "STAGED_PATHS": result.staged_paths,
        "RUN_ID": result.run_id,
        "CANDIDATE_IDENTITY": result.candidate_identity,
        "RUNTIME_SOURCE_REVISION": result.runtime_source_revision,
        "BOOTSTRAP_SOURCE_REVISION": result.bootstrap_source_revision,
        "GO_CAPABILITY": True,
        "GIT_CONTINUE": "FORBIDDEN",
        "RESOLVED_CLAIMED": "YES" if result.status in (
            "RESOLVED_PENDING_VERIFICATION",
            "VERIFIED_READY_FOR_CONTINUE",
        ) else "NO",
        "VERIFIED_CLAIMED": "YES" if result.status == "VERIFIED_READY_FOR_CONTINUE" else "NO",
    }
    if result.drill_down_path:
        report["DRILL_DOWN_PATH"] = result.drill_down_path
    if result.path_detail:
        report["PATH_DETAIL"] = result.path_detail
    if result.verification_handoff:
        report["VERIFICATION_HANDOFF"] = result.verification_handoff
    if result.execution_state:
        report["EXECUTION_STATE"] = result.execution_state
    if result.manifest:
        report["OPERATION"] = result.manifest.operation.operation_type.value
        report["UNMERGED_COUNT"] = len(result.manifest.unmerged_paths)
        report["PATH_INVENTORY"] = result.manifest.path_inventory()
    if result.partitions:
        report["PARTITION"] = {
            "mixed_scope": is_mixed_scope(result.partitions),
            "lanes": sorted({p.lane.value for p in result.partitions}),
            "paths": [
                {
                    "path": p.path,
                    "lane": p.lane.value,
                    "inventory": p.inventory_class,
                }
                for p in result.partitions
            ],
        }
    if result.classified:
        report["CLASSIFICATION"] = {
            "AUTO_SAFE": sum(
                1 for c in result.classified
                if c.resolution_class == ResolutionClass.AUTO_SAFE
            ),
            "AI_SEMANTIC": sum(
                1 for c in result.classified
                if c.resolution_class == ResolutionClass.AI_SEMANTIC
            ),
            "OWNER_REQUIRED": sum(
                1 for c in result.classified
                if c.resolution_class == ResolutionClass.OWNER_REQUIRED
            ),
        }
        report["CLASSIFIED_PATHS"] = [
            {
                "path": c.path,
                "lane": c.lane.value,
                "cluster_id": c.cluster_id,
                "resolution_class": c.resolution_class.value,
                "resolution_kind": c.resolution_kind.value,
                "reason": c.reason,
                "applied_policy_id": c.applied_policy_id,
                "policy_compatibility_reason": c.policy_compatibility_reason,
            }
            for c in result.classified
        ]
    if result.clusters:
        report["CLUSTERS"] = [
            {
                "id": c.cluster_id,
                "paths": c.paths,
                "member_lanes": c.member_lanes,
                "authority_homogeneous": c.authority_homogeneous,
                "lane": c.lane.value if c.lane is not None else None,
                "evidence": c.evidence,
            }
            for c in result.clusters
        ]
    if result.authority_policy_packets:
        report["AUTHORITY_POLICY_PACKETS"] = [
            p.to_dict() if hasattr(p, "to_dict") else p
            for p in result.authority_policy_packets
        ]
    if result.approved_policies:
        report["APPROVED_POLICIES"] = [
            p.to_dict() if hasattr(p, "to_dict") else p
            for p in result.approved_policies
        ]
    if result.owner_packets:
        report["OWNER_DECISION_PACKETS"] = [
            {
                "decision_id": p.decision_id,
                "paths": p.paths,
                "options": p.options,
                "recommended": p.recommended_option,
            }
            for p in result.owner_packets
        ]
    if result.ledger:
        report["LEDGER_ENTRIES"] = [e.to_dict() for e in result.ledger]
    return report