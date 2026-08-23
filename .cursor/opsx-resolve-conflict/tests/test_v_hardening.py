"""V: process-lane authority compression."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
sys.path.insert(0, str(RUNTIME))

from opsx_conflict.authority_policy import (
    AuthorityResolutionPolicy,
    build_policy_from_owner_choice,
    evaluate_under_target_policy,
    validate_policies_for_operation,
)
from opsx_conflict.models import (
    AuthorityLane,
    ConflictKind,
    PartitionedPath,
    ResolutionClass,
    UnmergedPath,
)
from opsx_conflict.pipeline import run_preview, result_to_report
from opsx_conflict.registry_verify import verify_registry_ndjson_synthesis

HOP = ".cursor/pipeline/bug-team/runtime/live_task_hop.py"
RULES = ".cursor/rules/testing-rules.mdc"
ADAPTER = ".opsx/adapters/poetry-python/README.md"
MANUAL = ".opsx/project/manual_review.md"
BOOTSTRAP = ".opsx/shared/bootstrap-profile.md"
REG_CA = ".opsx/registry/command_activation.ndjson"
REG_PROV = ".opsx/registry/provenance.ndjson"
ARCH = ".cursor/commands/opsx-arch-residual.md"
CONFTEST = "conftest.py"
WORKLOG = "DOTO/WORKLOG.md"
PRODUCT = "app/product.py"
DELETE_PATH = ".opsx/to_delete_process.txt"

LANE_PATHS = [HOP, RULES, ADAPTER, MANUAL, BOOTSTRAP]


def _apply_lane_policy(repo: Path) -> tuple[object, str]:
    before = run_preview(repo)
    pkt = before.authority_policy_packets[0]
    assert pkt.question_type == "process_lane_authority_conflict"
    after = run_preview(
        repo,
        owner_policy_choices={pkt.policy_id: "target_authoritative"},
    )
    return after, pkt.policy_id


@pytest.mark.unit
def test_v_a_multi_cluster_lane_policy(process_lane_residual_repo: Path) -> None:
    """V-A: one lane policy covers singleton clusters; per-path evidence."""

    before = run_preview(process_lane_residual_repo)
    process_before = sum(
        1
        for c in before.classified
        if c.lane == AuthorityLane.PROCESS
        and c.resolution_class == ResolutionClass.OWNER_REQUIRED
    )
    assert process_before >= 7
    assert len(before.authority_policy_packets) == 1

    after, policy_id = _apply_lane_policy(process_lane_residual_repo)
    lane_evaluated = [
        c
        for c in after.classified
        if c.path in LANE_PATHS
        and c.applied_policy_id == policy_id
    ]
    assert len(lane_evaluated) >= 5
    for item in lane_evaluated:
        assert item.policy_compatibility_reason
        assert item.resolution_class in (
            ResolutionClass.AI_SEMANTIC,
            ResolutionClass.AUTO_SAFE,
        )
    ids = {c.applied_policy_id for c in lane_evaluated}
    assert ids == {policy_id}


@pytest.mark.unit
def test_v_b_cross_lane_containment(process_lane_residual_repo: Path) -> None:
    """V-B: process lane policy does not affect product."""

    after, policy_id = _apply_lane_policy(process_lane_residual_repo)
    prod = next(c for c in after.classified if c.path == PRODUCT)
    assert prod.lane == AuthorityLane.PRODUCT
    assert prod.applied_policy_id is None


@pytest.mark.unit
def test_v_c_delete_modify_hard_stop(process_lane_residual_repo: Path) -> None:
    """V-C: delete/modify remains OWNER_REQUIRED under lane policy."""

    after, _ = _apply_lane_policy(process_lane_residual_repo)
    del_item = next(c for c in after.classified if c.path == DELETE_PATH)
    assert del_item.resolution_class == ResolutionClass.OWNER_REQUIRED
    assert del_item.reason == "delete_modify_requires_owner"
    assert del_item.applied_policy_id is None


@pytest.mark.unit
def test_v_d_architecture_residual(process_lane_residual_repo: Path) -> None:
    """V-D: architecture contradiction evaluated under policy, stays OWNER."""

    after, policy_id = _apply_lane_policy(process_lane_residual_repo)
    arch = next(c for c in after.classified if c.path == ARCH)
    assert arch.applied_policy_id == policy_id
    assert arch.resolution_class == ResolutionClass.OWNER_REQUIRED
    assert "policy_residual" in arch.reason
    assert arch.policy_compatibility_reason


@pytest.mark.unit
def test_v_e_allowlist_gap(process_lane_residual_repo: Path) -> None:
    """V-E: allowlist gaps stay OWNER_REQUIRED."""

    after, _ = _apply_lane_policy(process_lane_residual_repo)
    for path in (CONFTEST, WORKLOG):
        item = next(c for c in after.classified if c.path == path)
        assert item.resolution_class == ResolutionClass.OWNER_REQUIRED
        assert item.reason == "allowlist_gap"
        assert item.applied_policy_id is None


@pytest.mark.unit
def test_v_f_registry_bounded_verification(process_lane_residual_repo: Path) -> None:
    """V-F: registry NDJSON bounded verifier + policy eval (positive/negative)."""

    target = '{"command":"opsx-alpha","STATUS":"APPROVED"}\n'
    incoming = (
        '{"command":"opsx-alpha","STATUS":"APPROVED"}\n'
        '{"command":"opsx-beta","STATUS":"INCOMING"}\n'
    )
    synth = target + '{"command":"opsx-beta","STATUS":"INCOMING"}\n'
    ok, refs = verify_registry_ndjson_synthesis(synth, target, REG_CA)
    assert ok
    assert refs

    bad_ok, bad_refs = verify_registry_ndjson_synthesis(
        '{"command":"opsx-beta","STATUS":"INCOMING"}\n', target, REG_CA
    )
    assert not bad_ok
    assert bad_refs

    policy = build_policy_from_owner_choice(
        "target_authoritative",
        AuthorityLane.PROCESS,
        [REG_CA],
        [],
        "v-f-registry",
        policy_id="vftestregistry01",
    )
    assert policy is not None
    part = PartitionedPath(
        path=REG_CA,
        lane=AuthorityLane.PROCESS,
        inventory_class="A_IN_SCOPE",
        unmerged=UnmergedPath(
            path=REG_CA,
            kind=ConflictKind.BOTH_MODIFIED,
            stages=[],
            worktree_has_markers=False,
        ),
    )
    eval_ok = evaluate_under_target_policy(part, target, incoming, policy)
    assert eval_ok.resolution_class == ResolutionClass.AI_SEMANTIC
    assert eval_ok.reason == "policy_target_synthesis"
    assert "resolution:registry_ndjson_bounded" in eval_ok.verification_requirements

    eval_bad = evaluate_under_target_policy(
        part,
        target,
        '{"broken":}\n',
        policy,
    )
    assert eval_bad.resolution_class == ResolutionClass.OWNER_REQUIRED
    assert eval_bad.reason == "policy_residual:registry_verification_failed"


@pytest.mark.unit
def test_v_g_stale_policy_fail_closed(process_lane_residual_repo: Path) -> None:
    """V-G: stale policy path set fails closed."""

    before = run_preview(process_lane_residual_repo)
    partitions = before.partitions
    stale = AuthorityResolutionPolicy(
        policy_id="stale001",
        lane=AuthorityLane.PROCESS,
        covered_paths=["nonexistent/path.md"],
        covered_cluster_ids=[],
        authority_refs=[],
        authoritative_contract="target",
        preserved_invariants=[],
        incoming_delta_policy="incorporate_compatible_reject_obsolete",
        forbidden_changes=[],
        verification_requirements=[],
        owner_decision_ref="stale",
    )
    err = validate_policies_for_operation(
        [stale],
        partitions,
        {p.path for p in partitions},
    )
    assert err and "POLICY_STALE" in err

    result = run_preview(process_lane_residual_repo, approved_policies=[stale])
    assert result.status == "FAILED"
    assert "POLICY_STALE" in (result.stop_reason or "")


@pytest.mark.unit
def test_v_compression_counts(process_lane_residual_repo: Path) -> None:
    """V-B counts: process OWNER_REQUIRED materially decreases."""

    before = run_preview(process_lane_residual_repo)
    process_owner_before = sum(
        1
        for c in before.classified
        if c.lane == AuthorityLane.PROCESS
        and c.resolution_class == ResolutionClass.OWNER_REQUIRED
    )
    after, _ = _apply_lane_policy(process_lane_residual_repo)
    process_owner_after = sum(
        1
        for c in after.classified
        if c.lane == AuthorityLane.PROCESS
        and c.resolution_class == ResolutionClass.OWNER_REQUIRED
    )
    process_sem_after = sum(
        1
        for c in after.classified
        if c.lane == AuthorityLane.PROCESS
        and c.resolution_class
        in (ResolutionClass.AI_SEMANTIC, ResolutionClass.AUTO_SAFE)
    )
    assert process_owner_before >= 7
    assert process_owner_after <= 4
    assert process_sem_after >= 5


@pytest.mark.unit
def test_v_e_report_integrity(process_lane_residual_repo: Path) -> None:
    """V-E report: CLASSIFIED_PATHS and OWNER packets agree."""

    after, policy_id = _apply_lane_policy(process_lane_residual_repo)
    report = result_to_report(after)
    classified = {p["path"]: p for p in report["CLASSIFIED_PATHS"]}
    owner_paths = {
        p for pkt in report.get("OWNER_DECISION_PACKETS", []) for p in pkt["paths"]
    }
    for path in (HOP, REG_CA):
        if path not in classified:
            continue
        if classified[path]["resolution_class"] in ("AI_SEMANTIC", "AUTO_SAFE"):
            assert classified[path]["applied_policy_id"] == policy_id
            assert path not in owner_paths
    assert ARCH in owner_paths or classified[ARCH]["resolution_class"] == "OWNER_REQUIRED"
