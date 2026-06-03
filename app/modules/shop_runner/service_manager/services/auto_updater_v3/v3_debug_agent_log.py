"""NDJSON-логи debug-сессии V3 calibration (временно, для верификации ×2/÷2)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_SESSION_ID = "de9fc0"
_LOG_NAME = "debug-de9fc0.log"


def _log_path() -> Path:
    cwd = Path.cwd()
    if (cwd / "app").is_dir():
        return cwd / _LOG_NAME
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "app").is_dir() and parent.name != "app":
            return parent / _LOG_NAME
    return cwd / _LOG_NAME


def v3_agent_debug_log(
    *,
    location: str,
    message: str,
    data: dict[str, Any],
    hypothesis_id: str,
    run_id: str = "debug-run",
) -> None:
    """Append one NDJSON line; ошибки I/O игнорируются."""
    try:
        path = _log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "sessionId": _SESSION_ID,
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError:
        pass
