"""Schema-bound unit/run/stop receipts for R11 GO/STOP paths.

Normative JSON Schemas live under ``schemas/``. A terminal run receipt is built
only after the mandatory Wave A/B matrix and cancellation barrier pass.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Mapping

from .attestation import PACKAGE_ROOT, PACKAGE_VERSION
from .errors import StopRequired
from .hashutil import sha256_canonical


def _load_schema(name: str) -> dict[str, Any]:
    """Load a packaged JSON Schema by file name."""
    path = PACKAGE_ROOT / "schemas" / name
    if not path.is_file():
        raise StopRequired("RECEIPT_SCHEMA_MISSING", {"schema": name})
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_value(value: Any, schema: Mapping[str, Any], *, field: str) -> None:
    """Validate the JSON-Schema subset used by packaged receipt contracts."""
    if "const" in schema and value != schema["const"]:
        raise StopRequired(
            "RECEIPT_SCHEMA_INVALID",
            {"field": field, "expected": schema["const"], "actual": value},
        )
    if "enum" in schema and value not in schema["enum"]:
        raise StopRequired(
            "RECEIPT_SCHEMA_INVALID",
            {"field": field, "allowed": schema["enum"], "actual": value},
        )
    expected_type = schema.get("type")
    allowed_types = (
        expected_type if isinstance(expected_type, list) else [expected_type]
    )
    type_map = {
        "object": dict,
        "array": list,
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "null": type(None),
    }
    if expected_type is not None and not any(
        isinstance(value, type_map[item]) for item in allowed_types
    ):
        raise StopRequired(
            "RECEIPT_SCHEMA_INVALID",
            {"field": field, "expected_type": allowed_types},
        )
    if isinstance(value, str):
        if len(value) < int(schema.get("minLength", 0)):
            raise StopRequired("RECEIPT_SCHEMA_INVALID", {"field": field})
        pattern = schema.get("pattern")
        if pattern and re.fullmatch(pattern, value) is None:
            raise StopRequired(
                "RECEIPT_SCHEMA_INVALID",
                {"field": field, "pattern": pattern},
            )
    if isinstance(value, list):
        if len(value) < int(schema.get("minItems", 0)):
            raise StopRequired("RECEIPT_SCHEMA_INVALID", {"field": field})
        item_schema = schema.get("items")
        if isinstance(item_schema, Mapping):
            for index, item in enumerate(value):
                _validate_value(item, item_schema, field=f"{field}[{index}]")
    if isinstance(value, dict):
        _validate_schema(value, schema, field=field)


def _validate_schema(
    payload: Mapping[str, Any],
    schema: Mapping[str, Any],
    *,
    field: str = "$",
) -> None:
    """Fail closed on required fields, types, patterns and extra properties."""
    required = schema.get("required", [])
    props = schema.get("properties", {})
    missing = [key for key in required if key not in payload]
    if missing:
        raise StopRequired(
            "RECEIPT_SCHEMA_INVALID",
            {"field": field, "missing": missing},
        )
    if schema.get("additionalProperties") is False:
        extras = sorted(set(payload) - set(props))
        if extras:
            raise StopRequired(
                "RECEIPT_SCHEMA_INVALID",
                {"field": field, "additional_properties": extras},
            )
    for key, prop in props.items():
        if key in payload:
            _validate_value(payload[key], prop, field=f"{field}.{key}")


def validate_unit_receipt(payload: Mapping[str, Any]) -> None:
    """Validate an interim unit receipt against the packaged schema."""
    _validate_schema(payload, _load_schema("unit-receipt.schema.json"))


def validate_run_receipt(payload: Mapping[str, Any]) -> None:
    """Validate an interim run receipt against the packaged schema."""
    _validate_schema(payload, _load_schema("run-receipt.schema.json"))


def _fsync_dir(path: Path) -> None:
    """Durably sync a directory entry on platforms that support it."""
    import os

    flags = getattr(os, "O_RDONLY", 0)
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    try:
        fd = os.open(str(path), flags)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def persist_private_json(path: Path, payload: Mapping[str, Any]) -> Path:
    """Atomically persist a current-user-only JSON receipt with fsync durability."""
    import os

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    try:
        tmp.chmod(0o600)
    except OSError:
        pass
    os.replace(tmp, path)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    _fsync_dir(path.parent)
    return path


def build_unit_receipt(
    *,
    run_id: str,
    path: str,
    topology: str,
    operation: str,
    write_proof_token: str,
    semantic_proof: Mapping[str, Any],
    stage_roles: list[Mapping[str, Any]],
    authority_sources: list[Mapping[str, Any]],
    scope_manifest_hash: str,
    fingerprint_before: str,
    fingerprint_after: str,
    worktree_hash_before: str,
    worktree_hash_after: str,
    stage_oids: Mapping[str, str],
    staged_candidate: Mapping[str, str],
    diff_sha256: str,
    checks: list[Mapping[str, Any]],
    risk: str,
    ledger_record_hash: str,
) -> dict[str, Any]:
    """Build and validate one per-path unit receipt."""
    receipt = {
        "schema": "opsx-resolve-conflict/unit-receipt/v1",
        "package_version": PACKAGE_VERSION,
        "run_id": run_id,
        "path": path,
        "topology": topology,
        "step_id": f"unit:{path}",
        "unit_id": f"unit:{path}",
        "operation": operation,
        "paths": [path],
        "stage_roles": [dict(role) for role in stage_roles],
        "authority_sources": [dict(source) for source in authority_sources],
        "scope_manifest_hash": scope_manifest_hash,
        "state_fingerprint_before": fingerprint_before,
        "write_proof": write_proof_token,
        "semantic_proof": dict(semantic_proof),
        "fingerprint_after": fingerprint_after,
        "state_fingerprint_after": fingerprint_after,
        "worktree_hashes_before": {path: worktree_hash_before},
        "worktree_hashes_after": {path: worktree_hash_after},
        "diff_sha256": diff_sha256,
        "behavior_preserved": list(
            semantic_proof.get("preserved_from_stage2", ())
        )
        + list(semantic_proof.get("preserved_from_stage3", ())),
        "behavior_superseded": [],
        "checks": [dict(check) for check in checks],
        "risk": risk if risk in {"LOW", "MEDIUM", "HIGH"} else "HIGH",
        "confidence": "NOT_HIGH",
        "remaining_risks": [
            "single_file_autonomous_class",
            "external_sandbox_runner_trusted_by_digest",
            "semantic_proof_static_ast_class_only",
            "partial_spec_authority_path_lineage_heuristic",
            "preview_package_without_bundled_os_verified_sandbox",
        ],
        "ledger_record_hash": ledger_record_hash,
        "stage_oids": dict(stage_oids),
        "staged_candidate": dict(staged_candidate),
    }
    validate_unit_receipt(receipt)
    return receipt


def build_run_receipt(
    *,
    run_id: str,
    operation: str,
    repository_identity: str,
    start_head: str,
    final_head: str,
    initial_state_fingerprint: str,
    final_state_fingerprint: str,
    authority_sources: list[Mapping[str, Any]],
    host_contract_sha256: Mapping[str, str],
    host_contract_set_digest: str,
    registry_sha256: str,
    selected_check_ids: list[str],
    unit_receipts: list[Mapping[str, Any]],
    ledger_final_hash: str,
    final_checks: list[Mapping[str, Any]],
    unmerged_entries: int,
    conflict_markers: int,
    forbidden_commands_executed: int,
    forbidden_command_argv: list[list[str]],
    push_performed: bool,
    background_processes: int,
    validation_inventory: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build and validate the terminal interim run receipt."""
    inventory = [dict(row) for row in (validation_inventory or [])]
    passed_ids = {
        str(check.get("check_id"))
        for check in final_checks
        if int(check.get("exit_code", 1)) == 0
    }
    finalized_inventory: list[dict[str, Any]] = []
    for row in inventory:
        item = dict(row)
        status = str(item.get("status", ""))
        if status in {"REQUIRED", "SCHEDULED"}:
            # REQUIRED is the R24 pre-write plan status; SCHEDULED retained as
            # a synonym for older receipts during transition.
            required = [str(cid) for cid in item.get("check_ids", [])]
            if all(cid in passed_ids for cid in required):
                item["status"] = "PASSED"
            else:
                item["status"] = "BLOCKED"
                item["reason"] = "required_check_not_passed"
        finalized_inventory.append(item)
    inventory_complete = bool(finalized_inventory) and all(
        str(row.get("status")) in {"PASSED", "NOT_APPLICABLE"}
        for row in finalized_inventory
    )
    if finalized_inventory and not inventory_complete:
        raise StopRequired(
            "OPSX_VALIDATION_INVENTORY_NOT_GREEN",
            {"inventory": finalized_inventory},
        )
    receipt = {
        "schema": "opsx-resolve-conflict/run-receipt/v1",
        "package_version": PACKAGE_VERSION,
        "run_id": run_id,
        "operation": operation,
        "repository_identity": repository_identity,
        "start_head": start_head,
        "final_head": final_head,
        "initial_state_fingerprint": initial_state_fingerprint,
        "final_state_fingerprint": final_state_fingerprint,
        "authority_sources": [dict(source) for source in authority_sources],
        "host_contract_sha256": dict(host_contract_sha256),
        "host_contract_set_digest": host_contract_set_digest,
        "registry_sha256": registry_sha256,
        "selected_check_ids": list(selected_check_ids),
        "unit_receipt_hashes": [sha256_canonical(dict(u)) for u in unit_receipts],
        "ledger_final_hash": ledger_final_hash,
        "unmerged_entries": unmerged_entries,
        "conflict_markers": conflict_markers,
        "forbidden_commands_executed": forbidden_commands_executed,
        "forbidden_command_argv": forbidden_command_argv,
        "push_performed": push_performed,
        "background_processes": background_processes,
        "final_checks": [dict(check) for check in final_checks],
        "validation_inventory": finalized_inventory,
        "validation_inventory_complete": inventory_complete,
        "cancellation_barrier_closed": True,
        "final_validation": "FULL" if inventory_complete else "INCOMPLETE",
        "opsx_full_validation_claimed": bool(inventory_complete),
        "resolved_claimed": False,
    }
    validate_run_receipt(receipt)
    return receipt


def persist_stop_receipt(
    state_root: Path,
    *,
    run_id: str,
    fingerprint: str,
    repository_root: str,
    stop_reason: str,
    evidence: Mapping[str, Any],
    cancellation_barrier_closed: bool,
    background_processes: int,
    git_state: Mapping[str, Any] | None = None,
    completed_units: list[str] | None = None,
    staged_paths: list[str] | None = None,
    ledger_final_hash: str | None = None,
    owner_blocker: str | None = None,
    next_action: str = "Owner must inspect STOP evidence and choose recovery.",
) -> Path:
    """Persist a reconstructable STOP receipt under the durable state root."""
    state_root.mkdir(parents=True, exist_ok=True)
    rid = run_id or "unknown"
    path = state_root / f"{rid}.stop.json"
    payload = {
        "schema": "opsx-resolve-conflict/stop-receipt/v1",
        "package_version": PACKAGE_VERSION,
        "run_id": rid,
        "fingerprint": fingerprint or "",
        "repository_root": repository_root,
        "stop_reason": stop_reason,
        "evidence": dict(evidence),
        "cancellation_barrier_closed": bool(cancellation_barrier_closed),
        "background_processes": int(background_processes),
        "git_state": dict(git_state or {}),
        "completed_units": list(completed_units or []),
        "staged_paths": list(staged_paths or []),
        "failed_gate": stop_reason,
        "ledger_final_hash": ledger_final_hash,
        "owner_blocker": owner_blocker or stop_reason,
        "next_action": next_action,
    }
    return persist_private_json(path, payload)
