# SUPERVISOR_POLICY — orchestration execution policy (not route semantics)

```text
SCHEMA: bug-episode/SUPERVISOR_POLICY
CONSUMER: /opsx-supervisor BUG_MISSION mode
IMPLEMENTATION_STATUS: LIVE_ACTIVATED
```

## Role

Controls **how** the supervisor executes a multi-finding bug mission.

Does **not** encode product/bug route semantics (Route A/B/C/D next commands,
skip-test heuristics, etc.). Those belong to `ORCHESTRATION_MVP.md` and
worker `ROUTE_TRANSITION` envelopes.

## v1 policy object

```text
SUPERVISOR_POLICY

execution_strategy: sequential
route_authority: worker_transition_envelope
max_active_findings: 1

on_blocked: stop
on_paused: stop
on_needs_owner: stop
on_worker_failure: stop

require_claim: yes
require_evidence_for_transition: yes
require_terminal_evidence_for_close: yes

mission_completion: queue_exhausted_and_all_terminal
```

## Allowed vs forbidden options

### Allowed (execution policy)

```text
execution_strategy=sequential
max_active_findings=1
on_blocked=stop
on_paused=stop
on_needs_owner=stop
on_worker_failure=stop
require_claim=yes
```

### Forbidden (route / product semantics as options)

```text
route_a_next=/opsx-fix-bug
route_b_next=/opsx-update
skip_test_for_simple_bug=true
scenario=implementation_bug → classify → test → fix
```

Encoding workflows as supervisor options creates a second route authority.

## Sequential invariant (v1)

```text
MAX_ACTIVE_FINDINGS: 1
ACTIVE_FINDING_ID = zero or one finding
```

While active finding is non-terminal:

```text
MUST NOT claim/start another finding
```

After terminal closure (with required evidence):

```text
clear ACTIVE_FINDING_ID
→ select NEXT_ELIGIBLE_FINDING (claim-next order)
```

Queue order authority: `/opsx-claim-next-bug` deterministic selection
(`CLAIM_PRIORITY` → ledger order → `FINDING_ID`). Do not invent severity
heuristics in supervisor.

## Mission completion proof

`MISSION_COMPLETE: yes` only when **all** hold (machine-checkable):

```text
all materialized findings have terminal dispositions
AND no active/orphan claim remains
AND no required recovery is pending
AND queue contains no eligible unresolved finding
```

Forbidden:

```text
one worker PASS → MISSION_COMPLETE
```

Finding terminal kinds (see `ROUTE_TRANSITION.md` / `CLOSE_POLICY.md`):

```text
CLOSED_GREEN
CLOSED_FALSE_POSITIVE
ROUTED_OUT_OF_SCOPE
CLOSED_WITH_ACCEPTED_DISPOSITION
```

(or canonical durable equivalents: `closed_fixed`, `closed_false_positive`,
`OUT_OF_SCOPE` / `ROUTE_TO_OTHER_PROCESS` with evidence).

## Recovery enum

Every non-terminal execution reduces to exactly one of:

```text
ADVANCE
RETRY_ALLOWED
PAUSED
BLOCKED
NEEDS_OWNER
TERMINAL
```

No implicit continuation after failure. Retry requires
`RETRY_ALLOWED: yes` plus idempotency / execution identity; else `PAUSED`.

Unknown writer outcome (side effects possible, envelope not committed):

```text
PAUSED
EXECUTION_OUTCOME_UNKNOWN
```

No blind replay.

### Platform Task abort / interrupt (same recovery)

Top-level Cursor Task ending as `aborted` | `interrupted` | `tool_error`
| empty envelope (Owner tool cancel, platform kill, mid-flight interrupt)
maps to the same recovery — including when the primary command is
`/opsx-bug-team` or `/opsx-static-check`:

```text
PAUSED
EXECUTION_OUTCOME_UNKNOWN
ADVANCE: no
CLAIM_NEXT: no
BLIND_REPLAY: no
```

If supervisor hang clocks are exceeded first → `TIMEOUT` (stricter) with
the same bans. Pasteable resume of the **same** primary command is
required; do not invent success or skip to the next finding.

Authority for numeric clocks / Owner-visible long-orchestrator rules:
`/opsx-supervisor` §12.0–§12.4.

## Top-level hang clocks (policy pointer)

```text
ordinary hop defaults: TIMEOUT=1800s NO_PROGRESS=600s
internal orchestrator defaults: TIMEOUT=3600s NO_PROGRESS=900s
empty clocks: FORBIDDEN
```

Exact field names and STOP_ACK / HEARTBEAT live in `/opsx-supervisor` §12.0.

## SUPERVISOR_EVENT (prefer ROUTE-TRACE)

Minimal event fields (append via existing ROUTE-TRACE conventions when
possible):

```text
SUPERVISOR_EVENT
MISSION_ID
CASE_ID
FINDING_ID
PREVIOUS_STATE
WORKER_COMMAND
WORKER_EXECUTION_ID
WORKER_RESULT_REF
NEW_STATE
NEXT_COMMAND
DISPOSITION
```

Do not create a competing history system if `ROUTE-TRACE.jsonl` already
owns the episode.
