# -*- coding: utf-8 -*-
"""Orchestrator host helpers.

Authoritative live hop: ``runtime.live_task_hop`` (prepare → host Task → finalize).
This module retains legacy helpers; new code must use live_task_hop.
Does NOT invoke Cursor Task itself — the host agent must call Task tool.
Does NOT import ``harness.task_dispatch`` (SIMULATED_BACKEND only).
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import activation, execution_identity, fs_boundary, owner_go, packets, route_trace, timeout


class OrchestratorRuntime:
    def __init__(
        self,
        *,
        case_root: Path,
        orchestration_id: Optional[str] = None,
        execution_mode: str = "NORMAL",
        proof_root: Optional[Path] = None,
    ) -> None:
        self.case_root = Path(case_root)
        self.execution_mode = execution_mode
        self.proof_root = Path(proof_root) if proof_root else None
        self.orchestration_id = orchestration_id or f"ORCH/{uuid.uuid4().hex[:12]}"
        self.checkpoint_generation = 1
        self.packet_generation = 1
        self.completed_hops: List[str] = []
        self.blocked_reason: Optional[str] = None
        self.timeouts = timeout.TimeoutController()
        self.dispatch_path = self.case_root / "team" / "DISPATCH.jsonl"
        self.trace_path = self.case_root / "results" / "ROUTE-TRACE.jsonl"
        self.checkpoint_path = self.case_root / "team" / "CHECKPOINT.json"
        (self.case_root / "team" / "packets").mkdir(parents=True, exist_ok=True)
        (self.case_root / "results").mkdir(parents=True, exist_ok=True)
        (self.case_root / "gates").mkdir(parents=True, exist_ok=True)

    def gate_or_block(self) -> Tuple[str, Dict[str, Any]]:
        return activation.check_invocation_gate(
            execution_mode=self.execution_mode,
            proof_root=self.proof_root or self.case_root,
        )

    def activation_hash(self) -> str:
        return activation.activation_state_hash()

    def new_wex(self, worker_id: str) -> str:
        return f"WEX/{worker_id}/{uuid.uuid4().hex[:10]}"

    def prepare_input(
        self,
        worker_id: str,
        payload: Dict[str, Any],
        *,
        case_id: str,
        finding_id: Optional[str],
        parent_packet_id: Optional[str] = None,
        dependency_packet_ids: Optional[List[str]] = None,
        dependency_hashes: Optional[Dict[str, str]] = None,
    ) -> Tuple[Dict[str, Any], Path, str, fs_boundary.FsSnapshot]:
        status, details = self.gate_or_block()
        if status == "BLOCKED_CANDIDATE_NOT_ACTIVE":
            raise RuntimeError("BLOCKED_CANDIDATE_NOT_ACTIVE")
        if status.startswith("BLOCKED_"):
            raise RuntimeError(status)
        if self.blocked_reason or not self.timeouts.may_dispatch_dependent():
            raise RuntimeError(self.blocked_reason or "TIMEOUT_BLOCKS_DEPENDENT")

        wex = self.new_wex(worker_id)
        pkt = packets.new_input_packet(
            worker_id=worker_id,
            orchestration_id=self.orchestration_id,
            worker_execution_id=wex,
            case_id=case_id,
            finding_id=finding_id,
            checkpoint_generation=self.checkpoint_generation,
            packet_generation=self.packet_generation,
            activation_state_hash=self.activation_hash(),
            execution_mode=self.execution_mode,
            payload=payload,
            parent_packet_id=parent_packet_id,
            dependency_packet_ids=dependency_packet_ids,
            dependency_hashes=dependency_hashes,
        )
        # Validate input before dispatch
        packets.validate_packet(
            pkt,
            expect_type="WORKER_INPUT",
            expect_worker_id=worker_id,
            expect_wex=wex,
            expect_orch=self.orchestration_id,
            expect_case=case_id,
            expect_finding=finding_id,
            expect_checkpoint_generation=self.checkpoint_generation,
            expect_packet_generation=self.packet_generation,
            expect_activation_hash=self.activation_hash(),
            require_active_for_normal=True,
            activation_is_active=activation.is_active(),
        )
        in_path = self.case_root / "team" / "packets" / f"{wex.replace('/', '_')}.in.json"
        hash_info = packets.write_packet(in_path, pkt)
        # Legacy callers may treat third return as raw SHA-256 string
        digest = hash_info["RAW_SHA256"]
        snap = fs_boundary.FsSnapshot.take(self.case_root)
        return pkt, in_path, digest, snap

    def prepare_live_hop(self, **kwargs: Any) -> Dict[str, Any]:
        """Delegate to authoritative live_task_hop.prepare_live_hop."""
        from . import live_task_hop

        return live_task_hop.prepare_live_hop(
            case_root=self.case_root,
            orchestration_id=self.orchestration_id,
            execution_mode=self.execution_mode,
            proof_root=self.proof_root or self.case_root,
            checkpoint_generation=kwargs.pop("checkpoint_generation", self.checkpoint_generation),
            packet_generation=kwargs.pop("packet_generation", self.packet_generation),
            **kwargs,
        )

    def finalize_live_hop(self, **kwargs: Any) -> Dict[str, Any]:
        """Delegate to authoritative live_task_hop.finalize_live_hop."""
        from . import live_task_hop

        result = live_task_hop.finalize_live_hop(case_root=self.case_root, **kwargs)
        if result.get("CHECKPOINT_ADVANCED"):
            self.checkpoint_generation = int(
                result.get("CHECKPOINT_GENERATION", self.checkpoint_generation + 1)
            )
        return result

    def require_execution_identity(
        self,
        *,
        worker_execution_id: str,
        case_id: str,
        finding_id: str,
        input_packet_path: Path,
        output_packet_path: Path,
        branch_id: Any = None,
    ) -> Dict[str, Any]:
        """Gate dependent-wave advance on EXECUTION_IDENTITY_VALIDATION=PASS."""
        result = execution_identity.gate_execution_identity_for_advance(
            case_root=self.case_root,
            worker_execution_id=worker_execution_id,
            expected_orchestration_id=self.orchestration_id,
            expected_case_id=case_id,
            expected_finding_id=finding_id,
            input_packet_path=Path(input_packet_path),
            output_packet_path=Path(output_packet_path),
            checkpoint_path=self.checkpoint_path,
            dispatch_log_path=self.dispatch_path,
            expected_branch_id=branch_id,
        )
        payload = result.as_dict()
        if not result.VALID:
            self.blocked_reason = f"BLOCKED_EXECUTION_IDENTITY_NOT_FINALIZED:{result.REASON_CODE}"
        return payload

    def build_task_prompt(
        self,
        *,
        worker_id: str,
        wex: str,
        in_path: Path,
        out_path: Path,
        case_id: str,
        finding_id: Optional[str],
        timeout_seconds: int,
        attempt: int,
    ) -> Dict[str, Any]:
        """Cursor Task tool arguments — model omitted (auto/inherit)."""
        prompt = "\n".join(
            [
                f"WORKER_ID: {worker_id}",
                f"WORKER_EXECUTION_ID: {wex}",
                f"PARENT_ORCHESTRATION_ID: {self.orchestration_id}",
                f"CASE_ID: {case_id}",
                f"FINDING_ID: {finding_id}",
                f"EXECUTION_MODE: {self.execution_mode}",
                f"INPUT_PACKET_PATH: {in_path}",
                f"OUTPUT_PACKET_PATH: {out_path}",
                "PACKET_FORMAT: JSON envelope (SCHEMA_VERSION 1)",
                "Write OUTPUT as JSON matching WORKER_OUTPUT fields.",
                "PRODUCT_WRITES: FORBIDDEN in REVIEW_PROOF_ONLY.",
                "Do not perform other workers' duties.",
                f"TIMEOUT_SECONDS: {timeout_seconds}",
                f"ATTEMPT: {attempt}",
                # HEREDOC-SHELL-PAYLOAD-001 — cite opsx-execution-preflight § Shell payload I/O
                "FORBIDDEN: bash heredoc (cat <<EOF / <<'EOF') for multi-line JSON/Python/packet writes.",
                "REQUIRED: Write tool (or write .py/.json to path) then run/read by path; "
                "encoding=utf-8; ensure_ascii=True. On heredoc failure: do not retry "
                "heredoc — switch Write->path once. Cite preflight Shell payload I/O "
                "(anti-heredoc) + Windows Shell JSON/JSONL write safety.",
            ]
        )
        return {
            "description": f"opsx-bug-team/{worker_id}",
            "subagent_type": "generalPurpose",
            "prompt": prompt,
        }

    def append_dispatch(self, record: Dict[str, Any]) -> None:
        self.dispatch_path.parent.mkdir(parents=True, exist_ok=True)
        with self.dispatch_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    def finalize_after_task(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """DISABLED (BF-ICT-002) — not a live success authority.

        Live Cursor Task success may only go through
        ``live_task_hop.finalize_live_hop``.
        """
        return {
            "STATUS": "BLOCKED_LEGACY_FINALIZE_DISABLED",
            "TERMINAL_STATUS": "BLOCKED_LEGACY_FINALIZE_DISABLED",
            "CHECKPOINT_ADVANCED": False,
            "ROUTE_TRACE_SUCCESS_EVENT_APPENDED": False,
            "DEPENDENT_WORKERS_DISPATCHED": False,
            "OWNER_RECEIPT_CONSUMED": False,
            "LIVE_SUCCESS_AUTHORITY": "runtime/live_task_hop.py::finalize_live_hop",
            "DETAIL": "OrchestratorRuntime.finalize_after_task is legacy non-authority",
        }

    def _save_checkpoint(self, case_id: str, finding_id: Optional[str]) -> None:
        data = {
            "CASE_ID": case_id,
            "FINDING_ID": finding_id,
            "ORCHESTRATION_ID": self.orchestration_id,
            "CHECKPOINT_GENERATION": self.checkpoint_generation,
            "PACKET_GENERATION": self.packet_generation,
            "COMPLETED_HOPS": self.completed_hops,
            "BLOCKED_REASON": self.blocked_reason,
            "EXECUTION_MODE": self.execution_mode,
            "UPDATED_AT": time.time(),
        }
        self.checkpoint_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
