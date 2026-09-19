"""Thin read-only canonical bootstrap for `/opsx-scripts`.

Bootstrap performs only caller identity and Git topology checks. It never
loads Registry, matches collectors, selects outcomes or runs Jobs. After
selecting exact `refs/heads/scripts`, it executes the resolver from that
absolute worktree using the current Poetry interpreter.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

if __package__ in {None, ""}:
    _repo_root = Path(__file__).resolve().parents[2]
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))

from tools.scripts.resolver import (
    RESULT_SCHEMA,
    ResolverBlocked,
    _absolute_path,
    _git,
    _identity,
    _parse_worktrees,
)


def select_canonical_root(caller_root: Path, explicit_root: str | None) -> Path:
    """Выбрать canonical root без чтения Registry или execution inputs."""
    caller = _identity(caller_root)
    if explicit_root is not None:
        candidates = [_absolute_path(explicit_root, "--canonical-root")]
    else:
        environment_root = os.environ.get("SCRIPTS_CANONICAL_ROOT")
        if environment_root:
            candidates = [_absolute_path(environment_root, "SCRIPTS_CANONICAL_ROOT")]
        else:
            candidates = [
                path
                for path, branch in _parse_worktrees(
                    _git(caller.root, "worktree", "list", "--porcelain")
                )
                if branch == "refs/heads/scripts"
            ]
    valid_candidates: list[Path] = []
    for candidate in candidates:
        try:
            identity = _identity(candidate)
        except ResolverBlocked:
            continue
        if identity.branch != "refs/heads/scripts":
            continue
        if identity.common_dir != caller.common_dir:
            continue
        try:
            dirty = _git(
                identity.root, "status", "--porcelain=v1", "--untracked-files=no"
            )
        except ResolverBlocked:
            continue
        if dirty:
            continue
        if not (identity.root / "tools/scripts/resolver.py").is_file():
            continue
        valid_candidates.append(identity.root)
    if len(valid_candidates) > 1:
        raise ResolverBlocked(
            "ambiguous canonical topology: multiple valid refs/heads/scripts worktrees"
        )
    if valid_candidates:
        return valid_candidates[0]
    raise ResolverBlocked("no clean exact refs/heads/scripts canonical worktree")


def _blocked(mode: str | None, message: str) -> dict[str, object]:
    """Создать machine result при bootstrap failure до resolver startup."""
    return {
        "schema_version": RESULT_SCHEMA,
        "mode": mode,
        "request_id": None,
        "run_id": None,
        "caller": None,
        "outcome": "BLOCKED",
        "execution_sha": None,
        "registry_sha": None,
        "canonical_worktree": None,
        "selection": [],
        "selection_mode": "NONE",
        "compose_plan": None,
        "formal_change": None,
        "error": {"code": "BOOTSTRAP_BLOCKED", "message": message},
        "operational_write_path": False,
    }


def main(argv: list[str] | None = None) -> int:
    """Запустить только canonical resolver из выбранного worktree."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("PLAN_RUN", "RUN"))
    parser.add_argument("--request-file", required=True)
    parser.add_argument("--caller-root", required=True)
    parser.add_argument("--canonical-root")
    args = parser.parse_args(argv)
    try:
        request_file = _absolute_path(args.request_file, "--request-file")
        caller_root = _absolute_path(args.caller_root, "--caller-root")
        canonical_root = select_canonical_root(caller_root, args.canonical_root)
        resolver_path = canonical_root / "tools/scripts/resolver.py"
        completed = subprocess.run(
            [
                sys.executable,
                str(resolver_path),
                args.mode,
                "--request-file",
                str(request_file),
                "--caller-root",
                str(caller_root),
                "--canonical-root",
                str(canonical_root),
            ],
            cwd=canonical_root,
            check=False,
        )
        return completed.returncode
    except (ResolverBlocked, ValueError, OSError) as exc:
        print(json.dumps(_blocked(args.mode, str(exc)), separators=(",", ":")))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
