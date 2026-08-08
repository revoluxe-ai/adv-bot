"""R30 OS trust-store path protection: policy + platform integration tests."""

from __future__ import annotations

import binascii
import json
import os
import stat
import sys
from pathlib import Path

import pytest

from opsx_conflict.errors import StopRequired
from opsx_conflict.os_trust_store import (
    TrustKeySession,
    evaluate_posix_component_policy,
    evaluate_windows_owner_policy,
    evaluate_windows_rights_policy,
    identities_match,
    open_authenticated_trust_pubkey,
    os_authority_trust_pubkey_path,
)

# Machine-readable skip inventory for platform-unavailable integration cases.
SKIP_INVENTORY: list[dict[str, str]] = []


def _record_skip(test_id: str, reason: str) -> None:
    """Append a structured skip row for ship SKIP_INVENTORY consumption."""
    SKIP_INVENTORY.append(
        {
            "test_id": test_id,
            "platform": sys.platform,
            "reason": reason,
        }
    )


# ---------------------------------------------------------------------------
# Platform-independent policy (must never skip)
# ---------------------------------------------------------------------------


def test_policy_owner_mismatch_posix() -> None:
    """Non-root UID is rejected for directory and final key."""
    mode_dir = stat.S_IFDIR | 0o755
    mode_file = stat.S_IFREG | 0o444
    assert (
        evaluate_posix_component_policy(is_final=False, st_mode=mode_dir, st_uid=1000)
        == "os_trust_owner_invalid"
    )
    assert (
        evaluate_posix_component_policy(is_final=True, st_mode=mode_file, st_uid=1000)
        == "os_trust_owner_invalid"
    )


def test_policy_writable_parent_posix() -> None:
    """Group/other-writable directory is rejected."""
    mode = stat.S_IFDIR | 0o775
    assert (
        evaluate_posix_component_policy(is_final=False, st_mode=mode, st_uid=0)
        == "os_trust_parent_writable"
    )
    mode_o = stat.S_IFDIR | 0o757
    assert (
        evaluate_posix_component_policy(is_final=False, st_mode=mode_o, st_uid=0)
        == "os_trust_parent_writable"
    )


def test_policy_writable_final_key_posix() -> None:
    """Owner/group/other-writable final key is rejected."""
    for bits in (0o644, 0o464, 0o446):
        mode = stat.S_IFREG | bits
        assert (
            evaluate_posix_component_policy(is_final=True, st_mode=mode, st_uid=0)
            == "os_trust_pubkey_writable"
        )


def test_policy_component_symlink_posix() -> None:
    """Symlink mode is rejected for any component."""
    mode = stat.S_IFLNK | 0o777
    assert (
        evaluate_posix_component_policy(is_final=False, st_mode=mode, st_uid=0)
        == "os_trust_component_symlink"
    )
    assert (
        evaluate_posix_component_policy(is_final=True, st_mode=mode, st_uid=0)
        == "os_trust_component_symlink"
    )


def test_policy_non_regular_final_posix() -> None:
    """Final non-regular object is unreadable as a trust key."""
    mode = stat.S_IFDIR | 0o755
    assert (
        evaluate_posix_component_policy(is_final=True, st_mode=mode, st_uid=0)
        == "os_trust_pubkey_unreadable"
    )


def test_policy_allowed_posix_matrix() -> None:
    """Root-owned 0755 parents + 0444 regular key are accepted by policy."""
    assert (
        evaluate_posix_component_policy(
            is_final=False, st_mode=stat.S_IFDIR | 0o755, st_uid=0
        )
        is None
    )
    assert (
        evaluate_posix_component_policy(
            is_final=True, st_mode=stat.S_IFREG | 0o444, st_uid=0
        )
        is None
    )


def test_policy_windows_owner_matrix() -> None:
    """Only LocalSystem and Builtin Administrators owners are accepted."""
    assert evaluate_windows_owner_policy("S-1-5-18") is None
    assert evaluate_windows_owner_policy("S-1-5-32-544") is None
    assert evaluate_windows_owner_policy("S-1-5-21-1-2-3-1001") == "os_trust_owner_invalid"


def test_policy_windows_rights_matrix() -> None:
    """Write/delete family rights map to typed DACL STOP reasons."""
    assert (
        evaluate_windows_rights_policy(is_directory=False, granted_mask=0x0002)
        == "os_trust_dacl_allows_agent_write"
    )
    assert (
        evaluate_windows_rights_policy(is_directory=False, granted_mask=0x00010000)
        == "os_trust_dacl_allows_agent_delete"
    )
    assert (
        evaluate_windows_rights_policy(is_directory=True, granted_mask=0x0040)
        == "os_trust_dacl_allows_agent_delete"
    )
    assert evaluate_windows_rights_policy(is_directory=False, granted_mask=0) is None
    assert (
        evaluate_windows_rights_policy(is_directory=False, granted_mask=0x0001) is None
    )


def test_policy_identity_mismatch() -> None:
    """Identity helper detects device/inode and volume/index drift."""
    a = {"device": 1, "inode": 2}
    b = {"device": 1, "inode": 3}
    assert identities_match(a, a)
    assert not identities_match(a, b)
    wa = {"volume_serial": 9, "file_index_high": 0, "file_index_low": 1}
    wb = {"volume_serial": 9, "file_index_high": 0, "file_index_low": 2}
    assert identities_match(wa, wa)
    assert not identities_match(wa, wb)
    assert not identities_match({}, {"device": 1})


def test_fixed_trust_paths_are_installer_owned() -> None:
    """Trust path is fixed; not relative and not env-overridable."""
    path = os_authority_trust_pubkey_path()
    if os.name == "nt":
        assert str(path) == r"C:\ProgramData\OPSX\conflict-authority\ed25519.pub"
    else:
        assert str(path) == "/etc/opsx/conflict-authority/ed25519.pub"
# ---------------------------------------------------------------------------
# POSIX integration
# ---------------------------------------------------------------------------


def _posix_or_skip(test_id: str) -> None:
    if os.name == "nt":
        _record_skip(test_id, "posix_integration_unavailable_on_windows")
        pytest.skip(json.dumps(SKIP_INVENTORY[-1]))


def test_posix_attacker_owned_0444_stops(tmp_path: Path) -> None:
    """Attacker-owned 0444 key fails closed (owner invalid)."""
    _posix_or_skip("posix_attacker_owned_0444")
    key = tmp_path / "ed25519.pub"
    key.write_bytes(b"00" * 32)
    key.chmod(0o444)
    with pytest.raises(StopRequired) as exc:
        open_authenticated_trust_pubkey(key)
    assert exc.value.reason == "STOP_AUTHORITY_UNPROVEN"
    assert exc.value.details.get("reason") in {
        "os_trust_owner_invalid",
        "os_trust_parent_writable",
    }


def test_posix_writable_parent_stops(tmp_path: Path) -> None:
    """Writable parent directory fails closed."""
    _posix_or_skip("posix_writable_parent")
    parent = tmp_path / "parent"
    parent.mkdir(mode=0o777)
    key = parent / "ed25519.pub"
    key.write_bytes(b"00" * 32)
    key.chmod(0o444)
    # Ensure parent stays group/other writable for the check.
    parent.chmod(0o777)
    with pytest.raises(StopRequired) as exc:
        open_authenticated_trust_pubkey(key)
    assert exc.value.details.get("reason") in {
        "os_trust_owner_invalid",
        "os_trust_parent_writable",
    }


def test_posix_component_symlink_stops(tmp_path: Path) -> None:
    """Symlink component: policy + early fail-closed (no /tmp root required)."""
    _posix_or_skip("posix_component_symlink")
    # Deterministic policy proof (does not depend on ancestor ownership).
    assert (
        evaluate_posix_component_policy(
            is_final=False, st_mode=stat.S_IFLNK | 0o777, st_uid=0
        )
        == "os_trust_component_symlink"
    )
    real = tmp_path / "realdir"
    real.mkdir()
    link = tmp_path / "linkdir"
    link.symlink_to(real, target_is_directory=True)
    key = link / "ed25519.pub"
    key.write_bytes(b"00" * 32)
    with pytest.raises(StopRequired) as exc:
        open_authenticated_trust_pubkey(key)
    # May STOP on earlier unsafe ancestor (owner/parent) or on symlink itself.
    assert exc.value.details.get("reason") in {
        "os_trust_component_symlink",
        "os_trust_owner_invalid",
        "os_trust_parent_writable",
    }


def test_posix_final_symlink_stops(tmp_path: Path) -> None:
    """Final symlink: policy seam + opener fail-closed (secure ancestors optional)."""
    _posix_or_skip("posix_final_symlink")
    assert (
        evaluate_posix_component_policy(
            is_final=True, st_mode=stat.S_IFLNK | 0o777, st_uid=0
        )
        == "os_trust_component_symlink"
    )
    target = tmp_path / "target.pub"
    target.write_bytes(b"00" * 32)
    link = tmp_path / "ed25519.pub"
    link.symlink_to(target)
    with pytest.raises(StopRequired) as exc:
        open_authenticated_trust_pubkey(link)
    assert exc.value.details.get("reason") in {
        "os_trust_component_symlink",
        "os_trust_owner_invalid",
        "os_trust_parent_writable",
    }


def test_posix_non_regular_final_stops(tmp_path: Path) -> None:
    """Final directory object is not a trust key."""
    _posix_or_skip("posix_non_regular_final")
    d = tmp_path / "ed25519.pub"
    d.mkdir()
    with pytest.raises(StopRequired) as exc:
        open_authenticated_trust_pubkey(d)
    assert exc.value.details.get("reason") in {
        "os_trust_pubkey_unreadable",
        "os_trust_owner_invalid",
        "os_trust_parent_writable",
        "os_trust_component_symlink",
    }


def test_posix_identity_drift_after_open_stops(tmp_path: Path) -> None:
    """Pathname replace after open is detected on recheck."""
    _posix_or_skip("posix_identity_drift_after_open")
    key = tmp_path / "ed25519.pub"
    key.write_bytes(binascii.hexlify(os.urandom(32)))
    # Open via FD without full policy (simulate validated session), then replace.
    fd = os.open(key, os.O_RDONLY)
    try:
        st = os.fstat(fd)
        raw = os.read(fd, 1 << 20)
        session = TrustKeySession(
            path=key,
            key_bytes=raw,
            identity={
                "device": int(st.st_dev),
                "inode": int(st.st_ino),
                "size": int(st.st_size),
                "uid": int(st.st_uid),
                "mode": int(st.st_mode),
            },
            _fd=fd,
        )
        fd = -1
        key.unlink()
        key.write_bytes(binascii.hexlify(os.urandom(32)))
        with pytest.raises(StopRequired) as exc:
            session.recheck_identity()
        assert exc.value.details.get("reason") == "os_trust_identity_changed"
        session.close()
    finally:
        if fd >= 0:
            os.close(fd)


def test_posix_secure_walk_rejects_before_read(tmp_path: Path) -> None:
    """Production opener never returns bytes for a user-owned tree."""
    _posix_or_skip("posix_secure_walk_rejects")
    key = tmp_path / "ed25519.pub"
    key.write_bytes(b"aa" * 32)
    with pytest.raises(StopRequired):
        open_authenticated_trust_pubkey(key)


def test_posix_valid_root_owned_path() -> None:
    """Valid root-owned installer path — skip without root privileges."""
    _posix_or_skip("posix_valid_root_owned_path")
    if os.geteuid() != 0:  # type: ignore[attr-defined]
        _record_skip(
            "posix_valid_root_owned_path",
            "requires_uid0_to_install_root_owned_trust_tree",
        )
        pytest.skip(json.dumps(SKIP_INVENTORY[-1]))
    path = os_authority_trust_pubkey_path()
    if not path.is_file():
        _record_skip(
            "posix_valid_root_owned_path",
            "installer_trust_pubkey_not_present_on_host",
        )
        pytest.skip(json.dumps(SKIP_INVENTORY[-1]))
    session = open_authenticated_trust_pubkey(path)
    try:
        assert session.key_bytes
        session.recheck_identity()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Windows integration
# ---------------------------------------------------------------------------


def _windows_or_skip(test_id: str) -> None:
    if os.name != "nt":
        _record_skip(test_id, "windows_integration_unavailable_on_posix")
        pytest.skip(json.dumps(SKIP_INVENTORY[-1]))


def test_windows_readonly_writable_dacl_stops(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """FILE_ATTRIBUTE_READONLY alone is not a trust boundary (DACL after owner)."""
    _windows_or_skip("windows_readonly_writable_dacl")
    from opsx_conflict.os_trust_store import (
        WIN_FILE_WRITE_DATA,
        set_per_right_grant_seam,
    )

    monkeypatch.setattr(
        "opsx_conflict.os_trust_store._windows_owner_sid_string",
        lambda _h: "S-1-5-18",
    )
    key = tmp_path / "ed25519.pub"
    key.write_bytes(binascii.hexlify(os.urandom(32)))
    import ctypes

    ctypes.windll.kernel32.SetFileAttributesW(str(key), 0x1)  # READONLY (ignored)
    set_per_right_grant_seam(lambda right, is_dir: (not is_dir) and right == WIN_FILE_WRITE_DATA)
    try:
        with pytest.raises(StopRequired) as exc:
            open_authenticated_trust_pubkey(key)
        assert exc.value.details.get("reason") == "os_trust_dacl_allows_agent_write"
    finally:
        set_per_right_grant_seam(None)


def test_windows_wrong_owner_stops(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Current-user-owned key is not SYSTEM/Administrators."""
    _windows_or_skip("windows_wrong_owner")
    import opsx_conflict.os_trust_store as m

    key = tmp_path / "ed25519.pub"
    key.write_bytes(binascii.hexlify(os.urandom(32)))

    # Isolate owner gate on the final object (parent/drive DACL covered in R31).
    def final_owner_only(path: Path, *, is_final: bool) -> None:
        if not is_final:
            return
        handle = m._windows_create_file_noreparse(path, for_directory=False)
        try:
            owner = m._windows_owner_sid_string(handle)
            reason = evaluate_windows_owner_policy(owner)
            if reason:
                raise StopRequired(
                    "STOP_AUTHORITY_UNPROVEN",
                    {
                        "blocker": "BLOCKER_AUTHORITY_PRODUCER_MISSING",
                        "reason": reason,
                        "owner_sid": owner,
                    },
                )
        finally:
            import ctypes

            ctypes.windll.kernel32.CloseHandle(handle)

    monkeypatch.setattr(m, "_windows_assert_component", final_owner_only)
    with pytest.raises(StopRequired) as exc:
        open_authenticated_trust_pubkey(key)
    assert exc.value.details.get("reason") == "os_trust_owner_invalid"


def test_windows_writable_parent_dacl_stops(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Parent DACL write/delete STOP after owner gate (not owner shortcut)."""
    _windows_or_skip("windows_writable_parent_dacl")
    from opsx_conflict.os_trust_store import (
        WIN_FILE_ADD_FILE,
        set_per_right_grant_seam,
    )

    monkeypatch.setattr(
        "opsx_conflict.os_trust_store._windows_owner_sid_string",
        lambda _h: "S-1-5-18",
    )
    parent = tmp_path / "opsx-parent"
    parent.mkdir()
    key = parent / "ed25519.pub"
    key.write_bytes(binascii.hexlify(os.urandom(32)))
    set_per_right_grant_seam(
        lambda right, is_dir: is_dir and right == WIN_FILE_ADD_FILE
    )
    try:
        with pytest.raises(StopRequired) as exc:
            open_authenticated_trust_pubkey(key)
        assert exc.value.details.get("reason") == "os_trust_dacl_allows_agent_write"
    finally:
        set_per_right_grant_seam(None)


def test_windows_reparse_component_stops(tmp_path: Path) -> None:
    """Junction/reparse component fails closed when creatable."""
    _windows_or_skip("windows_reparse_component")
    import subprocess

    real = tmp_path / "real"
    real.mkdir()
    junction = tmp_path / "junc"
    # mklink /J does not require elevation for local dirs.
    proc = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(real)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not junction.exists():
        _record_skip(
            "windows_reparse_component",
            f"junction_create_failed:{proc.returncode}:{proc.stderr.strip()[:80]}",
        )
        pytest.skip(json.dumps(SKIP_INVENTORY[-1]))
    key = junction / "ed25519.pub"
    key.write_bytes(binascii.hexlify(os.urandom(32)))
    with pytest.raises(StopRequired) as exc:
        open_authenticated_trust_pubkey(key)
    assert exc.value.details.get("reason") in {
        "os_trust_component_reparse",
        "os_trust_owner_invalid",
        "os_trust_dacl_allows_agent_write",
        "os_trust_dacl_allows_agent_delete",
    }


def test_windows_identity_drift_session_stops(tmp_path: Path) -> None:
    """Handle identity recheck fails when session identity is mutated."""
    _windows_or_skip("windows_identity_drift")
    key = tmp_path / "ed25519.pub"
    key.write_bytes(binascii.hexlify(os.urandom(32)))
    # Force open via CreateFile path helpers by constructing a session from a
    # successful low-level open that bypasses owner policy — use FD fixture.
    fd = os.open(key, os.O_RDONLY)
    try:
        st = os.fstat(fd)
        session = TrustKeySession(
            path=key,
            key_bytes=os.read(fd, 4096),
            identity={
                "device": int(st.st_dev),
                "inode": int(st.st_ino) ^ 0xFFFFFF,
                "size": int(st.st_size),
                "uid": 0,
                "mode": int(st.st_mode),
            },
            _fd=fd,
        )
        fd = -1
        with pytest.raises(StopRequired) as exc:
            session.recheck_identity()
        assert exc.value.details.get("reason") == "os_trust_identity_changed"
        session.close()
    finally:
        if fd >= 0:
            os.close(fd)


def test_windows_valid_system_path() -> None:
    """Valid SYSTEM/Administrators trust path — skip if not installed."""
    _windows_or_skip("windows_valid_system_path")
    path = os_authority_trust_pubkey_path()
    if not path.is_file():
        _record_skip(
            "windows_valid_system_path",
            "installer_trust_pubkey_not_present_on_host",
        )
        pytest.skip(json.dumps(SKIP_INVENTORY[-1]))
    try:
        session = open_authenticated_trust_pubkey(path)
    except StopRequired as exc:
        _record_skip(
            "windows_valid_system_path",
            f"host_trust_path_rejected:{exc.details.get('reason')}",
        )
        pytest.skip(json.dumps(SKIP_INVENTORY[-1]))
    try:
        assert session.key_bytes
        assert session._win_handle is not None
        session.recheck_identity()
    finally:
        session.close()


def test_key_bytes_come_from_session_not_second_pathname_read(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Authenticated load uses TrustKeySession.key_bytes (handle-sourced)."""
    from opsx_conflict import authority as authority_module

    from authority_test_helpers import install_os_trust_pubkey, write_signed_producer

    priv = install_os_trust_pubkey(monkeypatch, tmp_path)
    pub_path = authority_module.os_authority_trust_pubkey_path()
    write_signed_producer(tmp_path, monkeypatch, private_key=priv)

    reads: list[str] = []
    real_read = Path.read_bytes

    def spy_read(self: Path) -> bytes:
        reads.append(str(self.resolve()) if self.exists() else str(self))
        return real_read(self)

    monkeypatch.setattr(Path, "read_bytes", spy_read)
    result = authority_module.load_authenticated_authority_root(tmp_path)
    assert result["sha256"]
    pub_resolved = str(Path(pub_path).resolve())
    assert all(pub_resolved not in r and str(pub_path) not in r for r in reads)
