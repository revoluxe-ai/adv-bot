"""Typed Git actions only — no generic read(args) (RC04-C01).

Git runs in a sealed config environment: no system/global config, no hooks,
no fsmonitor, and staging uses filter-free plumbing so validated bytes equal
stage-0 blob bytes.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Sequence

from .cancellation import run_process
from .errors import PolicyViolation, StopRequired
from .hashutil import sha256_text


def _git_bin() -> str:
    path = shutil.which("git")
    if not path:
        raise StopRequired("GIT_NOT_FOUND")
    return path


def _empty_hooks_dir() -> str:
    """Return the packaged empty hooks directory (no host temp mkdir)."""
    root = Path(__file__).resolve().parent / "empty_hooks"
    if not root.is_dir():
        raise StopRequired("EMPTY_HOOKS_DIR_MISSING", {"path": str(root)})
    return str(root)


def _git_binding_root() -> Path:
    """Return owner-local directory for immutable trusted Git copies."""
    explicit = os.environ.get("OPSX_CONFLICT_STATE", "").strip()
    if explicit:
        return (Path(explicit).expanduser().resolve() / "trusted-git-bin")
    return (Path.home() / ".opsx-resolve-conflict" / "trusted-git-bin").resolve()


def _lstat_component(path: Path) -> os.stat_result:
    """lstat one path component; FS errors → typed STOP."""
    try:
        return os.lstat(path)
    except OSError as exc:
        raise StopRequired(
            "GIT_TRUST_BIND_FAILED",
            {"path": str(path), "error": type(exc).__name__, "detail": str(exc)},
        ) from exc


def _assert_binding_ancestry_safe(path: Path) -> None:
    """Component-by-component lstat for every ancestor (no symlink follow)."""
    import stat as statmod

    abs_path = Path(os.path.abspath(str(path)))
    chain: list[Path] = []
    cur = abs_path
    while True:
        chain.append(cur)
        parent = cur.parent
        if parent == cur:
            break
        cur = parent
    for comp in reversed(chain):
        if not comp.exists():
            continue
        st = _lstat_component(comp)
        if statmod.S_ISLNK(st.st_mode):
            raise StopRequired(
                "GIT_TRUST_BIND_PATH_UNSAFE",
                {"path": str(comp), "reason": "symlink_component"},
            )
        if comp != abs_path and not statmod.S_ISDIR(st.st_mode):
            raise StopRequired(
                "GIT_TRUST_BIND_PATH_UNSAFE",
                {"path": str(comp), "reason": "component_not_dir"},
            )
        if os.name != "nt":
            if st.st_uid != os.getuid():
                raise StopRequired(
                    "GIT_TRUST_BIND_OWNER_MISMATCH",
                    {"path": str(comp), "uid": st.st_uid, "expected": os.getuid()},
                )
            mode = st.st_mode & 0o777
            if mode & 0o022:
                raise StopRequired(
                    "GIT_TRUST_BIND_PERMS_UNSAFE",
                    {"path": str(comp), "mode": oct(mode)},
                )


def _verify_bound_executable(*, path: str, digest: str) -> None:
    """Re-hash bound executable immediately before use (TOCTOU close)."""
    from .hashutil import sha256_bytes
    import stat as statmod

    bound = Path(path)
    try:
        st = os.lstat(bound)
        if statmod.S_ISLNK(st.st_mode) or not statmod.S_ISREG(st.st_mode):
            raise StopRequired(
                "GIT_TRUST_BOUND_PATH_INVALID",
                {"path": path, "reason": "pre_exec_not_regular"},
            )
        actual = sha256_bytes(bound.read_bytes())
    except StopRequired:
        raise
    except OSError as exc:
        raise StopRequired(
            "GIT_TRUST_BIND_FAILED",
            {
                "path": path,
                "error": type(exc).__name__,
                "reason": "pre_exec_unreadable",
            },
        ) from exc
    if actual.lower() != digest.lower():
        raise StopRequired(
            "GIT_TRUST_BOUND_DIGEST_MISMATCH",
            {
                "expected": digest.lower(),
                "actual": actual.lower(),
                "path": path,
                "reason": "pre_exec_digest",
            },
        )


# Sole Git process-launch primitive name (static inventory tests pin this).
_GIT_EXECUTION_PRIMITIVE = "_execute_trusted_git"


def _execute_trusted_git(
    *,
    executable: str,
    digest: str,
    args: Sequence[str],
    cwd: Path | str,
    env: dict[str, str] | None,
    timeout: float,
    input_data: bytes | None = None,
    text: bool = True,
) -> subprocess.CompletedProcess[Any]:
    """Sole Git process launch: verify bound executable, then spawn.

    All Git ``subprocess.run`` / ``run_process`` calls in this module MUST go
    through this function. Supervised ``run_process`` is used for text
    launches without stdin (cancellation / process-group semantics). Stdin
    plumbing and binary stdout use ``subprocess.run`` after the same
    pre-exec verify (``run_process`` is text-oriented).
    """
    _reject_dangerous_options(args)
    _verify_bound_executable(path=executable, digest=digest)
    argv = [executable, *list(args)]
    try:
        if input_data is not None or not text:
            return subprocess.run(
                argv,
                cwd=str(cwd),
                env=env,
                input=input_data,
                capture_output=True,
                check=False,
                shell=False,
                timeout=timeout,
                text=text,
            )
        return run_process(
            argv,
            cwd=cwd,
            env=env,
            timeout=timeout,
            text=True,
        )
    except StopRequired:
        raise
    except (OSError, subprocess.SubprocessError) as exc:
        raise StopRequired(
            "GIT_EXEC_SPAWN_FAILED",
            {
                "argv": argv,
                "error": type(exc).__name__,
                "detail": str(exc),
            },
        ) from exc


def _bind_trusted_git_executable(*, executable: str, digest: str) -> str:
    """Atomically publish trusted Git bytes; FS/TOCTOU failures → typed STOP.

    Uses exclusive create (O_EXCL), component lstat, and post-publish digest.
    Does not mutate the repository under test.
    """
    from .hashutil import sha256_bytes
    import stat as statmod

    try:
        source = Path(executable)
        st_src = _lstat_component(source)
        if statmod.S_ISLNK(st_src.st_mode) or not statmod.S_ISREG(st_src.st_mode):
            raise StopRequired(
                "GIT_TRUST_SOURCE_INVALID",
                {"path": str(source)},
            )
        try:
            data = source.read_bytes()
        except OSError as exc:
            raise StopRequired(
                "GIT_TRUST_BIND_FAILED",
                {
                    "path": str(source),
                    "error": type(exc).__name__,
                    "detail": str(exc),
                    "reason": "source_unreadable",
                },
            ) from exc
        source_digest = sha256_bytes(data)
        if source_digest.lower() != digest.lower():
            raise StopRequired(
                "GIT_TRUST_SOURCE_DIGEST_MISMATCH",
                {
                    "expected": digest.lower(),
                    "actual": source_digest.lower(),
                    "path": str(source),
                },
            )

        bind_root = _git_binding_root()
        bind_root.mkdir(parents=True, exist_ok=True)
        _assert_binding_ancestry_safe(bind_root)
        bind_dir = bind_root / digest.lower()
        bind_dir.mkdir(parents=True, exist_ok=True)
        _assert_binding_ancestry_safe(bind_dir)
        if os.name != "nt":
            try:
                bind_dir.chmod(0o700)
            except OSError as exc:
                raise StopRequired(
                    "GIT_TRUST_BIND_FAILED",
                    {
                        "path": str(bind_dir),
                        "error": type(exc).__name__,
                        "reason": "chmod_failed",
                    },
                ) from exc

        bound = bind_dir / source.name
        _assert_binding_ancestry_safe(bound)
        if bound.exists():
            st_b = _lstat_component(bound)
            if statmod.S_ISLNK(st_b.st_mode) or not statmod.S_ISREG(st_b.st_mode):
                raise StopRequired(
                    "GIT_TRUST_BOUND_PATH_INVALID",
                    {"path": str(bound)},
                )
            try:
                existing = bound.read_bytes()
            except OSError as exc:
                raise StopRequired(
                    "GIT_TRUST_BIND_FAILED",
                    {
                        "path": str(bound),
                        "error": type(exc).__name__,
                        "reason": "bound_unreadable",
                    },
                ) from exc
            if sha256_bytes(existing).lower() != digest.lower():
                raise StopRequired(
                    "GIT_TRUST_BOUND_DIGEST_MISMATCH",
                    {
                        "expected": digest.lower(),
                        "actual": sha256_bytes(existing).lower(),
                        "path": str(bound),
                    },
                )
            return str(bound)

        # Exclusive create: O_CREAT|O_EXCL prevents symlink replace races.
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY
        tmp = bind_dir / f".{source.name}.{os.getpid()}.{os.urandom(4).hex()}.tmp"
        try:
            fd = os.open(str(tmp), flags, 0o500 if os.name != "nt" else 0o600)
        except FileExistsError as exc:
            raise StopRequired(
                "GIT_TRUST_BIND_TMP_UNSAFE",
                {"path": str(tmp), "reason": "tmp_exists_race"},
            ) from exc
        except OSError as exc:
            raise StopRequired(
                "GIT_TRUST_BIND_FAILED",
                {
                    "path": str(tmp),
                    "error": type(exc).__name__,
                    "reason": "exclusive_create_failed",
                },
            ) from exc
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, bound)
        except OSError as exc:
            try:
                if tmp.exists() and not tmp.is_symlink():
                    tmp.unlink()
            except OSError:
                pass
            raise StopRequired(
                "GIT_TRUST_BIND_FAILED",
                {
                    "path": str(bound),
                    "error": type(exc).__name__,
                    "detail": str(exc),
                    "reason": "atomic_publish_failed",
                },
            ) from exc

        _verify_bound_executable(path=str(bound), digest=digest)
        return str(bound)
    except StopRequired:
        raise
    except (OSError, PermissionError) as exc:
        raise StopRequired(
            "GIT_TRUST_BIND_FAILED",
            {"error": type(exc).__name__, "detail": str(exc)},
        ) from exc


def resolve_trusted_git() -> dict[str, str]:
    """Resolve Git and enforce trust binding **before** any Git invocation.

    Owner must set ``OPSX_CONFLICT_GIT_TRUST_DIGEST`` to the approved executable
    SHA-256. Unbound mode is not available in production code.
    """
    from .hashutil import sha256_bytes

    if os.environ.get("OPSX_CONFLICT_GIT_TRUST_UNBOUND", "").strip() == "1":
        raise StopRequired(
            "GIT_TRUST_UNBOUND_FORBIDDEN",
            {
                "hint": (
                    "remove OPSX_CONFLICT_GIT_TRUST_UNBOUND; "
                    "pin OPSX_CONFLICT_GIT_TRUST_DIGEST"
                ),
            },
        )
    executable = _git_bin()
    path = Path(executable)
    try:
        if path.is_symlink() or not path.is_file():
            raise StopRequired("GIT_EXECUTABLE_NOT_FILE", {"path": executable})
        digest = sha256_bytes(path.read_bytes())
    except StopRequired:
        raise
    except (OSError, PermissionError) as exc:
        raise StopRequired(
            "GIT_TRUST_BIND_FAILED",
            {
                "path": executable,
                "error": type(exc).__name__,
                "detail": str(exc),
                "reason": "executable_unreadable",
            },
        ) from exc
    approved = os.environ.get("OPSX_CONFLICT_GIT_TRUST_DIGEST", "").strip().lower()
    if not approved:
        raise StopRequired(
            "GIT_TRUST_DIGEST_REQUIRED",
            {
                "executable": executable,
                "sha256": digest,
                "hint": "set OPSX_CONFLICT_GIT_TRUST_DIGEST before Git use",
            },
        )
    if digest.lower() != approved:
        raise StopRequired(
            "GIT_TRUST_DIGEST_MISMATCH",
            {"expected": approved, "got": digest, "executable": executable},
        )
    try:
        bound_executable = _bind_trusted_git_executable(
            executable=executable,
            digest=digest,
        )
    except StopRequired:
        raise
    except (OSError, PermissionError) as exc:
        raise StopRequired(
            "GIT_TRUST_BIND_FAILED",
            {"error": type(exc).__name__, "detail": str(exc)},
        ) from exc
    _verify_bound_executable(path=bound_executable, digest=digest)
    trust = "DIGEST_BOUND"
    version = "unknown"
    # Version probe runs against the immutable bound executable via sole launch.
    try:
        proc = _execute_trusted_git(
            executable=bound_executable,
            digest=digest,
            args=["--version"],
            cwd=Path.cwd(),
            env=None,
            timeout=10.0,
            text=True,
        )
        version = (proc.stdout or proc.stderr or "").strip().splitlines()[0]
    except StopRequired:
        raise
    except (OSError, subprocess.SubprocessError, IndexError):
        version = "unknown"
    return {
        "executable": executable,
        "bound_executable": bound_executable,
        "version": version,
        "sha256": digest,
        "trust": trust,
        "optional_locks": "0",
        "hooks_path": _empty_hooks_dir(),
    }


def git_executable_identity() -> dict[str, str]:
    """Return path/version/digest evidence for the resolved Git executable."""
    return resolve_trusted_git()


def git_safe_env(repo_root: Path) -> dict[str, str]:
    """Build a sealed Git environment that disables external process drivers."""
    null_path = os.devnull
    hooks = _empty_hooks_dir()
    env = {
        "PATH": os.environ.get("PATH", ""),
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_PAGER": "cat",
        "PAGER": "cat",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": null_path,
        "GIT_CONFIG_SYSTEM": null_path,
        "GIT_CONFIG_COUNT": "8",
        "GIT_CONFIG_KEY_0": "core.pager",
        "GIT_CONFIG_VALUE_0": "cat",
        "GIT_CONFIG_KEY_1": "diff.external",
        "GIT_CONFIG_VALUE_1": "",
        "GIT_CONFIG_KEY_2": "core.quotepath",
        "GIT_CONFIG_VALUE_2": "false",
        "GIT_CONFIG_KEY_3": "core.hooksPath",
        "GIT_CONFIG_VALUE_3": hooks,
        "GIT_CONFIG_KEY_4": "core.fsmonitor",
        "GIT_CONFIG_VALUE_4": "",
        "GIT_CONFIG_KEY_5": "core.useBuiltinFSMonitor",
        "GIT_CONFIG_VALUE_5": "false",
        "GIT_CONFIG_KEY_6": "core.attributesFile",
        "GIT_CONFIG_VALUE_6": null_path,
        # Match Windows host EOL handling for status/diff checks. Staging still
        # uses filter-free plumbing with exact validated bytes.
        "GIT_CONFIG_KEY_7": "core.autocrlf",
        "GIT_CONFIG_VALUE_7": "true",
        "LANG": os.environ.get("LANG", "C"),
        "LC_ALL": os.environ.get("LC_ALL", "C"),
    }
    for key in (
        "WINDIR",
        "SYSTEMROOT",
        "TMP",
        "TEMP",
        "USERPROFILE",
        "HOME",
        "HOMEDRIVE",
        "HOMEPATH",
    ):
        if key in os.environ:
            env[key] = os.environ[key]
    return env


def _reject_dangerous_options(args: Sequence[str]) -> None:
    banned = {"--output", "--ext-diff", "--textconv"}
    for a in args:
        base = a.split("=", 1)[0]
        if base in banned or a.startswith("--output="):
            raise PolicyViolation(f"forbidden git option: {a}")


class TypedGit:
    """Closed set of Git read/mutation helpers with fixed argv templates."""

    def __init__(self, repo_root: Path, ledger: Any | None = None) -> None:
        self.repo_root = repo_root.resolve()
        self.ledger = ledger
        # Trust gate runs before any later Git subprocess from this instance.
        self.git_identity = resolve_trusted_git()
        self.git_bin = self.git_identity.get(
            "bound_executable",
            self.git_identity["executable"],
        )
        self.git_digest = str(self.git_identity.get("sha256", ""))

    def _run(
        self,
        args: list[str],
        *,
        timeout: float = 60.0,
        allow_nonzero: bool = False,
        env: dict[str, str] | None = None,
    ):
        argv = [self.git_bin, *args]
        if self.ledger is not None:
            self.ledger.append("COMMAND_START", {"kind": "git_typed", "argv": argv})
        result = _execute_trusted_git(
            executable=self.git_bin,
            digest=self.git_digest,
            args=args,
            cwd=self.repo_root,
            env=env or git_safe_env(self.repo_root),
            timeout=timeout,
            text=True,
        )
        if self.ledger is not None:
            self.ledger.append(
                "COMMAND_END",
                {
                    "kind": "git_typed",
                    "argv": argv,
                    "returncode": result.returncode,
                    "stdout_sha256": sha256_text(result.stdout),
                    "stderr_sha256": sha256_text(result.stderr),
                },
            )
        if result.returncode != 0 and not allow_nonzero:
            raise StopRequired(
                "GIT_READ_FAILED",
                {
                    "argv": argv,
                    "returncode": result.returncode,
                    "stderr": result.stderr[-3000:],
                },
            )
        return result

    def rev_parse_head(self) -> str:
        return self._run(["rev-parse", "HEAD"]).stdout.strip()

    def rev_parse(self, rev: str) -> str:
        if not rev or rev.startswith("-"):
            raise PolicyViolation("invalid rev")
        return self._run(["rev-parse", rev], allow_nonzero=True).stdout.strip()

    def commit_message(self, oid: str) -> str:
        """Read the full message of one validated commit object."""
        if not oid or oid.startswith("-") or len(oid) not in {40, 64}:
            raise PolicyViolation("invalid commit oid")
        return self._run(["show", "-s", "--format=%B", oid]).stdout

    def branch_show_current(self) -> str:
        return self._run(["branch", "--show-current"], allow_nonzero=True).stdout.strip()

    def status_porcelain_v2_z(self) -> str:
        return self._run(["status", "--porcelain=v2", "-z", "--branch"]).stdout

    def ls_files_unmerged_z(self) -> str:
        return self._run(["ls-files", "-u", "-z"]).stdout

    def ls_files_z(self) -> str:
        """List tracked paths (NUL-delimited)."""
        return self._run(["ls-files", "-z"]).stdout

    def ls_files_stage_path_z(self, path: str) -> str:
        """Return the exact stage-0 index record for one safe path."""
        if not path or path.startswith("-"):
            raise PolicyViolation("invalid stage path")
        return self._run(["ls-files", "--stage", "-z", "--", path]).stdout

    def object_format(self) -> str:
        """Return the repository object hash format."""
        value = self._run(["rev-parse", "--show-object-format"]).stdout.strip()
        if value not in {"sha1", "sha256"}:
            raise StopRequired("GIT_OBJECT_FORMAT_UNSUPPORTED", {"format": value})
        return value

    def hash_bytes_no_filters(self, data: bytes) -> str:
        """Hash raw bytes into the object store without clean filters."""
        args = ["hash-object", "-w", "--stdin", "--no-filters"]
        argv = [self.git_bin, *args]
        if self.ledger is not None:
            self.ledger.append("COMMAND_START", {"kind": "git_typed", "argv": argv})
        completed = _execute_trusted_git(
            executable=self.git_bin,
            digest=self.git_digest,
            args=args,
            cwd=self.repo_root,
            env=git_safe_env(self.repo_root),
            timeout=60.0,
            input_data=data,
            text=False,
        )
        stdout = completed.stdout.decode("utf-8", "replace")
        stderr = completed.stderr.decode("utf-8", "replace")
        if self.ledger is not None:
            self.ledger.append(
                "COMMAND_END",
                {
                    "kind": "git_typed",
                    "argv": argv,
                    "returncode": completed.returncode,
                    "stdout_sha256": sha256_text(stdout),
                    "stderr_sha256": sha256_text(stderr),
                },
            )
        oid = stdout.strip()
        if completed.returncode != 0 or len(oid) not in {40, 64}:
            raise StopRequired(
                "GIT_HASH_OBJECT_INVALID",
                {"oid": oid, "stderr": stderr[-1000:]},
            )
        return oid

    def hash_worktree_path(self, path: str) -> str:
        """Hash one worktree file without clean filters (raw bytes)."""
        if not path or path.startswith("-"):
            raise PolicyViolation("invalid hash-object path")
        target = self.repo_root / path
        if not target.is_file():
            raise StopRequired("GIT_HASH_OBJECT_MISSING", {"path": path})
        return self.hash_bytes_no_filters(target.read_bytes())

    def cat_file_blob_bytes(self, oid: str) -> bytes:
        """Read raw blob bytes by object ID."""
        if not oid or oid.startswith("-") or len(oid) not in {40, 64}:
            raise PolicyViolation(f"invalid blob oid: {oid}")
        args = ["cat-file", "blob", oid]
        argv = [self.git_bin, *args]
        if self.ledger is not None:
            self.ledger.append("COMMAND_START", {"kind": "git_typed", "argv": argv})
        completed = _execute_trusted_git(
            executable=self.git_bin,
            digest=self.git_digest,
            args=args,
            cwd=self.repo_root,
            env=git_safe_env(self.repo_root),
            timeout=60.0,
            text=False,
        )
        if self.ledger is not None:
            self.ledger.append(
                "COMMAND_END",
                {
                    "kind": "git_typed",
                    "argv": argv,
                    "returncode": completed.returncode,
                    "stdout_sha256": sha256_text(
                        completed.stdout.decode("utf-8", "replace")
                        if completed.returncode != 0
                        else ""
                    ),
                    "stderr_sha256": sha256_text(
                        completed.stderr.decode("utf-8", "replace")
                    ),
                },
            )
        if completed.returncode != 0:
            raise StopRequired(
                "GIT_CAT_FILE_FAILED",
                {
                    "oid": oid,
                    "stderr": completed.stderr.decode("utf-8", "replace")[-1000:],
                },
            )
        return completed.stdout

    def diff_name_status_z(self) -> str:
        return self._run(
            ["diff", "--name-status", "-z", "--no-ext-diff", "--no-textconv"],
            allow_nonzero=True,
        ).stdout

    def diff_cached_name_status_z(self) -> str:
        return self._run(
            [
                "diff",
                "--cached",
                "--name-status",
                "-z",
                "--no-ext-diff",
                "--no-textconv",
            ],
            allow_nonzero=True,
        ).stdout

    def diff_tree_name_status_z(self, old: str, new: str) -> str:
        """Return rename-aware NUL-delimited commit-to-commit path changes."""
        for rev in (old, new):
            if not rev or rev.startswith("-"):
                raise PolicyViolation("invalid diff tree revision")
        return self._run(
            [
                "diff",
                "--name-status",
                "-z",
                "-M",
                "--no-ext-diff",
                "--no-textconv",
                old,
                new,
            ],
            allow_nonzero=True,
        ).stdout

    def diff_check_paths(self, paths: Sequence[str]) -> str:
        safe = [p for p in paths if p and not str(p).startswith("-")]
        return self._run(
            ["diff", "--check", "--no-ext-diff", "--no-textconv", "--", *safe],
            allow_nonzero=True,
        ).stdout

    def diff_cached_paths(self, paths: Sequence[str]) -> str:
        """Return the actual staged binary/full-index diff for exact paths."""
        safe = [p for p in paths if p and not str(p).startswith("-")]
        if len(safe) != len(paths):
            raise PolicyViolation("invalid staged diff path")
        return self._run(
            [
                "diff",
                "--cached",
                "--binary",
                "--full-index",
                "--no-ext-diff",
                "--no-textconv",
                "--",
                *safe,
            ],
            allow_nonzero=True,
        ).stdout

    def cat_file_blob(self, oid: str) -> str:
        """Read blob contents by object ID (UTF-8 replace)."""
        return self.cat_file_blob_bytes(oid).decode("utf-8", "replace")

    def merge_base(self, a: str, b: str) -> str:
        r = self._run(["merge-base", a, b], allow_nonzero=True)
        if r.returncode != 0:
            raise StopRequired("MERGE_BASE_UNAVAILABLE")
        return r.stdout.strip()

    def merge_base_all(self, a: str, b: str) -> list[str]:
        r = self._run(["merge-base", "--all", a, b], allow_nonzero=True)
        if r.returncode != 0:
            return []
        return [x for x in r.stdout.splitlines() if x.strip()]

    def git_dir(self) -> Path:
        out = self._run(["rev-parse", "--git-dir"]).stdout.strip()
        p = Path(out)
        return p if p.is_absolute() else (self.repo_root / p).resolve()

    def _stage_exact(self, paths: Sequence[str]) -> None:
        """Stage exact worktree bytes via filter-free object plumbing."""
        if not paths:
            raise PolicyViolation("empty stage list")
        for path in paths:
            if not path or str(path).startswith("-"):
                raise PolicyViolation(f"invalid stage path: {path}")
            target = self.repo_root / path
            if not target.is_file():
                raise StopRequired("STAGE_TARGET_MISSING", {"path": path})
            data = target.read_bytes()
            oid = self.hash_bytes_no_filters(data)
            mode = "100755" if os.access(target, os.X_OK) else "100644"
            # Prefer explicit mode from caller via update-index; executable bit
            # is refined by orchestrator expected_mode after staging.
            self._run(
                [
                    "update-index",
                    "--add",
                    "--cacheinfo",
                    f"{mode},{oid},{path}",
                ],
                timeout=60.0,
            )

    def _run_index_info(self, index_info: str) -> None:
        """Feed ``update-index --index-info`` to restore unmerged stages."""
        args = ["update-index", "--index-info"]
        argv = [self.git_bin, *args]
        if self.ledger is not None:
            self.ledger.append("COMMAND_START", {"kind": "git_typed", "argv": argv})
        completed = _execute_trusted_git(
            executable=self.git_bin,
            digest=self.git_digest,
            args=args,
            cwd=self.repo_root,
            env=git_safe_env(self.repo_root),
            timeout=60.0,
            input_data=index_info.encode("utf-8"),
            text=False,
        )
        stdout = completed.stdout.decode("utf-8", "replace")
        stderr = completed.stderr.decode("utf-8", "replace")
        if self.ledger is not None:
            self.ledger.append(
                "COMMAND_END",
                {
                    "kind": "git_typed",
                    "argv": argv,
                    "returncode": completed.returncode,
                    "stdout_sha256": sha256_text(stdout),
                    "stderr_sha256": sha256_text(stderr),
                },
            )
        if completed.returncode != 0:
            raise StopRequired(
                "GIT_INDEX_INFO_FAILED",
                {"stderr": stderr[-1000:]},
            )

    def stage_validated_bytes(
        self,
        *,
        path: str,
        data: bytes,
        mode: str,
    ) -> str:
        """Stage exact validated bytes and return the stage-0 blob OID."""
        if not path or path.startswith("-"):
            raise PolicyViolation(f"invalid stage path: {path}")
        if mode not in {"100644", "100755", "120000"}:
            raise PolicyViolation(f"invalid stage mode: {mode}")
        oid = self.hash_bytes_no_filters(data)
        self._run(
            [
                "update-index",
                "--add",
                "--cacheinfo",
                f"{mode},{oid},{path}",
            ],
            timeout=60.0,
        )
        return oid

    def _continue(self, operation: str) -> None:
        """Forbidden in r06 default flow (CF-003) — commit-producing."""
        raise PolicyViolation(f"GIT_CONTINUE_FORBIDDEN:{operation}")


def read(*_a, **_k):
    raise PolicyViolation("GitClient.read removed; use TypedGit typed actions only")
