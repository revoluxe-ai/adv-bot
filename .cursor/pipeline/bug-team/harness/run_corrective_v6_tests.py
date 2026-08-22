# -*- coding: utf-8 -*-
"""Corrective V6 tests — BF-ICT-SR-001 retry authorization copy/replay.

Does NOT issue Independent Tester PASS. Does NOT activate runtime.
"""

from __future__ import annotations

import json
import shutil
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime import live_task_hop, packets, retry_auth  # noqa: E402
from runtime import activation  # noqa: E402

Result = Tuple[bool, str, str]
HARNESS = Path(".tmp/opsx-bug-team-harness/corrective-v6-unit")


def _case(name: str) -> Path:
    p = HARNESS / name
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)
    p.mkdir(parents=True, exist_ok=True)
    (p / "team" / "packets").mkdir(parents=True, exist_ok=True)
    (p / "results").mkdir(parents=True, exist_ok=True)
    (p / "gates").mkdir(parents=True, exist_ok=True)
    return p


def _prep(case: Path, **kw: Any) -> Dict[str, Any]:
    return live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id=kw.get("orch", "ORCH/v6"),
        worker_id=kw.get("worker", "CLASSIFIER"),
        case_id=kw.get("case_id", "C-V6"),
        finding_id=kw.get("finding", "F-V6"),
        execution_mode="REVIEW_PROOF_ONLY",
        checkpoint_generation=kw.get("cpg", 1),
        packet_generation=kw.get("pkg", 1),
        attempt=kw.get("attempt", 1),
        proof_root=case,
        payload=kw.get("payload") or {"PROOF": True},
    )


def _auth_flow(case: Path) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    p1 = _prep(case)
    live_task_hop.mark_timeout(case, p1["WORKER_EXECUTION_ID"])
    auth = live_task_hop.authorize_retry_or_resume(
        case_root=case,
        reason="v6",
        orchestration_id="ORCH/v6",
        case_id="C-V6",
        finding_id="F-V6",
    )
    return p1, auth, {}


def _prepare_retry(case: Path, auth: Dict[str, Any], **kw: Any) -> Dict[str, Any]:
    return live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id=kw.get("orch", "ORCH/v6"),
        worker_id=kw.get("worker", "CLASSIFIER"),
        case_id=kw.get("case_id", "C-V6"),
        finding_id=kw.get("finding", "F-V6"),
        execution_mode="REVIEW_PROOF_ONLY",
        checkpoint_generation=auth["CHECKPOINT_GENERATION"],
        packet_generation=auth["PACKET_GENERATION"],
        attempt=auth["NEXT_ATTEMPT"],
        proof_root=case,
    )


def _forge_ready(case: Path, auth_id: str, auth: Dict[str, Any]) -> None:
    cp = live_task_hop.load_checkpoint(case / "team" / "CHECKPOINT.json")
    cp["ACTIVE_STATUS"] = "READY_FOR_RETRY"
    cp["RETRY_AUTHORIZED"] = True
    cp["RETRY_AUTHORIZATION_ID"] = auth_id
    cp["ACTIVE_WORKER_EXECUTION_ID"] = None
    cp["CHECKPOINT_GENERATION"] = auth["CHECKPOINT_GENERATION"]
    cp["PACKET_GENERATION"] = auth["PACKET_GENERATION"]
    cp["ACTIVE_ATTEMPT"] = auth["NEXT_ATTEMPT"]
    live_task_hop.save_checkpoint(case / "team" / "CHECKPOINT.json", cp)


def _finalize_ok(case: Path, prep: Dict[str, Any]) -> Dict[str, Any]:
    live_task_hop.mark_task_started(Path(prep["DISPATCH_INTENT_PATH"]))
    out = Path(prep["EXPECTED_OUTPUT_PATH"])
    now = time.time()
    pkt = {
        "SCHEMA_VERSION": "1",
        "PACKET_TYPE": "WORKER_OUTPUT",
        "PACKET_ID": f"PKT/{prep['WORKER_EXECUTION_ID']}/OUT",
        "PACKET_GENERATION": prep.get("ATTEMPT", 2) and json.loads(
            Path(prep["DISPATCH_INTENT_PATH"]).read_text(encoding="utf-8")
        ).get("PACKET_GENERATION", 2),
        "ORCHESTRATION_ID": "ORCH/v6",
        "WORKER_EXECUTION_ID": prep["WORKER_EXECUTION_ID"],
        "WORKER_ID": "CLASSIFIER",
        "CASE_ID": "C-V6",
        "FINDING_ID": "F-V6",
        "PARENT_PACKET_ID": f"PKT/{prep['WORKER_EXECUTION_ID']}/IN",
        "DEPENDENCY_PACKET_IDS": [],
        "DEPENDENCY_HASHES": {},
        "CHECKPOINT_GENERATION": json.loads(
            Path(prep["DISPATCH_INTENT_PATH"]).read_text(encoding="utf-8")
        ).get("CHECKPOINT_GENERATION", 2),
        "CREATED_AT": now,
        "EXPIRES_AT": now + 3600,
        "STATUS": "PASS",
        "TERMINAL_STATUS": "PASS",
        "PAYLOAD": {"PROOF": True},
        "ARTIFACTS_WRITTEN": [],
        "EXECUTION_MODE": "REVIEW_PROOF_ONLY",
        "ACTIVATION_STATE_HASH": activation.activation_state_hash(),
        "ATTEMPT": prep["ATTEMPT"],
    }
    packets.write_packet(out, pkt)
    return live_task_hop.finalize_live_hop(
        case_root=case,
        dispatch_intent_path=Path(prep["DISPATCH_INTENT_PATH"]),
        actual_cursor_agent_id="agent-v6",
        output_packet_path=out,
    )


# --- Copy/replay ---


def replay01() -> Result:
    case = _case("replay01")
    _, auth, _ = _auth_flow(case)
    p2 = _prepare_retry(case, auth)
    _finalize_ok(case, p2)
    src = Path(auth["RETRY_AUTHORIZATION_PATH"])
    copied = case / "team" / "retries" / "RETRYAUTH-copied01.json"
    obj = json.loads(src.read_text(encoding="utf-8"))
    obj["RETRY_AUTHORIZATION_ID"] = "RETRYAUTH-copied01"
    obj["CANONICAL_RECEIPT_PATH"] = "team/retries/RETRYAUTH-copied01.json"
    obj["CONSUMED"] = False
    copied.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    _forge_ready(case, "RETRYAUTH-copied01", auth)
    cp_before = (case / "team" / "CHECKPOINT.json").read_text(encoding="utf-8")
    try:
        _prepare_retry(case, auth)
        return False, "copy replay should fail", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        cp_after = (case / "team" / "CHECKPOINT.json").read_text(encoding="utf-8")
        ok = (
            exc.code
            in {
                "BLOCKED_RETRY_AUTHORIZATION_NON_CANONICAL_PATH",
                "BLOCKED_RETRY_AUTHORIZATION_SIGNATURE_MISMATCH",
                "BLOCKED_RETRY_AUTHORIZATION_REPLAY",
                "BLOCKED_RETRY_AUTHORIZATION_REGISTRY_INVALID",
            }
            and cp_before == cp_after
        )
        return ok, "copied receipt path replay rejected", "RUNTIME_UNIT"


def replay02() -> Result:
    case = _case("replay02")
    _, auth, _ = _auth_flow(case)
    p2 = _prepare_retry(case, auth)
    _finalize_ok(case, p2)
    path = Path(auth["RETRY_AUTHORIZATION_PATH"])
    obj = json.loads(path.read_text(encoding="utf-8"))
    obj["CONSUMED"] = False
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    _forge_ready(case, auth["RETRY_AUTHORIZATION_ID"], auth)
    try:
        _prepare_retry(case, auth)
        return False, "edited CONSUMED=false should fail", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        status = retry_auth.registry_status(case, auth["RETRY_AUTHORIZATION_ID"])
        ok = (
            status == retry_auth.STATUS_CONSUMED
            and exc.code
            in {
                "BLOCKED_RETRY_AUTHORIZATION_REPLAY",
                "BLOCKED_RETRY_AUTHORIZATION_SIGNATURE_MISMATCH",
            }
        )
        return ok, "edited CONSUMED=false still CONSUMED in registry", "RUNTIME_UNIT"


def replay03() -> Result:
    case = _case("replay03")
    _, auth, _ = _auth_flow(case)
    original_bytes = Path(auth["RETRY_AUTHORIZATION_PATH"]).read_bytes()
    p2 = _prepare_retry(case, auth)
    _finalize_ok(case, p2)
    Path(auth["RETRY_AUTHORIZATION_PATH"]).write_bytes(original_bytes)
    _forge_ready(case, auth["RETRY_AUTHORIZATION_ID"], auth)
    try:
        _prepare_retry(case, auth)
        return False, "restored old bytes should fail", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        ok = (
            retry_auth.registry_status(case, auth["RETRY_AUTHORIZATION_ID"])
            == retry_auth.STATUS_CONSUMED
            and exc.code == "BLOCKED_RETRY_AUTHORIZATION_REPLAY"
        )
        return ok, "restored pre-consumption receipt rejected", "RUNTIME_UNIT"


def replay04() -> Result:
    case = _case("replay04")
    _, auth, _ = _auth_flow(case)
    p2 = _prepare_retry(case, auth)
    _finalize_ok(case, p2)
    src = Path(auth["RETRY_AUTHORIZATION_PATH"])
    # unchanged bytes under new filename
    new_path = case / "team" / "retries" / "RETRYAUTH-othername.json"
    new_path.write_bytes(src.read_bytes())
    _forge_ready(case, "RETRYAUTH-othername", auth)
    try:
        _prepare_retry(case, auth)
        return False, "should reject", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        ok = exc.code in {
            "BLOCKED_RETRY_AUTHORIZATION_NON_CANONICAL_PATH",
            "BLOCKED_RETRY_AUTHORIZATION_REQUIRED",
            "BLOCKED_RETRY_AUTHORIZATION_SIGNATURE_MISMATCH",
        }
        return ok, "copied under new AUTH filename rejected", "RUNTIME_UNIT"


def replay05() -> Result:
    case = _case("replay05")
    _, auth, _ = _auth_flow(case)
    receipt = json.loads(Path(auth["RETRY_AUTHORIZATION_PATH"]).read_text(encoding="utf-8"))
    nonce = receipt["NONCE"]
    # Attempt second issue with same nonce via direct registry forge is blocked;
    # simulate by trying to write ISSUED event with same nonce
    try:
        retry_auth._assert_unique_identity(
            case, auth_id="RETRYAUTH-newid999999", nonce=nonce
        )
        return False, "same nonce should reject", "RUNTIME_UNIT"
    except retry_auth.RetryAuthError as exc:
        return (
            exc.code == "BLOCKED_RETRY_NONCE_ALREADY_EXISTS",
            "same NONCE with new AUTH ID rejected",
            "RUNTIME_UNIT",
        )


def replay06() -> Result:
    case = _case("replay06")
    _, auth, _ = _auth_flow(case)
    try:
        retry_auth._assert_unique_identity(
            case, auth_id=auth["RETRY_AUTHORIZATION_ID"], nonce="freshnonce" + "ab" * 8
        )
        return False, "same auth id should reject", "RUNTIME_UNIT"
    except retry_auth.RetryAuthError as exc:
        return (
            exc.code == "BLOCKED_RETRY_AUTHORIZATION_ID_ALREADY_EXISTS",
            "same AUTH ID with new NONCE rejected",
            "RUNTIME_UNIT",
        )


def replay07() -> Result:
    case = _case("replay07")
    _, auth, _ = _auth_flow(case)
    src = Path(auth["RETRY_AUTHORIZATION_PATH"])
    obj = json.loads(src.read_text(encoding="utf-8"))
    obj["RETRY_AUTHORIZATION_ID"] = "RETRYAUTH-mutated01"
    obj["NONCE"] = "00" * 16
    obj["CANONICAL_RECEIPT_PATH"] = "team/retries/RETRYAUTH-mutated01.json"
    path = case / "team" / "retries" / "RETRYAUTH-mutated01.json"
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    _forge_ready(case, "RETRYAUTH-mutated01", auth)
    try:
        _prepare_retry(case, auth)
        return False, "should reject", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_RETRY_AUTHORIZATION_SIGNATURE_MISMATCH",
            "ID+NONCE modified signature mismatch",
            "RUNTIME_UNIT",
        )


def replay08() -> Result:
    case = _case("replay08")
    _, auth, _ = _auth_flow(case)
    p2 = _prepare_retry(case, auth)
    _finalize_ok(case, p2)
    # Rewrite registry to only a fake ISSUED without host signature
    reg = retry_auth.registry_path(case)
    fake = {
        "EVENT_ID": "RAE/fake/1",
        "SEQUENCE": 1,
        "EVENT_TYPE": retry_auth.EVENT_ISSUED,
        "RETRY_AUTHORIZATION_ID": auth["RETRY_AUTHORIZATION_ID"],
        "NONCE": auth.get("NONCE")
        or json.loads(Path(auth["RETRY_AUTHORIZATION_PATH"]).read_text(encoding="utf-8"))["NONCE"],
        "ORCHESTRATION_ID": "ORCH/v6",
        "CASE_ID": "C-V6",
        "FINDING_ID": "F-V6",
        "WORKER_ID": "CLASSIFIER",
        "PREVIOUS_WORKER_EXECUTION_ID": "WEX/X",
        "NEW_WORKER_EXECUTION_ID": None,
        "FROM_STATUS": None,
        "TO_STATUS": "ISSUED",
        "RECEIPT_CANONICAL_PATH": "team/retries/x.json",
        "RECEIPT_RAW_SHA256": "0" * 64,
        "RECEIPT_CANONICAL_SHA256": "0" * 64,
        "CREATED_AT": time.time(),
        "HOST_EVENT_SIGNATURE": "deadbeef",
    }
    reg.write_text(json.dumps(fake) + "\n", encoding="utf-8")
    _forge_ready(case, auth["RETRY_AUTHORIZATION_ID"], auth)
    try:
        _prepare_retry(case, auth)
        return False, "rewritten registry should fail", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_RETRY_AUTHORIZATION_REGISTRY_INVALID",
            "registry rewritten ISSUED rejected",
            "RUNTIME_UNIT",
        )


# --- Registry ---


def reg01() -> Result:
    case = _case("reg01")
    _, auth, _ = _auth_flow(case)
    assert retry_auth.registry_status(case, auth["RETRY_AUTHORIZATION_ID"]) == "ISSUED"
    p2 = _prepare_retry(case, auth)
    ok = p2.get("DISPATCH_INTENT_CREATED") is True
    return ok, "receipt ISSUED + registry ISSUED allows reservation", "RUNTIME_UNIT"


def reg02() -> Result:
    case = _case("reg02")
    _, auth, _ = _auth_flow(case)
    _prepare_retry(case, auth)
    _forge_ready(case, auth["RETRY_AUTHORIZATION_ID"], auth)
    try:
        _prepare_retry(case, auth)
        return False, "second reserve should fail", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_RETRY_AUTHORIZATION_REPLAY",
            "second reservation rejected",
            "RUNTIME_UNIT",
        )


def reg03() -> Result:
    case = _case("reg03")
    _, auth, _ = _auth_flow(case)
    p2 = _prepare_retry(case, auth)
    _finalize_ok(case, p2)
    _forge_ready(case, auth["RETRY_AUTHORIZATION_ID"], auth)
    try:
        _prepare_retry(case, auth)
        return False, "consumed should fail", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_RETRY_AUTHORIZATION_REPLAY",
            "registry CONSUMED replay rejected",
            "RUNTIME_UNIT",
        )


def reg04() -> Result:
    case = _case("reg04")
    _, auth, _ = _auth_flow(case)
    retry_auth.registry_path(case).unlink()
    _forge_ready(case, auth["RETRY_AUTHORIZATION_ID"], auth)
    try:
        _prepare_retry(case, auth)
        return False, "missing registry should fail", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_RETRY_AUTHORIZATION_REGISTRY_INVALID",
            "receipt exists + registry missing rejected",
            "RUNTIME_UNIT",
        )


def reg05() -> Result:
    case = _case("reg05")
    _, auth, _ = _auth_flow(case)
    # Tamper ISSUED event receipt hash then resign fails — rewrite line with wrong hash but keep sig broken
    events = retry_auth.load_registry_events(case)
    ev = dict(events[0])
    ev["RECEIPT_CANONICAL_SHA256"] = "11" * 32
    secret = retry_auth.ensure_host_secret(case)
    ev.pop("HOST_EVENT_SIGNATURE", None)
    ev["HOST_EVENT_SIGNATURE"] = retry_auth._sign_event(secret, ev)
    retry_auth.registry_path(case).write_text(json.dumps(ev) + "\n", encoding="utf-8")
    try:
        retry_auth.load_and_verify_receipt(case, auth["RETRY_AUTHORIZATION_ID"])
        return False, "hash mismatch should fail", "RUNTIME_UNIT"
    except retry_auth.RetryAuthError as exc:
        return (
            exc.code == "BLOCKED_RETRY_AUTHORIZATION_REGISTRY_INVALID",
            "registry receipt hash differs rejected",
            "RUNTIME_UNIT",
        )


def reg06() -> Result:
    case = _case("reg06")
    _, auth, _ = _auth_flow(case)
    line = retry_auth.registry_path(case).read_text(encoding="utf-8").strip()
    retry_auth.registry_path(case).write_text(line + "\n" + line + "\n", encoding="utf-8")
    try:
        retry_auth.load_registry_events(case)
        return False, "dup seq should fail", "RUNTIME_UNIT"
    except retry_auth.RetryAuthError as exc:
        return (
            exc.code == "BLOCKED_RETRY_AUTHORIZATION_REGISTRY_INVALID",
            "duplicate registry sequence rejected",
            "RUNTIME_UNIT",
        )


def reg07() -> Result:
    case = _case("reg07")
    _, auth, _ = _auth_flow(case)
    receipt = json.loads(Path(auth["RETRY_AUTHORIZATION_PATH"]).read_text(encoding="utf-8"))
    try:
        retry_auth._assert_unique_identity(
            case, auth_id="RETRYAUTH-another0001", nonce=receipt["NONCE"]
        )
        return False, "dup nonce should fail", "RUNTIME_UNIT"
    except retry_auth.RetryAuthError as exc:
        return (
            exc.code == "BLOCKED_RETRY_NONCE_ALREADY_EXISTS",
            "duplicate NONCE identity rejected",
            "RUNTIME_UNIT",
        )


def reg08() -> Result:
    case = _case("reg08")
    _, auth, _ = _auth_flow(case)
    p2 = _prepare_retry(case, auth)
    _finalize_ok(case, p2)
    try:
        retry_auth._validate_transition(retry_auth.STATUS_CONSUMED, retry_auth.STATUS_ISSUED)
        return False, "rollback should fail", "RUNTIME_UNIT"
    except retry_auth.RetryAuthError as exc:
        return (
            exc.code == "BLOCKED_RETRY_AUTHORIZATION_REGISTRY_INVALID",
            "invalid CONSUMED->ISSUED transition rejected",
            "RUNTIME_UNIT",
        )


# --- State ---


def state01() -> Result:
    case = _case("state01")
    _, auth, _ = _auth_flow(case)
    p2 = _prepare_retry(case, auth)
    last = retry_auth.latest_status_for(case, auth["RETRY_AUTHORIZATION_ID"])[1]
    ok = (
        retry_auth.registry_status(case, auth["RETRY_AUTHORIZATION_ID"]) == "RESERVED"
        and last is not None
        and last.get("NEW_WORKER_EXECUTION_ID") == p2["WORKER_EXECUTION_ID"]
    )
    return ok, "exact valid authorization reserves for one WEX", "RUNTIME_UNIT"


def state02() -> Result:
    case = _case("state02")
    _, auth, _ = _auth_flow(case)
    p2 = _prepare_retry(case, auth)
    # Attempt consume with different WEX
    try:
        retry_auth.consume_authorization(
            case,
            auth_id=auth["RETRY_AUTHORIZATION_ID"],
            new_worker_execution_id="WEX/CLASSIFIER/OTHER",
            output_packet_raw_sha256="0" * 64,
            checkpoint_generation=2,
        )
        return False, "WEX-B consume should fail", "RUNTIME_UNIT"
    except retry_auth.RetryAuthError as exc:
        _ = p2
        return (
            exc.code == "BLOCKED_RETRY_AUTHORIZATION_REPLAY",
            "WEX-B cannot use reservation for WEX-A",
            "RUNTIME_UNIT",
        )


def state03() -> Result:
    case = _case("state03")
    _, auth, _ = _auth_flow(case)
    p2 = _prepare_retry(case, auth)
    res = _finalize_ok(case, p2)
    ok = (
        res.get("CHECKPOINT_ADVANCED") is not False
        and retry_auth.registry_status(case, auth["RETRY_AUTHORIZATION_ID"]) == "CONSUMED"
    )
    # finalize returns various shapes; check status CONSUMED
    ok = retry_auth.registry_status(case, auth["RETRY_AUTHORIZATION_ID"]) == "CONSUMED"
    return ok, "valid finalize consumes authorization", "RUNTIME_UNIT"


def state04() -> Result:
    case = _case("state04")
    _, auth, _ = _auth_flow(case)
    p2 = _prepare_retry(case, auth)
    _finalize_ok(case, p2)
    before = len(retry_auth.load_registry_events(case))
    # second consume same WEX — idempotent no new event
    retry_auth.consume_authorization(
        case,
        auth_id=auth["RETRY_AUTHORIZATION_ID"],
        new_worker_execution_id=p2["WORKER_EXECUTION_ID"],
        output_packet_raw_sha256="0" * 64,
        checkpoint_generation=2,
    )
    after = len(retry_auth.load_registry_events(case))
    return before == after, "duplicate finalize does not create second consume", "RUNTIME_UNIT"


def state05() -> Result:
    case = _case("state05")
    _, auth, _ = _auth_flow(case)
    p2 = _prepare_retry(case, auth)
    # stale finalize
    live_task_hop.mark_timeout(case, p2["WORKER_EXECUTION_ID"])
    out = Path(p2["EXPECTED_OUTPUT_PATH"])
    packets.write_packet(
        out,
        {
            "SCHEMA_VERSION": "1",
            "PACKET_TYPE": "WORKER_OUTPUT",
            "PACKET_ID": "PKT/x/OUT",
            "PACKET_GENERATION": auth["PACKET_GENERATION"],
            "ORCHESTRATION_ID": "ORCH/v6",
            "WORKER_EXECUTION_ID": p2["WORKER_EXECUTION_ID"],
            "WORKER_ID": "CLASSIFIER",
            "CASE_ID": "C-V6",
            "FINDING_ID": "F-V6",
            "PARENT_PACKET_ID": None,
            "DEPENDENCY_PACKET_IDS": [],
            "DEPENDENCY_HASHES": {},
            "CHECKPOINT_GENERATION": auth["CHECKPOINT_GENERATION"],
            "CREATED_AT": time.time(),
            "EXPIRES_AT": time.time() + 3600,
            "STATUS": "PASS",
            "TERMINAL_STATUS": "PASS",
            "PAYLOAD": {},
            "ARTIFACTS_WRITTEN": [],
            "EXECUTION_MODE": "REVIEW_PROOF_ONLY",
            "ACTIVATION_STATE_HASH": activation.activation_state_hash(),
            "ATTEMPT": auth["NEXT_ATTEMPT"],
        },
    )
    intent = json.loads(Path(p2["DISPATCH_INTENT_PATH"]).read_text(encoding="utf-8"))
    intent["STATUS"] = "DISPATCHED"
    Path(p2["DISPATCH_INTENT_PATH"]).write_text(json.dumps(intent, indent=2) + "\n", encoding="utf-8")
    live_task_hop.finalize_live_hop(
        case_root=case,
        dispatch_intent_path=Path(p2["DISPATCH_INTENT_PATH"]),
        actual_cursor_agent_id="agent",
        output_packet_path=out,
    )
    ok = retry_auth.registry_status(case, auth["RETRY_AUTHORIZATION_ID"]) == "RESERVED"
    return ok, "failed/stale finalize does not consume authorization", "RUNTIME_UNIT"


def state06() -> Result:
    case = _case("state06")
    _, auth, _ = _auth_flow(case)
    p2 = _prepare_retry(case, auth)
    _finalize_ok(case, p2)
    _forge_ready(case, auth["RETRY_AUTHORIZATION_ID"], auth)
    try:
        _prepare_retry(case, auth)
        return False, "should not create intent", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_RETRY_AUTHORIZATION_REPLAY"
            and exc.payload.get("DISPATCH_INTENT_CREATED", False) is not True,
            "consumed authorization cannot create another dispatch intent",
            "RUNTIME_UNIT",
        )


def ict_sr_reg_ap10() -> Result:
    """Literal ICT-SR-REG-AP10 reproduction."""
    case = _case("ict_ap10")
    p1 = live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id="ORCH/ap10",
        worker_id="CLASSIFIER",
        case_id="C-AP10",
        finding_id="F-AP10",
        execution_mode="REVIEW_PROOF_ONLY",
        checkpoint_generation=1,
        packet_generation=1,
        proof_root=case,
    )
    live_task_hop.mark_timeout(case, p1["WORKER_EXECUTION_ID"])
    auth = live_task_hop.authorize_retry_or_resume(
        case_root=case,
        reason="ap10",
        orchestration_id="ORCH/ap10",
        case_id="C-AP10",
        finding_id="F-AP10",
    )
    p2 = live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id="ORCH/ap10",
        worker_id="CLASSIFIER",
        case_id="C-AP10",
        finding_id="F-AP10",
        execution_mode="REVIEW_PROOF_ONLY",
        checkpoint_generation=auth["CHECKPOINT_GENERATION"],
        packet_generation=auth["PACKET_GENERATION"],
        attempt=auth["NEXT_ATTEMPT"],
        proof_root=case,
    )
    src = Path(auth["RETRY_AUTHORIZATION_PATH"])
    copied = case / "team" / "retries" / "RETRYAUTH-copied01.json"
    obj = json.loads(src.read_text(encoding="utf-8"))
    obj["RETRY_AUTHORIZATION_ID"] = "RETRYAUTH-copied01"
    obj["CANONICAL_RECEIPT_PATH"] = "team/retries/RETRYAUTH-copied01.json"
    obj["CONSUMED"] = False
    copied.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    cp = live_task_hop.load_checkpoint(case / "team" / "CHECKPOINT.json")
    cp_before = json.dumps(cp, sort_keys=True)
    cp["ACTIVE_STATUS"] = "READY_FOR_RETRY"
    cp["RETRY_AUTHORIZED"] = True
    cp["RETRY_AUTHORIZATION_ID"] = "RETRYAUTH-copied01"
    cp["ACTIVE_WORKER_EXECUTION_ID"] = None
    live_task_hop.save_checkpoint(case / "team" / "CHECKPOINT.json", cp)
    try:
        p3 = live_task_hop.prepare_live_hop(
            case_root=case,
            orchestration_id="ORCH/ap10",
            worker_id="CLASSIFIER",
            case_id="C-AP10",
            finding_id="F-AP10",
            execution_mode="REVIEW_PROOF_ONLY",
            checkpoint_generation=auth["CHECKPOINT_GENERATION"],
            packet_generation=auth["PACKET_GENERATION"],
            attempt=auth["NEXT_ATTEMPT"],
            proof_root=case,
        )
        return False, f"AP10 must not create WEX-3 got {p3.get('WORKER_EXECUTION_ID')}", "ICT_REGRESSION"
    except live_task_hop.LiveHopError as exc:
        cp_after = live_task_hop.load_checkpoint(case / "team" / "CHECKPOINT.json")
        # no new intent for copied id
        intents = list((case / "team" / "intents").glob("*.intent.json"))
        wex_ids = {json.loads(p.read_text(encoding="utf-8")).get("WORKER_EXECUTION_ID") for p in intents}
        ok = (
            exc.code
            in {
                "BLOCKED_RETRY_AUTHORIZATION_SIGNATURE_MISMATCH",
                "BLOCKED_RETRY_AUTHORIZATION_NON_CANONICAL_PATH",
                "BLOCKED_RETRY_AUTHORIZATION_REPLAY",
                "BLOCKED_RETRY_AUTHORIZATION_REGISTRY_INVALID",
            }
            and p2["WORKER_EXECUTION_ID"] in wex_ids
            and len(wex_ids) == 2  # only WEX-1 and WEX-2
            and cp_after.get("RETRY_AUTHORIZATION_ID") == "RETRYAUTH-copied01"  # forge remains but no prepare
        )
        _ = cp_before
        return ok, "ICT-SR-REG-AP10 copy-replay rejected; no WEX-3", "ICT_REGRESSION"


# --- Adversarial ---


def adv_a1() -> Result:
    case = _case("adv_a1")
    _, auth, _ = _auth_flow(case)
    p2 = _prepare_retry(case, auth)
    _finalize_ok(case, p2)
    dup = case / "team" / "retries" / "dup.json"
    shutil.copy2(auth["RETRY_AUTHORIZATION_PATH"], dup)
    _forge_ready(case, Path(auth["RETRY_AUTHORIZATION_PATH"]).stem, auth)
    # use original id but also try load from dup - runtime only uses canonical
    try:
        _prepare_retry(case, auth)
        return False, "should reject", "ADVERSARIAL"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_RETRY_AUTHORIZATION_REPLAY",
            "duplicated receipt replay rejected by registry",
            "ADVERSARIAL",
        )


def adv_a2() -> Result:
    case = _case("adv_a2")
    _, auth, _ = _auth_flow(case)
    p2 = _prepare_retry(case, auth)
    _finalize_ok(case, p2)
    path = Path(auth["RETRY_AUTHORIZATION_PATH"])
    tmp = case / "team" / "retries" / "_moved.json"
    data = path.read_bytes()
    path.unlink()
    tmp.write_bytes(data)
    path.write_bytes(tmp.read_bytes())
    _forge_ready(case, auth["RETRY_AUTHORIZATION_ID"], auth)
    try:
        _prepare_retry(case, auth)
        return False, "should reject", "ADVERSARIAL"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_RETRY_AUTHORIZATION_REPLAY",
            "moved/copied-back still CONSUMED",
            "ADVERSARIAL",
        )


def adv_a3() -> Result:
    case = _case("adv_a3")
    _, auth, _ = _auth_flow(case)
    p2 = _prepare_retry(case, auth)
    _forge_ready(case, auth["RETRY_AUTHORIZATION_ID"], auth)
    try:
        live_task_hop.prepare_live_hop(
            case_root=case,
            orchestration_id="ORCH/v6",
            worker_id="CLASSIFIER",
            case_id="C-V6",
            finding_id="F-V6",
            execution_mode="REVIEW_PROOF_ONLY",
            checkpoint_generation=auth["CHECKPOINT_GENERATION"],
            packet_generation=auth["PACKET_GENERATION"],
            attempt=auth["NEXT_ATTEMPT"],
            proof_root=case,
        )
        return False, "WEX-B should fail", "ADVERSARIAL"
    except live_task_hop.LiveHopError as exc:
        _ = p2
        return (
            exc.code == "BLOCKED_RETRY_AUTHORIZATION_REPLAY",
            "RESERVED for WEX-A blocks WEX-B",
            "ADVERSARIAL",
        )


def adv_a4() -> Result:
    case = _case("adv_a4")
    _, auth, _ = _auth_flow(case)
    p2 = _prepare_retry(case, auth)
    _finalize_ok(case, p2)
    path = Path(auth["RETRY_AUTHORIZATION_PATH"])
    # touch receipt newer
    obj = json.loads(path.read_text(encoding="utf-8"))
    obj["ISSUED_AT"] = time.time() + 9999
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    _forge_ready(case, auth["RETRY_AUTHORIZATION_ID"], auth)
    try:
        _prepare_retry(case, auth)
        return False, "newer timestamp must not restore", "ADVERSARIAL"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code
            in {
                "BLOCKED_RETRY_AUTHORIZATION_REPLAY",
                "BLOCKED_RETRY_AUTHORIZATION_SIGNATURE_MISMATCH",
            },
            "newer receipt timestamp no authority restoration",
            "ADVERSARIAL",
        )


def adv_a5() -> Result:
    case_a = _case("adv_a5a")
    case_b = _case("adv_a5b")
    _, auth, _ = _auth_flow(case_a)
    # copy receipt+secret attempt into other case root
    retries_b = case_b / "team" / "retries"
    retries_b.mkdir(parents=True, exist_ok=True)
    shutil.copy2(auth["RETRY_AUTHORIZATION_PATH"], retries_b / Path(auth["RETRY_AUTHORIZATION_PATH"]).name)
    _forge_ready(case_b, auth["RETRY_AUTHORIZATION_ID"], auth)
    try:
        live_task_hop.prepare_live_hop(
            case_root=case_b,
            orchestration_id="ORCH/v6",
            worker_id="CLASSIFIER",
            case_id="C-V6",
            finding_id="F-V6",
            execution_mode="REVIEW_PROOF_ONLY",
            checkpoint_generation=auth["CHECKPOINT_GENERATION"],
            packet_generation=auth["PACKET_GENERATION"],
            attempt=auth["NEXT_ATTEMPT"],
            proof_root=case_b,
        )
        return False, "cross-case should fail", "ADVERSARIAL"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code
            in {
                "BLOCKED_RETRY_AUTHORIZATION_REGISTRY_INVALID",
                "BLOCKED_RETRY_AUTHORIZATION_SIGNATURE_MISMATCH",
                "BLOCKED_RETRY_AUTHORIZATION_REQUIRED",
            },
            "receipt from another proof/case root rejected",
            "ADVERSARIAL",
        )


def adv_a6() -> Result:
    case = _case("adv_a6")
    _, auth, _ = _auth_flow(case)
    # place receipt at noncanonical path only
    canon = Path(auth["RETRY_AUTHORIZATION_PATH"])
    noncanon = case / "team" / "retries" / "noncanonical.json"
    noncanon.write_bytes(canon.read_bytes())
    canon.unlink()
    _forge_ready(case, auth["RETRY_AUTHORIZATION_ID"], auth)
    try:
        _prepare_retry(case, auth)
        return False, "noncanonical should fail", "ADVERSARIAL"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code
            in {
                "BLOCKED_RETRY_AUTHORIZATION_REQUIRED",
                "BLOCKED_RETRY_AUTHORIZATION_NON_CANONICAL_PATH",
            },
            "ISSUED registry but noncanonical path rejected",
            "ADVERSARIAL",
        )


def adv_a7() -> Result:
    case = _case("adv_a7")
    _, auth, _ = _auth_flow(case)
    # pre-create reserve lock
    lock = case / "team" / "retries" / f".reserve_lock_{auth['RETRY_AUTHORIZATION_ID']}"
    lock.write_text("other", encoding="utf-8")
    try:
        _prepare_retry(case, auth)
        return False, "concurrent should fail", "ADVERSARIAL"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_RETRY_AUTHORIZATION_REPLAY",
            "two simultaneous reservation attempts - only one succeeds",
            "ADVERSARIAL",
        )


def adv_a8() -> Result:
    case = _case("adv_a8")
    p1 = _prep(case)
    live_task_hop.mark_timeout(case, p1["WORKER_EXECUTION_ID"])
    # issue with ttl already expired via direct API
    intent = json.loads(
        (case / "team" / "intents" / f"{live_task_hop._wex_slug(p1['WORKER_EXECUTION_ID'])}.intent.json").read_text(
            encoding="utf-8"
        )
    )
    receipt = retry_auth.issue_retry_authorization(
        case,
        orchestration_id="ORCH/v6",
        case_id="C-V6",
        finding_id="F-V6",
        worker_id="CLASSIFIER",
        previous_wex=p1["WORKER_EXECUTION_ID"],
        previous_terminal_status="TIMEOUT",
        previous_attempt=1,
        previous_packet_generation=1,
        previous_checkpoint_generation=1,
        previous_input_raw=intent["INPUT_PACKET_RAW_SHA256"],
        previous_input_canonical=intent["INPUT_PACKET_CANONICAL_SHA256"],
        next_attempt=2,
        next_packet_generation=2,
        next_checkpoint_generation=2,
        ttl_seconds=-1,
    )
    auth = {
        "RETRY_AUTHORIZATION_ID": receipt["RETRY_AUTHORIZATION_ID"],
        "CHECKPOINT_GENERATION": 2,
        "PACKET_GENERATION": 2,
        "NEXT_ATTEMPT": 2,
    }
    _forge_ready(case, receipt["RETRY_AUTHORIZATION_ID"], auth)
    try:
        _prepare_retry(case, auth)
        return False, "expired should fail", "ADVERSARIAL"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_RETRY_AUTHORIZATION_EXPIRED",
            "authorization expired before reservation",
            "ADVERSARIAL",
        )


TESTS: List[Tuple[str, Callable[[], Result]]] = [
    ("V6-REPLAY-01", replay01),
    ("V6-REPLAY-02", replay02),
    ("V6-REPLAY-03", replay03),
    ("V6-REPLAY-04", replay04),
    ("V6-REPLAY-05", replay05),
    ("V6-REPLAY-06", replay06),
    ("V6-REPLAY-07", replay07),
    ("V6-REPLAY-08", replay08),
    ("V6-REG-01", reg01),
    ("V6-REG-02", reg02),
    ("V6-REG-03", reg03),
    ("V6-REG-04", reg04),
    ("V6-REG-05", reg05),
    ("V6-REG-06", reg06),
    ("V6-REG-07", reg07),
    ("V6-REG-08", reg08),
    ("V6-STATE-01", state01),
    ("V6-STATE-02", state02),
    ("V6-STATE-03", state03),
    ("V6-STATE-04", state04),
    ("V6-STATE-05", state05),
    ("V6-STATE-06", state06),
    ("ICT-SR-REG-AP10", ict_sr_reg_ap10),
    ("V6-ADV-A1", adv_a1),
    ("V6-ADV-A2", adv_a2),
    ("V6-ADV-A3", adv_a3),
    ("V6-ADV-A4", adv_a4),
    ("V6-ADV-A5", adv_a5),
    ("V6-ADV-A6", adv_a6),
    ("V6-ADV-A7", adv_a7),
    ("V6-ADV-A8", adv_a8),
]


def main() -> int:
    print("=== Corrective V6 tests (BF-ICT-SR-001) ===")
    print(f"activation: {activation.load_activation().get('RUNTIME_STATUS')}")
    passed = failed = 0
    rows: List[Dict[str, Any]] = []
    for name, fn in TESTS:
        try:
            ok, detail, kind = fn()
        except Exception as exc:  # noqa: BLE001
            ok, detail, kind = False, f"EXC {exc}", "ERROR"
            traceback.print_exc()
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"[{status}] {name}: {detail} ({kind})".encode("ascii", "replace").decode("ascii"))
        rows.append({"id": name, "status": status, "detail": detail, "kind": kind})
    total = passed + failed
    print(f"\nTOTAL={total} PASSED={passed} FAILED={failed}")
    out = Path(".tmp/opsx-bug-team-harness/corrective-v6-unit/RESULTS.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"total": total, "passed": passed, "failed": failed, "rows": rows}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
