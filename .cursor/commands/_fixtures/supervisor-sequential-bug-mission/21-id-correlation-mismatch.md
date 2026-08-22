# 21 — Correlation: optional IDs vs mandatory handle (SUP-LIVE-003)

## 21a — Optional IDs absent (must PASS identity)

```text
PRIMARY_TASK_HANDLE: handle-abc  (matches launch)
PLATFORM_TASK_ID: absent
PLATFORM_AGENT_ID: absent
TASK_ID / ATTEMPT: match
```

### Expected 21a

```text
IDENTITY_VALID=YES
ENVELOPE_INTEGRITY_FAIL=NO
absence of optional platform IDs is NOT integrity fail
```

## 21b — Known mandatory handle mismatch (must FAIL)

```text
LAUNCH PRIMARY_TASK_HANDLE: handle-abc
RESULT bound to: handle-xyz
```

### Expected 21b

```text
PAUSED
ENVELOPE_INTEGRITY_FAIL
attempt MUST leave RUNNING
no silent wait on stale handle
```
