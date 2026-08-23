"""Path-level CAS identities для resume safety."""

from __future__ import annotations

import hashlib
from pathlib import Path

from opsx_conflict.execution_state import ExecutionRunState


def path_identity(repo_root: Path, path: str) -> str:
    """Identity path state: content hash, ABSENT, or DELETED marker."""

    target = repo_root / path
    if target.is_file():
        return hashlib.sha256(target.read_bytes()).hexdigest()
    if target.exists():
        return hashlib.sha256(target.read_bytes()).hexdigest()
    return "ABSENT"


def capture_pre_write_identities(
    repo_root: Path,
    paths: list[str],
) -> dict[str, str]:
    return {p: path_identity(repo_root, p) for p in paths}


def verify_resume_cas(
    repo_root: Path,
    exec_state: ExecutionRunState,
    planned_paths: list[str],
) -> tuple[bool, str | None]:
    """CAS pre/post check перед resume writes."""

    for path in exec_state.completed_paths:
        expected = exec_state.path_post_write.get(path)
        if expected is None:
            return False, f"resume_cas_missing_post_write:{path}"
        current = path_identity(repo_root, path)
        if current != expected:
            return False, (
                f"resume_cas_completed_drift:{path}:"
                f"expected:{expected}:actual:{current}"
            )

    for path in planned_paths:
        if path in exec_state.completed_paths:
            continue
        expected_pre = exec_state.path_pre_write.get(path)
        if expected_pre is None:
            return False, f"resume_cas_missing_pre_write:{path}"
        current = path_identity(repo_root, path)
        if current != expected_pre:
            return False, (
                f"resume_cas_pending_drift:{path}:"
                f"expected:{expected_pre}:actual:{current}"
            )

    return True, None
