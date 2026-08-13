"""R31: per-right Windows DACL AccessCheck + drive-root policy tests."""

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
    FORBIDDEN_DIRECTORY_RIGHTS,
    FORBIDDEN_FILE_RIGHTS,
    WIN_DELETE,
    WIN_FILE_DELETE_CHILD,
    WIN_FILE_WRITE_DATA,
    WIN_WRITE_DAC,
    WIN_WRITE_OWNER,
    _windows_assert_component,
    _windows_granted_access_mask,
    evaluate_posix_component_policy,
    evaluate_windows_owner_policy,
    evaluate_windows_rights_policy,
    merge_per_right_grants,
    open_authenticated_trust_pubkey,
    set_per_right_grant_seam,
)

SKIP_INVENTORY: list[dict[str, str]] = []


def _record_skip(test_id: str, reason: str) -> None:
    """Append a structured skip row for ship SKIP_INVENTORY consumption."""
    SKIP_INVENTORY.append(
        {"test_id": test_id, "platform": sys.platform, "reason": reason}
    )


# ---------------------------------------------------------------------------
# Platform-independent effective-mask adapter (must never skip)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("right", "is_directory", "expected"),
    [
        (WIN_FILE_WRITE_DATA, False, "os_trust_dacl_allows_agent_write"),
        (WIN_DELETE, False, "os_trust_dacl_allows_agent_delete"),
        (WIN_WRITE_DAC, False, "os_trust_dacl_allows_agent_write"),
        (WIN_WRITE_OWNER, False, "os_trust_dacl_allows_agent_write"),
        (WIN_FILE_DELETE_CHILD, True, "os_trust_dacl_allows_agent_delete"),
    ],
)
def test_merge_single_forbidden_right_never_collapses_to_zero(
    right: int, is_directory: bool, expected: str
) -> None:
    """A single granted forbidden right must remain visible in the mask."""
    rights = FORBIDDEN_DIRECTORY_RIGHTS if is_directory else FORBIDDEN_FILE_RIGHTS
    grants = {r: (r == right) for r in rights}
    mask = merge_per_right_grants(grants, is_directory=is_directory)
    assert mask == right
    assert mask != 0
    assert (
        evaluate_windows_rights_policy(is_directory=is_directory, granted_mask=mask)
        == expected
    )


def test_merge_partial_subset_of_rights_stops() -> None:
    """Arbitrary subset of forbidden rights must not convert to zero."""
    grants = {
        WIN_FILE_WRITE_DATA: True,
        WIN_WRITE_DAC: True,
        WIN_DELETE: False,
    }
    # Fill remaining file rights as denied.
    for right in FORBIDDEN_FILE_RIGHTS:
        grants.setdefault(right, False)
    mask = merge_per_right_grants(grants, is_directory=False)
    assert mask == (WIN_FILE_WRITE_DATA | WIN_WRITE_DAC)
    assert (
        evaluate_windows_rights_policy(is_directory=False, granted_mask=mask)
        == "os_trust_dacl_allows_agent_write"
    )


def test_merge_mask_zero_passes_dacl_policy() -> None:
    """Effective forbidden mask=0 is accepted by DACL policy."""
    grants = {r: False for r in FORBIDDEN_FILE_RIGHTS}
    mask = merge_per_right_grants(grants, is_directory=False)
    assert mask == 0
    assert evaluate_windows_rights_policy(is_directory=False, granted_mask=0) is None


def test_access_check_seam_single_write_data_stops() -> None:
    """Seam: only FILE_WRITE_DATA granted → STOP (not owner shortcut)."""
    set_per_right_grant_seam(lambda right, _is_dir: right == WIN_FILE_WRITE_DATA)
    try:
        # Simulate granted-mask path used by opener after owner gate.
        grants = {
            r: (r == WIN_FILE_WRITE_DATA) for r in FORBIDDEN_FILE_RIGHTS
        }
        mask = merge_per_right_grants(grants, is_directory=False)
        reason = evaluate_windows_rights_policy(
            is_directory=False, granted_mask=mask
        )
        assert reason == "os_trust_dacl_allows_agent_write"
        assert evaluate_windows_owner_policy("S-1-5-18") is None
    finally:
        set_per_right_grant_seam(None)


def test_access_check_seam_delete_only_stops() -> None:
    """Seam: only DELETE granted → STOP."""
    set_per_right_grant_seam(lambda right, _is_dir: right == WIN_DELETE)
    try:
        mask = merge_per_right_grants(
            {r: (r == WIN_DELETE) for r in FORBIDDEN_FILE_RIGHTS},
            is_directory=False,
        )
        assert (
            evaluate_windows_rights_policy(is_directory=False, granted_mask=mask)
            == "os_trust_dacl_allows_agent_delete"
        )
    finally:
        set_per_right_grant_seam(None)


def test_access_check_seam_write_dac_and_owner_stop() -> None:
    """Seam: WRITE_DAC-only and WRITE_OWNER-only each STOP."""
    for right in (WIN_WRITE_DAC, WIN_WRITE_OWNER):
        mask = merge_per_right_grants(
            {r: (r == right) for r in FORBIDDEN_FILE_RIGHTS},
            is_directory=False,
        )
        assert mask == right
        assert (
            evaluate_windows_rights_policy(is_directory=False, granted_mask=mask)
            == "os_trust_dacl_allows_agent_write"
        )


def test_access_check_seam_delete_child_on_directory_stops() -> None:
    """Seam: only FILE_DELETE_CHILD on a directory → STOP."""
    mask = merge_per_right_grants(
        {r: (r == WIN_FILE_DELETE_CHILD) for r in FORBIDDEN_DIRECTORY_RIGHTS},
        is_directory=True,
    )
    assert mask == WIN_FILE_DELETE_CHILD
    assert (
        evaluate_windows_rights_policy(is_directory=True, granted_mask=mask)
        == "os_trust_dacl_allows_agent_delete"
    )


# ---------------------------------------------------------------------------
# Windows DACL tests that pass the owner gate first
# ---------------------------------------------------------------------------


def _force_allowed_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pass owner gate so DACL outcome is the asserted failure mode."""
    monkeypatch.setattr(
        "opsx_conflict.os_trust_store._windows_owner_sid_string",
        lambda _handle: "S-1-5-18",
    )
    assert evaluate_windows_owner_policy("S-1-5-18") is None


def _windows_or_skip(test_id: str) -> None:
    if os.name != "nt":
        _record_skip(test_id, "windows_integration_unavailable_on_posix")
        pytest.skip(json.dumps(SKIP_INVENTORY[-1]))


def test_windows_dacl_write_only_after_owner_gate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Readonly+writable DACL proves DACL STOP after owner gate passes."""
    _windows_or_skip("windows_dacl_write_only_after_owner")
    _force_allowed_owner(monkeypatch)
    key = tmp_path / "ed25519.pub"
    key.write_bytes(binascii.hexlify(os.urandom(32)))
    import ctypes

    ctypes.windll.kernel32.SetFileAttributesW(str(key), 0x1)  # READONLY (ignored)

    set_per_right_grant_seam(lambda right, _d: right == WIN_FILE_WRITE_DATA)
    # Also force parent components through the same seam + allowed owner.
    monkeypatch.setattr(
        "opsx_conflict.os_trust_store._windows_assert_component",
        lambda path, *, is_final: _assert_component_dacl_only(
            path, is_final=is_final, monkeypatch=monkeypatch
        ),
    )
    try:
        with pytest.raises(StopRequired) as exc:
            open_authenticated_trust_pubkey(key)
        assert exc.value.details.get("reason") == "os_trust_dacl_allows_agent_write"
        assert exc.value.details.get("reason") != "os_trust_owner_invalid"
    finally:
        set_per_right_grant_seam(None)


def _assert_component_dacl_only(
    path: Path, *, is_final: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Component check with forced owner; DACL from seam/native mask."""
    del monkeypatch
    from opsx_conflict import os_trust_store as m

    if m._windows_is_drive_root(path):
        # Drive root: still evaluate directory DACL via seam.
        granted = merge_per_right_grants(
            {r: bool(m._PER_RIGHT_GRANT_SEAM and m._PER_RIGHT_GRANT_SEAM(r, True)) for r in FORBIDDEN_DIRECTORY_RIGHTS}
            if m._PER_RIGHT_GRANT_SEAM
            else {r: False for r in FORBIDDEN_DIRECTORY_RIGHTS},
            is_directory=True,
        )
        # When testing file write-only, parents may be clean.
        reason = evaluate_windows_rights_policy(
            is_directory=True, granted_mask=granted
        )
        if reason:
            raise StopRequired(
                "STOP_AUTHORITY_UNPROVEN",
                {"blocker": "BLOCKER_AUTHORITY_PRODUCER_MISSING", "reason": reason},
            )
        return
    if is_final:
        handle = m._windows_create_file_noreparse(path, for_directory=False)
        try:
            granted = m._windows_granted_access_mask(handle, is_directory=False)
            reason = evaluate_windows_rights_policy(
                is_directory=False, granted_mask=granted
            )
            if reason:
                raise StopRequired(
                    "STOP_AUTHORITY_UNPROVEN",
                    {
                        "blocker": "BLOCKER_AUTHORITY_PRODUCER_MISSING",
                        "reason": reason,
                        "granted_mask": hex(granted),
                    },
                )
        finally:
            import ctypes

            ctypes.windll.kernel32.CloseHandle(handle)
        return
    # Intermediate dirs: allow when seam denies directory rights.
    granted = merge_per_right_grants(
        {
            r: bool(m._PER_RIGHT_GRANT_SEAM and m._PER_RIGHT_GRANT_SEAM(r, True))
            for r in FORBIDDEN_DIRECTORY_RIGHTS
        }
        if m._PER_RIGHT_GRANT_SEAM
        else {r: False for r in FORBIDDEN_DIRECTORY_RIGHTS},
        is_directory=True,
    )
    reason = evaluate_windows_rights_policy(is_directory=True, granted_mask=granted)
    if reason:
        raise StopRequired(
            "STOP_AUTHORITY_UNPROVEN",
            {"blocker": "BLOCKER_AUTHORITY_PRODUCER_MISSING", "reason": reason},
        )


@pytest.mark.parametrize(
    ("seam_right", "is_directory", "expected"),
    [
        (WIN_FILE_WRITE_DATA, False, "os_trust_dacl_allows_agent_write"),
        (WIN_DELETE, False, "os_trust_dacl_allows_agent_delete"),
        (WIN_WRITE_DAC, False, "os_trust_dacl_allows_agent_write"),
        (WIN_WRITE_OWNER, False, "os_trust_dacl_allows_agent_write"),
        (WIN_FILE_DELETE_CHILD, True, "os_trust_dacl_allows_agent_delete"),
    ],
)
def test_windows_granted_mask_uses_seam_per_right(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    seam_right: int,
    is_directory: bool,
    expected: str,
) -> None:
    """Native _windows_granted_access_mask honors per-right seam (owner passed)."""
    _windows_or_skip(f"windows_seam_{seam_right:x}")
    _force_allowed_owner(monkeypatch)
    target = tmp_path / ("dir" if is_directory else "ed25519.pub")
    if is_directory:
        target.mkdir()
    else:
        target.write_bytes(b"00" * 32)
    from opsx_conflict import os_trust_store as m

    handle = m._windows_create_file_noreparse(target, for_directory=is_directory)
    set_per_right_grant_seam(lambda right, _d: right == seam_right)
    try:
        mask = _windows_granted_access_mask(handle, is_directory=is_directory)
        assert mask == seam_right
        assert (
            evaluate_windows_rights_policy(
                is_directory=is_directory, granted_mask=mask
            )
            == expected
        )
    finally:
        set_per_right_grant_seam(None)
        import ctypes

        ctypes.windll.kernel32.CloseHandle(handle)


def test_drive_root_dacl_checked_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive/volume root must not skip effective-rights verification."""
    _windows_or_skip("windows_drive_root_dacl")
    _force_allowed_owner(monkeypatch)
    # Grant FILE_ADD_FILE on directory root via seam → STOP.
    set_per_right_grant_seam(lambda right, is_dir: is_dir and right == WIN_FILE_WRITE_DATA)
    try:
        root = Path(os_authority_drive_root())
        with pytest.raises(StopRequired) as exc:
            _windows_assert_component(root, is_final=False)
        assert exc.value.details.get("reason") in {
            "os_trust_dacl_allows_agent_write",
            "os_trust_dacl_allows_agent_delete",
        }
        assert exc.value.details.get("reason") != "os_trust_owner_invalid"
    finally:
        set_per_right_grant_seam(None)


def os_authority_drive_root() -> str:
    """Return the drive root of the fixed Windows trust path."""
    return str(Path(r"C:\ProgramData\OPSX\conflict-authority\ed25519.pub").anchor)


def test_windows_owner_gate_passed_delete_only_dacl(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Delete-only DACL STOP after owner gate; not owner_invalid."""
    _windows_or_skip("windows_delete_only_after_owner")
    _force_allowed_owner(monkeypatch)
    key = tmp_path / "ed25519.pub"
    key.write_bytes(binascii.hexlify(os.urandom(32)))
    set_per_right_grant_seam(lambda right, _d: right == WIN_DELETE)
    monkeypatch.setattr(
        "opsx_conflict.os_trust_store._windows_assert_component",
        lambda path, *, is_final: _assert_component_dacl_only(
            path, is_final=is_final, monkeypatch=monkeypatch
        ),
    )
    try:
        with pytest.raises(StopRequired) as exc:
            open_authenticated_trust_pubkey(key)
        assert exc.value.details.get("reason") == "os_trust_dacl_allows_agent_delete"
        assert "owner_invalid" not in str(exc.value.details.get("reason"))
    finally:
        set_per_right_grant_seam(None)


def test_windows_native_system_owned_dacl_fixture_unavailable() -> None:
    """Machine-readable skip: cannot mint SYSTEM-owned DACL without privileges."""
    _windows_or_skip("windows_native_system_owned_dacl")
    _record_skip(
        "windows_native_system_owned_dacl",
        "cannot_create_system_owned_object_without_new_privileges",
    )
    pytest.skip(json.dumps(SKIP_INVENTORY[-1]))


# ---------------------------------------------------------------------------
# POSIX symlink fixtures: policy seam + secure-ancestor open
# ---------------------------------------------------------------------------


def test_posix_symlink_policy_deterministic_seam() -> None:
    """Symlink mode is rejected by policy without opening /tmp ancestors."""
    mode = stat.S_IFLNK | 0o777
    assert (
        evaluate_posix_component_policy(is_final=False, st_mode=mode, st_uid=0)
        == "os_trust_component_symlink"
    )
    assert (
        evaluate_posix_component_policy(is_final=True, st_mode=mode, st_uid=0)
        == "os_trust_component_symlink"
    )


def test_posix_final_symlink_with_secure_ancestor_seam(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Final symlink STOP without requiring a real root-owned /tmp tree."""
    if os.name == "nt":
        _record_skip(
            "posix_final_symlink_secure_ancestors",
            "posix_integration_unavailable_on_windows",
        )
        pytest.skip(json.dumps(SKIP_INVENTORY[-1]))

    import opsx_conflict.os_trust_store as m

    target = tmp_path / "target.pub"
    target.write_bytes(b"00" * 32)
    link = tmp_path / "ed25519.pub"
    link.symlink_to(target)

    real_lstat = os.lstat
    # Capture identity before patching — never call Path.resolve() inside the
    # patched lstat (it re-enters lstat and RecursionError's on POSIX).
    link_identity = real_lstat(link)

    def fake_lstat(path: str | bytes | os.PathLike[str]) -> os.stat_result:
        st = real_lstat(path)
        if (
            stat.S_ISLNK(st.st_mode)
            and st.st_ino == link_identity.st_ino
            and st.st_dev == link_identity.st_dev
        ):
            return st
        seq = list(st)
        seq[0] = stat.S_IFDIR | 0o755
        seq[4] = 0
        seq[5] = 0
        return os.stat_result(seq)

    monkeypatch.setattr(m.os, "lstat", fake_lstat)
    # Skip O_DIRECTORY open probes that would observe real non-root ownership.
    monkeypatch.setattr(m.os, "O_DIRECTORY", 0, raising=False)

    with pytest.raises(StopRequired) as exc:
        open_authenticated_trust_pubkey(link)
    assert exc.value.details.get("reason") == "os_trust_component_symlink"


def test_posix_component_symlink_policy_without_tmp_walk() -> None:
    """Component symlink fail-closed is proven via policy (no /tmp dependency)."""
    assert (
        evaluate_posix_component_policy(
            is_final=False, st_mode=stat.S_IFLNK | 0o777, st_uid=0
        )
        == "os_trust_component_symlink"
    )
