# -*- coding: utf-8 -*-
"""Host prepare for resume-family-fanout INVARIANT_CAPTURE (T06)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / ".cursor" / "pipeline" / "bug-team"))

from runtime import activation, family_policy  # noqa: E402
from runtime.live_task_hop import (  # noqa: E402
    prepare_live_hop,
    validate_dispatch_intent_before_task,
)

CASE_ID = "BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z"
CASE_ROOT = ROOT / ".opsx" / "runs" / "bug-cases" / CASE_ID
OUT_PATH = CASE_ROOT / "team" / "scripts" / "prepare_invariant_capture_t06.result.json"


def main() -> int:
    gate_status, gate_details = activation.check_invocation_gate(
        execution_mode="CONTROLLED_LIVE_UNCOMMITTED",
        proof_root=CASE_ROOT,
    )
    fanout_status, fanout_details = family_policy.check_family_fanout_gate(
        execution_mode="CONTROLLED_LIVE_UNCOMMITTED",
        proof_root=CASE_ROOT,
    )
    envelope = {
        "INVOCATION_GATE": gate_status,
        "INVOCATION_DETAILS": gate_details,
        "FAMILY_FANOUT_GATE": fanout_status,
        "FAMILY_FANOUT_DETAILS": fanout_details,
    }
    if gate_status != "ACTIVE_ALLOWED":
        OUT_PATH.write_text(
            json.dumps(envelope, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
        )
        print(json.dumps({"STATUS": gate_status}, ensure_ascii=True))
        return 2
    if fanout_status != "FAMILY_FANOUT_ACTIVE_ALLOWED":
        OUT_PATH.write_text(
            json.dumps(envelope, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
        )
        print(json.dumps({"STATUS": fanout_status}, ensure_ascii=True))
        return 3

    green_out = CASE_ROOT / "team" / "packets" / "WEX_GREEN_VERIFIER_2770822420.out.json"
    hunter_out = CASE_ROOT / "team" / "packets" / "WEX_BOUNDED_HUNTER_9b10ba8467.out.json"
    fanin_out = CASE_ROOT / "team" / "packets" / "WEX_FAN_IN_ASSEMBLER_eaddd78ea1.out.json"

    payload = {
        "WORKER_ID": "INVARIANT_CAPTURE_WORKER",
        "MODE": "resume-family-fanout",
        "MAPS_TO": "post-root-GREEN invariant capture",
        "FINDING_ID": "FINDING-002",
        "ROOT_FINDING_ID": "FINDING-002",
        "REUSE_ROOT_GREEN": True,
        "RERUN_ROOT_IMPLEMENTATION": False,
        "ROOT_GREEN_EVIDENCE": "results/GREEN-FINDING-002.md",
        "ROOT_FIX_EVIDENCE": "results/FIX-FINDING-002.md",
        "RED_EVIDENCE": "results/RED-FINDING-002.md",
        "FROZEN_TEST_NODE": (
            "tests/unit/auto_budget_manager/test_promo_state_service.py::"
            "test_refresh_does_not_set_fresh_false_empty_pool_when_balance_fetch_fails"
        ),
        "FROZEN_TEST_SHA256": "4abf693330ccdd5b2aed034bdab31936f9e66f57d6d24669d213f718005414b5",
        "INVARIANT_ID": (
            "INV/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/"
            "FINDING-002/PROMO-POOL-FAIL-NO-FALSE-EMPTY"
        ),
        "INVARIANT_CANDIDATE": (
            "On get_campaign_balance failure, do not redis.set a fresh "
            "pool_usable=false snapshot; miss/stale -> conservative M=1."
        ),
        "ROOT_CAUSE": (
            "PromoStateService.refresh persisted a fresh Redis shop-promo-state "
            "snapshot with pool_usable=false after get_campaign_balance failed."
        ),
        "ROOT_FIX": (
            "On Exception from get_campaign_balance, leave pool_fetch_ok=False, "
            "skip RedisPromoStateManager.set, return."
        ),
        "PRESERVE_CLOSED_FAMILY_ROOT_001": True,
        "CLOSED_FAMILY_SNAPSHOT_DIR": "family/closed/ROOT-001/",
        "DO_NOT_REOPEN_ROOT_001": True,
        "DO_NOT_START_ITEMS_3_TO_6": True,
        "DO_NOT_START_HC001_RED": True,
        "MAX_ACTIVE_FINDINGS": 1,
        "OPEN_CANDIDATE_PATH": "findings/HC-001.md",
        "NEXT_WORKER_AFTER_PASS": "RELATION_CLASSIFIER",
        "FAMILY_STATUS_AFTER": "HUNTING",
        "HUNT_ALREADY_COMPLETE": True,
    }

    prep = prepare_live_hop(
        case_root=CASE_ROOT,
        orchestration_id="ORCH/sup-promo-t06-d06",
        worker_id="INVARIANT_CAPTURE_WORKER",
        case_id=CASE_ID,
        finding_id="FINDING-002",
        execution_mode="CONTROLLED_LIVE_UNCOMMITTED",
        checkpoint_generation=22,
        packet_generation=1,
        attempt=1,
        parent_packet_id="PKT/WEX/FAN_IN_ASSEMBLER/eaddd78ea1/OUT",
        dependency_packets={
            "PKT/WEX/GREEN_VERIFIER/2770822420/OUT": green_out,
            "PKT/WEX/BOUNDED_HUNTER/9b10ba8467/OUT": hunter_out,
            "PKT/WEX/FAN_IN_ASSEMBLER/eaddd78ea1/OUT": fanin_out,
        },
        payload=payload,
        proof_root=CASE_ROOT,
    )
    toctou = validate_dispatch_intent_before_task(
        case_root=CASE_ROOT,
        dispatch_intent_path=Path(prep["DISPATCH_INTENT_PATH"]),
    )
    envelope["PREPARE"] = prep
    envelope["TOCTOU"] = toctou
    OUT_PATH.write_text(json.dumps(envelope, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "STATUS": prep.get("STATUS"),
                "WORKER_EXECUTION_ID": prep.get("WORKER_EXECUTION_ID"),
                "DISPATCH_INTENT_PATH": prep.get("DISPATCH_INTENT_PATH"),
                "INPUT_PACKET_PATH": prep.get("INPUT_PACKET_PATH"),
                "EXPECTED_OUTPUT_PATH": prep.get("EXPECTED_OUTPUT_PATH"),
                "TOCTOU": toctou.get("STATUS"),
                "RESULT_PATH": str(OUT_PATH),
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
