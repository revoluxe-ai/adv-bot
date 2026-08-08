from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import run
from opsx_conflict.runtime import _empty_hooks_dir, _run_process


def test_explicit_empty_hooks_path_blocks_repository_hook(
    git_repo: Path, isolated_state: Path
) -> None:
    (git_repo / "x.txt").write_text("x\n", encoding="utf-8")
    run(["git", "add", "x.txt"], git_repo)
    run(["git", "commit", "-m", "base"], git_repo)

    hooks = git_repo / ".git" / "hooks"
    hooks.mkdir(exist_ok=True)
    marker = git_repo / "HOOK_RAN"
    hook = hooks / "pre-commit"
    hook.write_text(f"#!/bin/sh\necho bad > '{marker}'\n", encoding="utf-8")
    hook.chmod(0o755)

    env = dict(os.environ)
    env["XDG_STATE_HOME"] = str(isolated_state)
    result = subprocess.run(
        ["git", "-c", f"core.hooksPath={_empty_hooks_dir()}", "commit", "--allow-empty", "-m", "no hook"],
        cwd=git_repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert not marker.exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX process-group replay")
def test_timeout_kills_process_group(tmp_path: Path) -> None:
    marker = tmp_path / "child-survived"
    script = (
        "import os,subprocess,sys,time;"
        f"subprocess.Popen([sys.executable,'-c',\"import time,pathlib;time.sleep(2);pathlib.Path(r'{marker}').write_text('bad')\"]);"
        "time.sleep(20)"
    )
    with pytest.raises(Exception):
        _run_process([sys.executable, "-c", script], cwd=tmp_path, timeout=0.2)
    import time
    time.sleep(2.5)
    assert not marker.exists()
