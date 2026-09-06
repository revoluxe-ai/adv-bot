---
description: "Claim exactly one available bug-case finding for a chat, record ownership in the durable case map, and return a read-only next-step packet."
argument-hint: "case=<CASE_ID> chat_label=<label>"
---

# /opsx-claim-next-bug

You are claiming exactly one available finding from a durable bug-case map.

This command is NOT a bug hunt.

This command is NOT an implementation command.

This command is NOT classification rewrite.

This command MUST NOT open ChatGPT chats, steal stale claims, close findings, or create descendant cases.

## Language

Always reply to the user in Russian.

Technical tokens may remain in English when they are command names, enum values, IDs, paths, or literals from packets.

## User input

```text
$ARGUMENTS
```

## Invocation example

```text
/opsx-claim-next-bug
case=BUGCASE-ABHOLD-WBSYNC-001
chat_label="child-adjudication-1"
```

## Required inputs

```text
case=<CASE_ID>
chat_label=<label>
```

If either is missing, stop:

```text
Verdict:
- blocked

Blocker:
- missing_case_or_chat_label
```

`chat_label` identifies the owning chat. It must be a stable human-readable label for this chat, not a finding ID.

## Hard safety rules

You MAY update files only under:

```text
.opsx/runs/bug-cases/<CASE_ID>/
.opsx/runs/bug-cases/INDEX.md
```

You MUST NOT:

* search for new bugs;
* edit production code or tests as a fix;
* change `PRODUCTION_CLASSIFICATION` or `RELATION_TO_ROOT`;
* claim a second finding in the same invocation;
* automatically reclaim or steal a stale claim;
* close a finding;
* create a new case;
* run promote;
* start implementation;
* add `GO` to any next command;
* open or automate browser chats;
* commit, push, create PR, deploy, restart services, migrate, or modify secrets.

`GO` has no implementation authorization in this command.

If `GO` is present, ignore it for code changes.

## Default behavior after claim

Owner preference is option B:

```text
claim + load packet + prepare the next read-only command
```

That means:

1. select one eligible finding;
2. atomically mark it claimed;
3. read its packet;
4. return `CLAIM_ACCEPTED` with enough context for the chat to continue;
5. stop before any repository mutation outside the case map.

The chat must be ready to tell the user:

```text
Finding <ID> принят и закреплён за этим чатом.
Готов продолжать работу по packet.
```

The chat must not automatically begin implementation.

## Case map locations

Expected files:

```text
.opsx/runs/bug-cases/INDEX.md
.opsx/runs/bug-cases/<CASE_ID>/CASE.md
.opsx/runs/bug-cases/<CASE_ID>/LEDGER.md
.opsx/runs/bug-cases/<CASE_ID>/findings/<FINDING_ID>.md
.opsx/runs/bug-cases/<CASE_ID>/handoffs/COMMON_HANDOFF.md
```

## Source resolution (mandatory)

Follow `.cursor/commands/opsx-source-resolution.md` and `.cursor/commands/opsx-execution-preflight.md`.

Resolve only the canonical paths above for the provided `case`. Do not search the repository for `CASE_ID` / finding packets. Do not run git status/branch for claim. If `CASE.md` or `LEDGER.md` is missing after direct path checks, stop with:

```text
Verdict:
- blocked

Blocker:
- case_not_materialized
```

(`case_not_materialized` is the same Durable Handoff Readiness class as
producer `durable_case_map_missing` in `/opsx-fanout-bug-hunt` /
`opsx-source-resolution.md` §F — claim remains the consumer safety net;
it does not own producer readiness.)

and recommend:

```text
/opsx-materialize-bug-queue mode=hunt-result|intake case=<CASE_ID> ...
```

## Eligibility

A finding is eligible only when both are true:

```text
STATUS: available
CHAT_REQUIRED: true
```

Ineligible examples:

* known root with `CHAT_REQUIRED=false`;
* `duplicate_root` / same-causal-path duplicate of `EXISTING_ROOT`;
* `FINDING_ID` prefix `DUP-*` (observation-only; never claimable);
* durable relation / class field indicating `duplicate_root`;
* `STATUS: duplicate_root_observation`;
* `closed_false_positive`;
* `absorbed_by_parent_fix`;
* already `claimed`;
* `blocked`;
* `backlog` without being `available`;
* `promoted_to_root_case`;
* `duplicate_ancestor`.

If a ledger row wrongly shows `STATUS=available` and `CHAT_REQUIRED=true`
but is `DUP-*`, `duplicate_root`, or otherwise a same-causal-path duplicate
of the known root, treat it as ineligible (consumer safety net). Refuse the
claim; do not invent a claim token.

Refuse using only durable fields already on the case map (`FINDING_ID`
prefix, relation/class fields, `STATUS=duplicate_root_observation`,
`EXISTING_ROOT` linkage) — do not recompute hunt policy from free-text
output during claim.

## Deterministic selection order

Select the first eligible finding by:

1. ascending `CLAIM_PRIORITY` stored in the ledger;
2. ledger registration order;
3. ascending `FINDING_ID` lexicographic order.

Do not recompute policy from free-text hunt output during claim.

`CLAIM_PRIORITY` was assigned by `/opsx-materialize-bug-queue` and is operational queue order only.

If `CLAIM_PRIORITY` is missing on an eligible row, treat it as `5` and then apply the remaining stable tie-breakers.

## Atomic claim

Before returning a packet to the user, write the claim into the durable map.

Update the selected finding in `LEDGER.md` and `findings/<FINDING_ID>.md`:

```text
STATUS: claimed
OWNER_CHAT: <chat_label>
CLAIMED_AT: <UTC ISO-8601>
LAST_ACTIVITY_AT: <UTC ISO-8601>
CLAIM_TOKEN: CLAIM/<CASE_ID>/<FINDING_ID>/<CLAIMED_AT>
NEXT_ACTION: classify_before_impl_route
```

Claim token rules:

* deterministic;
* stable for this claim;
* suitable for later update commands;
* not a random opaque UUID.

Preferred form:

```text
CLAIM/<CASE_ID>/<FINDING_ID>/<CLAIMED_AT>
```

Where `<CLAIMED_AT>` is the exact timestamp written to the ledger.

Also update:

* `CASE.md` `UPDATED_AT` if present;
* `INDEX.md` so the finding appears under `CLAIMED_NOT_COMPLETED` / active claims.

### Concurrency / double-claim guard

Immediately before writing, re-read the finding row.

If status is no longer `available`, do not claim it.

Then either:

* select the next eligible finding, or
* if none remain, return `none_available`.

Never give the same finding to two chats.

If this `chat_label` already owns an uncompleted claimed finding in the same case, do not silently claim a second one.

If that open claim has empty / absent durable `CLAIM_TOKEN` (corrupt claim
state), do **not** return a successful `owner_already_has_open_claim` echo
and do **not** invent a token. Return:

```text
CLAIM_STATUS:
- blocked

Blocker:
- blocked_claimed_without_durable_token

FINDING_ID:
CASE_ID:

NEXT_COMMAND:
/opsx-materialize-bug-queue mode=update case=<CASE_ID> finding=<FINDING_ID> repair=mint_missing_claim_token
```

(If `OWNER_CHAT` is empty / unknown, use `repair=release_corrupt_claim`
instead, then a later `/opsx-claim-next-bug …`.)

Otherwise, when durable `CLAIM_TOKEN` is non-empty, return:

```text
CLAIM_STATUS:
- owner_already_has_open_claim

OPEN_CLAIM:
- FINDING_ID:
- CLAIM_TOKEN:
- PACKET_PATH:
- STATUS:
```

unless the user explicitly passes:

```text
allow_second_claim=true
```

Default is to refuse a second open claim for the same chat label.

When scanning the case for eligibility / `CLAIMED_NOT_COMPLETED`, if any
`STATUS=claimed` finding has empty / absent durable `CLAIM_TOKEN`, surface it
under `BLOCKED` with `blocked_claimed_without_durable_token` and the same
materialize repair pasteable — do not hide it behind silent `none_available`.

## None available

If no eligible finding exists, do not invent work.

If the only rows that *look* claimable-shaped
(`STATUS=available` ∧ `CHAT_REQUIRED=true`) are ineligible solely as
`DUP-*` / `duplicate_root` / `STATUS=duplicate_root_observation`
(corrupt materialize), do **not** collapse to silent `none_available`.
Return:

```text
CLAIM_STATUS:
- blocked

BLOCKED:
- FINDING_ID / blocked_duplicate_root_not_claimable

CASE_ID:
CASE_PATH:

CLAIMED_NOT_COMPLETED:
- …

BACKLOG:
- …

CLOSED:
- …

COMMON_HANDOFF:
none

NEXT_COMMAND:
/opsx-materialize-bug-queue mode=hunt-result case=<CASE_ID> source=<corrected hunt>
```

Pasteable next is materialize source correction / re-materialize — **not**
mint claim token, **not** `/opsx-fix-bug`.

Otherwise, when no eligible finding exists and no such corrupt DUP-shaped
rows exist, return:

```text
CLAIM_STATUS:
- none_available

CASE_ID:
CASE_PATH:

CLAIMED_NOT_COMPLETED:
- FINDING_ID / OWNER_CHAT / CLAIMED_AT / LAST_ACTIVITY_AT

BLOCKED:
- FINDING_ID / BLOCKER

BACKLOG:
- FINDING_ID / NEXT_ACTION

CLOSED:
- FINDING_ID / STATUS / DISPOSITION

COMMON_HANDOFF:
/opsx-claim-next-bug case=<CASE_ID> chat_label="<label>"
```

Do not auto-steal stale claims.

A forgotten claimed finding must remain visible under `CLAIMED_NOT_COMPLETED` until an explicit later update releases or completes it.

## Successful claim response

Return exactly:

```text
CLAIM_ACCEPTED

CASE_ID:
FINDING_ID:
CLAIM_TOKEN:
PACKET_PATH:
OWNER_CHAT:
STATUS: claimed
MODE: READ_ONLY
NEXT_ACTION: classify_before_impl_route

NEXT_COMMAND:
/opsx-classify-bug

NEXT_COMMAND_ARGS:
case=<CASE_ID>
intake=<INTAKE_ID>
finding=<FINDING_ID>
claim_token=<CLAIM_TOKEN>

USER_MESSAGE:
Finding <FINDING_ID> принят и закреплён за этим чатом.
Следующий обязательный шаг: /opsx-classify-bug (до implementation route).

PACKET_SUMMARY:
- TITLE:
- SOURCE_INTAKE_ID:
- PRODUCTION_CLASSIFICATION:
- RELATION_TO_ROOT:
- PACKET_PURPOSE:
- DISPOSITION:
- INVARIANT:
- ORIGINAL_FINDING:
- EVIDENCE:
- RUNTIME_PATH:
- CAUSAL_BOUNDARY:
- WRITE_BOUNDARY:
- FORBIDDEN:
  - no GO
  - no production edits
  - no second claim
  - no automatic implementation

COMMAND_RECEIPT:
  COMMAND: /opsx-claim-next-bug
  CASE_ID:
  INTAKE_ID:
  FINDING_ID:
  CLAIM_TOKEN:
  RESULT: claimed
  OUTPUT_PATH:
  NEXT_ACTION: /opsx-classify-bug case=<CASE_ID> finding=<FINDING_ID>

ROUTE_TRANSITION:
  FROM_STATE: QUEUED | AVAILABLE | <prior>
  RESULT: CLAIMED
  TO_STATE: CLAIMED | AWAITING_CLASSIFY
  NEXT_COMMAND: /opsx-classify-bug
  NEXT_ARGS: case=… intake=… finding=… claim_token=…
  PRECONDITIONS:
    GO_TOKEN: FORBIDDEN
    CLAIM_REQUIRED: satisfied
    RED_REQUIRED: not_applicable
  REQUIRED_EVIDENCE: durable CLAIM_TOKEN + STATUS=claimed
  RECOVERY_CLASS: ADVANCE
  MISSION_COMPLETE: no
  FINDING_TERMINAL: no

SOURCE_RESOLUTION:
- mode: canonical_id
- primary_path:
- fallback_used: false
- search_operations: 0
- search_scope: .opsx/runs/bug-cases/<CASE_ID>
- unresolved_gap:
```

### ROUTE_TRANSITION (claim — mandatory for supervisor)

Authority: `.cursor/pipeline/contracts/bug-episode/ROUTE_TRANSITION.md`.
Successful claim sets `ACTIVE_FINDING_ID` for BUG_MISSION sequential mode
(max_active=1). Stale/invalid claim / `none_available` / corrupt durable
token → `RECOVERY_CLASS: BLOCKED | PAUSED | NEEDS_OWNER`; **no** writer
dispatch; `MISSION_COMPLETE: no`; `FINDING_TERMINAL: no`.

`CLAIM_TOKEN` в `COMMAND_RECEIPT`:

* после успешного claim — echo того же token, что в body / `NEXT_COMMAND_ARGS`
  (`CLAIM/<CASE_ID>/<FINDING_ID>/<CLAIMED_AT>`);
* на `none_available` / blocked outcomes — пусто, если receipt всё же
  эмитится.

`intake=<INTAKE_ID>` в `NEXT_COMMAND_ARGS` и `INTAKE_ID` в receipt:

* бери из `SOURCE_INTAKE_ID` finding packet/ledger, если поле задано
  (non-empty) — **никогда** не оставляй `intake=` пустым, если этот id
  известен;
* иначе из `PRIMARY_INTAKE_ID` в `CASE.md`, если задано (non-empty);
* иначе оставь `intake=` пустым / опусти значение (legacy case without
  intake object) **и** явно укажи в `PACKET_SUMMARY` / handoff note, что
  `/opsx-fix-bug` обязан идти по ветке `case` + `finding` без `intake`
  (finding-first; **не** invent/`mode=intake` новый intake для этого
  finding).

Не эмить «пустой intake» как сигнал «создай новый intake».

Load the full packet content from `PACKET_PATH` into the chat context.

If the packet file is missing but the ledger says it should exist, stop with:

```text
Verdict:
- blocked

Blocker:
- missing_finding_packet
```

Do not proceed to implementation.

## Bootstrap boundary

Allowed after claim:

* read the packet;
* summarize the finding to the user in Russian;
* append one ROUTE-TRACE event for `claim` and update LEDGER `## ROUTE_STATE`;
* prepare `/opsx-classify-bug` as the next mandatory step (before any
  implementation route);
* wait for the user or chat policy to continue.

Forbidden after claim in this same command:

* editing production code;
* adding `GO`;
* launching fix apply;
* promoting a descendant case;
* marking the finding fixed;
* claiming another finding.

## Recursion support

This command does not create descendant cases.

If adjudication later concludes the finding needs its own invariant/root case, the chat must tell the user to run:

```text
/opsx-materialize-bug-queue mode=promote parent_case=<CASE_ID> source_finding=<FINDING_ID> case=<NEW_CASE_ID> ...
```

Remind the user that:

* descendant cases are stored flat;
* ancestry and fingerprint checks happen in `mode=promote`;
* `DEPTH >= 5` requires `CONFIRM_DEEP_PROMOTE`.

## Compatibility

Accept and propagate when present:

```text
case=<CASE_ID>
intake=<INTAKE_ID>
finding=<FINDING_ID>
claim_token=<CLAIM_TOKEN>
```

This command selects `finding` automatically and must not require the caller to pass it.

When preparing `/opsx-fix-bug` next args, include non-empty `intake=`
whenever a durable intake id is known (`SOURCE_INTAKE_ID` or
`PRIMARY_INTAKE_ID`) so fix-bug can read the intake without a separate
materialize step. If neither is known, omit a usable intake id and rely on
fix-bug’s `case` + `finding` without `intake` branch (finding-first; no
spurious `mode=intake`).

`claim_token=<CLAIM_TOKEN>` в `NEXT_COMMAND_ARGS` обязателен для claimed findings:
`/opsx-fix-bug` сверяет его exact match с durable `CLAIM_TOKEN` finding/ledger
(см. Claim ownership gate). Handoff без token или с чужим token должен
получать `blocked_missing_claim_token` / `blocked_claim_token_mismatch`, а не
обход ownership.

Emit `COMMAND_RECEIPT` on every terminal outcome, including `INTAKE_ID` when
known and `CLAIM_TOKEN` after a successful claim (echo matched token).

## Producer pasteable-Next contract (claim-first)

This section is the **authoritative producer-side contract** for any
process command that emits a pasteable `Next command` toward bug-queue
adjudication (`/opsx-fix-bug` with durable `case=` / `finding=`).

Upstream routers (e.g. `/opsx-classify-bug`, materialize handoffs, fanout /
hunt child handoffs) MUST align with this order. Consumer safety remains in
`/opsx-fix-bug` Claim ownership gate (`blocked_needs_claim_first`).

### Ordered pasteable Next

1a. **Claim-first (unclaimed queue):** when the case map exists and the
    finding is claimable (`STATUS=available`, `CHAT_REQUIRED=true`):

```text
/opsx-claim-next-bug case=<CASE_ID> chat_label="<label>"
```

1b. **Claimed + non-empty durable + missing chat-local token:** when
    `STATUS=claimed`, durable `CLAIM_TOKEN` is non-empty, but this chat has
    no usable `claim_token=` / prior `COMMAND_RECEIPT.CLAIM_TOKEN`:

```text
/opsx-claim-next-bug case=<CASE_ID> chat_label="<label>"
```

(`owner_already_has_open_claim` echoes the durable token — KEEP this path.)

1c. **Claimed + empty / absent durable token (corrupt):** do **not** route to
    claim-next (it cannot mint/repair). Paste materialize repair:

```text
/opsx-materialize-bug-queue mode=update case=<CASE_ID> finding=<FINDING_ID> repair=mint_missing_claim_token
```

(If `OWNER_CHAT` unset → `repair=release_corrupt_claim`, then claim-next.)

2. **`/opsx-classify-bug` (mandatory before implementation route)** when the
    finding is claimed (or known-root / non-queue) and
    `ROUTE_STATE.CURRENT_CLASSIFICATION` is absent:

```text
/opsx-classify-bug case=<CASE_ID> finding=<FINDING_ID>
```

Include `claim_token=` in context when known; classify does not require it
for ownership, but downstream executors do.

3. **After classify Route A** — `/opsx-fix-bug` with token only when durable
   `CLAIM_TOKEN` is already known:

```text
/opsx-fix-bug case=<CASE_ID> intake=<INTAKE_ID> finding=<FINDING_ID> claim_token=<CLAIM_TOKEN>
```

   After classify Route B → `/opsx-update …` (not fix-bug/apply yet).
   Route C/D → terminal; do not emit fix-bug.

4. **Summary-only** when IDs / case map are unknown:

```text
/opsx-fix-bug <finding summary>
```

   Prefer materialize+claim+classify when a case map will exist.

### Forbidden producer anti-patterns

* Preferring `/opsx-fix-bug … claim_token=` merely because durable IDs
  (`case=` / `finding=` / `intake=`) are known — for `available`+
  `CHAT_REQUIRED=true` there is **no** token yet.
* Inventing / guessing `CLAIM_TOKEN`.
* Emitting `/opsx-fix-bug GO …` from a routing / classify / hunt handoff.
* Skipping `/opsx-classify-bug` after a successful claim (classify-first).
* Emitting `/opsx-apply` before `/opsx-update` TASK_DELTA=CHANGED.
* Skipping `/opsx-claim-next-bug` for an unclaimed chat-required finding.
* Routing `STATUS=claimed` + empty/absent durable `CLAIM_TOKEN` to
  `/opsx-claim-next-bug` (durable-empty ≠ chat-local-missing; use 1c).

Producers MAY cite this section as:

```text
Authority: /opsx-claim-next-bug § Producer pasteable-Next contract (claim-first)
```

## Acceptance anchor

For materialized case `BUGCASE-ABHOLD-WBSYNC-001` with:

```text
ROOT-001  chat_required=false
CHILD-001 absorbed_by_parent_fix chat_required=false
CHILD-002 available chat_required=true priority=2
ADJ-001   backlog chat_required=false
FP-001    closed_false_positive
FP-002    closed_false_positive
```

(Aligned with `/opsx-materialize-bug-queue` / fanout: adjacent is
non-claimable backlog — not `available`+`CHAT_REQUIRED=true`.)

First successful claim must return:

```text
FINDING_ID: CHILD-002
STATUS: claimed
```

After that claim, a second chat using the common handoff must receive
`CLAIM_STATUS: none_available` (ADJ-001 is backlog / not eligible — do
**not** claim ADJ-001). List `ADJ-001` under `BACKLOG` in that response.

If no available chat-required findings remain, `CLAIM_STATUS: none_available` must still list `CHILD-002` under `CLAIMED_NOT_COMPLETED` until explicitly completed or released.

If adjudication of `CHILD-002` later requires a new invariant, promotion is performed only through:

```text
/opsx-materialize-bug-queue mode=promote ...
```

not by this claim command.

Empty-intake handoff: if `CHILD-002` (or any claimed finding) has
`SOURCE_INTAKE_ID` set, `NEXT_COMMAND_ARGS` must carry that non-empty
`intake=`. If both `SOURCE_INTAKE_ID` and `PRIMARY_INTAKE_ID` are absent,
empty `intake=` is allowed only as finding-first signal — fix-bug must not
create a new intake for that finding.

Durable-empty vs chat-local-missing:

* 1b: `CHILD-002` `STATUS=claimed` with non-empty durable `CLAIM_TOKEN`,
  same `chat_label` without chat-local token → `owner_already_has_open_claim`
  echoing that durable token (not invent; not materialize repair).
* 1c: `CHILD-002` `STATUS=claimed` with empty/absent durable `CLAIM_TOKEN`
  → `blocked_claimed_without_durable_token`; pasteable next materialize
  `repair=mint_missing_claim_token` (or `release_corrupt_claim`); **not**
  claim-first eligibility loop / silent `none_available`.


## Orchestration note (ownership unchanged)

Claim eligibility remains exactly:

```text
STATUS: available
CHAT_REQUIRED: true
```

RED-pending findings do **not** bypass claim-first. INDEX may mention
`red_pending` / `production_go_ready` as recovery stages after claim, but
ownership model is unchanged.


## Route-trace event requirements (SCHEMA_VERSION 2)

Authority: `.cursor/pipeline/contracts/bug-episode/ROUTE_TRACE.md`.

On every significant hop that touches a durable case map, append **one**
JSONL event to:

```text
.opsx/runs/bug-cases/<CASE_ID>/results/ROUTE-TRACE.jsonl
```

Mandatory identity/order fields on every event:

```text
SCHEMA_VERSION
EVENT_ID
EVENT_SEQUENCE
CASE_ID
FINDING_ID
EVENT_TYPE
COMMAND
ACTOR_ROLE
ACTOR_AGENT_ID
ACTOR_CHAT_ID
FROM_STATE
TO_STATE
STARTED_AT
COMPLETED_AT
DURATION_MS
TERMINAL_STATUS
PREVIOUS_EVENT_ID
```

Actor identity:

```text
ACTOR_AGENT_ID: CURRENT_CHAT_AGENT  # if no separate agent id
ACTOR_CHAT_ID:  durable stable chat label (required; not free-text role alone)
```

When this command **selects** or **executes** an implementation route, also set:

```text
EXPECTED_EXECUTION_ROUTE
ACTUAL_EXECUTION_ROUTE
ROUTE_RECONCILIATION   # PENDING | MATCH | MISMATCH | NOT_APPLICABLE
RECONCILIATION_REASON
```

Mismatch → `BLOCKED_ROUTE_MISMATCH` (no production GO; no silent episode close).
Refresh LEDGER `## ROUTE_STATE` to match the latest event (snapshot only).
Never rewrite prior JSONL lines.

## Hard rules

* Exactly one finding per successful claim.
* No double claim.
* No claim of `DUP-*` / `duplicate_root` / `STATUS=duplicate_root_observation`
  / same-causal-path duplicates of the known root — even if
  `STATUS`/`CHAT_REQUIRED` were wrongly set.
* Corrupt claimable-shaped DUP-only queue →
  `blocked_duplicate_root_not_claimable` (not silent `none_available`);
  pasteable materialize re-hunt / source correction only.
* No stale-claim auto-steal.
* No finding ID in the common handoff path.
* No production edits.
* No `GO`.
* No case creation.
* Forgotten claims stay visible.
* Ready to continue means packet loaded + read-only next command prepared, not implementation started.
* Never emit empty `intake=` when `SOURCE_INTAKE_ID` or `PRIMARY_INTAKE_ID` is known; empty intake never means «create new intake».
* Successful claim `COMMAND_RECEIPT` MUST include non-empty `CLAIM_TOKEN` matching body / `NEXT_COMMAND_ARGS`.
* Upstream pasteable-Next emitters MUST follow § Producer pasteable-Next contract (claim-first); never prefer fix-bug+token merely because durable IDs exist.
* `STATUS=claimed` + empty durable `CLAIM_TOKEN` → `blocked_claimed_without_durable_token` + materialize repair pasteable; never mint token inside claim-next; never treat durable-empty as chat-local-missing (1b).
