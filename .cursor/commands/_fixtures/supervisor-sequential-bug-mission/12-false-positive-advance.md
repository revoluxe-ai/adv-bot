# 12 — T13 false positive advances queue

```text
CLASSIFY: FALSE_POSITIVE
ROUTE_TRANSITION:
  FINDING_TERMINAL: yes
  FINDING_TERMINAL_KIND: CLOSED_FALSE_POSITIVE
  NEXT_COMMAND: CLOSED_NO_IMPLEMENTATION
  MISSION_COMPLETE: no
QUEUE: ROOT-002 eligible
```

## Expected

```text
close ROOT-001 with evidence
clear ACTIVE_FINDING_ID
select ROOT-002
MUST NOT dispatch /opsx-fix-bug
```
