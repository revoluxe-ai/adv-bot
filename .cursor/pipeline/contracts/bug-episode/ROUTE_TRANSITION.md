# ROUTE_TRANSITION — machine-readable hop packet

```text
SCHEMA: bug-episode/ROUTE_TRANSITION
AUTHORITY: ORCHESTRATION_MVP Routes A–D + producing command
CONSUMER: /opsx-supervisor (BUG_MISSION sequential reducer)
IMPLEMENTATION_STATUS: LIVE_ACTIVATED
```

## Role

Canonical **structured transition** emitted by bug-episode worker commands
(`/opsx-classify-bug`, `/opsx-fix-bug`, `/opsx-test`, `/opsx-update`,
`/opsx-claim-next-bug`, materialize close, etc.).

Supervisor **consumes** this packet. Narrative `Next command:` / prose stop
conditions are human UX only and MUST NOT override a present structured
`ROUTE_TRANSITION`.

```text
NEXT_TRANSITION
=
transition(durable_current_state, verified_ROUTE_TRANSITION)
```

Forbidden:

```text
NEXT_TRANSITION = LLM interpretation of worker prose
```

## Packet shape

```text
ROUTE_TRANSITION

FROM_STATE:
RESULT:
TO_STATE:

NEXT_COMMAND:
NEXT_ARGS:

PRECONDITIONS:
  GO_TOKEN: FORBIDDEN | REQUIRED | NOT_APPLICABLE
  CLAIM_REQUIRED: yes | no
  RED_REQUIRED: yes | no | not_applicable
  GREEN_REQUIRED: yes | no | not_applicable
  OTHER: <optional machine keys>

REQUIRED_EVIDENCE:
  - <evidence kind / path field>

ON_SUCCESS_STATE:
ON_FAILURE_STATE:

RECOVERY_COMMAND:
RECOVERY_CLASS: ADVANCE | RETRY_ALLOWED | PAUSED | BLOCKED | NEEDS_OWNER | TERMINAL

MISSION_COMPLETE: no | yes
FINDING_TERMINAL: no | yes
FINDING_TERMINAL_KIND:
  CLOSED_GREEN
  | CLOSED_FALSE_POSITIVE
  | ROUTED_OUT_OF_SCOPE
  | CLOSED_WITH_ACCEPTED_DISPOSITION
  | none
```

## Rules

1. `MISSION_COMPLETE: yes` on a **worker** hop is forbidden unless the
   producer is explicitly the mission reducer proving all-findings-terminal
   (supervisor). Worker commands default `MISSION_COMPLETE: no`.
2. `TERMINAL_STATUS: PASS` on a command ≠ `FINDING_TERMINAL: yes`.
3. If `NEXT_COMMAND` and mandatory `PRECONDITIONS` / route contract
   contradict → supervisor MUST NOT guess:

```text
PAUSED
ROUTE_CONTRACT_CONFLICT
```

4. Prefer extending `ROUTE-TRACE.jsonl` with these fields (or a nested
   `ROUTE_TRANSITION` object) over a second history store.
5. Route **semantics** (which command follows Route A/B/C/D) live in
   `ORCHESTRATION_MVP.md` and producing commands — not in supervisor policy.

## Envelope identity (supervisor validation minimum)

Before applying a transition, supervisor verifies:

```text
MISSION_ID / TASK_ID (when mission mode)
COMMAND == dispatched command
CASE_ID == active case
FINDING_ID == ACTIVE_FINDING_ID
claim identity still valid when CLAIM_REQUIRED
CURRENT_CLASSIFICATION / CHOSEN_ROUTE when applicable
CURRENT_ROUTE_STATE / FROM_STATE consistent with durable snapshot
TERMINAL_STATUS present
NEXT_COMMAND / transition present or TERMINAL
MISSION_COMPLETE == no for ordinary workers
required evidence refs present when REQUIRED_EVIDENCE non-empty
for RED / GREEN / CLOSE hops: non-empty evidence path field
  (RED_EVIDENCE_PATH | GREEN_EVIDENCE_PATH | OWNER-CLOSURE path)
  AND DURABLE_FILE_WRITTEN=YES (worker attestation)
  — prose-only STATUS without path/attestation → reject (not ADVANCE)
```

Mismatch →:

```text
PAUSED
ENVELOPE_INTEGRITY_FAIL
```

Evidence-incomplete GREEN/CLOSE (missing path or
`DURABLE_FILE_WRITTEN`) may also be classified
`RESULT_VALIDATION=REJECTED_RETRYABLE` per `/opsx-supervisor` §9.1
before PAUSED on retry exhaustion.

## Alias note (state names)

Producers historically use both:

```text
AWAITING_FIX_BUG          # classify Route A seed (adjudication WITHOUT GO)
AWAITING_FIX_BUG_RED      # post-TASK_DELTA / RED-gated executor wait
```

Do **not** silently normalize in supervisor. Treat as distinct unless
ORCHESTRATION_MVP documents an explicit alias table.

## FINDING_TERMINAL_KIND ↔ durable STATUS map

Supervisor / CLOSE_POLICY accept either side via this table (one SoT —
kinds live here; durable statuses remain CLOSE_POLICY / materialize):

| FINDING_TERMINAL_KIND (envelope) | Durable finding STATUS / disposition |
|---|---|
| `CLOSED_GREEN` | `closed_fixed` (after GREEN + close evidence) |
| `CLOSED_FALSE_POSITIVE` | `closed_false_positive` |
| `ROUTED_OUT_OF_SCOPE` | `OUT_OF_SCOPE` / `ROUTE_TO_OTHER_PROCESS` with evidence |
| `CLOSED_WITH_ACCEPTED_DISPOSITION` | Owner-accepted terminal disposition (documented) |
| `none` | non-terminal |

`FINDING_TERMINAL: yes` without a mapped kind → treat as incomplete envelope
(`ENVELOPE_INTEGRITY_FAIL` or `PAUSED`), not silent close.
