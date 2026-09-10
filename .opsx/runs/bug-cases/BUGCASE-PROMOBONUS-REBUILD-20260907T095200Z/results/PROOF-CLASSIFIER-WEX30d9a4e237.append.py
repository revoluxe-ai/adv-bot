# Append one ROUTE-TRACE event for CLASSIFIER WEX/CLASSIFIER/30d9a4e237.
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / ".cursor" / "pipeline" / "bug-team" / "runtime"))

from route_trace import append_event  # noqa: E402

CASE = ROOT / ".opsx" / "runs" / "bug-cases" / "BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z"
event_path = CASE / "results" / "PROOF-CLASSIFIER-WEX30d9a4e237.event.json"
trace_path = CASE / "results" / "ROUTE-TRACE.jsonl"

event = json.loads(event_path.read_text(encoding="utf-8"))
verified = append_event(trace_path, event)
print("APPENDED")
print(verified.get("EVENT_ID"))
print(verified.get("SEQUENCE"))
