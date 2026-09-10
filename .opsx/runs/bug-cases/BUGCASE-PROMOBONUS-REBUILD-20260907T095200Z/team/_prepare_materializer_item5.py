# -*- coding: utf-8 -*-
"""Prepare MATERIALIZER hop for INTAKE-001 item 5 (CASE_RESUME)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / ".cursor" / "pipeline" / "bug-team"))

from runtime.activation import activation_state_hash, check_invocation_gate
from runtime.live_task_hop import LiveHopError, prepare_live_hop

CASE_ID = "BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z"
CASE_ROOT = ROOT / ".opsx" / "runs" / "bug-cases" / CASE_ID
OUT_PATH = CASE_ROOT / "team" / "_prepare_materializer_item5.result.json"

RAW_INTAKE_TEXT = (
    "Independent READ_ONLY review of uncommitted dirty promobonus rebuild. "
    "Six findings. No production migration. No commit/push/PR.\n\n"
    "HIGH:\n"
    "1. auto_shelf_bid_control_view_provider.py:881 -- Telegram rec-bid uses "
    "get_effective_promo_plan(adv) without promo_fraction/ComplexAdv\n"
    "2. promo_state_service.py:127-201 -- get_campaign_balance failure still "
    "redis.set with pool_usable=false (false empty pool, not stale->M=1)\n"
    "3. promo_ledger.py 90-day lookback drops campaign remaining -> false "
    "AND-stop vs Owner availability law\n"
    "4. promo_accounting.py FEFO applies spend to expired tranches first, "
    "inflating live remaining\n\n"
    "MEDIUM:\n"
    "5. campaign leftover fraction uses budget_after/total so M collapses\n"
    "6. journal only bot WBAutoBudgetTopUp; manual WB promo deposits invisible"
)


def main() -> int:
    gate_status, gate_details = check_invocation_gate(
        execution_mode="CONTROLLED_LIVE_UNCOMMITTED",
        proof_root=CASE_ROOT,
    )
    if gate_status.startswith("BLOCKED_"):
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

    payload = {
        "AFFECTED_AREA_CANDIDATE": "campaign leftover fraction (budget_after/total)",
        "ALLOWED_INPUT_ARTIFACTS": [
            "intakes/INTAKE-001.md",
            "CASE.md",
            "LEDGER.md",
            "INDEX.md",
            "findings/ROOT-001.md",
            "findings/FINDING-002.md",
            "findings/HC-001.md",
            "findings/FINDING-003.md",
            "findings/FINDING-004.md",
            "findings/HC-FINDING-004-STALE-TEST.md",
            "results/OWNER-CLOSURE-ROOT-001.md",
            "results/OWNER-CLOSURE-FINDING-002.md",
            "results/OWNER-CLOSURE-FINDING-003.md",
            "results/OWNER-CLOSURE-FINDING-004.md",
            "results/HUMAN_SUMMARY.md",
            ".cursor/pipeline/bug-team/workers/MATERIALIZER.md",
            ".cursor/pipeline/bug-team/WRITE_BOUNDARY.md",
            ".cursor/commands/opsx-materialize-bug-queue.md",
            ".cursor/pipeline/bug-team/packets/WORKER_IO.md",
            ".cursor/pipeline/bug-team/packets/RAW_INTAKE.md",
        ],
        "CHAT_LABEL": "SUP-PROMO-FIX-20260907",
        "CLAIMABLE": True,
        "CLAIM_PRIORITY": 3,
        "CLOSED_FINDING_IDS": [
            "ROOT-001",
            "FINDING-002",
            "HC-001",
            "FINDING-003",
            "FINDING-004",
            "HC-FINDING-004-STALE-TEST",
        ],
        "CREATE_ROOT_FINDING": False,
        "CURRENT_CHAT_CONTEXT": (
            "CASE_RESUME of BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z. "
            "INTAKE-001 already recorded. ROOT-001 closed_fixed (do not reopen). "
            "FINDING-002 closed_fixed (do not reopen). "
            "HC-001 closed_fixed / INTEGRATED (do not reopen). "
            "FINDING-003 closed_false_positive / Route C (do not reopen). "
            "FINDING-004 closed_fixed (do not reopen). "
            "HC-FINDING-004-STALE-TEST closed_fixed / INTEGRATED (do not reopen). "
            "Sequential max_active_findings=1. Materialize only MEDIUM item 5 as "
            "FINDING-005. Leave item 6 on intake residual. Do not classify. Do not fix."
        ),
        "DO_NOT_CREATE_FINDING_006": True,
        "DO_NOT_CREATE_NEW_CASE": True,
        "DO_NOT_REOPEN_FINDING_002": True,
        "DO_NOT_REOPEN_FINDING_003": True,
        "DO_NOT_REOPEN_FINDING_004": True,
        "DO_NOT_REOPEN_HC_001": True,
        "DO_NOT_REOPEN_HC_FINDING_004_STALE_TEST": True,
        "DO_NOT_REOPEN_ROOT_001": True,
        "DO_NOT_TREAT_AS_NEW_RAW_REPORT": True,
        "DUPLICATE_SEARCH_ROOT": ".opsx/runs/bug-cases",
        "EXISTING_CASE_ID": CASE_ID,
        "EXPECTED_CHAT_REQUIRED": True,
        "EXPECTED_FINDING_ID": "FINDING-005",
        "EXPECTED_STATUS": "available",
        "INTAKE_ID": "INTAKE-001",
        "INVOCATION_MODE": "CASE_RESUME",
        "ITEM_TEXT": "campaign leftover fraction uses budget_after/total so M collapses",
        "ITEM_TO_MATERIALIZE": 5,
        "MAPS_TO": "/opsx-materialize-bug-queue mode=update",
        "MATERIALIZE_COUNT": 1,
        "MAX_ACTIVE_FINDINGS": 1,
        "MODE": "CASE_RESUME_UPDATE",
        "ON_BLOCKED": "stop",
        "PRIOR_FINDING_ID": "FINDING-004",
        "PRIOR_FINDING_STATUS": "closed_fixed",
        "RAW_INTAKE_HASH": "637477c63f7498ef1f0f6201bd2408e6548154bac9cc32b85336c40032261794",
        "RAW_INTAKE_PATH": "intakes/INTAKE-001.md",
        "RAW_INTAKE_RECEIVED_AT": "2026-09-07T09:52:00Z",
        "RAW_INTAKE_SOURCE": "EXISTING_ARTIFACT",
        "RAW_INTAKE_TEXT": RAW_INTAKE_TEXT,
        "REQUIRE_CLAIM": True,
        "RESIDUAL_AFTER_THIS_ITEM": [6],
        "WORKER_ID": "MATERIALIZER",
    }

    try:
        result = prepare_live_hop(
            case_root=CASE_ROOT,
            orchestration_id="ORCH/sup-promo-t10-d10",
            worker_id="MATERIALIZER",
            case_id=CASE_ID,
            finding_id=None,
            execution_mode="CONTROLLED_LIVE_UNCOMMITTED",
            checkpoint_generation=62,
            packet_generation=1,
            payload=payload,
            attempt=1,
            proof_root=CASE_ROOT,
        )
    except LiveHopError as exc:
        OUT_PATH.write_text(
            json.dumps(
                {
                    "STATUS": exc.code,
                    "DETAIL": exc.detail,
                    "PAYLOAD": exc.payload,
                    "GATE_STATUS": gate_status,
                    "ACTIVATION_STATE_HASH": activation_state_hash(),
                },
                indent=2,
                ensure_ascii=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return 1

    result["GATE_STATUS"] = gate_status
    result["ACTIVATION_STATE_HASH"] = activation_state_hash()
    OUT_PATH.write_text(
        json.dumps(result, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
