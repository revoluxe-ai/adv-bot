#!/usr/bin/env python3
"""Copy-only OPSX portable zip builder (always-all directory roots).

Walks fixed repo-relative roots, preserves paths inside the archive, never
mutates or deletes source trees. New files under those roots are included
automatically on every run.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

# Fixed roots — no scope flags. Missing optional paths are skipped.
INCLUDE_DIR_ROOTS: tuple[str, ...] = (
    ".cursor",
    "openspec",
    ".agents",
    ".github/prompts",
    ".github/skills",
)
INCLUDE_FILES: tuple[str, ...] = (
    "AGENTS.md",
    ".github/copilot-instructions.md",
    ".github/git-commit-instructions.md",
)

# Relative to repo root, or under a packed path (posix-style match).
EXCLUDE_SUFFIXES: tuple[str, ...] = (
    ".zip",
    ".pyc",
)
EXCLUDE_DIR_NAMES: frozenset[str] = frozenset(
    {
        "__pycache__",
        ".git",
        "node_modules",
        ".venv",
        "projects",  # Cursor local project state if present
    }
)


def _posix(path: Path) -> str:
    """Return forward-slash relative path for zip members."""
    return PurePosixPath(path.as_posix()).as_posix()


def _is_excluded(repo_root: Path, path: Path) -> bool:
    """Return True when path must not enter the archive."""
    try:
        rel = path.relative_to(repo_root)
    except ValueError:
        return True
    parts = rel.parts
    if any(part in EXCLUDE_DIR_NAMES for part in parts):
        return True
    # Exclude Cursor IDE settings only at `.cursor/settings.json`.
    if (
        len(parts) >= 2
        and parts[0] == ".cursor"
        and parts[-1] == "settings.json"
    ):
        return True
    if path.name.endswith(EXCLUDE_SUFFIXES):
        return True
    return False


def collect_members(repo_root: Path) -> list[Path]:
    """Collect files under include roots (copy-only inventory)."""
    found: list[Path] = []
    seen: set[Path] = set()

    for root_rel in INCLUDE_DIR_ROOTS:
        root = repo_root / root_rel
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if _is_excluded(repo_root, path):
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            found.append(path)

    for file_rel in INCLUDE_FILES:
        path = repo_root / file_rel
        if not path.is_file():
            continue
        if _is_excluded(repo_root, path):
            continue
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        found.append(path)

    found.sort(key=lambda p: _posix(p.relative_to(repo_root)).lower())
    return found


def build_zip(
    repo_root: Path,
    *,
    dry_run: bool,
    output_dir: Path | None = None,
) -> tuple[Path | None, list[Path], int]:
    """Build zip or return dry-run inventory.

    Returns:
        (zip_path_or_None, member_paths, total_bytes)
    """
    members = collect_members(repo_root)
    total_bytes = sum(p.stat().st_size for p in members)
    if dry_run:
        return None, members, total_bytes

    out_dir = output_dir or (repo_root / "opsx-export")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    zip_path = out_dir / f"opsx-bundle-{stamp}.zip"

    with zipfile.ZipFile(
        zip_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as zf:
        for path in members:
            arcname = _posix(path.relative_to(repo_root))
            zf.write(path, arcname=arcname)

    return zip_path.resolve(), members, total_bytes


def file_uri(path: Path) -> str:
    """Return a file:// URI for the absolute path (Windows-safe)."""
    return path.resolve().as_uri()


def main(argv: list[str] | None = None) -> int:
    """CLI entry: dry-run inventory or write always-all OPSX zip."""
    parser = argparse.ArgumentParser(
        description="Pack OPSX process + OpenSpec trees into a portable zip."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (default: parent of .cursor/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List members only; do not write a zip.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for zip (default: <repo>/opsx-export)",
    )
    args = parser.parse_args(argv)

    if args.repo_root is not None:
        repo_root = args.repo_root.resolve()
    else:
        # This file lives at <repo>/.cursor/opsx-export/export_bundle.py
        repo_root = Path(__file__).resolve().parents[2]

    if not (repo_root / ".cursor").is_dir() and not (repo_root / "openspec").is_dir():
        print(f"ERROR: not an OPSX repo root: {repo_root}", file=sys.stderr)
        return 2

    zip_path, members, total_bytes = build_zip(
        repo_root,
        dry_run=args.dry_run,
        output_dir=args.output_dir.resolve() if args.output_dir else None,
    )

    print(f"REPO_ROOT: {repo_root}")
    print(f"FILE_COUNT: {len(members)}")
    print(f"BYTES: {total_bytes}")
    print("INCLUDE_DIR_ROOTS:")
    for root in INCLUDE_DIR_ROOTS:
        present = (repo_root / root).is_dir()
        print(f"  - {root} ({'present' if present else 'missing'})")
    print("INCLUDE_FILES:")
    for rel in INCLUDE_FILES:
        present = (repo_root / rel).is_file()
        print(f"  - {rel} ({'present' if present else 'missing'})")

    if args.dry_run:
        print("MODE: DRY_RUN")
        for path in members:
            print(f"  {_posix(path.relative_to(repo_root))}")
        return 0

    assert zip_path is not None
    print("MODE: ZIP_WRITTEN")
    print(f"ZIP_ABS_PATH: {zip_path}")
    print(f"FILE_URI: {file_uri(zip_path)}")
    print(f"ZIP_BYTES: {zip_path.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
