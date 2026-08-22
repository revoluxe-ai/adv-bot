# Corrective V3 Report — `/opsx-bug-team`

```text
BUILDER_ROLE: Corrective OPSX Agent Team Builder / Runtime Engineer V3
STATUS: OPSX_BUG_TEAM_CORRECTIVE_V3_IMPLEMENTED
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
OWNER_ACTIVATION: NOT_ISSUED
INDEPENDENT_CONTROLLED_TEST_ALLOWED: NO (not claimed)
RUNTIME_ACTIVATION_ALLOWED: NO
REAL_BUG_EXECUTION_ALLOWED: NO
COMMIT_CREATED_BY_CORRECTIVE_BUILDER: NO
```

## Controlling prior verdict addressed

```text
CANDIDATE_TEAM_REVIEW_V2_FAIL → BF-V2-001..004 corrective build
```

## Evidence class legend

| Label | Meaning |
|-------|---------|
| REAL_CURSOR_TASK | Host invoked Cursor Task; agent UUID recorded |
| RUNTIME_UNIT | Python unit/harness under proof root |
| FILESYSTEM_ENFORCEMENT | before/after snapshot + allowlist |
| CONTRACT_STATIC | docs/activation/fingerprint contracts |
| SIMULATED_BACKEND | `harness/task_dispatch.py` only — `LIVE_RUNTIME_AUTHORITY: NONE` |

---

## BF-V2-001 — End-to-end reusable live Task hop

```text
STATUS: IMPLEMENTED
AUTHORITATIVE_PATH: .cursor/pipeline/bug-team/runtime/live_task_hop.py
SIMULATED_PATH: .cursor/pipeline/bug-team/harness/task_dispatch.py
SIMULATED_PATH_SEPARATION: runtime does not import harness.task_dispatch
PROOF_ROOT: .tmp/opsx-bug-team-harness/corrective-v3-proof/20260728T050402Z/
```

Phases: `prepare_live_hop` → host Cursor Task → `finalize_live_hop`.

Hash semantics:

```text
INPUT_PACKET_RAW_SHA256 / OUTPUT_PACKET_RAW_SHA256 — exact file bytes
INPUT_PACKET_CANONICAL_SHA256 / OUTPUT_PACKET_CANONICAL_SHA256 — canonical JSON
```

### Live workers proven (REAL_CURSOR_TASK)

Proof root: `.tmp/opsx-bug-team-harness/corrective-v3-proof/20260728T050402Z/`

| Worker | cursor_agent_id | duration_ms | checkpoint |
|--------|-----------------|-------------|------------|
| MATERIALIZER | `3b93f7eb-7275-45b7-8f15-2494104495ed` | 112121 | ADVANCED |
| CLASSIFIER | `eca01886-5528-4803-9fc0-9e68f937ccd9` | 112316 | ADVANCED |
| IMPLEMENTATION_EXECUTOR | `3f8441a8-b076-4b50-acb3-d57066032ee7` | 112290 | ADVANCED |
| GREEN_VERIFIER | `4c14dada-b41d-42aa-905e-ce069410794e` | 112359 | ADVANCED |
| FAN_IN_ASSEMBLER | `06185706-ed59-410d-a7f6-fb96134933bd` | 112452 | ADVANCED |

Full hashes / snapshots / diffs: see `FINALIZE_RESULTS.json` under the proof root.
Raw file SHA-256 verified against disk bytes for all five hops.

Remaining worker contracts: reusable `prepare_live_hop` validation via `V3-REG-PREPARE-ALL` (RUNTIME_UNIT).

Filesystem: finalize loads `BEFORE_SNAPSHOT_PATH`, takes after snapshot, computes real `FsDiff` (no synthetic diff).

Timing: `PREPARED_AT` / `TASK_STARTED_AT` / `FINALIZED_AT` / `DURATION_MS` (non-zero for live proofs).

---

## BF-V2-002 — Single packet validation gate

```text
STATUS: IMPLEMENTED
VALIDATOR_PATH: runtime/packets.py::validate_packet_for_transition
TERMINAL_STATUS_ENFORCEMENT: worker_contracts.ALLOWED_STATUS_TERMINAL_PAIRS
DEPENDENCY_HASH_ENFORCEMENT: raw + canonical inside same gate
```

Tests (RUNTIME_UNIT): V3-VAL-01..08 — all PASS.

---

## BF-V2-003 — Owner GO hard prepare/dispatch gate

```text
STATUS: IMPLEMENTED
HOST_REGISTRATION_PATH: runtime/owner_decision_host.py
WORKER_FORGE: owner_go.create_production_go raises WORKER_OWNER_GO_CREATION_FORBIDDEN
PREPARE_WITHOUT_GO: BLOCKED_OWNER_PRODUCTION_GO_REQUIRED (no intent)
ONE_TIME: ISSUED → RESERVED → CONSUMED
TOKEN: OWNER_AUTHORITY_TOKEN host-only (not in packets/DISPATCH/TRACE)
```

Tests (RUNTIME_UNIT): V3-GATE-01..11 — all PASS.

---

## BF-V2-004 — Active execution + universal stale rejection

```text
STATUS: IMPLEMENTED
ACTIVE_EXECUTION_SOURCE: team/CHECKPOINT.json ACTIVE_* fields
FINALIZE_AUTHORITY: dispatch intent + checkpoint (not caller expected gen/attempt)
UNIVERSAL_STALE: timeout / superseded / wrong attempt / gens / worker / duplicate
```

Tests (RUNTIME_UNIT): V3-STALE-01..10 — all PASS.

---

## Timeout model (docs)

```text
CURSOR_TASK_CANCELLATION: PARTIAL_INTERRUPT_ON_RESUME
PROCESS_TREE_TERMINATION: BLOCKED_PLATFORM_TERMINATION_LIMITATION
SAFE_TIMEOUT_ENFORCEMENT: logical isolation + dependent-wave stop + stale rejection + finite retry
```

Updated: `dispatch/TASK_DISPATCH.md`.

---

## Corrective V3 test suite

```text
COMMAND: python .cursor/pipeline/bug-team/harness/run_corrective_v3_tests.py
TOTAL: 34
PASSED: 34
FAILED: 0
INDEPENDENT_TESTER_PASS: NOT_ISSUED
```

Includes regressions: NOT_ACTIVE, FANIN FS boundary, route-trace monotonicity, graph fingerprint, prepare-all workers.

---

## Acceptance checklist (Builder self-check)

```text
AC-01..AC-15: addressed in this build (Builder claim only — not Independent Review)
```

## Boundaries preserved

```text
PRODUCT_APP_FILES_CHANGED: NONE
PRODUCT_TEST_FILES_CHANGED: NONE
OPENSPEC_PRODUCT_FILES_CHANGED: NONE
REAL_BUG_CASES_CREATED: NONE
RUNTIME_ACTIVATED: NO
```

## ONE_NEXT_ACTION

```text
Independent Candidate Team Review V3
```
