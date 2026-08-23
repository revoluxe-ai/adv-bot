"""Stdlib-only launcher — materializes trusted bootstrap from Git HEAD.

Ни один byte conflicted worktree не нужен для запуска resolver.
Entry path вне `.opsx/tools` и `.cursor/opsx-resolve-conflict/`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

BOOTSTRAP_REL = ".opsx/tools/trusted_resolver_boot.py"


def _is_git_marker(candidate: Path) -> bool:
    git_marker = candidate / ".git"
    return git_marker.is_dir() or git_marker.is_file()


def discover_worktree_root(start: Path) -> Path:
    """Worktree root via git plumbing; stops at linked-worktree `.git` file."""

    resolved_start = start.resolve()
    for candidate in [resolved_start, *resolved_start.parents]:
        if not _is_git_marker(candidate):
            continue
        result = subprocess.run(
            ["git", "-C", str(candidate), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode != 0 or not (result.stdout or "").strip():
            raise RuntimeError(
                f"REPO_ROOT_DISCOVERY_FAILED:git_top_level:{candidate}"
            )
        top = Path((result.stdout or "").strip()).resolve()
        if not top.is_dir():
            raise RuntimeError(
                f"REPO_ROOT_DISCOVERY_FAILED:invalid_top_level:{top}"
            )
        return top
    raise RuntimeError("REPO_ROOT_DISCOVERY_FAILED:not_in_git_worktree")


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "").strip())
    return (result.stdout or "").strip()


def _fail_closed(reason: str, as_json: bool) -> int:
    payload = {
        "STATUS": "FAILED",
        "STAGE": "FAILED",
        "STOP_REASON": reason,
        "GO_CAPABILITY": False,
        "GIT_CONTINUE": "FORBIDDEN",
    }
    if as_json:
        print(json.dumps(payload, ensure_ascii=True))
    else:
        print("STATUS: FAILED")
        print(f"STOP_REASON: {reason}")
    return 2


def materialize_trusted_bootstrap(repo_root: Path, revision: str) -> Path:
    """Extract committed bootstrap script into revision-bound cache."""

    cache_root = (
        Path.home()
        / ".opsx"
        / "resolve-conflict"
        / "trusted-bootstrap"
        / revision[:16]
    )
    boot_path = cache_root / "trusted_resolver_boot.py"
    marker = cache_root / ".trusted_revision"
    if (
        marker.is_file()
        and marker.read_text(encoding="utf-8").strip() == revision
        and boot_path.is_file()
    ):
        return boot_path

    blob = subprocess.run(
        ["git", "show", f"HEAD:{BOOTSTRAP_REL}"],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if blob.returncode != 0 or not blob.stdout:
        raise RuntimeError("EXECUTION_CAPABILITY_OR_COMPATIBILITY_MISSING")

    cache_root.mkdir(parents=True, exist_ok=True)
    boot_path.write_bytes(blob.stdout)
    marker.write_text(revision, encoding="utf-8")
    provenance = cache_root / "provenance.json"
    provenance.write_text(
        json.dumps(
            {
                "bootstrap_source_revision": revision,
                "bootstrap_rel": BOOTSTRAP_REL,
                "source": "HEAD",
            },
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return boot_path


def main() -> int:
    argv = list(sys.argv[1:])
    as_json = "--json" in argv

    repo_arg: str | None = None
    if "--repo" in argv:
        idx = argv.index("--repo")
        if idx + 1 < len(argv):
            repo_arg = argv[idx + 1]

    start = Path(repo_arg).resolve() if repo_arg else Path.cwd()
    try:
        repo_root = discover_worktree_root(start)
    except RuntimeError as exc:
        return _fail_closed(str(exc), as_json)

    try:
        revision = _git(repo_root, "rev-parse", "HEAD")
        boot_path = materialize_trusted_bootstrap(repo_root, revision)
    except RuntimeError as exc:
        return _fail_closed(str(exc), as_json)

    os.environ["OPSX_BOOTSTRAP_SOURCE_REVISION"] = revision
    os.environ["OPSX_RESOLVER_REPO_ROOT"] = str(repo_root)
    return subprocess.call(
        [sys.executable, str(boot_path), *argv],
        cwd=repo_root,
    )


if __name__ == "__main__":
    raise SystemExit(main())
