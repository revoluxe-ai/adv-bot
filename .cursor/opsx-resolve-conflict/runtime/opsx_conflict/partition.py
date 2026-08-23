"""Authority partition — mixed scope → lanes, не global stop."""

from __future__ import annotations

import fnmatch
from pathlib import Path

import yaml

from opsx_conflict.models import (
    AuthorityLane,
    ConflictManifest,
    PartitionedPath,
)


def _load_sources(repo_root: Path) -> tuple[list[str], list[str]]:
    sources_path = repo_root / ".opsx" / "sources.yaml"
    if not sources_path.is_file():
        return [], []
    data = yaml.safe_load(sources_path.read_text(encoding="utf-8")) or {}
    allowlist = list(data.get("allowlist") or [])
    hard_exclude = list(data.get("hard_exclude") or [])
    return allowlist, hard_exclude


def _matches_any(path: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if fnmatch.fnmatch(path, pat) or fnmatch.fnmatch(path.replace("\\", "/"), pat):
            return True
        norm = path.replace("\\", "/")
        if pat.endswith("/**"):
            prefix = pat[:-3]
            if norm == prefix or norm.startswith(prefix + "/"):
                return True
    return False


def _inventory_class(
    path: str,
    allowlist: list[str],
    hard_exclude: list[str],
) -> str:
  if _matches_any(path, hard_exclude):
      return "C_OUT_OF_SCOPE"
  if _matches_any(path, allowlist):
      return "A_IN_SCOPE"
  norm = path.replace("\\", "/")
  if norm.startswith("openspec/"):
      return "SPEC_GOVERNANCE"
  config_names = {
      "pyproject.toml",
      "poetry.lock",
      "pyrightconfig.json",
      "pyrightconfig_strict.json",
      "ruff.toml",
      ".pre-commit-config.yaml",
      "docker-compose.yaml",
      "alembic.ini",
  }
  if norm in config_names or norm.startswith("tests/"):
      return "PROJECT_OR_TEST"
  if norm.startswith("app/") or norm.startswith("src/"):
      return "C_OUT_OF_SCOPE"
  return "B_ALLOWLIST_GAP"


def _lane_for_class(inventory_class: str) -> AuthorityLane:
    mapping = {
        "A_IN_SCOPE": AuthorityLane.PROCESS,
        "B_ALLOWLIST_GAP": AuthorityLane.PROCESS,
        "C_OUT_OF_SCOPE": AuthorityLane.PRODUCT,
        "SPEC_GOVERNANCE": AuthorityLane.SPEC_GOVERNANCE,
        "PROJECT_OR_TEST": AuthorityLane.PROJECT_CONFIG,
    }
    return mapping.get(inventory_class, AuthorityLane.UNKNOWN)


def partition_manifest(
    manifest: ConflictManifest,
    repo_root: Path,
) -> list[PartitionedPath]:
    """PARTITION: authority lanes вместо BLOCKED_MIXED_SCOPE."""

    allowlist, hard_exclude = _load_sources(repo_root)
    result: list[PartitionedPath] = []
    for unmerged in manifest.unmerged_paths:
        inv = _inventory_class(unmerged.path, allowlist, hard_exclude)
        lane = _lane_for_class(inv)
        if inv == "C_OUT_OF_SCOPE":
            lane = AuthorityLane.PRODUCT
        result.append(
            PartitionedPath(
                path=unmerged.path,
                lane=lane,
                inventory_class=inv,
                unmerged=unmerged,
            )
        )
    return result


def lanes_present(partitions: list[PartitionedPath]) -> set[AuthorityLane]:
    return {p.lane for p in partitions}


def is_mixed_scope(partitions: list[PartitionedPath]) -> bool:
    """Mixed scope — partition, не dead end."""

    return len(lanes_present(partitions)) > 1
