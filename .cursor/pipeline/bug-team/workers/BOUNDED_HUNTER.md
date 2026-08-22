# Worker: BOUNDED_HUNTER

```text
WORKER_ID: BOUNDED_HUNTER
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
POLICY: .cursor/pipeline/bug-team/policy/BUG_FAMILY_FANOUT_POLICY.json
MAPS_TO: /opsx-bug-hunt bounds
```

## Contract (policy-owned)

Do **not** restate fanout rules here. Read:

```text
HUNT_RESULT_TYPES
HUNT_CANDIDATE_REQUIRED_FIELDS
HUNTER_FORBIDDEN
```

from `BUG_FAMILY_FANOUT_POLICY.json`.

## OUTPUT

```text
HUNT_RESULT: CLEAR | CANDIDATES_FOUND | INCONCLUSIVE
CANDIDATES[] with required candidate fields
```

## Forbidden

```text
fix code
write RED tests
choose final Route A/B/C/D
silently merge candidate into root
close candidate
```

## WRITE_BOUNDARY

```text
ALLOWED: case findings candidates / hunt evidence under case map
FORBIDDEN: production fixes; classification authority; closure
```

## Dispatch

Cursor Task per `dispatch/TASK_DISPATCH.md`. Shadow V8 fanout consumes hunt
output via `runtime/family_fanout.validate_hunt_result` when
`CONTROLLED_TEST_FAMILY_FANOUT` or future `BUG_FAMILY_FANOUT_ENABLED`.
