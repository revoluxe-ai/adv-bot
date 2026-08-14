"""Race-safe scoped writes preserving content and supported file metadata.

The writer first prepares a same-directory inode, atomically claims the current
target by rename, verifies the claimed inode, and installs with hard-link
``no-replace`` semantics. A concurrent path writer therefore wins without its
content being overwritten. The claimed original is locked until commit/rollback.
"""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
import shutil
from pathlib import Path
import stat
from typing import BinaryIO, Iterator
from uuid import uuid4

from .errors import StopRequired
from .hashutil import sha256_bytes
from .pathsafety import prepare_new_path_under_repo, resolve_under_repo
from .process_surfaces import classify_path_risk, is_protected_process_path
from .proofs import Proof
from .scope import ScopeManifest


def detect_newline(data: bytes) -> bytes:
    """Return dominant newline sequence for the file (CRLF or LF)."""
    if b"\r\n" in data:
        return b"\r\n"
    return b"\n"


def encode_with_newline(text: str, newline: bytes) -> bytes:
    """Normalize logical newlines then re-emit with original policy."""
    logical = text.replace("\r\n", "\n").replace("\r", "\n")
    if newline == b"\r\n":
        return logical.replace("\n", "\r\n").encode("utf-8")
    return logical.encode("utf-8")


def assert_no_conflict_markers(text: str, *, path: str) -> None:
    """Reject unresolved conflict markers in written content."""
    for marker in ("<<<<<<<", "=======", ">>>>>>>"):
        if marker in text:
            raise StopRequired("CONFLICT_MARKERS_REMAIN", {"path": path, "marker": marker})


@contextmanager
def _exclusive_content_lock(path: Path) -> Iterator[BinaryIO]:
    """Hold the strongest available platform file-content lock."""
    handle = path.open("r+b")
    locked = False
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(
                handle.fileno(),
                msvcrt.LK_NBLCK,
                max(1, path.stat().st_size),
            )
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        locked = True
        yield handle
    except (OSError, IOError) as exc:
        raise StopRequired(
            "WORKTREE_EXCLUSIVE_LOCK_UNAVAILABLE",
            {"path": str(path), "error": str(exc)},
        ) from exc
    finally:
        if locked:
            try:
                if os.name == "nt":
                    import msvcrt

                    handle.seek(0)
                    msvcrt.locking(
                        handle.fileno(),
                        msvcrt.LK_UNLCK,
                        max(1, path.stat().st_size),
                    )
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        handle.close()


def _metadata(path: Path) -> dict[str, int]:
    """Capture metadata this runtime can preserve and verify portably."""
    current = path.stat(follow_symlinks=False)
    metadata = {"mode": stat.S_IMODE(current.st_mode)}
    if os.name != "nt":
        metadata["uid"] = current.st_uid
        metadata["gid"] = current.st_gid
    return metadata


def _verify_posix_mode(path: Path, *, expected: int, label: str) -> None:
    """Fail closed when effective POSIX mode is weaker than required."""
    if os.name == "nt":
        return
    mode = path.stat().st_mode & 0o777
    if mode != expected:
        raise StopRequired(
            "WRITE_TRANSACTION_BACKUP_ACL_FAILED",
            {
                "path": str(path),
                "label": label,
                "expected_mode": oct(expected),
                "actual_mode": oct(mode),
            },
        )


def _secure_windows_owner_only(path: Path) -> None:
    """Force and verify current-user-only DACL on Windows paths."""
    if os.name != "nt":
        return
    icacls = shutil.which("icacls")
    user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
    if not icacls or not user:
        raise StopRequired(
            "WRITE_TRANSACTION_BACKUP_ACL_FAILED",
            {"path": str(path), "error": "icacls_or_user_missing"},
        )
    from .cancellation import run_process

    harden = run_process(
        [icacls, str(path), "/inheritance:r", "/grant:r", f"{user}:F"],
        timeout=30.0,
    )
    if harden.returncode != 0:
        raise StopRequired(
            "WRITE_TRANSACTION_BACKUP_ACL_FAILED",
            {"path": str(path), "error": harden.stderr[-500:]},
        )
    result = run_process([icacls, str(path)], timeout=30.0)
    if result.returncode != 0:
        raise StopRequired(
            "WRITE_TRANSACTION_BACKUP_ACL_FAILED",
            {"path": str(path), "error": result.stderr[-500:]},
        )
    text = result.stdout.lower().replace(" ", "")
    suspicious = (
        "everyone:(f)",
        "everyone:(m)",
        "everyone:(w)",
        "authenticatedusers:(f)",
        "authenticatedusers:(m)",
        "users:(f)",
        "users:(m)",
    )
    if any(tok in text for tok in suspicious):
        raise StopRequired(
            "WRITE_TRANSACTION_BACKUP_ACL_FAILED",
            {"path": str(path), "error": "broad_acl"},
        )


def _secure_backup_tree(backup_path: Path) -> None:
    """Ensure transactional backup parents are current-user-only (0700)."""
    cur = backup_path.parent
    chain: list[Path] = []
    while True:
        chain.append(cur)
        if cur.name == "opsx-resolve-conflict" or cur == cur.parent:
            break
        cur = cur.parent
    for directory in reversed(chain):
        try:
            directory.mkdir(parents=True, exist_ok=True)
            if os.name != "nt":
                directory.chmod(0o700)
        except OSError as exc:
            raise StopRequired(
                "WRITE_TRANSACTION_BACKUP_ACL_FAILED",
                {"path": str(directory), "error": str(exc)},
            ) from exc
        if os.name != "nt":
            _verify_posix_mode(directory, expected=0o700, label="backup_dir")
        else:
            _secure_windows_owner_only(directory)


def _secure_backup_file(backup_path: Path) -> None:
    """Restrict backup file mode to 0600 after original-byte verification."""
    try:
        if os.name != "nt":
            backup_path.chmod(0o600)
    except OSError as exc:
        raise StopRequired(
            "WRITE_TRANSACTION_BACKUP_ACL_FAILED",
            {"path": str(backup_path), "error": str(exc)},
        ) from exc
    if os.name != "nt":
        _verify_posix_mode(backup_path, expected=0o600, label="backup_file")
    else:
        _secure_windows_owner_only(backup_path)


def _apply_metadata(path: Path, metadata: dict[str, int]) -> None:
    """Apply preserved mode/ownership before the candidate becomes visible."""
    os.chmod(path, metadata["mode"])
    if os.name != "nt" and hasattr(os, "chown"):
        current = path.stat(follow_symlinks=False)
        if (current.st_uid, current.st_gid) != (
            metadata["uid"],
            metadata["gid"],
        ):
            try:
                os.chown(
                    path,
                    metadata["uid"],
                    metadata["gid"],
                    follow_symlinks=False,
                )
            except PermissionError as exc:
                raise StopRequired(
                    "WORKTREE_METADATA_NOT_PRESERVABLE",
                    {"path": str(path), "metadata": metadata},
                ) from exc


def _link_noreplace(source: Path, target: Path) -> None:
    """Atomically install a same-filesystem inode without replacing a winner."""
    try:
        os.link(source, target, follow_symlinks=False)
    except FileExistsError as exc:
        raise StopRequired(
            "WORKTREE_CONCURRENT_PATH_WRITE",
            {"path": str(target)},
        ) from exc
    except OSError as exc:
        raise StopRequired(
            "ATOMIC_NOREPLACE_LINK_UNAVAILABLE",
            {"source": str(source), "target": str(target), "error": str(exc)},
        ) from exc


def _claim_target(target: Path, backup: Path) -> None:
    """Atomically move the current path entry into the locked transaction."""
    os.rename(target, backup)


def _restore_claimed_original(
    *,
    target: Path,
    backup: Path,
    candidate_sha256: str,
    original_sha256: str,
) -> str:
    """Best-effort rollback which never overwrites concurrent path content."""
    abandoned_candidate: Path | None = None
    if target.exists() and target.is_file() and not target.is_symlink():
        if sha256_bytes(target.read_bytes()) == candidate_sha256:
            abandoned_candidate = target.with_name(
                target.name + f".opsx-abandoned-{uuid4().hex}"
            )
            os.rename(target, abandoned_candidate)
        elif (
            backup.is_file()
            and sha256_bytes(backup.read_bytes()) == original_sha256
        ):
            # Preserve the concurrent winner. The unmerged stage OIDs remain
            # the recovery authority, so no plaintext conflict snapshot stays.
            backup.unlink()
            return "EXTERNAL_WINNER"
    if not target.exists() and backup.exists():
        _link_noreplace(backup, target)
        backup.unlink()
    if abandoned_candidate is not None and target.exists():
        abandoned_candidate.unlink(missing_ok=True)
    return "ROLLED_BACK" if target.exists() else "INCOMPLETE"


def _fsync_dir(path: Path) -> None:
    """Durably sync directory metadata after atomic replace."""
    flags = getattr(os, "O_RDONLY", 0)
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    try:
        fd = os.open(str(path), flags)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _persist_transaction(path: Path, payload: dict[str, object]) -> None:
    """Durably replace a hash-only write-ahead transaction record."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    try:
        tmp.chmod(0o600)
    except OSError:
        pass
    os.replace(tmp, path)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    _fsync_dir(path.parent)


def recover_write_transactions(
    repo_root: Path,
    transaction_root: Path,
    *,
    preserve_run_ids: set[str] | None = None,
    terminal_success_run_ids: set[str] | None = None,
) -> None:
    """Rollback incomplete writes or finish cleanup from hash-only journals.

    ``preserve_run_ids`` keeps ``VERIFIED``/``STAGED`` journals for an ACTIVE
    resume so rollback authority survives until terminal success.
    ``terminal_success_run_ids`` finishes release for runs whose terminal
    bundle is already durable — never restores pre-run bytes for those runs.
    """
    if not transaction_root.is_dir():
        return
    root = repo_root.resolve()
    keep = preserve_run_ids or set()
    terminal_ok = terminal_success_run_ids or set()
    for journal_path in sorted(transaction_root.rglob("*.json")):
        try:
            payload = json.loads(journal_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StopRequired(
                "WRITE_TRANSACTION_JOURNAL_INVALID",
                {"path": str(journal_path)},
            ) from exc
        if payload.get("repository_root") != str(root):
            raise StopRequired(
                "WRITE_TRANSACTION_REPOSITORY_MISMATCH",
                {"path": str(journal_path)},
            )
        state = str(payload.get("state", ""))
        run_id = str(payload.get("run_id", ""))
        if state in {"ROLLED_BACK", "EXTERNAL_WINNER", "RETIRED"}:
            continue
        if state == "RELEASE_COMMITTED" or (
            state in {"VERIFIED", "STAGED", "RECOVERY_RELEASED"}
            and run_id in terminal_ok
        ):
            candidate = str(payload.get("candidate_sha256", ""))
            if candidate:
                release_write_transaction(
                    journal_path,
                    expected_candidate_sha256=candidate,
                )
            else:
                payload["state"] = "RETIRED"
                _persist_transaction(journal_path, payload)
            continue
        if state in {"VERIFIED", "STAGED"} and run_id in keep:
            continue
        rel = str(payload.get("path", ""))
        _, target = resolve_under_repo(root, rel)
        _, backup = resolve_under_repo(root, str(payload.get("backup", "")))
        _, tmp = resolve_under_repo(root, str(payload.get("tmp", "")))
        original_sha256 = str(payload.get("original_sha256", ""))
        candidate_sha256 = str(payload.get("candidate_sha256", ""))
        # Legacy/completed journals must not block later Owner edits.
        if state == "RECOVERY_RELEASED":
            if backup.exists():
                backup.unlink()
            tmp.unlink(missing_ok=True)
            payload["state"] = "RETIRED"
            _persist_transaction(journal_path, payload)
            continue
        if backup.exists():
            if (
                not backup.is_file()
                or sha256_bytes(backup.read_bytes()) != original_sha256
            ):
                raise StopRequired(
                    "WRITE_TRANSACTION_BACKUP_DRIFT",
                    {"path": rel},
                )
            if target.exists():
                if (
                    not target.is_file()
                    or sha256_bytes(target.read_bytes()) != candidate_sha256
                ):
                    raise StopRequired(
                        "WRITE_TRANSACTION_CONCURRENT_TARGET",
                        {"path": rel},
                    )
                target.unlink()
            os.replace(backup, target)
        elif (
            not target.is_file()
            or sha256_bytes(target.read_bytes()) != original_sha256
        ):
            raise StopRequired(
                "WRITE_TRANSACTION_ORIGINAL_UNRECOVERABLE",
                {"path": rel, "state": state},
            )
        if state == "STAGED":
            _restore_unmerged_index(root, rel, payload)
        tmp.unlink(missing_ok=True)
        payload["state"] = "ROLLED_BACK"
        _persist_transaction(journal_path, payload)


def _restore_unmerged_index(
    repo_root: Path,
    rel: str,
    payload: dict[str, object],
) -> None:
    """Rebuild stage 1/2/3 index entries recorded before staging."""
    restore = payload.get("unmerged_restore")
    if not isinstance(restore, dict) or not restore:
        raise StopRequired(
            "WRITE_TRANSACTION_UNMERGED_RESTORE_MISSING",
            {"path": rel},
        )
    lines: list[str] = []
    for stage in ("1", "2", "3"):
        entry = restore.get(stage)
        if not isinstance(entry, dict):
            raise StopRequired(
                "WRITE_TRANSACTION_UNMERGED_RESTORE_INVALID",
                {"path": rel, "stage": stage},
            )
        mode = str(entry.get("mode", ""))
        oid = str(entry.get("oid", ""))
        if mode not in {"100644", "100755", "120000"} or len(oid) not in {
            40,
            64,
        }:
            raise StopRequired(
                "WRITE_TRANSACTION_UNMERGED_RESTORE_INVALID",
                {"path": rel, "stage": stage},
            )
        lines.append(f"{mode} {oid} {stage}\t{rel}")
    from .cancellation import active_execution_ledger
    from .git_typed import TypedGit

    git = TypedGit(repo_root, ledger=active_execution_ledger())
    info = "\n".join(lines) + "\n"
    git._run_index_info(info)


def mark_write_transaction_staged(
    journal_path: Path,
    *,
    expected_candidate_sha256: str,
    staged_candidate: dict[str, str],
    unmerged_restore: dict[str, dict[str, str]],
) -> None:
    """Record that staging succeeded while rollback authority remains."""
    try:
        payload = json.loads(journal_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StopRequired(
            "WRITE_TRANSACTION_JOURNAL_INVALID",
            {"path": str(journal_path)},
        ) from exc
    if str(payload.get("state", "")) != "VERIFIED":
        raise StopRequired(
            "WRITE_TRANSACTION_STAGE_INVALID_STATE",
            {"path": str(journal_path), "state": payload.get("state")},
        )
    if str(payload.get("candidate_sha256", "")) != expected_candidate_sha256:
        raise StopRequired(
            "WRITE_TRANSACTION_STAGE_CANDIDATE_MISMATCH",
            {"path": str(journal_path)},
        )
    payload["state"] = "STAGED"
    payload["staged_candidate"] = dict(staged_candidate)
    payload["unmerged_restore"] = {
        stage: dict(entry) for stage, entry in unmerged_restore.items()
    }
    _persist_transaction(journal_path, payload)


def release_write_transaction(
    journal_path: Path,
    *,
    expected_candidate_sha256: str,
) -> None:
    """Drop rollback authority only after durable terminal success.

    Release is two-phase: durable ``RELEASE_COMMITTED`` (backup still present),
    then idempotent backup unlink and ``RETIRED``. Crash between those steps
    never requires restoring pre-run bytes when a terminal bundle exists.
    """
    try:
        payload = json.loads(journal_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StopRequired(
            "WRITE_TRANSACTION_JOURNAL_INVALID",
            {"path": str(journal_path)},
        ) from exc
    state = str(payload.get("state", ""))
    if state == "RETIRED":
        return
    if state not in {"VERIFIED", "STAGED", "RELEASE_COMMITTED"}:
        raise StopRequired(
            "WRITE_TRANSACTION_RELEASE_INVALID_STATE",
            {"path": str(journal_path), "state": state},
        )
    if str(payload.get("candidate_sha256", "")) != expected_candidate_sha256:
        raise StopRequired(
            "WRITE_TRANSACTION_RELEASE_CANDIDATE_MISMATCH",
            {"path": str(journal_path)},
        )
    root = Path(str(payload.get("repository_root", "")))
    rel = str(payload.get("path", ""))
    _, target = resolve_under_repo(root, rel)
    _, backup = resolve_under_repo(root, str(payload.get("backup", "")))
    _, tmp = resolve_under_repo(root, str(payload.get("tmp", "")))
    if (
        not target.is_file()
        or sha256_bytes(target.read_bytes()) != expected_candidate_sha256
    ):
        raise StopRequired(
            "WRITE_TRANSACTION_RELEASE_TARGET_DRIFT",
            {"path": rel},
        )
    if state != "RELEASE_COMMITTED":
        payload["state"] = "RELEASE_COMMITTED"
        payload["terminal_release_committed"] = True
        _persist_transaction(journal_path, payload)
    if backup.exists():
        backup.unlink()
    tmp.unlink(missing_ok=True)
    payload["state"] = "RETIRED"
    _persist_transaction(journal_path, payload)


def retire_write_transactions(transaction_root: Path) -> None:
    """Mark remaining journals inactive after durable terminal success."""
    if not transaction_root.is_dir():
        return
    for journal_path in sorted(transaction_root.rglob("*.json")):
        try:
            payload = json.loads(journal_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        state = str(payload.get("state", ""))
        if state in {"RETIRED", "ROLLED_BACK", "EXTERNAL_WINNER"}:
            continue
        backup_rel = str(payload.get("backup", ""))
        tmp_rel = str(payload.get("tmp", ""))
        root = Path(str(payload.get("repository_root", "")))
        if backup_rel:
            try:
                _, backup = resolve_under_repo(root, backup_rel)
                if backup.exists():
                    backup.unlink()
            except Exception:
                pass
        if tmp_rel:
            try:
                _, tmp = resolve_under_repo(root, tmp_rel)
                tmp.unlink(missing_ok=True)
            except Exception:
                pass
        payload["state"] = "RETIRED"
        _persist_transaction(journal_path, payload)


def write_scoped_file(
    repo_root: Path,
    rel_path: str,
    content: str,
    *,
    scope: ScopeManifest,
    scope_proof: Proof,
    unit_plan: Proof,
    run_id: str,
    fingerprint: str,
    expected_worktree_sha256: str,
    recovery_dir: Path,
) -> Proof:
    """Perform a proof-bound, locked, no-replace conditional write."""
    scope_proof.assert_binds(
        kind="SCOPE",
        run_id=run_id,
        fingerprint=fingerprint,
        scope_sha256=scope.manifest_sha256,
    )
    unit_plan.assert_binds(
        kind="UNIT_PLAN",
        run_id=run_id,
        fingerprint=fingerprint,
        scope_sha256=scope.manifest_sha256,
    )
    rel, target = resolve_under_repo(repo_root, rel_path)
    if is_protected_process_path(rel) and classify_path_risk(rel) == "HIGH":
        if unit_plan.payload.get("allow_process_write") is not True:
            raise StopRequired("PROCESS_SURFACE_WRITE_BLOCKED", {"path": rel})
    item = scope.require(rel, allowed_operation="write")
    if item.initial_worktree_sha256 != expected_worktree_sha256:
        raise StopRequired(
            "WRITE_CAS_EXPECTATION_NOT_FROZEN",
            {"path": rel},
        )
    assert_no_conflict_markers(content, path=rel)
    if target.exists() and target.is_symlink():
        raise StopRequired("SNAPSHOT_UNSUPPORTED_SYMLINK", {"path": rel})
    if not target.is_file():
        raise StopRequired("WORKTREE_TARGET_NOT_REGULAR_FILE", {"path": rel})
    original = target.read_bytes()
    newline = detect_newline(original)
    original_metadata = _metadata(target)
    actual_worktree_sha256 = sha256_bytes(original)
    if actual_worktree_sha256 != expected_worktree_sha256:
        raise StopRequired(
            "WORKTREE_COMPARE_AND_SWAP_FAILED",
            {
                "path": rel,
                "expected": expected_worktree_sha256,
                "actual": actual_worktree_sha256,
            },
        )
    data = encode_with_newline(content, newline)
    nonce = uuid4().hex
    tmp = target.with_name(target.name + f".opsx-tmp-{nonce}")
    # Keep rollback bytes outside the worktree so Git status stays clean while
    # rollback authority is retained through validation/staging.
    backup_rel = (
        ".git/opsx-resolve-conflict/backups/"
        f"{sha256_bytes(rel.encode('utf-8'))}-{nonce}.original"
    )
    recovery_dir.mkdir(parents=True, exist_ok=True)
    transaction_path = (
        recovery_dir / f"{sha256_bytes(rel.encode('utf-8'))}-{nonce}.json"
    )
    # Ensure tmp stays under repo
    _, tmp_resolved = prepare_new_path_under_repo(
        repo_root,
        tmp.relative_to(repo_root.resolve()).as_posix(),
    )
    _, backup_resolved = prepare_new_path_under_repo(repo_root, backup_rel)
    _secure_backup_tree(backup_resolved)
    transaction: dict[str, object] = {
        "schema": "opsx-resolve-conflict/write-transaction/v1",
        "repository_root": str(repo_root.resolve()),
        "run_id": run_id,
        "path": rel,
        "tmp": tmp_resolved.relative_to(repo_root.resolve()).as_posix(),
        "backup": backup_resolved.relative_to(repo_root.resolve()).as_posix(),
        "original_sha256": actual_worktree_sha256,
        "candidate_sha256": sha256_bytes(data),
        "metadata": original_metadata,
        "state": "PREPARED",
    }
    installed = False
    verified = False
    try:
        with tmp_resolved.open("xb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        _apply_metadata(tmp_resolved, original_metadata)
        _persist_transaction(transaction_path, transaction)

        # Atomic claim: a path-level writer racing before this point is moved to
        # backup and detected by the hash/metadata check below, never overwritten.
        _claim_target(target, backup_resolved)
        transaction["state"] = "ORIGINAL_CLAIMED"
        _persist_transaction(transaction_path, transaction)
        with _exclusive_content_lock(backup_resolved) as claimed:
            claimed.seek(0)
            claimed_bytes = claimed.read()
            if (
                sha256_bytes(claimed_bytes) != expected_worktree_sha256
                or _metadata(backup_resolved) != original_metadata
            ):
                raise StopRequired(
                    "WORKTREE_COMPARE_AND_SWAP_FAILED",
                    {
                        "path": rel,
                        "expected": expected_worktree_sha256,
                        "actual": sha256_bytes(claimed_bytes),
                    },
                )
            _secure_backup_file(backup_resolved)

            # Hard-link creation is atomic and fails if a concurrent writer has
            # recreated target after the claim.
            _link_noreplace(tmp_resolved, target)
            installed = True
            transaction["state"] = "CANDIDATE_INSTALLED"
            _persist_transaction(transaction_path, transaction)
            if (
                sha256_bytes(target.read_bytes()) != sha256_bytes(data)
                or _metadata(target) != original_metadata
            ):
                raise StopRequired(
                    "WORKTREE_POST_WRITE_VERIFICATION_FAILED",
                    {"path": rel},
                )

            claimed.seek(0)
            if sha256_bytes(claimed.read()) != expected_worktree_sha256:
                raise StopRequired(
                    "WORKTREE_CLAIMED_ORIGINAL_CHANGED",
                    {"path": rel, "backup": str(backup_resolved)},
                )
            # Keep rollback authority until staging/terminal release.
            transaction["state"] = "VERIFIED"
            _persist_transaction(transaction_path, transaction)
            verified = True
    except BaseException:
        if backup_resolved.exists():
            try:
                recovery_state = _restore_claimed_original(
                    target=target,
                    backup=backup_resolved,
                    candidate_sha256=sha256_bytes(data),
                    original_sha256=actual_worktree_sha256,
                )
                if recovery_state in {"ROLLED_BACK", "EXTERNAL_WINNER"}:
                    transaction["state"] = recovery_state
                    _persist_transaction(transaction_path, transaction)
            except (OSError, StopRequired):
                # Keep the in-repository transaction recoverable; never copy
                # plaintext conflict content into the external state root.
                pass
        raise
    finally:
        if tmp_resolved.exists():
            try:
                tmp_resolved.unlink()
            except OSError:
                pass
    if not verified:
        raise StopRequired("WRITE_TRANSACTION_NOT_VERIFIED", {"path": rel})
    return Proof.issue(
        "WRITE",
        run_id=run_id,
        fingerprint=fingerprint,
        scope_sha256=scope.manifest_sha256,
        payload={
            "path": rel,
            "content_sha256": sha256_bytes(data),
            "replaced_sha256": actual_worktree_sha256,
            "newline": newline.decode("ascii", "replace"),
            "metadata_before": original_metadata,
            "metadata_after": _metadata(target),
            "conditional_write": "locked_claim_plus_link_noreplace",
            "installed": installed,
            "transaction_journal": str(transaction_path),
            "transaction_state": str(transaction["state"]),
            "rollback_authority_retained": True,
            "plaintext_backup_persisted": True,
            "plaintext_backup_location": "git_dir_transactional",
            "plaintext_backup_rel": backup_rel,
        },
    )
