"""RC-CRIT-003: ledger prev_hash chain must detect deletion/reorder."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from opsx_conflict.errors import StopRequired
from opsx_conflict.ledger import ExecutionLedger, verify_ledger


def _happy_ledger(path: Path) -> None:
    ledger = ExecutionLedger(path)
    ledger.append("STATE_CAPTURED", {"v": 1})
    ledger.append("SCOPE_FROZEN", {"v": 2})
    ledger.append("AUTHORITY_RESOLVED", {"v": 3})
    ledger.append("UNIT_PLANNED", {"v": 4})
    ledger.append("WRITE_DONE", {"v": 5})
    ledger.append("CHECK_DONE", {"v": 6})
    ledger.append("STAGE_DONE", {"v": 7})
    ledger.append("CANCELLATION_BARRIER_CLOSED", {"v": 8})
    ledger.append("RUN_FINALIZED", {"v": 9})
    ledger.append("LEDGER_FINALIZED", {"v": 10})


def test_verify_accepts_intact_chain(isolated_state: Path) -> None:
    path = isolated_state / "ok.ledger.jsonl"
    _happy_ledger(path)
    out = verify_ledger(path)
    assert out["LEDGER_FINALIZED"] is True


def test_deletion_breaks_prev_hash(isolated_state: Path) -> None:
    path = isolated_state / "del.ledger.jsonl"
    _happy_ledger(path)
    rows = path.read_text(encoding="utf-8").splitlines()
    # Drop a middle COMMAND-less semantic record (SCOPE_FROZEN)
    del rows[1]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises(StopRequired) as exc:
        verify_ledger(path)
    assert exc.value.reason in {"LEDGER_PREV_HASH_MISMATCH", "LEDGER_ILLEGAL_TRANSITION"}


def test_command_deletion_breaks_chain(isolated_state: Path) -> None:
    path = isolated_state / "cmd.ledger.jsonl"
    ledger = ExecutionLedger(path)
    ledger.append("STATE_CAPTURED", {})
    ledger.append("COMMAND_START", {"argv": ["git", "status"]})
    ledger.append("SCOPE_FROZEN", {})
    rows = path.read_text(encoding="utf-8").splitlines()
    # remove COMMAND_START
    rows = [r for r in rows if "COMMAND_START" not in r]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises(StopRequired) as exc:
        ExecutionLedger(path)
    assert exc.value.reason == "LEDGER_PREV_HASH_MISMATCH"
