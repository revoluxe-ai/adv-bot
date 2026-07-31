# Episode terminal ↔ durable LEDGER map

```text
DURABLE_STATUS model: parallel EPISODE_TERMINAL
Claim matrix / existing STATUS values: UNCHANGED
```

## Episode terminals

```text
FIXED
REJECTED
DUPLICATE
DEFERRED
BLOCKED
TIMEOUT
TEST_NOT_REPRODUCING
RED_NOT_APPLICABLE
```

## Mapping

| Episode terminal (`EPISODE_TERMINAL`) | Closest durable `STATUS` today | FAN_IN_ELIGIBLE_TERMINAL? |
|---|---|---|
| FIXED | `closed_fixed` + RED/GREEN linkage | yes (with evidence) |
| REJECTED | `closed_false_positive` / plan-only closed | yes |
| DUPLICATE | `duplicate_*` / `absorbed_*` / `duplicate_root_observation` | yes |
| DEFERRED | `backlog` | yes (not class closed) |
| BLOCKED | `blocked` | yes (not class closed) |
| TIMEOUT | parallel field only (no claim-status rename) | yes (not class closed) |
| TEST_NOT_REPRODUCING | parallel field; may keep claim STATUS | yes |
| RED_NOT_APPLICABLE | parallel + Owner `RED_NOT_APPLICABLE_APPROVED` | yes (conditional) |

## Rules

- Closing a branch ≠ closing the error class ≠ lesson gate pass.
- `FAN_IN_ELIGIBLE_TERMINAL` means the branch may be included in fan-in
  rollup; it does **not** grant `LESSON_GATE_PASS`.
- Do not change claim `STATUS` vocabulary to encode episode terminals in
  this increment — use `EPISODE_TERMINAL` on finding/LEDGER/BRANCH_REGISTRY.
