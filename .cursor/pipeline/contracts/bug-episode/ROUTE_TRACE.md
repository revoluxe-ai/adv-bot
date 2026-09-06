# ROUTE_TRACE schema (append-only)

```text
SCHEMA: bug-episode/ROUTE_TRACE
SCHEMA_VERSION: 2
POLICY_SOT: .cursor/pipeline/ORCHESTRATION_MVP.md
RUNTIME_PATH:
  .opsx/runs/bug-cases/<CASE_ID>/results/ROUTE-TRACE.jsonl
```

## Role

Append-only durable team route history for product/logic bug episodes.

Supports:

```text
exact episode reconstruction
expected-vs-actual route comparison
agent/chat handoff analysis
stage duration analysis
Owner waiting-time analysis
BLOCKED/TIMEOUT analysis
silent route mismatch prevention
```

Each significant OPSX command or Owner decision gate appends **exactly one**
JSON object (one JSONL line). Never rewrite, delete, or mutate prior events.

Human-readable current snapshot lives in `LEDGER.md` → `## ROUTE_STATE`
and does **not** replace this file. Snapshot MUST align with the latest
applicable JSONL event.

## Event ordering

```text
EVENT_SEQUENCE:
  monotonically increasing integer per CASE_ID (1, 2, 3, …)
  never reuse; never renumber prior events

EVENT_ID:
  unique within CASE_ID (recommended globally unique)
  preferred form: RTE/<CASE_ID>/<EVENT_SEQUENCE>
  or RTE/<CASE_ID>/<UTC>/<EVENT_SEQUENCE>

PREVIOUS_EVENT_ID:
  required except for the first event in the case
  first event: NOT_APPLICABLE or null
```

Forbidden:

```text
rewrite existing history
reuse EVENT_SEQUENCE
silently delete an event
change an old route decision
```

## Required event fields

Every event MUST include identity/order fields (never omit):

```text
SCHEMA_VERSION
EVENT_ID
EVENT_SEQUENCE

CASE_ID
FINDING_ID
ROOT_FINDING_ID

EVENT_TYPE
COMMAND
COMMAND_MODE

ACTOR_ROLE
ACTOR_AGENT_ID
ACTOR_CHAT_ID

FROM_STATE
TO_STATE

STARTED_AT
TERMINAL_STATUS
```

Full field set (use `NOT_APPLICABLE` or `null` when not applicable — do not
silently drop required identity fields):

```json
{
  "SCHEMA_VERSION": "2",
  "EVENT_ID": "RTE/<CASE_ID>/<EVENT_SEQUENCE>",
  "EVENT_SEQUENCE": 1,

  "CASE_ID": "<CASE_ID>",
  "FINDING_ID": "<FINDING_ID or null>",
  "ROOT_FINDING_ID": "<ROOT_FINDING_ID or null>",

  "EVENT_TYPE": "<see vocabulary>",
  "COMMAND": "</opsx-… or OWNER_DECISION>",
  "COMMAND_MODE": "<mode or NOT_APPLICABLE>",

  "ACTOR_ROLE": "<Classifier|Claimer|Executor|Owner|…>",
  "ACTOR_AGENT_ID": "<id or CURRENT_CHAT_AGENT>",
  "ACTOR_CHAT_ID": "<stable durable chat label>",

  "FROM_STATE": "<durable state before>",
  "TO_STATE": "<durable state after>",

  "CLASSIFICATION": "<IMPLEMENTATION_BUG|SPEC_BUG|SPEC_GAP|FALSE_POSITIVE|OUT_OF_SCOPE|NOT_APPLICABLE|null>",

  "CHOSEN_ROUTE": "<ROUTE_A|ROUTE_B|ROUTE_C|ROUTE_D|NOT_APPLICABLE|null>",
  "EXPECTED_NEXT_COMMAND": "</opsx-update|/opsx-fix-bug|/opsx-apply|CLOSED_NO_IMPLEMENTATION|ROUTE_TO_OTHER_PROCESS|PENDING|NOT_APPLICABLE|null>",
  "ACTUAL_NEXT_COMMAND": "</opsx-update|/opsx-fix-bug|/opsx-apply|CLOSED_NO_IMPLEMENTATION|ROUTE_TO_OTHER_PROCESS|PENDING|NOT_APPLICABLE|null>",
  "NEXT_COMMAND_RECONCILIATION": "PENDING|MATCH|MISMATCH|NOT_APPLICABLE",

  "EXPECTED_EXECUTION_ROUTE": "</opsx-fix-bug|/opsx-apply|PENDING_UNTIL_TASK_DELTA|ROUTE_TO_OTHER_PROCESS|CLOSED_NO_IMPLEMENTATION|NOT_APPLICABLE|PENDING|null>",
  "ACTUAL_EXECUTION_ROUTE": "</opsx-fix-bug|/opsx-apply|PENDING|NOT_APPLICABLE|null>",
  "ROUTE_RECONCILIATION": "PENDING|MATCH|MISMATCH|NOT_APPLICABLE",
  "RECONCILIATION_REASON": "<bounded text or NOT_APPLICABLE>",

  "REJECTED_ROUTES": [],
  "REJECTED_ROUTE_REASONS": {},

  "TASK_DELTA": "CHANGED|UNCHANGED|NOT_APPLICABLE",
  "TASK_DELTA_EVIDENCE_PATH": "<path or NOT_APPLICABLE>",

  "OWNER_GATE_STATUS": "NOT_APPLICABLE|NOT_ISSUED|WAITING|APPROVED|REJECTED",
  "OWNER_GATE_OPENED_AT": "<ISO-8601|null|NOT_APPLICABLE>",
  "OWNER_GO_ISSUED_AT": "<ISO-8601|null|NOT_APPLICABLE>",
  "OWNER_WAIT_DURATION_MS": null,

  "STARTED_AT": "<ISO-8601>",
  "LAST_PROGRESS_AT": "<ISO-8601|null>",
  "COMPLETED_AT": "<ISO-8601|null>",
  "DURATION_MS": null,

  "TERMINAL_STATUS": "<see vocabulary>",
  "BLOCKED_REASON": "<token or NOT_APPLICABLE>",
  "TIMEOUT_CLASSIFICATION": "<token or NOT_APPLICABLE>",
  "RETRY_COUNT": 0,

  "EVIDENCE_PATHS": [],
  "PREVIOUS_EVENT_ID": "<EVENT_ID or NOT_APPLICABLE>",

  "ROUTE_TARGET_PROCESS_ID": "<id or NOT_APPLICABLE>",
  "ROUTE_TARGET_REASON": "<text or NOT_APPLICABLE>"
}
```

JSON producers MAY emit snake_case mirrors of the same semantics, but the
normative field names above MUST appear (uppercase as shown) in durable
events written after this schema version.

### Nullability

Fields that do not apply to a hop use:

```text
NOT_APPLICABLE
```

or `null` when the schema cell allows it.

Never omit:

```text
EVENT_ID
EVENT_SEQUENCE
CASE_ID
FINDING_ID
EVENT_TYPE
COMMAND
ACTOR_ROLE
FROM_STATE
TO_STATE
STARTED_AT
TERMINAL_STATUS
```

(`FINDING_ID` may be JSON `null` for case-level hops such as fan-in /
intake-only materialize.)

## Route layers (analytics)

Do not collapse these three layers into one field:

```text
CHOSEN_ROUTE:
  high-level classification route ROUTE_A | ROUTE_B | ROUTE_C | ROUTE_D

EXPECTED_NEXT_COMMAND / ACTUAL_NEXT_COMMAND / NEXT_COMMAND_RECONCILIATION:
  immediate process handoff (e.g. /opsx-update after Route B classify)

EXPECTED_EXECUTION_ROUTE / ACTUAL_EXECUTION_ROUTE / ROUTE_RECONCILIATION:
  eventual production executor (/opsx-fix-bug | /opsx-apply) or terminal
```

`/opsx-update` is an immediate process command only. It MUST NEVER be written
as `EXPECTED_EXECUTION_ROUTE` or `ACTUAL_EXECUTION_ROUTE`.

### Route B chronology (must be reconstructible)

```text
classify:
  CHOSEN_ROUTE=ROUTE_B
  EXPECTED_NEXT_COMMAND=/opsx-update
  EXPECTED_EXECUTION_ROUTE=PENDING_UNTIL_TASK_DELTA
  CURRENT_ROUTE_STATE=AWAITING_SPEC_UPDATE

update + task_delta_decision:
  TASK_DELTA=CHANGED|UNCHANGED
  EXPECTED_EXECUTION_ROUTE=/opsx-apply|/opsx-fix-bug
  EXPECTED_NEXT_COMMAND=/opsx-apply|/opsx-fix-bug
  CURRENT_ROUTE_STATE=AWAITING_APPLY_RED|AWAITING_FIX_BUG_RED
```

## Route reconciliation

```text
ROUTE_RECONCILIATION:
  PENDING
  MATCH
  MISMATCH
  NOT_APPLICABLE
```

### Lifecycle

1. When a **classification route** is selected:

```text
CHOSEN_ROUTE: ROUTE_A|ROUTE_B|ROUTE_C|ROUTE_D
EXPECTED_NEXT_COMMAND: <immediate handoff>
ACTUAL_NEXT_COMMAND: PENDING
NEXT_COMMAND_RECONCILIATION: PENDING
EXPECTED_EXECUTION_ROUTE:
  Route A → /opsx-fix-bug
  Route B → PENDING_UNTIL_TASK_DELTA
  Route C → CLOSED_NO_IMPLEMENTATION
  Route D → ROUTE_TO_OTHER_PROCESS
ACTUAL_EXECUTION_ROUTE: PENDING | NOT_APPLICABLE
ROUTE_RECONCILIATION: PENDING | NOT_APPLICABLE
```

2. When `/opsx-update` **starts** as the Route B process step:

```text
ACTUAL_NEXT_COMMAND: /opsx-update
NEXT_COMMAND_RECONCILIATION: MATCH   # iff EXPECTED_NEXT_COMMAND == /opsx-update
```

Do **not** set `ACTUAL_EXECUTION_ROUTE=/opsx-update`.

3. When TASK_DELTA selects an implementation executor:

```text
EXPECTED_EXECUTION_ROUTE: </opsx-apply | /opsx-fix-bug>
ACTUAL_EXECUTION_ROUTE: PENDING
ROUTE_RECONCILIATION: PENDING
EXPECTED_NEXT_COMMAND: </opsx-apply | /opsx-fix-bug>
```

4. When an **implementation executor starts** (`/opsx-fix-bug` or
   `/opsx-apply` on a production/adjudication hop):

```text
ACTUAL_EXECUTION_ROUTE: </opsx-fix-bug | /opsx-apply>
ACTUAL_NEXT_COMMAND: </opsx-fix-bug | /opsx-apply>
```

then compute:

```text
MATCH    iff EXPECTED_EXECUTION_ROUTE == ACTUAL_EXECUTION_ROUTE
MISMATCH otherwise
```

5. Terminal non-implementation routes (C/D):

```text
ACTUAL_EXECUTION_ROUTE: NOT_APPLICABLE
ROUTE_RECONCILIATION: NOT_APPLICABLE
ACTUAL_NEXT_COMMAND: NOT_APPLICABLE
NEXT_COMMAND_RECONCILIATION: NOT_APPLICABLE
```

### MISMATCH hard gate

If `EXPECTED_EXECUTION_ROUTE != ACTUAL_EXECUTION_ROUTE` on an executor hop,
or `EXPECTED_NEXT_COMMAND != ACTUAL_NEXT_COMMAND` on a process-handoff hop:

```text
ROUTE_RECONCILIATION / NEXT_COMMAND_RECONCILIATION: MISMATCH
STATUS: BLOCKED_ROUTE_MISMATCH
EPISODE_CLOSE_ALLOWED: NO
PRODUCTION_GO_ALLOWED: NO
```

Mismatch MUST NOT be closed silently. Continuation requires an explicit
Owner route decision or corrected route evidence. Manager / Coordinator /
executor MUST NOT self-approve a mismatch.

## Actor identity

```text
ACTOR_ROLE:           required (Classifier, Claimer, SpecReviser, BugAnalyst,
                       RegressionAuthor, Executor, Owner, Coordinator, Hunter, …)
ACTOR_AGENT_ID:       required; if no separate agent id → CURRENT_CHAT_AGENT
ACTOR_CHAT_ID:        required stable episode-local durable chat label
                      (platform chat id if available; else supplied/generated
                      label — never free-text role alone)
```

## Owner waiting fields

When Owner gate opens:

```text
OWNER_GATE_STATUS: WAITING
OWNER_GATE_OPENED_AT: <ISO-8601>
```

After Owner production GO:

```text
OWNER_GATE_STATUS: APPROVED
OWNER_GO_ISSUED_AT: <ISO-8601>
OWNER_WAIT_DURATION_MS: <opened → issued>
```

On rejection:

```text
OWNER_GATE_STATUS: REJECTED
```

Production executors MUST NOT invent or backdate these timestamps.

## Out-of-scope target (Route D)

When `CLASSIFICATION=OUT_OF_SCOPE`:

```text
EXPECTED_EXECUTION_ROUTE: ROUTE_TO_OTHER_PROCESS
ROUTE_TARGET_PROCESS_ID: <required>
ROUTE_TARGET_REASON: <required>
ACTUAL_EXECUTION_ROUTE: NOT_APPLICABLE
ROUTE_RECONCILIATION: NOT_APPLICABLE
```

Missing target:

```text
STATUS: BLOCKED_MISSING_ROUTE_TARGET
```

## EVENT_TYPE vocabulary (producers)

```text
materialize
claim
classify-bug
classification_route_selection
update
task_delta_decision
test_red
owner_production_go
owner_production_rejection
fix-bug
apply
test_green
hunt
fanout
fan-in
lesson_analysis
supervisor_transition
```

Optional nested object on events (see `ROUTE_TRANSITION.md`):

```text
ROUTE_TRANSITION: { ... }
SUPERVISOR_EVENT fields when EVENT_TYPE=supervisor_transition
```

Do not create a second append-only history for supervisor; reuse this JSONL.
## TERMINAL_STATUS vocabulary

```text
PASS
FAIL
BLOCKED
BLOCKED_ROUTE_MISMATCH
BLOCKED_MISSING_ROUTE_TARGET
TIMEOUT
REJECTED
CLOSED_NO_IMPLEMENTATION
ROUTE_TO_OTHER_PROCESS
PENDING
NOT_APPLICABLE
null
```

## Write rules

1. Append only; never rewrite prior lines.
2. Allocate next `EVENT_SEQUENCE` by reading the last line of the JSONL (or 1 if empty).
3. Set `PREVIOUS_EVENT_ID` from the prior event’s `EVENT_ID`.
4. Do not log secrets or raw claim tokens (presence only).
5. After append, refresh LEDGER `## ROUTE_STATE` to match this event (snapshot only).
6. Ad-hoc Shell/Python append MUST follow
   `.cursor/commands/opsx-execution-preflight.md` →
   **Windows Shell JSON / JSONL write safety**
   (`encoding="utf-8"` + `ensure_ascii=True` for agent recipes; no unsafe
   console print of the line; ASCII `->` in machine string fields).
7. Prefer an authoritative `route_trace` runtime helper when available;
   do not invent a second write recipe that uses `ensure_ascii=False` on
   Windows agent Shell/stdin scripts.
```
