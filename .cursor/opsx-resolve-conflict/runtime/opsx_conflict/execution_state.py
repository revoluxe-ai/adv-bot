"""Durable execution state для mid-write recovery.

Role: RECOVERY_CACHE — не authoritative terminal evidence.
Terminal evidence = candidate-bound verification artifacts (verification_handoff).
Потеря ~/.opsx не делает unverified candidate verified и не меняет Git truth.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ExecutionRunState:
    """Resumable execution trace одного GO run."""

    run_id: str
    operation_fingerprint: str
    completed_paths: list[str] = field(default_factory=list)
    pending_paths: list[str] = field(default_factory=list)
    failed_path: str | None = None
    status: str = "IN_PROGRESS"
    ledger_role: str = "RECOVERY_CACHE"
    path_pre_write: dict[str, str] = field(default_factory=dict)
    path_post_write: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "opsx-resolve-conflict/execution-state/v1",
            "run_id": self.run_id,
            "operation_fingerprint": self.operation_fingerprint,
            "completed_paths": self.completed_paths,
            "pending_paths": self.pending_paths,
            "failed_path": self.failed_path,
            "status": self.status,
            "ledger_role": self.ledger_role,
            "path_pre_write": self.path_pre_write,
            "path_post_write": self.path_post_write,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def _state_root(repo_root: Path) -> Path:
    repo_id = repo_root.resolve().name
    return Path.home() / ".opsx" / "resolve-conflict" / "execution" / repo_id


def save_execution_state(repo_root: Path, state: ExecutionRunState) -> Path:
    root = _state_root(repo_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{state.run_id}.json"
    path.write_text(
        json.dumps(state.to_dict(), ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return path


def load_execution_state(repo_root: Path, run_id: str) -> ExecutionRunState | None:
    path = _state_root(repo_root) / f"{run_id}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return ExecutionRunState(
        run_id=data["run_id"],
        operation_fingerprint=data["operation_fingerprint"],
        completed_paths=list(data.get("completed_paths") or []),
        pending_paths=list(data.get("pending_paths") or []),
        failed_path=data.get("failed_path"),
        status=data.get("status", "IN_PROGRESS"),
        path_pre_write=dict(data.get("path_pre_write") or {}),
        path_post_write=dict(data.get("path_post_write") or {}),
    )
