# 18 — Prose GREEN without durable path rejected (SUP-DEF-003)

```text
FROM_STATE: AWAITING_GREEN
WORKER_ENVELOPE:
  STATUS: GREEN_CONFIRMED
  GREEN_EVIDENCE_PATH: (empty / absent)
  DURABLE_FILE_WRITTEN: (absent / no)
  prose: "tests passed, green confirmed"
```

## Expected

```text
RESULT_VALIDATION=REJECTED_RETRYABLE
FAILURE_CLASS=EVIDENCE_INCOMPLETE
(or ENVELOPE_INTEGRITY_FAIL)
ADVANCE: no
FINDING_TERMINAL: no
no claim-next
after retry exhaust → PAUSED
```
