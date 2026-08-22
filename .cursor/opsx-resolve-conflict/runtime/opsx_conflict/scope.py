"""Immutable schema-valid scope manifest (RC04-H03)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence  # Any used by freeze helpers

from .errors import PolicyViolation, StopRequired
from .hashutil import sha256_bytes, sha256_canonical
from .process_surfaces import norm_rel

SCOPE_SCHEMA = "opsx-resolve-conflict/scope-manifest/v2"


@dataclass(frozen=True)
class ScopeItem:
    path: str
    unit_id: str
    reason: str
    authority_source: str
    authority_sha256: str
    allowed_operation: str
    expected_semantic_change: str
    initial_stage_oids: Mapping[str, str]
    initial_worktree_sha256: str
    required_checks: tuple[tuple[str, ...], ...]


class ScopeManifest:
    """Frozen scope; items are MappingProxyType — mutation after freeze impossible."""

    def __init__(
        self,
        items: Sequence[ScopeItem],
        *,
        run_id: str,
        frozen_at_fingerprint: str,
    ) -> None:
        normalized: dict[str, ScopeItem] = {}
        for item in items:
            path = norm_rel(item.path)
            if path in normalized:
                raise PolicyViolation(f"duplicate scope path: {path}")
            if item.allowed_operation != "write":
                raise PolicyViolation("allowed_operation must be write")
            normalized[path] = ScopeItem(
                path=path,
                unit_id=item.unit_id,
                reason=item.reason,
                authority_source=item.authority_source,
                authority_sha256=item.authority_sha256,
                allowed_operation=item.allowed_operation,
                expected_semantic_change=item.expected_semantic_change,
                initial_stage_oids=dict(item.initial_stage_oids),
                initial_worktree_sha256=item.initial_worktree_sha256,
                required_checks=tuple(tuple(x) for x in item.required_checks),
            )
        object.__setattr__(self, "_items", MappingProxyType(normalized))
        object.__setattr__(self, "run_id", run_id)
        object.__setattr__(self, "frozen_at_fingerprint", frozen_at_fingerprint)
        object.__setattr__(self, "schema", SCOPE_SCHEMA)
        object.__setattr__(self, "manifest_sha256", self._compute_hash())

    def __setattr__(self, name: str, value: Any) -> None:
        raise PolicyViolation("ScopeManifest is immutable")

    @property
    def items(self) -> Mapping[str, ScopeItem]:
        return self._items  # type: ignore[attr-defined]

    def _compute_hash(self) -> str:
        return sha256_canonical(self.to_dict_unsigned())

    def to_dict_unsigned(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "run_id": self.run_id,
            "frozen_at_state_fingerprint": self.frozen_at_fingerprint,
            "items": [
                {
                    "path": it.path,
                    "unit_id": it.unit_id,
                    "reason": it.reason,
                    "authority_source": it.authority_source,
                    "authority_sha256": it.authority_sha256,
                    "allowed_operation": it.allowed_operation,
                    "expected_semantic_change": it.expected_semantic_change,
                    "initial_stage_oids": dict(it.initial_stage_oids),
                    "initial_worktree_sha256": it.initial_worktree_sha256,
                    "required_checks": [list(x) for x in it.required_checks],
                }
                for it in self.items.values()
            ],
        }

    def to_dict(self) -> dict[str, Any]:
        d = self.to_dict_unsigned()
        d["manifest_sha256"] = self.manifest_sha256
        return d

    def require(self, path: str, *, allowed_operation: str) -> ScopeItem:
        rel = norm_rel(path)
        if rel not in self.items:
            raise StopRequired("SCOPE_EXPANSION_REQUIRED", {"path": rel})
        item = self.items[rel]
        if allowed_operation != item.allowed_operation:
            raise StopRequired(
                "SCOPE_OPERATION_NOT_AUTHORIZED",
                {"path": rel, "operation": allowed_operation},
            )
        return item

    def persist(self, path: Path) -> None:
        """Atomically persist the immutable scope with private permissions."""
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        try:
            tmp.chmod(0o600)
        except OSError:
            pass
        tmp.replace(path)

    @staticmethod
    def load(path: Path) -> "ScopeManifest":
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema") != SCOPE_SCHEMA:
            raise StopRequired("SCOPE_SCHEMA_MISMATCH")
        items = [
            ScopeItem(
                path=i["path"],
                unit_id=i["unit_id"],
                reason=i["reason"],
                authority_source=i["authority_source"],
                authority_sha256=i["authority_sha256"],
                allowed_operation=i["allowed_operation"],
                expected_semantic_change=i["expected_semantic_change"],
                initial_stage_oids=i["initial_stage_oids"],
                initial_worktree_sha256=i["initial_worktree_sha256"],
                required_checks=tuple(tuple(x) for x in i["required_checks"]),
            )
            for i in data["items"]
        ]
        manifest = ScopeManifest(
            items,
            run_id=data["run_id"],
            frozen_at_fingerprint=data["frozen_at_state_fingerprint"],
        )
        if manifest.manifest_sha256 != data.get("manifest_sha256"):
            raise StopRequired("SCOPE_HASH_MISMATCH")
        return manifest


def freeze_scope_from_state(
    state: Any,
    *,
    repo_root: Path,
    run_id: str,
    authority_sha256: str,
) -> ScopeManifest:
    """Build immutable scope exclusively from current unmerged conflict inventory (CF-002)."""
    from .operation import OperationState

    if not isinstance(state, OperationState):
        raise PolicyViolation("freeze_scope_from_state requires OperationState")
    if not state.unmerged:
        raise StopRequired("NO_CONFIRMED_CONFLICT_INVENTORY")
    by_path: dict[str, dict[str, str]] = {}
    for entry in state.unmerged:
        by_path.setdefault(entry.path, {})[str(entry.stage)] = entry.oid
    items: list[ScopeItem] = []
    for path, stage_oids in sorted(by_path.items()):
        wt = repo_root / path
        wt_hash = sha256_bytes(wt.read_bytes()) if wt.is_file() else ""
        items.append(
            ScopeItem(
                path=path,
                unit_id=f"unit-{path}",
                reason="unmerged_conflict",
                authority_source="runtime_conflict_inventory",
                authority_sha256=authority_sha256,
                allowed_operation="write",
                expected_semantic_change="resolve_conflict_markers",
                initial_stage_oids=stage_oids,
                initial_worktree_sha256=wt_hash,
                required_checks=(("syntax-parse", path), ("git-diff-check", path)),
            )
        )
    return ScopeManifest(items, run_id=run_id, frozen_at_fingerprint=state.fingerprint)


def assert_scope_bound_to_state(scope: ScopeManifest, state: Any, *, repo_root: Path) -> None:
    """Reject forged/stale/expanded scopes (CF-002)."""
    from .operation import OperationState

    if not isinstance(state, OperationState):
        raise PolicyViolation("assert_scope_bound_to_state requires OperationState")
    if scope.frozen_at_fingerprint != state.fingerprint:
        raise StopRequired("SCOPE_FINGERPRINT_MISMATCH")
    conflict_paths = sorted({e.path for e in state.unmerged})
    scope_paths = sorted(scope.items.keys())
    if scope_paths != conflict_paths:
        raise StopRequired(
            "SCOPE_NOT_BOUND_TO_CONFLICT_INVENTORY",
            {"scope": scope_paths, "conflicts": conflict_paths},
        )
    for path, item in scope.items.items():
        expected = {str(e.stage): e.oid for e in state.unmerged if e.path == path}
        if dict(item.initial_stage_oids) != expected:
            raise StopRequired("SCOPE_STAGE_OID_MISMATCH", {"path": path})
        wt = repo_root / path
        wt_hash = sha256_bytes(wt.read_bytes()) if wt.is_file() else ""
        if item.initial_worktree_sha256 != wt_hash:
            raise StopRequired("SCOPE_WORKTREE_HASH_MISMATCH", {"path": path})
