# Live success authority inventory (BF-ICT-002)

```text
SCHEMA: opsx-bug-team/LIVE_SUCCESS_AUTHORITY
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
```

## LIVE_SUCCESS_AUTHORITY_PATHS

```text
- runtime/live_task_hop.py::finalize_live_hop
```

Only this function may:

- accept worker output for live Cursor Task execution
- mark execution PASS
- advance checkpoint / COMPLETED_HOPS
- append WORKER_COMPLETED success transition
- consume Owner production receipt
- permit subsequent dependent prepare (via ACTIVE_STATUS=IDLE)

## LEGACY_NON_AUTHORITY_PATHS

```text
- runtime/orchestrator.py::finalize_after_task
    STATUS: BLOCKED_LEGACY_FINALIZE_DISABLED
    LIVE_TRANSITION_AUTHORITY: NONE

- runtime/packets.py::validate_packet
    LIVE_TRANSITION_AUTHORITY: NONE
    (parser / static helper only)

- harness/task_dispatch.py
    EXECUTION_CLASS: SIMULATED_BACKEND
    LIVE_RUNTIME_AUTHORITY: NONE

- harness/finalize_live_proof.py
    LIVE_RUNTIME_AUTHORITY: NONE
    (isolated V2 proof helper; not production success path)
```

## MULTIPLE_AUTHORITIES

If a second production-authoritative success path is found:

```text
STATUS: BLOCKED_MULTIPLE_LIVE_SUCCESS_AUTHORITIES
```
