"""U6: PREVIEW --policy-choice runtime wiring."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
sys.path.insert(0, str(RUNTIME))

from opsx_conflict.__main__ import main as cli_main
from opsx_conflict.models import ResolutionClass
from opsx_conflict.pipeline import run_preview, result_to_report

COMPAT_PATH = ".cursor/commands/opsx-alpha.md"
RESIDUAL_PATH = ".cursor/commands/opsx-residual.md"


@pytest.mark.unit
def test_u6_a_preview_policy_choice_wiring(process_authority_policy_repo: Path) -> None:
    """U6-A: PREVIEW with --policy-choice applies policy and reclassifies."""

    before = run_preview(process_authority_policy_repo)
    pkt = before.authority_policy_packets[0]
    policy_id = pkt.policy_id

    after = run_preview(
        process_authority_policy_repo,
        owner_policy_choices={policy_id: "target_authoritative"},
    )
    assert after.status == "PREVIEW_READY"
    covered = set(pkt.covered_paths)
    evaluated = [
        c
        for c in after.classified
        if c.path in covered and c.applied_policy_id == policy_id
    ]
    assert evaluated
    for item in evaluated:
        assert item.policy_compatibility_reason

    report = result_to_report(after)
    classified = {p["path"]: p for p in report["CLASSIFIED_PATHS"]}
    assert classified[COMPAT_PATH]["applied_policy_id"] == policy_id
    assert classified[COMPAT_PATH]["policy_compatibility_reason"]


@pytest.mark.unit
def test_u6_a_cli_preview_policy_choice(process_authority_policy_repo: Path) -> None:
    """U6-A: __main__ forwards --policy-choice to PREVIEW."""

    before = run_preview(process_authority_policy_repo)
    pkt = before.authority_policy_packets[0]
    code = cli_main(
        [
            "PREVIEW",
            "--repo",
            str(process_authority_policy_repo),
            "--policy-choice",
            f"{pkt.policy_id}=target_authoritative",
            "--json",
        ]
    )
    assert code in (0, 3)
    after = run_preview(
        process_authority_policy_repo,
        owner_policy_choices={pkt.policy_id: "target_authoritative"},
    )
    assert any(c.applied_policy_id == pkt.policy_id for c in after.classified)


@pytest.mark.unit
def test_u6_b_compression_after_preview_policy(process_authority_policy_repo: Path) -> None:
    """U6-B: TARGET policy via PREVIEW materially compresses OWNER_REQUIRED."""

    before = run_preview(process_authority_policy_repo)
    before_owner = sum(
        1 for c in before.classified if c.resolution_class == ResolutionClass.OWNER_REQUIRED
    )
    pkt = before.authority_policy_packets[0]
    after = run_preview(
        process_authority_policy_repo,
        owner_policy_choices={pkt.policy_id: "target_authoritative"},
    )
    after_owner = sum(
        1 for c in after.classified if c.resolution_class == ResolutionClass.OWNER_REQUIRED
    )
    after_auto_sem = sum(
        1
        for c in after.classified
        if c.resolution_class
        in (ResolutionClass.AUTO_SAFE, ResolutionClass.AI_SEMANTIC)
    )
    assert after_auto_sem > 4
    assert after_owner < before_owner
    assert after_owner <= 2


@pytest.mark.unit
def test_u6_c_residual_under_applied_policy(process_authority_policy_repo: Path) -> None:
    """U6-C: residual path shows applied_policy_id + OWNER_REQUIRED."""

    before = run_preview(process_authority_policy_repo)
    pkt = before.authority_policy_packets[0]
    after = run_preview(
        process_authority_policy_repo,
        owner_policy_choices={pkt.policy_id: "target_authoritative"},
    )
    residual = next(c for c in after.classified if c.path == RESIDUAL_PATH)
    assert residual.applied_policy_id == pkt.policy_id
    assert residual.resolution_class == ResolutionClass.OWNER_REQUIRED
    assert residual.policy_compatibility_reason
    assert "policy_residual" in residual.reason


@pytest.mark.unit
def test_u6_d_invalid_policy_id_fail_closed(process_authority_policy_repo: Path) -> None:
    """U6-D: unknown policy_id fails closed, not silent PREVIEW."""

    result = run_preview(
        process_authority_policy_repo,
        owner_policy_choices={"nonexistent_policy_id": "target_authoritative"},
    )
    assert result.status == "FAILED"
    assert result.stop_reason
    assert "POLICY_CHOICE_INVALID" in result.stop_reason

    code = cli_main(
        [
            "PREVIEW",
            "--repo",
            str(process_authority_policy_repo),
            "--policy-choice",
            "nonexistent_policy_id=target_authoritative",
            "--json",
        ]
    )
    assert code == 2


@pytest.mark.unit
def test_u6_e_report_integrity_after_policy(process_authority_policy_repo: Path) -> None:
    """U6-E: CLASSIFIED_PATHS and OWNER_DECISION_PACKETS agree after policy."""

    before = run_preview(process_authority_policy_repo)
    pkt = before.authority_policy_packets[0]
    after = run_preview(
        process_authority_policy_repo,
        owner_policy_choices={pkt.policy_id: "target_authoritative"},
    )
    report = result_to_report(after)
    classified = {p["path"]: p for p in report["CLASSIFIED_PATHS"]}
    owner_paths = {p for pkt in report.get("OWNER_DECISION_PACKETS", []) for p in pkt["paths"]}

    for path, row in classified.items():
        if row["resolution_class"] in ("AUTO_SAFE", "AI_SEMANTIC"):
            assert path not in owner_paths

    if RESIDUAL_PATH in classified:
        assert classified[RESIDUAL_PATH]["applied_policy_id"] == pkt.policy_id
        assert RESIDUAL_PATH in owner_paths or classified[RESIDUAL_PATH]["resolution_class"] == "OWNER_REQUIRED"

    assert classified[COMPAT_PATH]["resolution_class"] in ("AUTO_SAFE", "AI_SEMANTIC")
    assert COMPAT_PATH not in owner_paths
