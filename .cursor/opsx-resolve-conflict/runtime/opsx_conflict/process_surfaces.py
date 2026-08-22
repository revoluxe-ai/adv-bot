"""Machine-readable process-surface registry."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .pathsafety import normalize_repo_rel

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_REGISTRY_PATH = _PACKAGE_ROOT / "process_surfaces.json"


@lru_cache(maxsize=1)
def load_process_surfaces() -> dict:
    """Load process_surfaces.json shipped with the package."""
    return json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))


def norm_rel(path: str | Path) -> str:
    """Normalize relative path; never use lstrip('.') (breaks .github/)."""
    return normalize_repo_rel(path)


def is_protected_process_path(path: str) -> bool:
    """True if path is a process/OPSX governance surface (HIGH write risk)."""
    rel = norm_rel(path)
    reg = load_process_surfaces()
    if rel in set(reg.get("exact", [])):
        return True
    for prefix in reg.get("prefixes", []):
        if rel.startswith(prefix):
            return True
    for prefix in reg.get("pattern_prefixes", []):
        if rel.startswith(prefix):
            return True
    return False


def classify_path_risk(path: str, *, topology: str | None = None) -> str:
    """Return LOW|MEDIUM|HIGH risk class for a conflict path."""
    rel = norm_rel(path)
    if topology in {"binary", "symlink", "submodule", "directory/file", "file-mode"}:
        return "HIGH"
    if is_protected_process_path(rel):
        return "HIGH"
    if rel.startswith("alembic_") or "/migrations/" in f"/{rel}/":
        return "HIGH"
    if rel.endswith((".lock", "poetry.lock", "package-lock.json")):
        return "HIGH"
    if rel.startswith("app/") or rel.startswith("tests/"):
        return "MEDIUM"
    return "LOW"
