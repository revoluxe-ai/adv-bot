"""Closed read-only Git operations for Windows PREVIEW_ONLY (R34).

Exact operation IDs only — no caller-controlled argv. Uses the package
``resolve_trusted_git`` / ``git_safe_env`` contracts without modifying
``git_typed.py``. Does not claim verify-to-spawn atomicity (R25-MEDIUM-002 open).
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import StopRequired
from .git_typed import git_safe_env, resolve_trusted_git
from .hashutil import sha256_bytes

SEALED_ENV_POLICY_VERSION = "opsx-preview-git-env/v1"

# Exact argv templates compiled from operation IDs (no caller flags).
_OP_RESOLVE_GIT_DIR = "resolve_git_dir"
_OP_RESOLVE_HEAD = "resolve_head"
_OP_READ_REFS = "read_refs"
_OP_READ_UNMERGED = "read_unmerged_index"
_OP_READ_STAGE_BLOB = "read_stage_blob"

_KNOWN_OPERATIONS = frozenset(
    {
        _OP_RESOLVE_GIT_DIR,
        _OP_RESOLVE_HEAD,
        _OP_READ_REFS,
        _OP_READ_UNMERGED,
        _OP_READ_STAGE_BLOB,
    }
)

# Git object id: full SHA-1 (40) or SHA-256 (64) hex only.
_OID_RE = re.compile(r"^[0-9a-fA-F]{40}$|^[0-9a-fA-F]{64}$")

# Ambient redirect / config / diff drivers that must never reach the child.
_STRIP_ENV_KEYS = frozenset(
    {
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_COMMON_DIR",
        "GIT_CONFIG",
        "GIT_EXTERNAL_DIFF",
        "GIT_DIFF_OPTS",
        "GIT_TRACE",
        "GIT_TRACE2",
        "GIT_TRACE_PERFORMANCE",
        "GIT_TRACE_PACK_ACCESS",
        "GIT_TRACE_SETUP",
        "GIT_TRACE_SHALLOW",
        "GIT_EXEC_PATH",
        "GIT_NAMESPACE",
        "GIT_CEILING_DIRECTORIES",
    }
)


def normalize_blob_oid(oid: str) -> str:
    """Validate and normalize a full Git blob object id.

    Raises:
        StopRequired: revision expressions, short ids, or non-hex rejected.
    """
    raw = (oid or "").strip()
    if not raw or not _OID_RE.fullmatch(raw):
        raise StopRequired(
            "PREVIEW_INVALID_BLOB_OID",
            {"oid": raw[:120], "hint": "full hex SHA-1 (40) or SHA-256 (64) only"},
        )
    for ch in ("^", "~", ":", "@", "{", "}", "/", ".", " "):
        if ch in raw:
            raise StopRequired(
                "PREVIEW_INVALID_BLOB_OID",
                {"oid": raw[:120], "reason": "revision_expression"},
            )
    return raw.lower()


def compile_operation_argv(
    operation_id: str, *, blob_oid: str | None = None
) -> list[str]:
    """Compile a package-owned operation ID to exact Git argv (no flags)."""
    if operation_id not in _KNOWN_OPERATIONS:
        raise StopRequired(
            "PREVIEW_UNKNOWN_OPERATION",
            {"operation_id": operation_id, "known": sorted(_KNOWN_OPERATIONS)},
        )
    if operation_id == _OP_RESOLVE_GIT_DIR:
        return ["rev-parse", "--git-dir"]
    if operation_id == _OP_RESOLVE_HEAD:
        return ["rev-parse", "HEAD"]
    if operation_id == _OP_READ_REFS:
        return ["show-ref"]
    if operation_id == _OP_READ_UNMERGED:
        return ["ls-files", "--unmerged", "-z"]
    if operation_id == _OP_READ_STAGE_BLOB:
        oid = normalize_blob_oid(blob_oid or "")
        return ["cat-file", "blob", oid]
    raise StopRequired("PREVIEW_UNKNOWN_OPERATION", {"operation_id": operation_id})


@dataclass
class CommandLedgerEntry:
    """One closed preview Git invocation for evidence (not an atomicity claim)."""

    operation_id: str
    argv: list[str]
    executable_path: str
    expected_executable_digest: str
    observed_pre_exec_digest: str
    sealed_environment_policy_version: str
    returncode: int
    stdout_sha256: str
    stderr_sha256: str


@dataclass
class PreviewReadonlyGit:
    """Preview Git runner: exact operations only, trusted bound executable."""

    repo_root: Path
    ledger: list[CommandLedgerEntry] = field(default_factory=list)
    _bound_executable: str = ""
    _expected_digest: str = ""
    _source_executable: str = ""

    def __post_init__(self) -> None:
        """Resolve trusted Git binding and canonicalize repository path."""
        root = Path(self.repo_root).resolve()
        object.__setattr__(self, "repo_root", root)
        identity = resolve_trusted_git()
        object.__setattr__(self, "_bound_executable", identity["bound_executable"])
        object.__setattr__(self, "_expected_digest", identity["sha256"].lower())
        object.__setattr__(self, "_source_executable", identity["executable"])

    def _sealed_env(self) -> dict[str, str]:
        """Build sealed env from package git_safe_env; strip redirect vars."""
        env = dict(git_safe_env(self.repo_root))
        for key in _STRIP_ENV_KEYS:
            env.pop(key, None)
        # Ambient GIT_CONFIG_KEY_* from parent never enter — git_safe_env is
        # a fresh dict. Re-assert location redirects are absent.
        for key in (
            "GIT_DIR",
            "GIT_WORK_TREE",
            "GIT_INDEX_FILE",
            "GIT_OBJECT_DIRECTORY",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES",
            "GIT_COMMON_DIR",
        ):
            env.pop(key, None)
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GIT_OPTIONAL_LOCKS"] = "0"
        return env

    def _pre_exec_digest(self) -> str:
        """Re-hash bound executable immediately before spawn (not atomic)."""
        path = Path(self._bound_executable)
        try:
            actual = sha256_bytes(path.read_bytes()).lower()
        except OSError as exc:
            raise StopRequired(
                "PREVIEW_GIT_EXECUTABLE_UNREADABLE",
                {
                    "path": self._bound_executable,
                    "error": type(exc).__name__,
                },
            ) from exc
        if actual != self._expected_digest:
            raise StopRequired(
                "PREVIEW_GIT_EXECUTABLE_DIGEST_MISMATCH",
                {
                    "expected": self._expected_digest,
                    "observed": actual,
                    "path": self._bound_executable,
                    "note": "R25-MEDIUM-002 remains open; not an atomicity claim",
                },
            )
        return actual

    def _spawn(
        self,
        *,
        operation_id: str,
        argv: list[str],
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        """Spawn bound Git with exact argv against resolved repo_root."""
        observed = self._pre_exec_digest()
        env = self._sealed_env()
        for key in (
            "GIT_DIR",
            "GIT_WORK_TREE",
            "GIT_INDEX_FILE",
            "GIT_OBJECT_DIRECTORY",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES",
            "GIT_COMMON_DIR",
        ):
            if key in env:
                raise StopRequired(
                    "PREVIEW_GIT_ENV_REDIRECT_PRESENT",
                    {"key": key},
                )
        full_argv = [self._bound_executable, *argv]
        proc = subprocess.run(
            full_argv,
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            env=env,
        )
        out_sha = hashlib.sha256((proc.stdout or "").encode("utf-8")).hexdigest()
        err_sha = hashlib.sha256((proc.stderr or "").encode("utf-8")).hexdigest()
        self.ledger.append(
            CommandLedgerEntry(
                operation_id=operation_id,
                argv=list(argv),
                executable_path=self._bound_executable,
                expected_executable_digest=self._expected_digest,
                observed_pre_exec_digest=observed,
                sealed_environment_policy_version=SEALED_ENV_POLICY_VERSION,
                returncode=proc.returncode,
                stdout_sha256=out_sha,
                stderr_sha256=err_sha,
            )
        )
        if check and proc.returncode != 0:
            raise StopRequired(
                "PREVIEW_GIT_COMMAND_FAILED",
                {
                    "operation_id": operation_id,
                    "argv": list(argv),
                    "returncode": proc.returncode,
                    "stderr": (proc.stderr or "")[:400],
                },
            )
        return proc

    def resolve_git_dir(self) -> str:
        """Return ``git rev-parse --git-dir`` relative/absolute path text."""
        proc = self._spawn(
            operation_id=_OP_RESOLVE_GIT_DIR,
            argv=compile_operation_argv(_OP_RESOLVE_GIT_DIR),
            check=True,
        )
        return (proc.stdout or "").strip()

    def resolve_head(self) -> str:
        """Return ``git rev-parse HEAD``."""
        proc = self._spawn(
            operation_id=_OP_RESOLVE_HEAD,
            argv=compile_operation_argv(_OP_RESOLVE_HEAD),
            check=True,
        )
        return (proc.stdout or "").strip()

    def read_refs(self) -> str:
        """Return ``git show-ref`` stdout (empty refs → empty string, no STOP)."""
        proc = self._spawn(
            operation_id=_OP_READ_REFS,
            argv=compile_operation_argv(_OP_READ_REFS),
            check=False,
        )
        return proc.stdout or ""

    def read_unmerged_index(self) -> str:
        """Return ``git ls-files --unmerged -z`` payload."""
        proc = self._spawn(
            operation_id=_OP_READ_UNMERGED,
            argv=compile_operation_argv(_OP_READ_UNMERGED),
            check=True,
        )
        return proc.stdout or ""

    def read_stage_blob(self, oid: str) -> str:
        """Return blob bytes as text for a validated full hex object id."""
        argv = compile_operation_argv(_OP_READ_STAGE_BLOB, blob_oid=oid)
        proc = self._spawn(
            operation_id=_OP_READ_STAGE_BLOB,
            argv=argv,
            check=True,
        )
        return proc.stdout or ""

    def ledger_as_dicts(self) -> list[dict[str, Any]]:
        """Serialize command ledger for preview report embedding."""
        return [
            {
                "operation_id": e.operation_id,
                "argv": e.argv,
                "executable_path": e.executable_path,
                "expected_executable_digest": e.expected_executable_digest,
                "observed_pre_exec_digest": e.observed_pre_exec_digest,
                "sealed_environment_policy_version": e.sealed_environment_policy_version,
                "returncode": e.returncode,
                "stdout_sha256": e.stdout_sha256,
                "stderr_sha256": e.stderr_sha256,
                "atomicity_claim": False,
                "r25_medium_002_open": True,
            }
            for e in self.ledger
        ]

    def assert_ledger_has_no_mutations(self) -> None:
        """Post-condition: only known read-only operation IDs appear."""
        for e in self.ledger:
            if e.operation_id not in _KNOWN_OPERATIONS:
                raise StopRequired(
                    "PREVIEW_LEDGER_UNKNOWN_OPERATION",
                    {"operation_id": e.operation_id},
                )
            expected = compile_operation_argv(
                e.operation_id,
                blob_oid=e.argv[-1] if e.operation_id == _OP_READ_STAGE_BLOB else None,
            )
            if e.argv != expected:
                raise StopRequired(
                    "PREVIEW_LEDGER_ARGV_DRIFT",
                    {
                        "operation_id": e.operation_id,
                        "argv": e.argv,
                        "expected": expected,
                    },
                )
            for bad in (
                "add",
                "commit",
                "push",
                "checkout",
                "merge",
                "rebase",
                "config",
                "symbolic-ref",
                "diff",
                "show",
                "status",
                "merge-base",
            ):
                if bad in e.argv:
                    raise StopRequired(
                        "PREVIEW_LEDGER_MUTATION",
                        {"argv": e.argv, "token": bad},
                    )
