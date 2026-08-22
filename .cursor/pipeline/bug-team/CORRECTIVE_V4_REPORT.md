# Corrective V4 Report — ICT blockers only

```text
BUILDER_ROLE: Corrective OPSX Bug Team Runtime Builder V4
STATUS: OPSX_BUG_TEAM_CORRECTIVE_V4_IMPLEMENTED
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
OWNER_ACTIVATION: NOT_ISSUED
CONTROLLING_VERDICT: INDEPENDENT_CONTROLLED_TEST_FAIL
EVIDENCE_ROOT_ICT: .tmp/opsx-bug-team-harness/independent-controlled-test-v3/
EVIDENCE_ROOT_V4: .tmp/opsx-bug-team-harness/corrective-v4/20260728T053702Z/
COMMIT_CREATED_BY_CORRECTIVE_BUILDER: NO
```

## Candidate hashes

### Before (ICT V3 / Corrective V3)

| Path | SHA-256 |
|------|---------|
| runtime/live_task_hop.py | `953a86079550ed5c28358cfdf9447001e9b2a6df10d83b2b14d0c3adbfdeef55` |
| runtime/packets.py | `a70b90d09f51be4cb255e5574724661026686498039d80d96a7a3e0cbcad8de1` |
| runtime/owner_decision_host.py | `12e287638b016dc373d5ad7fe5e8796aa7734f66eab74039b472f612a512d8c2` |
| runtime/owner_go.py | `6695565fe64fb2317d53b26f29186387ab4b9400987a9044fa1728a012fd5f51` |
| runtime/orchestrator.py | `aeb848f8ee4a88f316b81b91b1cebf27f4c95424d44d502d7fa45aa4e912984a` |
| harness/task_dispatch.py | `1d6069ab71d3371e93ff2c71e571e290c74a84660390a6f2d78313c7b26754b7` |

### After (Corrective V4)

| Path | SHA-256 |
|------|---------|
| runtime/live_task_hop.py | `89b93432c739c53351c39788f2a81471ec973fa047c1c3df97332761a074c49d` |
| runtime/packets.py | `22efbae1e9bdc3cd733ccf6fe323793de8cc6e07c21d03c50ba2629264f8cc56` |
| runtime/owner_decision_host.py | `957505cf99099de73b0e834579fd7a00d4d976eacb4bc75b41fef3a60972e32d` |
| runtime/owner_go.py | `6695565fe64fb2317d53b26f29186387ab4b9400987a9044fa1728a012fd5f51` (unchanged) |
| runtime/orchestrator.py | `2a121b354a15ad8647f75076d758078c9901e9bad364bd6f679110fbc925284c` |
| harness/task_dispatch.py | `1d6069ab71d3371e93ff2c71e571e290c74a84660390a6f2d78313c7b26754b7` (unchanged) |

---

## BF-ICT-001 — RED raw + canonical at validate_and_reserve

```text
STATUS: IMPLEMENTED
VALIDATE_AND_RESERVE_PATH: runtime/owner_decision_host.py::validate_and_reserve_production_go
RAW_HASH_ENFORCEMENT: YES → OWNER_GO_RED_RAW_HASH_MISMATCH
CANONICAL_HASH_ENFORCEMENT: YES → OWNER_GO_RED_CANONICAL_HASH_MISMATCH
FROZEN_HASH_ENFORCEMENT: YES → OWNER_GO_FROZEN_HASH_MISMATCH
PACKET_ID_ENFORCEMENT: YES → OWNER_GO_RED_PACKET_ID_MISMATCH
MISMATCH_VS_GO_REQUIRED: mismatch codes when receipt exists; GO_REQUIRED only if missing
```

Tests: V4-GATE-01..08 PASS; ICT-REG-001 PASS.

---

## BF-ICT-002 — Single live success authority

```text
STATUS: IMPLEMENTED
AUTHORITATIVE_SUCCESS_PATH: runtime/live_task_hop.py::finalize_live_hop
LEGACY_FINALIZE_STATUS: BLOCKED_LEGACY_FINALIZE_DISABLED
WEAK_VALIDATOR_AUTHORITY: LIVE_TRANSITION_AUTHORITY: NONE (validate_packet)
CHECKPOINT_BYPASS_RESULT: blocked (legacy cannot advance)
RECEIPT_BYPASS_RESULT: blocked
DEPENDENT_DISPATCH_BYPASS_RESULT: blocked
INVENTORY: runtime/LIVE_SUCCESS_AUTHORITY.md
```

Tests: V4-AUTH-01..08 PASS; ICT-REG-002 PASS.

---

## BF-ICT-003 — ACTIVE RUNNING execution lock

```text
STATUS: IMPLEMENTED
ACTIVE_LOCK_PATH: live_task_hop.prepare_live_hop early gate
DIFFERENT_WORKER_RESULT: BLOCKED_ACTIVE_EXECUTION_RUNNING
SAME_WORKER_NEW_WEX_RESULT: BLOCKED_ACTIVE_EXECUTION_RUNNING
IDEMPOTENT_REPLAY_RESULT: EXISTING_DISPATCH_INTENT_RETURNED (no mutation)
EXPLICIT_RETRY_PATH: authorize_retry_or_resume after TIMEOUT|FAIL|CANCELLED|BLOCKED_RETRYABLE
```

Tests: V4-LOCK-01..10 PASS; ICT-REG-003 PASS.

---

## V4 test matrix

```text
COMMAND: python .cursor/pipeline/bug-team/harness/run_corrective_v4_tests.py
TOTAL: 29
PASSED: 29
FAILED: 0
```

Includes V4-GATE-01..08, V4-AUTH-01..08, V4-LOCK-01..10, ICT-REG-001..003.

## Regression

```text
V3: TOTAL 34 PASSED 34 FAILED 0
V2: TOTAL 18 PASSED 18 FAILED 0
```

## Owner receipt validation matrix

| Attribute | Enforced at reserve |
|-----------|---------------------|
| RED_PACKET_ID | OWNER_GO_RED_PACKET_ID_MISMATCH |
| RED_RAW_SHA256 | OWNER_GO_RED_RAW_HASH_MISMATCH |
| RED_CANONICAL_SHA256 | OWNER_GO_RED_CANONICAL_HASH_MISMATCH |
| FROZEN_TEST_HASHES | OWNER_GO_FROZEN_HASH_MISMATCH |
| CASE_ID | OWNER_GO_CASE_MISMATCH |
| FINDING_ID | path miss → GO_REQUIRED; else FINDING_MISMATCH |
| EXPECTED_EXECUTION_ROUTE | OWNER_GO_ROUTE_MISMATCH |
| CHECKPOINT_GENERATION | OWNER_GO_CHECKPOINT_GENERATION_MISMATCH |

## Active execution transition matrix

| From | Ordinary prepare | authorize_retry_or_resume |
|------|------------------|---------------------------|
| IDLE / missing / READY_FOR_RETRY | allow new WEX | n/a |
| RUNNING | block or idempotent replay | n/a |
| TIMEOUT / FAIL / CANCELLED / BLOCKED_RETRYABLE | BLOCKED_RETRY_AUTHORIZATION_REQUIRED | → READY_FOR_RETRY |

## Live success authority inventory

See `runtime/LIVE_SUCCESS_AUTHORITY.md`.

## Product isolation / activation

```text
PRODUCT_APP_FILES_CHANGED: NONE
PRODUCT_TEST_FILES_CHANGED: NONE
OPENSPEC_PRODUCT_FILES_CHANGED: NONE
REAL_BUG_CASES_CREATED: NONE
RUNTIME_ACTIVATED: NO
ICT_EVIDENCE_ROOT_UNTOUCHED: YES (no writes to independent-controlled-test-v3/)
```

## Known platform limitations

```text
PROCESS_TREE_TERMINATION: BLOCKED_PLATFORM_TERMINATION_LIMITATION
CURSOR_TASK_CANCELLATION: PARTIAL_INTERRUPT_ON_RESUME
SAFE_TIMEOUT_ENFORCEMENT: logical isolation + stale rejection + finite retry
```

## ONE_NEXT_ACTION

```text
Independent Controlled Test V3 rerun
```
