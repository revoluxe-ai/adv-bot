"""R25/R32 evidence portability, claim coverage, and raw→normalized proofs."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PACKAGE_ROOT / "scripts"

# Frozen R24 README failure sample (must be rejected by R25 claim scanner).
_R24_STALE_README = """
## Single delivery archive

- `C:\\Temp\\OPSX_RESOLVE_CONFLICT_COMMAND_001_R24_REVIEW_BUNDLE.zip`
- `bundle_sha256`: `93032f92e67ecff237ded5129641fa71129205fa71844b69719efdbce96afeea`
- Inner ZIP SHA: `32e3c355fd9edb83c73a04f2a451206f63af04e0d3394fb6082f95d3f0190be0`
- `package_digest`: `49cd86fcd1b130919b56e9b738992e55afa57f0b15940e8eb61eda33637130f0`
- Clean-unpack: 181 passed, 3 skipped
"""


def _load_ship_module():
    """Load ship_review_package.py as a module for validator helpers."""
    path = SCRIPTS / "ship_review_package.py"
    spec = importlib.util.spec_from_file_location("ship_review_package_r25", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_replay_module():
    """Load build_replay_evidence.py helpers."""
    path = SCRIPTS / "build_replay_evidence.py"
    spec = importlib.util.spec_from_file_location("build_replay_evidence_r25", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_path_workspace():
    """Load path_workspace helpers."""
    path = SCRIPTS / "path_workspace.py"
    spec = importlib.util.spec_from_file_location("path_workspace_r32", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_inner_operator_docs_omit_self_referential_delivery_claims() -> None:
    """Inner REVIEW_REQUEST and README_REVIEW omit current-delivery digests."""
    ship = _load_ship_module()
    ship.write_inner_review_request()
    for rel in ("REVIEW_REQUEST.md", "README_REVIEW.md"):
        text = (PACKAGE_ROOT / rel).read_text(encoding="utf-8")
        ship.scan_text_for_forbidden_claims(text, label=rel)
        assert "93032f92" not in text
        assert "181 passed" not in text


def test_validator_rejects_r24_stale_readme_claims() -> None:
    """Post-build claim scanner rejects the R24 README failure mode."""
    ship = _load_ship_module()
    assert ship.is_operator_review_document("README_REVIEW.md", _R24_STALE_README)
    with pytest.raises(SystemExit) as exc:
        ship.scan_text_for_forbidden_claims(
            _R24_STALE_README, label="README_REVIEW.md"
        )
    assert "validator STOP" in str(exc.value)


def test_validator_detects_cross_platform_home_paths() -> None:
    """Synthetic Windows / macOS / Linux home paths cause STOP (OS-independent)."""
    ship = _load_ship_module()
    win = "trace " + "\\".join(
        ("C:", "Users", "ReviewFixture", "workspace", "runtime", "x.py")
    )
    mac = "trace " + "/".join(
        ("", "Users", "ReviewFixture", "workspace", "runtime", "x.py")
    )
    linux = "trace " + "/".join(
        ("", "home", "ReviewFixture", "workspace", "runtime", "x.py")
    )
    for label, poison in (
        ("windows_home", win),
        ("macos_home", mac),
        ("linux_home", linux),
    ):
        with pytest.raises(SystemExit) as exc:
            ship.scan_text_for_forbidden_paths(poison, label=label)
        assert "validator STOP" in str(exc.value)


def test_raw_to_normalized_relationship(tmp_path: Path) -> None:
    """normalize(raw, mapping) reproduces normalized bytes and digests."""
    replay = _load_replay_module()
    staging = tmp_path / "OPSX_R33_NORM_TEST"
    staging.mkdir(parents=True, exist_ok=True)
    package_staging = staging / "package"
    package_staging.mkdir(parents=True, exist_ok=True)
    fixture = staging / "fixtures" / "repo"
    fixture.mkdir(parents=True, exist_ok=True)
    mapping = replay.build_normalization_map(
        staging_root=staging,
        package_staging=package_staging,
        fixture_repos=[fixture],
    )
    raw = f"boot={package_staging / 'runtime' / 'boot.py'} repo={fixture}"
    replay.assert_no_forbidden_paths(raw, label="raw_sample")
    normalized = replay.normalize_text(raw, mapping)
    result = replay.verify_raw_to_normalized(raw, normalized, mapping)
    assert result["ok"] is True
    assert "<PACKAGE_STAGING>" in normalized
    assert str(package_staging) not in normalized


def test_raw_to_normalized_synthetic_windows_and_posix_strings() -> None:
    """Synthetic Pure* paths normalize as strings without filesystem I/O."""
    replay = _load_replay_module()
    win_root = str(PureWindowsPath("C:/Temp/OPSX_R33_NORM_TEST/package"))
    posix_root = str(PurePosixPath("/tmp/OPSX_R33_NORM_TEST/package"))
    mapping = [
        (win_root, "<PACKAGE_STAGING>"),
        (posix_root, "<PACKAGE_STAGING>"),
    ]
    raw_win = "boot=" + str(
        PureWindowsPath("C:/Temp/OPSX_R33_NORM_TEST/package/runtime/boot.py")
    )
    raw_posix = f"boot={posix_root}/runtime/boot.py"
    for raw in (raw_win, raw_posix):
        normalized = replay.normalize_text(raw, mapping)
        result = replay.verify_raw_to_normalized(raw, normalized, mapping)
        assert result["ok"] is True
        assert "<PACKAGE_STAGING>" in normalized


def test_native_workspace_rejects_foreign_windows_path_on_posix() -> None:
    """Foreign Windows drive path cannot be used for native I/O on POSIX."""
    pw = _load_path_workspace()
    if os.name == "nt":
        pytest.skip("foreign Windows rejection is a POSIX-host check")
    with pytest.raises(SystemExit) as exc:
        pw.assert_native_io_path(r"C:\Temp\opsx", role="test")
    assert "foreign Windows path" in str(exc.value)


def test_native_workspace_accepts_tempdir(tmp_path: Path) -> None:
    """Native temp paths are accepted for filesystem I/O."""
    pw = _load_path_workspace()
    accepted = pw.assert_native_io_path(tmp_path, role="tmp")
    assert accepted == Path(tmp_path)


def test_mixed_separator_rejection() -> None:
    """Mixed-separator Windows drive samples are rejected for native I/O."""
    pw = _load_path_workspace()
    sample = r"C:\Temp/OPSX_MIXED/out"
    assert pw.has_mixed_separators(sample)
    if os.name != "nt":
        with pytest.raises(SystemExit):
            pw.assert_native_io_path(sample, role="mixed")


def test_synthetic_pure_paths_are_not_path_io() -> None:
    """PureWindowsPath / PurePosixPath helpers stay non-I/O samples."""
    pw = _load_path_workspace()
    win = pw.synthetic_windows_path("C:\\", "Temp", "x")
    posix = pw.synthetic_posix_path("/", "tmp", "x")
    assert isinstance(win, PureWindowsPath)
    assert isinstance(posix, PurePosixPath)
    assert not hasattr(win, "mkdir") or type(win).mkdir is PureWindowsPath.mkdir


def test_shipping_scripts_have_no_hardcoded_windows_temp() -> None:
    """Post-build style scan: shipping scripts must not hardcode C:\\Temp I/O."""
    ship = _load_ship_module()
    ship.validate_shipping_scripts_portability()


def test_package_version_is_r26() -> None:
    """Current package metadata pin (R40)."""
    ship = _load_ship_module()
    assert ship.PACKAGE_VERSION == "0.40.0"
    assert ship.PACKAGE_NAME.endswith("_R40")
    assert ship.REVISION == "R40"
