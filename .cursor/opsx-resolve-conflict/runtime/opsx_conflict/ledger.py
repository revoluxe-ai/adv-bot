"""Durable resolution ledger — RECOVERY_CACHE execution trace.

Не authoritative terminal evidence. Terminal evidence = verification_handoff +
external verification packet bound to candidate_identity.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opsx_conflict.models import ResolutionLedgerEntry


def _state_root(repo_root: Path) -> Path:
    local = Path.home() / ".opsx" / "resolve-conflict" / "ledger"
    try:
        repo_id = repo_root.resolve().name
    except OSError:
        repo_id = "unknown"
    return local / repo_id


def append_ledger(
    repo_root: Path,
    run_id: str,
    entries: list[ResolutionLedgerEntry],
) -> Path:
    """Persist ledger JSONL outside repo."""

    root = _state_root(repo_root)
    root.mkdir(parents=True, exist_ok=True)
    ledger_path = root / f"{run_id}.ledger.jsonl"
    with ledger_path.open("a", encoding="utf-8") as f:
        for entry in entries:
            record = {
                "schema": "opsx-resolve-conflict/resolution-ledger/v1",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "run_id": run_id,
                **entry.to_dict(),
            }
            f.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")
    return ledger_path


def load_ledger(repo_root: Path, run_id: str) -> list[dict[str, Any]]:
    root = _state_root(repo_root)
    ledger_path = root / f"{run_id}.ledger.jsonl"
    if not ledger_path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records
