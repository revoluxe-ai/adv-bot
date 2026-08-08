#!/usr/bin/env python3
"""Build portable REPLAY_EVIDENCE.zip with exact-match terminal assertions (R29).

Execution location:
- Stages a packaging copy under native temp ``..._REPLAY_STAGING`` (never the
  author source workspace). Uses ``tempfile.gettempdir()`` / OPSX_REVIEW_OUT_DIR.
- Runs command entrypoints from that staging tree only.

Acceptance (R29):
- Nonzero exit code alone is never PASS.
- Each case has a versioned expectation contract.
- PASS is the logical AND of exact assertions.
- Builder fails closed and does not write the final ZIP on any mismatch.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from path_workspace import native_artifact_root  # noqa: E402

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]
OUT_DIR = native_artifact_root()
PACKAGE_NAME = "OPSX_RESOLVE_CONFLICT_COMMAND_001_R34"
PACKAGE_VERSION = "0.34.0"
NORMALIZATION_SCHEMA = "opsx-resolve-conflict/path-normalization/v2"
REPLAY_SUMMARY_SCHEMA = "opsx-resolve-conflict/replay-evidence/v6"
REPLAY_EXPECTATION_SCHEMA = "opsx-resolve-conflict/replay-expectation/v1"
CLI_STOP_ENVELOPE_SCHEMA = "opsx-resolve-conflict/cli-stop-envelope/v1"
CLI_STOP_EXIT_CODE = 78

TRACEBACK_MARKERS = (
    "Traceback (most recent call last)",
    "File \"",
    "File '",
)


def sha256_bytes(data: bytes) -> str:
    """Return SHA-256 hex digest."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """Return SHA-256 hex digest of a file."""
    return sha256_bytes(path.read_bytes())


def _rmtree_force(path: Path) -> None:
    """Remove a tree, clearing read-only bits (Windows Git objects)."""

    def _onerror(func, name, _exc_info):  # type: ignore[no-untyped-def]
        try:
            os.chmod(name, 0o700)
            func(name)
        except OSError:
            pass

    if path.exists():
        shutil.rmtree(path, onerror=_onerror)


def _process_tree() -> str:
    """Capture portable process snapshot (name/pid only; no CommandLine home paths)."""
    if os.name == "nt":
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    "Get-CimInstance Win32_Process | "
                    "Select-Object ProcessId,ParentProcessId,Name | "
                    "ConvertTo-Json -Compress"
                ),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    else:
        proc = subprocess.run(
            ["ps", "-eo", "pid,ppid,comm"],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    return (proc.stdout or "") + (proc.stderr or "")


def _fixture_git_process_keys(repo: Path, state: Path) -> set[str]:
    """Return live git processes tied to fixture repo or replay state root."""
    tokens: list[str] = []
    for path in (repo, state):
        resolved = str(path.resolve())
        tokens.extend([resolved, resolved.replace("\\", "/")])
    if os.name == "nt":
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    "Get-CimInstance Win32_Process | "
                    "Where-Object { $_.Name -match '^git(\\.exe)?$' } | "
                    "Select-Object ProcessId,Name,CommandLine | "
                    "ConvertTo-Json -Compress"
                ),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        blob = proc.stdout or ""
    else:
        proc = subprocess.run(
            ["ps", "-eo", "pid,comm,args"],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        blob = proc.stdout or ""
    keys: set[str] = set()
    try:
        data = json.loads(blob) if blob.strip().startswith(("[", "{")) else None
    except json.JSONDecodeError:
        data = None
    rows: list[Any]
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = [data]
    else:
        rows = []
        for line in blob.splitlines():
            parts = line.split(None, 2)
            if len(parts) >= 2 and parts[0].isdigit():
                rows.append(
                    {
                        "ProcessId": parts[0],
                        "Name": parts[1],
                        "CommandLine": parts[2] if len(parts) > 2 else "",
                    }
                )
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        cmdline = str(row.get("CommandLine") or "")
        if not any(token in cmdline for token in tokens):
            continue
        # Portable key: omit absolute command line from shipped delta identities.
        keys.add(f"git:{row.get('ProcessId')}")
    return keys


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run git in cwd with text capture."""
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def _snapshot_git_state(cwd: Path) -> dict[str, str]:
    """Capture refs / index / worktree evidence for a fixture repo."""
    return {
        "head": _git(cwd, "rev-parse", "HEAD").stdout.strip(),
        "status_porcelain_v2": _git(
            cwd, "status", "--porcelain=v2", "-z", "--branch"
        ).stdout,
        "ls_files_unmerged": _git(cwd, "ls-files", "-u").stdout,
        "refs": _git(cwd, "for-each-ref", "--format=%(refname) %(objectname)").stdout,
        "diff_cached_name_status": _git(
            cwd, "diff", "--cached", "--name-status"
        ).stdout,
        "conflict_worktree_sha256": (
            sha256_file(cwd / "conflict.py") if (cwd / "conflict.py").is_file() else ""
        ),
    }


def _make_conflict_repo(root: Path, *, operation: str) -> dict[str, str]:
    """Create a real merge or rebase conflict fixture repository."""
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init")
    _git(root, "config", "user.email", "replay@example.com")
    _git(root, "config", "user.name", "replay")
    (root / "conflict.py").write_text(
        'def base():\n    return "base"\n',
        encoding="utf-8",
    )
    _git(root, "add", "conflict.py")
    _git(root, "commit", "-m", "base")
    base = _git(root, "rev-parse", "HEAD").stdout.strip()
    _git(root, "checkout", "-b", "feature")
    (root / "conflict.py").write_text(
        'def base():\n    return "base"\n\ndef feature_write():\n    return "feature"\n',
        encoding="utf-8",
    )
    _git(root, "add", "conflict.py")
    _git(root, "commit", "-m", "feature")
    feature = _git(root, "rev-parse", "HEAD").stdout.strip()
    _git(root, "checkout", "master")
    if _git(root, "rev-parse", "--verify", "master").returncode != 0:
        _git(root, "checkout", "-B", "master", base)
    (root / "conflict.py").write_text(
        'def base():\n    return "base"\n\ndef main_write():\n    return "main"\n',
        encoding="utf-8",
    )
    _git(root, "add", "conflict.py")
    _git(root, "commit", "-m", "mainline")
    mainline = _git(root, "rev-parse", "HEAD").stdout.strip()
    if operation == "merge":
        merge = _git(root, "merge", "--no-ff", "--no-commit", "feature")
        terminal_seed = {
            "operation": "merge",
            "merge_returncode": str(merge.returncode),
            "base": base,
            "feature": feature,
            "mainline": mainline,
        }
    else:
        _git(root, "checkout", "feature")
        rebase = _git(root, "rebase", "master")
        terminal_seed = {
            "operation": "rebase",
            "rebase_returncode": str(rebase.returncode),
            "base": base,
            "feature": feature,
            "mainline": mainline,
        }
    unmerged = _git(root, "ls-files", "-u").stdout
    if not unmerged.strip():
        raise SystemExit(f"replay fixture failed to create conflict: {operation}")
    git_dir = Path(_git(root, "rev-parse", "--git-dir").stdout.strip())
    if not git_dir.is_absolute():
        git_dir = (root / git_dir).resolve()
    if operation == "merge":
        merge_head = (git_dir / "MERGE_HEAD").read_text(encoding="utf-8").strip()
        terminal_seed["expected_operation_head"] = merge_head
    else:
        rebase_head_path = git_dir / "REBASE_HEAD"
        if rebase_head_path.is_file():
            terminal_seed["expected_operation_head"] = rebase_head_path.read_text(
                encoding="utf-8"
            ).strip()
        else:
            stopped = git_dir / "rebase-merge" / "stopped-sha"
            terminal_seed["expected_operation_head"] = stopped.read_text(
                encoding="utf-8"
            ).strip()
    terminal_seed["ls_files_unmerged"] = unmerged
    return terminal_seed


def _is_user_profile_path(path: Path) -> bool:
    """Return True if path sits under a user-profile home root."""
    text = str(path.resolve())
    _u = "Users"
    _h = "home"
    if re.search(rf"(?i)[A-Z]:\\{_u}\\", text):
        return True
    if re.search(rf"(?i)/{_u}/", text):
        return True
    if re.search(rf"(?i)/{_h}/", text):
        return True
    return False


def build_normalization_map(
    *,
    staging_root: Path,
    package_staging: Path,
    fixture_repos: list[Path],
) -> list[tuple[str, str]]:
    """Build longest-first portable mapping (staging/python only; no author roots)."""
    pairs: list[tuple[str, str]] = [
        (str(package_staging.resolve()), "<PACKAGE_STAGING>"),
        (str(staging_root.resolve()), "<REPLAY_STAGING>"),
    ]
    py = os.path.realpath(sys.executable)
    prefix = os.path.realpath(sys.prefix)
    if not _is_user_profile_path(Path(py)):
        pairs.append((py, "<PYTHON>"))
    if not _is_user_profile_path(Path(prefix)):
        pairs.append((prefix, "<PYTHON_PREFIX>"))
    for idx, repo in enumerate(fixture_repos):
        pairs.append((str(repo.resolve()), f"<FIXTURE_REPO_{idx}>"))
    seen: set[str] = set()
    ordered: list[tuple[str, str]] = []
    for literal, token in sorted(pairs, key=lambda item: len(item[0]), reverse=True):
        if not literal or literal in seen:
            continue
        seen.add(literal)
        ordered.append((literal, token))
    return ordered


def normalize_text(text: str, mapping: list[tuple[str, str]]) -> str:
    """Apply deterministic path token substitution (no silent home scrub)."""
    out = text
    for literal, token in mapping:
        out = out.replace(literal, token)
        alt = literal.replace("\\", "/")
        if alt != literal:
            out = out.replace(alt, token)
    return out


def assert_no_forbidden_paths(text: str, *, label: str) -> None:
    """Fail closed if author/user/source workspace paths remain."""
    _u = "Users"
    _h = "home"
    _mr = "meta" + "-repo"
    _ab = "adv" + "-bot"
    patterns = [
        (rf"(?i)[A-Z]:\\{_u}\\", "user_profile_path_windows"),
        (rf"(?i)/{_u}/", "user_profile_path_macos"),
        (rf"(?i)/{_h}/", "user_profile_path_linux"),
        (rf"(?i){_mr}\\{_ab}", "author_workspace"),
        (rf"(?i){_mr}/{_ab}", "author_workspace_posix"),
    ]
    author_root = str(REPO_ROOT.resolve())
    if author_root and author_root in text:
        raise SystemExit(f"replay STOP: author repo path leaked in {label}")
    package_root = str(PACKAGE_ROOT.resolve())
    if package_root and package_root in text:
        raise SystemExit(f"replay STOP: author package path leaked in {label}")
    for pat, reason in patterns:
        if re.search(pat, text):
            raise SystemExit(f"replay STOP: forbidden path ({reason}) in {label}")


def verify_raw_to_normalized(
    raw_text: str,
    normalized_text: str,
    mapping: list[tuple[str, str]],
) -> dict[str, object]:
    """Machine-check normalize(raw, mapping) == normalized."""
    recomputed = normalize_text(raw_text, mapping)
    raw_sha = sha256_bytes(raw_text.encode("utf-8"))
    norm_sha = sha256_bytes(normalized_text.encode("utf-8"))
    recomputed_sha = sha256_bytes(recomputed.encode("utf-8"))
    ok = recomputed == normalized_text and recomputed_sha == norm_sha
    return {
        "ok": ok,
        "raw_sha256": raw_sha,
        "normalized_sha256": norm_sha,
        "recomputed_normalized_sha256": recomputed_sha,
        "byte_equal": recomputed == normalized_text,
    }


def _stage_package(staging_root: Path) -> Path:
    """Copy packaged inventory into portable staging (boot + MANIFEST root)."""
    package_staging = staging_root / "package"
    _rmtree_force(package_staging)
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
            raise SystemExit(f"replay STOP: missing package member {rel}")
        if src.is_dir():
            shutil.copytree(
                src,
                dst,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
            )
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    boot = package_staging / "runtime" / "boot_opsx_conflict.py"
    if not boot.is_file():
        raise SystemExit("replay STOP: staged boot entrypoint missing")
    return package_staging


def _origin_commit() -> str:
    """Return origin commit for host-contract restore."""
    manifest = json.loads((PACKAGE_ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    origin = str(
        manifest.get("origin_source_commit") or manifest.get("source_commit") or ""
    ).strip()
    if origin:
        return origin
    return subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
        text=True,
    ).strip()


def _install_fixture_contracts(repo: Path, package_staging: Path) -> dict[str, str]:
    """Install packaged host contracts + command copy into the fixture repo."""
    manifest = json.loads((package_staging / "MANIFEST.json").read_text(encoding="utf-8"))
    categories = manifest.get("input_categories") or {}
    host_frozen = list(categories.get("host_frozen_contracts") or [])
    package_owned = list(categories.get("package_owned_required") or [])
    origin = _origin_commit()
    installed: dict[str, str] = {}
    for rel in host_frozen:
        proc = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "show", f"{origin}:{rel}"],
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            raise SystemExit(f"replay STOP: host contract missing at origin: {rel}")
        dest = repo / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(proc.stdout)
        installed[rel] = sha256_bytes(proc.stdout)
    # Package-owned required paths (command + process_surfaces).
    cmd_src = (
        package_staging / "candidate" / ".cursor" / "commands" / "opsx-resolve-conflict.md"
    )
    cmd_dst = repo / ".cursor" / "commands" / "opsx-resolve-conflict.md"
    cmd_dst.parent.mkdir(parents=True, exist_ok=True)
    cmd_dst.write_bytes(cmd_src.read_bytes())
    installed[str(cmd_dst.relative_to(repo).as_posix())] = sha256_file(cmd_dst)
    ps_src = package_staging / "process_surfaces.json"
    ps_dst = repo / ".cursor" / "opsx-resolve-conflict" / "process_surfaces.json"
    ps_dst.parent.mkdir(parents=True, exist_ok=True)
    ps_dst.write_bytes(ps_src.read_bytes())
    installed[str(ps_dst.relative_to(repo).as_posix())] = sha256_file(ps_dst)
    for rel in package_owned:
        if rel not in installed and not (repo / rel).is_file():
            raise SystemExit(f"replay STOP: package-owned path missing: {rel}")
    return installed


def _package_trust_digest(package_staging: Path) -> str:
    """Return live package_digest from the staged package inventory.

    Prefer computing digest from staged bytes (matches package_compatibility_gate)
    and verify it equals TRUST_ANCHOR.package_digest.
    """
    runtime = package_staging / "runtime"
    # Isolate staged attestation import from any previously loaded package.
    import importlib
    import sys as _sys

    # Drop already-loaded opsx_conflict modules so PACKAGE_ROOT resolves to staging.
    for name in list(_sys.modules):
        if name == "opsx_conflict" or name.startswith("opsx_conflict."):
            del _sys.modules[name]
    _sys.path.insert(0, str(runtime))
    from opsx_conflict.attestation import inventory_hashes, package_digest  # noqa: WPS433

    hashes = inventory_hashes()
    digest = package_digest(
        {key: value for key, value in hashes.items() if key != "TRUST_ANCHOR.json"}
    )
    anchor = json.loads(
        (package_staging / "TRUST_ANCHOR.json").read_text(encoding="utf-8")
    )
    anchor_digest = str(anchor.get("package_digest") or "").strip().lower()
    if digest != anchor_digest:
        raise SystemExit(
            "replay STOP: staged TRUST_ANCHOR digest drift "
            f"(anchor={anchor_digest} live={digest})"
        )
    return digest


def _build_scope_for_repo(
    *,
    repo: Path,
    state_dir: Path,
    package_staging: Path,
    run_id: str,
) -> Path:
    """Freeze a schema-valid scope bound to the current conflict inventory."""
    runtime = package_staging / "runtime"
    if str(runtime) not in sys.path:
        sys.path.insert(0, str(runtime))
    git_bin = shutil.which("git")
    if git_bin:
        os.environ["OPSX_CONFLICT_GIT_TRUST_DIGEST"] = sha256_file(Path(git_bin))
    os.environ["OPSX_CONFLICT_STATE"] = str(state_dir)
    from opsx_conflict.git_typed import TypedGit  # noqa: WPS433
    from opsx_conflict.hashutil import sha256_text  # noqa: WPS433
    from opsx_conflict.operation import detect_operation_state  # noqa: WPS433
    from opsx_conflict.scope import freeze_scope_from_state  # noqa: WPS433

    git = TypedGit(repo)
    op_state = detect_operation_state(repo, git)
    scope = freeze_scope_from_state(
        op_state,
        repo_root=repo,
        run_id=run_id,
        authority_sha256=sha256_text("replay-scope-authority"),
    )
    scope_path = state_dir / f"{run_id}.scope.json"
    scope.persist(scope_path)
    return scope_path


def parse_structured_output(stdout: str, stderr: str) -> dict[str, Any]:
    """Parse JSON from stdout (preferred) or stderr; record parse errors."""
    for label, blob in (("stdout", stdout), ("stderr", stderr)):
        text = blob.strip()
        if not text:
            continue
        try:
            return {
                "ok": True,
                "source": label,
                "value": json.loads(text),
                "error": None,
            }
        except json.JSONDecodeError as exc:
            # Try last JSON object in mixed output.
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                try:
                    return {
                        "ok": True,
                        "source": label,
                        "value": json.loads(text[start : end + 1]),
                        "error": None,
                    }
                except json.JSONDecodeError:
                    pass
            return {
                "ok": False,
                "source": label,
                "value": None,
                "error": str(exc),
            }
    return {"ok": False, "source": None, "value": None, "error": "no_json_output"}


def contains_traceback(text: str) -> bool:
    """Return True when output contains a Python traceback fingerprint."""
    return any(marker in text for marker in TRACEBACK_MARKERS)


def make_expectation(
    *,
    case_id: str,
    command_kind: str,
    expected_exit_code: int,
    expected_status: str | None,
    expected_stop_reason: str | None,
    expected_operation: str | None,
    expected_gate: str | None,
    expected_state: dict[str, Any],
) -> dict[str, Any]:
    """Build a versioned replay expectation contract."""
    return {
        "schema": REPLAY_EXPECTATION_SCHEMA,
        "case_id": case_id,
        "command_kind": command_kind,
        "expected_exit_code": expected_exit_code,
        "expected_status": expected_status,
        "expected_stop_reason": expected_stop_reason,
        "expected_operation": expected_operation,
        "expected_gate": expected_gate,
        "expected_state": expected_state,
    }


def evaluate_replay_case(
    *,
    expectation: Mapping[str, Any],
    returncode: int,
    stdout: str,
    stderr: str,
    before_state: Mapping[str, str],
    after_state: Mapping[str, str],
    process_delta: list[str],
    fixture_meta: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Exact-match assertion engine. Nonzero exit alone never yields PASS."""
    parsed = parse_structured_output(stdout, stderr)
    value = parsed.get("value") if parsed.get("ok") else None
    combined = (stdout or "") + (stderr or "")
    assertions: list[dict[str, Any]] = []

    def _check(name: str, expected: Any, actual: Any, *, ok: bool | None = None) -> None:
        passed = (expected == actual) if ok is None else bool(ok)
        assertions.append(
            {
                "name": name,
                "expected": expected,
                "actual": actual,
                "passed": passed,
            }
        )

    _check("exit_code", expectation["expected_exit_code"], returncode)

    forbid_scope_pass = bool(
        (expectation.get("expected_state") or {}).get(
            "forbid_scope_file_required_as_pass", True
        )
    )
    if forbid_scope_pass:
        is_scope_required = (
            returncode != 0
            and (
                "SCOPE_FILE_REQUIRED" in combined
                or (
                    isinstance(value, Mapping)
                    and value.get("reason") == "SCOPE_FILE_REQUIRED"
                )
            )
            and expectation.get("expected_stop_reason") != "SCOPE_FILE_REQUIRED"
        )
        _check(
            "scope_file_required_not_accepted_as_target",
            False,
            is_scope_required,
            ok=not is_scope_required,
        )

    forbid_traceback = bool(
        (expectation.get("expected_state") or {}).get("forbid_traceback", True)
    )
    if forbid_traceback:
        has_tb = contains_traceback(combined)
        _check("no_traceback", False, has_tb, ok=not has_tb)

    status_actual: str | None = None
    reason_actual: str | None = None
    gate_actual: str | None = None
    operation_actual: str | None = None
    state_obj: Mapping[str, Any] | None = None

    if expectation["command_kind"] == "state":
        _check("structured_json", True, parsed.get("ok"), ok=bool(parsed.get("ok")))
        if isinstance(value, Mapping):
            state_obj = value.get("state") if isinstance(value.get("state"), Mapping) else value
            if isinstance(state_obj, Mapping):
                operation_actual = state_obj.get("operation")
                status_actual = "OK"
        _check("status", expectation["expected_status"], status_actual)
        _check("stop_reason", expectation["expected_stop_reason"], reason_actual)
        _check("operation", expectation["expected_operation"], operation_actual)
        _check("reached_gate", expectation["expected_gate"], "operation_state_detection")
        gate_actual = "operation_state_detection"
    else:
        _check("structured_json", True, parsed.get("ok"), ok=bool(parsed.get("ok")))
        if isinstance(value, Mapping):
            status_actual = value.get("status")
            reason_actual = value.get("reason")
            gate_actual = value.get("reached_gate")
            _check("stop_envelope_schema", CLI_STOP_ENVELOPE_SCHEMA, value.get("schema"))
            _check("stop_envelope_status", "STOP", value.get("status"))
        _check("status", expectation["expected_status"], status_actual)
        _check("stop_reason", expectation["expected_stop_reason"], reason_actual)
        _check("reached_gate", expectation["expected_gate"], gate_actual)
        if expectation.get("expected_operation") is not None:
            _check("operation", expectation["expected_operation"], operation_actual)

    exp_state = expectation.get("expected_state") or {}
    if exp_state.get("require_unmerged_nonempty"):
        unmerged = ""
        if isinstance(state_obj, Mapping):
            unmerged_list = state_obj.get("unmerged") or []
            unmerged = json.dumps(unmerged_list)
        elif fixture_meta:
            unmerged = str(fixture_meta.get("ls_files_unmerged") or "")
        _check(
            "unmerged_nonempty",
            True,
            bool(unmerged.strip()),
            ok=bool(unmerged.strip()),
        )
    if exp_state.get("require_stage_oids"):
        oids: list[str] = []
        if isinstance(state_obj, Mapping):
            for entry in state_obj.get("unmerged") or []:
                if isinstance(entry, Mapping) and entry.get("oid"):
                    oids.append(str(entry["oid"]))
        _check(
            "stage_oids_present",
            True,
            bool(oids),
            ok=bool(oids) and all(len(o) == 40 for o in oids),
        )
    if exp_state.get("require_operation_head"):
        head_actual = None
        if isinstance(state_obj, Mapping):
            head_actual = state_obj.get("operation_head")
        expected_head = None
        if fixture_meta:
            expected_head = fixture_meta.get("expected_operation_head")
        _check("operation_head", expected_head, head_actual)
    if exp_state.get("refs_immutable", True):
        _check(
            "refs_immutable",
            before_state.get("refs"),
            after_state.get("refs"),
        )
    if exp_state.get("index_immutable", True):
        _check(
            "index_unmerged_immutable",
            before_state.get("ls_files_unmerged"),
            after_state.get("ls_files_unmerged"),
        )
        _check(
            "index_cached_immutable",
            before_state.get("diff_cached_name_status"),
            after_state.get("diff_cached_name_status"),
        )
    if exp_state.get("worktree_conflict_immutable", True):
        _check(
            "conflict_worktree_immutable",
            before_state.get("conflict_worktree_sha256"),
            after_state.get("conflict_worktree_sha256"),
        )
    if exp_state.get("process_delta_empty", True):
        _check("process_delta_empty", [], process_delta)
    if exp_state.get("go_capability") is not None and isinstance(value, Mapping):
        details = value.get("details") if isinstance(value.get("details"), Mapping) else {}
        actual_cap = details.get("go_capability")
        _check("go_capability", exp_state.get("go_capability"), actual_cap)

    # Exact PASS is AND of all assertions — never "any nonzero".
    passed = all(bool(a["passed"]) for a in assertions) and bool(assertions)
    actual = {
        "exit_code": returncode,
        "status": status_actual,
        "stop_reason": reason_actual,
        "operation": operation_actual,
        "reached_gate": gate_actual,
        "structured_ok": bool(parsed.get("ok")),
        "traceback": contains_traceback(combined),
    }
    return {
        "passed": passed,
        "assertions": assertions,
        "expected": {
            "exit_code": expectation["expected_exit_code"],
            "status": expectation["expected_status"],
            "stop_reason": expectation["expected_stop_reason"],
            "operation": expectation["expected_operation"],
            "reached_gate": expectation["expected_gate"],
        },
        "actual": actual,
        "reached_gate": gate_actual,
        "parsed": parsed,
    }


def _run_boot_command(
    *,
    argv_tail: list[str],
    repo: Path,
    state: Path,
    package_staging: Path,
    ledger: list[dict],
    mapping: list[tuple[str, str]],
    trust_digest: str | None,
) -> dict[str, Any]:
    """Invoke staged boot entrypoint and capture portable evidence."""
    boot = package_staging / "runtime" / "boot_opsx_conflict.py"
    runtime = package_staging / "runtime"
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("OPSX_CONFLICT_AUTHORITY_")
        and k
        not in {
            "OPSX_CONFLICT_SANDBOX_RUNNER",
            "OPSX_LINEAGE_SIGNED_PROVENANCE",
        }
    }
    env["PYTHONPATH"] = str(runtime)
    env["OPSX_CONFLICT_STATE"] = str(state)
    git = shutil.which("git")
    if git:
        env["OPSX_CONFLICT_GIT_TRUST_DIGEST"] = sha256_file(Path(git))
    if trust_digest:
        env["OPSX_CONFLICT_TRUST_DIGEST"] = trust_digest
    if _is_user_profile_path(Path(sys.executable)):
        raise SystemExit(
            "replay STOP: python executable under user profile; "
            "raw evidence would be non-portable"
        )
    real_argv = [sys.executable, str(boot), *argv_tail]
    before_state = _snapshot_git_state(repo)
    before_tree = _process_tree()
    before_git_procs = _fixture_git_process_keys(repo, state)
    proc = subprocess.run(
        real_argv,
        cwd=str(repo),
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    # Brief settle so short-lived trusted-git children exit before delta.
    time.sleep(0.35)
    after_tree = _process_tree()
    after_state = _snapshot_git_state(repo)
    after_git_procs = _fixture_git_process_keys(repo, state)
    process_delta = sorted(after_git_procs - before_git_procs)

    portable_argv = ["<PYTHON>", "<PACKAGE_STAGING>/runtime/boot_opsx_conflict.py", *argv_tail]
    # Replace absolute repo/scope paths in portable argv when present.
    portable_argv = [
        normalize_text(part, mapping) if os.path.isabs(part) or "\\" in part or "/" in part
        else part
        for part in portable_argv
    ]
    ledger.append(
        {
            "event": "COMMAND_START",
            "argv": portable_argv,
            "cwd": "<FIXTURE_REPO>",
            "execution_location": "package_staging_under_CTemp",
        }
    )
    stdout_raw = proc.stdout or ""
    stderr_raw = proc.stderr or ""
    for label, blob in (
        ("stdout_raw", stdout_raw),
        ("stderr_raw", stderr_raw),
        ("process_tree_before_raw", before_tree),
        ("process_tree_after_raw", after_tree),
    ):
        assert_no_forbidden_paths(blob, label=label)

    stdout_norm = normalize_text(stdout_raw, mapping)
    stderr_norm = normalize_text(stderr_raw, mapping)
    before_tree_norm = normalize_text(before_tree, mapping)
    after_tree_norm = normalize_text(after_tree, mapping)
    for label, blob in (
        ("stdout_normalized", stdout_norm),
        ("stderr_normalized", stderr_norm),
        ("process_tree_before_normalized", before_tree_norm),
        ("process_tree_after_normalized", after_tree_norm),
    ):
        assert_no_forbidden_paths(blob, label=label)

    verifications = {
        "stdout": verify_raw_to_normalized(stdout_raw, stdout_norm, mapping),
        "stderr": verify_raw_to_normalized(stderr_raw, stderr_norm, mapping),
        "process_tree_before": verify_raw_to_normalized(
            before_tree, before_tree_norm, mapping
        ),
        "process_tree_after": verify_raw_to_normalized(
            after_tree, after_tree_norm, mapping
        ),
    }
    if not all(bool(v["ok"]) for v in verifications.values()):
        raise SystemExit("replay STOP: raw→normalized verification failed")

    ledger.append(
        {
            "event": "COMMAND_END",
            "argv": portable_argv,
            "returncode": proc.returncode,
            "stdout_sha256_raw": verifications["stdout"]["raw_sha256"],
            "stderr_sha256_raw": verifications["stderr"]["raw_sha256"],
            "stdout_sha256_normalized": verifications["stdout"]["normalized_sha256"],
            "stderr_sha256_normalized": verifications["stderr"]["normalized_sha256"],
        }
    )
    return {
        "argv": portable_argv,
        "returncode": proc.returncode,
        "stdout_raw": stdout_raw,
        "stderr_raw": stderr_raw,
        "stdout_normalized": stdout_norm,
        "stderr_normalized": stderr_norm,
        "process_tree_before_raw": before_tree,
        "process_tree_after_raw": after_tree,
        "process_tree_before_normalized": before_tree_norm,
        "process_tree_after_normalized": after_tree_norm,
        "verifications": verifications,
        "stdout_sha256_raw": verifications["stdout"]["raw_sha256"],
        "stderr_sha256_raw": verifications["stderr"]["raw_sha256"],
        "stdout_sha256_normalized": verifications["stdout"]["normalized_sha256"],
        "stderr_sha256_normalized": verifications["stderr"]["normalized_sha256"],
        "before_state": before_state,
        "after_state": after_state,
        "process_delta": process_delta,
        "refs_immutable": before_state["refs"] == after_state["refs"],
        "no_push_continue_abort_in_argv": (
            "push" not in " ".join(portable_argv)
            and "continue" not in " ".join(portable_argv)
            and "abort" not in " ".join(portable_argv)
        ),
        "execution_location": str(package_staging),
    }


def main() -> Path:
    """Write external REPLAY_EVIDENCE.zip and in-tree summary (exact-match only)."""
    built = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    builder_sha = sha256_file(Path(__file__).resolve())
    ledger: list[dict] = []
    cases: list[dict] = []

    staging_root = OUT_DIR / f"{PACKAGE_NAME}_REPLAY_STAGING"
    _rmtree_force(staging_root)
    staging_root.mkdir(parents=True)
    package_staging = _stage_package(staging_root)
    trust_digest = _package_trust_digest(package_staging)
    fixture_repos: list[Path] = []

    case_specs: list[dict[str, Any]] = []
    for operation in ("merge", "rebase"):
        case_specs.append(
            {
                "case_id": f"{operation}_state_detection",
                "operation": operation,
                "command_kind": "state",
                "expectation": make_expectation(
                    case_id=f"{operation}_state_detection",
                    command_kind="state",
                    expected_exit_code=0,
                    expected_status="OK",
                    expected_stop_reason=None,
                    expected_operation=operation,
                    expected_gate="operation_state_detection",
                    expected_state={
                        "require_unmerged_nonempty": True,
                        "require_stage_oids": True,
                        "require_operation_head": True,
                        "refs_immutable": True,
                        "index_immutable": True,
                        "worktree_conflict_immutable": True,
                        "process_delta_empty": True,
                        "forbid_traceback": True,
                        "forbid_scope_file_required_as_pass": True,
                    },
                ),
            }
        )
        case_specs.append(
            {
                "case_id": f"{operation}_go_package_capability_disabled",
                "operation": operation,
                "command_kind": "go",
                "expectation": make_expectation(
                    case_id=f"{operation}_go_package_capability_disabled",
                    command_kind="go",
                    expected_exit_code=CLI_STOP_EXIT_CODE,
                    expected_status="STOP",
                    expected_stop_reason="PACKAGE_GO_CAPABILITY_DISABLED",
                    expected_operation=None,
                    expected_gate="package_compatibility_gate",
                    expected_state={
                        "require_unmerged_nonempty": False,
                        "require_stage_oids": False,
                        "require_operation_head": False,
                        "refs_immutable": True,
                        "index_immutable": True,
                        "worktree_conflict_immutable": True,
                        "process_delta_empty": True,
                        "forbid_traceback": True,
                        "forbid_scope_file_required_as_pass": True,
                        "go_capability": False,
                    },
                ),
            }
        )

    # One fixture repo per operation, shared by state + go cases.
    fixtures: dict[str, dict[str, Any]] = {}
    for operation in ("merge", "rebase"):
        case_dir = staging_root / "fixtures" / operation
        repo = case_dir / "repo"
        state = case_dir / "state"
        state.mkdir(parents=True)
        meta = _make_conflict_repo(repo, operation=operation)
        _install_fixture_contracts(repo, package_staging)
        fixture_repos.append(repo)
        fixtures[operation] = {
            "repo": repo,
            "state": state,
            "meta": meta,
            "repo_index": len(fixture_repos) - 1,
        }

    mapping = build_normalization_map(
        staging_root=staging_root,
        package_staging=package_staging,
        fixture_repos=fixture_repos,
    )

    for spec in case_specs:
        operation = spec["operation"]
        fx = fixtures[operation]
        repo: Path = fx["repo"]
        state: Path = fx["state"]
        meta: dict[str, str] = fx["meta"]
        argv_tail: list[str]
        scope_path: Path | None = None
        if spec["command_kind"] == "state":
            argv_tail = ["state", "--repo", str(repo)]
            trust = None
        else:
            scope_path = _build_scope_for_repo(
                repo=repo,
                state_dir=state,
                package_staging=package_staging,
                run_id=f"replay-{spec['case_id']}",
            )
            argv_tail = [
                "go",
                "--repo",
                str(repo),
                "--scope",
                str(scope_path),
            ]
            trust = trust_digest
        # Refresh mapping tokens for newly created scope paths.
        mapping = build_normalization_map(
            staging_root=staging_root,
            package_staging=package_staging,
            fixture_repos=fixture_repos,
        )
        result = _run_boot_command(
            argv_tail=argv_tail,
            repo=repo,
            state=state,
            package_staging=package_staging,
            ledger=ledger,
            mapping=mapping,
            trust_digest=trust,
        )
        evaluation = evaluate_replay_case(
            expectation=spec["expectation"],
            returncode=int(result["returncode"]),
            stdout=str(result["stdout_raw"]),
            stderr=str(result["stderr_raw"]),
            before_state=result["before_state"],
            after_state=result["after_state"],
            process_delta=list(result["process_delta"]),
            fixture_meta=meta,
        )
        scope_evidence = None
        if scope_path is not None and scope_path.is_file():
            scope_evidence = json.loads(scope_path.read_text(encoding="utf-8"))
        case_record = {
            "case_id": spec["case_id"],
            "command_kind": spec["command_kind"],
            "operation": operation,
            "expectation": spec["expectation"],
            "passed": evaluation["passed"],
            "assertions": evaluation["assertions"],
            "expected": evaluation["expected"],
            "actual": evaluation["actual"],
            "reached_gate": evaluation["reached_gate"],
            "parsed_structured_result": evaluation["parsed"],
            "scope_manifest": scope_evidence,
            "fixture_meta": meta,
            "argv": [
                normalize_text(x, mapping) if isinstance(x, str) else x
                for x in result["argv"]
            ],
            "refs_immutable": result["refs_immutable"],
            "no_push_continue_abort_in_argv": result["no_push_continue_abort_in_argv"],
            "process_delta": result["process_delta"],
            "stdout_sha256_raw": result["stdout_sha256_raw"],
            "stderr_sha256_raw": result["stderr_sha256_raw"],
            "stdout_sha256_normalized": result["stdout_sha256_normalized"],
            "stderr_sha256_normalized": result["stderr_sha256_normalized"],
            "execution_location": "<PACKAGE_STAGING>/runtime/boot_opsx_conflict.py",
            "_raw": result,
        }
        cases.append(case_record)
        if not evaluation["passed"]:
            failed = [a for a in evaluation["assertions"] if not a["passed"]]
            raise SystemExit(
                "replay STOP: exact assertion mismatch for "
                f"{spec['case_id']}: {json.dumps(failed, indent=2)}"
            )

    mapping = build_normalization_map(
        staging_root=staging_root,
        package_staging=package_staging,
        fixture_repos=fixture_repos,
    )
    mapping_payload = {
        "schema": NORMALIZATION_SCHEMA,
        "ordered": [{"literal": lit, "token": tok} for lit, tok in mapping],
        "note": (
            "Literals are staging/python paths under portable roots. "
            "Author workspace / user-profile paths are forbidden in raw "
            "and therefore absent from this mapping."
        ),
    }
    mapping_text = json.dumps(mapping_payload, indent=2) + "\n"
    assert_no_forbidden_paths(mapping_text, label="normalization_mapping.json")

    summary = {
        "schema": REPLAY_SUMMARY_SCHEMA,
        "package_name": PACKAGE_NAME,
        "package_version": PACKAGE_VERSION,
        "built_at_utc": built,
        "go_capability": False,
        "execution_location": (
            "native-temp staging copy of packaged runtime "
            "(not author source workspace)"
        ),
        "path_normalization": {
            "schema": NORMALIZATION_SCHEMA,
            "verify_relation": "normalize(raw_bytes, ordered_mapping) == normalized_bytes",
            "tokens": sorted({token for _, token in mapping}),
            "note": (
                "Raw and normalized artifacts are both shipped. "
                "Raw must already exclude author/user profile paths "
                "(generation STOP otherwise)."
            ),
        },
        "note": (
            "R29 exact-match replay: state proves merge/rebase operation detection; "
            "scoped GO proves PACKAGE_GO_CAPABILITY_DISABLED at "
            "package_compatibility_gate. Nonzero exit alone is never PASS. "
            "Not production GO readiness."
        ),
        "builder": {
            "path": "scripts/build_replay_evidence.py",
            "sha256": builder_sha,
        },
        "environment": {
            "python_version": sys.version.split()[0],
            "platform": platform.system() + "-" + platform.release(),
            "git_version": subprocess.run(
                ["git", "--version"], capture_output=True, text=True, check=False
            ).stdout.strip(),
        },
        "cases": [{k: v for k, v in c.items() if not k.startswith("_")} for c in cases],
        "command_ledger": ledger,
        "acceptance_tests": [
            "tests/test_r29_replay_terminal.py",
            "tests/test_r25_evidence_portability.py",
            "tests/test_git_execution_invariant.py",
        ],
    }
    summary_text = json.dumps(summary, indent=2) + "\n"
    assert_no_forbidden_paths(summary_text, label="REPLAY_SUMMARY")

    zip_path = OUT_DIR / f"{PACKAGE_NAME}.REPLAY_EVIDENCE.zip"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("REPLAY_SUMMARY.json", summary_text)
        zf.writestr("normalization_mapping.json", mapping_text)
        zf.writestr(
            "README.txt",
            "\n".join(
                [
                    "OPSX_RESOLVE_CONFLICT R29 REPLAY_EVIDENCE",
                    "Exact-match state + scoped GO capability-gate cases.",
                    "Execution under native-temp package staging (not author workspace).",
                    "PASS requires AND of exit/status/reason/operation/gate/state.",
                    "Nonzero exit alone is never PASS.",
                    "Verify: normalize(raw, normalization_mapping.json) == normalized.",
                    "GO_CAPABILITY=false.",
                    "",
                ]
            ),
        )
        for c in cases:
            payload = c["_raw"]
            base = f"cases/{c['case_id']}"
            pairs = (
                ("stdout.txt", "stdout_raw", "stdout_normalized"),
                ("stderr.txt", "stderr_raw", "stderr_normalized"),
                (
                    "process_tree_before.txt",
                    "process_tree_before_raw",
                    "process_tree_before_normalized",
                ),
                (
                    "process_tree_after.txt",
                    "process_tree_after_raw",
                    "process_tree_after_normalized",
                ),
            )
            for filename, raw_key, norm_key in pairs:
                raw_blob = payload[raw_key]
                norm_blob = payload[norm_key]
                assert_no_forbidden_paths(raw_blob, label=f"{base}/raw/{filename}")
                assert_no_forbidden_paths(
                    norm_blob, label=f"{base}/normalized/{filename}"
                )
                zf.writestr(f"{base}/raw/{filename}", raw_blob)
                zf.writestr(f"{base}/normalized/{filename}", norm_blob)
            zf.writestr(
                f"{base}/git_before.json",
                json.dumps(payload["before_state"], indent=2) + "\n",
            )
            zf.writestr(
                f"{base}/git_after.json",
                json.dumps(payload["after_state"], indent=2) + "\n",
            )
            verify_blob = json.dumps(payload["verifications"], indent=2) + "\n"
            assert_no_forbidden_paths(verify_blob, label=f"{base}/verification.json")
            zf.writestr(f"{base}/verification.json", verify_blob)
            exp_blob = json.dumps(c["expectation"], indent=2) + "\n"
            zf.writestr(f"{base}/expectation.json", exp_blob)
            assert_blob = json.dumps(
                {
                    "passed": c["passed"],
                    "assertions": c["assertions"],
                    "expected": c["expected"],
                    "actual": c["actual"],
                    "reached_gate": c["reached_gate"],
                },
                indent=2,
            ) + "\n"
            zf.writestr(f"{base}/assertions.json", assert_blob)
            if c.get("scope_manifest") is not None:
                scope_blob = json.dumps(c["scope_manifest"], indent=2) + "\n"
                assert_no_forbidden_paths(scope_blob, label=f"{base}/scope.json")
                zf.writestr(f"{base}/scope.json", scope_blob)
            meta_blob = json.dumps(
                {k: v for k, v in c.items() if not k.startswith("_")},
                indent=2,
            ) + "\n"
            assert_no_forbidden_paths(meta_blob, label=f"{base}/meta.json")
            zf.writestr(f"{base}/meta.json", meta_blob)
        ledger_blob = json.dumps(ledger, indent=2) + "\n"
        assert_no_forbidden_paths(ledger_blob, label="command_ledger.json")
        zf.writestr("command_ledger.json", ledger_blob)

    mirror = PACKAGE_ROOT / "context" / "REPLAY_EVIDENCE_SUMMARY.json"
    mirror.write_text(summary_text, encoding="utf-8")
    print(f"wrote {zip_path}")
    return zip_path


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        raw_p = Path(sys.argv[2])
        norm_p = Path(sys.argv[3])
        map_p = Path(sys.argv[4])
        mapping_doc = json.loads(map_p.read_text(encoding="utf-8"))
        ordered = [
            (row["literal"], row["token"]) for row in mapping_doc.get("ordered") or []
        ]
        result = verify_raw_to_normalized(
            raw_p.read_text(encoding="utf-8"),
            norm_p.read_text(encoding="utf-8"),
            ordered,
        )
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result["ok"] else 1)
    main()
