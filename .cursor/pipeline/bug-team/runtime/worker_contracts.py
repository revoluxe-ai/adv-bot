# -*- coding: utf-8 -*-
"""Machine-readable worker contracts for Corrective V3.

ALLOWED_STATUS_TERMINAL_PAIRS and prepare gates used by
validate_packet_for_transition / prepare_live_hop.
"""

from __future__ import annotations

from typing import Dict, List, Set, Tuple

# (STATUS, TERMINAL_STATUS)
ALLOWED_STATUS_TERMINAL_PAIRS: Dict[str, Set[Tuple[str, str]]] = {
    "MATERIALIZER": {
        ("PASS", "PASS"),
        ("BLOCKED", "DUPLICATE_ROOT_REJECTED"),
        ("BLOCKED", "BLOCKED_EVIDENCE_REQUIRED"),
        ("FAIL", "FAIL"),
        ("TIMEOUT", "TIMEOUT"),
        ("CANCELLED", "CANCELLED"),
    },
    "CLAIM_WORKER": {
        ("PASS", "PASS"),
        ("BLOCKED", "DUPLICATE_CLAIM_REJECTED"),
        ("FAIL", "FAIL"),
        ("TIMEOUT", "TIMEOUT"),
        ("CANCELLED", "CANCELLED"),
    },
    "CLASSIFIER": {
        ("PASS", "PASS"),
        ("BLOCKED", "BLOCKED_EVIDENCE_REQUIRED"),
        ("FAIL", "FAIL"),
        ("TIMEOUT", "TIMEOUT"),
        ("CANCELLED", "CANCELLED"),
    },
    "SPEC_UPDATE_WORKER": {
        ("PASS", "PASS"),
        ("BLOCKED", "BLOCKED"),
        ("WAITING_OWNER", "WAITING_OWNER"),
        ("FAIL", "FAIL"),
        ("TIMEOUT", "TIMEOUT"),
        ("CANCELLED", "CANCELLED"),
    },
    "RED_TEST_WORKER": {
        ("PASS", "PASS"),
        ("PASS", "RED_CONFIRMED"),
        ("BLOCKED", "PASS_ALREADY"),
        ("BLOCKED", "INVALID_RED"),
        ("FAIL", "INVALID_RED"),
        ("FAIL", "FAIL"),
        ("TIMEOUT", "TIMEOUT"),
        ("CANCELLED", "CANCELLED"),
    },
    "IMPLEMENTATION_EXECUTOR": {
        ("PASS", "PASS"),
        ("BLOCKED", "OWNER_GATE_BYPASS_REJECTED"),
        ("BLOCKED", "BLOCKED_OWNER_PRODUCTION_GO_REQUIRED"),
        ("FAIL", "FAIL"),
        ("TIMEOUT", "TIMEOUT"),
        ("CANCELLED", "CANCELLED"),
    },
    "GREEN_VERIFIER": {
        ("PASS", "PASS"),
        ("PASS", "GREEN_CONFIRMED"),
        ("FAIL", "FROZEN_TEST_HASH_MISMATCH"),
        ("FAIL", "FAIL"),
        ("TIMEOUT", "TIMEOUT"),
        ("CANCELLED", "CANCELLED"),
    },
    "TASK_COMPLETION_WORKER": {
        ("PASS", "PASS"),
        ("BLOCKED", "INCOMPLETE"),
        ("FAIL", "FAIL"),
        ("TIMEOUT", "TIMEOUT"),
        ("CANCELLED", "CANCELLED"),
    },
    "BOUNDED_HUNTER": {
        ("PASS", "PASS"),
        ("FAIL", "FAIL"),
        ("TIMEOUT", "TIMEOUT"),
        ("CANCELLED", "CANCELLED"),
    },
    "FAN_IN_ASSEMBLER": {
        ("PASS", "PASS"),
        ("PASS", "FANIN_READY"),
        ("BLOCKED", "FANIN_INCOMPLETE"),
        ("FAIL", "FAIL_WRITE_BOUNDARY"),
        ("FAIL", "FAIL"),
        ("TIMEOUT", "TIMEOUT"),
        ("CANCELLED", "CANCELLED"),
    },
    "FAMILY_LEARNING_WORKER": {
        ("PASS", "PASS"),
        ("PASS", "LEARNING_COMPLETE"),
        ("BLOCKED", "LEARNING_BLOCKED"),
        ("WAITING_OWNER", "OWNER_WAIT"),
        ("FAIL", "FAIL"),
        ("TIMEOUT", "TIMEOUT"),
        ("CANCELLED", "CANCELLED"),
    },
    "CLOSURE_OPERATOR": {
        ("PASS", "PASS"),
        ("PASS", "CLOSED"),
        ("WAITING_OWNER", "WAITING_OWNER_FINAL_CLOSURE"),
        ("FAIL", "FAIL"),
        ("TIMEOUT", "TIMEOUT"),
        ("CANCELLED", "CANCELLED"),
    },
}

REQUIRES_OWNER_PRODUCTION_GO = {"IMPLEMENTATION_EXECUTOR"}
REQUIRES_OWNER_CLOSURE_GO = {"CLOSURE_OPERATOR"}

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
    "FAMILY_LEARNING_WORKER": 600,
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


def allowed_pairs(worker_id: str) -> Set[Tuple[str, str]]:
    return ALLOWED_STATUS_TERMINAL_PAIRS.get(worker_id, {("PASS", "PASS"), ("FAIL", "FAIL"), ("TIMEOUT", "TIMEOUT")})
