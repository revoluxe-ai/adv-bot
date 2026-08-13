from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# Pin host Git digest for tests — unbound mode is forbidden in production.
os.environ.pop("OPSX_CONFLICT_GIT_TRUST_UNBOUND", None)
_git_executable = shutil.which("git")
if _git_executable:
    os.environ["OPSX_CONFLICT_GIT_TRUST_DIGEST"] = hashlib.sha256(
        Path(_git_executable).read_bytes()
    ).hexdigest()
sys.dont_write_bytecode = True
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PACKAGE_ROOT / "runtime"
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))


def run(argv, cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(argv),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"command failed: {argv}\nstdout={result.stdout}\nstderr={result.stderr}"
        )
    return result


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    run(["git", "init", "-b", "main"], repo)
    run(["git", "config", "user.email", "review@example.invalid"], repo)
    run(["git", "config", "user.name", "OPSX Review Fixture"], repo)
    return repo


@pytest.fixture
def isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    state = tmp_path / "state"
    state.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("XDG_STATE_HOME", str(state))
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(state))
    try:
        if os.name != "nt":
            os.chmod(state, 0o700)
        else:
            user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
            if user:
                subprocess.run(
                    ["icacls", str(state), "/inheritance:r", f"/grant:r", f"{user}:(OI)(CI)F"],
                    capture_output=True,
                    check=False,
                )
    except OSError:
        pass
    return state


@pytest.fixture(autouse=True)
def _reset_process_supervisor() -> None:
    """Isolate global supervisor across tests (cancel barrier must not leak)."""
    from opsx_conflict.cancellation import reset_supervisor_for_tests

    reset_supervisor_for_tests()
    yield
    reset_supervisor_for_tests()
