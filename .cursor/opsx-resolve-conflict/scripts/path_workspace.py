"""Native artifact workspace and path-flavor separation (R32).

Filesystem I/O for shipping/replay uses only native OS paths from
``tempfile.gettempdir()`` or ``OPSX_REVIEW_OUT_DIR``.

Foreign-platform samples must use ``PureWindowsPath`` / ``PurePosixPath``
(or plain strings) and must never be passed to open/mkdir/stat/resolve.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath

# Env override for operators who want a stable native output directory.
OUT_DIR_ENV = "OPSX_REVIEW_OUT_DIR"


def native_artifact_root() -> Path:
    """Return a native directory for real archive/replay/test artifacts."""
    override = os.environ.get(OUT_DIR_ENV, "").strip()
    root = Path(override) if override else Path(tempfile.gettempdir())
    root = assert_native_io_path(root, role="artifact_root")
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def looks_like_windows_drive_path(sample: str) -> bool:
    """True if *sample* is a Windows drive or UNC path string."""
    s = sample.replace("/", "\\")
    if s.startswith("\\\\"):
        return True
    return bool(re.match(r"^[A-Za-z]:\\", s)) or bool(re.match(r"^[A-Za-z]:/", sample))


def looks_like_posix_absolute_path(sample: str) -> bool:
    """True if *sample* is a POSIX absolute path string (not a Windows drive)."""
    if looks_like_windows_drive_path(sample):
        return False
    return sample.startswith("/")


def has_mixed_separators(sample: str) -> bool:
    """True when both backslash and slash appear in a path-like sample."""
    return ("\\" in sample) and ("/" in sample)


def assert_native_io_path(path: Path | str, *, role: str = "path") -> Path:
    """Fail closed if a foreign-platform path is used for real filesystem I/O."""
    sample = os.fspath(path)
    if has_mixed_separators(sample) and looks_like_windows_drive_path(sample):
        raise SystemExit(
            f"portability STOP: mixed-separator path used for native I/O "
            f"({role}): {sample!r}"
        )
    if os.name == "nt":
        if looks_like_posix_absolute_path(sample) and not sample.startswith("\\\\"):
            # Allow only if it is a real existing native path (rare); otherwise STOP.
            candidate = Path(sample)
            if not candidate.exists():
                raise SystemExit(
                    f"portability STOP: foreign POSIX path used for native I/O "
                    f"({role}): {sample!r}"
                )
    else:
        if looks_like_windows_drive_path(sample) or "\\" in sample:
            raise SystemExit(
                f"portability STOP: foreign Windows path used for native I/O "
                f"({role}): {sample!r}"
            )
    return Path(sample)


def synthetic_windows_path(*parts: str) -> PureWindowsPath:
    """Build a PureWindowsPath sample (never for filesystem I/O)."""
    if not parts:
        return PureWindowsPath("C:\\")
    return PureWindowsPath(parts[0]).joinpath(*parts[1:])


def synthetic_posix_path(*parts: str) -> PurePosixPath:
    """Build a PurePosixPath sample (never for filesystem I/O)."""
    if not parts:
        return PurePosixPath("/")
    return PurePosixPath(parts[0]).joinpath(*parts[1:])


def scan_source_for_hardcoded_windows_temp(text: str, *, label: str) -> None:
    """Reject shipping sources that hardcode Windows temp for I/O."""
    needles = (
        'Path(r"C:\\Temp")',
        "Path(r'C:\\Temp')",
        'Path("C:\\\\Temp")',
        "Path('C:\\\\Temp')",
        'OUT_DIR = Path(r"C:\\Temp")',
    )
    for needle in needles:
        if needle in text:
            raise SystemExit(
                f"portability STOP: hardcoded Windows temp I/O path in {label}: "
                f"{needle!r}"
            )


def platform_id() -> str:
    """Return a short platform id for capability matrix rows."""
    if os.name == "nt":
        return "windows"
    if sys_platform_darwin():
        return "macos"
    return "linux"


def sys_platform_darwin() -> bool:
    """True on macOS."""
    import sys

    return sys.platform == "darwin"
