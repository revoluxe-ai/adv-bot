# 25 — Manual abort after prior progress is not hang cause (SUP-LIVE-007)

## 25a — Abort of an in-flight attempt (no prior NO_PROGRESS)

```text
TASK RUNNING with PRIMARY_TASK_HANDLE awaitable
TASK_TOOL_RESULT: User aborted/interrupted manually
no SUPERVISOR_NO_PROGRESS recorded before abort
```

### Expected 25a

```text
PAUSED
EXECUTION_OUTCOME_UNKNOWN
PRIOR_NO_PROGRESS_DETECTED=NO
ADVANCE=no
CLAIM_NEXT=no
```

## 25b — Abort after already-recorded NO_PROGRESS

```text
SUPERVISOR_NO_PROGRESS already recorded (fingerprint stall)
later transcript: User aborted/interrupted manually
```

### Expected 25b

```text
manual abort classifies THAT later attempt only
MANUAL_ABORT_EXPLAINS_PRIOR_NO_PROGRESS=FORBIDDEN
keep SUPERVISOR_NO_PROGRESS as the liveness finding
do not rewrite hang cause to Owner abort
```
