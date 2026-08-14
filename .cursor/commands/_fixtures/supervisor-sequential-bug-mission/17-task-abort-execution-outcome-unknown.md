# 17 — Platform Task abort → EXECUTION_OUTCOME_UNKNOWN (SUP-DEF-002)

```text
ACTIVE_FINDING: ROOT-001
DISPATCHED: /opsx-bug-team case=… mode=resume-family-fanout
TASK_TOOL_RESULT: aborted | interrupted | empty envelope
Side effects: possible (children may have written)
```

## Expected

```text
PAUSED
EXECUTION_OUTCOME_UNKNOWN
(or TIMEOUT if §12.0 clocks already exceeded)
ADVANCE: no
CLAIM_NEXT: no
no blind replay / duplicate GO
pasteable resume of SAME primary command required
ROOT-002 never starts
```
