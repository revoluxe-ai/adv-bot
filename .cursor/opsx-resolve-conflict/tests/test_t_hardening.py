"""T: path authority independent of semantic clustering."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
sys.path.insert(0, str(RUNTIME))

from opsx_conflict.models import AuthorityLane, ResolutionClass
from opsx_conflict.pipeline import run_go, run_preview


BILLING_PROD = "app/modules/billing/billing.py"
BILLING_TEST = "tests/modules/billing/test_billing.py"


@pytest.mark.unit
def test_t1_mixed_lane_cluster_preserves_per_path_authority(
    billing_mixed_lane_cluster_repo: Path,
) -> None:
    """T1: billing cluster links producer+test; lanes stay per path."""

    result = run_preview(billing_mixed_lane_cluster_repo)
    assert result.status == "PREVIEW_READY"

    prod_part = next(p for p in result.partitions if p.path == BILLING_PROD)
    test_part = next(p for p in result.partitions if p.path == BILLING_TEST)
    assert prod_part.lane == AuthorityLane.PRODUCT
    assert test_part.lane == AuthorityLane.PROJECT_CONFIG

    cluster = next(
        c for c in result.clusters
        if BILLING_PROD in c.paths and BILLING_TEST in c.paths
    )
    assert not cluster.authority_homogeneous
    assert cluster.lane is None
    assert cluster.member_lanes[BILLING_PROD] == "product"
    assert cluster.member_lanes[BILLING_TEST] == "project_config"
    assert "test_production_relation" in cluster.evidence

    prod_cls = next(c for c in result.classified if c.path == BILLING_PROD)
    test_cls = next(c for c in result.classified if c.path == BILLING_TEST)
    assert prod_cls.lane == AuthorityLane.PRODUCT
    assert test_cls.lane == AuthorityLane.PROJECT_CONFIG


@pytest.mark.unit
def test_t1_preview_report_exposes_member_lanes(
    billing_mixed_lane_cluster_repo: Path,
) -> None:
    """T1: JSON report shows member_lanes, not authoritative cluster lane."""

    from opsx_conflict.pipeline import result_to_report

    preview = run_preview(billing_mixed_lane_cluster_repo)
    report = result_to_report(preview)
    cluster_entry = next(
        c for c in report["CLUSTERS"]
        if BILLING_PROD in c["paths"] and BILLING_TEST in c["paths"]
    )
    assert cluster_entry["authority_homogeneous"] is False
    assert cluster_entry["lane"] is None
    assert cluster_entry["member_lanes"][BILLING_PROD] == "product"
    assert cluster_entry["member_lanes"][BILLING_TEST] == "project_config"

    classified_paths = {p["path"]: p for p in report["CLASSIFIED_PATHS"]}
    assert classified_paths[BILLING_PROD]["lane"] == "product"
    assert classified_paths[BILLING_TEST]["lane"] == "project_config"


@pytest.mark.unit
def test_t2_process_authority_does_not_expand_to_product(
    mixed_scope_conflict_repo: Path,
) -> None:
    """T2: process authority does not spread to product path in preview/GO scope."""

    preview = run_preview(mixed_scope_conflict_repo)
    product_path = "app/module.py"
    prod_part = next(p for p in preview.partitions if p.path == product_path)
    assert prod_part.lane == AuthorityLane.PRODUCT

    prod_cls = next(c for c in preview.classified if c.path == product_path)
    assert prod_cls.lane == AuthorityLane.PRODUCT

    allowed_lanes = {AuthorityLane.PROCESS}
    for item in preview.classified:
        part = next(p for p in preview.partitions if p.path == item.path)
        if item.path == product_path:
            assert part.lane not in allowed_lanes

    prod_cluster = next(c for c in preview.clusters if product_path in c.paths)
    assert prod_cluster.member_lanes[product_path] == "product"
    assert prod_cluster.lane in (AuthorityLane.PRODUCT, None)

    process_cmd = ".cursor/commands/test-cmd.md"
    if process_cmd in {c.path for c in preview.classified}:
        cmd_cls = next(c for c in preview.classified if c.path == process_cmd)
        assert cmd_cls.lane == AuthorityLane.PROCESS


@pytest.mark.unit
def test_t2_process_go_skips_mixed_cluster_product_member(
    billing_mixed_lane_cluster_repo: Path,
) -> None:
    """T2: process lane cannot write product member of mixed semantic cluster."""

    preview = run_preview(billing_mixed_lane_cluster_repo)
    result = run_go(
        billing_mixed_lane_cluster_repo,
        frozen_fingerprint=preview.fingerprint,
        lanes=["process"],
    )
    assert BILLING_PROD not in result.staged_paths
    assert BILLING_TEST not in result.staged_paths


@pytest.mark.unit
def test_t3_homogeneous_process_cluster_aggregates(dual_write_repo: Path) -> None:
    """T3: multiple same-lane paths cluster with homogeneous authority."""

    preview = run_preview(dual_write_repo)
    proc_cluster = next(
        c for c in preview.clusters
        if len(c.paths) >= 2 and all(p.startswith(".opsx/") for p in c.paths)
    )
    assert proc_cluster.authority_homogeneous
    assert proc_cluster.lane == AuthorityLane.PROCESS
    assert all(
        lane == "process" for lane in proc_cluster.member_lanes.values()
    )


@pytest.mark.unit
def test_t3_homogeneous_cluster_owner_packets_per_lane(
    billing_mixed_lane_cluster_repo: Path,
) -> None:
    """T3/T: mixed cluster Owner packets split by lane, not one blended packet."""

    preview = run_preview(billing_mixed_lane_cluster_repo)
    owner_items = [
        c for c in preview.classified
        if c.resolution_class == ResolutionClass.OWNER_REQUIRED
    ]
    if not owner_items:
        pytest.skip("fixture produced no OWNER_REQUIRED paths")

    packets = preview.owner_packets
    if len({c.lane for c in owner_items}) > 1:
        lanes_in_packets = {
            ev.split(":", 1)[1]
            for p in packets
            for ev in p.authority_evidence
            if ev.startswith("lane:")
        }
        assert len(lanes_in_packets) >= 2
