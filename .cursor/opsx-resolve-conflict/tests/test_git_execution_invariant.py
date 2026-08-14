"""Trusted-Git execution invariant: sole launch primitive + pre-exec verify.

ITERATION_ID=R23-CORRECTIVE-GIT-EXEC-01
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from opsx_conflict.errors import StopRequired
from opsx_conflict.git_typed import (
    TypedGit,
    _GIT_EXECUTION_PRIMITIVE,
    _execute_trusted_git,
)

from authority_test_helpers import init_git_repo, pin_git_trust

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
GIT_TYPED = PACKAGE_ROOT / "runtime" / "opsx_conflict" / "git_typed.py"


def _call_name(node: ast.AST) -> str | None:
    """Return dotted call name for subprocess.run / run_process style calls."""
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        return f"{func.value.id}.{func.attr}"
    return None


def test_all_git_process_launches_use_sole_primitive() -> None:
    """Static: subprocess.run / run_process in git_typed.py only inside primitive."""
    tree = ast.parse(GIT_TYPED.read_text(encoding="utf-8"))
    assert _GIT_EXECUTION_PRIMITIVE == "_execute_trusted_git"
    assert any(
        isinstance(n, ast.FunctionDef) and n.name == _GIT_EXECUTION_PRIMITIVE
        for n in tree.body
    )

    forbidden_outside: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for child in ast.walk(node):
            name = _call_name(child)
            if name not in {"subprocess.run", "run_process", "subprocess.Popen"}:
                continue
            if node.name != _GIT_EXECUTION_PRIMITIVE:
                forbidden_outside.append((node.name, getattr(child, "lineno", -1)))
    assert forbidden_outside == [], (
        "Git process launches outside sole primitive: "
        f"{forbidden_outside}"
    )


def test_hash_bytes_no_filters_verifies_bound_before_launch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tamper bound executable before hash-object → typed StopRequired."""
    pin_git_trust(monkeypatch, tmp_path / "state")
    init_git_repo(tmp_path)
    git = TypedGit(tmp_path)
    Path(git.git_bin).write_bytes(b"tampered-bound-git-exec")
    with pytest.raises(StopRequired) as exc:
        git.hash_bytes_no_filters(b"payload")
    assert exc.value.reason == "GIT_TRUST_BOUND_DIGEST_MISMATCH"


def test_run_index_info_verifies_bound_before_launch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tamper bound executable before index-info → typed StopRequired."""
    pin_git_trust(monkeypatch, tmp_path / "state")
    init_git_repo(tmp_path)
    git = TypedGit(tmp_path)
    Path(git.git_bin).write_bytes(b"tampered-bound-git-exec")
    with pytest.raises(StopRequired) as exc:
        git._run_index_info("100644 " + ("0" * 40) + " 1\tapp/x.py\n")
    assert exc.value.reason == "GIT_TRUST_BOUND_DIGEST_MISMATCH"


def test_execute_trusted_git_is_the_exported_primitive() -> None:
    """Primitive is importable and named for inventory pinning."""
    assert callable(_execute_trusted_git)
    assert _execute_trusted_git.__name__ == _GIT_EXECUTION_PRIMITIVE


def test_go_capability_remains_false() -> None:
    """This corrective iteration must not raise GO_CAPABILITY."""
    manifest = json.loads((PACKAGE_ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest.get("go_capability") is False
