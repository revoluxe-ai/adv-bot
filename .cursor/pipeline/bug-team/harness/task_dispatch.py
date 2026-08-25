# -*- coding: utf-8 -*-
"""SIMULATED Task dispatch backend (NOT live runtime authority).

```text
EXECUTION_CLASS: SIMULATED_BACKEND
LIVE_RUNTIME_AUTHORITY: NONE
```

Authoritative live path: ``runtime/live_task_hop.py``.
This module must NOT be imported by the live orchestrator path.
Retained only for controlled harness / simulated unit tests.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


SCHEMA_VERSION = "1"
WORKER_IDS = (
    "MATERIALIZER",
    "CLAIM_WORKER",
    "CLASSIFIER",
    "SPEC_UPDATE_WORKER",
    "RED_TEST_WORKER",
    "IMPLEMENTATION_EXECUTOR",
    "GREEN_VERIFIER",
    "TASK_COMPLETION_WORKER",
    "BOUNDED_HUNTER",
    "FAN_IN_ASSEMBLER",
    "FAMILY_LEARNING_WORKER",
    "CLOSURE_OPERATOR",
)

# Independence: must never share execution identity
INDEPENDENCE_PAIRS = (
    ("RED_TEST_WORKER", "IMPLEMENTATION_EXECUTOR"),
    ("IMPLEMENTATION_EXECUTOR", "GREEN_VERIFIER"),
    ("BOUNDED_HUNTER", "IMPLEMENTATION_EXECUTOR"),
    ("FAN_IN_ASSEMBLER", "FAMILY_LEARNING_WORKER"),
    ("FAMILY_LEARNING_WORKER", "CLOSURE_OPERATOR"),
    ("FAN_IN_ASSEMBLER", "CLOSURE_OPERATOR"),
)

# Live WAVE_4 terminal edges (mandatory learning before closure).
LIVE_TERMINAL_EDGES = (
    ("FAN_IN_ASSEMBLER", "FAMILY_LEARNING_WORKER"),
    ("FAMILY_LEARNING_WORKER", "CLOSURE_OPERATOR"),
)

DEFAULT_TIMEOUTS = {
    "MATERIALIZER": 600,
    "CLAIM_WORKER": 300,
    "CLASSIFIER": 900,
    "SPEC_UPDATE_WORKER": 1800,
    "RED_TEST_WORKER": 2400,
    "IMPLEMENTATION_EXECUTOR": 2400,
    "GREEN_VERIFIER": 1800,
    "TASK_COMPLETION_WORKER": 600,
    "BOUNDED_HUNTER": 1800,
    "FAN_IN_ASSEMBLER": 600,
    "FAMILY_LEARNING_WORKER": 900,
    "CLOSURE_OPERATOR": 300,
}

MAX_ATTEMPTS = {
    "MATERIALIZER": 2,
    "CLAIM_WORKER": 2,
    "CLASSIFIER": 2,
    "SPEC_UPDATE_WORKER": 2,
    "RED_TEST_WORKER": 2,
    "IMPLEMENTATION_EXECUTOR": 2,
    "GREEN_VERIFIER": 2,
    "TASK_COMPLETION_WORKER": 2,
    "BOUNDED_HUNTER": 2,
    "FAN_IN_ASSEMBLER": 2,
    "FAMILY_LEARNING_WORKER": 2,
    "CLOSURE_OPERATOR": 1,
}

FANIN_ONLY_WRITE = "results/FANIN.md"


@dataclass
class TaskCallSpec:
    """Immutable Cursor Task tool invocation plan for one worker."""

    worker_id: str
    worker_execution_id: str
    parent_orchestration_id: str
    case_id: str
    finding_id: Optional[str]
    input_packet_path: str
    output_packet_path: str
    timeout_seconds: int
    attempt: int
    max_attempts: int
    checkpoint_path: str
    heartbeat_path: str
    task_subagent_type: str = "generalPurpose"
    description: str = ""
    model: str = "inherit"  # must remain inherit (MODEL_DISPATCH.md)

    def to_cursor_task_arguments(self) -> Dict[str, Any]:
        """Build exact Task tool arguments with explicit model: inherit."""
        if self.model != "inherit":
            raise ValueError("MODEL_SELECTION_POLICY=inherit forbids non-inherit model")
        prompt = "\n".join(
            [
                f"WORKER_ID: {self.worker_id}",
                f"WORKER_EXECUTION_ID: {self.worker_execution_id}",
                f"PARENT_ORCHESTRATION_ID: {self.parent_orchestration_id}",
                f"CASE_ID: {self.case_id}",
                f"FINDING_ID: {self.finding_id}",
                f"INPUT_PACKET_PATH: {self.input_packet_path}",
                f"OUTPUT_PACKET_PATH: {self.output_packet_path}",
                "WRITE_BOUNDARY_PATH: .cursor/pipeline/bug-team/WRITE_BOUNDARY.md",
                f"WORKER_SPEC_PATH: .cursor/pipeline/bug-team/workers/{self.worker_id}.md",
                f"TIMEOUT_SECONDS: {self.timeout_seconds}",
                f"ATTEMPT: {self.attempt}",
                f"MAX_ATTEMPTS: {self.max_attempts}",
                f"CHECKPOINT_PATH: {self.checkpoint_path}",
                f"HEARTBEAT_PATH: {self.heartbeat_path}",
                "MODEL_SELECTION_POLICY: inherit",
                "FORBIDDEN: do not perform other workers' duties",
                "FORBIDDEN: bash heredoc (cat <<EOF / <<'EOF') for multi-line "
                "JSON/Python/packet writes.",
                "REQUIRED: write OUTPUT_PACKET only within WRITE_BOUNDARY; "
                "update HEARTBEAT_PATH; exit with terminal STATUS; "
                "Write tool (or write .py/.json to path) then run/read by path; "
                "encoding=utf-8; ensure_ascii=True. On heredoc failure: do not "
                "retry heredoc — switch Write->path once. Cite preflight Shell "
                "payload I/O (anti-heredoc) + Windows Shell JSON/JSONL write safety.",
            ]
        )
        return {
            "description": self.description or f"opsx-bug-team/{self.worker_id}",
            "subagent_type": self.task_subagent_type,
            "model": "inherit",
            "prompt": prompt,
        }


@dataclass
class DispatchRecord:
    """One durable DISPATCH.jsonl line."""

    worker_execution_id: str
    parent_orchestration_id: str
    worker_id: str
    task_subagent_type: str
    started_at: float
    last_heartbeat_at: float
    timeout_seconds: int
    attempt: int
    max_attempts: int
    process_id_or_task_id: Optional[str]
    checkpoint_path: str
    input_packet_path: str
    output_artifact_path: str
    status: str
    terminal_status: Optional[str] = None
    schema_valid: Optional[bool] = None
    write_boundary_ok: Optional[bool] = None
    cursor_task_tool: str = "Task"
    schema_version: str = SCHEMA_VERSION

    def to_json(self) -> str:
        return json.dumps(
            {
                "SCHEMA_VERSION": self.schema_version,
                "WORKER_EXECUTION_ID": self.worker_execution_id,
                "PARENT_ORCHESTRATION_ID": self.parent_orchestration_id,
                "WORKER_ID": self.worker_id,
                "TASK_SUBAGENT_TYPE": self.task_subagent_type,
                "CURSOR_TASK_TOOL": self.cursor_task_tool,
                "STARTED_AT": self.started_at,
                "LAST_HEARTBEAT_AT": self.last_heartbeat_at,
                "TIMEOUT_SECONDS": self.timeout_seconds,
                "ATTEMPT": self.attempt,
                "MAX_ATTEMPTS": self.max_attempts,
                "PROCESS_ID_OR_TASK_ID": self.process_id_or_task_id,
                "CHECKPOINT_PATH": self.checkpoint_path,
                "INPUT_PACKET_PATH": self.input_packet_path,
                "OUTPUT_ARTIFACT_PATH": self.output_artifact_path,
                "STATUS": self.status,
                "TERMINAL_STATUS": self.terminal_status,
                "SCHEMA_VALID": self.schema_valid,
                "WRITE_BOUNDARY_OK": self.write_boundary_ok,
            },
            ensure_ascii=False,
            sort_keys=True,
        )


WorkerFn = Callable[["Orchestrator", TaskCallSpec], Dict[str, Any]]


@dataclass
class Orchestrator:
    """Host-chat orchestrator: plan, dispatch Task workers, validate packets.

    Never classifies / RED / fixes / GREEN / fan-in itself.
    """

    case_root: Path
    parent_orchestration_id: str = field(
        default_factory=lambda: f"ORCH/{uuid.uuid4().hex[:12]}"
    )
    dispatches: List[DispatchRecord] = field(default_factory=list)
    completed_hops: List[str] = field(default_factory=list)
    active_hop: Optional[str] = None
    owner_gate_status: str = "NONE"
    route: Dict[str, Any] = field(default_factory=dict)
    checkpoint: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    # Simulated Task backends keyed by WORKER_ID (controlled tests / Candidate)
    worker_backends: Dict[str, WorkerFn] = field(default_factory=dict)
    process_tree_terminated: bool = False
    blocked_reason: Optional[str] = None
    # Proof that orchestrator did NOT materialize itself
    orchestrator_materialized: bool = False

    def __post_init__(self) -> None:
        self.case_root = Path(self.case_root)
        (self.case_root / "team" / "packets").mkdir(parents=True, exist_ok=True)
        (self.case_root / "team" / "heartbeats").mkdir(parents=True, exist_ok=True)
        (self.case_root / "results").mkdir(parents=True, exist_ok=True)
        self.dispatch_log = self.case_root / "team" / "DISPATCH.jsonl"
        self.checkpoint_path = self.case_root / "team" / "CHECKPOINT.md"

    @property
    def case_id(self) -> str:
        return self.case_root.name

    def _new_wex(self, worker_id: str) -> str:
        return f"WEX/{worker_id}/{uuid.uuid4().hex[:10]}"

    def _append_dispatch(self, rec: DispatchRecord) -> None:
        self.dispatches.append(rec)
        with self.dispatch_log.open("a", encoding="utf-8") as fh:
            fh.write(rec.to_json() + "\n")

    def save_checkpoint(self) -> None:
        self.checkpoint.update(
            {
                "CASE_ID": self.case_id,
                "FINDING_ID": self.artifacts.get("FINDING_ID"),
                "CURRENT_ROUTE_STATE": self.route.get("CURRENT_ROUTE_STATE"),
                "COMPLETED_HOPS": list(self.completed_hops),
                "ACTIVE_HOP": self.active_hop,
                "EXPECTED_NEXT_COMMAND": self.route.get("EXPECTED_NEXT_COMMAND"),
                "OWNER_GATE_STATUS": self.owner_gate_status,
                "ARTIFACT_PATHS": {
                    k: str(v) if isinstance(v, Path) else v
                    for k, v in self.artifacts.items()
                    if k.endswith("_PATH") or k in ("CASE_ID", "FINDING_ID")
                },
                "ATTEMPTS": {
                    d.worker_id: d.attempt
                    for d in self.dispatches
                },
                "LAST_HEARTBEAT_AT": time.time(),
                "CHECKPOINT_SCHEMA_VERSION": 1,
                "PARENT_ORCHESTRATION_ID": self.parent_orchestration_id,
                "PROCESS_TREE_TERMINATED": self.process_tree_terminated,
                "BLOCKED_REASON": self.blocked_reason,
                "STALE": False,
            }
        )
        lines = ["# CHECKPOINT", ""]
        for k, v in self.checkpoint.items():
            lines.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
        self.checkpoint_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def build_task_call(self, worker_id: str, attempt: int = 1) -> TaskCallSpec:
        if worker_id not in WORKER_IDS:
            raise ValueError(f"unknown worker {worker_id}")
        wex = self._new_wex(worker_id)
        inp = self.case_root / "team" / "packets" / f"{wex.replace('/', '_')}.in.md"
        out = self.case_root / "team" / "packets" / f"{wex.replace('/', '_')}.out.md"
        hb = self.case_root / "team" / "heartbeats" / f"{wex.replace('/', '_')}.json"
        return TaskCallSpec(
            worker_id=worker_id,
            worker_execution_id=wex,
            parent_orchestration_id=self.parent_orchestration_id,
            case_id=self.case_id,
            finding_id=self.artifacts.get("FINDING_ID"),
            input_packet_path=str(inp),
            output_packet_path=str(out),
            timeout_seconds=DEFAULT_TIMEOUTS[worker_id],
            attempt=attempt,
            max_attempts=MAX_ATTEMPTS[worker_id],
            checkpoint_path=str(self.checkpoint_path),
            heartbeat_path=str(hb),
        )

    def write_input_packet(self, spec: TaskCallSpec, body: str) -> None:
        header = "\n".join(
            [
                f"WORKER_ID: {spec.worker_id}",
                f"WORKER_EXECUTION_ID: {spec.worker_execution_id}",
                f"PARENT_ORCHESTRATION_ID: {spec.parent_orchestration_id}",
                f"CASE_ID: {spec.case_id}",
                f"FINDING_ID: {spec.finding_id}",
                f"ATTEMPT: {spec.attempt}",
                f"MAX_ATTEMPTS: {spec.max_attempts}",
                f"TIMEOUT_SECONDS: {spec.timeout_seconds}",
                f"HEARTBEAT_PATH: {spec.heartbeat_path}",
                f"OUTPUT_PACKET_PATH: {spec.output_packet_path}",
                "",
                body,
            ]
        )
        Path(spec.input_packet_path).write_text(header + "\n", encoding="utf-8")

    def validate_output_packet(
        self, spec: TaskCallSpec, packet: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        required = (
            "WORKER_ID",
            "WORKER_EXECUTION_ID",
            "STATUS",
            "TERMINAL_STATUS",
        )
        for key in required:
            if key not in packet:
                return False, f"missing_{key}"
        if packet["WORKER_ID"] != spec.worker_id:
            return False, "worker_id_mismatch"
        if packet["WORKER_EXECUTION_ID"] != spec.worker_execution_id:
            return False, "wex_mismatch"
        return True, None

    def check_write_boundary(
        self, worker_id: str, written_paths: List[str]
    ) -> tuple[bool, Optional[str]]:
        if worker_id == "FAN_IN_ASSEMBLER":
            for p in written_paths:
                norm = p.replace("\\", "/")
                if not norm.endswith(FANIN_ONLY_WRITE) and FANIN_ONLY_WRITE not in norm:
                    # allow only FANIN.md
                    if not norm.endswith("FANIN.md"):
                        return False, "FANIN_WRITE_BOUNDARY_VIOLATION"
            return True, None
        if worker_id == "GREEN_VERIFIER":
            for p in written_paths:
                if "/app/" in p.replace("\\", "/") or p.endswith(".py") and "tests/" not in p:
                    if "results/GREEN" not in p.replace("\\", "/"):
                        return False, "GREEN_WRITE_BOUNDARY_VIOLATION"
        if worker_id == "IMPLEMENTATION_EXECUTOR":
            if self.owner_gate_status not in (
                "PRODUCTION_GO_RECEIVED",
                "WAITING_PRODUCTION_GO",
            ):
                # production write without GO
                for p in written_paths:
                    if "/app/" in p.replace("\\", "/"):
                        if self.owner_gate_status != "PRODUCTION_GO_RECEIVED":
                            return False, "OWNER_GATE_BYPASS_REJECTED"
            if self.owner_gate_status != "PRODUCTION_GO_RECEIVED":
                for p in written_paths:
                    if "/app/" in p.replace("\\", "/"):
                        return False, "OWNER_GATE_BYPASS_REJECTED"
        return True, None

    def dispatch(
        self,
        worker_id: str,
        input_body: str,
        *,
        attempt: int = 1,
        force_timeout: bool = False,
        malformed_output: bool = False,
        extra_writes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Dispatch a real Task-shaped worker (backend = Cursor Task or test double).

        Orchestrator never executes worker business logic itself.
        """
        if self.process_tree_terminated:
            return {
                "STATUS": "BLOCKED",
                "TERMINAL_STATUS": "PROCESS_TREE_TERMINATED",
                "ERROR": "dependent_wave_forbidden",
            }
        if self.blocked_reason:
            return {
                "STATUS": "BLOCKED",
                "TERMINAL_STATUS": self.blocked_reason,
            }

        spec = self.build_task_call(worker_id, attempt=attempt)
        # Proof: Task call arguments are built (Cursor Task shape)
        task_args = spec.to_cursor_task_arguments()
        assert "model" not in task_args
        assert task_args["subagent_type"] == "generalPurpose"
        assert "WORKER_ID:" in task_args["prompt"]

        self.write_input_packet(spec, input_body)
        self.active_hop = worker_id
        now = time.time()
        rec = DispatchRecord(
            worker_execution_id=spec.worker_execution_id,
            parent_orchestration_id=self.parent_orchestration_id,
            worker_id=worker_id,
            task_subagent_type="generalPurpose",
            started_at=now,
            last_heartbeat_at=now,
            timeout_seconds=spec.timeout_seconds,
            attempt=attempt,
            max_attempts=spec.max_attempts,
            process_id_or_task_id=None,
            checkpoint_path=spec.checkpoint_path,
            input_packet_path=spec.input_packet_path,
            output_artifact_path=spec.output_packet_path,
            status="RUNNING",
        )
        self._append_dispatch(rec)
        self.save_checkpoint()

        if force_timeout:
            rec.status = "TIMEOUT"
            rec.terminal_status = "TIMEOUT"
            rec.last_heartbeat_at = now
            self._rewrite_last_dispatch(rec)
            self.process_tree_terminated = True
            self.blocked_reason = "TIMEOUT"
            self.active_hop = None
            self.save_checkpoint()
            return {
                "STATUS": "TIMEOUT",
                "TERMINAL_STATUS": "TIMEOUT",
                "WORKER_EXECUTION_ID": spec.worker_execution_id,
                "DEPENDENT_WAVE_ALLOWED": False,
            }

        backend = self.worker_backends.get(worker_id)
        if backend is None:
            self.blocked_reason = "NO_WORKER_BACKEND"
            rec.status = "FAIL"
            rec.terminal_status = "NO_WORKER_BACKEND"
            self._rewrite_last_dispatch(rec)
            self.save_checkpoint()
            return {"STATUS": "FAIL", "TERMINAL_STATUS": "NO_WORKER_BACKEND"}

        # Backend stands in for Cursor Task subagent process boundary.
        # Live command uses Task tool; harness injects backends for T1–T26.
        packet = backend(self, spec)
        packet.setdefault("WORKER_ID", worker_id)
        packet.setdefault("WORKER_EXECUTION_ID", spec.worker_execution_id)
        packet.setdefault("PARENT_ORCHESTRATION_ID", self.parent_orchestration_id)

        if malformed_output:
            packet.pop("STATUS", None)

        written = list(packet.get("ARTIFACTS_WRITTEN") or [])
        if extra_writes:
            written.extend(extra_writes)
            packet["ARTIFACTS_WRITTEN"] = written

        ok_schema, schema_err = self.validate_output_packet(spec, packet)
        ok_wb, wb_err = self.check_write_boundary(worker_id, written)

        if not ok_schema:
            rec.status = "FAIL"
            rec.terminal_status = "MALFORMED_OUTPUT_PACKET"
            rec.schema_valid = False
            self.blocked_reason = "MALFORMED_OUTPUT_PACKET"
            self.process_tree_terminated = True
            self._rewrite_last_dispatch(rec)
            self.active_hop = None
            self.save_checkpoint()
            return {
                "STATUS": "FAIL",
                "TERMINAL_STATUS": "MALFORMED_OUTPUT_PACKET",
                "ERROR": schema_err,
                "DEPENDENT_WAVE_ALLOWED": False,
            }

        if not ok_wb:
            rec.status = "FAIL"
            rec.terminal_status = wb_err
            rec.schema_valid = True
            rec.write_boundary_ok = False
            self.blocked_reason = wb_err
            self.process_tree_terminated = True
            self._rewrite_last_dispatch(rec)
            self.active_hop = None
            self.save_checkpoint()
            return {
                "STATUS": "FAIL",
                "TERMINAL_STATUS": wb_err,
                "DEPENDENT_WAVE_ALLOWED": False,
            }

        # Persist output packet
        out_lines = [f"{k}: {v}" for k, v in packet.items()]
        Path(spec.output_packet_path).write_text(
            "\n".join(out_lines) + "\n", encoding="utf-8"
        )
        Path(spec.heartbeat_path).write_text(
            json.dumps({"LAST_HEARTBEAT_AT": time.time(), "STATUS": packet["STATUS"]}),
            encoding="utf-8",
        )

        rec.status = packet["STATUS"]
        rec.terminal_status = packet.get("TERMINAL_STATUS") or packet["STATUS"]
        rec.schema_valid = True
        rec.write_boundary_ok = True
        rec.process_id_or_task_id = packet.get("PROCESS_ID_OR_TASK_ID") or spec.worker_execution_id
        rec.last_heartbeat_at = time.time()
        self._rewrite_last_dispatch(rec)

        if packet["STATUS"] == "PASS":
            self.completed_hops.append(worker_id)
        elif packet["STATUS"] in ("FAIL", "BLOCKED", "TIMEOUT", "CANCELLED"):
            self.blocked_reason = packet.get("TERMINAL_STATUS") or packet["STATUS"]
            if packet["STATUS"] == "TIMEOUT":
                self.process_tree_terminated = True

        self.active_hop = None
        self.save_checkpoint()
        packet["DEPENDENT_WAVE_ALLOWED"] = (
            packet["STATUS"] == "PASS" and not self.process_tree_terminated
        )
        packet["_TASK_ARGS"] = task_args
        return packet

    def _rewrite_last_dispatch(self, rec: DispatchRecord) -> None:
        """Rewrite file from in-memory list (append-only semantics per hop;
        test harness rewrites last line for STATUS updates of same WEX)."""
        self.dispatches[-1] = rec
        with self.dispatch_log.open("w", encoding="utf-8") as fh:
            for d in self.dispatches:
                fh.write(d.to_json() + "\n")

    def reject_owner_bypass(self, kind: str) -> Dict[str, Any]:
        self.owner_gate_status = "BYPASS_REJECTED"
        self.blocked_reason = f"OWNER_GATE_BYPASS_REJECTED:{kind}"
        self.save_checkpoint()
        return {"STATUS": "BLOCKED", "TERMINAL_STATUS": self.blocked_reason}

    def grant_production_go(self) -> None:
        self.owner_gate_status = "PRODUCTION_GO_RECEIVED"

    def grant_closure(self) -> None:
        self.owner_gate_status = "CLOSURE_RECEIVED"

    def execution_ids_for(self, worker_id: str) -> List[str]:
        return [d.worker_execution_id for d in self.dispatches if d.worker_id == worker_id]

    def assert_independence(self) -> None:
        for a, b in INDEPENDENCE_PAIRS:
            ids_a = set(self.execution_ids_for(a))
            ids_b = set(self.execution_ids_for(b))
            if ids_a and ids_b and ids_a & ids_b:
                raise AssertionError(f"shared WEX between {a} and {b}")


def _is_placeholder_case_id(case_id: Optional[str]) -> bool:
    """True for template/non-durable case= values (must not trigger CASE_RESUME).

    CMD-IX-001: pasted ``case=<CASE_ID>`` from explore/ALSO_OK handbacks must
    not make free-form first intake ``BLOCKED_AMBIGUOUS_INVOCATION``.
    """
    if case_id is None:
        return True
    cid = case_id.strip().strip('"').rstrip(".,;")
    if not cid:
        return True
    if cid.upper() in {"CASE_ID", "<CASE_ID>"}:
        return True
    if cid.startswith("<") and cid.endswith(">"):
        return True
    return False


def parse_invocation(args: str, context_text: str = "") -> Dict[str, Any]:
    """Parse /opsx-bug-team invocation modes (orchestrator-only)."""
    text = (args or "").strip()
    case_id = None
    signal = None
    free_form = None
    if "case=" in text:
        for tok in text.split():
            if tok.startswith("case="):
                case_id = tok.split("=", 1)[1].strip().strip('"')
        if _is_placeholder_case_id(case_id):
            case_id = None
    if "signal=" in text:
        # signal="..."
        start = text.find("signal=")
        rest = text[start + 7 :]
        if rest.startswith('"'):
            end = rest.find('"', 1)
            signal = rest[1:end] if end > 0 else rest.strip('"')
        else:
            signal = rest.strip()
    # Ambiguous: case= + new free-form body
    remainder_parts: List[str] = []
    for line in text.splitlines() or [text]:
        tokens = line.split()
        kept: List[str] = []
        for tok in tokens:
            if tok.startswith("case=") or tok.startswith("signal="):
                continue
            # strip signal="..." already handled above; leftover free text kept
            kept.append(tok)
        if kept:
            remainder_parts.append(" ".join(kept))
    remainder = "\n".join(remainder_parts).strip()
    # Also strip quoted signal value from remainder if present as whole
    if signal and remainder == signal:
        remainder = ""

    if case_id and remainder:
        return {
            "MODE": "BLOCKED_AMBIGUOUS_INVOCATION",
            "CASE_ID": case_id,
            "RAW": remainder,
        }
    if case_id and signal:
        return {
            "MODE": "BLOCKED_AMBIGUOUS_INVOCATION",
            "CASE_ID": case_id,
            "RAW": signal,
        }
    if case_id:
        return {"MODE": "CASE_RESUME", "CASE_ID": case_id}
    if signal:
        return {
            "MODE": "EXPLICIT_SIGNAL",
            "RAW_INTAKE_TEXT": signal,
            "RAW_INTAKE_SOURCE": "USER_MESSAGE",
        }
    if text:
        return {
            "MODE": "FREE_FORM",
            "RAW_INTAKE_TEXT": text,
            "RAW_INTAKE_SOURCE": "USER_MESSAGE",
        }
    if context_text.strip():
        return {
            "MODE": "CURRENT_CONTEXT",
            "RAW_INTAKE_TEXT": context_text.strip(),
            "RAW_INTAKE_SOURCE": "CURRENT_CHAT_CONTEXT",
        }
    return {"MODE": "BLOCKED_INTAKE_REQUIRED"}
