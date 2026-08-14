# 15 — PLANFIT regression (SUP-ASEP-FULL-ENV-002)

```text
MISSION_ID: SUP-ASEP-FULL-ENV-002
CASE_ID: BUGCASE-ASEP-PLANFIT-20260812T063329Z
FINDING_ID: ROOT-001
NOTE: live case may be absent on disk; this fixture is structural SoT for dry-run
```

## Classify envelope (structural)

```text
CURRENT_CLASSIFICATION: IMPLEMENTATION_BUG
CHOSEN_ROUTE: ROUTE_A
CURRENT_ROUTE_STATE: AWAITING_FIX_BUG
EXPECTED_NEXT_COMMAND: /opsx-fix-bug
TERMINAL_STATUS: PASS
MISSION_COMPLETE: no
FINDING_TERMINAL: no

ROUTE_TRANSITION:
  NEXT_COMMAND: /opsx-fix-bug
  NEXT_ARGS: WITHOUT GO
  PRECONDITIONS.GO_TOKEN: FORBIDDEN
  PRECONDITIONS.RED_REQUIRED: not_applicable
  RECOVERY_CLASS: ADVANCE
```

Prose stop «no /opsx-fix-bug GO until RED» is UX only — does not change
NEXT_COMMAND to /opsx-test.

## Expected supervisor behavior

```text
1. consume structured ROUTE_TRANSITION (not prose)
2. MISSION_COMPLETE: no
3. NEXT_COMMAND=/opsx-fix-bug WITHOUT GO (not guessed /opsx-test)
4. after ROOT-001 terminal → select next unresolved finding if any
5. no prose-driven transition
```

If producer omitted GO_TOKEN=FORBIDDEN and prose demands RED-first as competing
NEXT → PAUSED ROUTE_CONTRACT_CONFLICT (fixture 07).
