# -*- coding: utf-8 -*-
"""Append-only retry authorization registry (BF-ICT-SR-001).

Receipt files are immutable issuance evidence. Current status is determined
ONLY by the latest valid event in team/retries/RETRY-AUTH-REGISTRY.jsonl.

Host signing secret lives in team/retries/.host_retry_authority and must never
appear in packets, DISPATCH, route trace, or reports.

LIVE_RUNTIME_AUTHORITY: runtime/retry_auth.py (registry + receipt verify)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = "1"
REGISTRY_FILENAME = "RETRY-AUTH-REGISTRY.jsonl"
HOST_SECRET_FILENAME = ".host_retry_authority"
RECEIPT_TTL_SECONDS = 7200

EVENT_ISSUED = "RETRY_AUTH_ISSUED"
EVENT_RESERVED = "RETRY_AUTH_RESERVED"
EVENT_CONSUMED = "RETRY_AUTH_CONSUMED"
EVENT_EXPIRED = "RETRY_AUTH_EXPIRED"
EVENT_REJECTED = "RETRY_AUTH_REJECTED"

STATUS_ISSUED = "ISSUED"
STATUS_RESERVED = "RESERVED"
STATUS_CONSUMED = "CONSUMED"
STATUS_EXPIRED = "EXPIRED"

ALLOWED_TRANSITIONS = {
    None: {STATUS_ISSUED},
    STATUS_ISSUED: {STATUS_RESERVED, STATUS_EXPIRED},
    STATUS_RESERVED: {STATUS_CONSUMED, STATUS_EXPIRED},
    STATUS_CONSUMED: set(),
    STATUS_EXPIRED: set(),
}

IMMUTABLE_RECEIPT_FIELDS = (
    "SCHEMA_VERSION",
    "RETRY_AUTHORIZATION_ID",
    "NONCE",
    "ORCHESTRATION_ID",
    "CASE_ID",
    "FINDING_ID",
    "WORKER_ID",
    "PREVIOUS_WORKER_EXECUTION_ID",
    "PREVIOUS_TERMINAL_STATUS",
    "PREVIOUS_ATTEMPT",
    "PREVIOUS_PACKET_GENERATION",
    "PREVIOUS_CHECKPOINT_GENERATION",
    "PREVIOUS_INPUT_RAW_SHA256",
    "PREVIOUS_INPUT_CANONICAL_SHA256",
    "NEXT_ATTEMPT",
    "NEXT_PACKET_GENERATION",
    "NEXT_CHECKPOINT_GENERATION",
    "ISSUED_AT",
    "EXPIRES_AT",
    "CANONICAL_RECEIPT_PATH",
)


class RetryAuthError(Exception):
    """Retry authorization protocol rejection."""

    def __init__(self, code: str, detail: str = "", payload: Optional[Dict[str, Any]] = None) -> None:
        self.code = code
        self.detail = detail
        self.payload = payload or {}
        super().__init__(f"{code}: {detail}" if detail else code)


def retries_dir(case_root: Path) -> Path:
    return Path(case_root) / "team" / "retries"


def registry_path(case_root: Path) -> Path:
    return retries_dir(case_root) / REGISTRY_FILENAME


def host_secret_path(case_root: Path) -> Path:
    return retries_dir(case_root) / HOST_SECRET_FILENAME


def canonical_receipt_path(case_root: Path, auth_id: str) -> Path:
    """Derive canonical receipt path from authorization identity (no arbitrary paths)."""
    if not auth_id or "/" in auth_id or "\\" in auth_id or ".." in auth_id:
        raise RetryAuthError("BLOCKED_RETRY_AUTHORIZATION_NON_CANONICAL_PATH", "bad_auth_id")
    return retries_dir(case_root) / f"{auth_id}.json"


def _canonical_bytes(obj: Dict[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_obj(obj: Dict[str, Any]) -> str:
    return _sha256_bytes(_canonical_bytes(obj))


def _receipt_raw_hash(receipt: Dict[str, Any]) -> str:
    """Hash of receipt excluding RECEIPT_RAW_SHA256 (avoids self-referential bytes)."""
    payload = {k: v for k, v in receipt.items() if k != "RECEIPT_RAW_SHA256"}
    return _sha256_obj(payload)


def ensure_host_secret(case_root: Path) -> str:
    """Load or mint host-only retry authority secret (never log / export)."""
    path = host_secret_path(case_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    secret = secrets.token_hex(32)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(str(path), flags)
    except FileExistsError:
        return path.read_text(encoding="utf-8").strip()
    try:
        os.write(fd, (secret + "\n").encode("utf-8"))
    finally:
        os.close(fd)
    return secret


def _sign(secret: str, material: str) -> str:
    return hmac.new(secret.encode("utf-8"), material.encode("utf-8"), hashlib.sha256).hexdigest()


def _signing_material(receipt: Dict[str, Any]) -> str:
    payload = {
        k: receipt[k]
        for k in IMMUTABLE_RECEIPT_FIELDS
        if k in receipt
    }
    return _canonical_bytes(payload).decode("utf-8")


def _sign_event(secret: str, event: Dict[str, Any]) -> str:
    payload = {k: v for k, v in event.items() if k != "HOST_EVENT_SIGNATURE"}
    return _sign(secret, _canonical_bytes(payload).decode("utf-8"))


def load_registry_events(case_root: Path) -> List[Dict[str, Any]]:
    path = registry_path(case_root)
    if not path.exists():
        return []
    secret = ensure_host_secret(case_root)
    events: List[Dict[str, Any]] = []
    seen_seq: set = set()
    seen_auth_issued: set = set()
    seen_nonces: set = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RetryAuthError(
                "BLOCKED_RETRY_AUTHORIZATION_REGISTRY_INVALID",
                f"json:{exc}",
            ) from exc
        seq = ev.get("SEQUENCE")
        if seq in seen_seq:
            raise RetryAuthError(
                "BLOCKED_RETRY_AUTHORIZATION_REGISTRY_INVALID",
                "duplicate_sequence",
            )
        seen_seq.add(seq)
        expected = _sign_event(secret, ev)
        if not hmac.compare_digest(expected, str(ev.get("HOST_EVENT_SIGNATURE") or "")):
            raise RetryAuthError(
                "BLOCKED_RETRY_AUTHORIZATION_REGISTRY_INVALID",
                "event_signature",
            )
        if ev.get("EVENT_TYPE") == EVENT_ISSUED:
            aid = ev.get("RETRY_AUTHORIZATION_ID")
            nonce = ev.get("NONCE")
            if aid in seen_auth_issued:
                raise RetryAuthError(
                    "BLOCKED_RETRY_AUTHORIZATION_REGISTRY_INVALID",
                    "duplicate_auth_issued",
                )
            if nonce in seen_nonces:
                raise RetryAuthError(
                    "BLOCKED_RETRY_AUTHORIZATION_REGISTRY_INVALID",
                    "duplicate_nonce",
                )
            seen_auth_issued.add(aid)
            seen_nonces.add(nonce)
        events.append(ev)
    # Reconstruct statuses and reject impossible rollbacks in history order
    status_by_auth: Dict[str, Optional[str]] = {}
    for ev in sorted(events, key=lambda e: int(e.get("SEQUENCE") or 0)):
        aid = str(ev.get("RETRY_AUTHORIZATION_ID"))
        frm = status_by_auth.get(aid)
        to = ev.get("TO_STATUS")
        try:
            _validate_transition(frm, str(to))
        except RetryAuthError as exc:
            raise RetryAuthError(
                "BLOCKED_RETRY_AUTHORIZATION_REGISTRY_INVALID",
                f"history:{exc.detail}",
            ) from exc
        # event FROM_STATUS must match reconstructed
        if ev.get("FROM_STATUS") != frm and not (ev.get("FROM_STATUS") is None and frm is None):
            # allow JSON null vs missing
            if ev.get("FROM_STATUS") is not None or frm is not None:
                raise RetryAuthError(
                    "BLOCKED_RETRY_AUTHORIZATION_REGISTRY_INVALID",
                    "from_status_mismatch",
                )
        status_by_auth[aid] = str(to)
    return events


def latest_status_for(case_root: Path, auth_id: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Return (status, latest_event) for authorization id from registry only."""
    events = [e for e in load_registry_events(case_root) if e.get("RETRY_AUTHORIZATION_ID") == auth_id]
    if not events:
        return None, None
    last = max(events, key=lambda e: int(e.get("SEQUENCE") or 0))
    return last.get("TO_STATUS"), last


def _validate_transition(from_status: Optional[str], to_status: str) -> None:
    allowed = ALLOWED_TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise RetryAuthError(
            "BLOCKED_RETRY_AUTHORIZATION_REGISTRY_INVALID",
            f"transition:{from_status}->{to_status}",
            {"FROM_STATUS": from_status, "TO_STATUS": to_status},
        )


def _next_sequence(case_root: Path) -> int:
    events = load_registry_events(case_root)
    if not events:
        return 1
    return max(int(e.get("SEQUENCE") or 0) for e in events) + 1


def _append_event(case_root: Path, event: Dict[str, Any]) -> Dict[str, Any]:
    """Append-only registry write with transition validation and host signature."""
    auth_id = str(event["RETRY_AUTHORIZATION_ID"])
    current, _ = latest_status_for(case_root, auth_id)
    to_status = str(event["TO_STATUS"])
    _validate_transition(current, to_status)
    if event.get("FROM_STATUS") != current:
        event["FROM_STATUS"] = current
    if to_status == STATUS_ISSUED:
        _assert_unique_identity(case_root, auth_id=auth_id, nonce=str(event["NONCE"]))
    path = registry_path(case_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    seq = int(event["SEQUENCE"])
    existing = load_registry_events(case_root)
    if any(int(e.get("SEQUENCE") or -1) == seq for e in existing):
        raise RetryAuthError(
            "BLOCKED_RETRY_AUTHORIZATION_REGISTRY_INVALID",
            "duplicate_sequence_race",
        )
    secret = ensure_host_secret(case_root)
    event.pop("HOST_EVENT_SIGNATURE", None)
    event["HOST_EVENT_SIGNATURE"] = _sign_event(secret, event)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return event


def _assert_unique_identity(case_root: Path, *, auth_id: str, nonce: str) -> None:
    events = load_registry_events(case_root)
    for ev in events:
        if ev.get("EVENT_TYPE") != EVENT_ISSUED:
            continue
        if ev.get("RETRY_AUTHORIZATION_ID") == auth_id:
            raise RetryAuthError(
                "BLOCKED_RETRY_AUTHORIZATION_ID_ALREADY_EXISTS",
                auth_id,
            )
        if ev.get("NONCE") == nonce:
            raise RetryAuthError(
                "BLOCKED_RETRY_NONCE_ALREADY_EXISTS",
                nonce,
            )


def previous_wex_has_active_authorization(case_root: Path, previous_wex: str) -> bool:
    """True if previous WEX already has ISSUED/RESERVED (not fully terminal-consumed for new issue)."""
    events = load_registry_events(case_root)
    # Group by auth id; if any auth for this prev WEX is ISSUED or RESERVED → active
    by_auth: Dict[str, List[Dict[str, Any]]] = {}
    for ev in events:
        if ev.get("PREVIOUS_WORKER_EXECUTION_ID") != previous_wex:
            continue
        aid = str(ev.get("RETRY_AUTHORIZATION_ID"))
        by_auth.setdefault(aid, []).append(ev)
    for aid, evs in by_auth.items():
        last = max(evs, key=lambda e: int(e.get("SEQUENCE") or 0))
        if last.get("TO_STATUS") in {STATUS_ISSUED, STATUS_RESERVED}:
            return True
        # Even CONSUMED means previous WEX already authorized once — cannot re-issue
        if last.get("TO_STATUS") == STATUS_CONSUMED:
            return True
        if last.get("EVENT_TYPE") == EVENT_ISSUED:
            return True
    return bool(by_auth)


def issue_retry_authorization(
    case_root: Path,
    *,
    orchestration_id: str,
    case_id: str,
    finding_id: Optional[str],
    worker_id: str,
    previous_wex: str,
    previous_terminal_status: str,
    previous_attempt: int,
    previous_packet_generation: int,
    previous_checkpoint_generation: int,
    previous_input_raw: str,
    previous_input_canonical: str,
    next_attempt: int,
    next_packet_generation: int,
    next_checkpoint_generation: int,
    ttl_seconds: int = RECEIPT_TTL_SECONDS,
) -> Dict[str, Any]:
    """Create immutable receipt + ISSUED registry event. Returns receipt dict."""
    case_root = Path(case_root)
    if previous_wex_has_active_authorization(case_root, previous_wex):
        raise RetryAuthError(
            "BLOCKED_RETRY_PREVIOUS_EXECUTION_ALREADY_AUTHORIZED",
            previous_wex,
        )

    auth_id = f"RETRYAUTH-{uuid.uuid4().hex[:12]}"
    nonce = secrets.token_hex(16)
    receipt_path = canonical_receipt_path(case_root, auth_id)
    try:
        canonical_rel = str(receipt_path.resolve().relative_to(Path(case_root).resolve()))
    except ValueError:
        canonical_rel = str(receipt_path)

    now = time.time()
    receipt: Dict[str, Any] = {
        "SCHEMA_VERSION": SCHEMA_VERSION,
        "RETRY_AUTHORIZATION_ID": auth_id,
        "NONCE": nonce,
        "ORCHESTRATION_ID": orchestration_id,
        "CASE_ID": case_id,
        "FINDING_ID": finding_id,
        "WORKER_ID": worker_id,
        "PREVIOUS_WORKER_EXECUTION_ID": previous_wex,
        "PREVIOUS_TERMINAL_STATUS": previous_terminal_status,
        "PREVIOUS_ATTEMPT": previous_attempt,
        "PREVIOUS_PACKET_GENERATION": previous_packet_generation,
        "PREVIOUS_CHECKPOINT_GENERATION": previous_checkpoint_generation,
        "PREVIOUS_INPUT_RAW_SHA256": previous_input_raw,
        "PREVIOUS_INPUT_CANONICAL_SHA256": previous_input_canonical,
        "NEXT_ATTEMPT": next_attempt,
        "NEXT_PACKET_GENERATION": next_packet_generation,
        "NEXT_CHECKPOINT_GENERATION": next_checkpoint_generation,
        "ISSUED_AT": now,
        "EXPIRES_AT": now + ttl_seconds,
        "CANONICAL_RECEIPT_PATH": canonical_rel.replace("\\", "/"),
    }
    secret = ensure_host_secret(case_root)
    material = _signing_material(receipt)
    receipt["RECEIPT_CANONICAL_SHA256"] = _sha256_bytes(material.encode("utf-8"))
    receipt["HOST_SIGNATURE"] = _sign(secret, material)
    receipt["RECEIPT_RAW_SHA256"] = _receipt_raw_hash(receipt)

    # Exclusive create receipt at canonical path
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    final_body = (json.dumps(receipt, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    try:
        fd = os.open(str(receipt_path), flags)
    except FileExistsError as exc:
        raise RetryAuthError(
            "BLOCKED_RETRY_AUTHORIZATION_ID_ALREADY_EXISTS",
            auth_id,
        ) from exc
    try:
        os.write(fd, final_body)
    finally:
        os.close(fd)

    seq = _next_sequence(case_root)
    event = {
        "EVENT_ID": f"RAE/{case_id}/{seq}",
        "SEQUENCE": seq,
        "EVENT_TYPE": EVENT_ISSUED,
        "RETRY_AUTHORIZATION_ID": auth_id,
        "NONCE": nonce,
        "ORCHESTRATION_ID": orchestration_id,
        "CASE_ID": case_id,
        "FINDING_ID": finding_id,
        "WORKER_ID": worker_id,
        "PREVIOUS_WORKER_EXECUTION_ID": previous_wex,
        "NEW_WORKER_EXECUTION_ID": None,
        "FROM_STATUS": None,
        "TO_STATUS": STATUS_ISSUED,
        "RECEIPT_CANONICAL_PATH": receipt["CANONICAL_RECEIPT_PATH"],
        "RECEIPT_RAW_SHA256": receipt["RECEIPT_RAW_SHA256"],
        "RECEIPT_CANONICAL_SHA256": receipt["RECEIPT_CANONICAL_SHA256"],
        "CREATED_AT": now,
    }
    _append_event(case_root, event)
    return receipt


def load_and_verify_receipt(case_root: Path, auth_id: str) -> Dict[str, Any]:
    """Load receipt ONLY from canonical path; verify signature + hashes + path."""
    case_root = Path(case_root)
    path = canonical_receipt_path(case_root, auth_id)
    if not path.exists():
        raise RetryAuthError(
            "BLOCKED_RETRY_AUTHORIZATION_REQUIRED",
            "receipt_missing",
        )
    raw = path.read_bytes()
    try:
        receipt = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RetryAuthError(
            "BLOCKED_RETRY_AUTHORIZATION_REGISTRY_INVALID",
            f"receipt_json:{exc}",
        ) from exc

    # Canonical path enforcement
    try:
        actual_rel = str(path.resolve().relative_to(case_root.resolve())).replace("\\", "/")
    except ValueError:
        actual_rel = str(path).replace("\\", "/")
    expected_rel = str(receipt.get("CANONICAL_RECEIPT_PATH") or "").replace("\\", "/")
    if actual_rel != expected_rel:
        raise RetryAuthError(
            "BLOCKED_RETRY_AUTHORIZATION_NON_CANONICAL_PATH",
            f"{actual_rel}!={expected_rel}",
        )
    if receipt.get("RETRY_AUTHORIZATION_ID") != auth_id:
        raise RetryAuthError(
            "BLOCKED_RETRY_AUTHORIZATION_NON_CANONICAL_PATH",
            "id_filename_mismatch",
        )

    secret = ensure_host_secret(case_root)
    material = _signing_material(receipt)
    expected_sig = _sign(secret, material)
    if not hmac.compare_digest(expected_sig, str(receipt.get("HOST_SIGNATURE") or "")):
        raise RetryAuthError(
            "BLOCKED_RETRY_AUTHORIZATION_SIGNATURE_MISMATCH",
            "host_signature",
        )
    expected_can = _sha256_bytes(material.encode("utf-8"))
    if receipt.get("RECEIPT_CANONICAL_SHA256") != expected_can:
        raise RetryAuthError(
            "BLOCKED_RETRY_AUTHORIZATION_SIGNATURE_MISMATCH",
            "canonical_hash",
        )
    if receipt.get("RECEIPT_RAW_SHA256") != _receipt_raw_hash(receipt):
        raise RetryAuthError(
            "BLOCKED_RETRY_AUTHORIZATION_SIGNATURE_MISMATCH",
            "raw_hash",
        )

    # Registry must contain matching ISSUED with same hashes
    events = load_registry_events(case_root)
    issued = [
        e
        for e in events
        if e.get("RETRY_AUTHORIZATION_ID") == auth_id and e.get("EVENT_TYPE") == EVENT_ISSUED
    ]
    if not issued:
        raise RetryAuthError(
            "BLOCKED_RETRY_AUTHORIZATION_REGISTRY_INVALID",
            "missing_issued",
        )
    iss = issued[0]
    if iss.get("RECEIPT_CANONICAL_SHA256") != receipt.get("RECEIPT_CANONICAL_SHA256"):
        raise RetryAuthError(
            "BLOCKED_RETRY_AUTHORIZATION_REGISTRY_INVALID",
            "receipt_hash_mismatch",
        )
    if iss.get("NONCE") != receipt.get("NONCE"):
        raise RetryAuthError(
            "BLOCKED_RETRY_AUTHORIZATION_REGISTRY_INVALID",
            "nonce_mismatch",
        )
    return receipt


def assert_registry_consistent(case_root: Path, auth_id: str) -> str:
    """Validate registry history for auth; return latest status."""
    if not registry_path(case_root).exists():
        raise RetryAuthError(
            "BLOCKED_RETRY_AUTHORIZATION_REGISTRY_INVALID",
            "registry_missing",
        )
    status, last = latest_status_for(case_root, auth_id)
    if status is None or last is None:
        raise RetryAuthError(
            "BLOCKED_RETRY_AUTHORIZATION_REGISTRY_INVALID",
            "no_events",
        )
    return str(status)


def reserve_authorization(
    case_root: Path,
    *,
    auth_id: str,
    new_worker_execution_id: str,
    orchestration_id: str,
    case_id: str,
    finding_id: Optional[str],
    worker_id: str,
) -> Dict[str, Any]:
    """ISSUED → RESERVED bound to exact new WEX. Returns verified receipt."""
    receipt = load_and_verify_receipt(case_root, auth_id)
    if receipt.get("ORCHESTRATION_ID") != orchestration_id:
        raise RetryAuthError("BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH", "orch")
    if receipt.get("CASE_ID") != case_id or receipt.get("FINDING_ID") != finding_id:
        raise RetryAuthError("BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH", "case_finding")
    if receipt.get("WORKER_ID") != worker_id:
        raise RetryAuthError("BLOCKED_RETRY_WORKER_MISMATCH", worker_id)

    now = time.time()
    if float(receipt.get("EXPIRES_AT") or 0) < now:
        # Record EXPIRED then reject
        try:
            status = assert_registry_consistent(case_root, auth_id)
            if status == STATUS_ISSUED:
                seq = _next_sequence(case_root)
                _append_event(
                    case_root,
                    {
                        "EVENT_ID": f"RAE/{case_id}/{seq}",
                        "SEQUENCE": seq,
                        "EVENT_TYPE": EVENT_EXPIRED,
                        "RETRY_AUTHORIZATION_ID": auth_id,
                        "NONCE": receipt["NONCE"],
                        "ORCHESTRATION_ID": orchestration_id,
                        "CASE_ID": case_id,
                        "FINDING_ID": finding_id,
                        "WORKER_ID": worker_id,
                        "PREVIOUS_WORKER_EXECUTION_ID": receipt["PREVIOUS_WORKER_EXECUTION_ID"],
                        "NEW_WORKER_EXECUTION_ID": None,
                        "FROM_STATUS": STATUS_ISSUED,
                        "TO_STATUS": STATUS_EXPIRED,
                        "RECEIPT_CANONICAL_PATH": receipt["CANONICAL_RECEIPT_PATH"],
                        "RECEIPT_RAW_SHA256": receipt["RECEIPT_RAW_SHA256"],
                        "RECEIPT_CANONICAL_SHA256": receipt["RECEIPT_CANONICAL_SHA256"],
                        "CREATED_AT": now,
                    },
                )
        except RetryAuthError:
            pass
        raise RetryAuthError("BLOCKED_RETRY_AUTHORIZATION_EXPIRED", auth_id)

    status = assert_registry_consistent(case_root, auth_id)
    if status == STATUS_RESERVED:
        raise RetryAuthError("BLOCKED_RETRY_AUTHORIZATION_REPLAY", "already_reserved")
    if status == STATUS_CONSUMED:
        raise RetryAuthError("BLOCKED_RETRY_AUTHORIZATION_REPLAY", "already_consumed")
    if status == STATUS_EXPIRED:
        raise RetryAuthError("BLOCKED_RETRY_AUTHORIZATION_EXPIRED", auth_id)
    if status != STATUS_ISSUED:
        raise RetryAuthError(
            "BLOCKED_RETRY_AUTHORIZATION_REGISTRY_INVALID",
            f"status={status}",
        )

    # Concurrent reservation: exclusive lock file per auth
    lock_path = retries_dir(case_root) / f".reserve_lock_{auth_id}"
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(str(lock_path), flags)
    except FileExistsError as exc:
        raise RetryAuthError(
            "BLOCKED_RETRY_AUTHORIZATION_REPLAY",
            "concurrent_reserve",
        ) from exc
    try:
        os.write(fd, new_worker_execution_id.encode("utf-8"))
    finally:
        os.close(fd)

    seq = _next_sequence(case_root)
    _append_event(
        case_root,
        {
            "EVENT_ID": f"RAE/{case_id}/{seq}",
            "SEQUENCE": seq,
            "EVENT_TYPE": EVENT_RESERVED,
            "RETRY_AUTHORIZATION_ID": auth_id,
            "NONCE": receipt["NONCE"],
            "ORCHESTRATION_ID": orchestration_id,
            "CASE_ID": case_id,
            "FINDING_ID": finding_id,
            "WORKER_ID": worker_id,
            "PREVIOUS_WORKER_EXECUTION_ID": receipt["PREVIOUS_WORKER_EXECUTION_ID"],
            "NEW_WORKER_EXECUTION_ID": new_worker_execution_id,
            "FROM_STATUS": STATUS_ISSUED,
            "TO_STATUS": STATUS_RESERVED,
            "RECEIPT_CANONICAL_PATH": receipt["CANONICAL_RECEIPT_PATH"],
            "RECEIPT_RAW_SHA256": receipt["RECEIPT_RAW_SHA256"],
            "RECEIPT_CANONICAL_SHA256": receipt["RECEIPT_CANONICAL_SHA256"],
            "CREATED_AT": now,
        },
    )
    return receipt


def consume_authorization(
    case_root: Path,
    *,
    auth_id: str,
    new_worker_execution_id: str,
    output_packet_raw_sha256: str,
    checkpoint_generation: int,
) -> Optional[Dict[str, Any]]:
    """RESERVED → CONSUMED. Idempotent if already CONSUMED for same WEX."""
    case_root = Path(case_root)
    status, last = latest_status_for(case_root, auth_id)
    if status == STATUS_CONSUMED:
        if last and last.get("NEW_WORKER_EXECUTION_ID") == new_worker_execution_id:
            return last  # duplicate finalize — no second event
        raise RetryAuthError("BLOCKED_RETRY_AUTHORIZATION_REPLAY", "consumed_other_wex")
    if status != STATUS_RESERVED:
        raise RetryAuthError(
            "BLOCKED_RETRY_AUTHORIZATION_REGISTRY_INVALID",
            f"consume_from={status}",
        )
    if last and last.get("NEW_WORKER_EXECUTION_ID") != new_worker_execution_id:
        raise RetryAuthError(
            "BLOCKED_RETRY_AUTHORIZATION_REPLAY",
            "wex_mismatch_on_consume",
        )

    receipt = load_and_verify_receipt(case_root, auth_id)
    seq = _next_sequence(case_root)
    now = time.time()
    return _append_event(
        case_root,
        {
            "EVENT_ID": f"RAE/{receipt['CASE_ID']}/{seq}",
            "SEQUENCE": seq,
            "EVENT_TYPE": EVENT_CONSUMED,
            "RETRY_AUTHORIZATION_ID": auth_id,
            "NONCE": receipt["NONCE"],
            "ORCHESTRATION_ID": receipt["ORCHESTRATION_ID"],
            "CASE_ID": receipt["CASE_ID"],
            "FINDING_ID": receipt["FINDING_ID"],
            "WORKER_ID": receipt["WORKER_ID"],
            "PREVIOUS_WORKER_EXECUTION_ID": receipt["PREVIOUS_WORKER_EXECUTION_ID"],
            "NEW_WORKER_EXECUTION_ID": new_worker_execution_id,
            "FROM_STATUS": STATUS_RESERVED,
            "TO_STATUS": STATUS_CONSUMED,
            "RECEIPT_CANONICAL_PATH": receipt["CANONICAL_RECEIPT_PATH"],
            "RECEIPT_RAW_SHA256": receipt["RECEIPT_RAW_SHA256"],
            "RECEIPT_CANONICAL_SHA256": receipt["RECEIPT_CANONICAL_SHA256"],
            "OUTPUT_PACKET_RAW_SHA256": output_packet_raw_sha256,
            "CHECKPOINT_GENERATION": checkpoint_generation,
            "CREATED_AT": now,
        },
    )


def registry_status(case_root: Path, auth_id: str) -> Optional[str]:
    status, _ = latest_status_for(case_root, auth_id)
    return status
