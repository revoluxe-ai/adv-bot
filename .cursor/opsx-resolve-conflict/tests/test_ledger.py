from __future__ import annotations

import json
from pathlib import Path

import pytest

from opsx_conflict.runtime import ExecutionLedger, StopRequired, verify_ledger


def test_hash_chained_ledger_detects_tampering(isolated_state: Path) -> None:
    path = isolated_state / "ledger.jsonl"
    ledger = ExecutionLedger(path)
    ledger.append("STATE_CAPTURED", {"value": 1})
    ledger.append("SCOPE_FROZEN", {"value": 2})
    ledger.append("AUTHORITY_RESOLVED", {"value": 3})
    ledger.append("UNIT_PLANNED", {"value": 4})
    ledger.append("WRITE_DONE", {"value": 5})
    ledger.append("CHECK_DONE", {"value": 6})
    ledger.append("STAGE_DONE", {"value": 7})
    ledger.append("CONTINUE_DONE", {"value": 8})
    ledger.append("RUN_FINALIZED", {"value": 9})
    ledger.append("LEDGER_FINALIZED", {"value": 10})
    final = verify_ledger(path)
    assert len(final["ledger_final_hash"]) == 64
    assert final["LEDGER_FINALIZED"] is True

    rows = path.read_text(encoding="utf-8").splitlines()
    row = json.loads(rows[0])
    row["payload"]["value"] = 999
    rows[0] = json.dumps(row)
    path.chmod(0o600)
    path.write_text(chr(10).join(rows) + chr(10), encoding="utf-8")
    with pytest.raises(StopRequired):
        verify_ledger(path)
