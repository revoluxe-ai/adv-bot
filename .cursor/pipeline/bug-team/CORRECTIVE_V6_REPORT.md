# Corrective V6 Report — BF-ICT-SR-001 Copy/Replay

```text
STATUS: OPSX_BUG_TEAM_CORRECTIVE_V6_IMPLEMENTED
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
OWNER_ACTIVATION: NOT_ISSUED
REAL_BUG_EXECUTION_ALLOWED: NO
COMMIT_ALLOWED: NO
INDEPENDENT_TESTER_PASS: NOT_ISSUED
```

Evidence:

```text
.tmp/opsx-bug-team-harness/corrective-v6/20260728T063029Z/

Controlling FAIL:

```text
.tmp/opsx-bug-team-harness/independent-controlled-test-v3-second-rerun/ICT-V3SR-20260728T060645Z/
adversarial/AP10_FINDING.md
```

## Candidate hashes before (V5 baseline)

| Path | SHA-256 |
|------|---------|
| runtime/live_task_hop.py | `c90ef1b9bce37a8a0ee303d5cbba28425fede3ec17f6eb870873f8e10c46f620` |
| runtime/route_trace.py | `bed1a80c3ef2d213d55b73fbd5ae4f2952a6902026826125fd27253f2d7ed4ba` |
| runtime/packets.py | `22efbae1e9bdc3cd733ccf6fe323793de8cc6e07c21d03c50ba2629264f8cc56` |
| runtime/orchestrator.py | `2a121b354a15ad8647f75076d758078c9901e9bad364bd6f679110fbc925284c` |
| harness/run_corrective_v5_tests.py | `a3a1ad81f4e667d9f13f6ab13256d4a9168ab83f55f1e4bafdced77d33c09fa8` |

## Candidate hashes after

See `CANDIDATE_HASHES_AFTER.json` in evidence root. Changed:

- `runtime/live_task_hop.py` — reserve/consume via registry
- `runtime/retry_auth.py` — **new**
- `harness/run_corrective_v6_tests.py` — **new**
- `harness/run_corrective_v5_tests.py` — RETRY-14 asserts registry RESERVED (not mutable receipt CONSUMED)

Unchanged: route_trace, packets, orchestrator.

## Immutable receipt schema

Receipt at canonical path is issuance evidence only:

```text
SCHEMA_VERSION, RETRY_AUTHORIZATION_ID, NONCE,
ORCHESTRATION_ID, CASE_ID, FINDING_ID, WORKER_ID,
PREVIOUS_*, NEXT_*,
ISSUED_AT, EXPIRES_AT,
CANONICAL_RECEIPT_PATH,
HOST_SIGNATURE, RECEIPT_RAW_SHA256, RECEIPT_CANONICAL_SHA256
```

`CONSUMED` / `RESERVED` are **not** authoritative receipt fields.

## Canonical path derivation

```text
<case_root>/team/retries/<RETRY_AUTHORIZATION_ID>.json
```

Validator requires `actual_path == CANONICAL_RECEIPT_PATH`. Arbitrary supplied paths are never used.

## Retry registry schema

```text
team/retries/RETRY-AUTH-REGISTRY.jsonl
```

Append-only, host-signed events (`HOST_EVENT_SIGNATURE`). Identity: `RETRY_AUTHORIZATION_ID + NONCE`.

Events: `RETRY_AUTH_ISSUED | RESERVED | CONSUMED | EXPIRED | REJECTED`.

## Registry transition table

| From | To |
|------|-----|
| (none) | ISSUED |
| ISSUED | RESERVED, EXPIRED |
| RESERVED | CONSUMED, EXPIRED |
| CONSUMED | ∅ |
| EXPIRED | ∅ |

Invalid history / unsigned rewrite → `BLOCKED_RETRY_AUTHORIZATION_REGISTRY_INVALID`.

## Nonce uniqueness

On ISSUED: duplicate `NONCE` or `RETRY_AUTHORIZATION_ID` rejected (`BLOCKED_RETRY_NONCE_ALREADY_EXISTS` / `BLOCKED_RETRY_AUTHORIZATION_ID_ALREADY_EXISTS`).

## Host signature

HMAC-SHA256 over immutable receipt fields using `team/retries/.host_retry_authority` (never logged / traced / dispatched).

## AP-10 literal reproduction

```text
ICT-SR-REG-AP10: PASS
copy receipt + CONSUMED=false + forge READY_FOR_RETRY → rejected
no WEX-3; no new dispatch intent
```

## V6 test matrix

| Group | Count | Result |
|-------|------:|--------|
| V6-REPLAY-01..08 | 8 | PASS |
| V6-REG-01..08 | 8 | PASS |
| V6-STATE-01..06 | 6 | PASS |
| ICT-SR-REG-AP10 | 1 | PASS |
| V6-ADV-A1..A8 | 8 | PASS |
| **Total** | **31** | **31/31** |

## Regressions

| Suite | Total | Passed | Failed |
|-------|------:|-------:|-------:|
| V5 | 39 | 39 | 0 |
| V4 | 29 | 29 | 0 |
| V3 | 34 | 34 | 0 |
| V2 | 18 | 18 | 0 |

AP-04 PASS, AP-05 PASS, AP-10 PASS.

## Activation / isolation

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
Host signature protects Candidate protocol authority, not OS-owner adversary
```

## Blocking findings

```text
NONE (within V6 corrective builder scope)
```

## Non-blocking findings

```text
Independent Controlled Test V3 third rerun still required
```

## ONE_NEXT_ACTION

```text
Independent Controlled Test V3 third rerun
```
