"""Test-only NDJSON-лог для ручных прогонов calibration (не импортировать из app/).

Пишет ``calibration_debug.log`` рядом с этим файлом; ``*.log`` в .gitignore.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_LOG_PATH = Path(__file__).resolve().parent / "calibration_debug.log"


def write_calibration_debug_log(
    *,
    location: str,
    message: str,
    data: dict[str, Any],
    hypothesis_id: str,
    run_id: str = "debug-run",
) -> None:
    """Append one NDJSON line; ошибки I/O игнорируются."""
    try:
        payload = {
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with _LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError:
        pass
