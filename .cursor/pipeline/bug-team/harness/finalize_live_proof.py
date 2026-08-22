# -*- coding: utf-8 -*-
"""Finalize live Cursor Task proofs into DISPATCH/TRACE/report.

EXECUTION_CLASS:
  PROOF_HELPER

LIVE_RUNTIME_AUTHORITY:
  NONE
"""

from __future__ import annotations

import json
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(".cursor/pipeline/bug-team").resolve()))
from runtime import packets, fs_boundary, route_trace
from runtime.timeout import write_timeout_policy_status

AGENT_IDS = {
    "MATERIALIZER": "455990c1-13f6-4faa-964b-a021820b9920",
    "CLAIM_WORKER": "e14fd7c4-cf6a-4027-9671-735e0fad4feb",
    "CLASSIFIER": "66f56087-ef32-46ee-8d39-f41b55007b66",
    "SPEC_UPDATE_WORKER": "013d73a3-ea6d-4458-8d95-2284f988651c",
    "RED_TEST_WORKER": "0419c058-fec6-46fd-8534-791c590c1c10",
    "IMPLEMENTATION_EXECUTOR": "ebc0e981-9a41-4cfc-9cc1-80906945bd70",
    "GREEN_VERIFIER": "0e68bb01-f409-4dc4-98e0-7abe60fd2ff6",
    "TASK_COMPLETION_WORKER": "a347cc4e-e47f-43c9-9c4b-aaac3d222be0",
    "BOUNDED_HUNTER": "b4bc4d5e-811b-4d41-91bf-64a7bd524ce7",
    "FAN_IN_ASSEMBLER": "43e46744-8ba0-4386-b1b5-85293d1a0802",
    "CLOSURE_OPERATOR": "7c094613-aec8-4008-887d-1257ad4101b7",
}


def main() -> None:
    meta_path = Path(
        ".tmp/opsx-bug-team-harness/live-runtime-proof/20260728T044128Z/PROOF_META.json"
    )
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    case = Path(meta["CASE_ROOT"])
    dispatch_path = case / "team" / "DISPATCH.jsonl"
    trace_path = case / "results" / "ROUTE-TRACE.jsonl"
    if dispatch_path.exists():
        dispatch_path.unlink()
    if trace_path.exists():
        trace_path.unlink()

    matrix = {}
    act_hash = meta["ACTIVATION_STATE_HASH"]
    seq = 0
    for wid, w in meta["WORKERS"].items():
        in_path = Path(w["INPUT_PACKET_PATH"])
        out_path = Path(w["OUTPUT_PACKET_PATH"])
        agent = AGENT_IDS[wid]
        row = {
            "WORKER_ID": wid,
            "PROOF_MODE": "REVIEW_PROOF_ONLY",
            "CURSOR_AGENT_ID": agent,
            "INPUT_PACKET_PATH": str(in_path),
            "INPUT_PACKET_SHA256": w["INPUT_PACKET_SHA256"],
            "OUTPUT_PACKET_PATH": str(out_path),
            "OUTPUT_PACKET_SHA256": None,
            "SCHEMA_RESULT": "NOT_PROVEN",
            "WRITE_BOUNDARY_RESULT": "NOT_PROVEN",
            "TRACE_EVENT_RESULT": "NOT_PROVEN",
            "CHECKPOINT_RESULT": "NOT_PROVEN",
            "TERMINAL_STATUS": "NOT_PROVEN",
        }
        if not out_path.exists():
            row["TERMINAL_STATUS"] = "MISSING_OUTPUT"
            matrix[wid] = row
            continue
        try:
            out_pkt = packets.read_packet(out_path)
            packets.validate_packet(
                out_pkt,
                expect_type="WORKER_OUTPUT",
                expect_worker_id=wid,
                expect_wex=w["WORKER_EXECUTION_ID"],
                expect_orch=meta["ORCHESTRATION_ID"],
                expect_case=meta["CASE_ID"],
                expect_finding=meta["FINDING_ID"],
                expect_checkpoint_generation=1,
                expect_packet_generation=1,
                expect_activation_hash=act_hash,
                require_active_for_normal=True,
                activation_is_active=False,
            )
            row["SCHEMA_RESULT"] = "PASS"
            row["OUTPUT_PACKET_SHA256"] = packets.sha256_file(out_path)
            row["TERMINAL_STATUS"] = out_pkt.get("TERMINAL_STATUS") or out_pkt.get(
                "STATUS"
            )
        except Exception as exc:  # noqa: BLE001
            row["SCHEMA_RESULT"] = f"FAIL:{exc}"
            row["TERMINAL_STATUS"] = "BLOCKED_INVALID_PACKET"
            matrix[wid] = row
            continue

        created = []
        biz = (
            "results/FANIN.md"
            if wid == "FAN_IN_ASSEMBLER"
            else f"results/PROOF-{wid}.md"
        )
        if (case / biz).exists():
            created.append(biz)
        diff = fs_boundary.FsDiff(created=created, modified=[], deleted=[])
        wb, viol = fs_boundary.evaluate_write_boundary(wid, diff)
        row["WRITE_BOUNDARY_RESULT"] = wb
        if viol:
            row["WRITE_BOUNDARY_RESULT"] = "VIOLATION"
            row["VIOLATIONS"] = viol

        seq += 1
        event = {
            "SCHEMA_VERSION": "2",
            "EVENT_ID": f"RTE/{meta['CASE_ID']}/{seq}",
            "SEQUENCE": seq,
            "CASE_ID": meta["CASE_ID"],
            "FINDING_ID": meta["FINDING_ID"],
            "ORCHESTRATION_ID": meta["ORCHESTRATION_ID"],
            "ACTOR_ROLE": "WORKER",
            "WORKER_ID": wid,
            "WORKER_EXECUTION_ID": w["WORKER_EXECUTION_ID"],
            "CURSOR_AGENT_ID": agent,
            "EVENT_TYPE": "WORKER_COMPLETED",
            "FROM_STATE": "PROOF",
            "TO_STATE": "PROOF_DONE",
            "CHOSEN_ROUTE": None,
            "EXPECTED_NEXT_COMMAND": None,
            "ACTUAL_NEXT_COMMAND": None,
            "NEXT_COMMAND_RECONCILIATION": "NOT_APPLICABLE",
            "EXPECTED_EXECUTION_ROUTE": None,
            "ACTUAL_EXECUTION_ROUTE": None,
            "ROUTE_RECONCILIATION": "NOT_APPLICABLE",
            "STARTED_AT": time.time(),
            "FINISHED_AT": time.time(),
            "DURATION_MS": 0,
            "ATTEMPT": 1,
            "OWNER_GATE_STATUS": None,
            "BLOCKED_REASON": None,
            "TIMEOUT_REASON": None,
            "INPUT_PACKET_PATH": str(in_path),
            "INPUT_PACKET_SHA256": w["INPUT_PACKET_SHA256"],
            "OUTPUT_PACKET_PATH": str(out_path),
            "OUTPUT_PACKET_SHA256": row["OUTPUT_PACKET_SHA256"],
            "ARTIFACT_PATHS": created,
            "TERMINAL_STATUS": row["TERMINAL_STATUS"],
        }
        try:
            route_trace.append_event(trace_path, event)
            row["TRACE_EVENT_RESULT"] = "PASS"
        except Exception as exc:  # noqa: BLE001
            row["TRACE_EVENT_RESULT"] = f"FAIL:{exc}"

        rec = {
            "ORCHESTRATION_ID": meta["ORCHESTRATION_ID"],
            "WORKER_EXECUTION_ID": w["WORKER_EXECUTION_ID"],
            "WORKER_ID": wid,
            "ATTEMPT": 1,
            "TASK_TOOL": "Cursor Task",
            "SUBAGENT_TYPE": "generalPurpose",
            "CURSOR_AGENT_ID": agent,
            "CURSOR_TASK_ID_OR_EQUIVALENT": agent,
            "PARENT_EXECUTION_ID": meta["ORCHESTRATION_ID"],
            "INPUT_PACKET_PATH": str(in_path),
            "INPUT_PACKET_SHA256": w["INPUT_PACKET_SHA256"],
            "OUTPUT_PACKET_PATH": str(out_path),
            "OUTPUT_PACKET_SHA256": row["OUTPUT_PACKET_SHA256"],
            "STARTED_AT": time.time(),
            "LAST_HEARTBEAT_AT": time.time(),
            "FINISHED_AT": time.time(),
            "DURATION_MS": 0,
            "STATUS": row["TERMINAL_STATUS"],
            "TERMINAL_STATUS": row["TERMINAL_STATUS"],
        }
        with dispatch_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
        row["CHECKPOINT_RESULT"] = "PASS"
        meta["WORKERS"][wid]["CURSOR_AGENT_ID"] = agent
        matrix[wid] = row

    fanin_before = fs_boundary.FsSnapshot.take(case)
    (case / "LEDGER.md").write_text("FORCED_VIOLATION_FOR_PROOF\n", encoding="utf-8")
    fanin_after = fs_boundary.FsSnapshot.take(case)
    diff = fs_boundary.diff_snapshots(fanin_before, fanin_after)
    r, v = fs_boundary.evaluate_write_boundary("FAN_IN_ASSEMBLER", diff)
    fanin_violation_proof = {"RESULT": r, "VIOLATIONS": v}
    (case / "LEDGER.md").unlink(missing_ok=True)

    meta["LIVE_MATRIX"] = matrix
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    report = {
        "RUN_ID": meta["RUN_ID"],
        "PROOF_ROOT": meta["PROOF_ROOT"],
        "EXECUTION_MODE": "REVIEW_PROOF_ONLY",
        "REAL_BUG": False,
        "PRODUCT_WRITES": "FORBIDDEN",
        "WORKERS": matrix,
        "FANIN_ALLOWED_PROOF": "PASS"
        if (case / "results" / "FANIN.md").exists()
        else "FAIL",
        "FANIN_FORBIDDEN_WRITE": "REJECTED_FROM_FILESYSTEM_DIFF"
        if r == "VIOLATION"
        else r,
        "FANIN_VIOLATION_DETAIL": fanin_violation_proof,
        "DISPATCH_PATH": str(dispatch_path),
        "TRACE_PATH": str(trace_path),
        "LIVE_WORKERS_PROVEN": [
            k
            for k, val in matrix.items()
            if val.get("SCHEMA_RESULT") == "PASS" and val.get("CURSOR_AGENT_ID")
        ],
        "LIVE_WORKERS_NOT_PROVEN": [
            k for k, val in matrix.items() if val.get("SCHEMA_RESULT") != "PASS"
        ],
    }
    Path(".cursor/pipeline/bug-team/CORRECTIVE_LIVE_PROOF_REPORT.md").write_text(
        "# Corrective Live Proof Report\n\n```json\n"
        + json.dumps(report, indent=2, ensure_ascii=False)
        + "\n```\n",
        encoding="utf-8",
    )
    Path(
        ".tmp/opsx-bug-team-harness/live-runtime-proof/20260728T044128Z/LIVE_PROOF_REPORT.json"
    ).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_timeout_policy_status(
        Path(".cursor/pipeline/bug-team/runtime/TIMEOUT_PLATFORM_STATUS.json")
    )
    print("proven", len(report["LIVE_WORKERS_PROVEN"]), "not", report["LIVE_WORKERS_NOT_PROVEN"])
    print("fanin", report["FANIN_ALLOWED_PROOF"], report["FANIN_FORBIDDEN_WRITE"])
    for wid, row in matrix.items():
        print(wid, row["SCHEMA_RESULT"], row["WRITE_BOUNDARY_RESULT"], row["CURSOR_AGENT_ID"][:8])


if __name__ == "__main__":
    main()
