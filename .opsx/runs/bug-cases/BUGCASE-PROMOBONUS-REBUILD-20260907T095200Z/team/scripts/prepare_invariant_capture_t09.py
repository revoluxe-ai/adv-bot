# -*- coding: utf-8 -*-
"""Prepare INVARIANT_CAPTURE_WORKER hop for FINDING-004 resume-family-fanout."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / ".cursor" / "pipeline" / "bug-team"))

from runtime import activation, live_task_hop  # noqa: E402

CASE_ID = "BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z"
CASE_ROOT = ROOT / ".opsx" / "runs" / "bug-cases" / CASE_ID
ORCH = "ORCH/sup-promo-t09-d09"
WORKER_ID = "INVARIANT_CAPTURE_WORKER"
OUT_PATH = Path(__file__).with_name("prepare_invariant_capture_t09.result.json")


def main() -> int:
    gate_status, gate_details = activation.check_invocation_gate(
        execution_mode="CONTROLLED_LIVE_UNCOMMITTED",
        proof_root=CASE_ROOT,
    )
    if gate_status != "ACTIVE_ALLOWED":
        OUT_PATH.write_text(
            json.dumps(
                {"STATUS": gate_status, "DETAILS": gate_details},
                indent=2,
                ensure_ascii=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return 2

    packets_dir = CASE_ROOT / "team" / "packets"
    dep = {
        "PKT/WEX/GREEN_VERIFIER/ce96b5a340/OUT": packets_dir
        / "WEX_GREEN_VERIFIER_ce96b5a340.out.json",
        "PKT/WEX/BOUNDED_HUNTER/4e8665d743/OUT": packets_dir
        / "WEX_BOUNDED_HUNTER_4e8665d743.out.json",
        "PKT/WEX/FAN_IN_ASSEMBLER/f588de6e82/OUT": packets_dir
        / "WEX_FAN_IN_ASSEMBLER_f588de6e82.out.json",
    }
    payload = {
        "WORKER_ID": WORKER_ID,
        "MODE": "resume-family-fanout",
        "MAPS_TO": "post-root-GREEN invariant capture",
        "FINDING_ID": "FINDING-004",
        "ROOT_FINDING_ID": "FINDING-004",
        "INVARIANT_ID": (
            "INV/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/"
            "FINDING-004/FEFO-SPEND-SKIP-EXPIRED"
        ),
        "BUG_FAMILY_ID": (
            "BFAM/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/"
            "FINDING-004/FEFO-SPEND-SKIP-EXPIRED"
        ),
        "INVARIANT_CANDIDATE": (
            "apply_spend_fefo must not apply spend to expired leftover before "
            "live leftover; expired 300 + live 200 + spend 50 must yield remaining 150."
        ),
        "ROOT_CAUSE": (
            "apply_spend_fefo sorted dated leftover FEFO and applied spend without "
            "skipping is_expired, so expired leftover absorbed spend and live remaining inflated."
        ),
        "ROOT_FIX": (
            "In the spend loop, continue when is_expired(item.expires_at, now=now)."
        ),
        "RED_EVIDENCE": "results/RED-FINDING-004.md",
        "ROOT_FIX_EVIDENCE": "results/FIX-FINDING-004.md",
        "ROOT_GREEN_EVIDENCE": "results/GREEN-FINDING-004.md",
        "FROZEN_TEST_NODE": (
            "tests/unit/wb/utils/test_promo_accounting.py::"
            "test_fefo_spend_hits_live_leftover_not_expired"
        ),
        "FROZEN_TEST_SHA256": (
            "cd926666fd7fcd2f958440220a58e1a6ff621fb8b839b518133ee0084ffc67b2"
        ),
        "HUNT_ALREADY_COMPLETE": True,
        "OPEN_CANDIDATE_PATH": "findings/HC-FINDING-004-STALE-TEST.md",
        "CLOSED_FAMILY_SNAPSHOT_DIR": "family/closed/FINDING-002/",
        "PRESERVE_CLOSED_FAMILY_ROOT_001": True,
        "PRESERVE_CLOSED_FAMILY_FINDING_002": True,
        "DO_NOT_OVERWRITE_CLOSED_SNAPSHOT_ROOT_001": True,
        "DO_NOT_REOPEN_ROOT_001": True,
        "DO_NOT_REOPEN_FINDING_002": True,
        "DO_NOT_REOPEN_HC_001": True,
        "DO_NOT_REOPEN_FINDING_003": True,
        "DO_NOT_START_HC_FINDING_004_RED": True,
        "DO_NOT_START_ITEMS_5_TO_6": True,
        "DO_NOT_CLASSIFY_RELATION": True,
        "RERUN_ROOT_IMPLEMENTATION": False,
        "REUSE_ROOT_GREEN": True,
        "FAMILY_STATUS_AFTER": "HUNTING",
        "NEXT_WORKER_AFTER_PASS": "RELATION_CLASSIFIER",
        "MAX_ACTIVE_FINDINGS": 1,
    }
    try:
        prep = live_task_hop.prepare_live_hop(
            case_root=CASE_ROOT,
            orchestration_id=ORCH,
            worker_id=WORKER_ID,
            case_id=CASE_ID,
            finding_id="FINDING-004",
            execution_mode="CONTROLLED_LIVE_UNCOMMITTED",
            checkpoint_generation=51,
            packet_generation=1,
            dependency_packets=dep,
            payload=payload,
            attempt=1,
            parent_packet_id="PKT/WEX/FAN_IN_ASSEMBLER/f588de6e82/OUT",
            proof_root=CASE_ROOT,
        )
    except live_task_hop.LiveHopError as exc:
        OUT_PATH.write_text(
            json.dumps(
                {
                    "STATUS": exc.code,
                    "DETAIL": exc.detail,
                    "PAYLOAD": exc.payload,
                    "GATE_STATUS": gate_status,
                },
                indent=2,
                ensure_ascii=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return 3

    toctou = live_task_hop.validate_dispatch_intent_before_task(
        case_root=CASE_ROOT,
        dispatch_intent_path=Path(prep["DISPATCH_INTENT_PATH"]),
    )
    started = live_task_hop.mark_task_started(Path(prep["DISPATCH_INTENT_PATH"]))
    result = {
        "GATE_STATUS": gate_status,
        "GATE_DETAILS": gate_details,
        "PREP": prep,
        "TOCTOU": toctou,
        "INTENT_STATUS": started.get("STATUS"),
        "WORKER_EXECUTION_ID": prep["WORKER_EXECUTION_ID"],
        "INPUT_PACKET_PATH": prep["INPUT_PACKET_PATH"],
        "EXPECTED_OUTPUT_PATH": prep["EXPECTED_OUTPUT_PATH"],
        "DISPATCH_INTENT_PATH": prep["DISPATCH_INTENT_PATH"],
        "TIMEOUT_SECONDS": prep["TIMEOUT_SECONDS"],
        "TASK_ARGS": prep["TASK_ARGS"],
        "ALLOWED_WRITE_PATHS": prep["ALLOWED_WRITE_PATHS"],
    }
    OUT_PATH.write_text(
        json.dumps(result, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
