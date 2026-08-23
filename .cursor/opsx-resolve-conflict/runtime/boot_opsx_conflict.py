"""Boot helper: delegate to stdlib launcher (never execute conflicted worktree bytes)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / ".git").is_dir():
            return candidate
    return start


def main() -> int:
    repo_root = _find_repo_root(Path.cwd())
    launcher = repo_root / ".cursor" / "opsx_resolve_conflict_launcher.py"
    if launcher.is_file():
        return subprocess.call(
            [sys.executable, str(launcher), *sys.argv[1:]],
            cwd=repo_root,
        )

    tools_boot = repo_root / ".opsx" / "tools" / "trusted_resolver_boot.py"
    if tools_boot.is_file():
        return subprocess.call(
            [sys.executable, str(tools_boot), *sys.argv[1:]],
            cwd=repo_root,
        )

    runtime = Path(__file__).resolve().parent
    if str(runtime) not in sys.path:
        sys.path.insert(0, str(runtime))
    from opsx_conflict.__main__ import main as cli_main

    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
