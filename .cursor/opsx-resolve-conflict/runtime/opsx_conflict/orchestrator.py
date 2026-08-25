"""Sealed orchestration layer for the conflict runtime (R14)."""

from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

from .attestation import (
    PACKAGE_VERSION,
    assert_repo_contracts_unchanged,
    package_compatibility_gate,
    resolve_state_root,
)
from .authority import resolve_authority
from .cancellation import clear_execution_ledger, set_execution_ledger, supervisor
from .errors import PolicyViolation, StopRequired
from .git_typed import TypedGit
from .hashutil import sha256_bytes, sha256_canonical, sha256_text
from .ledger import ExecutionLedger, verify_ledger as verify_ledger_file
from .operation import StageEntry, contamination_gate, conflict_start_gate, detect_operation_state
from .process_surfaces import classify_path_risk
from .proofs import Proof
from .receipts import (
    build_run_receipt,
    build_unit_receipt,
    persist_private_json,
    persist_stop_receipt,
)
from .resolution_proof import prove_text_resolution
from .scope import ScopeManifest, assert_scope_bound_to_state, freeze_scope_from_state
from .validation import (
    ALLOWED_TOOLS,
    FrozenTestPlanCompiler,
    build_validation_snapshot,
    run_frozen_check,
)
from .write_atomic import (
    mark_write_transaction_staged,
    recover_write_transactions,
    release_write_transaction,
    retire_write_transactions,
    write_scoped_file,
)
from .pathsafety import resolve_under_repo

# Topologies that must STOP without autonomous text write (HF-004).
_STOP_TOPOLOGIES = frozenset(
    {
        "add/add",
        "modify/delete",
        "delete/modify",
        "file-mode-or-type",
        "other",
    }
)


def _verify_staged_candidate(
    *,
    git: TypedGit,
    repo_root: Path,
    path: str,
    candidate_bytes: bytes,
    expected_oid: str,
    expected_mode: str,
) -> dict[str, str]:
    """Bind stage-0 OID/mode/blob bytes and worktree bytes to the candidate."""
    raw = git.ls_files_stage_path_z(path)
    records = [record for record in raw.split("\0") if record]
    if len(records) != 1 or "\t" not in records[0]:
        raise StopRequired(
            "STAGED_BLOB_RECORD_INVALID",
            {"path": path, "records": len(records)},
        )
    metadata, actual_path = records[0].split("\t", 1)
    fields = metadata.split()
    if len(fields) != 3 or fields[2] != "0" or actual_path != path:
        raise StopRequired(
            "STAGED_BLOB_RECORD_INVALID",
            {"path": path, "record": records[0]},
        )
    actual_mode, actual_oid, _stage = fields
    if actual_oid != expected_oid or actual_mode != expected_mode:
        raise StopRequired(
            "STAGED_BLOB_MISMATCH",
            {
                "path": path,
                "expected_oid": expected_oid,
                "actual_oid": actual_oid,
                "expected_mode": expected_mode,
                "actual_mode": actual_mode,
            },
        )
    staged_blob = git.cat_file_blob_bytes(actual_oid)
    if staged_blob != candidate_bytes:
        raise StopRequired(
            "STAGED_BLOB_BYTES_MISMATCH",
            {
                "path": path,
                "expected_sha256": sha256_bytes(candidate_bytes),
                "actual_sha256": sha256_bytes(staged_blob),
            },
        )
    _, resolved = resolve_under_repo(repo_root, path)
    worktree_sha256 = sha256_bytes(resolved.read_bytes())
    candidate_sha256 = sha256_bytes(candidate_bytes)
    if worktree_sha256 != candidate_sha256:
        raise StopRequired(
            "COMPLETED_PATH_WORKTREE_DRIFT",
            {
                "path": path,
                "expected_sha256": candidate_sha256,
                "actual_sha256": worktree_sha256,
            },
        )
    return {
        "path": path,
        "blob_oid": actual_oid,
        "mode": actual_mode,
        "content_sha256": candidate_sha256,
        "worktree_sha256": worktree_sha256,
        "staged_blob_sha256": sha256_bytes(staged_blob),
    }


def _verify_staged_evidence(
    *,
    git: TypedGit,
    repo_root: Path,
    evidence: Mapping[str, str],
) -> None:
    """Recheck terminal index/worktree state against prior stage evidence."""
    path = str(evidence.get("path", ""))
    raw = git.ls_files_stage_path_z(path)
    records = [record for record in raw.split("\0") if record]
    if len(records) != 1 or "\t" not in records[0]:
        raise StopRequired("STAGED_BLOB_RECORD_INVALID", {"path": path})
    metadata, actual_path = records[0].split("\t", 1)
    fields = metadata.split()
    if (
        len(fields) != 3
        or fields[2] != "0"
        or actual_path != path
        or fields[0] != evidence.get("mode")
        or fields[1] != evidence.get("blob_oid")
    ):
        raise StopRequired("STAGED_CANDIDATE_EVIDENCE_DRIFT", {"path": path})
    _, resolved = resolve_under_repo(repo_root, path)
    if sha256_bytes(resolved.read_bytes()) != evidence.get("worktree_sha256"):
        raise StopRequired("COMPLETED_PATH_WORKTREE_DRIFT", {"path": path})


def _git_subcommand(argv: Sequence[Any]) -> str | None:
    """Return the first non-option Git subcommand from a recorded argv."""
    if not argv:
        return None
    index = 1
    while index < len(argv):
        token = str(argv[index])
        if token.startswith("-"):
            if token in {"-C", "-c"} and index + 1 < len(argv):
                index += 2
                continue
            index += 1
            continue
        return token
    return None


def _derive_action_claims(ledger_path: Path) -> dict[str, Any]:
    """Derive forbidden-command and push claims from typed ledger actions."""
    forbidden_subcommands = {
        "cherry-pick",
        "commit",
        "merge",
        "push",
        "rebase",
        "reset",
    }
    forbidden: list[list[str]] = []
    push_performed = False
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("event") != "COMMAND_START":
            continue
        payload = record.get("payload", {})
        argv = payload.get("argv", []) if isinstance(payload, dict) else []
        if not isinstance(argv, list) or not argv:
            continue
        subcommand = _git_subcommand(argv)
        if subcommand == "push":
            push_performed = True
        if subcommand in forbidden_subcommands:
            forbidden.append([str(arg) for arg in argv])
    return {
        "forbidden_commands_executed": len(forbidden),
        "forbidden_command_argv": forbidden,
        "push_performed": push_performed,
    }


def _parse_name_status_z(raw: str) -> list[dict[str, str]]:
    """Parse ``git diff --name-status -z -M`` without losing rename paths."""
    fields = raw.split("\0")
    if fields and fields[-1] == "":
        fields.pop()
    changes: list[dict[str, str]] = []
    index = 0
    while index < len(fields):
        status = fields[index]
        index += 1
        if not status or index >= len(fields):
            raise StopRequired("OPERATION_GRAPH_MALFORMED_NAME_STATUS")
        old_path = fields[index]
        index += 1
        if status.startswith(("R", "C")):
            if index >= len(fields):
                raise StopRequired("OPERATION_GRAPH_MALFORMED_RENAME")
            new_path = fields[index]
            index += 1
            changes.append(
                {"status": status, "old_path": old_path, "path": new_path}
            )
        else:
            changes.append({"status": status, "path": old_path})
    return changes


@dataclass(frozen=True)
class OrchestrationResult:
    """Structured result returned by preview/go entrypoints."""

    status: str
    repository_root: str
    run_id: str
    fingerprint: str
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class StageRole:
    """Stage attribution for a conflicted path."""

    stage: int
    role: str
    commit_oid: str | None
    expected_blob_oid: str | None
    actual_blob_oid: str | None
    verified: bool
    note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SealedOrchestrator:
    """Typed runtime facade used by the package CLI and tests."""

    def __init__(self, repo_root: Path, *, state_root: Path | None = None) -> None:
        self.repo_root = repo_root.resolve()
        self.state_root = resolve_state_root(state_root)

    def _run_id(self, *, state_fingerprint: str, scope_sha256: str) -> str:
        return sha256_text(f"{self.repo_root}\n{state_fingerprint}\n{scope_sha256}\n")[:24]

    def _ledger(self, run_id: str) -> ExecutionLedger:
        self.state_root.mkdir(parents=True, exist_ok=True)
        return ExecutionLedger(self.state_root / f"{run_id}.ledger.jsonl")

    def _manifest_path(self, run_id: str) -> Path:
        self.state_root.mkdir(parents=True, exist_ok=True)
        return self.state_root / f"{run_id}.run.json"

    def _load_terminal_bundle(self, path: Path) -> dict[str, Any] | None:
        """Load and validate one durable terminal success bundle."""
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if (
            not isinstance(payload, dict)
            or payload.get("schema")
            != "opsx-resolve-conflict/terminal-bundle/v1"
            or payload.get("status")
            not in {
                "READY_FOR_OWNER_CONTINUE",
                "STAGED_AWAITING_OWNER_CONTINUE",
            }
            or not isinstance(payload.get("run_id"), str)
            or not isinstance(payload.get("run_manifest"), dict)
            or not isinstance(payload.get("run_receipt"), dict)
            or not isinstance(payload.get("run_manifest_sha256"), str)
            or len(str(payload.get("run_manifest_sha256"))) != 64
            or not isinstance(payload.get("run_receipt_sha256"), str)
            or len(str(payload.get("run_receipt_sha256"))) != 64
            or not isinstance(payload.get("ledger_final_hash"), str)
            or len(str(payload.get("ledger_final_hash"))) != 64
        ):
            return None
        return payload

    def _verify_terminal_bundle_against_live_state(
        self,
        *,
        path: Path,
        bundle: dict[str, Any],
        state,
    ) -> None:
        """Bind a terminal bundle to ledger finality and live Git evidence."""
        manifest_data = bundle["run_manifest"]
        receipt = bundle["run_receipt"]
        if not isinstance(receipt, dict):
            raise StopRequired(
                "TERMINAL_BUNDLE_RECEIPT_INVALID",
                {"path": str(path)},
            )
        expected_manifest_sha = bundle.get("run_manifest_sha256")
        expected_receipt_sha = bundle.get("run_receipt_sha256")
        actual_manifest_sha = sha256_canonical(manifest_data)
        actual_receipt_sha = sha256_canonical(receipt)
        if (
            expected_manifest_sha != actual_manifest_sha
            or expected_receipt_sha != actual_receipt_sha
        ):
            raise StopRequired(
                "TERMINAL_BUNDLE_COMPONENT_HASH_MISMATCH",
                {
                    "path": str(path),
                    "manifest": {
                        "expected": expected_manifest_sha,
                        "actual": actual_manifest_sha,
                    },
                    "receipt": {
                        "expected": expected_receipt_sha,
                        "actual": actual_receipt_sha,
                    },
                },
            )
        ledger_final = str(bundle.get("ledger_final_hash") or "")
        if (
            not ledger_final
            or ledger_final != manifest_data.get("ledger_final_hash")
            or ledger_final != receipt.get("ledger_final_hash")
        ):
            raise StopRequired(
                "TERMINAL_BUNDLE_LEDGER_HASH_MISMATCH",
                {"path": str(path), "ledger_final_hash": ledger_final},
            )
        run_id = str(bundle["run_id"])
        ledger_path = self.state_root / f"{run_id}.ledger.jsonl"
        if not ledger_path.is_file():
            raise StopRequired(
                "TERMINAL_BUNDLE_LEDGER_MISSING",
                {"path": str(path), "ledger": str(ledger_path)},
            )
        ledger_ok = verify_ledger_file(ledger_path)
        if ledger_ok.get("ledger_final_hash") != ledger_final:
            raise StopRequired(
                "TERMINAL_BUNDLE_LEDGER_FINAL_DRIFT",
                {
                    "path": str(path),
                    "expected": ledger_final,
                    "actual": ledger_ok.get("ledger_final_hash"),
                },
            )
        if state.fingerprint != manifest_data.get("last_verified_fingerprint"):
            raise StopRequired(
                "TERMINAL_BUNDLE_FINGERPRINT_DRIFT",
                {
                    "path": str(path),
                    "expected": manifest_data.get("last_verified_fingerprint"),
                    "actual": state.fingerprint,
                },
            )
        if state.unmerged:
            raise StopRequired(
                "TERMINAL_BUNDLE_UNMERGED_REMAIN",
                {
                    "path": str(path),
                    "unmerged": [entry.path for entry in state.unmerged],
                },
            )
        staged_paths = list(manifest_data.get("staged_paths") or ())
        if not staged_paths:
            raise StopRequired(
                "TERMINAL_BUNDLE_STAGED_PATHS_MISSING",
                {"path": str(path)},
            )
        git = TypedGit(self.repo_root)
        unit_receipts = receipt.get("unit_receipts")
        if not isinstance(unit_receipts, list) or not unit_receipts:
            raise StopRequired(
                "TERMINAL_BUNDLE_UNIT_RECEIPTS_MISSING",
                {"path": str(path)},
            )
        evidenced_paths: set[str] = set()
        for unit in unit_receipts:
            if not isinstance(unit, dict):
                raise StopRequired(
                    "TERMINAL_BUNDLE_UNIT_RECEIPT_INVALID",
                    {"path": str(path)},
                )
            staged_candidate = unit.get("staged_candidate")
            if not isinstance(staged_candidate, dict):
                raise StopRequired(
                    "TERMINAL_BUNDLE_STAGED_EVIDENCE_MISSING",
                    {"path": str(path), "unit": unit.get("path")},
                )
            evidence = {
                str(key): str(value) for key, value in staged_candidate.items()
            }
            _verify_staged_evidence(
                git=git,
                repo_root=self.repo_root,
                evidence=evidence,
            )
            evidenced_paths.add(str(evidence.get("path", "")))
        if set(staged_paths) != evidenced_paths:
            raise StopRequired(
                "TERMINAL_BUNDLE_STAGED_PATH_SET_MISMATCH",
                {
                    "path": str(path),
                    "staged_paths": staged_paths,
                    "evidenced_paths": sorted(evidenced_paths),
                },
            )

    def _recover_terminal_bundle(self, state) -> OrchestrationResult | None:
        """Treat durable terminal bundles as authoritative over ACTIVE caches."""
        from .runtime import RunManifest, save_run_manifest

        if not self.state_root.is_dir():
            return None
        for path in sorted(self.state_root.glob("*.terminal.json")):
            bundle = self._load_terminal_bundle(path)
            if bundle is None:
                continue
            manifest_data = bundle["run_manifest"]
            if (
                manifest_data.get("repository_identity")
                != state.repository_identity
                or manifest_data.get("operation") != state.operation
            ):
                continue
            if manifest_data.get("package_version") != PACKAGE_VERSION:
                raise StopRequired(
                    "TERMINAL_BUNDLE_PACKAGE_MISMATCH",
                    {
                        "path": str(path),
                        "run": manifest_data.get("package_version"),
                    },
                )
            self._verify_terminal_bundle_against_live_state(
                path=path,
                bundle=bundle,
                state=state,
            )
            run_id = str(bundle["run_id"])
            run_manifest = RunManifest(
                run_id=run_id,
                package_version=str(manifest_data["package_version"]),
                repository_identity=str(manifest_data["repository_identity"]),
                repository_root=str(manifest_data["repository_root"]),
                operation=str(manifest_data["operation"]),
                initial_fingerprint=str(manifest_data["initial_fingerprint"]),
                last_verified_fingerprint=str(
                    manifest_data["last_verified_fingerprint"]
                ),
                status=str(manifest_data["status"]),
                completed_units=tuple(manifest_data.get("completed_units") or ()),
                staged_paths=tuple(manifest_data.get("staged_paths") or ()),
                owner_decision_state=manifest_data.get("owner_decision_state"),
                ledger_final_hash=manifest_data.get("ledger_final_hash"),
            )
            save_run_manifest(self._manifest_path(run_id), run_manifest)
            persist_private_json(
                self.state_root / f"{run_id}.run-receipt.json",
                bundle["run_receipt"],
            )
            retire_write_transactions(
                self.state_root / "write-transactions" / run_id
            )
            return OrchestrationResult(
                status="READY_FOR_OWNER_CONTINUE",
                repository_root=str(self.repo_root),
                run_id=run_id,
                fingerprint=str(
                    manifest_data.get("last_verified_fingerprint") or ""
                ),
                payload={
                    "terminal_bundle_recovered": True,
                    "terminal_bundle_path": str(path),
                    "run_manifest": manifest_data,
                    "run_receipt": bundle["run_receipt"],
                    "ledger_final_hash": bundle.get("ledger_final_hash"),
                    "RESOLVED_CLAIMED": False,
                    "FINAL_VALIDATION": "FULL",
                    "OWNER_CONTINUE_REQUIRED": True,
                },
            )
        return None

    def _find_resumable_manifest(self, state) -> Any | None:
        from .runtime import load_run_manifest

        if not self.state_root.is_dir():
            return None
        for path in sorted(self.state_root.glob("*.run.json")):
            try:
                manifest = load_run_manifest(path)
            except Exception:
                continue
            if manifest.status not in {"ACTIVE", "STOPPING"}:
                continue
            if manifest.repository_identity != state.repository_identity:
                continue
            if manifest.operation != state.operation:
                continue
            if manifest.package_version != PACKAGE_VERSION:
                raise StopRequired(
                    "UNFINISHED_RUN_PACKAGE_MISMATCH",
                    {"path": str(path), "run": manifest.package_version},
                )
            return manifest
        return None

    def _state_dict(self, state) -> dict[str, Any]:
        return {
            "operation": state.operation,
            "head": state.head,
            "operation_head": state.operation_head,
            "branch": state.branch,
            "fingerprint": state.fingerprint,
            "unmerged": [asdict(entry) for entry in state.unmerged],
            "staged_paths": list(state.staged_paths),
            "unstaged_paths": list(state.unstaged_paths),
            "untracked_paths": list(state.untracked_paths),
            "sequencer_tree_hash": state.sequencer_tree_hash,
            "repository_identity": state.repository_identity,
            "git_dir": str(state.git_dir),
        }

    def _stage_role_matrix(self, state, git: TypedGit) -> dict[str, list[StageRole]]:
        from .runtime import stage_role_matrix as _matrix

        raw = _matrix(state, git)
        return {path: list(roles) for path, roles in raw.items()}

    def _role_bound_validation_nodes(
        self,
        path: str,
        *,
        role: str,
        production_text: str | None = None,
    ) -> tuple[str, ...]:
        """Discover tests with explicit role metadata for one production path."""
        from .validation import discover_role_bound_tests

        if not path.endswith(".py") or path.startswith("tests/"):
            return ()
        texts = {path: production_text} if production_text is not None else None
        return discover_role_bound_tests(
            self.repo_root,
            production_paths=(path,),
            role=role,
            production_texts=texts,
        )

    def _operation_change_graph(self, state, git: TypedGit) -> list[dict[str, str]]:
        """Build conservative source/target commit-range graph with renames."""
        if not state.operation_head:
            raise StopRequired("OPERATION_GRAPH_HEAD_MISSING")
        if state.operation == "merge":
            base = git.merge_base(state.head, state.operation_head)
        elif state.operation in {"rebase", "cherry-pick"}:
            base = git.rev_parse(f"{state.operation_head}^")
        else:
            raise StopRequired(
                "OPERATION_GRAPH_UNSUPPORTED_OPERATION",
                {"operation": state.operation},
            )
        if not base:
            raise StopRequired("OPERATION_GRAPH_BASE_MISSING")
        graph: list[dict[str, str]] = []
        for side, tip in (
            ("target", state.head),
            ("source", state.operation_head),
        ):
            for change in _parse_name_status_z(
                git.diff_tree_name_status_z(base, tip)
            ):
                graph.append({"side": side, **change})
        return graph

    def preview(
        self,
        *,
        change_id: str | None = None,
        store_id: str | None = None,
    ) -> OrchestrationResult:
        """Read-only preview of active conflict operation."""
        from .runtime import classify_conflict

        # Prevent .pyc writes into the installed package / repository tree.
        sys.dont_write_bytecode = True
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

        gate = package_compatibility_gate(self.repo_root, mode="preview")
        git = TypedGit(self.repo_root)
        state = detect_operation_state(self.repo_root, git)
        index_path = Path(state.git_dir) / "index"
        index_before = (
            sha256_bytes(index_path.read_bytes()) if index_path.is_file() else None
        )
        conflict_start_gate(state)
        matrix = self._stage_role_matrix(state, git)
        operation_graph = self._operation_change_graph(state, git)
        authority = resolve_authority(
            self.repo_root,
            run_id="preview",
            fingerprint=state.fingerprint,
            scope_sha256=sha256_canonical({"preview": True}),
            conflict_paths=sorted({e.path for e in state.unmerged}),
            change_id=change_id,
            store_id=store_id,
        )
        scope = freeze_scope_from_state(
            state,
            repo_root=self.repo_root,
            run_id="preview",
            authority_sha256=authority.token,
        )
        topologies = {
            path: classify_conflict(
                path,
                [
                    StageEntry(mode=e.mode, stage=e.stage, path=e.path, oid=e.oid)
                    for e in state.unmerged
                    if e.path == path
                ],
            )
            for path in scope.items
        }
        # Preview uses real stage-2/stage-3 blob texts (not worktree placeholders).
        from .change_graph import detect_logical_conflict_candidates as per_path_logical
        from .runtime import detect_logical_conflict_candidates as cross_file_logical

        logical: list[dict[str, Any]] = []
        stage2_texts: dict[str, str] = {}
        stage3_texts: dict[str, str] = {}
        for path in sorted(scope.items.keys()):
            entries = [e for e in state.unmerged if e.path == path]
            blobs: dict[int, str] = {}
            for entry in entries:
                blobs[entry.stage] = git.cat_file_blob(entry.oid)
            if 2 in blobs:
                stage2_texts[path] = blobs[2]
            if 3 in blobs:
                stage3_texts[path] = blobs[3]
            if path.endswith(".py"):
                logical.extend(
                    per_path_logical(
                        path=path,
                        base_text=blobs.get(1),
                        source_text=blobs.get(3),
                        target_text=blobs.get(2),
                    )
                )
        for hit in cross_file_logical(
            stage3_texts,
            stage2_texts,
            textual_conflict_paths=list(scope.items.keys()),
        ):
            logical.append({**hit, "kind": "cross_file_auto_merged_risk"})
        from .validation import FrozenTestPlanCompiler

        validation_registry = (
            self.repo_root / ".cursor" / "static-check" / "registry.yaml"
        )
        frozen_contract_hashes = dict(gate.get("host_contract_sha256", {}))
        validation_preflight: dict[str, dict[str, Any]] = {}
        for path in sorted(scope.items.keys()):
            if not path.endswith(".py"):
                continue
            preview_text = stage2_texts.get(path) or stage3_texts.get(path)
            if preview_text is None:
                continue
            try:
                plan = FrozenTestPlanCompiler(
                    run_id="preview",
                    fingerprint=state.fingerprint,
                    scope_sha256=scope.manifest_sha256,
                    content_fingerprints={path: sha256_text(preview_text)},
                    registry_path=validation_registry,
                    frozen_contract_hashes=frozen_contract_hashes,
                    targeted_nodes=(path,),
                    interface_nodes=self._role_bound_validation_nodes(
                        path,
                        role="interface_contract",
                        production_text=preview_text,
                    ),
                    contour_nodes=self._role_bound_validation_nodes(
                        path,
                        role="affected_contour",
                        production_text=preview_text,
                    ),
                    production_texts={path: preview_text},
                ).compile()
                validation_preflight[path] = {
                    "status": "READY",
                    "selected_check_ids": list(plan.payload["selected_check_ids"]),
                    "validation_inventory": list(plan.payload["validation_inventory"]),
                    "validation_inventory_complete": bool(
                        plan.payload.get("validation_inventory_complete")
                    ),
                }
            except StopRequired as exc:
                validation_preflight[path] = {
                    "status": "BLOCKED",
                    "reason": exc.reason,
                    "details": exc.details,
                }
        index_after = (
            sha256_bytes(index_path.read_bytes()) if index_path.is_file() else None
        )
        if index_before != index_after:
            raise StopRequired(
                "PREVIEW_INDEX_MUTATION",
                {
                    "before": index_before,
                    "after": index_after,
                },
            )
        from .git_typed import git_executable_identity

        git_identity = git_executable_identity()
        return OrchestrationResult(
            status="PREVIEW_READY",
            repository_root=str(self.repo_root),
            run_id="preview",
            fingerprint=state.fingerprint,
            payload={
                "gate": gate,
                "state": self._state_dict(state),
                "stage_matrix": {p: [r.to_dict() for r in roles] for p, roles in matrix.items()},
                "authority": asdict(authority),
                "scope": scope.to_dict(),
                "topologies": topologies,
                "operation_change_graph": operation_graph,
                "logical_candidates": logical,
                "validation_preflight": validation_preflight,
                "package_version": PACKAGE_VERSION,
                "git_identity": git_identity,
                "preview_index_sha256": index_after,
                "SAFE_USAGE_NOTE": "PREVIEW_ONLY until independent review ACCEPTED",
            },
        )

    def state(self) -> dict[str, Any]:
        """Return a machine-readable state snapshot."""
        git = TypedGit(self.repo_root)
        state = detect_operation_state(self.repo_root, git)
        matrix = self._stage_role_matrix(state, git)
        return {
            "state": self._state_dict(state),
            "fingerprint": state.fingerprint,
            "stage_matrix": {path: [role.to_dict() for role in roles] for path, roles in matrix.items()},
        }

    def go(
        self,
        *,
        resolutions: Mapping[str, str],
        scope: ScopeManifest | None = None,
        change_id: str | None = None,
        store_id: str | None = None,
        base: str | None = None,
        final: str = "FULL",
        **forbidden: Any,
    ) -> OrchestrationResult:
        """
        Resolve conflicts: per-unit write → check → stage (no git --continue).

        Production API does not accept validation callbacks (CF-001).
        """
        run_meta = {"run_id": "", "fingerprint": ""}
        barrier: dict[str, Any] | None = None
        try:
            if forbidden:
                raise PolicyViolation(
                    f"forbidden go kwargs (no validation_executor): {sorted(forbidden)}"
                )
            if base is not None:
                raise StopRequired(
                    "BASE_ARGUMENT_NOT_SUPPORTED",
                    {"base": base},
                )
            return self._go_impl(
                resolutions=resolutions,
                scope=scope,
                change_id=change_id,
                store_id=store_id,
                base=base,
                final=final,
                run_meta=run_meta,
            )
        except BaseException as exc:
            reason = getattr(exc, "reason", None) or type(exc).__name__
            details = getattr(exc, "details", None) or {"error": str(exc)}
            run_id = str(run_meta.get("run_id") or "")
            fingerprint = str(run_meta.get("fingerprint") or "")
            stop_git_state: dict[str, Any] = {}
            stop_completed: list[str] = []
            stop_staged: list[str] = []
            try:
                # Durable terminal success wins over STOP/rollback.
                recovery_ledger = None
                if run_id:
                    try:
                        recovery_ledger = self._ledger(run_id)
                        set_execution_ledger(recovery_ledger)
                    except Exception:
                        recovery_ledger = None
                git_probe = TypedGit(self.repo_root, ledger=recovery_ledger)
                state_probe = detect_operation_state(self.repo_root, git_probe)
                terminal_ok = self._recover_terminal_bundle(state_probe)
                if terminal_ok is not None:
                    recover_write_transactions(
                        self.repo_root,
                        self.state_root / "write-transactions",
                        terminal_success_run_ids={terminal_ok.run_id},
                    )
                    return terminal_ok
                # Restore exact pre-run worktree bytes before publishing STOP.
                recovery_root = self.state_root / "write-transactions"
                if run_id:
                    recovery_root = recovery_root / run_id
                recover_write_transactions(self.repo_root, recovery_root)
            except Exception as recovery_exc:
                base_details = (
                    dict(details)
                    if isinstance(details, Mapping)
                    else {"error": str(details)}
                )
                base_details["WRITE_RECOVERY_ERROR"] = str(recovery_exc)
                details = base_details
            try:
                current_state = detect_operation_state(
                    self.repo_root,
                    TypedGit(self.repo_root),
                )
                stop_git_state = self._state_dict(current_state)
            except Exception as state_exc:
                stop_git_state = {"read_error": str(state_exc)}
            if run_id:
                try:
                    from .runtime import load_run_manifest

                    current_manifest_path = self._manifest_path(run_id)
                    if current_manifest_path.is_file():
                        current_manifest = load_run_manifest(
                            current_manifest_path
                        )
                        stop_completed = list(
                            current_manifest.completed_units
                        )
                        stop_staged = list(current_manifest.staged_paths)
                except Exception:
                    pass
            shutil.rmtree(
                self.state_root / "validation-snapshots",
                ignore_errors=True,
            )
            try:
                barrier = supervisor().close_barrier(reason=str(reason))
            except BaseException as cancel_exc:
                stop_path = persist_stop_receipt(
                    self.state_root,
                    run_id=run_id,
                    fingerprint=fingerprint,
                    repository_root=str(self.repo_root),
                    stop_reason="CANCELLATION_BARRIER_FAILED",
                    evidence={
                        "ORIGINAL_STOP_REASON": reason,
                        "EVIDENCE": details,
                        "CANCELLATION_ERROR": str(cancel_exc),
                    },
                    cancellation_barrier_closed=False,
                    background_processes=supervisor().live_count(),
                    git_state=stop_git_state,
                    completed_units=stop_completed,
                    staged_paths=stop_staged,
                    owner_blocker="Cancellation barrier did not close.",
                    next_action=(
                        "Owner must terminate remaining processes before retry."
                    ),
                )
                return OrchestrationResult(
                    status="STOP_FOR_OWNER",
                    repository_root=str(self.repo_root),
                    run_id=run_id,
                    fingerprint=fingerprint,
                    payload={
                        "STOP_REASON": "CANCELLATION_BARRIER_FAILED",
                        "ORIGINAL_STOP_REASON": reason,
                        "EVIDENCE": details,
                        "CANCELLATION_ERROR": str(cancel_exc),
                        "CANCELLATION_BARRIER_CLOSED": False,
                        "BACKGROUND_PROCESSES": supervisor().live_count(),
                        "STOP_RECEIPT_PATH": str(stop_path),
                    },
                )
            stop_ledger_hash: str | None = None
            stop_ledger_error: str | None = None
            if run_id:
                try:
                    stop_ledger = self._ledger(run_id)
                    if not stop_ledger.finalized:
                        stop_ledger.append(
                            "STOP",
                            {"reason": str(reason), "evidence": details},
                        )
                        if bool(barrier.get("CANCELLATION_BARRIER_CLOSED")):
                            stop_ledger.append(
                                "CANCELLATION_BARRIER_CLOSED",
                                dict(barrier),
                            )
                        stop_ledger_hash = stop_ledger.append(
                            "LEDGER_FINALIZED",
                            {"terminal": "STOP_FOR_OWNER"},
                        )
                except Exception as ledger_exc:
                    stop_ledger_error = str(ledger_exc)
            stop_path = persist_stop_receipt(
                self.state_root,
                run_id=run_id,
                fingerprint=fingerprint,
                repository_root=str(self.repo_root),
                stop_reason=str(reason),
                evidence=details if isinstance(details, Mapping) else {"error": str(details)},
                cancellation_barrier_closed=bool(barrier.get("CANCELLATION_BARRIER_CLOSED")),
                background_processes=int(
                    barrier.get("BACKGROUND_PROCESSES", supervisor().live_count())
                ),
                git_state=stop_git_state,
                completed_units=stop_completed,
                staged_paths=stop_staged,
                ledger_final_hash=stop_ledger_hash,
                owner_blocker=str(reason),
                next_action=(
                    "Owner must inspect current Git state and STOP evidence; "
                    "do not continue automatically."
                ),
            )
            if run_id:
                try:
                    from .runtime import load_run_manifest, save_run_manifest

                    manifest_path = self._manifest_path(run_id)
                    if manifest_path.is_file():
                        stopped = replace(
                            load_run_manifest(manifest_path),
                            status="STOPPED",
                            owner_decision_state="STOP_FOR_OWNER",
                        )
                        save_run_manifest(manifest_path, stopped)
                except Exception:
                    pass
            supervisor().release_barrier()
            return OrchestrationResult(
                status="STOP_FOR_OWNER",
                repository_root=str(self.repo_root),
                run_id=run_id,
                fingerprint=fingerprint,
                payload={
                    "STOP_REASON": reason,
                    "EVIDENCE": details,
                    "BACKGROUND_PROCESSES": barrier.get(
                        "BACKGROUND_PROCESSES", supervisor().live_count()
                    ),
                    "CANCELLATION_BARRIER_CLOSED": bool(
                        barrier.get("CANCELLATION_BARRIER_CLOSED")
                    ),
                    "STOP_RECEIPT_PATH": str(stop_path),
                    "STOP_LEDGER_FINAL_HASH": stop_ledger_hash,
                    "STOP_LEDGER_ERROR": stop_ledger_error,
                },
            )
        finally:
            clear_execution_ledger()

    def _go_impl(
        self,
        *,
        resolutions: Mapping[str, str],
        scope: ScopeManifest | None,
        change_id: str | None,
        store_id: str | None,
        base: str | None,
        final: str,
        run_meta: dict[str, str] | None = None,
    ) -> OrchestrationResult:
        from .runtime import RunManifest, classify_conflict, resume_guard, save_run_manifest

        if final != "FULL":
            raise StopRequired("FINAL_FAST_NOT_SUPPORTED")

        gate = package_compatibility_gate(self.repo_root, mode="go")
        frozen_contract_hashes = gate.get("host_contract_sha256")
        frozen_contract_set_digest = gate.get("host_contract_set_digest")
        if (
            not isinstance(frozen_contract_hashes, dict)
            or not frozen_contract_hashes
            or not isinstance(frozen_contract_set_digest, str)
        ):
            raise StopRequired("HOST_CONTRACT_FREEZE_MISSING")
        if (
            assert_repo_contracts_unchanged(
                self.repo_root,
                frozen_contract_hashes,
            )
            != frozen_contract_set_digest
        ):
            raise StopRequired("HOST_CONTRACT_SET_DIGEST_MISMATCH")
        # Gate and orchestrator must share the same state root (RC-HIGH-006).
        if str(self.state_root) != gate.get("state_root"):
            raise StopRequired(
                "STATE_ROOT_MISMATCH",
                {"orchestrator": str(self.state_root), "gate": gate.get("state_root")},
            )
        capabilities = gate.get("capabilities")
        sandbox = (
            capabilities.get("validation_sandbox")
            if isinstance(capabilities, dict)
            else None
        )
        if not isinstance(sandbox, dict):
            raise StopRequired("VALIDATION_SANDBOX_CAPABILITY_MISSING")
        if (
            sandbox.get("enforcement_level") != "OS_VERIFIED"
            or sandbox.get("network") != "DENY"
            or sandbox.get("filesystem") != "SNAPSHOT_ONLY"
            or not isinstance(sandbox.get("spawn_argv_prefix"), list)
            or not sandbox.get("spawn_argv_prefix")
        ):
            raise StopRequired(
                "STOP_SANDBOX_UNAVAILABLE",
                {
                    "blocker": "BLOCKER_OS_SANDBOX_RUNNER_MISSING",
                    "enforcement_level": sandbox.get("enforcement_level"),
                    "required": "OS_VERIFIED",
                },
            )
        validation_registry = self.repo_root / ".cursor" / "static-check" / "registry.yaml"
        if not validation_registry.is_file():
            raise StopRequired(
                "MANDATORY_FULL_VALIDATION_UNAVAILABLE",
                {"registry": str(validation_registry)},
            )
        shutil.rmtree(
            self.state_root / "validation-snapshots",
            ignore_errors=True,
        )
        git = TypedGit(self.repo_root)
        state = detect_operation_state(self.repo_root, git)
        terminal_recovered = self._recover_terminal_bundle(state)
        if terminal_recovered is not None:
            return terminal_recovered
        resumable = self._find_resumable_manifest(state)
        recover_write_transactions(
            self.repo_root,
            self.state_root / "write-transactions",
            preserve_run_ids=(
                {resumable.run_id} if resumable is not None else set()
            ),
        )
        if resumable is None:
            conflict_start_gate(state)
        stage_matrix = self._stage_role_matrix(state, git)
        proof_fp = (
            resumable.initial_fingerprint
            if resumable is not None
            else state.fingerprint
        )
        if run_meta is not None:
            run_meta["fingerprint"] = proof_fp

        if resumable is not None:
            run_id = resumable.run_id
            completed_resume = list(resumable.completed_units)
            staged_resume = list(resumable.staged_paths)
        else:
            run_id = self._run_id(
                state_fingerprint=state.fingerprint,
                scope_sha256=sha256_canonical(
                    {"conflicts": sorted({e.path for e in state.unmerged})}
                ),
            )
            completed_resume = []
            staged_resume = []
        if run_meta is not None:
            run_meta["run_id"] = run_id
        scope_path = self.state_root / f"{run_id}.scope.json"
        if resumable is not None:
            if not scope_path.is_file():
                raise StopRequired(
                    "DURABLE_SCOPE_MISSING",
                    {"path": str(scope_path)},
                )
            runtime_scope = ScopeManifest.load(scope_path)
            conflict_paths = sorted(runtime_scope.items)
        else:
            runtime_scope = None
            conflict_paths = sorted({e.path for e in state.unmerged})
        commit_oids = {
            "head": state.head or "",
            "operation_head": state.operation_head or "",
            "repository_identity": state.repository_identity,
        }
        stage_blob_oids: dict[str, dict[str, str]] = {}
        for entry in state.unmerged:
            stage_blob_oids.setdefault(entry.path, {})[str(entry.stage)] = entry.oid
        authority = resolve_authority(
            self.repo_root,
            run_id=run_id,
            fingerprint=proof_fp,
            scope_sha256=sha256_canonical({"run_id": run_id}),
            conflict_paths=conflict_paths,
            change_id=change_id,
            store_id=store_id,
            commit_oids=commit_oids,
            strict=True,
            operation=state.operation,
            source_commit=(state.head or "").lower(),
            stage_blob_oids=stage_blob_oids,
        )
        authority_sha256 = authority.token

        if runtime_scope is None:
            runtime_scope = freeze_scope_from_state(
                state,
                repo_root=self.repo_root,
                run_id=run_id,
                authority_sha256=authority_sha256,
            )
            runtime_scope.persist(scope_path)
        if scope is not None:
            if resumable is None:
                assert_scope_bound_to_state(scope, state, repo_root=self.repo_root)
            if sorted(scope.items.keys()) != sorted(runtime_scope.items.keys()):
                raise StopRequired("CALLER_SCOPE_REJECTED")
        scope = runtime_scope
        if len(scope.items) != 1:
            raise StopRequired(
                "MULTI_UNIT_ATOMIC_RECOVERY_NOT_SUPPORTED",
                {"paths": sorted(scope.items)},
            )
        operation_graph = self._operation_change_graph(state, git)
        graph_paths: set[str] = set()
        unsupported_graph_entries: list[dict[str, str]] = []
        for change in operation_graph:
            graph_paths.add(change["path"])
            if "old_path" in change:
                graph_paths.add(change["old_path"])
            if change["status"].startswith(("R", "C", "D", "T")):
                unsupported_graph_entries.append(change)
        if unsupported_graph_entries:
            raise StopRequired(
                "OPERATION_GRAPH_UNSUPPORTED_PATH_SEMANTICS",
                {"entries": unsupported_graph_entries},
            )
        outside_scope = sorted(graph_paths - set(scope.items))
        if outside_scope:
            raise StopRequired(
                "OPERATION_GRAPH_OUTSIDE_CONFLICT_SCOPE",
                {"paths": outside_scope, "graph": operation_graph},
            )

        # Full-path logical graph before mutation (RC-HIGH-003)
        from .change_graph import detect_logical_conflict_candidates as per_path_logical
        from .runtime import detect_logical_conflict_candidates as cross_file_logical

        logical_units: list[dict[str, Any]] = []
        stage2_texts: dict[str, str] = {}
        stage3_texts: dict[str, str] = {}
        for path in sorted(scope.items.keys()):
            if path in completed_resume:
                continue
            entries = [e for e in state.unmerged if e.path == path]
            blobs: dict[int, str] = {}
            for e in entries:
                blobs[e.stage] = git.cat_file_blob(e.oid)
            if 2 in blobs:
                stage2_texts[path] = blobs[2]
            if 3 in blobs:
                stage3_texts[path] = blobs[3]
            if path.endswith(".py"):
                logical_units.extend(
                    per_path_logical(
                        path=path,
                        base_text=blobs.get(1),
                        source_text=blobs.get(3),
                        target_text=blobs.get(2),
                    )
                )
        cross = cross_file_logical(stage3_texts, stage2_texts, textual_conflict_paths=list(scope.items.keys()))
        # Cross-file hits outside frozen unmerged scope → STOP (RC-MED-003 honesty)
        for hit in cross:
            logical_units.append({**hit, "kind": "cross_file_auto_merged_risk"})
            for key in ("source_path", "target_path"):
                p = hit.get(key)
                if p and p not in scope.items:
                    raise StopRequired(
                        "LOGICAL_CONFLICT_OUTSIDE_SCOPE",
                        {"path": p, "hit": hit},
                    )

        contamination_gate(state, scope_paths=set(scope.items.keys()))
        ledger = self._ledger(run_id)
        set_execution_ledger(ledger)
        git = TypedGit(self.repo_root, ledger=ledger)
        progress_path = self.state_root / f"{run_id}.unit-progress.json"
        resume_phase: str | None = None
        resume_progress: dict[str, Any] | None = None

        if resumable is None:
            run_manifest = RunManifest(
                run_id=run_id,
                package_version=PACKAGE_VERSION,
                repository_identity=state.repository_identity,
                repository_root=str(self.repo_root),
                operation=state.operation,
                initial_fingerprint=proof_fp,
                last_verified_fingerprint=proof_fp,
                status="ACTIVE",
                completed_units=(),
                staged_paths=(),
                owner_decision_state=None,
                ledger_final_hash=None,
            )
            save_run_manifest(self._manifest_path(run_id), run_manifest)
            resume_guard(run_manifest, state)
            ledger.append("STATE_CAPTURED", {"fingerprint": proof_fp})
            ledger.append("SCOPE_FROZEN", {"scope_sha256": scope.manifest_sha256})
            ledger.append("AUTHORITY_RESOLVED", {"token": authority_sha256})
        else:
            run_manifest = resumable
            if ledger.last_event in {"WRITE_DONE", "CHECK_DONE", "STAGE_DONE"}:
                if not progress_path.is_file():
                    raise StopRequired(
                        "DURABLE_UNIT_PROGRESS_MISSING",
                        {"event": ledger.last_event},
                    )
                resume_progress = json.loads(
                    progress_path.read_text(encoding="utf-8")
                )
                resume_path = str(resume_progress.get("path", ""))
                if resume_path not in scope.items:
                    raise StopRequired(
                        "DURABLE_UNIT_PROGRESS_SCOPE_MISMATCH",
                        {"path": resume_path},
                    )
                resume_phase = ledger.last_event
                if resume_phase in {"WRITE_DONE", "CHECK_DONE"}:
                    current_path = self.repo_root / resume_path
                    if (
                        not current_path.is_file()
                        or sha256_text(current_path.read_text(encoding="utf-8"))
                        != resume_progress.get("resolution_sha256")
                        or not any(
                            entry.path == resume_path
                            for entry in state.unmerged
                        )
                    ):
                        raise StopRequired(
                            "DURABLE_WRITE_RECOVERY_STATE_MISMATCH",
                            {"path": resume_path, "phase": resume_phase},
                        )
                    run_manifest = replace(
                        run_manifest,
                        last_verified_fingerprint=state.fingerprint,
                    )
                    save_run_manifest(self._manifest_path(run_id), run_manifest)
                elif resume_phase == "STAGE_DONE":
                    if (
                        resume_path not in state.staged_paths
                        or any(
                            entry.path == resume_path
                            for entry in state.unmerged
                        )
                    ):
                        raise StopRequired(
                            "DURABLE_STAGE_RECOVERY_STATE_MISMATCH",
                            {"path": resume_path},
                        )
                    recovered_args = {
                        key: value
                        for key, value in dict(
                            resume_progress["receipt_args"]
                        ).items()
                        if key
                        not in {
                            "transaction_journal",
                            "content_sha256",
                            "rollback_authority_state",
                        }
                    }
                    recovered_receipt = build_unit_receipt(
                        **recovered_args,
                        fingerprint_after=state.fingerprint,
                        ledger_record_hash=ledger.prev_hash,
                    )
                    persist_private_json(
                        self.state_root
                        / f"{run_id}.units"
                        / f"{sha256_text(resume_path)[:16]}.json",
                        recovered_receipt,
                    )
                    completed_resume = [resume_path]
                    staged_resume = [resume_path]
                    run_manifest = replace(
                        run_manifest,
                        last_verified_fingerprint=state.fingerprint,
                        completed_units=(resume_path,),
                        staged_paths=(resume_path,),
                    )
                    save_run_manifest(self._manifest_path(run_id), run_manifest)
            resume_guard(run_manifest, state)

        scope_proof = Proof.issue(
            "SCOPE",
            run_id=run_id,
            fingerprint=proof_fp,
            scope_sha256=scope.manifest_sha256,
            payload={"paths": sorted(scope.items.keys())},
        )
        unit_plan = Proof.issue(
            "UNIT_PLAN",
            run_id=run_id,
            fingerprint=proof_fp,
            scope_sha256=scope.manifest_sha256,
            payload={"allow_process_write": False, "change_id": change_id, "store_id": store_id},
        )

        validated_paths: list[str] = list(staged_resume)
        write_proofs: list[Proof] = []
        check_receipts: list[Proof] = []
        unit_receipts: list[dict[str, Any]] = []
        validation_inventory: list[dict[str, Any]] = []
        units_dir = self.state_root / f"{run_id}.units"
        if resumable is not None:
            for receipt_path in sorted(units_dir.glob("*.json")):
                receipt_data = json.loads(receipt_path.read_text(encoding="utf-8"))
                if (
                    receipt_data.get("run_id") != run_id
                    or receipt_data.get("path") not in completed_resume
                ):
                    raise StopRequired(
                        "DURABLE_UNIT_RECEIPT_MISMATCH",
                        {"path": str(receipt_path)},
                    )
                unit_receipts.append(receipt_data)
            receipt_paths = {str(item["path"]) for item in unit_receipts}
            if receipt_paths != set(completed_resume):
                raise StopRequired(
                    "DURABLE_UNIT_RECEIPT_INCOMPLETE",
                    {
                        "expected": sorted(completed_resume),
                        "actual": sorted(receipt_paths),
                    },
                )
        completed: list[str] = list(completed_resume)
        staged: list[str] = list(staged_resume)
        semantic_proofs: list[dict[str, Any]] = []

        snap_root = self.state_root / "validation-snapshots"
        snap_root.mkdir(parents=True, exist_ok=True)

        for path in sorted(scope.items.keys()):
            if path in completed:
                continue
            entries = [e for e in state.unmerged if e.path == path]
            if path not in resolutions:
                raise StopRequired("MISSING_RESOLUTION_CONTENT", {"path": path})
            content_fps = {path: sha256_text(resolutions[path])}
            resolved_text = resolutions[path]
            if (
                resume_phase in {"WRITE_DONE", "CHECK_DONE"}
                and resume_progress is not None
                and resume_progress.get("path") == path
            ):
                receipt_args = dict(resume_progress["receipt_args"])
                topology = str(receipt_args["topology"])
                risk = str(receipt_args["risk"])
                semantic_proof_data = dict(receipt_args["semantic_proof"])
                semantic_proofs.append(semantic_proof_data)
            else:
                ledger.append("UNIT_PLANNED", {"path": path})
                topology = classify_conflict(
                    path,
                    [
                        StageEntry(
                            mode=e.mode,
                            stage=e.stage,
                            path=e.path,
                            oid=e.oid,
                        )
                        for e in entries
                    ],
                )
                risk = classify_path_risk(path, topology=topology)
                if topology in _STOP_TOPOLOGIES or risk == "HIGH":
                    raise StopRequired(
                        "HIGH_RISK_OR_AMBIGUOUS_TOPOLOGY",
                        {"path": path, "topology": topology, "risk": risk},
                    )

                stage_blobs: dict[int, str] = {}
                for entry in entries:
                    stage_blobs[entry.stage] = git.cat_file_blob(entry.oid)
                # Semantic proof precedes FULL inventory so invalid candidates
                # STOP on structure/semantics rather than role-metadata absence.
                proof = prove_text_resolution(
                    path=path,
                    resolution=resolutions[path],
                    stage_blobs=stage_blobs,
                    topology=topology,
                )
                semantic_proof_data = asdict(proof)
                semantic_proofs.append(semantic_proof_data)
                assert_repo_contracts_unchanged(
                    self.repo_root,
                    frozen_contract_hashes,
                )

            plan = FrozenTestPlanCompiler(
                run_id=run_id,
                fingerprint=proof_fp,
                scope_sha256=scope.manifest_sha256,
                content_fingerprints=content_fps,
                registry_path=validation_registry,
                frozen_contract_hashes=frozen_contract_hashes,
                targeted_nodes=(path,),
                interface_nodes=self._role_bound_validation_nodes(
                    path,
                    role="interface_contract",
                    production_text=resolved_text,
                ),
                contour_nodes=self._role_bound_validation_nodes(
                    path,
                    role="affected_contour",
                    production_text=resolved_text,
                ),
                production_texts={path: resolved_text},
            ).compile()
            inventory_rows = plan.payload.get("validation_inventory")
            if isinstance(inventory_rows, list):
                validation_inventory = [
                    dict(row) for row in inventory_rows if isinstance(row, dict)
                ]

            if not (
                resume_phase in {"WRITE_DONE", "CHECK_DONE"}
                and resume_progress is not None
                and resume_progress.get("path") == path
            ):
                state_before = detect_operation_state(self.repo_root, git)
                assert_repo_contracts_unchanged(
                    self.repo_root,
                    frozen_contract_hashes,
                )
                if state_before.operation != run_manifest.operation:
                    raise StopRequired("OPERATION_DRIFT_BEFORE_WRITE")
                if (
                    state_before.fingerprint
                    != run_manifest.last_verified_fingerprint
                ):
                    raise StopRequired(
                        "STATE_FINGERPRINT_DRIFT_BEFORE_WRITE",
                        {
                            "path": path,
                            "expected": run_manifest.last_verified_fingerprint,
                            "actual": state_before.fingerprint,
                        },
                    )
                current_stage_oids = {
                    str(entry.stage): entry.oid
                    for entry in state_before.unmerged
                    if entry.path == path
                }
                if current_stage_oids != dict(
                    scope.items[path].initial_stage_oids
                ):
                    raise StopRequired(
                        "STAGE_OIDS_DRIFT_BEFORE_WRITE",
                        {"path": path},
                    )
                contamination_gate(
                    state_before,
                    scope_paths=set(scope.items.keys()) - set(staged),
                )

                wp = write_scoped_file(
                    self.repo_root,
                    path,
                    resolutions[path],
                    scope=scope,
                    scope_proof=scope_proof,
                    unit_plan=unit_plan,
                    run_id=run_id,
                    fingerprint=proof_fp,
                    expected_worktree_sha256=scope.items[
                        path
                    ].initial_worktree_sha256,
                    recovery_dir=self.state_root
                    / "write-transactions"
                    / run_id,
                )
                write_proofs.append(wp)
                receipt_args = {
                    "run_id": run_id,
                    "path": path,
                    "topology": topology,
                    "operation": state.operation,
                    "write_proof_token": wp.token,
                    "transaction_journal": str(wp.payload["transaction_journal"]),
                    "content_sha256": str(wp.payload["content_sha256"]),
                    "semantic_proof": semantic_proof_data,
                    "stage_roles": [
                        {"path": path, **role.to_dict()}
                        for role in stage_matrix[path]
                    ],
                    "authority_sources": list(
                        authority.payload.get("sources", [])
                    ),
                    "scope_manifest_hash": scope.manifest_sha256,
                    "fingerprint_before": state_before.fingerprint,
                    "worktree_hash_before": scope.items[
                        path
                    ].initial_worktree_sha256,
                    "worktree_hash_after": str(wp.payload["content_sha256"]),
                    "stage_oids": {
                        str(entry.stage): entry.oid for entry in entries
                    },
                    "checks": [],
                    "risk": risk,
                }
                persist_private_json(
                    progress_path,
                    {
                        "path": path,
                        "resolution_sha256": sha256_text(resolutions[path]),
                        "receipt_args": receipt_args,
                    },
                )
                ledger.append("WRITE_DONE", {"path": path, "proof": wp.token})

                state_after_write = detect_operation_state(self.repo_root, git)
                if state_after_write.operation != run_manifest.operation:
                    raise StopRequired("OPERATION_DRIFT_AFTER_WRITE")
                contamination_gate(
                    state_after_write,
                    scope_paths=(set(scope.items.keys()) - set(staged))
                    | {path},
                )
                run_manifest = replace(
                    run_manifest,
                    last_verified_fingerprint=state_after_write.fingerprint,
                    status="ACTIVE",
                )
                save_run_manifest(self._manifest_path(run_id), run_manifest)

            # Live git diff --check on host repo (CF-001)
            diff_out = git.diff_check_paths([path])
            if diff_out.strip():
                raise StopRequired("GIT_DIFF_CHECK_FAILED", {"path": path, "output": diff_out[:2000]})

            snapshot = build_validation_snapshot(self.repo_root, snap_root / path.replace("/", "_"), git=git)
            unit_wave_passed: set[str] = set()
            unit_check_receipts: list[Mapping[str, Any]] = []
            for check in plan.payload["checks"]:
                check_id = check["check_id"]
                tool = check["tool"]
                if tool not in ALLOWED_TOOLS:
                    raise StopRequired("MANDATORY_CHECK_NOT_EXECUTABLE", {"check_id": check_id, "tool": tool})
                receipt = run_frozen_check(
                    plan=plan,
                    check_id=check_id,
                    snapshot=snapshot,
                    unit_wave_passed=unit_wave_passed,
                    content_fingerprints=content_fps,
                    sandbox=sandbox,
                )
                receipt.assert_binds(
                    kind="CHECK_RECEIPT",
                    run_id=run_id,
                    fingerprint=proof_fp,
                    scope_sha256=scope.manifest_sha256,
                )
                if receipt.payload.get("exit_code", 0) != 0:
                    raise StopRequired("CHECK_FAILED", {"check_id": check_id})
                if list(receipt.payload.get("argv", [])) != list(check["argv"]):
                    raise StopRequired("CHECK_ARGV_MISMATCH", {"check_id": check_id})
                check_receipts.append(receipt)
                unit_check_receipts.append(dict(receipt.payload))
                unit_wave_passed.add(check_id)
                receipt_args["checks"] = list(unit_check_receipts)
                persist_private_json(
                    progress_path,
                    {
                        "path": path,
                        "resolution_sha256": sha256_text(resolutions[path]),
                        "receipt_args": receipt_args,
                    },
                )
                ledger.append("CHECK_DONE", {"check_id": check_id, "path": path, "receipt": receipt.token})
            mandatory_checks = {
                "syntax-parse",
                "git-diff-check",
                "pyright-strict",
                "mypy",
                "pytest-unit",
                "pytest-full",
            }
            if not mandatory_checks.issubset(unit_wave_passed):
                raise StopRequired(
                    "MANDATORY_FULL_VALIDATION_INCOMPLETE",
                    {
                        "missing": sorted(mandatory_checks - unit_wave_passed),
                        "path": path,
                    },
                )
            shutil.rmtree(snapshot)

            # Contamination after checks
            state_after_checks = detect_operation_state(self.repo_root, git)
            if state_after_checks.fingerprint != run_manifest.last_verified_fingerprint:
                raise StopRequired(
                    "STATE_FINGERPRINT_DRIFT_DURING_CHECKS",
                    {
                        "path": path,
                        "expected": run_manifest.last_verified_fingerprint,
                        "actual": state_after_checks.fingerprint,
                    },
                )
            contamination_gate(
                state_after_checks,
                scope_paths=(set(scope.items.keys()) - set(staged)) | {path},
            )

            state_before_stage = detect_operation_state(self.repo_root, git)
            assert_repo_contracts_unchanged(
                self.repo_root,
                frozen_contract_hashes,
            )
            if state_before_stage.fingerprint != run_manifest.last_verified_fingerprint:
                raise StopRequired(
                    "STATE_FINGERPRINT_DRIFT_BEFORE_STAGE",
                    {
                        "path": path,
                        "expected": run_manifest.last_verified_fingerprint,
                        "actual": state_before_stage.fingerprint,
                    },
                )
            expected_modes = {entry.mode for entry in entries}
            if len(expected_modes) != 1:
                raise StopRequired(
                    "STAGED_MODE_AUTHORITY_AMBIGUOUS",
                    {"path": path, "modes": sorted(expected_modes)},
                )
            expected_mode = next(iter(expected_modes))
            _, stage_source = resolve_under_repo(self.repo_root, path)
            validated_candidate_bytes = stage_source.read_bytes()
            if sha256_bytes(validated_candidate_bytes) != receipt_args[
                "worktree_hash_after"
            ]:
                raise StopRequired(
                    "VALIDATED_WORKTREE_BYTES_DRIFT",
                    {"path": path},
                )
            unmerged_restore: dict[str, dict[str, str]] = {}
            for entry in state_before_stage.unmerged:
                if entry.path != path:
                    continue
                unmerged_restore[str(entry.stage)] = {
                    "mode": entry.mode,
                    "oid": entry.oid,
                }
            if set(unmerged_restore) != {"1", "2", "3"}:
                raise StopRequired(
                    "WRITE_TRANSACTION_UNMERGED_RESTORE_INCOMPLETE",
                    {"path": path, "stages": sorted(unmerged_restore)},
                )
            expected_clean_oid = git.stage_validated_bytes(
                path=path,
                data=validated_candidate_bytes,
                mode=expected_mode,
            )
            staged_candidate = _verify_staged_candidate(
                git=git,
                repo_root=self.repo_root,
                path=path,
                candidate_bytes=validated_candidate_bytes,
                expected_oid=expected_clean_oid,
                expected_mode=expected_mode,
            )
            journal_raw = receipt_args.get("transaction_journal")
            content_sha = receipt_args.get("content_sha256") or receipt_args.get(
                "worktree_hash_after"
            )
            if not isinstance(journal_raw, str) or not isinstance(content_sha, str):
                raise StopRequired(
                    "WRITE_TRANSACTION_JOURNAL_MISSING",
                    {"path": path},
                )
            # Keep rollback authority until durable terminal bundle commit.
            mark_write_transaction_staged(
                Path(journal_raw),
                expected_candidate_sha256=content_sha,
                staged_candidate=staged_candidate,
                unmerged_restore=unmerged_restore,
            )
            receipt_args["staged_candidate"] = staged_candidate
            receipt_args["rollback_authority_state"] = "STAGED"
            receipt_args["diff_sha256"] = sha256_text(
                git.diff_cached_paths([path])
            )
            persist_private_json(
                progress_path,
                {
                    "path": path,
                    "resolution_sha256": sha256_text(resolutions[path]),
                    "receipt_args": receipt_args,
                },
            )
            stage_record_hash = ledger.append(
                "STAGE_DONE",
                {"paths": [path], "staged_candidate": staged_candidate},
            )
            staged.append(path)
            validated_paths.append(path)
            completed.append(path)

            state_after_stage = detect_operation_state(self.repo_root, git)
            receipt_kwargs = {
                key: value
                for key, value in receipt_args.items()
                if key
                not in {
                    "transaction_journal",
                    "content_sha256",
                    "rollback_authority_state",
                }
            }
            unit_receipt = build_unit_receipt(
                **receipt_kwargs,
                fingerprint_after=state_after_stage.fingerprint,
                ledger_record_hash=stage_record_hash,
            )
            persist_private_json(
                self.state_root
                / f"{run_id}.units"
                / f"{sha256_text(path)[:16]}.json",
                unit_receipt,
            )
            unit_receipts.append(unit_receipt)

            run_manifest = RunManifest(
                run_id=run_id,
                package_version=PACKAGE_VERSION,
                repository_identity=state.repository_identity,
                repository_root=str(self.repo_root),
                operation=state.operation,
                initial_fingerprint=run_manifest.initial_fingerprint,
                last_verified_fingerprint=state_after_stage.fingerprint,
                status="ACTIVE",
                completed_units=tuple(completed),
                staged_paths=tuple(staged),
                owner_decision_state=None,
                ledger_final_hash=None,
            )
            save_run_manifest(self._manifest_path(run_id), run_manifest)

            # Remaining unmerged for this path should be gone
            if any(e.path == path for e in state_after_stage.unmerged):
                raise StopRequired("PATH_STILL_UNMERGED", {"path": path})

        if not validation_inventory and validated_paths:
            # Resume-after-STAGE_DONE skips the unit loop; recompile inventory.
            for path in validated_paths:
                resolved_text = resolutions[path]
                plan = FrozenTestPlanCompiler(
                    run_id=run_id,
                    fingerprint=proof_fp,
                    scope_sha256=scope.manifest_sha256,
                    content_fingerprints={
                        path: sha256_text(resolved_text)
                    },
                    registry_path=validation_registry,
                    frozen_contract_hashes=frozen_contract_hashes,
                    targeted_nodes=(path,),
                    interface_nodes=self._role_bound_validation_nodes(
                        path,
                        role="interface_contract",
                        production_text=resolved_text,
                    ),
                    contour_nodes=self._role_bound_validation_nodes(
                        path,
                        role="affected_contour",
                        production_text=resolved_text,
                    ),
                    production_texts={path: resolved_text},
                ).compile()
                inventory_rows = plan.payload.get("validation_inventory")
                if isinstance(inventory_rows, list):
                    validation_inventory = [
                        dict(row)
                        for row in inventory_rows
                        if isinstance(row, dict)
                    ]
                    break

        state_final = detect_operation_state(self.repo_root, git)
        remaining = [e.path for e in state_final.unmerged]
        if remaining:
            raise StopRequired("UNMERGED_REMAIN_AFTER_STAGE", {"paths": remaining})
        # Staged resolution paths are expected; anything else is contamination.
        contamination_gate(state_final, scope_paths=set(validated_paths))
        assert_repo_contracts_unchanged(
            self.repo_root,
            frozen_contract_hashes,
        )
        for unit_receipt in unit_receipts:
            unit_path = str(unit_receipt["path"])
            staged_candidate = unit_receipt.get("staged_candidate")
            if not isinstance(staged_candidate, dict):
                raise StopRequired(
                    "STAGED_CANDIDATE_EVIDENCE_MISSING",
                    {"path": unit_path},
                )
            _verify_staged_evidence(
                git=git,
                repo_root=self.repo_root,
                evidence={
                    str(key): str(value)
                    for key, value in staged_candidate.items()
                },
            )

        # Cancellation is the first terminal transition. The ledger is sealed
        # as PREPARED; only the atomic terminal bundle commits success.
        barrier = supervisor().close_barrier(reason="RUN_COMPLETE")
        if (
            not barrier.get("CANCELLATION_BARRIER_CLOSED")
            or barrier.get("BACKGROUND_PROCESSES", 1) != 0
        ):
            raise StopRequired("CANCELLATION_BARRIER_FAILED", barrier)
        ledger.append("CANCELLATION_BARRIER_CLOSED", barrier)
        ledger.append(
            "TERMINAL_PREPARED",
            {"paths": validated_paths, "continue": False},
        )
        final_hash = ledger.append(
            "LEDGER_FINALIZED",
            {"paths": validated_paths, "terminal": "PREPARED"},
        )
        ledger_ok = verify_ledger_file(ledger.path)
        action_claims = _derive_action_claims(ledger.path)
        conflict_marker_count = 0
        for validated_path in validated_paths:
            _, validated_file = resolve_under_repo(
                self.repo_root,
                validated_path,
            )
            content = validated_file.read_bytes()
            conflict_marker_count += sum(
                content.count(marker)
                for marker in (b"<<<<<<<", b"=======", b">>>>>>>")
            )

        run_manifest = RunManifest(
            run_id=run_id,
            package_version=PACKAGE_VERSION,
            repository_identity=state.repository_identity,
            repository_root=str(self.repo_root),
            operation=state.operation,
            initial_fingerprint=run_manifest.initial_fingerprint,
            last_verified_fingerprint=state_final.fingerprint,
            status="READY_FOR_OWNER_CONTINUE",
            completed_units=tuple(completed),
            staged_paths=tuple(staged),
            owner_decision_state="AWAITING_OWNER_CONTINUE",
            ledger_final_hash=final_hash,
        )
        run_receipt = build_run_receipt(
            run_id=run_id,
            operation=state.operation,
            repository_identity=state.repository_identity,
            start_head=state.head,
            final_head=state_final.head,
            initial_state_fingerprint=proof_fp,
            final_state_fingerprint=state_final.fingerprint,
            authority_sources=list(authority.payload.get("sources", [])),
            host_contract_sha256=frozen_contract_hashes,
            host_contract_set_digest=frozen_contract_set_digest,
            registry_sha256=frozen_contract_hashes[
                ".cursor/static-check/registry.yaml"
            ],
            selected_check_ids=[
                str(check.get("check_id"))
                for unit_receipt in unit_receipts
                for check in unit_receipt.get("checks", [])
            ],
            unit_receipts=unit_receipts,
            ledger_final_hash=final_hash,
            final_checks=[
                dict(check)
                for unit_receipt in unit_receipts
                for check in unit_receipt.get("checks", [])
            ],
            unmerged_entries=len(state_final.unmerged),
            conflict_markers=conflict_marker_count,
            forbidden_commands_executed=int(
                action_claims["forbidden_commands_executed"]
            ),
            forbidden_command_argv=list(
                action_claims["forbidden_command_argv"]
            ),
            push_performed=bool(action_claims["push_performed"]),
            background_processes=supervisor().live_count(),
            validation_inventory=validation_inventory,
        )
        terminal_bundle = {
            "schema": "opsx-resolve-conflict/terminal-bundle/v1",
            "status": "READY_FOR_OWNER_CONTINUE",
            "run_id": run_id,
            "ledger_terminal_state": "PREPARED",
            "ledger_final_hash": final_hash,
            "run_manifest": run_manifest.to_dict(),
            "run_receipt": run_receipt,
            "run_manifest_sha256": sha256_canonical(run_manifest.to_dict()),
            "run_receipt_sha256": sha256_canonical(run_receipt),
        }
        terminal_bundle_path = self.state_root / f"{run_id}.terminal.json"
        persist_private_json(terminal_bundle_path, terminal_bundle)
        terminal_bundle_sha256 = sha256_canonical(terminal_bundle)
        # Terminal bundle is the durability point. Release failures must finish
        # idempotently and must never convert durable success into STOP.
        publication_cache_errors: list[str] = []
        transaction_root = self.state_root / "write-transactions" / run_id
        try:
            if transaction_root.is_dir():
                for journal_path in sorted(transaction_root.rglob("*.json")):
                    try:
                        journal = json.loads(
                            journal_path.read_text(encoding="utf-8")
                        )
                    except (OSError, json.JSONDecodeError):
                        continue
                    if str(journal.get("state", "")) not in {
                        "VERIFIED",
                        "STAGED",
                        "RELEASE_COMMITTED",
                    }:
                        continue
                    candidate = journal.get("candidate_sha256")
                    if isinstance(candidate, str):
                        release_write_transaction(
                            journal_path,
                            expected_candidate_sha256=candidate,
                        )
            retire_write_transactions(transaction_root)
        except Exception as release_exc:
            publication_cache_errors.append(f"rollback_release:{release_exc}")
            try:
                recover_write_transactions(
                    self.repo_root,
                    self.state_root / "write-transactions",
                    terminal_success_run_ids={run_id},
                )
            except Exception as finish_exc:
                publication_cache_errors.append(
                    f"rollback_release_finish:{finish_exc}"
                )

        # Canonical manifest/receipt are recoverable caches. Failure to refresh
        # either cannot turn an already committed terminal bundle into STOP.
        try:
            persist_private_json(
                self.state_root / f"{run_id}.run-receipt.json",
                run_receipt,
            )
        except Exception as exc:
            publication_cache_errors.append(f"run_receipt:{exc}")
        try:
            save_run_manifest(self._manifest_path(run_id), run_manifest)
        except Exception as exc:
            publication_cache_errors.append(f"run_manifest:{exc}")

        result = OrchestrationResult(
            status="READY_FOR_OWNER_CONTINUE",
            repository_root=str(self.repo_root),
            run_id=run_id,
            fingerprint=state_final.fingerprint,
            payload={
                "OWNER_CONTINUE_REQUIRED": True,
                "gate": gate,
                "initial_state": self._state_dict(state),
                "final_state": self._state_dict(state_final),
                "stage_matrix": {p: [r.to_dict() for r in roles] for p, roles in stage_matrix.items()},
                "authority": asdict(authority),
                "scope": scope.to_dict(),
                "validated_paths": validated_paths,
                "write_proofs": [asdict(p) for p in write_proofs],
                "check_receipts": [asdict(r) for r in check_receipts],
                "unit_receipts": unit_receipts,
                "run_receipt": run_receipt,
                "semantic_proofs": semantic_proofs,
                "logical_units": logical_units,
                "operation_change_graph": operation_graph,
                "run_manifest": run_manifest.to_dict(),
                "state_root": str(self.state_root),
                "ledger_final_hash": final_hash,
                "ledger_verify": ledger_ok,
                "terminal_bundle_path": str(terminal_bundle_path),
                "terminal_bundle_sha256": terminal_bundle_sha256,
                "publication_cache_errors": publication_cache_errors,
                "git_continue": "FORBIDDEN",
                "RESOLVED_CLAIMED": False,
                "OPSX_FULL_VALIDATION_CLAIMED": True,
                "FINAL_VALIDATION": "FULL",
                "BACKGROUND_PROCESSES": 0,
                "CANCELLATION_BARRIER_CLOSED": True,
                "base": base,
                "final": final,
                "NEXT_ACTION": (
                    "Owner may run git merge|rebase|cherry-pick --continue "
                    "manually after review"
                ),
            },
        )
        supervisor().release_barrier()
        return result

    def verify_ledger(self, path: Path) -> dict[str, Any]:
        return verify_ledger_file(path)

    def cancel(self) -> dict[str, Any]:
        return supervisor().cancel_all(reason="STOP")


def _as_json(result: OrchestrationResult | dict[str, Any]) -> str:
    if isinstance(result, OrchestrationResult):
        payload = {
            "status": result.status,
            "repository_root": result.repository_root,
            "run_id": result.run_id,
            "fingerprint": result.fingerprint,
            "payload": result.payload,
        }
    else:
        payload = result
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2)
