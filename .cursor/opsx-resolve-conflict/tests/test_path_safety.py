"""CF-001 / R13: reject path traversal; read paths must not mkdir."""

from __future__ import annotations

from pathlib import Path

import pytest

from opsx_conflict.errors import PolicyViolation, StopRequired
from opsx_conflict.pathsafety import (
    normalize_repo_rel,
    prepare_new_path_under_repo,
    resolve_existing_under_repo,
    resolve_under_repo,
)


@pytest.mark.parametrize(
    "bad",
    [
        "../other/file.txt",
        "..\\other\\file.txt",
        "/etc/passwd",
        "C:/Windows/system.ini",
        "//server/share/x",
        "foo/../../escape.txt",
    ],
)
def test_normalize_rejects_escapes(bad: str) -> None:
    with pytest.raises((PolicyViolation, StopRequired)):
        normalize_repo_rel(bad)


def test_sibling_prefix_escape_blocked(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    sibling = tmp_path / "repo-other"
    repo.mkdir()
    sibling.mkdir()
    target = sibling / "secret.txt"
    target.write_text("secret\n", encoding="utf-8")
    with pytest.raises((PolicyViolation, StopRequired)):
        resolve_under_repo(repo, "../repo-other/secret.txt")


def test_resolve_under_repo_does_not_create_missing_parents(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    rel, path = resolve_under_repo(repo, "openspec/changes/missing/authority.json")
    assert rel == "openspec/changes/missing/authority.json"
    assert not path.exists()
    assert not (repo / "openspec").exists()


def test_resolve_existing_requires_present_path(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(StopRequired) as exc:
        resolve_existing_under_repo(repo, "openspec/changes/missing/x.json")
    assert exc.value.reason == "PATH_NOT_FOUND"
    assert not (repo / "openspec").exists()


def test_prepare_new_path_creates_parents_under_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    rel, path = prepare_new_path_under_repo(repo, "nested/dir/file.txt")
    assert rel == "nested/dir/file.txt"
    assert path.parent.is_dir()
    assert path.parent == (repo / "nested" / "dir").resolve()
