# Bug-episode close + handback policy (human-native)

```text
SCHEMA: bug-episode/CLOSE_POLICY
AUTHORITY: ORCHESTRATION_MVP §0.7 / §4.3 + this file
IMPLEMENTATION_STATUS: LIVE_ACTIVATED
```

## Three closes (do not mix)

| Layer | Meaning | Who closes |
|---|---|---|
| **FINDING** | This branch/card is terminal (`EPISODE_TERMINAL=FIXED` → durable `STATUS=closed_fixed`) | Default: **bug-team CLOSURE** after family path; solo: materialize `close=fixed` after GREEN |
| **CASE** | All started findings terminal (or sole ROOT `closed_fixed`) | Same writers; INDEX/CASE terminal update |
| **CLASS** | Error-class / lesson | `/opsx-learn-from-bug` + FANIN / LESSON_GATE only — **never** from apply/update |

Closing finding ≠ closing class ≠ OpenSpec archive.

Envelope terminal kinds (`CLOSED_GREEN`, `CLOSED_FALSE_POSITIVE`,
`ROUTED_OUT_OF_SCOPE`, `CLOSED_WITH_ACCEPTED_DISPOSITION`) map to durable
statuses via
`.cursor/pipeline/contracts/bug-episode/ROUTE_TRANSITION.md`
§ FINDING_TERMINAL_KIND ↔ durable STATUS map. Do not invent a second map
here.

## Durable intent fields (cross-chat)

Write on LEDGER `## ROUTE_STATE` and echo on TASK-DELTA / finding when known:

```text
CLOSE_FINDING_INTENT: auto_after_green | ask_after_green | never
POST_GREEN_OWNER: bug-team | solo
HANDBACK_COMMAND: /opsx-bug-team case=<CASE_ID> mode=<resume-family-fanout|continue>
CLOSE_INTENT_SET_BY: /opsx-update | /opsx-materialize-bug-queue | explicit Owner
```

Defaults when case= present and fields empty:

```text
CLOSE_FINDING_INTENT: ask_after_green
POST_GREEN_OWNER: bug-team
```

`/opsx-update` may set intent via `close_finding=`. Chat paraphrase is not authority.
`apply` / `fix-bug` / `test` **read** these fields; they do not invent them from chat memory.

## When NOT to close finding after GREEN (leave open)

Record `LEAVE_OPEN_REASON` when leaving open:

```text
followup_hunt_or_invariant
partial_residual
sibling_or_family_orchestrator
owner_prod_smoke
wrong_or_ambiguous_finding
deferred_or_blocked_terminal
batch_human_index_review
```

## Execution rules

1. **Never** write `closed_fixed` from `/opsx-apply`, `/opsx-update`, or `/opsx-verify`.
2. GREEN writer remains `/opsx-test … verify` only.
3. After GREEN:
   - if `POST_GREEN_OWNER=bug-team` (default) → primary pasteable `HANDBACK_COMMAND` (no silent return);
   - if `POST_GREEN_OWNER=solo` + `auto_after_green` → materialize `close=fixed`;
   - if `POST_GREEN_OWNER=solo` + `ask_after_green` → pasteable close vs leave-open;
   - if `never` → leave open; still show handback as ALSO_OK when team case.
4. Episode close still requires ORCHESTRATION §0.7 route reconciliation ∈ {MATCH, NOT_APPLICABLE}.
5. FIXED requires RED/GREEN linkage per TERMINAL_STATUS_MAP.

## Handback UX (HANDBACK_EXPLICIT / NO_SILENT_RETURN)

Any recommend to return to bug-team MUST emit one pasteable line with `case=`:

```text
/opsx-bug-team case=<CASE_ID> mode=resume-family-fanout
```

or `mode=continue` when durable checkpoint is pre-family / pre-GREEN.

Never describe “returning you to bug-team” without that pasteable command.

## Solo walk (advisory)

Owner may walk Route B/A themselves (`update` → `apply` | `fix-bug GO` → look at code).  
This is **not** a process violation. Soft recommends:

- **PRIMARY** while mid-step: finish current command;
- **SECONDARY**: handback pasteable when ready;
- **ALSO_OK**: continue solo through GREEN.

## Owner-block hints (bug-team stopped)

When team needs Owner A/B/C (or policy):

```text
OWNER_DECISION_REQUIRED: A | B | C | …
OPTIONAL_IF_UNSURE: /opsx-explore case=CASE_ID finding=FINDING_ID
THEN_RETURN (pasteable, not silent): /opsx-bug-team case=CASE_ID mode=…
```

Substitute durable `BUGCASE-…` / finding ids — never emit angle-bracket
`case=<CASE_ID>` templates (CMD-IX-001). Omit until ids known. Do not paste
into free-form first-intake `RAW_REPORT` (CMD-IX-002).

Explore does not replace A/B/C; it clarifies before the answer.
