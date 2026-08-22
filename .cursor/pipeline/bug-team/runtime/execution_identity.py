# -*- coding: utf-8 -*-
"""Authoritative execution identity (Corrective V10).

Binds one real Cursor Task agent to one WORKER_EXECUTION_ID, one dispatch
record, one orchestration/case/finding(/branch), one input packet, one output
packet, and one attempt/generation. Identity JSON alone is insufficient —
``validate_execution_identity`` reconciles against DISPATCH.jsonl, packet
bytes, checkpoint, and runtime agent id.

Host HMAC reuses ``retry_auth.ensure_host_secret`` (no separate weak scheme).

LIVE_RUNTIME_AUTHORITY: runtime/execution_identity.py
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import retry_auth

IDENTITY_RECORD_VERSION = "1"
PENDING = "PENDING_DISPATCH"

STATUS_PENDING_DISPATCH = "PENDING_DISPATCH"
STATUS_DISPATCHED = "DISPATCHED"
STATUS_OUTPUT_RECEIVED = "OUTPUT_RECEIVED"
STATUS_VALIDATED = "VALIDATED"
STATUS_REJECTED = "REJECTED"

ALLOWED_IDENTITY_STATUS = {
    STATUS_PENDING_DISPATCH,
    STATUS_DISPATCHED,
    STATUS_OUTPUT_RECEIVED,
    STATUS_VALIDATED,
    STATUS_REJECTED,
}

# Fields covered by IDENTITY_RECORD_HASH (excludes hash + host signature).
HASHED_FIELDS = (
    "IDENTITY_RECORD_VERSION",
    "ORCHESTRATION_ID",
    "CASE_ID",
    "FINDING_ID",
    "BRANCH_ID",
    "WORKER_ID",
    "WORKER_EXECUTION_ID",
    "ATTEMPT",
    "CURSOR_AGENT_ID",
    "CURSOR_AGENT_ID_SOURCE",
    "DISPATCH_RECORD_ID",
    "DISPATCH_LOG_PATH",
    "DISPATCH_RECORD_HASH",
    "INPUT_PACKET_ID",
    "INPUT_PACKET_PATH",
    "INPUT_PACKET_HASH",
    "INPUT_PACKET_GENERATION",
    "OUTPUT_PACKET_ID",
    "OUTPUT_PACKET_PATH",
    "OUTPUT_PACKET_HASH",
    "OUTPUT_PACKET_GENERATION",
    "CHECKPOINT_PATH",
    "CHECKPOINT_GENERATION",
    "STARTED_AT",
    "FINISHED_AT",
    "IDENTITY_STATUS",
)

PLACEHOLDER_PREFIXES = ("PLACEHOLDER", "TEST_PLACEHOLDER", "FAKE_AGENT", "SYNTHETIC_AGENT")


class ExecutionIdentityError(Exception):
    """Execution identity reconciliation failure."""

    def __init__(self, code: str, detail: str = "", payload: Optional[Dict[str, Any]] = None) -> None:
        self.code = code
        self.detail = detail
        self.payload = payload or {}
        super().__init__(f"{code}: {detail}" if detail else code)


@dataclass
class ExecutionIdentityValidationResult:
    """Result of authoritative identity validation against dispatch/packets."""

    STATUS: str
    VALID: bool
    REASON_CODE: str
    WORKER_EXECUTION_ID: Optional[str] = None
    CURSOR_AGENT_ID: Optional[str] = None
    DISPATCH_RECONCILIATION: str = "NOT_CHECKED"
    INPUT_PACKET_RECONCILIATION: str = "NOT_CHECKED"
    OUTPUT_PACKET_RECONCILIATION: str = "NOT_CHECKED"
    CHECKPOINT_RECONCILIATION: str = "NOT_CHECKED"
    STALE_OR_SUPERSEDED: bool = False
    MISMATCHES: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        """Serialize validation result for gates and evidence."""
        return {
            "STATUS": self.STATUS,
            "VALID": self.VALID,
            "REASON_CODE": self.REASON_CODE,
            "WORKER_EXECUTION_ID": self.WORKER_EXECUTION_ID,
            "CURSOR_AGENT_ID": self.CURSOR_AGENT_ID,
            "DISPATCH_RECONCILIATION": self.DISPATCH_RECONCILIATION,
            "INPUT_PACKET_RECONCILIATION": self.INPUT_PACKET_RECONCILIATION,
            "OUTPUT_PACKET_RECONCILIATION": self.OUTPUT_PACKET_RECONCILIATION,
            "CHECKPOINT_RECONCILIATION": self.CHECKPOINT_RECONCILIATION,
            "STALE_OR_SUPERSEDED": self.STALE_OR_SUPERSEDED,
            "MISMATCHES": list(self.MISMATCHES),
            "EXECUTION_IDENTITY_VALIDATION": "PASS" if self.VALID else "FAIL",
        }


def executions_dir(case_root: Path) -> Path:
    """Return team/executions directory under case root."""
    return Path(case_root) / "team" / "executions"


def wex_slug(wex_id: str) -> str:
    """Filesystem-safe WORKER_EXECUTION_ID slug."""
    return wex_id.replace("/", "_").replace("\\", "_")


def identity_path(case_root: Path, wex_id: str) -> Path:
    """Canonical identity path: team/executions/<WEX_SLUG>.identity.json."""
    return executions_dir(case_root) / f"{wex_slug(wex_id)}.identity.json"


def is_canonical_identity_path(case_root: Path, path: Path, wex_id: str) -> bool:
    """True when path resolves to the canonical identity location for WEX."""
    expected = identity_path(case_root, wex_id).resolve()
    try:
        return Path(path).resolve() == expected
    except OSError:
        return False


def _canonical_bytes(obj: Dict[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(Path(path).read_bytes())


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def is_placeholder_agent(agent_id: Optional[str]) -> bool:
    """True when agent id is missing, PENDING_DISPATCH, or a test placeholder."""
    if agent_id is None:
        return True
    s = str(agent_id).strip()
    if not s or s == PENDING:
        return True
    upper = s.upper()
    return any(upper.startswith(p) for p in PLACEHOLDER_PREFIXES)


# Back-compat private alias
_is_placeholder_agent = is_placeholder_agent


def _hash_material(record: Dict[str, Any]) -> Dict[str, Any]:
    return {k: record.get(k) for k in HASHED_FIELDS}


def compute_identity_record_hash(record: Dict[str, Any]) -> str:
    """SHA-256 over canonical identity fields (excludes hash/signature)."""
    return _sha256_bytes(_canonical_bytes(_hash_material(record)))


def _sign_identity(case_root: Path, record_hash: str) -> str:
    secret = retry_auth.ensure_host_secret(case_root)
    material = f"IDENTITY_V10|{record_hash}"
    return hmac.new(secret.encode("utf-8"), material.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_identity_host_signature(case_root: Path, record: Dict[str, Any]) -> bool:
    """Verify HOST_SIGNATURE against host retry authority secret."""
    expected_hash = compute_identity_record_hash(record)
    if record.get("IDENTITY_RECORD_HASH") != expected_hash:
        return False
    sig = str(record.get("HOST_SIGNATURE") or "")
    if not sig:
        return False
    expected_sig = _sign_identity(case_root, expected_hash)
    return hmac.compare_digest(expected_sig, sig)


def seal_identity_record(case_root: Path, record: Dict[str, Any]) -> Dict[str, Any]:
    """Attach IDENTITY_RECORD_HASH + HOST_SIGNATURE; return sealed copy."""
    sealed = dict(record)
    sealed["IDENTITY_RECORD_VERSION"] = sealed.get("IDENTITY_RECORD_VERSION") or IDENTITY_RECORD_VERSION
    sealed["IDENTITY_RECORD_HASH"] = compute_identity_record_hash(sealed)
    sealed["HOST_SIGNATURE"] = _sign_identity(case_root, sealed["IDENTITY_RECORD_HASH"])
    return sealed


def write_identity_record(case_root: Path, record: Dict[str, Any]) -> Path:
    """Write sealed identity to canonical path derived from WORKER_EXECUTION_ID."""
    wex = str(record["WORKER_EXECUTION_ID"])
    path = identity_path(case_root, wex)
    path.parent.mkdir(parents=True, exist_ok=True)
    sealed = seal_identity_record(case_root, record)
    path.write_text(json.dumps(sealed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_identity_record(path: Path) -> Dict[str, Any]:
    """Load identity JSON from path."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dispatch_record_id_for(wex: str, attempt: int) -> str:
    """Stable dispatch record id for a WEX attempt."""
    return f"DISP/{wex}/A{attempt}"


def hash_dispatch_record(record: Dict[str, Any]) -> str:
    """Canonical hash of a DISPATCH.jsonl record object."""
    return _sha256_bytes(_canonical_bytes(record))


def find_dispatch_record(
    dispatch_log_path: Path,
    *,
    worker_execution_id: str,
    dispatch_record_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Locate authoritative DISPATCH.jsonl record for WEX (latest matching)."""
    path = Path(dispatch_log_path)
    if not path.exists():
        return None
    found: Optional[Dict[str, Any]] = None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("WORKER_EXECUTION_ID") != worker_execution_id:
            continue
        if dispatch_record_id and obj.get("DISPATCH_RECORD_ID") != dispatch_record_id:
            continue
        found = obj
    return found


def create_pending_identity(
    case_root: Path,
    *,
    worker_execution_id: str,
    input_packet_id: str,
    dispatch_record_id: Optional[str] = None,
    orchestration_id: Optional[str] = None,
    case_id: Optional[str] = None,
    finding_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    worker_id: Optional[str] = None,
    attempt: int = 1,
    input_packet_path: Optional[str] = None,
    input_packet_hash: Optional[str] = None,
    input_packet_generation: Optional[int] = None,
    checkpoint_path: Optional[str] = None,
    checkpoint_generation: Optional[int] = None,
    dispatch_log_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Pre-dispatch identity with PENDING agent id (V9-compatible + V10 fields)."""
    now = _utc_now()
    obj: Dict[str, Any] = {
        "IDENTITY_RECORD_VERSION": IDENTITY_RECORD_VERSION,
        "ORCHESTRATION_ID": orchestration_id,
        "CASE_ID": case_id,
        "FINDING_ID": finding_id,
        "BRANCH_ID": branch_id,  # explicit null allowed
        "WORKER_ID": worker_id,
        "WORKER_EXECUTION_ID": worker_execution_id,
        "ATTEMPT": attempt,
        "CURSOR_AGENT_ID": PENDING,
        "CURSOR_AGENT_ID_SOURCE": None,
        "CURSOR_AGENT_ID_RECONCILIATION": "PENDING",
        "DISPATCH_RECORD_ID": dispatch_record_id,
        "DISPATCH_LOG_PATH": dispatch_log_path
        or str(Path(case_root) / "team" / "DISPATCH.jsonl"),
        "DISPATCH_RECORD_HASH": None,
        "INPUT_PACKET_ID": input_packet_id,
        "INPUT_PACKET_PATH": input_packet_path,
        "INPUT_PACKET_HASH": input_packet_hash,
        "INPUT_PACKET_GENERATION": input_packet_generation,
        "OUTPUT_PACKET_ID": None,
        "OUTPUT_PACKET_PATH": None,
        "OUTPUT_PACKET_HASH": None,
        "OUTPUT_PACKET_GENERATION": None,
        "CHECKPOINT_PATH": checkpoint_path
        or str(Path(case_root) / "team" / "CHECKPOINT.json"),
        "CHECKPOINT_GENERATION": checkpoint_generation,
        "STARTED_AT": now,
        "FINISHED_AT": None,
        "IDENTITY_STATUS": STATUS_PENDING_DISPATCH,
        "CREATED_AT": now,
    }
    write_identity_record(case_root, obj)
    return load_identity_record(identity_path(case_root, worker_execution_id))


def finalize_identity(
    case_root: Path,
    *,
    worker_execution_id: str,
    cursor_agent_id: str,
    output_packet_id: str,
    dispatch_record_id: Optional[str] = None,
    orchestration_id: Optional[str] = None,
    case_id: Optional[str] = None,
    finding_id: Optional[str] = None,
    branch_id: Optional[Any] = None,
    worker_id: Optional[str] = None,
    attempt: Optional[int] = None,
    dispatch_log_path: Optional[str] = None,
    dispatch_record_hash: Optional[str] = None,
    input_packet_id: Optional[str] = None,
    input_packet_path: Optional[str] = None,
    input_packet_hash: Optional[str] = None,
    input_packet_generation: Optional[int] = None,
    output_packet_path: Optional[str] = None,
    output_packet_hash: Optional[str] = None,
    output_packet_generation: Optional[int] = None,
    checkpoint_path: Optional[str] = None,
    checkpoint_generation: Optional[int] = None,
    started_at: Optional[str] = None,
    finished_at: Optional[str] = None,
    identity_status: str = STATUS_OUTPUT_RECEIVED,
) -> Dict[str, Any]:
    """Bind real Cursor agent id after Task dispatch/finalize (V9 + V10)."""
    if _is_placeholder_agent(cursor_agent_id):
        raise ExecutionIdentityError(
            "BLOCKED_CURSOR_AGENT_ID_PLACEHOLDER",
            str(cursor_agent_id),
        )
    if not output_packet_id:
        raise ExecutionIdentityError(
            "BLOCKED_EXECUTION_IDENTITY_NOT_FINALIZED",
            "OUTPUT_PACKET_ID required",
        )
    path = identity_path(case_root, worker_execution_id)
    if path.exists():
        obj = load_identity_record(path)
    else:
        obj = {
            "IDENTITY_RECORD_VERSION": IDENTITY_RECORD_VERSION,
            "WORKER_EXECUTION_ID": worker_execution_id,
            "INPUT_PACKET_ID": input_packet_id,
            "BRANCH_ID": None,
            "IDENTITY_STATUS": STATUS_PENDING_DISPATCH,
            "STARTED_AT": _utc_now(),
        }
    now = _utc_now()
    obj.update(
        {
            "CURSOR_AGENT_ID": cursor_agent_id,
            "CURSOR_AGENT_ID_SOURCE": "DISPATCH_RUNTIME",
            "CURSOR_AGENT_ID_RECONCILIATION": "MATCH",
            "OUTPUT_PACKET_ID": output_packet_id,
            "FINALIZED_AT": now,
            "FINISHED_AT": finished_at or now,
            "IDENTITY_STATUS": identity_status,
        }
    )
    if dispatch_record_id:
        obj["DISPATCH_RECORD_ID"] = dispatch_record_id
    if orchestration_id is not None:
        obj["ORCHESTRATION_ID"] = orchestration_id
    if case_id is not None:
        obj["CASE_ID"] = case_id
    if finding_id is not None:
        obj["FINDING_ID"] = finding_id
    if branch_id is not None or "BRANCH_ID" not in obj:
        obj["BRANCH_ID"] = branch_id
    if worker_id is not None:
        obj["WORKER_ID"] = worker_id
    if attempt is not None:
        obj["ATTEMPT"] = attempt
    if dispatch_log_path is not None:
        obj["DISPATCH_LOG_PATH"] = dispatch_log_path
    if dispatch_record_hash is not None:
        obj["DISPATCH_RECORD_HASH"] = dispatch_record_hash
    if input_packet_id is not None:
        obj["INPUT_PACKET_ID"] = input_packet_id
    if input_packet_path is not None:
        obj["INPUT_PACKET_PATH"] = input_packet_path
    if input_packet_hash is not None:
        obj["INPUT_PACKET_HASH"] = input_packet_hash
    if input_packet_generation is not None:
        obj["INPUT_PACKET_GENERATION"] = input_packet_generation
    if output_packet_path is not None:
        obj["OUTPUT_PACKET_PATH"] = output_packet_path
    if output_packet_hash is not None:
        obj["OUTPUT_PACKET_HASH"] = output_packet_hash
    if output_packet_generation is not None:
        obj["OUTPUT_PACKET_GENERATION"] = output_packet_generation
    if checkpoint_path is not None:
        obj["CHECKPOINT_PATH"] = checkpoint_path
    if checkpoint_generation is not None:
        obj["CHECKPOINT_GENERATION"] = checkpoint_generation
    if started_at is not None:
        obj["STARTED_AT"] = started_at
    write_identity_record(case_root, obj)
    return load_identity_record(path)


def mark_identity_validated(case_root: Path, worker_execution_id: str) -> Dict[str, Any]:
    """Set IDENTITY_STATUS=VALIDATED after successful authoritative validation."""
    path = identity_path(case_root, worker_execution_id)
    obj = load_identity_record(path)
    obj["IDENTITY_STATUS"] = STATUS_VALIDATED
    write_identity_record(case_root, obj)
    return load_identity_record(path)


def mark_identity_rejected(
    case_root: Path, worker_execution_id: str, reason_code: str
) -> Dict[str, Any]:
    """Mark identity REJECTED with reason (does not authorize advance)."""
    path = identity_path(case_root, worker_execution_id)
    if path.exists():
        obj = load_identity_record(path)
    else:
        obj = {
            "IDENTITY_RECORD_VERSION": IDENTITY_RECORD_VERSION,
            "WORKER_EXECUTION_ID": worker_execution_id,
            "BRANCH_ID": None,
            "STARTED_AT": _utc_now(),
        }
    obj["IDENTITY_STATUS"] = STATUS_REJECTED
    obj["REJECT_REASON"] = reason_code
    obj["FINISHED_AT"] = _utc_now()
    write_identity_record(case_root, obj)
    return load_identity_record(path)


def validate_identity(case_root: Path, worker_execution_id: str) -> Dict[str, Any]:
    """V9-compatible gate: reject unresolved / missing output binding.

    Still insufficient alone for orchestration advance — use
    ``validate_execution_identity`` for authoritative reconciliation.
    """
    path = identity_path(case_root, worker_execution_id)
    if not path.exists():
        raise ExecutionIdentityError("BLOCKED_EXECUTION_IDENTITY_MISSING", worker_execution_id)
    obj = load_identity_record(path)
    if obj.get("CURSOR_AGENT_ID") in {None, PENDING} or _is_placeholder_agent(
        str(obj.get("CURSOR_AGENT_ID"))
    ):
        raise ExecutionIdentityError(
            "BLOCKED_CURSOR_AGENT_ID_UNRESOLVED",
            str(obj.get("CURSOR_AGENT_ID")),
        )
    if obj.get("CURSOR_AGENT_ID_RECONCILIATION") != "MATCH":
        raise ExecutionIdentityError("BLOCKED_CURSOR_AGENT_ID_RECONCILIATION", str(obj))
    if obj.get("CURSOR_AGENT_ID_SOURCE") != "DISPATCH_RUNTIME":
        raise ExecutionIdentityError(
            "BLOCKED_CURSOR_AGENT_ID_SOURCE",
            str(obj.get("CURSOR_AGENT_ID_SOURCE")),
        )
    # V10: missing output binding is not a finalized identity (ID_MISSING_OUTPUT)
    if not obj.get("OUTPUT_PACKET_ID"):
        raise ExecutionIdentityError(
            "BLOCKED_EXECUTION_IDENTITY_NOT_FINALIZED",
            "OUTPUT_PACKET_ID missing",
        )
    return obj


def _fail(
    code: str,
    *,
    wex: Optional[str] = None,
    agent: Optional[str] = None,
    mismatches: Optional[List[str]] = None,
    stale: bool = False,
    dispatch_rec: str = "FAIL",
    input_rec: str = "FAIL",
    output_rec: str = "FAIL",
    checkpoint_rec: str = "FAIL",
) -> ExecutionIdentityValidationResult:
    return ExecutionIdentityValidationResult(
        STATUS="BLOCKED_EXECUTION_IDENTITY_NOT_FINALIZED"
        if code
        in {
            "CURSOR_AGENT_ID_NOT_FINALIZED",
            "IDENTITY_PATH_NON_CANONICAL",
            "IDENTITY_RECORD_HASH_MISMATCH",
        }
        or code.startswith("CURSOR_AGENT")
        else "FAIL",
        VALID=False,
        REASON_CODE=code,
        WORKER_EXECUTION_ID=wex,
        CURSOR_AGENT_ID=agent,
        DISPATCH_RECONCILIATION=dispatch_rec,
        INPUT_PACKET_RECONCILIATION=input_rec,
        OUTPUT_PACKET_RECONCILIATION=output_rec,
        CHECKPOINT_RECONCILIATION=checkpoint_rec,
        STALE_OR_SUPERSEDED=stale,
        MISMATCHES=list(mismatches or [code]),
    )


def validate_execution_identity(
    *,
    identity_path: Path,
    dispatch_log_path: Path,
    input_packet_path: Path,
    output_packet_path: Path,
    checkpoint_path: Path,
    expected_orchestration_id: str,
    expected_case_id: str,
    expected_finding_id: str,
    expected_worker_execution_id: str,
    expected_branch_id: Any = None,
    case_root: Optional[Path] = None,
    require_validated_status: bool = False,
) -> ExecutionIdentityValidationResult:
    """Authoritative identity validation against dispatch + packets + checkpoint.

    A worker terminal output may advance orchestration only when VALID=True
    (and typically IDENTITY_STATUS becomes VALIDATED after this gate).
    """
    id_path = Path(identity_path)
    disp_path = Path(dispatch_log_path)
    in_path = Path(input_packet_path)
    out_path = Path(output_packet_path)
    cp_path = Path(checkpoint_path)
    root = Path(case_root) if case_root else id_path.parents[2]  # .../team/executions → case

    if not id_path.exists():
        return _fail("DISPATCH_RECORD_MISSING", wex=expected_worker_execution_id, mismatches=["IDENTITY_MISSING"])

    if not is_canonical_identity_path(root, id_path, expected_worker_execution_id):
        return _fail(
            "IDENTITY_PATH_NON_CANONICAL",
            wex=expected_worker_execution_id,
            mismatches=[f"path={id_path} expected={identity_path(root, expected_worker_execution_id)}"],
        )

    try:
        record = load_identity_record(id_path)
    except (OSError, json.JSONDecodeError) as exc:
        return _fail("IDENTITY_RECORD_HASH_MISMATCH", wex=expected_worker_execution_id, mismatches=[str(exc)])

    wex = str(record.get("WORKER_EXECUTION_ID") or "")
    agent = record.get("CURSOR_AGENT_ID")

    # Path WEX must match record WEX (copied identity to another WEX path)
    if wex != expected_worker_execution_id:
        return _fail(
            "WORKER_EXECUTION_ID_MISMATCH",
            wex=wex,
            agent=str(agent) if agent else None,
            mismatches=["identity.WORKER_EXECUTION_ID != expected"],
        )
    # File slug must match record (copy of another identity into this WEX path)
    if wex_slug(wex) != id_path.name.replace(".identity.json", ""):
        return _fail(
            "IDENTITY_PATH_NON_CANONICAL",
            wex=wex,
            agent=str(agent) if agent else None,
            mismatches=["slug/path WEX mismatch"],
        )

    expected_hash = compute_identity_record_hash(record)
    if record.get("IDENTITY_RECORD_HASH") != expected_hash:
        return _fail(
            "IDENTITY_RECORD_HASH_MISMATCH",
            wex=wex,
            agent=str(agent) if agent else None,
            mismatches=["IDENTITY_RECORD_HASH"],
        )
    if not verify_identity_host_signature(root, record):
        return _fail(
            "IDENTITY_RECORD_HASH_MISMATCH",
            wex=wex,
            agent=str(agent) if agent else None,
            mismatches=["HOST_SIGNATURE"],
        )

    if _is_placeholder_agent(str(agent) if agent is not None else None):
        return _fail(
            "CURSOR_AGENT_ID_NOT_FINALIZED",
            wex=wex,
            agent=str(agent) if agent else None,
            mismatches=["CURSOR_AGENT_ID pending/placeholder"],
        )

    if not record.get("OUTPUT_PACKET_ID"):
        return _fail(
            "OUTPUT_PACKET_MISMATCH",
            wex=wex,
            agent=str(agent),
            mismatches=["OUTPUT_PACKET_ID missing"],
            output_rec="FAIL_MISSING",
        )

    mismatches: List[str] = []

    if record.get("ORCHESTRATION_ID") != expected_orchestration_id:
        mismatches.append("ORCHESTRATION_ID")
        return _fail(
            "ORCHESTRATION_ID_MISMATCH",
            wex=wex,
            agent=str(agent),
            mismatches=mismatches,
        )
    if record.get("CASE_ID") != expected_case_id:
        return _fail("CASE_ID_MISMATCH", wex=wex, agent=str(agent), mismatches=["CASE_ID"])
    if record.get("FINDING_ID") != expected_finding_id:
        return _fail("FINDING_ID_MISMATCH", wex=wex, agent=str(agent), mismatches=["FINDING_ID"])
    # BRANCH_ID: explicit null vs value — both sides must agree
    if record.get("BRANCH_ID") != expected_branch_id:
        return _fail("BRANCH_ID_MISMATCH", wex=wex, agent=str(agent), mismatches=["BRANCH_ID"])

    # --- packets ---
    if not in_path.exists() or not out_path.exists():
        return _fail(
            "INPUT_PACKET_MISMATCH" if not in_path.exists() else "OUTPUT_PACKET_MISMATCH",
            wex=wex,
            agent=str(agent),
            mismatches=["packet file missing"],
        )
    in_pkt = json.loads(in_path.read_text(encoding="utf-8"))
    out_pkt = json.loads(out_path.read_text(encoding="utf-8"))
    in_hash = _sha256_file(in_path)
    out_hash = _sha256_file(out_path)

    if in_pkt.get("WORKER_EXECUTION_ID") != expected_worker_execution_id:
        return _fail(
            "WORKER_EXECUTION_ID_MISMATCH",
            wex=wex,
            agent=str(agent),
            mismatches=["input.WORKER_EXECUTION_ID"],
            input_rec="FAIL",
        )
    if out_pkt.get("WORKER_EXECUTION_ID") != expected_worker_execution_id:
        return _fail(
            "WORKER_EXECUTION_ID_MISMATCH",
            wex=wex,
            agent=str(agent),
            mismatches=["output.WORKER_EXECUTION_ID"],
            output_rec="FAIL",
        )

    if record.get("INPUT_PACKET_ID") != in_pkt.get("PACKET_ID"):
        return _fail(
            "INPUT_PACKET_MISMATCH",
            wex=wex,
            agent=str(agent),
            mismatches=["INPUT_PACKET_ID"],
            input_rec="FAIL_ID",
        )
    if record.get("INPUT_PACKET_HASH") and record.get("INPUT_PACKET_HASH") != in_hash:
        return _fail(
            "INPUT_PACKET_MISMATCH",
            wex=wex,
            agent=str(agent),
            mismatches=["INPUT_PACKET_HASH"],
            input_rec="FAIL_HASH",
        )
    if record.get("OUTPUT_PACKET_ID") != out_pkt.get("PACKET_ID"):
        return _fail(
            "OUTPUT_PACKET_MISMATCH",
            wex=wex,
            agent=str(agent),
            mismatches=["OUTPUT_PACKET_ID"],
            output_rec="FAIL_ID",
        )
    if record.get("OUTPUT_PACKET_HASH") and record.get("OUTPUT_PACKET_HASH") != out_hash:
        return _fail(
            "OUTPUT_PACKET_MISMATCH",
            wex=wex,
            agent=str(agent),
            mismatches=["OUTPUT_PACKET_HASH"],
            output_rec="FAIL_HASH",
        )

    parent = out_pkt.get("PARENT_PACKET_ID")
    if parent != in_pkt.get("PACKET_ID"):
        return _fail(
            "PACKET_PARENT_MISMATCH",
            wex=wex,
            agent=str(agent),
            mismatches=[f"parent={parent} input={in_pkt.get('PACKET_ID')}"],
            input_rec="PASS",
            output_rec="FAIL_PARENT",
        )

    # Cross-ids on packets
    for label, pkt in (("input", in_pkt), ("output", out_pkt)):
        if pkt.get("ORCHESTRATION_ID") != expected_orchestration_id:
            return _fail(
                "ORCHESTRATION_ID_MISMATCH",
                wex=wex,
                agent=str(agent),
                mismatches=[f"{label}.ORCHESTRATION_ID"],
            )
        if pkt.get("CASE_ID") != expected_case_id:
            return _fail(
                "CASE_ID_MISMATCH",
                wex=wex,
                agent=str(agent),
                mismatches=[f"{label}.CASE_ID"],
            )
        if pkt.get("FINDING_ID") != expected_finding_id:
            return _fail(
                "FINDING_ID_MISMATCH",
                wex=wex,
                agent=str(agent),
                mismatches=[f"{label}.FINDING_ID"],
            )

    # --- dispatch ---
    disp = find_dispatch_record(
        disp_path,
        worker_execution_id=expected_worker_execution_id,
        dispatch_record_id=str(record.get("DISPATCH_RECORD_ID") or "") or None,
    )
    if disp is None:
        # try without record id filter
        disp = find_dispatch_record(disp_path, worker_execution_id=expected_worker_execution_id)
    if disp is None:
        return _fail(
            "DISPATCH_RECORD_MISSING",
            wex=wex,
            agent=str(agent),
            mismatches=["dispatch missing"],
            dispatch_rec="MISSING",
            input_rec="PASS",
            output_rec="PASS",
        )

    if disp.get("WORKER_EXECUTION_ID") != expected_worker_execution_id:
        return _fail(
            "DISPATCH_RECORD_MISMATCH",
            wex=wex,
            agent=str(agent),
            mismatches=["dispatch.WORKER_EXECUTION_ID"],
            dispatch_rec="FAIL",
            input_rec="PASS",
            output_rec="PASS",
        )
    if record.get("DISPATCH_RECORD_ID") and disp.get("DISPATCH_RECORD_ID") != record.get(
        "DISPATCH_RECORD_ID"
    ):
        return _fail(
            "DISPATCH_RECORD_MISMATCH",
            wex=wex,
            agent=str(agent),
            mismatches=["DISPATCH_RECORD_ID"],
            dispatch_rec="FAIL_ID",
            input_rec="PASS",
            output_rec="PASS",
        )

    disp_hash = hash_dispatch_record(disp)
    if record.get("DISPATCH_RECORD_HASH") and record.get("DISPATCH_RECORD_HASH") != disp_hash:
        return _fail(
            "DISPATCH_RECORD_MISMATCH",
            wex=wex,
            agent=str(agent),
            mismatches=["DISPATCH_RECORD_HASH"],
            dispatch_rec="FAIL_HASH",
            input_rec="PASS",
            output_rec="PASS",
        )

    runtime_agent = disp.get("CURSOR_AGENT_ID")
    if _is_placeholder_agent(str(runtime_agent) if runtime_agent is not None else None):
        return _fail(
            "CURSOR_AGENT_ID_NOT_FINALIZED",
            wex=wex,
            agent=str(agent),
            mismatches=["dispatch CURSOR_AGENT_ID not finalized"],
            dispatch_rec="FAIL_AGENT",
            input_rec="PASS",
            output_rec="PASS",
        )
    if str(runtime_agent) != str(agent):
        return _fail(
            "CURSOR_AGENT_ID_MISMATCH",
            wex=wex,
            agent=str(agent),
            mismatches=[f"identity={agent} dispatch={runtime_agent}"],
            dispatch_rec="FAIL_AGENT",
            input_rec="PASS",
            output_rec="PASS",
        )

    # --- checkpoint / attempt / generation / supersession ---
    if not cp_path.exists():
        return _fail(
            "GENERATION_MISMATCH",
            wex=wex,
            agent=str(agent),
            mismatches=["checkpoint missing"],
            dispatch_rec="PASS",
            input_rec="PASS",
            output_rec="PASS",
            checkpoint_rec="MISSING",
        )
    checkpoint = json.loads(cp_path.read_text(encoding="utf-8"))

    attempt = record.get("ATTEMPT")
    if attempt is not None and in_pkt.get("ATTEMPT") is not None and attempt != in_pkt.get("ATTEMPT"):
        return _fail(
            "ATTEMPT_MISMATCH",
            wex=wex,
            agent=str(agent),
            mismatches=["identity vs input ATTEMPT"],
            dispatch_rec="PASS",
            input_rec="PASS",
            output_rec="PASS",
            checkpoint_rec="FAIL_ATTEMPT",
        )
    if attempt is not None and out_pkt.get("ATTEMPT") is not None and attempt != out_pkt.get("ATTEMPT"):
        return _fail(
            "ATTEMPT_MISMATCH",
            wex=wex,
            agent=str(agent),
            mismatches=["identity vs output ATTEMPT"],
            dispatch_rec="PASS",
            input_rec="PASS",
            output_rec="PASS",
            checkpoint_rec="FAIL_ATTEMPT",
        )
    if disp.get("ATTEMPT") is not None and attempt is not None and disp.get("ATTEMPT") != attempt:
        return _fail(
            "ATTEMPT_MISMATCH",
            wex=wex,
            agent=str(agent),
            mismatches=["identity vs dispatch ATTEMPT"],
            dispatch_rec="FAIL_ATTEMPT",
            input_rec="PASS",
            output_rec="PASS",
            checkpoint_rec="FAIL_ATTEMPT",
        )

    # Generation agreement
    id_cpg = record.get("CHECKPOINT_GENERATION")
    id_ipg = record.get("INPUT_PACKET_GENERATION")
    id_opg = record.get("OUTPUT_PACKET_GENERATION")
    if id_ipg is not None and in_pkt.get("PACKET_GENERATION") is not None:
        if id_ipg != in_pkt.get("PACKET_GENERATION"):
            return _fail(
                "GENERATION_MISMATCH",
                wex=wex,
                agent=str(agent),
                mismatches=["INPUT_PACKET_GENERATION"],
                dispatch_rec="PASS",
                input_rec="FAIL_GEN",
                output_rec="PASS",
                checkpoint_rec="FAIL_GEN",
            )
    if id_opg is not None and out_pkt.get("PACKET_GENERATION") is not None:
        if id_opg != out_pkt.get("PACKET_GENERATION"):
            return _fail(
                "GENERATION_MISMATCH",
                wex=wex,
                agent=str(agent),
                mismatches=["OUTPUT_PACKET_GENERATION"],
                dispatch_rec="PASS",
                input_rec="PASS",
                output_rec="FAIL_GEN",
                checkpoint_rec="FAIL_GEN",
            )
    if id_cpg is not None:
        # During finalize ACTIVE may still be RUNNING with matching generation;
        # after advance CHECKPOINT_GENERATION increments — accept either active
        # match or LAST_ACCEPTED_WEX match for post-finalize validation.
        active_wex = checkpoint.get("ACTIVE_WORKER_EXECUTION_ID")
        last_accepted = checkpoint.get("LAST_ACCEPTED_WEX")
        active_status = checkpoint.get("ACTIVE_STATUS")
        cp_gen = checkpoint.get("ACTIVE_CHECKPOINT_GENERATION")
        if cp_gen is None:
            cp_gen = checkpoint.get("CHECKPOINT_GENERATION")

        superseded = False
        if active_status == "RUNNING" and active_wex and active_wex != expected_worker_execution_id:
            superseded = True
        if (
            active_status in {"IDLE", "SUPERSEDED"}
            and last_accepted
            and last_accepted != expected_worker_execution_id
            and active_wex != expected_worker_execution_id
        ):
            # Late output from older WEX after another hop accepted
            if last_accepted != expected_worker_execution_id:
                superseded = True
        # Explicit superseded list
        superseded_list = checkpoint.get("SUPERSEDED_WEX") or []
        if expected_worker_execution_id in superseded_list:
            superseded = True

        if superseded:
            return _fail(
                "IDENTITY_SUPERSEDED",
                wex=wex,
                agent=str(agent),
                mismatches=["WEX superseded"],
                stale=True,
                dispatch_rec="PASS",
                input_rec="PASS",
                output_rec="PASS",
                checkpoint_rec="SUPERSEDED",
            )

        # Retry: identity attempt must match active attempt when RUNNING
        if active_status == "RUNNING" and active_wex == expected_worker_execution_id:
            if checkpoint.get("ACTIVE_ATTEMPT") is not None and attempt is not None:
                if checkpoint.get("ACTIVE_ATTEMPT") != attempt:
                    return _fail(
                        "ATTEMPT_MISMATCH",
                        wex=wex,
                        agent=str(agent),
                        mismatches=["checkpoint ACTIVE_ATTEMPT"],
                        stale=True,
                        dispatch_rec="PASS",
                        input_rec="PASS",
                        output_rec="PASS",
                        checkpoint_rec="FAIL_ATTEMPT",
                    )
            active_cpg = checkpoint.get("ACTIVE_CHECKPOINT_GENERATION")
            if active_cpg is not None and id_cpg != active_cpg:
                return _fail(
                    "GENERATION_MISMATCH",
                    wex=wex,
                    agent=str(agent),
                    mismatches=["CHECKPOINT_GENERATION"],
                    dispatch_rec="PASS",
                    input_rec="PASS",
                    output_rec="PASS",
                    checkpoint_rec="FAIL_GEN",
                )
            if (
                active_cpg is None
                and checkpoint.get("CHECKPOINT_GENERATION") is not None
                and id_cpg != checkpoint.get("CHECKPOINT_GENERATION")
            ):
                return _fail(
                    "GENERATION_MISMATCH",
                    wex=wex,
                    agent=str(agent),
                    mismatches=["CHECKPOINT_GENERATION"],
                    dispatch_rec="PASS",
                    input_rec="PASS",
                    output_rec="PASS",
                    checkpoint_rec="FAIL_GEN",
                )
        elif last_accepted == expected_worker_execution_id:
            # Post-accept: identity cpg is the generation at accept time
            pass
        elif active_wex and active_wex != expected_worker_execution_id:
            return _fail(
                "IDENTITY_STALE",
                wex=wex,
                agent=str(agent),
                mismatches=["not active WEX"],
                stale=True,
                dispatch_rec="PASS",
                input_rec="PASS",
                output_rec="PASS",
                checkpoint_rec="STALE",
            )

        # Copied identity from previous retry: attempt below active/next
        if (
            active_status == "RUNNING"
            and active_wex
            and active_wex != expected_worker_execution_id
            and attempt is not None
            and checkpoint.get("ACTIVE_ATTEMPT") is not None
            and attempt < checkpoint.get("ACTIVE_ATTEMPT")
        ):
            return _fail(
                "IDENTITY_SUPERSEDED",
                wex=wex,
                agent=str(agent),
                mismatches=["prior retry identity"],
                stale=True,
                dispatch_rec="PASS",
                input_rec="PASS",
                output_rec="PASS",
                checkpoint_rec="SUPERSEDED",
            )

    if require_validated_status and record.get("IDENTITY_STATUS") != STATUS_VALIDATED:
        # During gate we allow OUTPUT_RECEIVED then promote; this flag for post-checks
        if record.get("IDENTITY_STATUS") not in {STATUS_OUTPUT_RECEIVED, STATUS_VALIDATED}:
            return _fail(
                "CURSOR_AGENT_ID_NOT_FINALIZED",
                wex=wex,
                agent=str(agent),
                mismatches=[f"IDENTITY_STATUS={record.get('IDENTITY_STATUS')}"],
                dispatch_rec="PASS",
                input_rec="PASS",
                output_rec="PASS",
                checkpoint_rec="PASS",
            )

    return ExecutionIdentityValidationResult(
        STATUS="PASS",
        VALID=True,
        REASON_CODE="OK",
        WORKER_EXECUTION_ID=wex,
        CURSOR_AGENT_ID=str(agent),
        DISPATCH_RECONCILIATION="PASS",
        INPUT_PACKET_RECONCILIATION="PASS",
        OUTPUT_PACKET_RECONCILIATION="PASS",
        CHECKPOINT_RECONCILIATION="PASS",
        STALE_OR_SUPERSEDED=False,
        MISMATCHES=[],
    )


def build_identity_from_finalize(
    *,
    case_root: Path,
    intent: Dict[str, Any],
    actual_cursor_agent_id: str,
    in_path: Path,
    out_path: Path,
    in_pkt: Dict[str, Any],
    out_pkt: Dict[str, Any],
    dispatch_record: Dict[str, Any],
    checkpoint_path: Path,
    branch_id: Any = None,
) -> Dict[str, Any]:
    """Build + seal identity record from live finalize context (pre-checkpoint)."""
    wex = intent["WORKER_EXECUTION_ID"]
    attempt = int(intent["ATTEMPT"])
    disp_id = dispatch_record.get("DISPATCH_RECORD_ID") or dispatch_record_id_for(wex, attempt)
    disp_hash = hash_dispatch_record(dispatch_record)
    in_hash = _sha256_file(in_path)
    out_hash = _sha256_file(out_path)
    record = {
        "IDENTITY_RECORD_VERSION": IDENTITY_RECORD_VERSION,
        "ORCHESTRATION_ID": intent["ORCHESTRATION_ID"],
        "CASE_ID": intent["CASE_ID"],
        "FINDING_ID": intent["FINDING_ID"],
        "BRANCH_ID": branch_id if branch_id is not None else intent.get("BRANCH_ID"),
        "WORKER_ID": intent["WORKER_ID"],
        "WORKER_EXECUTION_ID": wex,
        "ATTEMPT": attempt,
        "CURSOR_AGENT_ID": actual_cursor_agent_id,
        "CURSOR_AGENT_ID_SOURCE": "DISPATCH_RUNTIME",
        "CURSOR_AGENT_ID_RECONCILIATION": "MATCH",
        "DISPATCH_RECORD_ID": disp_id,
        "DISPATCH_LOG_PATH": str(Path(case_root) / "team" / "DISPATCH.jsonl"),
        "DISPATCH_RECORD_HASH": disp_hash,
        "INPUT_PACKET_ID": in_pkt.get("PACKET_ID"),
        "INPUT_PACKET_PATH": str(in_path),
        "INPUT_PACKET_HASH": in_hash,
        "INPUT_PACKET_GENERATION": in_pkt.get("PACKET_GENERATION"),
        "OUTPUT_PACKET_ID": out_pkt.get("PACKET_ID"),
        "OUTPUT_PACKET_PATH": str(out_path),
        "OUTPUT_PACKET_HASH": out_hash,
        "OUTPUT_PACKET_GENERATION": out_pkt.get("PACKET_GENERATION"),
        "CHECKPOINT_PATH": str(checkpoint_path),
        "CHECKPOINT_GENERATION": intent.get("CHECKPOINT_GENERATION"),
        "STARTED_AT": intent.get("TASK_STARTED_AT") or intent.get("PREPARED_AT") or _utc_now(),
        "FINISHED_AT": _utc_now(),
        "IDENTITY_STATUS": STATUS_OUTPUT_RECEIVED,
        "FINALIZED_AT": _utc_now(),
    }
    write_identity_record(case_root, record)
    return load_identity_record(identity_path(case_root, wex))


def gate_execution_identity_for_advance(
    *,
    case_root: Path,
    worker_execution_id: str,
    expected_orchestration_id: str,
    expected_case_id: str,
    expected_finding_id: str,
    input_packet_path: Path,
    output_packet_path: Path,
    checkpoint_path: Path,
    dispatch_log_path: Optional[Path] = None,
    expected_branch_id: Any = None,
) -> ExecutionIdentityValidationResult:
    """Orchestrator gate: require EXECUTION_IDENTITY_VALIDATION=PASS."""
    return validate_execution_identity(
        identity_path=identity_path(case_root, worker_execution_id),
        dispatch_log_path=dispatch_log_path
        or (Path(case_root) / "team" / "DISPATCH.jsonl"),
        input_packet_path=input_packet_path,
        output_packet_path=output_packet_path,
        checkpoint_path=checkpoint_path,
        expected_orchestration_id=expected_orchestration_id,
        expected_case_id=expected_case_id,
        expected_finding_id=expected_finding_id,
        expected_worker_execution_id=worker_execution_id,
        expected_branch_id=expected_branch_id,
        case_root=Path(case_root),
    )
