# -*- coding: utf-8 -*-
"""Orchestrator prepare script: MATERIALIZER hop for INTAKE-001 item 3."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
BUG_TEAM_ROOT = REPO_ROOT / ".cursor" / "pipeline" / "bug-team"
sys.path.insert(0, str(BUG_TEAM_ROOT))

from runtime import activation, live_task_hop  # noqa: E402

CASE_ID = "BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z"
CASE_ROOT = REPO_ROOT / ".opsx" / "runs" / "bug-cases" / CASE_ID
OUT_PATH = CASE_ROOT / "team" / "prepare_materializer_item3.result.json"

RAW_INTAKE_TEXT = (
    "Independent READ_ONLY review of uncommitted dirty promobonus rebuild. "
    "Six findings. No production migration. No commit/push/PR.\n\n"
    "HIGH:\n"
    "1. auto_shelf_bid_control_view_provider.py:881 — Telegram rec-bid uses "
    "get_effective_promo_plan(adv) without promo_fraction/ComplexAdv\n"
    "2. promo_state_service.py:127-201 — get_campaign_balance failure still "
    "redis.set with pool_usable=false (false empty pool, not stale->M=1)\n"
    "3. promo_ledger.py 90-day lookback drops campaign remaining -> false AND-stop "
    "vs Owner availability law\n"
    "4. promo_accounting.py FEFO applies spend to expired tranches first, "
    "inflating live remaining\n\n"
    "MEDIUM:\n"
    "5. campaign leftover fraction uses budget_after/total so M collapses\n"
    "6. journal only bot WBAutoBudgetTopUp; manual WB promo deposits invisible"
)

PAYLOAD = {
    "AFFECTED_AREA_CANDIDATE": "promo_ledger.py",
    "ALLOWED_INPUT_ARTIFACTS": [
        "intakes/INTAKE-001.md",
        "CASE.md",
        "LEDGER.md",
        "INDEX.md",
        "findings/ROOT-001.md",
        "findings/FINDING-002.md",
        "findings/HC-001.md",
        "results/OWNER-CLOSURE-ROOT-001.md",
        "results/OWNER-CLOSURE-FINDING-002.md",
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
    "CREATE_ROOT_FINDING": False,
    "CURRENT_CHAT_CONTEXT": (
        "CASE_RESUME of BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z. "
        "INTAKE-001 already recorded. ROOT-001 closed_fixed (do not reopen). "
        "FINDING-002 closed_fixed (do not reopen). HC-001 closed_fixed / "
        "INTEGRATED (do not reopen). Sequential max_active_findings=1. "
        "Materialize only HIGH item 3 as FINDING-003. Leave items 4-6 on "
        "intake residual. Do not classify. Do not fix."
    ),
    "DO_NOT_CREATE_FINDINGS_4_TO_6": True,
    "DO_NOT_CREATE_NEW_CASE": True,
    "DO_NOT_REOPEN_ROOT_001": True,
    "DO_NOT_REOPEN_FINDING_002": True,
    "DO_NOT_REOPEN_HC_001": True,
    "DO_NOT_TREAT_AS_NEW_RAW_REPORT": True,
    "DUPLICATE_SEARCH_ROOT": ".opsx/runs/bug-cases",
    "EXISTING_CASE_ID": CASE_ID,
    "EXPECTED_CHAT_REQUIRED": True,
    "EXPECTED_FINDING_ID": "FINDING-003",
    "EXPECTED_STATUS": "available",
    "INTAKE_ID": "INTAKE-001",
    "INVOCATION_MODE": "CASE_RESUME",
    "ITEM_TEXT": (
        "promo_ledger.py 90-day lookback drops campaign remaining -> "
        "false AND-stop vs Owner availability law"
    ),
    "ITEM_TO_MATERIALIZE": 3,
    "MAPS_TO": "/opsx-materialize-bug-queue mode=update",
    "MATERIALIZE_COUNT": 1,
    "MAX_ACTIVE_FINDINGS": 1,
    "MODE": "CASE_RESUME_UPDATE",
    "ON_BLOCKED": "stop",
    "PRIOR_FINDING_ID": "FINDING-002",
    "PRIOR_FINDING_STATUS": "closed_fixed",
    "CLOSED_FINDING_IDS": ["ROOT-001", "FINDING-002", "HC-001"],
    "RAW_INTAKE_HASH": "637477c63f7498ef1f0f6201bd2408e6548154bac9cc32b85336c40032261794",
    "RAW_INTAKE_PATH": "intakes/INTAKE-001.md",
    "RAW_INTAKE_RECEIVED_AT": "2026-09-07T09:52:00Z",
    "RAW_INTAKE_SOURCE": "EXISTING_ARTIFACT",
    "RAW_INTAKE_TEXT": RAW_INTAKE_TEXT,
    "REQUIRE_CLAIM": True,
    "RESIDUAL_AFTER_THIS_ITEM": [4, 5, 6],
    "WORKER_ID": "MATERIALIZER",
}


def main() -> None:
    gate_status, gate_details = activation.check_invocation_gate(
        execution_mode="CONTROLLED_LIVE_UNCOMMITTED",
        proof_root=CASE_ROOT,
    )
    result: dict = {
        "GATE_STATUS": gate_status,
        "GATE_DETAILS": gate_details,
    }
    if gate_status != "ACTIVE_ALLOWED":
        OUT_PATH.write_text(
            json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
        )
        raise SystemExit(2)

    try:
        prep = live_task_hop.prepare_live_hop(
            case_root=CASE_ROOT,
            orchestration_id="ORCH/sup-promo-t07-d07",
            worker_id="MATERIALIZER",
            case_id=CASE_ID,
            finding_id=None,
            execution_mode="CONTROLLED_LIVE_UNCOMMITTED",
            checkpoint_generation=35,
            packet_generation=1,
            payload=PAYLOAD,
            attempt=1,
            proof_root=CASE_ROOT,
        )
        result["PREPARE"] = prep
    except live_task_hop.LiveHopError as exc:
        result["PREPARE_ERROR"] = {
            "CODE": exc.code,
            "DETAIL": exc.detail,
            "PAYLOAD": exc.payload,
        }
        OUT_PATH.write_text(
            json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
        )
        raise SystemExit(3)

    OUT_PATH.write_text(
        json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
