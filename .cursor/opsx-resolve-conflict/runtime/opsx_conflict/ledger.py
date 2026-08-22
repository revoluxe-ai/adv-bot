"""Append-only execution ledger with R11 prepared-terminal semantics."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Mapping

from .errors import PolicyViolation, StopRequired
from .hashutil import sha256_canonical

LEDGER_SCHEMA = "opsx-resolve-conflict/v2"

ALLOWED_TRANSITIONS = {
    "RUN_START": {"STATE_CAPTURED", "STOP"},
    "STATE_CAPTURED": {"SCOPE_FROZEN", "STOP"},
    "SCOPE_FROZEN": {"AUTHORITY_RESOLVED", "STOP"},
    "AUTHORITY_RESOLVED": {"UNIT_PLANNED", "STOP"},
    "UNIT_PLANNED": {"WRITE_DONE", "STOP"},
    "WRITE_DONE": {"WRITE_DONE", "CHECK_DONE", "STOP"},
    "CHECK_DONE": {"CHECK_DONE", "STAGE_DONE", "STOP"},
    "STAGE_DONE": {
        "UNIT_PLANNED",
        "CANCELLATION_BARRIER_CLOSED",
        "CONTINUE_DONE",
        "STOP",
    },
    "CONTINUE_DONE": {"RUN_FINALIZED", "STATE_CAPTURED", "STOP"},
    "RUN_FINALIZED": {"LEDGER_FINALIZED", "STOP"},
    "STOP": {"LEDGER_FINALIZED", "CANCELLATION_BARRIER_CLOSED"},
    "CANCELLATION_BARRIER_CLOSED": {
        "TERMINAL_PREPARED",
        "RUN_FINALIZED",
        "LEDGER_FINALIZED",
        "STOP",
    },
    "TERMINAL_PREPARED": {"LEDGER_FINALIZED", "STOP"},
    "LEDGER_FINALIZED": set(),
}


class ExecutionLedger:
    """Hash-chained ledger; verify_ledger enforces prev_hash links and transitions."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.prev_hash = "0" * 64
        self.last_event = "RUN_START"
        self.last_payload: dict[str, Any] = {}
        self.finalized = False
        self.seq = 0
        if self.path.exists():
            self._replay()

    def _replay(self) -> None:
        prev = "0" * 64
        last = "RUN_START"
        finalized = False
        seq = 0
        last_payload: dict[str, Any] = {}
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            body = {k: v for k, v in rec.items() if k != "record_hash"}
            if body.get("prev_hash") != prev:
                raise StopRequired(
                    "LEDGER_PREV_HASH_MISMATCH",
                    {"expected_prev": prev, "got": body.get("prev_hash"), "seq": seq},
                )
            expect = sha256_canonical(body)
            if rec.get("record_hash") != expect:
                raise StopRequired("LEDGER_HASH_MISMATCH", {"seq": seq})
            event = body["event"]
            seq += 1
            if event.startswith("COMMAND_") or event.startswith("META_"):
                prev = rec["record_hash"]
                continue
            allowed = ALLOWED_TRANSITIONS.get(last, set())
            if event not in allowed:
                raise StopRequired("LEDGER_ILLEGAL_TRANSITION", {"from": last, "to": event})
            prev = rec["record_hash"]
            last = event
            last_payload = dict(body.get("payload", {}))
            if event == "LEDGER_FINALIZED":
                finalized = True
        self.prev_hash = prev
        self.last_event = last
        self.finalized = finalized
        self.seq = seq
        self.last_payload = last_payload

    def append(self, event: str, payload: Mapping[str, Any] | None = None) -> str:
        if self.finalized:
            raise PolicyViolation("ledger already finalized")
        if not (event.startswith("COMMAND_") or event.startswith("META_")):
            if self.prev_hash != "0" * 64 or self.last_event != "RUN_START":
                allowed = ALLOWED_TRANSITIONS.get(self.last_event, set())
                if event not in allowed:
                    raise StopRequired(
                        "LEDGER_ILLEGAL_TRANSITION",
                        {"from": self.last_event, "to": event},
                    )
            elif event != "STATE_CAPTURED" and event != "RUN_START" and event != "STOP":
                if self.last_event == "RUN_START" and event not in ALLOWED_TRANSITIONS["RUN_START"]:
                    raise StopRequired(
                        "LEDGER_ILLEGAL_TRANSITION",
                        {"from": self.last_event, "to": event},
                    )
        body = {
            "schema": LEDGER_SCHEMA,
            "ts_ns": time.time_ns(),
            "seq": self.seq,
            "event": event,
            "payload": dict(payload or {}),
            "prev_hash": self.prev_hash,
        }
        digest = sha256_canonical(body)
        rec = {**body, "record_hash": digest}
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=True, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        self.prev_hash = digest
        self.seq += 1
        if not event.startswith("COMMAND_") and not event.startswith("META_"):
            self.last_event = event
            self.last_payload = dict(payload or {})
        if event == "LEDGER_FINALIZED":
            self.finalized = True
        return digest


def verify_ledger(path: Path) -> dict[str, Any]:
    """Validate hash chain (including prev_hash links), transitions, finalized state."""
    ledger = ExecutionLedger(path)
    if not ledger.finalized:
        raise StopRequired("LEDGER_NOT_FINALIZED")
    return {
        "ledger_final_hash": ledger.prev_hash,
        "LEDGER_FINALIZED": True,
        "last_event": ledger.last_event,
        "record_count": ledger.seq,
    }
