"""Trusted resolver entry — stdlib-only until HEAD runtime is materialized.

Исполняет opsx_conflict из committed HEAD revision, не из conflicted worktree.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RUNTIME_PREFIX = ".cursor/opsx-resolve-conflict/runtime"
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
        check=True,
    )
    return result.stdout.strip()


def _fail_closed(reason: str) -> int:
    payload = {
        "STATUS": "FAILED",
        "STAGE": "FAILED",
        "STOP_REASON": reason,
        "GO_CAPABILITY": False,
        "GIT_CONTINUE": "FORBIDDEN",
    }
    if "--json" in sys.argv:
        print(json.dumps(payload, ensure_ascii=True))
    else:
        print("STATUS: FAILED")
        print(f"STOP_REASON: {reason}")
    return 2


def materialize_trusted_runtime(repo_root: Path, revision: str) -> tuple[Path, str]:
    """Extract HEAD runtime tree into revision-bound cache."""

    listing = _git(
        repo_root,
        "ls-tree",
        "-r",
        "--name-only",
        "HEAD",
        RUNTIME_PREFIX,
    )
    rel_paths = [p.strip() for p in listing.splitlines() if p.strip()]
    if not rel_paths:
        raise RuntimeError("EXECUTION_CAPABILITY_OR_COMPATIBILITY_MISSING")

    cache_root = (
        Path.home()
        / ".opsx"
        / "resolve-conflict"
        / "trusted-runtime"
        / revision[:16]
    )
    marker = cache_root / ".trusted_revision"
    if marker.is_file() and marker.read_text(encoding="utf-8").strip() == revision:
        runtime_dir = cache_root / "runtime"
        if (runtime_dir / "opsx_conflict").is_dir():
            return runtime_dir, revision

    runtime_dir = cache_root / "runtime"
    if runtime_dir.exists():
        for child in runtime_dir.rglob("*"):
            if child.is_file():
                child.unlink()
    runtime_dir.mkdir(parents=True, exist_ok=True)

    prefix_len = len(RUNTIME_PREFIX) + 1
    for rel in rel_paths:
        if rel == RUNTIME_PREFIX or not rel.startswith(RUNTIME_PREFIX + "/"):
            continue
        sub = rel[prefix_len:]
        out = runtime_dir / sub
        out.parent.mkdir(parents=True, exist_ok=True)
        blob = subprocess.run(
            ["git", "show", f"HEAD:{rel}"],
            cwd=repo_root,
            capture_output=True,
            check=False,
        )
        if blob.returncode != 0:
            continue
        out.write_bytes(blob.stdout)

    if not (runtime_dir / "opsx_conflict").is_dir():
        raise RuntimeError("EXECUTION_CAPABILITY_OR_COMPATIBILITY_MISSING")

    marker.write_text(revision, encoding="utf-8")
    provenance = cache_root / "provenance.json"
    provenance.write_text(
        json.dumps(
            {
                "runtime_source_revision": revision,
                "source": "HEAD",
            },
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return runtime_dir, revision


def main() -> int:
    repo_arg = None
    argv = list(sys.argv[1:])
    if "--repo" in argv:
        idx = argv.index("--repo")
        if idx + 1 < len(argv):
            repo_arg = argv[idx + 1]

    start = Path(repo_arg).resolve() if repo_arg else Path.cwd()
    try:
        repo_root = discover_worktree_root(start)
    except RuntimeError as exc:
        return _fail_closed(str(exc))

    try:
        revision = _git(repo_root, "rev-parse", "HEAD")
        bootstrap_rev = os.environ.get("OPSX_BOOTSTRAP_SOURCE_REVISION", revision)
        if bootstrap_rev != revision:
            return _fail_closed(
                "EXECUTION_CAPABILITY_OR_COMPATIBILITY_MISSING:"
                "bootstrap_runtime_revision_mismatch"
            )
        os.environ["OPSX_BOOTSTRAP_SOURCE_REVISION"] = revision
        runtime_dir, runtime_rev = materialize_trusted_runtime(repo_root, revision)
        if runtime_rev != revision:
            return _fail_closed(
                "EXECUTION_CAPABILITY_OR_COMPATIBILITY_MISSING:"
                "bootstrap_runtime_revision_mismatch"
            )
    except RuntimeError as exc:
        return _fail_closed(str(exc))

    os.environ["OPSX_RESOLVER_RUNTIME_SOURCE_REVISION"] = revision
    os.environ["OPSX_RESOLVER_REPO_ROOT"] = str(repo_root)
    sys.path.insert(0, str(runtime_dir))
    from opsx_conflict.__main__ import main as cli_main

    return cli_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
