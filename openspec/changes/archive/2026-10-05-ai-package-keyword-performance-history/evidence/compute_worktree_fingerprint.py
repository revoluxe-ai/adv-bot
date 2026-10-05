#!/usr/bin/env python3
"""Compute WORKTREE_FINGERPRINT for keyword-performance evidence freshness.

Manifest: sorted LF-normalized sha256 per path under implementation scope.
Excludes generated evidence/report outputs to avoid circular hash dependency.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]
CHANGE_ROOT = pathlib.Path(__file__).resolve().parents[1]

INCLUDE_GLOBS = (
    "app/modules/ai_package_v1/keyword_performance/**/*.py",
    "app/modules/ai_package_v1/keyword_performance/**/*.sql",
    "app/modules/ai_package_v1/export/export_service.py",
    "app/modules/ai_package_v1/validator/package_validator.py",
    "app/modules/ai_package_v1/domain/enums.py",
    "tests/unit/ai_package_v1/keyword_performance/**/*.py",
    "tests/unit/ai_package_v1/test_export_settings_integration.py",
    "tests/unit/ai_package_v1/conftest.py",
    "pyrightconfig_strict.json",
)

EXCLUDE_PARTS = (
    "openspec/changes/ai-package-keyword-performance-history/evidence/",
    "openspec/changes/ai-package-keyword-performance-history/scenario-coverage/audit.receipt.json",
)


def lf_sha256(path: pathlib.Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def collect_paths() -> list[pathlib.Path]:
    found: set[pathlib.Path] = set()
    for pattern in INCLUDE_GLOBS:
        for path in REPO_ROOT.glob(pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(REPO_ROOT).as_posix()
            if any(part in rel for part in EXCLUDE_PARTS):
                continue
            found.add(path)
    return sorted(found, key=lambda p: p.relative_to(REPO_ROOT).as_posix())


def compute_fingerprint() -> dict[str, object]:
    entries: list[dict[str, str]] = []
    for path in collect_paths():
        rel = path.relative_to(REPO_ROOT).as_posix()
        entries.append({"path": rel, "content_hash": lf_sha256(path)})
    manifest_json = json.dumps(entries, sort_keys=False, separators=(",", ":"))
    fingerprint = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()
    return {
        "WORKTREE_FINGERPRINT": fingerprint,
        "MANIFEST_PATH_COUNT": len(entries),
        "MANIFEST": entries,
    }


def main() -> int:
    result = compute_fingerprint()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
