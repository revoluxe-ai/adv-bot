"""Helpers for R28 actual OPSX registry (task_type + pack) fixtures."""

from __future__ import annotations

import hashlib
from pathlib import Path


ACTUAL_FULL_REGISTRY = """\
version: 1
modes:
  FULL:
    waves:
      - id: A
        parallel: true
        checks: [pyright-strict, mypy, pytest-unit]
      - id: B
        parallel: false
        after: [pytest-unit]
        require_status: PASS
        checks: [pytest-full]
checks:
  pyright-strict:
    task_type: shell
    pack: .cursor/static-check/checks/pyright-strict
  mypy:
    task_type: shell
    pack: .cursor/static-check/checks/mypy
  pytest-unit:
    task_type: shell
    pack: .cursor/static-check/checks/pytest-unit
  pytest-full:
    task_type: shell
    pack: .cursor/static-check/checks/pytest-full
"""


def write_pack_tree(root: Path, check_id: str) -> dict[str, str]:
    """Write origin-shaped pack files and return relative SHA-256 map."""
    pack = root / ".cursor" / "static-check" / "checks" / check_id
    pack.mkdir(parents=True, exist_ok=True)
    files = {
        "context.md": f"# context for {check_id}\n",
        "instructions.md": f"# instructions for {check_id}\n",
    }
    hashes: dict[str, str] = {}
    for name, text in files.items():
        path = pack / name
        raw = text.encode("utf-8")
        path.write_bytes(raw)
        rel = path.relative_to(root).as_posix()
        hashes[rel] = hashlib.sha256(raw).hexdigest()
    return hashes


def install_actual_registry(root: Path) -> tuple[Path, dict[str, str]]:
    """Install actual FULL registry shape + four pack trees."""
    registry = root / ".cursor" / "static-check" / "registry.yaml"
    registry.parent.mkdir(parents=True, exist_ok=True)
    raw = ACTUAL_FULL_REGISTRY.encode("utf-8")
    registry.write_bytes(raw)
    hashes: dict[str, str] = {
        registry.relative_to(root).as_posix(): hashlib.sha256(raw).hexdigest()
    }
    for check_id in (
        "pyright-strict",
        "mypy",
        "pytest-unit",
        "pytest-full",
    ):
        hashes.update(write_pack_tree(root, check_id))
    return registry, hashes
