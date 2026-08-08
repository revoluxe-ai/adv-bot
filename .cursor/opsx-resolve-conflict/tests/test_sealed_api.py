from __future__ import annotations

from pathlib import Path

import pytest

import opsx_conflict.runtime as runtime
from opsx_conflict.runtime import GitClient, PolicyViolation, ScopeItem, ScopeManifest


def test_git_client_exposes_typed_reads_only() -> None:
    assert not hasattr(GitClient, "read")
    assert hasattr(GitClient, "status_porcelain_v2_z")
    assert hasattr(GitClient, "diff_cached_name_status_z")


def test_validate_check_argv_is_not_public() -> None:
    assert not hasattr(runtime, "validate_check_argv")


def test_scope_manifest_items_are_frozen(tmp_path: Path) -> None:
    scope = ScopeManifest(
        [
            ScopeItem(
                path="app/x.py",
                unit_id="u1",
                reason="test",
                authority_source="active",
                authority_sha256="0" * 64,
                allowed_operation="write",
                expected_semantic_change="resolve merge conflict",
                initial_stage_oids={"1": "a", "2": "b", "3": "c"},
                initial_worktree_sha256="x",
                required_checks=(("syntax-parse", "app/x.py"),),
            )
        ],
        run_id="run-1",
        frozen_at_fingerprint="f" * 64,
    )
    with pytest.raises(TypeError):
        scope.items["app/x.py"] = scope.items["app/x.py"]  # type: ignore[index]
