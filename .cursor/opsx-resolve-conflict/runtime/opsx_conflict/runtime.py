"""Typed facade for the sealed `/opsx-resolve-conflict` runtime."""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from .attestation import (
    CONTRACT_SCHEMA_VERSION,
    PACKAGE_VERSION,
    effective_acl_ok,
    inventory_hashes,
    load_manifest,
    package_compatibility_gate,
)
from .cancellation import ProcessSupervisor, reset_supervisor_for_tests, run_process, supervisor
from .change_graph import ContractView, extract_python_contracts
from .errors import (
    CLI_STOP_ENVELOPE_SCHEMA,
    CLI_STOP_EXIT_CODE,
    CLI_STOP_SCHEMA_VERSION,
    STOP_REASON_REACHED_GATE,
    PolicyViolation,
    StateDrift,
    StopRequired,
)
from .git_typed import TypedGit
from .hashutil import canonical_json, sha256_bytes, sha256_canonical, sha256_text
from .ledger import ExecutionLedger, verify_ledger as _verify_ledger_file
from .operation import OperationState, contamination_gate, conflict_start_gate, detect_operation_state, hash_sequencer_tree, parse_unmerged_z, repo_identity
from .proofs import Proof
from .scope import SCOPE_SCHEMA, ScopeItem, ScopeManifest
from .validation import (
    FrozenCheck,
    FrozenTestPlanCompiler,
    assert_frozen_argv,
    build_validation_snapshot as _build_validation_snapshot,
    effective_final_gate as _effective_final_gate,
    minimal_validation_env,
    run_frozen_check,
)
from .process_surfaces import classify_path_risk as _base_classify_path_risk
from .write_atomic import detect_newline, encode_with_newline, write_scoped_file
from .orchestrator import SealedOrchestrator

SUPPORTED_PYTHON = ">=3.11"
GitClient = TypedGit
TestPlanCompiler = FrozenTestPlanCompiler
verify_ledger = _verify_ledger_file
run_validation_check = run_frozen_check


@dataclasses.dataclass(frozen=True, init=False)
class StageEntry:
    """Compatibility stage-entry object accepted by the legacy tests."""

    mode: str
    blob_oid: str
    stage: int
    path: str

    def __init__(
        self,
        mode: str,
        stage: int,
        path: str,
        blob_oid: str | None = None,
        oid: str | None = None,
    ) -> None:
        value = blob_oid if blob_oid is not None else oid
        if value is None:
            raise TypeError("StageEntry requires blob_oid or oid")
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "blob_oid", value)
        object.__setattr__(self, "stage", stage)
        object.__setattr__(self, "path", path)

    @property
    def oid(self) -> str:
        return self.blob_oid


OperationState.head_oid = property(lambda self: self.head)  # type: ignore[attr-defined]
OperationState.operation_head_oid = property(lambda self: self.operation_head)  # type: ignore[attr-defined]
OperationState.rebase_backend = property(  # type: ignore[attr-defined]
    lambda self: "rebase-merge"
    if (self.git_dir / "rebase-merge").exists()
    else ("rebase-apply" if (self.git_dir / "rebase-apply").exists() else None)
)


@dataclasses.dataclass(frozen=True)
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
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class RunManifest:
    """Durable run metadata used by resume guards."""

    run_id: str
    package_version: str
    repository_identity: str
    repository_root: str
    operation: str
    initial_fingerprint: str
    last_verified_fingerprint: str
    status: str
    completed_units: tuple[str, ...]
    staged_paths: tuple[str, ...]
    owner_decision_state: str | None
    ledger_final_hash: str | None

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def _state_dict(state: OperationState) -> dict[str, Any]:
    return {
        "operation": state.operation,
        "head": state.head,
        "operation_head": state.operation_head,
        "branch": state.branch,
        "fingerprint": state.fingerprint,
        "unmerged": [dataclasses.asdict(entry) for entry in state.unmerged],
        "staged_paths": list(state.staged_paths),
        "unstaged_paths": list(state.unstaged_paths),
        "untracked_paths": list(state.untracked_paths),
        "sequencer_tree_hash": state.sequencer_tree_hash,
        "repository_identity": state.repository_identity,
        "git_dir": str(state.git_dir),
        "raw_status": state.raw_status,
        "details": dict(state.details),
    }


def stage_role_matrix(state: OperationState, git: TypedGit) -> Mapping[str, tuple[StageRole, ...]]:
    """Build the stage-role matrix for every conflicted path."""

    by_path: dict[str, dict[int, StageEntry]] = {}
    for entry in state.unmerged:
        by_path.setdefault(entry.path, {})[entry.stage] = entry

    matrix: dict[str, tuple[StageRole, ...]] = {}
    for path, stages in by_path.items():
        if state.operation == "merge":
            merge_base = git.merge_base(state.head, state.operation_head or state.head)
            refs = {1: ("merge_base", merge_base), 2: ("current_HEAD", state.head), 3: ("incoming_MERGE_HEAD", state.operation_head)}
        elif state.operation == "rebase":
            if not state.operation_head:
                raise StopRequired("REBASE_HEAD_MISSING")
            refs = {1: ("parent_of_replayed_commit", f"{state.operation_head}^"), 2: ("accumulated_onto_plus_replayed_commits", state.head), 3: ("current_replayed_commit", state.operation_head)}
        elif state.operation == "cherry-pick":
            if not state.operation_head:
                raise StopRequired("CHERRY_PICK_HEAD_MISSING")
            refs = {1: ("parent_of_cherry_picked_commit", f"{state.operation_head}^"), 2: ("current_HEAD", state.head), 3: ("cherry_picked_commit", state.operation_head)}
        else:
            raise StopRequired("UNSUPPORTED_OPERATION", {"operation": state.operation})

        roles: list[StageRole] = []
        for stage in (1, 2, 3):
            role, ref = refs[stage]
            actual = stages.get(stage).oid if stage in stages else None
            expected = git.rev_parse(f"{ref}:{path}") if ref else None
            verified = actual == expected or (actual is None and not expected)
            roles.append(StageRole(stage=stage, role=role, commit_oid=str(ref) if ref else None, expected_blob_oid=expected or None, actual_blob_oid=actual, verified=verified, note=("verified" if verified else "stage/blob origin mismatch")))
        if not all(r.verified for r in roles):
            raise StopRequired("STAGE_ROLE_MATRIX_MISMATCH", {"path": path, "roles": [r.to_dict() for r in roles]})
        matrix[path] = tuple(roles)
    return matrix


def classify_conflict(path: str, entries: Sequence[StageEntry], *, mode_by_stage: Mapping[int, str] | None = None) -> str:
    """Classify an unmerged path into the supported conflict taxonomy."""

    stages = {entry.stage for entry in entries}
    if stages == {2, 3}:
        return "add/add"
    if stages == {1, 2}:
        return "modify/delete"
    if stages == {1, 3}:
        return "delete/modify"
    if stages == {1, 2, 3}:
        modes = mode_by_stage or {entry.stage: entry.mode for entry in entries}
        return "file-mode-or-type" if len(set(modes.values())) > 1 else "modify/modify"
    return "other"


def operation_state_to_dict(state: OperationState) -> dict[str, Any]:
    return _state_dict(state)


def classify_path_risk(path: str, *, topology: str | None = None) -> str:
    rel = str(path).replace("\\", "/")
    if topology in {"directory-rename", "rename/rename", "rename/delete", "rename/add", "rename/modify", "file/symlink", "file-mode", "submodule", "binary"}:
        return "HIGH"
    if rel.startswith((".cursor/commands/", ".cursor/rules/", ".cursor/skills/", ".cursor/agents/", ".cursor/static-check/", ".cursor/pipeline/", ".cursor/antipattern-gate/", ".agents/", ".github/skills/", ".github/prompts/")):
        return "HIGH"
    if rel in {".cursor/opsx-review-commands", ".github/copilot-instructions.md", ".github/git-commit-instructions.md", "AGENTS.md", "openspec/config.yaml", "openspec/decisions/index.md"}:
        return "HIGH"
    if rel.startswith(("openspec/policies/", "openspec/decisions/", "openspec/changes/", ".tmp/opsx-bug-cases/", "alembic_/versions/", "migrations/")):
        return "HIGH"
    if rel.endswith((".lock", "poetry.lock", "package-lock.json", "pnpm-lock.yaml", "yarn.lock")):
        return "HIGH"
    return _base_classify_path_risk(path, topology=topology)


def detect_logical_conflict_candidates(source_files: Mapping[str, str], target_files: Mapping[str, str], textual_conflict_paths: Sequence[str] = ()) -> list[dict[str, Any]]:
    """Legacy wrapper that scans Python contract interactions by file pair."""

    textual = {str(x).replace("\\", "/") for x in textual_conflict_paths}
    source_contracts = {p: extract_python_contracts(t) for p, t in source_files.items() if p.endswith('.py')}
    target_contracts = {p: extract_python_contracts(t) for p, t in target_files.items() if p.endswith('.py')}
    candidates: list[dict[str, Any]] = []
    for spath, s in source_contracts.items():
        for tpath, t in target_contracts.items():
            if spath in textual or tpath in textual:
                continue
            if not s.parse_ok or not t.parse_ok:
                candidates.append({"source_path": spath, "target_path": tpath, "reason": "syntax-error", "parse_ok": False})
                continue
            def_call = sorted(set(s.definitions) & set(t.calls))
            call_def = sorted(set(s.calls) & set(t.definitions))
            import_overlap = sorted(set(s.imports) & set(t.definitions))
            if def_call or call_def or import_overlap:
                candidates.append({
                    "source_path": spath,
                    "target_path": tpath,
                    "reason": "cross-file contract interaction",
                    "source_defs_target_calls": def_call,
                    "source_calls_target_defs": call_def,
                    "imports_overlap": import_overlap,
                })
    return candidates


@dataclasses.dataclass(frozen=True)
class PathTopologyChange:
    """Topology change record used for directory-rename heuristics."""

    status: str
    old_path: str | None
    new_path: str
    score: int | None = None


def parse_name_status(raw: str) -> tuple[PathTopologyChange, ...]:
    """Parse `git diff --name-status` output."""

    changes: list[PathTopologyChange] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("	")
        code = parts[0]
        if code.startswith(("R", "C")):
            if len(parts) != 3:
                raise StopRequired("INVALID_NAME_STATUS_RENAME_RECORD", {"line": line})
            score = int(code[1:]) if code[1:].isdigit() else None
            changes.append(
                PathTopologyChange(
                    status="rename" if code.startswith("R") else "copy",
                    old_path=parts[1],
                    new_path=parts[2],
                    score=score,
                )
            )
        else:
            if len(parts) != 2:
                raise StopRequired("INVALID_NAME_STATUS_RECORD", {"line": line})
            mapping = {"A": "add", "M": "modify", "D": "delete", "T": "type-change", "U": "unmerged"}
            changes.append(PathTopologyChange(status=mapping.get(code, f"other:{code}"), old_path=None, new_path=parts[1]))
    return tuple(changes)


def detect_directory_renames(changes: Sequence[PathTopologyChange]) -> tuple[Mapping[str, Any], ...]:
    """Group coherent renames into directory-rename candidates."""

    groups: dict[tuple[str, str], list[PathTopologyChange]] = {}
    for change in changes:
        if change.status != "rename" or not change.old_path:
            continue
        old_parent = str(Path(change.old_path).parent.as_posix())
        new_parent = str(Path(change.new_path).parent.as_posix())
        if old_parent == new_parent:
            continue
        groups.setdefault((old_parent, new_parent), []).append(change)
    out: list[Mapping[str, Any]] = []
    for (old_dir, new_dir), items in sorted(groups.items()):
        if len(items) >= 2:
            out.append({
                "type": "directory-rename",
                "old_dir": old_dir,
                "new_dir": new_dir,
                "paths": [{"old": x.old_path, "new": x.new_path, "score": x.score} for x in items],
            })
    return tuple(out)


def untracked_gate(state: OperationState, *, explicit_inert_allowlist: Mapping[str, str] | None = None) -> None:
    """Fail closed unless all untracked files are explicitly allowlisted."""

    allow = dict(explicit_inert_allowlist or {})
    violations = [path for path in state.untracked_paths if allow.get(path) != sha256_text(Path(path).name)]
    if violations:
        raise StopRequired("UNTRACKED_CONTAMINATION", {"untracked": violations})


def create_metadata_snapshot(run_dir: Path, state: OperationState, *, stage_matrix: Mapping[str, Sequence[StageRole]]) -> Path:
    """Write a metadata-only snapshot without plaintext file copies."""

    payload = {
        "schema": CONTRACT_SCHEMA_VERSION,
        "snapshot_mode": "METADATA_ONLY_NO_FILE_CONTENT",
        "state": _state_dict(state),
        "state_fingerprint": state.fingerprint,
        "stage_matrix": {path: [role.to_dict() for role in roles] for path, roles in stage_matrix.items()},
    }
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2)
    path = run_dir / "initial-snapshot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def save_run_manifest(path: Path, manifest: RunManifest) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(manifest.to_dict(), ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    try:
        tmp.chmod(0o600)
    except OSError:
        pass
    os.replace(tmp, path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def load_run_manifest(path: Path) -> RunManifest:
    data = json.loads(path.read_text(encoding="utf-8"))
    return RunManifest(
        run_id=data["run_id"],
        package_version=data["package_version"],
        repository_identity=data["repository_identity"],
        repository_root=data["repository_root"],
        operation=data["operation"],
        initial_fingerprint=data["initial_fingerprint"],
        last_verified_fingerprint=data["last_verified_fingerprint"],
        status=data["status"],
        completed_units=tuple(data.get("completed_units", ())),
        staged_paths=tuple(data.get("staged_paths", ())),
        owner_decision_state=data.get("owner_decision_state"),
        ledger_final_hash=data.get("ledger_final_hash"),
    )


def resume_guard(manifest: RunManifest, state: OperationState) -> None:
    if manifest.package_version != PACKAGE_VERSION:
        raise StopRequired("RUN_PACKAGE_VERSION_MISMATCH", {"run": manifest.package_version, "current": PACKAGE_VERSION})
    if manifest.repository_identity != state.repository_identity:
        raise StopRequired("RUN_REPOSITORY_IDENTITY_MISMATCH")
    expected_root = os.path.normcase(str(Path(manifest.repository_root).resolve()))
    actual_root = os.path.normcase(str(Path(state.git_dir).resolve().parent))
    if expected_root != actual_root:
        raise StopRequired("RUN_REPOSITORY_MISMATCH")
    if manifest.operation != state.operation:
        raise StopRequired("RUN_OPERATION_MISMATCH")
    if manifest.last_verified_fingerprint != state.fingerprint:
        raise StopRequired("RUN_STATE_DRIFT", {"expected": manifest.last_verified_fingerprint, "actual": state.fingerprint})


def build_validation_snapshot(repo_root: Path, run_dir: Path, *, ledger: ExecutionLedger | None = None, git: TypedGit | None = None) -> Path:
    git_obj = git or TypedGit(repo_root, ledger)
    return _build_validation_snapshot(repo_root, run_dir, git_obj)


def effective_final_gate(
    *,
    changed_paths: Sequence[str] | None = None,
    registry_path: Path | None = None,
    requested_mode: str = "FULL",
    frozen_contract_hashes: Mapping[str, str] | None = None,
) -> list[str]:
    """Return the validated registry-derived FULL check sequence."""
    _ = changed_paths
    return _effective_final_gate(
        registry_path=registry_path,
        requested_mode=requested_mode,
        frozen_contract_hashes=frozen_contract_hashes,
    )


def _empty_hooks_dir() -> str:
    hooks = Path(__file__).resolve().parent / "_empty_hooks"
    hooks.mkdir(exist_ok=True)
    return str(hooks)


def _run_process(argv: Sequence[str], *, cwd: Path | str | None = None, env: Mapping[str, str] | None = None, timeout: float = 60.0):
    return run_process(list(argv), cwd=cwd, env=dict(env or {}), timeout=timeout)


def build_cli_stop_envelope(
    *,
    reason: str,
    details: Mapping[str, Any] | None,
    command: str,
) -> dict[str, Any]:
    """Build the stable CLI StopRequired JSON envelope (R29).

    Unexpected internal exceptions must not use this helper — only typed
    ``StopRequired`` (and CLI-mapped orchestrator STOP terminals).
    """
    detail_map = dict(details or {})
    reached = detail_map.pop("reached_gate", None) or STOP_REASON_REACHED_GATE.get(
        reason
    )
    envelope: dict[str, Any] = {
        "schema": CLI_STOP_ENVELOPE_SCHEMA,
        "schema_version": CLI_STOP_SCHEMA_VERSION,
        "status": "STOP",
        "reason": reason,
        "details": detail_map,
        "command": command,
        "package_version": PACKAGE_VERSION,
    }
    if reached:
        envelope["reached_gate"] = reached
    return envelope


def emit_cli_stop(
    *,
    reason: str,
    details: Mapping[str, Any] | None,
    command: str,
) -> int:
    """Print StopRequired envelope to stdout and return the stable STOP exit code."""
    envelope = build_cli_stop_envelope(
        reason=reason, details=details, command=command
    )
    print(json.dumps(envelope, ensure_ascii=True, sort_keys=True, indent=2))
    return CLI_STOP_EXIT_CODE


def _cli() -> int:
    """Argparse CLI body; may raise ``StopRequired`` for typed fail-closed stops."""
    parser = argparse.ArgumentParser(prog="opsx_conflict")
    parser.add_argument("--version", action="store_true")
    sub = parser.add_subparsers(dest="cmd")

    p_state = sub.add_parser("state")
    p_state.add_argument("--repo", required=True)

    p_preview = sub.add_parser("preview")
    p_preview.add_argument("--repo", required=True)
    p_preview.add_argument(
        "--path",
        required=False,
        default=None,
        help="Optional single unmerged path to analyze",
    )
    p_preview.add_argument(
        "--format",
        choices=("json", "human"),
        default="json",
        help="json (machine report) or human (Russian advisory text)",
    )

    p_go = sub.add_parser("go")
    p_go.add_argument("--repo", required=True)
    p_go.add_argument("--scope", required=False)
    p_go.add_argument("--resolution", action="append", default=[])

    p_verify = sub.add_parser("verify-ledger")
    p_verify.add_argument("--ledger", required=True)

    sub.add_parser("cancel")

    args = parser.parse_args()
    if args.version:
        print(PACKAGE_VERSION)
        return 0
    if args.cmd == "state":
        orch = SealedOrchestrator(Path(args.repo))
        print(json.dumps(orch.state(), ensure_ascii=True, sort_keys=True, indent=2))
        return 0
    if args.cmd == "preview":
        from .preview_advisory import run_preview_advisory

        report = run_preview_advisory(Path(args.repo), path=args.path)
        if getattr(args, "format", "json") == "human":
            print(report.get("human_report_ru") or "")
        else:
            print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    if args.cmd == "go":
        orch = SealedOrchestrator(Path(args.repo))
        if not args.scope:
            raise StopRequired("SCOPE_FILE_REQUIRED")
        scope = ScopeManifest.load(Path(args.scope))
        resolutions = {}
        for item in args.resolution:
            if "=" not in item:
                raise PolicyViolation("resolution must be path=text")
            path, content = item.split("=", 1)
            resolutions[path] = content
        result = orch.go(scope=scope, resolutions=resolutions)
        data = dataclasses.asdict(result)
        payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
        stop_reason = payload.get("STOP_REASON")
        if data.get("status") in {"STOP", "STOP_FOR_OWNER"} and stop_reason:
            evidence = payload.get("EVIDENCE")
            details: dict[str, Any] = (
                dict(evidence) if isinstance(evidence, Mapping) else {"evidence": evidence}
            )
            if stop_reason == "PACKAGE_GO_CAPABILITY_DISABLED":
                details.setdefault("go_capability", False)
                details.setdefault("reached_gate", "package_compatibility_gate")
            return emit_cli_stop(
                reason=str(stop_reason),
                details=details,
                command="go",
            )
        print(json.dumps(data, ensure_ascii=True, sort_keys=True, indent=2))
        return 0
    if args.cmd == "verify-ledger":
        print(json.dumps(verify_ledger(Path(args.ledger)), ensure_ascii=True, sort_keys=True, indent=2))
        return 0
    if args.cmd == "cancel":
        print(json.dumps(supervisor().cancel_all(), ensure_ascii=True, sort_keys=True, indent=2))
        return 0
    parser.print_help()
    return 2


def run_cli(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint with typed StopRequired envelope; unexpected errors propagate.

    Enforces ADR-OPSX-RC-PLATFORM-001 (Windows-only) before dispatch.
    ``StopRequired`` → structured STOP envelope + ``CLI_STOP_EXIT_CODE``.
    Any other exception (including unexpected RuntimeError) is not masked as STOP
    and will surface as a traceback / nonzero process failure for replay builders.
    """
    if argv is not None:
        import sys as _sys

        _sys.argv = [_sys.argv[0], *list(argv)]
    try:
        from .attestation import assert_supported_platform

        assert_supported_platform()
        return _cli()
    except StopRequired as exc:
        command = "unknown"
        try:
            import sys as _sys

            if len(_sys.argv) > 1 and not str(_sys.argv[1]).startswith("-"):
                command = str(_sys.argv[1])
        except Exception:
            command = "unknown"
        return emit_cli_stop(
            reason=exc.reason,
            details=exc.details,
            command=command,
        )


if __name__ == "__main__":
    raise SystemExit(run_cli())
