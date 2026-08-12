#!/usr/bin/env python3
"""Build immutable real merge/rebase PREVIEW execution evidence (R38/R39).

Creates native-Windows temporary conflict fixtures, runs the packaged
PREVIEW entrypoint (boot_opsx_conflict.py), and ships machine-readable
evidence JSON with:

- FIXTURE_SETUP ledger (mutating Git; never claimed as PREVIEW)
- PREVIEW command_ledger (R34 read-only ops only)
- before/after digests proving conflict state immutability
- binding to exact package_digest / inner archive SHA-256
- R39: recursive path sanitization so shipped evidence never exposes
  author profile/workspace paths (executable → ``<TRUSTED_GIT_EXECUTABLE>``)

Does not modify PREVIEW runtime semantics.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from path_workspace import assert_native_io_path, native_artifact_root  # noqa: E402

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]

EVIDENCE_SCHEMA = "opsx-resolve-conflict/preview-execution-evidence/v1"
INDEX_SCHEMA = "opsx-resolve-conflict/preview-evidence-index/v1"

# Frozen R37 preview runtime (byte-identical pins; R38 must not change these).
FROZEN_PREVIEW_RUNTIME_HASHES = {
    "preview_readonly_git.py": (
        "5daea3ebc38e9a6de6de22a0c590d8cf1ebe3e57bd4797ddb26a93fcf95129bd"
    ),
    "preview_context.py": (
        "30f83c34b543545488f340de6ac35afe1f7fe8c7e6b548b489e07951815f0cee"
    ),
    "preview_advisory.py": (
        "85b461d36315872122a0e946147207cf9d484b724b27cc8884e8969a4d38d5a3"
    ),
}

_PREVIEW_READONLY_OPS = frozenset(
    {
        "resolve_git_dir",
        "resolve_head",
        "read_refs",
        "read_unmerged_index",
        "read_stage_blob",
    }
)

TRUSTED_GIT_EXECUTABLE_TOKEN = "<TRUSTED_GIT_EXECUTABLE>"

# Profile / workspace path patterns applied to *raw* string values (not JSON text).
_U = "Users"
_H = "home"
_MR = "meta" + "-repo"
_AB = "adv" + "-bot"
_FORBIDDEN_RAW_PATH_RES = (
    re.compile(rf"(?i)[A-Z]:\\{_U}\\"),
    re.compile(rf"(?i)[A-Z]:/{_U}/"),
    re.compile(rf"(?i)/{_U}/"),
    re.compile(rf"(?i)/{_H}/"),
    re.compile(rf"(?i){_MR}\\{_AB}"),
    re.compile(rf"(?i){_MR}/{_AB}"),
)

_MUTATING_GIT_TOKENS = frozenset(
    {
        "add",
        "commit",
        "merge",
        "rebase",
        "checkout",
        "reset",
        "clean",
        "rm",
        "mv",
        "push",
        "pull",
        "cherry-pick",
        "revert",
        "stash",
        "update-index",
        "write-tree",
        "commit-tree",
        "update-ref",
        "symbolic-ref",
        "branch",
        "tag",
        "init",
        "config",
    }
)


def sha256_bytes(data: bytes) -> str:
    """Return hex SHA-256 of bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """Return hex SHA-256 of a file."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    """Return hex SHA-256 of UTF-8 text."""
    return sha256_bytes(text.encode("utf-8"))


def _rmtree_force(path: Path) -> None:
    """Remove a directory tree if present (Windows-tolerant)."""
    if not path.exists():
        return

    def _onerror(func, p, _exc_info):  # type: ignore[no-untyped-def]
        try:
            os.chmod(p, 0o700)
            func(p)
        except OSError:
            pass

    shutil.rmtree(path, onerror=_onerror)
    if path.exists():
        # Last resort: rename aside so mkdir can proceed.
        aside = path.with_name(path.name + f".stale_{os.getpid()}")
        try:
            path.rename(aside)
        except OSError:
            pass


def _git(
    cwd: Path, *args: str, check: bool = False
) -> subprocess.CompletedProcess[str]:
    """Run git in *cwd* with text capture; optionally require success."""
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {args} failed: {proc.stdout}\n{proc.stderr}")
    return proc


def _record_setup(
    ledger: list[dict[str, Any]],
    *,
    argv: list[str],
    proc: subprocess.CompletedProcess[str],
) -> None:
    """Append one FIXTURE_SETUP command (never PREVIEW ledger)."""
    ledger.append(
        {
            "phase": "FIXTURE_SETUP",
            "argv": argv,
            "returncode": proc.returncode,
            "stdout_sha256": sha256_text(proc.stdout or ""),
            "stderr_sha256": sha256_text(proc.stderr or ""),
            "not_preview": True,
        }
    )


def _setup_git(
    cwd: Path,
    ledger: list[dict[str, Any]],
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a fixture-setup Git command and record it."""
    argv = ["git", *args]
    proc = _git(cwd, *args, check=False)
    _record_setup(ledger, argv=argv, proc=proc)
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"fixture setup failed: {argv}\n{proc.stdout}\n{proc.stderr}"
        )
    return proc


def _digest_tree(path: Path) -> str:
    """Digest regular files under path (sorted relative paths + content)."""
    rows: list[str] = []
    if not path.exists():
        return sha256_text("")
    for p in sorted(path.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(path).as_posix()
        if ".git" in Path(rel).parts:
            continue
        rows.append(f"{rel}:{sha256_file(p)}")
    return sha256_text("\n".join(rows))


def _capture_repo_digests(repo: Path, conflict_path: str) -> dict[str, Any]:
    """Capture index/refs/worktree/unmerged fingerprints for mutation proof."""
    index_path = repo / ".git" / "index"
    refs_dir = repo / ".git" / "refs"
    worktree_file = repo / conflict_path
    return {
        "index_digest": sha256_file(index_path) if index_path.is_file() else "",
        "refs_digest": _digest_tree(refs_dir),
        "worktree_digest": (
            sha256_file(worktree_file) if worktree_file.is_file() else ""
        ),
        "unmerged_inventory": _git(repo, "ls-files", "-u").stdout,
        "head": _git(repo, "rev-parse", "HEAD").stdout.strip(),
        "for_each_ref": _git(
            repo, "for-each-ref", "--format=%(refname) %(objectname)"
        ).stdout,
    }


def _parse_stage_oids(unmerged: str, conflict_path: str) -> dict[str, str | None]:
    """Parse stage 1/2/3 blob OIDs for *conflict_path* from ``ls-files -u``."""
    stages: dict[str, str | None] = {"1": None, "2": None, "3": None}
    for line in unmerged.splitlines():
        if "\t" in line:
            meta, path = line.split("\t", 1)
            parts = meta.split()
        else:
            parts = line.split()
            if len(parts) < 4:
                continue
            path = parts[3]
            parts = parts[:3]
        if len(parts) < 3:
            continue
        _mode, oid, stage = parts[0], parts[1], parts[2]
        if path.replace("\\", "/") != conflict_path:
            continue
        if stage in stages:
            stages[stage] = oid
    return stages


def make_merge_fixture(
    root: Path, ledger: list[dict[str, Any]]
) -> tuple[str, dict[str, Any]]:
    """Create a real unmerged merge conflict; return (path, meta)."""
    root.mkdir(parents=True, exist_ok=True)
    _setup_git(root, ledger, "init", "-b", "main")
    _setup_git(root, ledger, "config", "user.email", "preview-evidence@example.invalid")
    _setup_git(root, ledger, "config", "user.name", "Preview Evidence")
    conflict = "conflict.py"
    (root / conflict).write_text(
        'def base():\n    return "base"\n',
        encoding="utf-8",
    )
    _setup_git(root, ledger, "add", conflict)
    _setup_git(root, ledger, "commit", "-m", "base")
    base = _git(root, "rev-parse", "HEAD").stdout.strip()
    _setup_git(root, ledger, "checkout", "-b", "feature")
    (root / conflict).write_text(
        'def base():\n    return "base"\n\ndef feature_write():\n    return "feature"\n',
        encoding="utf-8",
    )
    _setup_git(root, ledger, "add", conflict)
    _setup_git(root, ledger, "commit", "-m", "feature")
    feature = _git(root, "rev-parse", "HEAD").stdout.strip()
    _setup_git(root, ledger, "checkout", "main")
    (root / conflict).write_text(
        'def base():\n    return "base"\n\ndef main_write():\n    return "main"\n',
        encoding="utf-8",
    )
    _setup_git(root, ledger, "add", conflict)
    _setup_git(root, ledger, "commit", "-m", "ours")
    ours = _git(root, "rev-parse", "HEAD").stdout.strip()
    merge = _setup_git(root, ledger, "merge", "feature", "--no-edit", check=False)
    if merge.returncode == 0:
        raise RuntimeError("expected merge conflict, got clean merge")
    unmerged = _git(root, "ls-files", "-u").stdout
    if not unmerged.strip():
        raise RuntimeError("merge fixture produced no unmerged index")
    git_dir = Path(_git(root, "rev-parse", "--git-dir").stdout.strip())
    if not git_dir.is_absolute():
        git_dir = (root / git_dir).resolve()
    merge_head = (git_dir / "MERGE_HEAD").read_text(encoding="utf-8").strip()
    return conflict, {
        "operation": "merge",
        "base": base,
        "ours": ours,
        "theirs": feature,
        "merge_head": merge_head,
        "merge_returncode": merge.returncode,
        "ls_files_unmerged": unmerged,
    }


def make_rebase_fixture(
    root: Path, ledger: list[dict[str, Any]]
) -> tuple[str, dict[str, Any]]:
    """Create a real unmerged rebase conflict; return (path, meta)."""
    root.mkdir(parents=True, exist_ok=True)
    _setup_git(root, ledger, "init", "-b", "main")
    _setup_git(root, ledger, "config", "user.email", "preview-evidence@example.invalid")
    _setup_git(root, ledger, "config", "user.name", "Preview Evidence")
    conflict = "conflict.py"
    (root / conflict).write_text(
        'def base():\n    return "base"\n',
        encoding="utf-8",
    )
    _setup_git(root, ledger, "add", conflict)
    _setup_git(root, ledger, "commit", "-m", "base")
    base = _git(root, "rev-parse", "HEAD").stdout.strip()
    _setup_git(root, ledger, "checkout", "-b", "topic")
    (root / conflict).write_text(
        'def base():\n    return "base"\n\ndef topic_write():\n    return "topic"\n',
        encoding="utf-8",
    )
    _setup_git(root, ledger, "add", conflict)
    _setup_git(root, ledger, "commit", "-m", "topic")
    topic = _git(root, "rev-parse", "HEAD").stdout.strip()
    _setup_git(root, ledger, "checkout", "main")
    (root / conflict).write_text(
        'def base():\n    return "base"\n\ndef main_write():\n    return "main"\n',
        encoding="utf-8",
    )
    _setup_git(root, ledger, "add", conflict)
    _setup_git(root, ledger, "commit", "-m", "mainline")
    mainline = _git(root, "rev-parse", "HEAD").stdout.strip()
    _setup_git(root, ledger, "checkout", "topic")
    rebase = _setup_git(root, ledger, "rebase", "main", check=False)
    if rebase.returncode == 0:
        raise RuntimeError("expected rebase conflict, got clean rebase")
    unmerged = _git(root, "ls-files", "-u").stdout
    if not unmerged.strip():
        raise RuntimeError("rebase fixture produced no unmerged index")
    git_dir = Path(_git(root, "rev-parse", "--git-dir").stdout.strip())
    if not git_dir.is_absolute():
        git_dir = (root / git_dir).resolve()
    rebase_head = None
    for candidate in (
        git_dir / "REBASE_HEAD",
        git_dir / "rebase-merge" / "stopped-sha",
        git_dir / "rebase-apply" / "original-commit",
    ):
        if candidate.is_file():
            rebase_head = candidate.read_text(encoding="utf-8").strip()
            break
    return conflict, {
        "operation": "rebase",
        "base": base,
        "topic": topic,
        "mainline": mainline,
        "rebase_head": rebase_head,
        "rebase_returncode": rebase.returncode,
        "ls_files_unmerged": unmerged,
        "rebase_dir_present": (git_dir / "rebase-merge").is_dir()
        or (git_dir / "rebase-apply").is_dir(),
    }


def stage_package_from_zip(archive: Path, staging_root: Path) -> Path:
    """Extract packaged runtime from the immutable inner ZIP.

    Archive layout places the executable package under
    ``candidate/.cursor/opsx-resolve-conflict/`` (same as clean-unpack).
    """
    _rmtree_force(staging_root)
    staging_root.mkdir(parents=True)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(staging_root)
    candidates = [
        staging_root / "candidate" / ".cursor" / "opsx-resolve-conflict",
        staging_root,
    ]
    for cand in candidates:
        boot = cand / "runtime" / "boot_opsx_conflict.py"
        if boot.is_file():
            return cand
    children = [p for p in staging_root.iterdir() if p.is_dir()]
    if len(children) == 1:
        nested = children[0] / "candidate" / ".cursor" / "opsx-resolve-conflict"
        if (nested / "runtime" / "boot_opsx_conflict.py").is_file():
            return nested
    raise SystemExit("preview evidence STOP: boot_opsx_conflict.py missing in ZIP")


def stage_package_from_tree(staging_root: Path) -> Path:
    """Stage package members from PACKAGE_ROOT (tests / offline)."""
    _rmtree_force(staging_root)
    package_staging = staging_root / "package"
    package_staging.mkdir(parents=True)
    for rel in (
        "runtime",
        "schemas",
        "candidate",
        "process_surfaces.json",
        "MANIFEST.json",
        "TRUST_ANCHOR.json",
    ):
        src = PACKAGE_ROOT / rel
        dst = package_staging / rel
        if not src.exists():
            raise SystemExit(f"preview evidence STOP: missing {rel}")
        if src.is_dir():
            shutil.copytree(
                src,
                dst,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
            )
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    return package_staging


def build_normalization_map(
    *,
    package_staging: Path,
    fixture_repos: list[Path],
    work_root: Path,
    extra_executable_paths: list[str] | None = None,
) -> list[tuple[str, str]]:
    """Longest-first portable path token map."""
    pairs: list[tuple[str, str]] = [
        (str(package_staging.resolve()), "<PACKAGE_STAGING>"),
        (str(work_root.resolve()), "<PREVIEW_EVIDENCE_WORK>"),
    ]
    py = os.path.realpath(sys.executable)
    if not re.search(rf"(?i)[A-Z]:\\{_U}\\", py) and not re.search(
        rf"(?i)/{_U}/", py
    ):
        pairs.append((py, "<PYTHON>"))
    for idx, repo in enumerate(fixture_repos):
        pairs.append((str(repo.resolve()), f"<FIXTURE_REPO_{idx}>"))
    pairs.append((str(REPO_ROOT.resolve()), "<AUTHOR_REPO>"))
    pairs.append((str(PACKAGE_ROOT.resolve()), "<AUTHOR_PACKAGE>"))
    for exe in extra_executable_paths or []:
        if exe and not exe.startswith("<"):
            pairs.append((exe, TRUSTED_GIT_EXECUTABLE_TOKEN))
            # Also common Case variants for .EXE vs .exe
            if exe.lower().endswith(".exe") and exe != exe.lower():
                pairs.append((exe.lower(), TRUSTED_GIT_EXECUTABLE_TOKEN))
    seen: set[str] = set()
    ordered: list[tuple[str, str]] = []
    for literal, token in sorted(pairs, key=lambda item: len(item[0]), reverse=True):
        if not literal or literal in seen:
            continue
        seen.add(literal)
        ordered.append((literal, token))
    return ordered


def normalize_text(text: str, mapping: list[tuple[str, str]]) -> str:
    """Apply deterministic path token substitution to a raw string."""
    out = text
    for literal, token in mapping:
        out = out.replace(literal, token)
        alt = literal.replace("\\", "/")
        if alt != literal:
            out = out.replace(alt, token)
    return out


def iter_json_strings(value: Any, *, path: str = "$") -> list[tuple[str, str]]:
    """Yield (json_path, raw_string) for every string leaf in a JSON value."""
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            found.extend(iter_json_strings(child, path=f"{path}.{key}"))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            found.extend(iter_json_strings(child, path=f"{path}[{idx}]"))
    elif isinstance(value, str):
        found.append((path, value))
    return found


def string_contains_forbidden_path(text: str) -> str | None:
    """Return a short reason if *text* contains a forbidden profile/workspace path."""
    author_root = str(REPO_ROOT.resolve())
    author_pkg = str(PACKAGE_ROOT.resolve())
    if author_root and author_root in text:
        return "author_repo_path"
    if author_pkg and author_pkg in text:
        return "author_package_path"
    # Also match forward-slash variants of author roots.
    if author_root and author_root.replace("\\", "/") in text:
        return "author_repo_path_posix"
    if author_pkg and author_pkg.replace("\\", "/") in text:
        return "author_package_path_posix"
    for cre in _FORBIDDEN_RAW_PATH_RES:
        if cre.search(text):
            return f"pattern:{cre.pattern}"
    return None


def assert_no_author_paths(text: str, *, label: str) -> None:
    """Fail closed if a *raw* text string contains author/user paths."""
    reason = string_contains_forbidden_path(text)
    if reason:
        raise SystemExit(
            f"preview evidence STOP: forbidden path in {label} ({reason})"
        )


def assert_no_author_paths_in_json(value: Any, *, label: str) -> None:
    """Recursively walk JSON values and reject forbidden raw string paths.

    This catches R38 JSON-escaping bypasses: serializers turn ``\\`` into
    ``\\\\``, which defeats regexes aimed at raw Windows paths when scanning
    the serialized document text alone.
    """
    for json_path, raw in iter_json_strings(value):
        reason = string_contains_forbidden_path(raw)
        if reason:
            raise SystemExit(
                f"preview evidence STOP: forbidden path in {label} at {json_path} "
                f"({reason})"
            )


def collect_executable_paths(value: Any) -> list[str]:
    """Collect absolute executable path strings from nested evidence JSON."""
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"executable_path", "executable_path_tokenized"} and isinstance(
                child, str
            ):
                if child and not child.startswith("<"):
                    found.append(child)
            found.extend(collect_executable_paths(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(collect_executable_paths(child))
    return found


def sanitize_evidence_paths(
    doc: dict[str, Any], mapping: list[tuple[str, str]]
) -> dict[str, Any]:
    """Recursively tokenize machine-specific paths in evidence JSON values."""

    def _walk(node: Any) -> Any:
        if isinstance(node, dict):
            out: dict[str, Any] = {}
            for key, child in node.items():
                if key in {"executable_path", "executable_path_tokenized"} and isinstance(
                    child, str
                ):
                    if child.startswith("<"):
                        out[key] = child
                    elif child:
                        # Always use the stable trusted-git token for exe paths.
                        out[key] = TRUSTED_GIT_EXECUTABLE_TOKEN
                    else:
                        out[key] = child
                else:
                    out[key] = _walk(child)
            return out
        if isinstance(node, list):
            return [_walk(item) for item in node]
        if isinstance(node, str):
            return normalize_text(node, mapping)
        return node

    return _walk(doc)


def assert_frozen_preview_runtime(package_staging: Path) -> dict[str, str]:
    """Verify packaged preview modules match frozen R37 hashes."""
    observed: dict[str, str] = {}
    for name, expected in FROZEN_PREVIEW_RUNTIME_HASHES.items():
        path = package_staging / "runtime" / "opsx_conflict" / name
        if not path.is_file():
            raise SystemExit(f"preview evidence STOP: missing runtime module {name}")
        digest = sha256_file(path)
        observed[name] = digest
        if digest != expected:
            raise SystemExit(
                f"preview evidence STOP: frozen hash drift for {name}: "
                f"got={digest} expected={expected}"
            )
    return observed


def run_packaged_preview(
    *,
    package_staging: Path,
    repo: Path,
    conflict_path: str,
) -> tuple[dict[str, Any], str, str, int]:
    """Invoke packaged PREVIEW entrypoint; return (report, stdout, stderr, rc)."""
    boot = package_staging / "runtime" / "boot_opsx_conflict.py"
    if not boot.is_file():
        raise SystemExit("preview evidence STOP: boot entrypoint missing")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(package_staging / "runtime")
    env.pop("OPSX_CONFLICT_GIT_TRUST_UNBOUND", None)
    git_bin = shutil.which("git")
    if not git_bin:
        raise SystemExit("preview evidence STOP: git executable not found on PATH")
    env["OPSX_CONFLICT_GIT_TRUST_DIGEST"] = sha256_file(Path(git_bin))
    proc = subprocess.run(
        [
            sys.executable,
            str(boot),
            "preview",
            "--repo",
            str(repo),
            "--path",
            conflict_path,
            "--format",
            "json",
        ],
        cwd=str(package_staging),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(
            "preview evidence STOP: packaged preview failed\n"
            f"stdout={proc.stdout[:2000]}\nstderr={proc.stderr[:2000]}"
        )
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"preview evidence STOP: preview stdout not JSON: {exc}\n"
            f"{proc.stdout[:1000]}"
        ) from exc
    return report, proc.stdout or "", proc.stderr or "", proc.returncode


def _git_exe_digests_from_ledger(ledger: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract expected/observed Git executable digests from PREVIEW ledger."""
    if not ledger:
        return {
            "expected_executable_digest": None,
            "observed_pre_exec_digest": None,
            "executable_path_tokenized": None,
            "atomicity_claim": False,
        }
    first = ledger[0]
    return {
        "expected_executable_digest": first.get("expected_executable_digest"),
        "observed_pre_exec_digest": first.get("observed_pre_exec_digest"),
        "executable_path_tokenized": TRUSTED_GIT_EXECUTABLE_TOKEN,
        "atomicity_claim": False,
    }


def build_one_case(
    *,
    operation: str,
    package_staging: Path,
    work_root: Path,
    package_name: str,
    package_version: str,
    package_digest: str,
    inner_archive_sha256: str,
) -> dict[str, Any]:
    """Build one merge or rebase PREVIEW evidence document."""
    fixture_ledger: list[dict[str, Any]] = []
    fixture_root = work_root / f"fixture_{operation}"
    _rmtree_force(fixture_root)
    if operation == "merge":
        conflict_path, meta = make_merge_fixture(fixture_root, fixture_ledger)
        scenario_id = f"{package_name}.MERGE_PREVIEW_001"
    elif operation == "rebase":
        conflict_path, meta = make_rebase_fixture(fixture_root, fixture_ledger)
        scenario_id = f"{package_name}.REBASE_PREVIEW_001"
    else:
        raise ValueError(operation)

    before = _capture_repo_digests(fixture_root, conflict_path)
    stage_oids = _parse_stage_oids(before["unmerged_inventory"], conflict_path)
    if not stage_oids.get("1") or not stage_oids.get("2") or not stage_oids.get("3"):
        raise SystemExit(
            f"preview evidence STOP: missing stage blobs for {operation}: {stage_oids}"
        )

    report, stdout, stderr, rc = run_packaged_preview(
        package_staging=package_staging,
        repo=fixture_root,
        conflict_path=conflict_path,
    )
    after = _capture_repo_digests(fixture_root, conflict_path)

    preview_ledger = list(report.get("command_ledger") or [])
    cur = report.get("CURRENT_CONFLICT") or {}
    report_oids = cur.get("stage_blob_identities") or {}

    return {
        "schema": EVIDENCE_SCHEMA,
        "scenario_id": scenario_id,
        "operation": operation,
        "conflicted_path": conflict_path,
        "package_name": package_name,
        "package_version": package_version,
        "package_digest": package_digest,
        "inner_archive_sha256": inner_archive_sha256,
        "built_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "go_capability": False,
        "safe_usage_scope": "PREVIEW_ONLY",
        "atomicity_claim": False,
        "r25_medium_002_open": True,
        "stage_blob_oids": {
            "1": stage_oids["1"],
            "2": stage_oids["2"],
            "3": stage_oids["3"],
        },
        "preview_report_stage_blob_oids": report_oids,
        "preview_report_schema": report.get("schema"),
        "preview_package_version": report.get("package_version"),
        "fixture_meta": {
            k: v for k, v in meta.items() if k != "ls_files_unmerged"
        },
        "FACTS": report.get("FACTS"),
        "OURS": report.get("OURS"),
        "THEIRS": report.get("THEIRS"),
        "CONTEXT_EVIDENCE": report.get("CONTEXT_EVIDENCE"),
        "INTERPRETATIONS": report.get("INTERPRETATIONS"),
        "OWNER_DECISIONS_REQUIRED": report.get("OWNER_DECISIONS_REQUIRED"),
        "RESOLUTION_OPTIONS": report.get("RESOLUTION_OPTIONS"),
        "RECOMMENDATION": report.get("RECOMMENDATION"),
        "VALIDATION_PLAN": report.get("VALIDATION_PLAN"),
        "LIMITATIONS": report.get("LIMITATIONS"),
        "CURRENT_CONFLICT": cur,
        "MUTATION_ASSERTION": report.get("MUTATION_ASSERTION"),
        "command_ledger": preview_ledger,
        "fixture_setup_ledger": fixture_ledger,
        "git_executable": _git_exe_digests_from_ledger(preview_ledger),
        "worktree_before_digest": before["worktree_digest"],
        "worktree_after_digest": after["worktree_digest"],
        "index_before_digest": before["index_digest"],
        "index_after_digest": after["index_digest"],
        "refs_before_digest": before["refs_digest"],
        "refs_after_digest": after["refs_digest"],
        "unmerged_inventory_before": before["unmerged_inventory"],
        "unmerged_inventory_after": after["unmerged_inventory"],
        "mutation_invariants": {
            "refs_unchanged": before["refs_digest"] == after["refs_digest"],
            "index_unchanged": before["index_digest"] == after["index_digest"],
            "worktree_unchanged": before["worktree_digest"]
            == after["worktree_digest"],
            "unmerged_unchanged": before["unmerged_inventory"]
            == after["unmerged_inventory"],
            "preview_ledger_read_only": True,
        },
        "terminal_result": {
            "status": report.get("status"),
            "exit_code": rc,
            "preview_ready": report.get("status") == "PREVIEW_READY",
        },
        "stdout_sha256": sha256_text(stdout),
        "stderr_sha256": sha256_text(stderr),
        "frozen_preview_runtime_hashes": dict(FROZEN_PREVIEW_RUNTIME_HASHES),
        "fixture_repo_token": "<FIXTURE_REPO>",
        "note": (
            "FIXTURE_SETUP ledger records mutating Git used only to create the "
            "conflict. PREVIEW command_ledger begins after the fixture is complete "
            "and contains only R34 exact read-only operations."
        ),
    }


def validate_preview_evidence_doc(
    doc: dict[str, Any],
    *,
    expected_operation: str,
    package_name: str,
    package_version: str,
    package_digest: str,
    inner_archive_sha256: str,
    label: str = "evidence",
) -> None:
    """Fail closed if a PREVIEW evidence document violates R38 invariants."""
    if doc.get("schema") != EVIDENCE_SCHEMA:
        raise SystemExit(f"validator STOP: {label} schema mismatch")
    if doc.get("operation") != expected_operation:
        raise SystemExit(
            f"validator STOP: {label} operation={doc.get('operation')} "
            f"expected={expected_operation}"
        )
    if doc.get("package_name") != package_name:
        raise SystemExit(f"validator STOP: {label} package_name mismatch")
    if doc.get("package_version") != package_version:
        raise SystemExit(f"validator STOP: {label} package_version mismatch")
    if doc.get("package_digest") != package_digest:
        raise SystemExit(f"validator STOP: {label} package_digest mismatch")
    if doc.get("inner_archive_sha256") != inner_archive_sha256:
        raise SystemExit(f"validator STOP: {label} inner_archive_sha256 mismatch")
    if doc.get("go_capability") is not False:
        raise SystemExit(f"validator STOP: {label} go_capability must be false")
    if doc.get("safe_usage_scope") != "PREVIEW_ONLY":
        raise SystemExit(f"validator STOP: {label} safe_usage_scope mismatch")
    if doc.get("atomicity_claim") is not False:
        raise SystemExit(f"validator STOP: {label} atomicity_claim must be false")

    oids = doc.get("stage_blob_oids") or {}
    for stage in ("1", "2", "3"):
        oid = oids.get(stage)
        if not oid or not re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", str(oid)):
            raise SystemExit(f"validator STOP: {label} missing/invalid stage {stage}")

    mut = doc.get("mutation_invariants") or {}
    for key in (
        "refs_unchanged",
        "index_unchanged",
        "worktree_unchanged",
        "unmerged_unchanged",
    ):
        if mut.get(key) is not True:
            raise SystemExit(f"validator STOP: {label} mutation invariant failed: {key}")
    if doc.get("refs_before_digest") != doc.get("refs_after_digest"):
        raise SystemExit(f"validator STOP: {label} refs before!=after")
    if doc.get("index_before_digest") != doc.get("index_after_digest"):
        raise SystemExit(f"validator STOP: {label} index before!=after")
    if doc.get("worktree_before_digest") != doc.get("worktree_after_digest"):
        raise SystemExit(f"validator STOP: {label} worktree before!=after")
    if doc.get("unmerged_inventory_before") != doc.get("unmerged_inventory_after"):
        raise SystemExit(f"validator STOP: {label} unmerged before!=after")

    terminal = doc.get("terminal_result") or {}
    if terminal.get("status") != "PREVIEW_READY" or not terminal.get("preview_ready"):
        raise SystemExit(f"validator STOP: {label} did not reach PREVIEW_READY")

    for required in (
        "FACTS",
        "OURS",
        "THEIRS",
        "CONTEXT_EVIDENCE",
        "INTERPRETATIONS",
        "OWNER_DECISIONS_REQUIRED",
        "RESOLUTION_OPTIONS",
        "VALIDATION_PLAN",
        "LIMITATIONS",
        "command_ledger",
        "fixture_setup_ledger",
        "RECOMMENDATION",
    ):
        if required not in doc:
            raise SystemExit(f"validator STOP: {label} missing field {required}")

    preview_ledger = doc.get("command_ledger") or []
    if not preview_ledger:
        raise SystemExit(f"validator STOP: {label} empty PREVIEW command_ledger")
    for entry in preview_ledger:
        op = entry.get("operation_id")
        if op not in _PREVIEW_READONLY_OPS:
            raise SystemExit(
                f"validator STOP: {label} PREVIEW ledger unknown/mutating op: {op}"
            )
        for tok in entry.get("argv") or []:
            if str(tok) in _MUTATING_GIT_TOKENS:
                raise SystemExit(
                    f"validator STOP: {label} mutating token in PREVIEW ledger: {tok}"
                )

    setup = doc.get("fixture_setup_ledger") or []
    if not setup:
        raise SystemExit(f"validator STOP: {label} empty FIXTURE_SETUP ledger")
    for entry in setup:
        if entry.get("phase") != "FIXTURE_SETUP" or not entry.get("not_preview"):
            raise SystemExit(
                f"validator STOP: {label} fixture entry not marked FIXTURE_SETUP"
            )

    frozen = doc.get("frozen_preview_runtime_hashes") or {}
    for name, expected in FROZEN_PREVIEW_RUNTIME_HASHES.items():
        if frozen.get(name) != expected:
            raise SystemExit(
                f"validator STOP: {label} frozen hash pin mismatch for {name}"
            )

    text = json.dumps(doc, ensure_ascii=False, sort_keys=True)
    # Serialized scan is optional defense-in-depth only; recursive raw-value
    # walk is authoritative (R39 / R38 JSON-escaping bypass).
    assert_no_author_paths_in_json(doc, label=label)
    # Also reject if raw author roots somehow appear unescaped in dumps.
    author_root = str(REPO_ROOT.resolve())
    author_pkg = str(PACKAGE_ROOT.resolve())
    if author_root and author_root in text:
        raise SystemExit(f"validator STOP: {label} serialized author repo path")
    if author_pkg and author_pkg in text:
        raise SystemExit(f"validator STOP: {label} serialized author package path")

    # Executable identity must remain; path must be tokenized.
    for entry in preview_ledger:
        exe = entry.get("executable_path")
        if exe and exe != TRUSTED_GIT_EXECUTABLE_TOKEN:
            raise SystemExit(
                f"validator STOP: {label} executable_path not tokenized: {exe!r}"
            )
        if not entry.get("expected_executable_digest") or not entry.get(
            "observed_pre_exec_digest"
        ):
            raise SystemExit(f"validator STOP: {label} missing executable digests")
        if entry.get("atomicity_claim") is not False:
            raise SystemExit(f"validator STOP: {label} atomicity_claim must be false")
    git_meta = doc.get("git_executable") or {}
    if git_meta.get("executable_path_tokenized") != TRUSTED_GIT_EXECUTABLE_TOKEN:
        raise SystemExit(
            f"validator STOP: {label} git_executable path not tokenized"
        )


def validate_preview_evidence_artifacts(
    *,
    merge_path: Path,
    rebase_path: Path,
    package_name: str,
    package_version: str,
    package_digest: str,
    inner_archive_sha256: str,
) -> None:
    """Validate both shipped evidence files on disk."""
    for path, op in ((merge_path, "merge"), (rebase_path, "rebase")):
        if not path.is_file():
            raise SystemExit(f"validator STOP: missing preview evidence: {path.name}")
        doc = json.loads(path.read_text(encoding="utf-8"))
        validate_preview_evidence_doc(
            doc,
            expected_operation=op,
            package_name=package_name,
            package_version=package_version,
            package_digest=package_digest,
            inner_archive_sha256=inner_archive_sha256,
            label=path.name,
        )


def write_evidence_pair(
    *,
    out_dir: Path,
    package_staging: Path,
    package_name: str,
    package_version: str,
    package_digest: str,
    inner_archive_sha256: str,
) -> tuple[Path, Path, Path]:
    """Generate merge+rebase evidence into *out_dir*; return paths."""
    assert_native_io_path(out_dir, role="preview_evidence_out")
    out_dir.mkdir(parents=True, exist_ok=True)
    observed = assert_frozen_preview_runtime(package_staging)
    work_root = out_dir / f"{package_name}_PREVIEW_EVIDENCE_WORK_{os.getpid()}"
    _rmtree_force(work_root)
    work_root.mkdir(parents=True, exist_ok=True)
    fixtures: list[Path] = []
    docs: dict[str, dict[str, Any]] = {}
    for operation in ("merge", "rebase"):
        doc = build_one_case(
            operation=operation,
            package_staging=package_staging,
            work_root=work_root,
            package_name=package_name,
            package_version=package_version,
            package_digest=package_digest,
            inner_archive_sha256=inner_archive_sha256,
        )
        fixtures.append(work_root / f"fixture_{operation}")
        docs[operation] = doc

    mapping = build_normalization_map(
        package_staging=package_staging,
        fixture_repos=fixtures,
        work_root=work_root,
        extra_executable_paths=[],
    )

    def _normalize_doc(doc: dict[str, Any]) -> dict[str, Any]:
        # Collect every absolute executable path before tokenization.
        exe_paths = collect_executable_paths(doc)
        # Also collect argv[0]-style absolute git paths that look like profiles.
        for _path, raw in iter_json_strings(doc):
            if string_contains_forbidden_path(raw) and (
                "git" in raw.lower() or raw.endswith(".EXE") or raw.endswith(".exe")
            ):
                exe_paths.append(raw)
        local_map = build_normalization_map(
            package_staging=package_staging,
            fixture_repos=fixtures,
            work_root=work_root,
            extra_executable_paths=exe_paths,
        )
        sanitized = sanitize_evidence_paths(doc, local_map)
        assert_no_author_paths_in_json(
            sanitized, label=doc.get("scenario_id") or "evidence"
        )
        return sanitized

    merge_doc = _normalize_doc(docs["merge"])
    rebase_doc = _normalize_doc(docs["rebase"])

    for doc, op in ((merge_doc, "merge"), (rebase_doc, "rebase")):
        validate_preview_evidence_doc(
            doc,
            expected_operation=op,
            package_name=package_name,
            package_version=package_version,
            package_digest=package_digest,
            inner_archive_sha256=inner_archive_sha256,
            label=f"normalized:{op}",
        )

    merge_path = out_dir / f"{package_name}.MERGE_PREVIEW_EVIDENCE.json"
    rebase_path = out_dir / f"{package_name}.REBASE_PREVIEW_EVIDENCE.json"
    index_path = out_dir / f"{package_name}.PREVIEW_EVIDENCE_INDEX.json"

    merge_path.write_text(
        json.dumps(merge_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    rebase_path.write_text(
        json.dumps(rebase_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    index = {
        "schema": INDEX_SCHEMA,
        "package_name": package_name,
        "package_version": package_version,
        "package_digest": package_digest,
        "inner_archive_sha256": inner_archive_sha256,
        "go_capability": False,
        "safe_usage_scope": "PREVIEW_ONLY",
        "frozen_preview_runtime_hashes": observed,
        "members": [
            {
                "path": merge_path.name,
                "operation": "merge",
                "sha256": sha256_file(merge_path),
                "bytes": merge_path.stat().st_size,
                "scenario_id": merge_doc["scenario_id"],
            },
            {
                "path": rebase_path.name,
                "operation": "rebase",
                "sha256": sha256_file(rebase_path),
                "bytes": rebase_path.stat().st_size,
                "scenario_id": rebase_doc["scenario_id"],
            },
        ],
    }
    index_path.write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    _rmtree_force(work_root)
    return merge_path, rebase_path, index_path


def build_preview_evidence_for_ship(
    *,
    archive_path: Path,
    out_dir: Path,
    package_name: str,
    package_version: str,
    package_digest: str,
    inner_archive_sha256: str,
) -> tuple[Path, Path, Path]:
    """Ship entry: extract packaged runtime from ZIP and emit evidence."""
    work = out_dir / f"{package_name}_PREVIEW_STAGING"
    package_staging = stage_package_from_zip(archive_path, work)
    try:
        return write_evidence_pair(
            out_dir=out_dir,
            package_staging=package_staging,
            package_name=package_name,
            package_version=package_version,
            package_digest=package_digest,
            inner_archive_sha256=inner_archive_sha256,
        )
    finally:
        _rmtree_force(work)


def main() -> None:
    """CLI: build evidence against current PACKAGE_ROOT tree (dev/test)."""
    sys.path.insert(0, str(PACKAGE_ROOT / "runtime"))
    from opsx_conflict.attestation import PACKAGE_VERSION

    out = native_artifact_root()
    manifest = json.loads((PACKAGE_ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    package_name = str(
        manifest.get("package_name") or "OPSX_RESOLVE_CONFLICT_COMMAND_001"
    )
    package_version = str(manifest.get("package_version") or PACKAGE_VERSION)
    package_digest = str(manifest.get("package_digest") or ("0" * 64))
    staging = out / f"{package_name}_PREVIEW_TREE_STAGING"
    package_staging = stage_package_from_tree(staging)
    try:
        merge_p, rebase_p, index_p = write_evidence_pair(
            out_dir=out,
            package_staging=package_staging,
            package_name=package_name,
            package_version=package_version,
            package_digest=package_digest,
            inner_archive_sha256="0" * 64,
        )
    finally:
        _rmtree_force(staging)
    print(f"MERGE={merge_p}")
    print(f"REBASE={rebase_p}")
    print(f"INDEX={index_p}")


if __name__ == "__main__":
    main()
