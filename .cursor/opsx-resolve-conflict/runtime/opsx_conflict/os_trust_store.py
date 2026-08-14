"""OS-pinned authority trust-store path protection (R30/R31).

Installer-owned Ed25519 public key paths are authenticated only after a
component-by-component, no-follow walk with owner/ACL checks and a stable
file handle that remains open through producer signature verification.

R31: Windows effective rights are collected per forbidden right (never a
single all-or-nothing AccessCheck of the combined mask). Drive/volume roots
are subject to the same owner/DACL fail-closed policy as other parents.

This module is package-owned OS primitives only — it does not mint trust keys
and does not accept environment-provided trust key paths.
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from .errors import StopRequired

BLOCKER = "BLOCKER_AUTHORITY_PRODUCER_MISSING"

# Forbidden effective rights for the current process/agent on trust objects.
POSIX_DIR_WRITE_BITS = 0o022  # group/other write
POSIX_FILE_WRITE_BITS = 0o222  # owner/group/other write

# Win32 specific access rights (winnt.h) used by DACL policy.
WIN_FILE_WRITE_DATA = 0x0002
WIN_FILE_APPEND_DATA = 0x0004
WIN_FILE_WRITE_EA = 0x0010
WIN_FILE_WRITE_ATTRIBUTES = 0x0100
WIN_FILE_DELETE_CHILD = 0x0040
WIN_FILE_ADD_FILE = 0x0002  # same bit as FILE_WRITE_DATA
WIN_FILE_ADD_SUBDIRECTORY = 0x0004  # same bit as FILE_APPEND_DATA
WIN_DELETE = 0x00010000
WIN_WRITE_DAC = 0x00040000
WIN_WRITE_OWNER = 0x00080000

FORBIDDEN_FILE_RIGHTS: tuple[int, ...] = (
    WIN_FILE_WRITE_DATA,
    WIN_FILE_APPEND_DATA,
    WIN_FILE_WRITE_EA,
    WIN_FILE_WRITE_ATTRIBUTES,
    WIN_DELETE,
    WIN_WRITE_DAC,
    WIN_WRITE_OWNER,
)

FORBIDDEN_DIRECTORY_RIGHTS: tuple[int, ...] = (
    WIN_FILE_ADD_FILE,
    WIN_FILE_ADD_SUBDIRECTORY,
    WIN_FILE_WRITE_EA,
    WIN_FILE_WRITE_ATTRIBUTES,
    WIN_FILE_DELETE_CHILD,
    WIN_DELETE,
    WIN_WRITE_DAC,
    WIN_WRITE_OWNER,
)

# Deterministic test seam: right → granted?  When set, native AccessCheck is skipped.
_PER_RIGHT_GRANT_SEAM: Callable[[int, bool], bool] | None = None


def os_authority_trust_pubkey_path() -> Path:
    """Return the installer-pinned Ed25519 public key path (not env-overridable)."""
    if os.name == "nt":
        return Path(r"C:\ProgramData\OPSX\conflict-authority\ed25519.pub")
    return Path("/etc/opsx/conflict-authority/ed25519.pub")


def _stop(reason: str, **extra: Any) -> StopRequired:
    """Build typed STOP_AUTHORITY_UNPROVEN for trust-store failures."""
    details: dict[str, Any] = {"blocker": BLOCKER, "reason": reason}
    details.update(extra)
    return StopRequired("STOP_AUTHORITY_UNPROVEN", details)


@dataclass
class TrustKeySession:
    """Stable trust-key handle: bytes read from validated FD + identity binding."""

    path: Path
    key_bytes: bytes
    identity: dict[str, Any]
    _fd: int | None = None
    _win_handle: int | None = None
    _closed: bool = False

    def recheck_identity(self) -> None:
        """Fail closed if pathname or handle identity drifted."""
        if self._closed:
            raise _stop("os_trust_identity_changed", path=str(self.path), note="closed")
        # FD-backed sessions (including test fixtures) use POSIX-style fstat binding.
        if self._fd is not None:
            _posix_recheck(self)
            return
        if os.name == "nt":
            _windows_recheck(self)
            return
        raise _stop("os_trust_identity_changed", path=str(self.path), note="no_handle")

    def close(self) -> None:
        """Release OS handles."""
        if self._closed:
            return
        self._closed = True
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None
        if self._win_handle is not None:
            try:
                import ctypes

                ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(self._win_handle))
            except Exception:
                pass
            self._win_handle = None


def open_authenticated_trust_pubkey(path: Path | None = None) -> TrustKeySession:
    """Secure-walk trust path, open stable handle, read key bytes from that handle."""
    target = path if path is not None else os_authority_trust_pubkey_path()
    if os.name == "nt":
        return _windows_open_trust(target)
    return _posix_open_trust(target)


# ---------------------------------------------------------------------------
# Policy helpers (platform-independent; used by tests + openers)
# ---------------------------------------------------------------------------


def evaluate_posix_component_policy(
    *,
    is_final: bool,
    st_mode: int,
    st_uid: int,
    st_gid: int | None = None,
) -> str | None:
    """Return STOP reason or None if POSIX component policy accepts the object."""
    del st_gid  # reserved for future group-policy tightening
    if stat.S_ISLNK(st_mode):
        return "os_trust_component_symlink" if not is_final else "os_trust_component_symlink"
    if is_final:
        if not stat.S_ISREG(st_mode):
            return "os_trust_pubkey_unreadable"
        if st_uid != 0:
            return "os_trust_owner_invalid"
        if (st_mode & 0o777) & POSIX_FILE_WRITE_BITS:
            return "os_trust_pubkey_writable"
        return None
    if not stat.S_ISDIR(st_mode):
        return "os_trust_component_symlink"
    if st_uid != 0:
        return "os_trust_owner_invalid"
    if (st_mode & 0o777) & POSIX_DIR_WRITE_BITS:
        return "os_trust_parent_writable"
    return None


def evaluate_windows_owner_policy(owner_sid: str) -> str | None:
    """Return STOP reason unless owner is LocalSystem or Builtin Administrators."""
    allowed = {
        "S-1-5-18",  # Local System
        "S-1-5-32-544",  # Builtin Administrators
    }
    if owner_sid.upper() not in {s.upper() for s in allowed}:
        return "os_trust_owner_invalid"
    return None


def forbidden_rights_for(*, is_directory: bool) -> tuple[int, ...]:
    """Return the closed set of rights that must not be granted to the agent."""
    return FORBIDDEN_DIRECTORY_RIGHTS if is_directory else FORBIDDEN_FILE_RIGHTS


def merge_per_right_grants(
    grants: Mapping[int, bool],
    *,
    is_directory: bool,
) -> int:
    """OR individually granted forbidden rights (never all-or-nothing).

    Partial grants (e.g. only DELETE) must not collapse to zero.
    """
    mask = 0
    for right in forbidden_rights_for(is_directory=is_directory):
        if grants.get(right, False):
            mask |= right
    return mask


def evaluate_windows_rights_policy(
    *,
    is_directory: bool,
    granted_mask: int,
) -> str | None:
    """Return STOP reason if granted access includes agent write/delete rights."""
    delete_bits = WIN_DELETE
    if is_directory:
        delete_bits |= WIN_FILE_DELETE_CHILD
    write_bits = 0
    for right in forbidden_rights_for(is_directory=is_directory):
        if right & delete_bits:
            continue
        write_bits |= right
    if granted_mask & delete_bits:
        return "os_trust_dacl_allows_agent_delete"
    if granted_mask & write_bits:
        return "os_trust_dacl_allows_agent_write"
    return None


def set_per_right_grant_seam(
    seam: Callable[[int, bool], bool] | None,
) -> Callable[[int, bool], bool] | None:
    """Install or clear the AccessCheck-per-right test seam. Returns previous."""
    global _PER_RIGHT_GRANT_SEAM
    previous = _PER_RIGHT_GRANT_SEAM
    _PER_RIGHT_GRANT_SEAM = seam
    return previous


def identities_match(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    """Compare stable trust-object identities."""
    keys = ("device", "inode", "volume_serial", "file_index_high", "file_index_low")
    present = [k for k in keys if k in a or k in b]
    if not present:
        return False
    return all(a.get(k) == b.get(k) for k in present if k in a or k in b)


# ---------------------------------------------------------------------------
# POSIX opener
# ---------------------------------------------------------------------------


def _posix_components(path: Path) -> list[Path]:
    """Return absolute components from filesystem root to path (no resolve)."""
    abs_path = Path(os.path.abspath(os.fspath(path)))
    parts: list[Path] = []
    cur = abs_path
    while True:
        parts.append(cur)
        parent = cur.parent
        if parent == cur:
            break
        cur = parent
    return list(reversed(parts))


def _posix_open_trust(path: Path) -> TrustKeySession:
    """Component-by-component O_NOFOLLOW walk; read key from final FD."""
    o_nofollow = getattr(os, "O_NOFOLLOW", 0)
    o_directory = getattr(os, "O_DIRECTORY", 0)
    components = _posix_components(path)
    if not components:
        raise _stop("os_trust_pubkey_unreadable", path=str(path))

    # Validate each ancestor via lstat before opening the final file.
    for comp in components[:-1]:
        try:
            st = os.lstat(comp)
        except OSError as exc:
            raise _stop(
                "os_trust_pubkey_unreadable",
                path=str(comp),
                error=type(exc).__name__,
            ) from exc
        reason = evaluate_posix_component_policy(
            is_final=False, st_mode=st.st_mode, st_uid=st.st_uid, st_gid=st.st_gid
        )
        if reason:
            raise _stop(reason, path=str(comp))
        # Prefer open+fstat when flags available.
        if o_directory and o_nofollow:
            try:
                dfd = os.open(comp, os.O_RDONLY | o_directory | o_nofollow)
            except OSError as exc:
                raise _stop(
                    "os_trust_component_symlink",
                    path=str(comp),
                    error=type(exc).__name__,
                ) from exc
            try:
                fst = os.fstat(dfd)
                if (fst.st_dev, fst.st_ino) != (st.st_dev, st.st_ino):
                    raise _stop("os_trust_identity_changed", path=str(comp))
            finally:
                os.close(dfd)

    final = components[-1]
    try:
        st = os.lstat(final)
    except OSError as exc:
        raise _stop(
            "os_trust_pubkey_unreadable",
            path=str(final),
            error=type(exc).__name__,
        ) from exc
    reason = evaluate_posix_component_policy(
        is_final=True, st_mode=st.st_mode, st_uid=st.st_uid, st_gid=st.st_gid
    )
    if reason:
        # Map non-regular to a clearer final reason when not symlink.
        if reason == "os_trust_pubkey_unreadable" and not stat.S_ISREG(st.st_mode):
            if stat.S_ISLNK(st.st_mode):
                raise _stop("os_trust_component_symlink", path=str(final))
            raise _stop("os_trust_pubkey_unreadable", path=str(final), note="not_regular")
        raise _stop(reason, path=str(final))

    flags = os.O_RDONLY
    if o_nofollow:
        flags |= o_nofollow
    try:
        fd = os.open(final, flags)
    except OSError as exc:
        raise _stop(
            "os_trust_component_symlink"
            if getattr(exc, "errno", None) in {errno_efloop(), 40, 62}
            else "os_trust_pubkey_unreadable",
            path=str(final),
            error=type(exc).__name__,
        ) from exc
    try:
        fst = os.fstat(fd)
        if stat.S_ISLNK(fst.st_mode) or not stat.S_ISREG(fst.st_mode):
            raise _stop("os_trust_component_symlink", path=str(final))
        if (fst.st_dev, fst.st_ino) != (st.st_dev, st.st_ino):
            raise _stop("os_trust_identity_changed", path=str(final))
        reason = evaluate_posix_component_policy(
            is_final=True, st_mode=fst.st_mode, st_uid=fst.st_uid, st_gid=fst.st_gid
        )
        if reason:
            raise _stop(reason, path=str(final))
        key_bytes = os.read(fd, 1 << 20)
        if not key_bytes:
            raise _stop("os_trust_pubkey_unreadable", path=str(final), note="empty")
        # Drain remainder if needed.
        while True:
            chunk = os.read(fd, 1 << 20)
            if not chunk:
                break
            key_bytes += chunk
        identity = {
            "device": int(fst.st_dev),
            "inode": int(fst.st_ino),
            "size": int(fst.st_size),
            "uid": int(fst.st_uid),
            "mode": int(fst.st_mode),
        }
        session = TrustKeySession(
            path=final,
            key_bytes=key_bytes,
            identity=identity,
            _fd=fd,
        )
        fd = None  # ownership transferred
        return session
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass


def errno_efloop() -> int:
    """Return ELOOP errno when available."""
    return getattr(__import__("errno"), "ELOOP", 40)


def _posix_recheck(session: TrustKeySession) -> None:
    """Compare pathname lstat with open FD identity."""
    if session._fd is None:
        raise _stop("os_trust_identity_changed", path=str(session.path))
    try:
        fst = os.fstat(session._fd)
        lst = os.lstat(session.path)
    except OSError as exc:
        raise _stop(
            "os_trust_identity_changed",
            path=str(session.path),
            error=type(exc).__name__,
        ) from exc
    cur = {
        "device": int(fst.st_dev),
        "inode": int(fst.st_ino),
        "size": int(fst.st_size),
        "uid": int(fst.st_uid),
        "mode": int(fst.st_mode),
    }
    path_id = {
        "device": int(lst.st_dev),
        "inode": int(lst.st_ino),
        "size": int(lst.st_size),
        "uid": int(lst.st_uid),
        "mode": int(lst.st_mode),
    }
    if not identities_match(session.identity, cur) or not identities_match(
        session.identity, path_id
    ):
        raise _stop("os_trust_identity_changed", path=str(session.path))
    # Pathname must still name a regular non-symlink object at the same identity.
    if stat.S_ISLNK(lst.st_mode) or not stat.S_ISREG(lst.st_mode):
        raise _stop("os_trust_component_symlink", path=str(session.path))
    if stat.S_ISLNK(fst.st_mode) or not stat.S_ISREG(fst.st_mode):
        raise _stop("os_trust_component_symlink", path=str(session.path))


# ---------------------------------------------------------------------------
# Windows opener (ctypes, no third-party deps)
# ---------------------------------------------------------------------------


def _windows_open_trust(path: Path) -> TrustKeySession:
    """No-reparse component walk + DACL/owner checks + stable CreateFile handle."""
    import ctypes
    from ctypes import wintypes

    abs_path = Path(os.path.abspath(os.fspath(path)))
    components = _posix_components(abs_path)  # same parent-walk logic
    # Skip the drive root check nuances: still verify each existing component.
    for comp in components:
        is_final = comp == components[-1]
        _windows_assert_component(comp, is_final=is_final)

    handle = _windows_create_file_noreparse(abs_path, for_directory=False)
    try:
        identity = _windows_file_identity(handle)
        owner = _windows_owner_sid_string(handle)
        reason = evaluate_windows_owner_policy(owner)
        if reason:
            raise _stop(reason, path=str(abs_path), owner_sid=owner)
        granted = _windows_granted_access_mask(handle, is_directory=False)
        reason = evaluate_windows_rights_policy(
            is_directory=False, granted_mask=granted
        )
        if reason:
            raise _stop(reason, path=str(abs_path), granted_mask=hex(granted))
        key_bytes = _windows_read_handle(handle)
        if not key_bytes:
            raise _stop("os_trust_pubkey_unreadable", path=str(abs_path), note="empty")
        session = TrustKeySession(
            path=abs_path,
            key_bytes=key_bytes,
            identity={**identity, "owner_sid": owner},
            _win_handle=int(handle),
        )
        handle = None
        return session
    finally:
        if handle is not None:
            ctypes.windll.kernel32.CloseHandle(handle)


def _windows_is_drive_root(path: Path) -> bool:
    """Return True for volume roots (e.g. C:\\) that still need DACL policy."""
    return path == path.anchor or str(path).endswith(":\\") or str(path).endswith(":/")


def _windows_assert_component(path: Path, *, is_final: bool) -> None:
    """Validate one Windows path component without following reparse points.

    Drive/volume roots are not exempt: they are checked as directory parents
    with the same owner + effective-rights policy so top-level trust-path
    components cannot be silently replaced.
    """
    import ctypes

    FILE_ATTRIBUTE_REPARSE_POINT = 0x400
    FILE_ATTRIBUTE_DIRECTORY = 0x10
    INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF

    # Prefer GetFileAttributesW (no FindFirstFile) to avoid fragile FIND_DATA layout.
    attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
    if attrs == INVALID_FILE_ATTRIBUTES:
        raise _stop("os_trust_pubkey_unreadable", path=str(path))

    if attrs & FILE_ATTRIBUTE_REPARSE_POINT:
        raise _stop("os_trust_component_reparse", path=str(path))

    is_root = _windows_is_drive_root(path)
    is_dir = bool(attrs & FILE_ATTRIBUTE_DIRECTORY) or is_root
    if is_final and is_dir:
        raise _stop("os_trust_pubkey_unreadable", path=str(path), note="not_regular")
    if not is_final and not is_dir:
        raise _stop("os_trust_pubkey_unreadable", path=str(path), note="not_directory")

    handle = _windows_create_file_noreparse(path, for_directory=is_dir)
    try:
        owner = _windows_owner_sid_string(handle)
        reason = evaluate_windows_owner_policy(owner)
        if reason:
            raise _stop(reason, path=str(path), owner_sid=owner)
        granted = _windows_granted_access_mask(handle, is_directory=is_dir)
        reason = evaluate_windows_rights_policy(
            is_directory=is_dir, granted_mask=granted
        )
        if reason:
            raise _stop(
                reason,
                path=str(path),
                granted_mask=hex(granted),
                drive_root=is_root,
            )
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def _windows_create_file_noreparse(path: Path, *, for_directory: bool) -> int:
    """CreateFileW without following reparse points; deny share write/delete."""
    import ctypes
    from ctypes import wintypes

    GENERIC_READ = 0x80000000
    FILE_SHARE_READ = 0x00000001
    OPEN_EXISTING = 3
    FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
    FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
    flags = FILE_FLAG_OPEN_REPARSE_POINT
    if for_directory:
        flags |= FILE_FLAG_BACKUP_SEMANTICS
    handle = ctypes.windll.kernel32.CreateFileW(
        str(path),
        GENERIC_READ,
        FILE_SHARE_READ,  # no WRITE/DELETE share
        None,
        OPEN_EXISTING,
        flags,
        None,
    )
    if handle == INVALID_HANDLE_VALUE or handle == -1:
        raise _stop(
            "os_trust_pubkey_unreadable",
            path=str(path),
            error="CreateFileW",
            winerr=ctypes.GetLastError(),
        )
    # If the object is a reparse point, reject even with OPEN_REPARSE_POINT
    # (we opened the reparse point itself — still not a trust file).
    FILE_ATTRIBUTE_REPARSE_POINT = 0x400
    attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
    if attrs != 0xFFFFFFFF and attrs & FILE_ATTRIBUTE_REPARSE_POINT:
        ctypes.windll.kernel32.CloseHandle(handle)
        raise _stop("os_trust_component_reparse", path=str(path))
    return int(handle)


def _windows_file_identity(handle: int) -> dict[str, Any]:
    """Return volume serial + file index for a handle."""
    import ctypes
    from ctypes import wintypes

    class BY_HANDLE_FILE_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("dwFileAttributes", wintypes.DWORD),
            ("ftCreationTime", wintypes.FILETIME),
            ("ftLastAccessTime", wintypes.FILETIME),
            ("ftLastWriteTime", wintypes.FILETIME),
            ("dwVolumeSerialNumber", wintypes.DWORD),
            ("nFileSizeHigh", wintypes.DWORD),
            ("nFileSizeLow", wintypes.DWORD),
            ("nNumberOfLinks", wintypes.DWORD),
            ("nFileIndexHigh", wintypes.DWORD),
            ("nFileIndexLow", wintypes.DWORD),
        ]

    info = BY_HANDLE_FILE_INFORMATION()
    ok = ctypes.windll.kernel32.GetFileInformationByHandle(
        ctypes.c_void_p(handle), ctypes.byref(info)
    )
    if not ok:
        raise _stop("os_trust_identity_changed", error="GetFileInformationByHandle")
    return {
        "volume_serial": int(info.dwVolumeSerialNumber),
        "file_index_high": int(info.nFileIndexHigh),
        "file_index_low": int(info.nFileIndexLow),
        "size": (int(info.nFileSizeHigh) << 32) | int(info.nFileSizeLow),
    }


def _windows_owner_sid_string(handle: int) -> str:
    """Return owner SID string for an open handle."""
    import ctypes
    from ctypes import wintypes

    advapi = ctypes.windll.advapi32
    OWNER_SECURITY_INFORMATION = 0x00000001
    p_sd = ctypes.c_void_p()
    p_owner = ctypes.c_void_p()
    # GetSecurityInfo from handle
    err = advapi.GetSecurityInfo(
        ctypes.c_void_p(handle),
        1,  # SE_FILE_OBJECT
        OWNER_SECURITY_INFORMATION,
        ctypes.byref(p_owner),
        None,
        None,
        None,
        ctypes.byref(p_sd),
    )
    if err != 0:
        raise _stop("os_trust_owner_invalid", error="GetSecurityInfo", winerr=err)
    try:
        sid_str = ctypes.c_wchar_p()
        if not advapi.ConvertSidToStringSidW(p_owner, ctypes.byref(sid_str)):
            raise _stop("os_trust_owner_invalid", error="ConvertSidToStringSidW")
        try:
            return str(sid_str.value or "")
        finally:
            if sid_str:
                ctypes.windll.kernel32.LocalFree(sid_str)
    finally:
        if p_sd:
            ctypes.windll.kernel32.LocalFree(p_sd)


def _windows_granted_access_mask(handle: int, *, is_directory: bool) -> int:
    """Return effective forbidden-rights mask via per-right AccessCheck.

    R31: never issue one AccessCheck for the combined forbidden set. A token
    granted only DELETE (or only FILE_WRITE_DATA) must still surface that bit.

    When ``_PER_RIGHT_GRANT_SEAM`` is installed (tests), native AccessCheck is
    skipped and the seam supplies per-right boolean grants.
    """
    if _PER_RIGHT_GRANT_SEAM is not None:
        grants = {
            right: bool(_PER_RIGHT_GRANT_SEAM(right, is_directory))
            for right in forbidden_rights_for(is_directory=is_directory)
        }
        return merge_per_right_grants(grants, is_directory=is_directory)

    import ctypes
    from ctypes import wintypes

    advapi = ctypes.windll.advapi32
    kernel = ctypes.windll.kernel32

    DACL_SECURITY_INFORMATION = 0x00000004
    OWNER_SECURITY_INFORMATION = 0x00000001
    GROUP_SECURITY_INFORMATION = 0x00000002
    si = (
        DACL_SECURITY_INFORMATION
        | OWNER_SECURITY_INFORMATION
        | GROUP_SECURITY_INFORMATION
    )
    p_sd = ctypes.c_void_p()
    err = advapi.GetSecurityInfo(
        ctypes.c_void_p(handle),
        1,
        si,
        None,
        None,
        None,
        None,
        ctypes.byref(p_sd),
    )
    if err != 0 or not p_sd:
        raise _stop(
            "os_trust_dacl_allows_agent_write",
            error="GetSecurityInfo",
            winerr=err,
        )

    try:
        TOKEN_QUERY = 0x0008
        TOKEN_DUPLICATE = 0x0002
        TOKEN_IMPERSONATE = 0x0004
        process = kernel.GetCurrentProcess()
        token = wintypes.HANDLE()
        if not advapi.OpenProcessToken(
            process,
            TOKEN_QUERY | TOKEN_DUPLICATE | TOKEN_IMPERSONATE,
            ctypes.byref(token),
        ):
            raise _stop(
                "os_trust_dacl_allows_agent_write",
                error="OpenProcessToken",
                winerr=ctypes.GetLastError(),
            )
        try:
            SecurityImpersonation = 2
            TokenImpersonation = 2
            dup = wintypes.HANDLE()
            if not advapi.DuplicateTokenEx(
                token,
                TOKEN_QUERY | TOKEN_IMPERSONATE,
                None,
                SecurityImpersonation,
                TokenImpersonation,
                ctypes.byref(dup),
            ):
                raise _stop(
                    "os_trust_dacl_allows_agent_write",
                    error="DuplicateTokenEx",
                    winerr=ctypes.GetLastError(),
                )
            try:

                class GENERIC_MAPPING(ctypes.Structure):
                    _fields_ = [
                        ("GenericRead", wintypes.DWORD),
                        ("GenericWrite", wintypes.DWORD),
                        ("GenericExecute", wintypes.DWORD),
                        ("GenericAll", wintypes.DWORD),
                    ]

                mapping = GENERIC_MAPPING(
                    0x120089,
                    0x120116,
                    0x1200A0,
                    0x1F01FF,
                )
                grants: dict[int, bool] = {}
                for right in forbidden_rights_for(is_directory=is_directory):
                    grants[right] = _windows_access_check_one_right(
                        advapi=advapi,
                        security_descriptor=p_sd,
                        token=dup,
                        right=right,
                        mapping=mapping,
                    )
                return merge_per_right_grants(grants, is_directory=is_directory)
            finally:
                kernel.CloseHandle(dup)
        finally:
            kernel.CloseHandle(token)
    finally:
        kernel.LocalFree(p_sd)


def _windows_access_check_one_right(
    *,
    advapi: Any,
    security_descriptor: Any,
    token: Any,
    right: int,
    mapping: Any,
) -> bool:
    """Return True if AccessCheck grants exactly this single right."""
    import ctypes
    from ctypes import wintypes

    privilege_set = (ctypes.c_byte * 1024)()
    priv_size = wintypes.DWORD(ctypes.sizeof(privilege_set))
    granted = wintypes.DWORD(0)
    access_status = wintypes.BOOL(False)
    desired = wintypes.DWORD(right)
    advapi.MapGenericMask(ctypes.byref(desired), ctypes.byref(mapping))
    ok = advapi.AccessCheck(
        security_descriptor,
        token,
        desired,
        ctypes.byref(mapping),
        ctypes.byref(privilege_set),
        ctypes.byref(priv_size),
        ctypes.byref(granted),
        ctypes.byref(access_status),
    )
    if not ok:
        raise _stop(
            "os_trust_dacl_allows_agent_write",
            error="AccessCheck",
            winerr=ctypes.GetLastError(),
            right=hex(right),
        )
    return bool(access_status.value) and bool(int(granted.value) & right)


def _windows_read_handle(handle: int) -> bytes:
    """Read all bytes from an open file handle."""
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.windll.kernel32
    chunks: list[bytes] = []
    buf = ctypes.create_string_buffer(1 << 16)
    read = wintypes.DWORD(0)
    while True:
        ok = kernel.ReadFile(
            ctypes.c_void_p(handle),
            buf,
            len(buf),
            ctypes.byref(read),
            None,
        )
        if not ok:
            err = ctypes.GetLastError()
            if err == 38:  # ERROR_HANDLE_EOF
                break
            raise _stop("os_trust_pubkey_unreadable", error="ReadFile", winerr=err)
        if read.value == 0:
            break
        chunks.append(buf.raw[: read.value])
    return b"".join(chunks)


def _windows_recheck(session: TrustKeySession) -> None:
    """Recheck handle identity and pathname non-reparse binding."""
    import ctypes

    if session._win_handle is None:
        raise _stop("os_trust_identity_changed", path=str(session.path))
    cur = _windows_file_identity(session._win_handle)
    if not identities_match(session.identity, cur):
        raise _stop("os_trust_identity_changed", path=str(session.path))
    # Pathname must still name the same non-reparse object.
    attrs = ctypes.windll.kernel32.GetFileAttributesW(str(session.path))
    if attrs == 0xFFFFFFFF:
        raise _stop("os_trust_identity_changed", path=str(session.path))
    if attrs & 0x400:  # FILE_ATTRIBUTE_REPARSE_POINT
        raise _stop("os_trust_component_reparse", path=str(session.path))
    # Re-open pathname briefly to compare identity (detect replace).
    probe = _windows_create_file_noreparse(session.path, for_directory=False)
    try:
        probe_id = _windows_file_identity(probe)
        if not identities_match(session.identity, probe_id):
            raise _stop("os_trust_identity_changed", path=str(session.path))
        owner = _windows_owner_sid_string(probe)
        reason = evaluate_windows_owner_policy(owner)
        if reason:
            raise _stop(reason, path=str(session.path), owner_sid=owner)
        granted = _windows_granted_access_mask(probe, is_directory=False)
        reason = evaluate_windows_rights_policy(
            is_directory=False, granted_mask=granted
        )
        if reason:
            raise _stop(reason, path=str(session.path), granted_mask=hex(granted))
    finally:
        ctypes.windll.kernel32.CloseHandle(probe)
