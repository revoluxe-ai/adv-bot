# Corrective V5 Report — ICT Rerun Blockers

```text
STATUS: OPSX_BUG_TEAM_CORRECTIVE_V5_IMPLEMENTED
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
OWNER_ACTIVATION: NOT_ISSUED
REAL_BUG_EXECUTION_ALLOWED: NO
COMMIT_ALLOWED: NO
INDEPENDENT_TESTER_PASS: NOT_ISSUED
```

Evidence root:

```text
.tmp/opsx-bug-team-harness/corrective-v5/20260728T060302Z/
```

Controlling FAIL evidence (ICT V3 rerun):

```text
.tmp/opsx-bug-team-harness/independent-controlled-test-v3-rerun/ICT-V3R-20260728T054057Z/
```

## Candidate hashes before (V4 baseline)

| Path | SHA-256 |
|------|---------|
| runtime/live_task_hop.py | `89b93432c739c53351c39788f2a81471ec973fa047c1c3df97332761a074c49d` |
| runtime/orchestrator.py | `2a121b354a15ad8647f75076d758078c9901e9bad364bd6f679110fbc925284c` |
| runtime/packets.py | `22efbae1e9bdc3cd733ccf6fe323793de8cc6e07c21d03c50ba2629264f8cc56` |
| runtime/owner_decision_host.py | `957505cf99099de73b0e834579fd7a00d4d976eacb4bc75b41fef3a60972e32d` |
| runtime/owner_go.py | `6695565fe64fb2317d53b26f29186387ab4b9400987a9044fa1728a012fd5f51` |
| runtime/route_trace.py | `bed1a80c3ef2d213d55b73fbd5ae4f2952a6902026826125fd27253f2d7ed4ba` |
| runtime/LIVE_SUCCESS_AUTHORITY.md | `c1d9037eaa7f6034a4a655d888b629cc85d26f778fcfa41f0d178d697221ef20` |
| harness/run_corrective_v4_tests.py | `816d980aa2d16c8d7d7fffaca5769a6f96d86f85e18a41e4743d14159853602d` |

## Candidate hashes after (V5)

| Path | SHA-256 |
|------|---------|
| runtime/live_task_hop.py | `c90ef1b9bce37a8a0ee303d5cbba28425fede3ec17f6eb870873f8e10c46f620` |
| runtime/orchestrator.py | unchanged |
| runtime/packets.py | unchanged |
| runtime/owner_decision_host.py | unchanged |
| runtime/owner_go.py | unchanged |
| runtime/route_trace.py | unchanged |
| runtime/LIVE_SUCCESS_AUTHORITY.md | unchanged |
| harness/run_corrective_v4_tests.py | unchanged |
| harness/run_corrective_v5_tests.py | `a3a1ad81f4e667d9f13f6ab13256d4a9168ab83f55f1e4bafdced77d33c09fa8` |
| harness/finalize_live_proof.py | `c06ac46b744cf2b9c7a9d07ef67babdb06ee6e894c3d773c28ebefbda825f2bc` |

## BF-ICT-RERUN-001 — Idempotency fingerprint

### Prepare fingerprint schema

`REQUEST_FINGERPRINT_SHA256` = SHA-256 of canonical JSON over:

```text
ORCHESTRATION_ID, CASE_ID, FINDING_ID, WORKER_ID, ATTEMPT,
PACKET_GENERATION, CHECKPOINT_GENERATION, PAYLOAD,
DEPENDENCY_PACKET_IDS, DEPENDENCY_HASHES (raw+canonical),
EXECUTION_MODE, ACTIVATION_STATE_HASH,
WORKER_CONTRACT_HASH, ALLOWED_WRITE_BOUNDARY_HASH,
EXPECTED_OUTPUT_PATH (relative)
```

`PREPARE_FINGERPRINT_SHA256` = SHA-256 of:

```text
REQUEST_FINGERPRINT_SHA256 + WORKER_EXECUTION_ID
+ INPUT_PACKET_RAW_SHA256 + INPUT_PACKET_CANONICAL_SHA256
```

Stored in: `DISPATCH_INTENT`, `CHECKPOINT` (`ACTIVE_*_FINGERPRINT`), `DISPATCH.jsonl` prepare records.

### Exact replay matrix

| Case | Result |
|------|--------|
| Same payload/deps/gens | `EXISTING_DISPATCH_INTENT_RETURNED` |
| No new WEX | YES |
| Checkpoint unchanged | YES |
| No route/dispatch append | YES |

### Divergent replay matrix

| Divergence | Status | Failure code |
|------------|--------|--------------|
| Payload / bytes | `BLOCKED_IDEMPOTENCY_INPUT_MISMATCH` | `IDEMPOTENCY_PREPARE_FINGERPRINT_MISMATCH` / `IDEMPOTENCY_INPUT_RAW_HASH_MISMATCH` |
| Dependency hashes | same | `IDEMPOTENCY_DEPENDENCY_HASH_MISMATCH` |
| Contract hash | same | `IDEMPOTENCY_CONTRACT_HASH_MISMATCH` |
| Write-boundary hash | same | `IDEMPOTENCY_WRITE_BOUNDARY_HASH_MISMATCH` |
| Output path | same | `IDEMPOTENCY_OUTPUT_PATH_MISMATCH` |
| Packet/checkpoint gen | same | `IDEMPOTENCY_*_GENERATION_MISMATCH` |

Rejected replay: `CHECKPOINT_CHANGED=NO`, `DISPATCH_INTENT_CREATED=NO`, `OWNER_RECEIPT_RESERVED=NO`.

### Pre-dispatch TOCTOU matrix

`validate_dispatch_intent_before_task(...)` re-checks input raw+canonical, dependency hashes, checkpoint generation, active WEX, prepare fingerprint.

| Case | Result |
|------|--------|
| Input mutated after prepare | `BLOCKED_DISPATCH_INTENT_INPUT_CHANGED` |
| Unchanged | `PASS` / `TASK_DISPATCH_ALLOWED=YES` |

## BF-ICT-RERUN-002 — Retry authority

### Retry authorization schema

Durable artifact under `team/retries/<RETRY_AUTHORIZATION_ID>.json`:

```text
RETRY_AUTHORIZATION_ID, PREVIOUS_WORKER_EXECUTION_ID,
PREVIOUS_TERMINAL_STATUS, PREVIOUS_ATTEMPT,
PREVIOUS_PACKET_GENERATION, PREVIOUS_CHECKPOINT_GENERATION,
PREVIOUS_INPUT_RAW_SHA256, PREVIOUS_INPUT_CANONICAL_SHA256,
NEXT_ATTEMPT, NEXT_PACKET_GENERATION, NEXT_CHECKPOINT_GENERATION,
AUTHORIZED_WORKER_ID, AUTHORIZED_AT, NONCE,
CONSUMED, CONSUMED_BY_NEW_WORKER_EXECUTION_ID
```

Exclusive lock file: `team/retries/by_prev_<WEX_SLUG>.json` (`O_CREAT|O_EXCL`).

### Authoritative previous-WEX sources

1. Original `DISPATCH_INTENT`
2. `DISPATCH.jsonl` mention
3. Checkpoint active binding (must match claimed previous)
4. Optional ROUTE-TRACE (used for RETRY_AUTHORIZED / RETRY_DISPATCH events)

Caller-supplied `PREVIOUS_WORKER_EXECUTION_ID` alone is insufficient.

### Previous-WEX validation matrix

| Case | Status |
|------|--------|
| Real TIMEOUT | `RETRY_AUTHORIZED` |
| Forged/unknown | `BLOCKED_RETRY_PREVIOUS_EXECUTION_NOT_FOUND` |
| Cross case/finding/orch | `BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH` |
| RUNNING | `BLOCKED_RETRY_PREVIOUS_EXECUTION_NOT_TERMINAL` |
| PASS | `BLOCKED_RETRY_STATUS_NOT_ELIGIBLE` |
| Wrong worker/attempt/pkg/hash | `BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH` |
| Duplicate auth | `BLOCKED_RETRY_AUTHORIZATION_DUPLICATE` |
| Consumed replay | `BLOCKED_RETRY_AUTHORIZATION_REPLAY` |

### Retry chain / branch matrix

| Case | Result |
|------|--------|
| WEX-1 → auth → WEX-2 | PASS (attempt/gen +1) |
| WEX-3 from WEX-1 after WEX-2 | `BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH` |
| One-time consume | `CONSUMED=true` bound to new WEX |
| Late previous output | `REJECTED_STALE_OUTPUT` |

## ICT AP-04 / AP-05 regression

| Probe | Result |
|-------|--------|
| ICT-RERUN-REG-AP04 | PASS — `BLOCKED_IDEMPOTENCY_INPUT_MISMATCH` |
| ICT-RERUN-REG-AP05 | PASS — `BLOCKED_RETRY_PREVIOUS_EXECUTION_NOT_FOUND` |

## Suite results

| Suite | Command | Total | Passed | Failed |
|-------|---------|------:|-------:|-------:|
| V5 | `python .cursor/pipeline/bug-team/harness/run_corrective_v5_tests.py` | 39 | 39 | 0 |
| V4 | `python .cursor/pipeline/bug-team/harness/run_corrective_v4_tests.py` | 29 | 29 | 0 |
| V3 | `python .cursor/pipeline/bug-team/harness/run_corrective_v3_tests.py` | 34 | 34 | 0 |
| V2 | `python .cursor/pipeline/bug-team/harness/run_corrective_tests.py` | 18 | 18 | 0 |
| Adversarial A1–A6 | included in V5 | 6 | 6 | 0 |

## Activation / product isolation

```text
RUNTIME_STATUS: NOT_ACTIVE
RUNTIME_ACTIVATED: NO
PRODUCT_APP_FILES_CHANGED: NONE
PRODUCT_TEST_FILES_CHANGED: NONE
OPENSPEC_PRODUCT_FILES_CHANGED: NONE
REAL_BUG_CASES_CREATED: NONE
COMMIT_CREATED_BY_CORRECTIVE_BUILDER: NO
```

## Known platform limitations

```text
CURSOR_TASK_CANCELLATION: PARTIAL_INTERRUPT_ON_RESUME
PROCESS_TREE_TERMINATION: BLOCKED_PLATFORM_TERMINATION_LIMITATION
SAFE_TIMEOUT_ENFORCEMENT: logical isolation only
```

## Blocking findings

```text
NONE (within V5 corrective builder scope)
```

## Non-blocking findings

```text
finalize_live_proof.py marked EXECUTION_CLASS=PROOF_HELPER / LIVE_RUNTIME_AUTHORITY=NONE
Independent Controlled Test V3 second rerun still required for external verdict
```

## ONE_NEXT_ACTION

```text
Independent Controlled Test V3 second rerun
```
