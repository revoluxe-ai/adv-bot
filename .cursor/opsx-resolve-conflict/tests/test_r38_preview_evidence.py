"""R38: immutable real merge/rebase PREVIEW evidence."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PACKAGE_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(PACKAGE_ROOT / "runtime"))

from build_preview_evidence import (  # noqa: E402
    FROZEN_PREVIEW_RUNTIME_HASHES,
    assert_no_author_paths_in_json,
    stage_package_from_tree,
    validate_preview_evidence_doc,
    write_evidence_pair,
)

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows PREVIEW_ONLY")


@pytest.fixture(scope="module")
def evidence_pair(tmp_path_factory) -> tuple[dict, dict, Path, Path]:
    """Generate real merge/rebase PREVIEW evidence once per module."""
    out = tmp_path_factory.mktemp("r38_preview_evidence")
    staging = out / "staging"
    package_staging = stage_package_from_tree(staging)
    package_name = "OPSX_RESOLVE_CONFLICT_COMMAND_001_R38_TEST"
    package_version = "0.38.0"
    package_digest = "a" * 64
    archive_sha = "b" * 64
    merge_p, rebase_p, _index_p = write_evidence_pair(
        out_dir=out,
        package_staging=package_staging,
        package_name=package_name,
        package_version=package_version,
        package_digest=package_digest,
        inner_archive_sha256=archive_sha,
    )
    merge = json.loads(merge_p.read_text(encoding="utf-8"))
    rebase = json.loads(rebase_p.read_text(encoding="utf-8"))
    return merge, rebase, merge_p, rebase_p


def test_real_merge_preview_evidence_generation(evidence_pair) -> None:
    merge, _rebase, _mp, _rp = evidence_pair
    assert merge["operation"] == "merge"
    assert merge["terminal_result"]["status"] == "PREVIEW_READY"
    assert merge["stage_blob_oids"]["1"]
    assert merge["stage_blob_oids"]["2"]
    assert merge["stage_blob_oids"]["3"]


def test_real_rebase_preview_evidence_generation(evidence_pair) -> None:
    _merge, rebase, _mp, _rp = evidence_pair
    assert rebase["operation"] == "rebase"
    assert rebase["terminal_result"]["status"] == "PREVIEW_READY"
    assert rebase["fixture_meta"].get("rebase_dir_present") is True
    assert rebase["stage_blob_oids"]["1"]
    assert rebase["stage_blob_oids"]["2"]
    assert rebase["stage_blob_oids"]["3"]


def test_stage_123_presence(evidence_pair) -> None:
    merge, rebase, _mp, _rp = evidence_pair
    for doc in (merge, rebase):
        for stage in ("1", "2", "3"):
            oid = doc["stage_blob_oids"][stage]
            assert len(oid) in {40, 64}
            assert all(c in "0123456789abcdefABCDEF" for c in oid)


def test_operation_identity(evidence_pair) -> None:
    merge, rebase, _mp, _rp = evidence_pair
    assert merge["operation"] == "merge"
    assert rebase["operation"] == "rebase"
    assert merge["CURRENT_CONFLICT"]["operation"] == "merge"
    assert rebase["CURRENT_CONFLICT"]["operation"] == "rebase"


def test_command_ledger_separated_from_fixture_setup(evidence_pair) -> None:
    merge, rebase, _mp, _rp = evidence_pair
    for doc in (merge, rebase):
        setup = doc["fixture_setup_ledger"]
        preview = doc["command_ledger"]
        assert setup and all(e.get("phase") == "FIXTURE_SETUP" for e in setup)
        assert setup and all(e.get("not_preview") for e in setup)
        assert any("merge" in e["argv"] or "rebase" in e["argv"] for e in setup)
        assert preview
        assert all(e.get("operation_id") for e in preview)
        assert all("phase" not in e or e.get("phase") != "FIXTURE_SETUP" for e in preview)


def test_no_mutation_before_after(evidence_pair) -> None:
    merge, rebase, _mp, _rp = evidence_pair
    for doc in (merge, rebase):
        mut = doc["mutation_invariants"]
        assert mut["refs_unchanged"] is True
        assert mut["index_unchanged"] is True
        assert mut["worktree_unchanged"] is True
        assert mut["unmerged_unchanged"] is True
        assert doc["refs_before_digest"] == doc["refs_after_digest"]
        assert doc["index_before_digest"] == doc["index_after_digest"]
        assert doc["worktree_before_digest"] == doc["worktree_after_digest"]
        assert doc["unmerged_inventory_before"] == doc["unmerged_inventory_after"]


def test_evidence_hash_binding(evidence_pair) -> None:
    merge, rebase, merge_p, rebase_p = evidence_pair
    for doc, path in ((merge, merge_p), (rebase, rebase_p)):
        assert doc["package_digest"] == "a" * 64
        assert doc["inner_archive_sha256"] == "b" * 64
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert len(digest) == 64


def test_wrong_package_digest_fault(evidence_pair) -> None:
    merge, _rebase, _mp, _rp = evidence_pair
    bad = copy.deepcopy(merge)
    bad["package_digest"] = "c" * 64
    with pytest.raises(SystemExit) as exc:
        validate_preview_evidence_doc(
            bad,
            expected_operation="merge",
            package_name=merge["package_name"],
            package_version=merge["package_version"],
            package_digest="a" * 64,
            inner_archive_sha256="b" * 64,
            label="fault-digest",
        )
    assert "package_digest" in str(exc.value)


def test_missing_evidence_fault(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc:
        from build_preview_evidence import validate_preview_evidence_artifacts

        validate_preview_evidence_artifacts(
            merge_path=tmp_path / "missing_merge.json",
            rebase_path=tmp_path / "missing_rebase.json",
            package_name="x",
            package_version="0.38.0",
            package_digest="a" * 64,
            inner_archive_sha256="b" * 64,
        )
    assert "missing" in str(exc.value).lower()


def test_mutating_ledger_entry_fault(evidence_pair) -> None:
    merge, _rebase, _mp, _rp = evidence_pair
    bad = copy.deepcopy(merge)
    bad["command_ledger"] = list(bad["command_ledger"]) + [
        {
            "operation_id": "merge",
            "argv": ["git", "merge", "feature"],
            "atomicity_claim": False,
        }
    ]
    with pytest.raises(SystemExit) as exc:
        validate_preview_evidence_doc(
            bad,
            expected_operation="merge",
            package_name=merge["package_name"],
            package_version=merge["package_version"],
            package_digest="a" * 64,
            inner_archive_sha256="b" * 64,
            label="fault-mutate",
        )
    assert "mutating" in str(exc.value).lower() or "unknown" in str(exc.value).lower()


def test_author_workspace_path_rejection(evidence_pair) -> None:
    merge, _rebase, _mp, _rp = evidence_pair
    # Evidence itself must already be clean under recursive scan.
    assert_no_author_paths_in_json(merge, label="merge-clean")
    _u = "Users"
    poisoned = {
        "nested": {"path": f"C:\\{_u}\\vkita\\my_code\\" + "meta" + "-repo\\adv-bot\\leak"}
    }
    with pytest.raises(SystemExit):
        assert_no_author_paths_in_json(poisoned, label="poison")


def test_r37_runtime_semantic_hash_pins() -> None:
    runtime = PACKAGE_ROOT / "runtime" / "opsx_conflict"
    for name, expected in FROZEN_PREVIEW_RUNTIME_HASHES.items():
        digest = hashlib.sha256((runtime / name).read_bytes()).hexdigest()
        assert digest == expected, name
