"""U: authority policy → bounded automatic synthesis."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
sys.path.insert(0, str(RUNTIME))

from opsx_conflict.authority_policy import (
    build_policy_from_owner_choice,
    synthesize_under_target_authority,
)
from opsx_conflict.models import AuthorityLane, ResolutionClass
from opsx_conflict.pipeline import run_go, run_preview, result_to_report
from opsx_conflict.resolve_text import resolve_text


COMPAT_PATH = ".cursor/commands/opsx-alpha.md"
RESIDUAL_PATH = ".cursor/commands/opsx-residual.md"
PRODUCT_PATH = "app/module.py"


@pytest.mark.unit
def test_u1_decision_compression(process_authority_policy_repo: Path) -> None:
    """U1: one Owner policy reclassifies majority of process OWNER_REQUIRED."""

    preview = run_preview(process_authority_policy_repo)
    before_owner = sum(
        1 for c in preview.classified if c.resolution_class == ResolutionClass.OWNER_REQUIRED
    )
    assert before_owner >= 8
    assert preview.authority_policy_packets
    pkt = preview.authority_policy_packets[0]
    assert len(pkt.covered_paths) >= 8

    policy = build_policy_from_owner_choice(
        choice="target_authoritative",
        lane=AuthorityLane.PROCESS,
        covered_paths=pkt.covered_paths,
        cluster_ids=[pkt.cluster_id],
        owner_decision_ref=f"{pkt.policy_id}:target_authoritative",
    )
    assert policy is not None

    after = run_preview(process_authority_policy_repo, approved_policies=[policy])
    auto_or_sem = sum(
        1
        for c in after.classified
        if c.path in pkt.covered_paths
        and c.resolution_class
        in (ResolutionClass.AUTO_SAFE, ResolutionClass.AI_SEMANTIC)
    )
    residual = sum(
        1
        for c in after.classified
        if c.path in pkt.covered_paths
        and c.resolution_class == ResolutionClass.OWNER_REQUIRED
    )
    assert auto_or_sem >= 6
    assert residual <= 2
    assert auto_or_sem > residual
    assert len(after.authority_policy_packets) == 0 or residual > 0


@pytest.mark.unit
def test_u2_no_blanket_keep_ours(process_authority_policy_repo: Path) -> None:
    """U2: TARGET policy preserves compatible incoming additive behavior."""

    preview = run_preview(process_authority_policy_repo)
    pkt = preview.authority_policy_packets[0]
    policy = build_policy_from_owner_choice(
        "target_authoritative",
        AuthorityLane.PROCESS,
        pkt.covered_paths,
        [pkt.cluster_id],
        f"{pkt.policy_id}:target",
    )
    assert policy is not None
    after = run_preview(process_authority_policy_repo, approved_policies=[policy])
    item = next(c for c in after.classified if c.path == COMPAT_PATH)
    assert item.resolution_class in (
        ResolutionClass.AUTO_SAFE,
        ResolutionClass.AI_SEMANTIC,
    )
    assert item.applied_policy_id == policy.policy_id

    from opsx_conflict.git_capture import read_stage_content

    side_a = read_stage_content(process_authority_policy_repo, COMPAT_PATH, 2) or ""
    side_b = read_stage_content(process_authority_policy_repo, COMPAT_PATH, 3) or ""
    resolved, kind = resolve_text(item, side_a, side_b, None)
    assert resolved is not None
    assert "INCOMING_COMPAT: additive-" in resolved
    assert "TARGET_CONTRACT: v2-" in resolved
    assert "OBSOLETE_CONTRACT:" not in resolved
    assert kind.value == "SYNTHESIS" or kind.value == "UNION"
    assert resolved != side_a  # not blind keep_ours


@pytest.mark.unit
def test_u3_residual_architecture_contradiction(
    process_authority_policy_repo: Path,
) -> None:
    """U3: incoming redefining TARGET architecture stays OWNER_REQUIRED."""

    preview = run_preview(process_authority_policy_repo)
    pkt = preview.authority_policy_packets[0]
    assert RESIDUAL_PATH in pkt.covered_paths
    policy = build_policy_from_owner_choice(
        "target_authoritative",
        AuthorityLane.PROCESS,
        pkt.covered_paths,
        [pkt.cluster_id],
        f"{pkt.policy_id}:target",
    )
    assert policy is not None
    after = run_preview(process_authority_policy_repo, approved_policies=[policy])
    residual = next(c for c in after.classified if c.path == RESIDUAL_PATH)
    assert residual.resolution_class == ResolutionClass.OWNER_REQUIRED
    assert "policy_residual" in residual.reason


@pytest.mark.unit
def test_u4_policy_scope_process_only(process_authority_policy_repo: Path) -> None:
    """U4: process policy does not change product authority or write product."""

    preview = run_preview(process_authority_policy_repo)
    prod = next(p for p in preview.partitions if p.path == PRODUCT_PATH)
    assert prod.lane == AuthorityLane.PRODUCT

    pkt = preview.authority_policy_packets[0]
    assert PRODUCT_PATH not in pkt.covered_paths
    policy = build_policy_from_owner_choice(
        "target_authoritative",
        AuthorityLane.PROCESS,
        pkt.covered_paths,
        [pkt.cluster_id],
        f"{pkt.policy_id}:target",
    )
    assert policy is not None
    after = run_preview(process_authority_policy_repo, approved_policies=[policy])
    prod_cls = next(c for c in after.classified if c.path == PRODUCT_PATH)
    assert prod_cls.lane == AuthorityLane.PRODUCT
    assert prod_cls.applied_policy_id is None

    result = run_go(
        process_authority_policy_repo,
        frozen_fingerprint=after.fingerprint,
        authority_policies=[policy],
        lanes=["process"],
    )
    assert PRODUCT_PATH not in result.staged_paths


@pytest.mark.unit
def test_u5_provenance_records_policy(process_authority_policy_repo: Path) -> None:
    """U5: resolved paths record policy_id and compatibility evidence."""

    preview = run_preview(process_authority_policy_repo)
    pkt = preview.authority_policy_packets[0]
    policy = build_policy_from_owner_choice(
        "target_authoritative",
        AuthorityLane.PROCESS,
        pkt.covered_paths,
        [pkt.cluster_id],
        f"{pkt.policy_id}:target",
    )
    assert policy is not None
    after = run_preview(process_authority_policy_repo, approved_policies=[policy])
    report = result_to_report(after)
    classified = {p["path"]: p for p in report["CLASSIFIED_PATHS"]}
    assert classified[COMPAT_PATH]["applied_policy_id"] == policy.policy_id
    assert classified[COMPAT_PATH]["policy_compatibility_reason"]

    result = run_go(
        process_authority_policy_repo,
        frozen_fingerprint=preview.fingerprint,
        authority_policies=[policy],
        lanes=["process"],
    )
    policy_entries = [e for e in result.ledger if e.policy_id == policy.policy_id]
    assert policy_entries
    for entry in policy_entries:
        assert entry.policy_id
        assert any("policy:" in r or "sources.yaml" in r for r in entry.authority_refs)
        assert entry.preserved_invariants
        assert entry.policy_compatibility_reason
        assert entry.verification_requirements

@pytest.mark.unit
def test_u_synthesize_rejects_obsolete() -> None:
    """Unit: target synthesis keeps additive, drops obsolete."""

    target = "# TARGET_CONTRACT: v2\nshared\n"
    incoming = "# OBSOLETE_CONTRACT: old\nshared\n# INCOMING_COMPAT: keep-me\n"
    out = synthesize_under_target_authority(target, incoming)
    assert "INCOMING_COMPAT: keep-me" in out
    assert "TARGET_CONTRACT: v2" in out
    assert "OBSOLETE_CONTRACT" not in out
