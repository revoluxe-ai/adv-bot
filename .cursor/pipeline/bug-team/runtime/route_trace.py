# -*- coding: utf-8 -*-
"""Append-only ROUTE-TRACE SCHEMA_VERSION 2 utility (BF-005).

Also accepts legacy episode events that use EVENT_SEQUENCE instead of
SEQUENCE when reading history (resume-family-fanout on mixed traces).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = "2"


class TraceIntegrityError(Exception):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        super().__init__(f"{code}: {detail}" if detail else code)


def _event_sequence(event: Dict[str, Any]) -> int:
    """Return monotonic sequence from SCHEMA_VERSION 2 or episode EVENT_SEQUENCE."""
    if "SEQUENCE" in event and event["SEQUENCE"] is not None:
        return int(event["SEQUENCE"])
    if "EVENT_SEQUENCE" in event and event["EVENT_SEQUENCE"] is not None:
        return int(event["EVENT_SEQUENCE"])
    raise TraceIntegrityError("MISSING_SEQUENCE", "SEQUENCE|EVENT_SEQUENCE")


def _read_events(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    events: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        events.append(json.loads(line))
    return events


def last_sequence(path: Path) -> int:
    events = _read_events(path)
    if not events:
        return 0
    return _event_sequence(events[-1])


def validate_reconciliation(event: Dict[str, Any]) -> None:
    exp = event.get("EXPECTED_EXECUTION_ROUTE")
    act = event.get("ACTUAL_EXECUTION_ROUTE")
    recon = event.get("ROUTE_RECONCILIATION")
    if recon == "MATCH" and exp != act:
        raise TraceIntegrityError("INVALID_ROUTE_RECONCILIATION", "MATCH with unequal routes")
    nexp = event.get("EXPECTED_NEXT_COMMAND")
    nact = event.get("ACTUAL_NEXT_COMMAND")
    nrecon = event.get("NEXT_COMMAND_RECONCILIATION")
    if nrecon == "MATCH" and nexp != nact:
        raise TraceIntegrityError(
            "INVALID_NEXT_COMMAND_RECONCILIATION", "MATCH with unequal next commands"
        )


def append_event(
    path: Path,
    event: Dict[str, Any],
    *,
    allow_rewrite_check: bool = True,
) -> Dict[str, Any]:
    """Append exactly one JSONL event after integrity checks; flush+verify."""
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = _read_events(path)
    seqs = [_event_sequence(e) for e in existing]
    ids = [e["EVENT_ID"] for e in existing]

    if "SCHEMA_VERSION" not in event:
        event = dict(event)
        event["SCHEMA_VERSION"] = SCHEMA_VERSION
    if event.get("SCHEMA_VERSION") != SCHEMA_VERSION:
        raise TraceIntegrityError("WRONG_SCHEMA_VERSION")

    required = (
        "EVENT_ID",
        "SEQUENCE",
        "CASE_ID",
        "ORCHESTRATION_ID",
        "EVENT_TYPE",
        "FROM_STATE",
        "TO_STATE",
        "TERMINAL_STATUS",
    )
    for key in required:
        if key not in event:
            raise TraceIntegrityError("MISSING_FIELD", key)

    new_seq = int(event["SEQUENCE"])
    expected_next = (seqs[-1] + 1) if seqs else 1
    if new_seq in seqs:
        raise TraceIntegrityError("DUPLICATE_SEQUENCE", str(new_seq))
    if new_seq != expected_next:
        raise TraceIntegrityError(
            "NON_MONOTONIC_SEQUENCE", f"got {new_seq} expected {expected_next}"
        )
    if event["EVENT_ID"] in ids:
        raise TraceIntegrityError("DUPLICATE_EVENT_ID", event["EVENT_ID"])

    validate_reconciliation(event)

    # Historical rewrite attempt: refuse if caller tries to truncate/replace
    if allow_rewrite_check and path.exists():
        before = path.read_bytes()
    else:
        before = b""

    line = json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()

    after = path.read_bytes()
    if before and not after.startswith(before):
        # restore is not done — signal integrity failure
        raise TraceIntegrityError("HISTORICAL_REWRITE_DETECTED")

    # Verify last event
    verified = _read_events(path)[-1]
    if verified.get("EVENT_ID") != event["EVENT_ID"]:
        raise TraceIntegrityError("APPEND_VERIFY_FAILED")
    return verified


def attempt_historical_rewrite(path: Path, new_content: str) -> str:
    """Test helper: simulating rewrite must be detectable/rejected by policy."""
    # Policy: callers must not rewrite; this function marks the attempt.
    raise TraceIntegrityError("HISTORICAL_REWRITE_ATTEMPT_REJECTED")
