# TASK_DELTA schema (post-/opsx-update)

```text
SCHEMA: bug-episode/TASK_DELTA
POLICY_SOT: .cursor/pipeline/ORCHESTRATION_MVP.md
RUNTIME_PATH (recommended):
  .tmp/opsx-bug-cases/<CASE_ID>/results/TASK-DELTA-<FINDING_ID>.md
```

## Role

Durable decision after `/opsx-update` on a bug-episode spec route
(`SPEC_BUG` | `SPEC_GAP`). Chooses the expected implementation executor:

```text
TASK_DELTA: CHANGED   → EXPECTED_EXECUTION_ROUTE: /opsx-apply
TASK_DELTA: UNCHANGED → EXPECTED_EXECUTION_ROUTE: /opsx-fix-bug
```

`/opsx-update` revises specification only. It is **not** production GO and
does **not** replace the implementation executor.

## Canonical vocabulary

```text
TASK_DELTA:
  CHANGED
  UNCHANGED
```

Do **not** write competing normative pairs such as `YES`/`NO` or
`TASK_DELTA_DETECTED` in **new** artifacts.

### Legacy read compatibility

Older packets may still say:

```text
TASK_DELTA_DETECTED: YES | NO
```

Readers MAY map:

```text
YES → CHANGED
NO  → UNCHANGED
```

Writers of new evidence MUST emit only `CHANGED` | `UNCHANGED`.

## Required fields

```text
CASE_ID:
FINDING_ID:
CHANGE_ID:
COMPARED_AT_UTC:
BASELINE_TASKS_REF:

SPEC_FILES_CHANGED: []
TASK_FILES_INSPECTED: []

TASKS_BEFORE: []
TASKS_AFTER: []

NEW_TASKS: []
CHANGED_TASKS: []
REMOVED_TASKS: []

TASK_DELTA: CHANGED | UNCHANGED

EXPECTED_EXECUTION_ROUTE:
  /opsx-apply
  | /opsx-fix-bug

TASK_DELTA_EVIDENCE_PATH:
  .tmp/opsx-bug-cases/<CASE_ID>/results/TASK-DELTA-<FINDING_ID>.md

DECISION_REASON:

# Optional close / handback (see CLOSE_POLICY.md); persist on ROUTE_STATE too
CLOSE_FINDING_INTENT: auto_after_green | ask_after_green | never
POST_GREEN_OWNER: bug-team | solo
HANDBACK_COMMAND: /opsx-bug-team case=<CASE_ID> mode=<resume-family-fanout|continue>
```

Optional list mirrors (informational):

```text
TASK_IDS_ADDED
TASK_IDS_CHANGED
TASK_IDS_REMOVED
```

## Detection rule

```text
TASK_DELTA: CHANGED
  iff any of NEW_TASKS / CHANGED_TASKS / REMOVED_TASKS is non-empty

TASK_DELTA: UNCHANGED
  iff no added/changed/removed implementation tasks
```

Checkbox-only progress (`[ ]` → `[x]`) without requirement text change is
**not** a task delta for this gate unless Owner notes otherwise.

## Route selection + reconciliation seed

After writing TASK_DELTA evidence, append ROUTE-TRACE event
`task_delta_decision` with:

```text
TASK_DELTA: CHANGED | UNCHANGED

If CHANGED:
  EXPECTED_EXECUTION_ROUTE: /opsx-apply
  EXPECTED_NEXT_COMMAND: /opsx-apply
  CURRENT_ROUTE_STATE: AWAITING_APPLY_RED

If UNCHANGED:
  EXPECTED_EXECUTION_ROUTE: /opsx-fix-bug
  EXPECTED_NEXT_COMMAND: /opsx-fix-bug
  CURRENT_ROUTE_STATE: AWAITING_FIX_BUG_RED

ACTUAL_EXECUTION_ROUTE: PENDING
ROUTE_RECONCILIATION: PENDING
ACTUAL_NEXT_COMMAND: PENDING
NEXT_COMMAND_RECONCILIATION: PENDING
```

Never write `/opsx-update` into `EXPECTED_EXECUTION_ROUTE` or
`ACTUAL_EXECUTION_ROUTE`.

## Downstream gates (unchanged)

Selecting `/opsx-apply` or `/opsx-fix-bug` does **not** authorize production
edits. Both executors still require:

```text
BUG_CONFIRMED
AND FIX_NOW
AND (
  RED_CONFIRMED
  OR RED_NOT_APPLICABLE_APPROVED
)
AND OWNER_PRODUCTION_GO
```

before production implementation.

Executor start MUST set `ACTUAL_EXECUTION_ROUTE` and compute
`ROUTE_RECONCILIATION` (`MATCH` | `MISMATCH`). Mismatch →
`BLOCKED_ROUTE_MISMATCH` (no silent close / no production GO).
```
