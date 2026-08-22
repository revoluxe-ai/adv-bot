# -*- coding: utf-8 -*-
"""Honest timeout / cancellation model (BF-006).

Platform discovery (Cursor IDE Task tool, 2026-07-28):
- Resume of a *running* async Task supports `interrupt=true`.
- No general process-tree kill API is exposed to the orchestrator for an
  arbitrary running Task without going through resume+interrupt.
- Python harness subprocess kill is NOT Cursor Task cancellation.

Therefore:
  CURSOR_TASK_CANCELLATION: PARTIAL (interrupt-on-resume only)
  PROCESS_TREE_TERMINATION: BLOCKED_PLATFORM_TERMINATION_LIMITATION
  SAFE_TIMEOUT_STOP: IMPLEMENTED
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Set

CURSOR_TASK_CANCELLATION = "PARTIAL_INTERRUPT_ON_RESUME"
PROCESS_TREE_TERMINATION = "BLOCKED_PLATFORM_TERMINATION_LIMITATION"
MAX_ATTEMPTS_DEFAULT = 2


@dataclass
class WorkerRuntimeState:
    worker_execution_id: str
    worker_id: str
    attempt: int
    max_attempts: int
    packet_generation: int
    checkpoint_generation: int
    status: str = "RUNNING"
    timed_out: bool = False
    cursor_agent_id: Optional[str] = None


@dataclass
class TimeoutController:
    """Safe timeout stop without claiming full process-tree kill."""

    timed_out_wex: Set[str] = field(default_factory=set)
    process_tree_terminated_claim: bool = False  # must stay False unless platform proves

    def mark_timeout(self, state: WorkerRuntimeState, reason: str = "heartbeat_expired") -> Dict[str, Any]:
        state.status = "TIMEOUT"
        state.timed_out = True
        self.timed_out_wex.add(state.worker_execution_id)
        return {
            "STATUS": "TIMEOUT",
            "TERMINAL_STATUS": "TIMEOUT",
            "TIMEOUT_REASON": reason,
            "WORKER_EXECUTION_ID": state.worker_execution_id,
            "DEPENDENT_WORKERS_DISPATCHED": False,
            "CURSOR_TASK_CANCELLATION": CURSOR_TASK_CANCELLATION,
            "PROCESS_TREE_TERMINATION": PROCESS_TREE_TERMINATION,
            "SAFE_TIMEOUT_STOP": True,
            "PARTIAL_ARTIFACTS": "PRESERVED",
        }

    def may_dispatch_dependent(self) -> bool:
        return not self.timed_out_wex

    def accept_late_output(
        self,
        *,
        worker_execution_id: str,
        packet_generation: int,
        expected_generation: int,
        attempt: int,
        expected_attempt: int,
    ) -> str:
        """Late output from timed-out or stale generation/attempt is rejected."""
        if worker_execution_id in self.timed_out_wex:
            return "REJECT_LATE_OUTPUT_AFTER_TIMEOUT"
        if packet_generation != expected_generation:
            return "REJECT_STALE_PACKET_GENERATION"
        if attempt != expected_attempt:
            return "REJECT_STALE_ATTEMPT"
        return "ACCEPT"

    def retry_allowed(self, state: WorkerRuntimeState) -> str:
        if state.attempt >= state.max_attempts:
            return "BLOCKED_MAX_RETRY_EXHAUSTED"
        return "RETRY_ALLOWED"


def write_timeout_policy_status(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "CURSOR_TASK_CANCELLATION": CURSOR_TASK_CANCELLATION,
                "PROCESS_TREE_TERMINATION": PROCESS_TREE_TERMINATION,
                "SAFE_TIMEOUT_STOP": True,
                "LATE_OUTPUT_REJECTION": True,
                "MAX_ATTEMPTS_DEFAULT": MAX_ATTEMPTS_DEFAULT,
                "DISCOVERY_NOTE": (
                    "Task tool interrupt=true on resume of running async agent; "
                    "no proven general process-tree termination API for OPSX orchestrator."
                ),
                "UPDATED_AT": time.time(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
