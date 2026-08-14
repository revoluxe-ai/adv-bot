"""R39: recursive PREVIEW evidence path sanitization (closes R38 JSON bypass)."""

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
    TRUSTED_GIT_EXECUTABLE_TOKEN,
    assert_no_author_paths,
    assert_no_author_paths_in_json,
    stage_package_from_tree,
    validate_preview_evidence_doc,
    write_evidence_pair,
)

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows PREVIEW_ONLY")


def _win_users_path(*parts: str) -> str:
    """Build a Windows profile path without embedding contiguous forbidden literals."""
    return "C:\\" + "Users" + "\\" + "\\".join(parts)


def _posix_home_path(*parts: str) -> str:
    return "/" + "home" + "/" + "/".join(parts)


def _macos_users_path(*parts: str) -> str:
    return "/" + "Users" + "/" + "/".join(parts)


@pytest.fixture(scope="module")
def evidence_pair(tmp_path_factory) -> tuple[dict, dict, Path, Path]:
    """Generate real merge/rebase PREVIEW evidence once per module."""
    out = tmp_path_factory.mktemp("r39_preview_evidence")
    staging = out / "staging"
    package_staging = stage_package_from_tree(staging)
    merge_p, rebase_p, _index_p = write_evidence_pair(
        out_dir=out,
        package_staging=package_staging,
        package_name="OPSX_RESOLVE_CONFLICT_COMMAND_001_R40_TEST",
        package_version="0.40.0",
        package_digest="a" * 64,
        inner_archive_sha256="b" * 64,
    )
    merge = json.loads(merge_p.read_text(encoding="utf-8"))
    rebase = json.loads(rebase_p.read_text(encoding="utf-8"))
    return merge, rebase, merge_p, rebase_p


def test_recursive_json_string_value_path_scan() -> None:
    """Recursive walker rejects nested forbidden raw strings."""
    bad = {"outer": {"inner": [_win_users_path("alice", "trusted-git-bin", "git.EXE")]}}
    with pytest.raises(SystemExit):
        assert_no_author_paths_in_json(bad, label="nested")


def test_windows_backslash_profile_path() -> None:
    with pytest.raises(SystemExit):
        assert_no_author_paths(
            _win_users_path("alice", "x", "git.EXE"), label="win-bs"
        )


def test_windows_forward_slash_profile_path() -> None:
    path = "C:/" + "Users" + "/alice/git.EXE"
    with pytest.raises(SystemExit):
        assert_no_author_paths(path, label="win-fs")
    with pytest.raises(SystemExit):
        assert_no_author_paths_in_json({"p": path}, label="win-fs-json")


def test_linux_home_path() -> None:
    path = _posix_home_path("alice", ".local", "git")
    with pytest.raises(SystemExit):
        assert_no_author_paths(path, label="linux")
    with pytest.raises(SystemExit):
        assert_no_author_paths_in_json({"p": path}, label="linux-json")


def test_macos_users_path() -> None:
    path = _macos_users_path("alice", "bin", "git")
    with pytest.raises(SystemExit):
        assert_no_author_paths(path, label="macos")
    with pytest.raises(SystemExit):
        assert_no_author_paths_in_json({"p": path}, label="macos-json")


def test_nested_dict_path() -> None:
    with pytest.raises(SystemExit):
        assert_no_author_paths_in_json(
            {"git_executable": {"executable_path_tokenized": _win_users_path("a", "g")}},
            label="dict",
        )


def test_nested_list_path() -> None:
    with pytest.raises(SystemExit):
        assert_no_author_paths_in_json(
            {"command_ledger": [{"executable_path": _posix_home_path("a", "git")}]},
            label="list",
        )


def test_json_escaping_regression_r38_bypass() -> None:
    """Serialized JSON escapes backslashes; recursive walk must still catch."""
    raw = _win_users_path("alice", ".opsx-resolve-conflict", "trusted-git-bin", "git.EXE")
    dumped = json.dumps({"path": raw})
    # R38 bug: scanning dumps alone may miss Win profile paths because JSON
    # escapes backslashes. Authoritative check is recursive on parsed values.
    with pytest.raises(SystemExit):
        assert_no_author_paths_in_json(json.loads(dumped), label="r38-bypass")
    # Confirm raw path is still rejected when scanned as a raw string.
    with pytest.raises(SystemExit):
        assert_no_author_paths(raw, label="r38-raw")


def test_merge_evidence_generation_regression(evidence_pair) -> None:
    merge, _rebase, _mp, _rp = evidence_pair
    assert merge["operation"] == "merge"
    assert merge["terminal_result"]["status"] == "PREVIEW_READY"


def test_rebase_evidence_generation_regression(evidence_pair) -> None:
    _merge, rebase, _mp, _rp = evidence_pair
    assert rebase["operation"] == "rebase"
    assert rebase["terminal_result"]["status"] == "PREVIEW_READY"


def test_stage_oid_regression(evidence_pair) -> None:
    merge, rebase, _mp, _rp = evidence_pair
    for doc in (merge, rebase):
        for stage in ("1", "2", "3"):
            assert doc["stage_blob_oids"][stage]


def test_mutation_invariant_regression(evidence_pair) -> None:
    merge, rebase, _mp, _rp = evidence_pair
    for doc in (merge, rebase):
        mut = doc["mutation_invariants"]
        assert mut["refs_unchanged"] is True
        assert mut["index_unchanged"] is True
        assert mut["worktree_unchanged"] is True
        assert mut["unmerged_unchanged"] is True


def test_command_ledger_read_only_and_tokenized(evidence_pair) -> None:
    merge, rebase, _mp, _rp = evidence_pair
    for doc in (merge, rebase):
        assert_no_author_paths_in_json(doc, label=doc["scenario_id"])
        for entry in doc["command_ledger"]:
            assert entry["operation_id"] in {
                "resolve_git_dir",
                "resolve_head",
                "read_refs",
                "read_unmerged_index",
                "read_stage_blob",
            }
            assert entry["executable_path"] == TRUSTED_GIT_EXECUTABLE_TOKEN
            assert entry["expected_executable_digest"]
            assert entry["observed_pre_exec_digest"]
            assert entry["expected_executable_digest"] == entry["observed_pre_exec_digest"]
            assert entry["atomicity_claim"] is False
        assert (
            doc["git_executable"]["executable_path_tokenized"]
            == TRUSTED_GIT_EXECUTABLE_TOKEN
        )
        # No profile path substrings in any string leaf.
        _u = "Users"
        _h = "home"
        win_marker = _u + "\\"
        posix_users = "/" + _u + "/"
        posix_home = "/" + _h + "/"
        for _jp, raw in __import__(
            "build_preview_evidence", fromlist=["iter_json_strings"]
        ).iter_json_strings(doc):
            assert win_marker not in raw and posix_users not in raw
            assert posix_home not in raw


def test_validator_rejects_nested_windows_author_path(evidence_pair) -> None:
    merge, _rebase, _mp, _rp = evidence_pair
    bad = copy.deepcopy(merge)
    bad["command_ledger"] = list(bad["command_ledger"])
    bad["command_ledger"][0] = dict(bad["command_ledger"][0])
    bad["command_ledger"][0]["executable_path"] = _win_users_path(
        "alice", "trusted-git-bin", "git.EXE"
    )
    with pytest.raises(SystemExit):
        validate_preview_evidence_doc(
            bad,
            expected_operation="merge",
            package_name=merge["package_name"],
            package_version=merge["package_version"],
            package_digest="a" * 64,
            inner_archive_sha256="b" * 64,
            label="fault-win",
        )


def test_validator_rejects_nested_posix_author_path(evidence_pair) -> None:
    merge, _rebase, _mp, _rp = evidence_pair
    bad = copy.deepcopy(merge)
    bad["extra"] = {"paths": [_posix_home_path("bob", "git")]}
    with pytest.raises(SystemExit):
        validate_preview_evidence_doc(
            bad,
            expected_operation="merge",
            package_name=merge["package_name"],
            package_version=merge["package_version"],
            package_digest="a" * 64,
            inner_archive_sha256="b" * 64,
            label="fault-posix",
        )


def test_r37_runtime_hash_pins() -> None:
    runtime = PACKAGE_ROOT / "runtime" / "opsx_conflict"
    for name, expected in FROZEN_PREVIEW_RUNTIME_HASHES.items():
        digest = hashlib.sha256((runtime / name).read_bytes()).hexdigest()
        assert digest == expected, name
