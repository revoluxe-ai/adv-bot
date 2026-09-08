---
description: "Materialize or update a durable bug-case map from intake, hunt-result, promote, or field update without re-analysing the repository or fixing bugs."
argument-hint: "mode=<intake|hunt-result|promote|update|fanin_assemble> [case=<CASE_ID>] [intake=<INTAKE_ID>] [source=<artifact>] [finding=<FINDING_ID>] [repair=mint_missing_claim_token|release_corrupt_claim] [fields...]"
---

# /opsx-materialize-bug-queue

You are materializing a durable file-backed bug-case map.

This command is NOT a bug hunt.

This command is NOT a classification rewrite.

This command is NOT an implementation command.

This command is NOT browser automation and MUST NOT open ChatGPT chats.

Its only purpose is to create or update process artifacts under:

```text
.opsx/runs/bug-cases/
```

so raw intakes and findings survive across chats and can recursively spawn descendant cases.

Authoritative storage is only:

```text
.opsx/runs/bug-cases/**
```

## Source resolution (mandatory)

Follow `.cursor/commands/opsx-source-resolution.md` and `.cursor/commands/opsx-execution-preflight.md`.

When `case` / `intake` / `finding` are provided:

* resolve only under `.opsx/runs/bug-cases/<CASE_ID>/...` canonical paths;
* do not search the wider repository for these artifacts;
* do not run git status/branch as a gate for materialize;
* if the canonical path is missing, return `blocked` / `unknown_case` / `unknown_finding` / `unknown_intake` rather than repo-wide rediscovery.

`mode=intake` records a raw signal before adjudication. It does not assert that a production bug is confirmed.

## Language

Always reply to the user in Russian.

Technical tokens may remain in English when they are command names, enum values, IDs, paths, or literals from source packets.

## User input

```text
$ARGUMENTS
```



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

## Modes

Exactly one mode is required:

```text
mode=intake
mode=hunt-result
mode=promote
mode=update
mode=fanin_assemble
```

If `mode` is missing or unknown, stop:

```text
Verdict:
- blocked

Blocker:
- missing_or_invalid_mode
```

## Hard safety rules

You MAY create or update files only under:

```text
.opsx/runs/bug-cases/
```

You MUST NOT:

* edit production code;
* edit tests as a fix;
* edit OpenSpec product specs as a side effect;
* re-analyse the repository to invent new findings;
* change `PRODUCTION_CLASSIFICATION` or `RELATION_TO_ROOT` received from an authoritative source;
* run `/opsx-fix-bug` with `GO`;
* add `GO` to any handoff;
* claim a finding for a chat;
* open or automate chats;
* commit, push, create PR, deploy, restart services, migrate, or modify secrets;
* delete false-positive records;
* nest descendant case directories inside parent case directories.

`GO` has no authorization effect for production edits in this command.

If `GO` is present, ignore it for code changes and still write only process artifacts under `.opsx/runs/bug-cases/`.

## Durable layout

Use exactly this layout. Do not add extra files without a concrete function required by this contract.

```text
.opsx/runs/bug-cases/
  INDEX.md

  <CASE_ID>/
    CASE.md
    LEDGER.md
    intakes/
      <INTAKE_ID>.md
    findings/
      <FINDING_ID>.md
    handoffs/
      COMMON_HANDOFF.md
    results/
```

Rules:

* Cases are stored flat under `.opsx/runs/bug-cases/`.
* Parent/child relationships live in metadata, not in nested folders.
* `results/` may be empty until a later command writes a result.
* Do not create placeholder junk files.
* `intakes/<INTAKE_ID>.md` holds the durable raw signal before adjudication.
* `LEDGER.md` is the operational source of truth for finding status and claim eligibility.
* `findings/<FINDING_ID>.md` holds either a working packet or a closed false-positive record.
* `handoffs/COMMON_HANDOFF.md` is the short shared handoff for new chats.
* `INDEX.md` is the cross-case recovery board and status board for forgotten, claimed, blocked, backlog, open findings, and open hunt candidates (`OPEN_CANDIDATES`, including SAME_INVARIANT residuals that HARD_BLOCK READY). Operator front-door to **read** that debt without rewriting INDEX: `/opsx-bug-debt-board`.

## INTAKE object

Intake is a raw signal. It is not a confirmed finding.

Every `intakes/<INTAKE_ID>.md` MUST carry:

```text
CASE_ID
INTAKE_ID
CREATED_AT
SOURCE_TYPE
SOURCE_REFERENCE
RAW_REPORT
OBSERVED_SYMPTOM
KNOWN_CONTEXT
STATUS
LAST_ACTIVITY_AT
NEXT_ACTION
```

Initial status:

```text
intake_recorded
```

When closed as a duplicate of an earlier intake/finding, also record:

```text
DISPOSITION: duplicate_intake
CANONICAL_INTAKE_ID
RELATED_FINDING_ID
RESULT_PATH
```

and set:

```text
STATUS: closed_duplicate
```

Intake MUST NOT assert:

* that a production bug is confirmed;
* root cause;
* invariant;
* how many separate findings exist;
* that a fix is required;
* `PRODUCTION_CLASSIFICATION` or `RELATION_TO_ROOT`.

`RAW_REPORT` MUST preserve the user/Bugbot/CI text verbatim (or the closest durable copy available in the current invocation).

Closing an intake as `closed_duplicate` is a linkage decision about the signal, not a claim that the canonical finding is newly proven.

## Evidence / status labels for design statements

When this command itself records a design or policy choice inside artifacts, use only:

```text
confirmed
draft
needs extraction
question for user
not migrate
```

Do not promote raw hunt prose into permanent policy.

Owner directions encoded in this command contract are `confirmed` for materialization behavior.

## Finding operational states

These are ledger states only. They are not an OpenSpec lifecycle model.
**Claim `STATUS` vocabulary is unchanged** by orchestration companions.

```text
available
claimed
adjudicating
ready_for_fix
implementing
verification
closed_fixed
closed_false_positive
backlog
blocked
absorbed_by_parent_fix
promoted_to_root_case
duplicate_ancestor
duplicate_root_observation
```

## Bug-episode shared schemas (reference)

```text
.cursor/pipeline/contracts/bug-episode/
```

Policy SoT: `.cursor/pipeline/ORCHESTRATION_MVP.md`.

```text
IMPLEMENTATION_STATUS: LIVE_ACTIVATED
VALIDATION_STATUS: INDEPENDENT_TEST_PASS
RUNTIME_ENFORCEMENT: ACTIVE
LIVE_COMMAND_BEHAVIOR_CHANGED: YES
GO_ACTIVATE: ISSUED
```

## Parallel EPISODE_TERMINAL (claim STATUS unchanged)

Episode terminals live in a **parallel** field. Do **not** rename or replace
claim `STATUS` values to encode them.

```text
EPISODE_TERMINAL:
  FIXED | REJECTED | DUPLICATE | DEFERRED | BLOCKED | TIMEOUT
  | TEST_NOT_REPRODUCING | RED_NOT_APPLICABLE
```

Map: `.cursor/pipeline/contracts/bug-episode/TERMINAL_STATUS_MAP.md`.

## BRANCH_REGISTRY (runtime instance)

Schema definition:
`.cursor/pipeline/contracts/bug-episode/BRANCH_REGISTRY.md`

**Only** runtime instance:

```text
.opsx/runs/bug-cases/<ROOT_CASE_ID>/LEDGER.md
  ## BRANCH_REGISTRY
```

Do **not** create a sibling `BRANCH_REGISTRY.md` file in the case map.

LEDGER summary / BRANCH_REGISTRY header should carry hunt counters when known:

```text
HUNT_PASSES_EXECUTED
MAX_DEPTH_SEEN
ACTIVE_BRANCH_COUNT
MAX_HUNT_PASSES: 3
MAX_DEPTH_FROM_ROOT: 3
MAX_ACTIVE_BRANCHES: 3
```

## Required finding fields

Every finding row in `LEDGER.md` and every `findings/<FINDING_ID>.md` header MUST carry:

```text
FINDING_ID
CASE_ID
SOURCE_INTAKE_ID
PARENT_FINDING_ID
TITLE
PRODUCTION_CLASSIFICATION
RELATION_TO_ROOT
STATUS
CHAT_REQUIRED
PACKET_PATH
OWNER_CHAT
CLAIM_TOKEN
CREATED_AT
CLAIMED_AT
LAST_ACTIVITY_AT
COMPLETED_AT
NEXT_ACTION
BLOCKER
RESULT_PATH
DISPOSITION
CLAIM_PRIORITY
EPISODE_TERMINAL
RED_EVIDENCE_PATH
GREEN_EVIDENCE_PATH
OWNER_GO_RECEIPT_PATH
FIX_EVIDENCE_PATH
TEST_ID
TEST_CONTENT_SHA256
FANIN_PATH
```

Evidence path fields and `EPISODE_TERMINAL` may be empty until RED/GREEN/GO/FANIN
are recorded. Claim `STATUS` / `CHAT_REQUIRED` / `CLAIM_TOKEN` rules are unchanged.

Allowed empty values:

* `OWNER_CHAT`, `CLAIM_TOKEN`, `CLAIMED_AT`, `COMPLETED_AT`, `BLOCKER`, `RESULT_PATH` may be empty when unset;
* `PARENT_FINDING_ID` may be empty for the case root finding;
* `SOURCE_INTAKE_ID` may be empty only for legacy findings created before intake objects existed; new findings MUST set it when an intake exists;
* `PACKET_PATH` is empty only for proven false positives that intentionally have no working chat packet.

## Required case fields

`CASE.md` MUST carry at least:

```text
CASE_ID
PRIMARY_INTAKE_ID
ROOT_FINDING_ID
SOURCE_TYPE
SOURCE_REFERENCE
PARENT_CASE_ID
SOURCE_FINDING_ID
ANCESTOR_CHAIN
DEPTH
STATUS
CURRENT_STAGE
NEXT_ACTION
PROPOSED_INVARIANT
ROOT_FINGERPRINT
CREATED_AT
UPDATED_AT
LAST_COMMAND
```

For a raw intake case before any finding:

* `PRIMARY_INTAKE_ID` is set;
* `ROOT_FINDING_ID` may be empty;
* `PARENT_CASE_ID` may be empty;
* `SOURCE_FINDING_ID` may be empty;
* `ANCESTOR_CHAIN` is `[CASE_ID]` or equivalent explicit single-element chain;
* `DEPTH` is `0`;
* `STATUS` / `CURRENT_STAGE` start as `intake_recorded`;
* `PROPOSED_INVARIANT` and `ROOT_FINGERPRINT` may be empty until adjudication/hunt supplies them.

## Fingerprint

When a fingerprint is required, compute a logical fingerprint from at least:

```text
forbidden_effect
causal_boundary
write_boundary
production_state
invariant
```

Normalize whitespace. Do not include chat labels or timestamps in the fingerprint.

Store it as `ROOT_FINGERPRINT` on the case and, when useful for dedup, on false-positive records.

## CHAT_REQUIRED decision matrix

`confirmed` for this command.

Align with `/opsx-fanout-bug-hunt` `CREATE_CHILD_CHAT` eligibility and forbids.
Durable ledger owns storage/recursion, but **must not** mark a finding
claimable (`CHAT_REQUIRED=true` + `STATUS=available`) when fanout forbids
a child chat for that class.

| Condition | Packet | CHAT_REQUIRED | Initial STATUS |
|---|---|---|---|
| Proven false positive | no working packet; closed record only | `false` | `closed_false_positive` |
| Known root / `EXISTING_ROOT` already owned by the case | packet preserved/updated | `false` | keep existing operational status or `available` if new intake root awaiting work in its own case flow |
| `duplicate_root` / same-causal-path duplicate of known root / `DUP-*` observation (fanout `duplicate_root_emitted_as_new_finding` class) | optional closed/observation record only (fold into root evidence); never a working child packet | `false` | `duplicate_root_observation` (**never** `available`) |
| Authoritative disposition `absorbed_by_parent_fix` | packet preserved | `false` | `absorbed_by_parent_fix` |
| Child-chat eligible: `CHILD_CHAT_RECOMMENDED=true` (or equivalent hunt fields) **and** `RELATION_TO_ROOT=same_invariant_different_path` **and** production classification ∈ {`confirmed production bug`, `reachable but low-risk`, `unclear reachability`} | packet created | `true` | `available` |
| Fanout backlog-class forbids: `adjacent_out_of_scope` / adjacent; `dead legacy`; `tests-only` (fanout `BACKLOG_ONLY` / `CLEANUP_BACKLOG` / `TEST_COVERAGE_BACKLOG`) | packet/record created | `false` | `backlog` |
| `different_invariant_candidate` / different-invariant (fanout `CREATE_SEPARATE_ROOT_CANDIDATE` — not a child claim chat on this case) | packet/record created | `false` | `backlog` (or case-local separate-root tracking; never `available`+`CHAT_REQUIRED=true` on this case) |
| Non-FP finding with `CHILD_CHAT_RECOMMENDED=false` (or missing recommendation) that is not otherwise absorbed/FP/root | packet/record created | `false` | `backlog` |

Notes:

* Packet purpose for chat-required findings must state why the chat exists: adjudication, disposition decision, or promotion decision. Backlog packets record backlog/cleanup/test-coverage/separate-root purpose **without** making the finding claimable.
* Adjacent, dead-legacy, tests-only, and different-invariant findings still get packets under the owner rule, but **not** working claimable chats (`CHAT_REQUIRED=false`, `STATUS=backlog`).
* `duplicate_root` / `DUP-*` observations are part of the known root case: keep an optional record with `STATUS: duplicate_root_observation` if useful for evidence, but **never** `CHAT_REQUIRED=true` or `STATUS=available`. Do not overload `absorbed_by_parent_fix` or `duplicate_ancestor` for this class.
* Low-risk and unclear findings are claimable **only** when they meet the child-chat-eligible row (including `CHILD_CHAT_RECOMMENDED=true`). Do not promote them solely because they are non-FP.
* Only proven false positives skip the working chat packet entirely; backlog-class still keeps a durable packet/record.
* Do not invent absorption. Set `absorbed_by_parent_fix` only when the authoritative source already states that disposition.
* Never let durable ownership override fanout “no child chat” rules by writing `CHAT_REQUIRED=true` for backlog-class forbids or for `duplicate_root` / `DUP-*`.

## Claim priority assignment

At materialize time, assign `CLAIM_PRIORITY` once and store it on the finding.

This is operational queue order, not a new severity policy.

Mapping:

```text
1 = confirmed production bug
2 = reachable but low-risk
3 = unclear reachability
4 = different_invariant_candidate / different-invariant candidate
5 = adjacent_out_of_scope / dead legacy / tests-only / other backlog (CHAT_REQUIRED=false)
```

Tie-breaker later used by `/opsx-claim-next-bug`:

1. lower `CLAIM_PRIORITY` number first;
2. then source registration order in `LEDGER.md`;
3. then `FINDING_ID` lexicographic ascending.

Do not re-rank on every claim.

If the authoritative source already provides an explicit ordered list, preserve that order inside equal `CLAIM_PRIORITY` buckets via ledger registration order.

## mode=intake

Create a durable raw intake before adjudication.

Typical sources:

* Bugbot (residual external safety net);
* `/opsx-project-bug-hunt` structured findings (primary project-tuned hunter;
  prefer one intake per finding `RAW_REPORT` from that command's output);
* manual finding;
* CI;
* incident;
* promotion from another case;
* automatic call from `/opsx-fix-bug` when `case`/`intake` are absent.

Required logical inputs:

```text
mode=intake
RAW_REPORT
```

`RAW_REPORT` may come from `$ARGUMENTS`, an explicit field block, or the immediate bug text in the same invocation.

Optional inputs:

```text
case=<CASE_ID>
intake=<INTAKE_ID>
SOURCE_TYPE
SOURCE_REFERENCE
OBSERVED_SYMPTOM
KNOWN_CONTEXT
```

Auto-generation when omitted:

* `CASE_ID`: `BUGCASE-<SHORT>-<UTC>` where `<SHORT>` is a compact slug from symptom/source (fallback `MANUAL`) and `<UTC>` is `YYYYMMDDTHHMMSSZ`;
* `INTAKE_ID`: next free `INTAKE-NNN` inside the case (`INTAKE-001` for a new case).

Defaults when omitted:

```text
SOURCE_TYPE: manual
SOURCE_REFERENCE: invocation payload
OBSERVED_SYMPTOM: first non-empty line / short summary of RAW_REPORT
KNOWN_CONTEXT: empty
STATUS: intake_recorded
NEXT_ACTION: /opsx-claim-next-bug case=<CASE_ID> chat_label="<label>"  # or /opsx-classify-bug when claim not required
```

If `case=<CASE_ID>` points to an existing case:

* do not destroy the case;
* append a new intake file with a new `INTAKE_ID`;
* update `PRIMARY_INTAKE_ID` only when the caller explicitly requests it or no primary intake exists;
* do not invent findings.

If `case` is omitted, create a new case directory.

Minimal actions:

1. Create `<CASE_ID>/` layout including `intakes/`, `findings/`, `handoffs/`, `results/` when the case is new.
2. Write `intakes/<INTAKE_ID>.md` with the required intake fields and verbatim `RAW_REPORT`.
3. Write or update `CASE.md` with `PRIMARY_INTAKE_ID`, `STATUS=intake_recorded`, `CURRENT_STAGE=intake_recorded`, `LAST_COMMAND=/opsx-materialize-bug-queue mode=intake`, and pasteable `NEXT_ACTION`.
4. Write or update `LEDGER.md` with summary counts; do **not** create a finding row by default.
5. Write `handoffs/COMMON_HANDOFF.md` when the case is new.
6. Update `INDEX.md` recovery row for the case.

Default behavior:

* no `findings/<FINDING_ID>.md`;
* no `ROOT_FINDING_ID` assignment;
* no production classification;
* no invariant;
* no child chats.

Compatibility escape hatch only when the caller explicitly passes:

```text
create_root_finding=true
```

Then a root finding packet may be created in addition to the intake. Default remains intake-only.

Raw intake does not by itself create child chats or claimable findings.

## mode=hunt-result

Accept structured output from root-aware `/opsx-bug-hunt`.

Required inputs:

```text
mode=hunt-result
case=<CASE_ID>
source=<artifact-or-inline-hunt-result>
```

If `source` is omitted, the command MAY use the immediately preceding complete `/opsx-bug-hunt` output in the same chat.

It MUST NOT reconstruct hunt results from distant chat memory.

Required source sections:

```text
KNOWN_ROOT_RESULT
NEW_FINDINGS
```

Prefer also:

```text
FANOUT_INPUT
ROOT_FINDING_ID
INVARIANT
```

If incomplete, stop with:

```text
Verdict:
- blocked

Blocker:
- incomplete_bug_hunt_result
```

and list missing fields.

### Trust boundary

Treat the hunt result as authoritative for:

* production classification;
* relationship to root;
* finding IDs;
* evidence snapshots;
* known-root status.

This command may:

* validate structural completeness;
* create/update durable files;
* assign ledger states and `CHAT_REQUIRED` by the matrix above;
* create packets;
* count chats required.

This command must not:

* inspect code again to change classifications;
* merge, split, or renumber findings;
* turn adjacent into confirmed production bug;
* turn unclear into confirmed;
* drop findings;
* create working chats for false positives.

### Materialize all of

* known root;
* confirmed findings;
* low-risk findings;
* unclear findings;
* adjacent findings;
* different-invariant candidates;
* false positives;
* dead legacy;
* tests-only findings;
* optional `duplicate_root` / `DUP-*` observation records (evidence only; never claimable).

Preserve IDs from the hunt. Do not renumber `ROOT-001`, `CHILD-001`, `ADJ-001`, `FP-001`, `DUP-001`, etc.
Never promote a `DUP-*` or `duplicate_root` observation to a claimable `CHILD-*` / `STATUS=available` row.

### False positives

For every proven false positive:

* keep a closed record in `findings/<FINDING_ID>.md`;
* set `STATUS: closed_false_positive`;
* set `CHAT_REQUIRED: false`;
* set `PACKET_PATH` empty or point to the closed record explicitly labeled `CLOSED_FALSE_POSITIVE_RECORD`;
* do not create a working chat packet section;
* preserve:

```text
ORIGINAL_CLAIM
EVIDENCE
REASON_REJECTED
SOURCE_SNAPSHOT
COMPLETED_AT
ROOT_FINGERPRINT
```

Never delete FP records.

### Known root

Update the root ledger row from `KNOWN_ROOT_RESULT`.

Do not create a new working chat for the known root merely because hunt reconfirmed it.

Set materialize output flag:

```text
EXISTING_ROOT: true
```

### CHILD absorbed by root fix

If the authoritative source states the finding is absorbed by the root fix:

```text
STATUS: absorbed_by_parent_fix
CHAT_REQUIRED: false
DISPOSITION: absorbed_by_parent_fix
```

Preserve the packet for audit and later verification.

Do not count it in `CHATS_REQUIRED`.

## mode=promote

Create a new descendant case from an adjudicated finding.

Required inputs:

```text
mode=promote
parent_case=<PARENT_CASE_ID>
source_finding=<SOURCE_FINDING_ID>
case=<NEW_CASE_ID>
proposed_invariant=<text>
root_fingerprint=<value-or-compute>
```

Also require enough payload to create the new root finding packet.

Before creating the new case:

1. Read parent `CASE.md`.
2. Build `ANCESTOR_CHAIN = parent.ANCESTOR_CHAIN + parent.CASE_ID` if not already terminal-inclusive; store the full chain including the new case after creation.
3. Set `DEPTH = parent.DEPTH + 1`.
4. Compute or verify `ROOT_FINGERPRINT`.
5. Compare fingerprint against every ancestor case fingerprint.
6. If fingerprint matches an ancestor:

```text
STATUS: duplicate_ancestor
```

Do not create the new case directory.

Update the source finding in the parent ledger:

```text
STATUS: duplicate_ancestor
DISPOSITION: duplicate_ancestor
NEXT_ACTION: none
```

and return the duplicate result.

### Depth warning

If `DEPTH >= 5`:

* emit warning `DEEP_PROMOTION_WARNING`;
* do not create the descendant case unless the user input contains the exact token:

```text
CONFIRM_DEEP_PROMOTE
```

If confirmation is missing, stop with:

```text
Verdict:
- blocked

Blocker:
- deep_promotion_needs_confirm
```

After successful promote:

* create the new flat case directory;
* set parent finding:

```text
STATUS: promoted_to_root_case
DISPOSITION: promoted_to_root_case
RESULT_PATH: ../<NEW_CASE_ID>/CASE.md
```

* new case starts at intake/adjudication-ready state with its own root finding;
* update `INDEX.md` for both cases.


## mode=fanin_assemble

Assemble read-only fan-in rollup for a root episode.

Required:

```text
mode=fanin_assemble
case=<ROOT_CASE_ID>
```

Schema: `.cursor/pipeline/contracts/bug-episode/FANIN.md`.

### Write boundary (HARD)

```text
PRODUCTION_READ_ONLY: YES
COMMAND_AND_GRAPH_READ_ONLY: YES

CASE_MAP_WRITE_ALLOWED:
  .opsx/runs/bug-cases/<ROOT_CASE_ID>/results/FANIN.md

ALL_OTHER_WRITES: DENIED
```

This mode MUST NOT:

* edit production code or tests;
* edit `.cursor/commands/**`, GRAPH, META, or ORCHESTRATION markers to ACTIVE;
* create `/opsx-fan-in-*`;
* mutate LEDGER finding claim `STATUS`, `CLAIM_TOKEN`, OWNER fields
  (read LEDGER / BRANCH_REGISTRY only);
* write any other case-map path (including intakes/, findings/, INDEX.md);
* exercise Owner authority or close the error class;
* claim `LEARNING_READY` as `FANIN_READY`.

### Preconditions

Fan-in assemble is forbidden until:

* `ROOT_CASE_ID` present and case map exists;
* `ROOT_FINDING_ID` / root invariant known (from CASE.md / root finding);
* `HUNT_PASSES_EXECUTED ≤ MAX_HUNT_PASSES` (default 3);
* `## BRANCH_REGISTRY` lists all started branches;
* every started branch has `EPISODE_TERMINAL` ∈ episode terminal set;
* `LIMITS_CHECK` can be evaluated.

If preconditions fail, write `results/FANIN.md` with
`STATUS: FANIN_INCOMPLETE` **only if** the caller explicitly requests a
partial assemble receipt; otherwise stop with:

```text
Verdict:
- blocked

Blocker:
- fanin_preconditions_not_met
```

Preferred: always write `FANIN.md` with either `FANIN_READY` or
`FANIN_INCOMPLETE` so the lesson gate has a durable path — but never write
any path other than `results/FANIN.md`.

### Output

Write exactly:

```text
.opsx/runs/bug-cases/<ROOT_CASE_ID>/results/FANIN.md
```

Include required FANIN fields from the schema (STATUS, BRANCH_SUMMARY,
CHECKS 1–6, LIMITS_CHECK, etc.).

```text
FANIN_READY
  iff assembly complete
  ∧ all started branches terminal
  ∧ checks 3–6 PASS
  ∧ checks 1–2 PASS or N/A with Owner-noted exceptions
```

Else `FANIN_INCOMPLETE`.

Pasteable next when `FANIN_READY`:

```text
/opsx-learn-from-bug case=<ROOT_CASE_ID> FANIN_PATH=.opsx/runs/bug-cases/<ROOT_CASE_ID>/results/FANIN.md
```

When incomplete:

```text
LESSON_CANDIDATE_ONLY
CLASS_STATUS: OPEN
CLASS_LEVEL_GO_WRITE: FORBIDDEN
```

## mode=update

Update only explicitly provided fields on an existing case, intake, or finding.

Required:

```text
mode=update
case=<CASE_ID>
```

Optional selectors:

```text
intake=<INTAKE_ID>
finding=<FINDING_ID>
```

### Close finding after GREEN (`close=fixed`)

Authority: `.cursor/pipeline/contracts/bug-episode/CLOSE_POLICY.md`.

```text
mode=update
case=<CASE_ID>
finding=<FINDING_ID>
close=fixed
```

Allowed only when:

* GREEN evidence exists (`GREEN_EVIDENCE_PATH` / `results/GREEN-<FINDING_ID>.md`);
* route reconciliation permits episode close (ORCHESTRATION §0.7);
* caller is post-`/opsx-test verify` or explicit Owner solo close — **not**
  `/opsx-apply` / `/opsx-update` / `/opsx-verify`.

Writes:

* finding `STATUS: closed_fixed`
* `EPISODE_TERMINAL: FIXED`
* `COMPLETED_AT` (UTC ISO-8601)
* LEDGER counts / finding row
* CASE/INDEX terminal or next-action refresh (if no other open working
  findings → case may move to closed/fixed stage; else keep case open and
  set NEXT to remaining work / handback)

Optional:

```text
leave_open_reason=<token from CLOSE_POLICY>
```

When `leave_open_reason=` is set instead of `close=fixed`, do **not**
set `closed_fixed`; record reason on finding/ROUTE_STATE only.

Also may patch close-intent fields when explicitly named:

```text
CLOSE_FINDING_INTENT=
POST_GREEN_OWNER=
HANDBACK_COMMAND=
```

Rules:

* patch only named fields from `$ARGUMENTS` or an explicit field block;
* do not rewrite the whole ledger from chat memory;
* do not invent status transitions **except** the documented `close=fixed`
  / leave_open_reason ops above;
* do not clear `OWNER_CHAT` / `CLAIM_TOKEN` unless explicitly requested
  **or** an explicit `repair=` corrupt-claim op below applies;
* do not auto-steal claims;
* append a short update note with timestamp in the intake/finding file or ledger history section if present;
* refresh `UPDATED_AT` / `LAST_ACTIVITY_AT` when touching a case, intake, or finding;
* refresh `INDEX.md` recovery fields when stage, next action, blockers, or finding counts change.

### Corrupt-claim repair (`repair=`)

Explicit ops for `STATUS=claimed` + empty/absent durable `CLAIM_TOKEN`.
Claim-next cannot mint/repair this state; fix-bug must paste these, not
claim-next. Never auto-reclaim; never silent steal; only when the caller
passes the exact `repair=` token (or equivalent named field block).

Required:

```text
mode=update
case=<CASE_ID>
finding=<FINDING_ID>
repair=mint_missing_claim_token | release_corrupt_claim
```

Preconditions (both repair values):

* finding exists;
* `STATUS=claimed`;
* durable `CLAIM_TOKEN` empty / absent.

If preconditions fail → `blocked` / `repair_precondition_failed` (no partial writes).

#### `repair=mint_missing_claim_token`

Prefer when `OWNER_CHAT` is non-empty.

* keep `STATUS=claimed` and `OWNER_CHAT`;
* set `CLAIMED_AT` to existing value if present, else now (UTC ISO-8601);
* write `CLAIM_TOKEN: CLAIM/<CASE_ID>/<FINDING_ID>/<CLAIMED_AT>`
  (same form as `/opsx-claim-next-bug`);
* refresh `LAST_ACTIVITY_AT` / INDEX;
* pasteable `NEXT_ACTION`:
  `/opsx-fix-bug case=<CASE_ID> intake=<…> finding=<FINDING_ID> claim_token=<CLAIM_TOKEN>`
  (include non-empty `intake=` when known).

If `OWNER_CHAT` is empty / absent → do not mint; stop with
`blocked` / `repair_needs_owner_or_release` and recommend
`repair=release_corrupt_claim`.

#### `repair=release_corrupt_claim`

Use when `OWNER_CHAT` is empty / unknown, or operator chooses re-queue.

* set `STATUS=available` (only valid when `CHAT_REQUIRED=true`; if
  `CHAT_REQUIRED=false`, stop with `repair_precondition_failed` — do not
  invent claimable state);
* clear `OWNER_CHAT`, `CLAIMED_AT`, `CLAIM_TOKEN`;
* append a short ledger/finding note that corrupt claim was released;
* refresh INDEX;
* pasteable `NEXT_ACTION`:
  `/opsx-claim-next-bug case=<CASE_ID> chat_label="<label>"`.

Still: this command never auto-reclaims; `repair=` is the only allowed
path to repair durable-empty claimed rows.

### Creating or updating a finding after adjudication

`/opsx-fix-bug` without `GO` persists adjudication through this mode (not a separate mode).

When the field block includes a new or updated finding, write or patch:

```text
FINDING_ID
SOURCE_INTAKE_ID
TITLE
PRODUCTION_CLASSIFICATION
RELATION_TO_ROOT
STATUS
CHAT_REQUIRED
PACKET_PATH
CLAIM_PRIORITY
NEXT_ACTION
...plus other provided finding fields
```

Rules for adjudication persistence:

* `SOURCE_INTAKE_ID` MUST be set when the case has a known intake;
* do not create a finding during `mode=intake` by default; create/update it here after adjudication;
* if `FINDING_ID` is omitted for a new finding, allocate the next free id (`ROOT-001` for the first finding in the case, otherwise the next stable typed id supplied by the caller);
* update `CASE.md` `ROOT_FINDING_ID` when the first root finding is created;
* set `CURRENT_STAGE` appropriately (for example `adjudicated`);
* set `LAST_COMMAND` to the command that requested the update;
* set pasteable `NEXT_ACTION` on case and INDEX.

### Cross-intake finding update guard

Before updating an **existing** finding when `intake=<INTAKE_ID>` is present (or implied as the current intake):

1. Read the finding's existing `SOURCE_INTAKE_ID`.
2. Compare with the current intake id.

Allowed without special relation:

```text
existing SOURCE_INTAKE_ID == current INTAKE_ID
```

or the finding is being newly created with:

```text
SOURCE_INTAKE_ID: <current INTAKE_ID>
```

If existing `SOURCE_INTAKE_ID` differs from current `INTAKE_ID`:

* allow the update **only** when the caller explicitly passes:

```text
relation=duplicate_intake
```

* and then **do not modify** the canonical finding body/classification/status;
* instead update only:

  * the current intake (`STATUS=closed_duplicate`, `DISPOSITION=duplicate_intake`, `CANONICAL_INTAKE_ID`, `RELATED_FINDING_ID`);
  * ledger intake row;
  * `INDEX.md` recovery fields;
  * separate result file `results/<INTAKE_ID>-duplicate-check.md`.

Required duplicate fields:

```text
relation=duplicate_intake
canonical_intake=<CANONICAL_INTAKE_ID>
related_finding=<RELATED_FINDING_ID>
```

If a caller attempts to patch a finding whose `SOURCE_INTAKE_ID` differs from the current intake **without** `relation=duplicate_intake`, stop:

```text
Verdict:
- blocked

Blocker:
- cross_intake_finding_update_without_relation
```

Do not silently reassign `SOURCE_INTAKE_ID` of an existing finding to a newer intake.

Do not treat textual similarity alone as authorization for `relation=duplicate_intake`; that decision belongs to `/opsx-fix-bug` adjudication evidence.

### Duplicate-intake update path

When `relation=duplicate_intake`:

1. Verify `related_finding` exists.
2. Verify canonical finding `SOURCE_INTAKE_ID` equals `canonical_intake` (or document legacy empty `SOURCE_INTAKE_ID` explicitly in the duplicate-check result).
3. Leave the canonical finding unchanged.
4. Update current intake to `closed_duplicate`.
5. Write `results/<INTAKE_ID>-duplicate-check.md` with:

```text
DUPLICATE_INTAKE_CHECK

CASE_ID:
INTAKE_ID:
CANONICAL_INTAKE_ID:
RELATED_FINDING_ID:
LITERAL_CLAIM_MATCH:
BOUNDARY_MATCH:
ADJUDICATION_RESULT_MATCH:
NEW_EVIDENCE_SCOPE: false
REASON:
COMPLETED_AT:
```

6. Refresh INDEX / ledger / case timestamps and pasteable `NEXT_ACTION`.

If the case does not exist, stop with blocker `unknown_case`.

If `finding=<FINDING_ID>` is supplied and the finding file/row does not exist, creating it is allowed when the field block provides the required finding fields and `SOURCE_INTAKE_ID` equals the current intake (or the current intake is being linked as the source).

If `intake=<INTAKE_ID>` is supplied and the intake does not exist, stop with blocker `unknown_intake` unless the caller is explicitly creating that intake via field block in the same update (prefer `mode=intake` for new intakes).

## File contents

### CASE.md

Write a compact Markdown case record with the required case fields and a short summary of source.

### LEDGER.md

Write a deterministic registry.

Recommended structure:

```markdown
# Ledger: <CASE_ID>

## Summary
- TOTAL_INTAKES:
- TOTAL_FINDINGS:
- CHATS_REQUIRED:
- READY_TO_CLAIM:
- CLAIMED_NOT_COMPLETED:
- BLOCKED:
- BACKLOG:
- CLOSED:

## Intakes

### <INTAKE_ID>
- STATUS:
- SOURCE_TYPE:
- CREATED_AT:
- LAST_ACTIVITY_AT:
- NEXT_ACTION:
- DISPOSITION:
- CANONICAL_INTAKE_ID:
- RELATED_FINDING_ID:
- RESULT_PATH:
- PACKET_PATH: intakes/<INTAKE_ID>.md

## Findings

### <FINDING_ID>
- TITLE:
- SOURCE_INTAKE_ID:
- PARENT_FINDING_ID:
- PRODUCTION_CLASSIFICATION:
- RELATION_TO_ROOT:
- STATUS:
- CHAT_REQUIRED:
- CLAIM_PRIORITY:
- PACKET_PATH:
- OWNER_CHAT:
- CLAIM_TOKEN:
- CREATED_AT:
- CLAIMED_AT:
- LAST_ACTIVITY_AT:
- COMPLETED_AT:
- NEXT_ACTION:
- BLOCKER:
- RESULT_PATH:
- DISPOSITION:
- EPISODE_TERMINAL:
- RED_EVIDENCE_PATH:
- GREEN_EVIDENCE_PATH:
- OWNER_GO_RECEIPT_PATH:
- FIX_EVIDENCE_PATH:
- TEST_ID:
- FANIN_PATH:

## BRANCH_REGISTRY

Schema: `.cursor/pipeline/contracts/bug-episode/BRANCH_REGISTRY.md`.

Header counters when known:

```text
HUNT_PASSES_EXECUTED:
MAX_DEPTH_SEEN:
ACTIVE_BRANCH_COUNT:
```

One row per started branch (FINDING_ID, PARENT, DEPTH, EPISODE_TERMINAL,
evidence paths, OWNER_PRODUCTION_GO, …).

## ROUTE_STATE

Current snapshot only (append-only history is ROUTE-TRACE.jsonl).
MUST align with the latest applicable JSONL event:

```text
CURRENT_CLASSIFICATION:
EXPECTED_EXECUTION_ROUTE:
ACTUAL_EXECUTION_ROUTE:
ROUTE_RECONCILIATION:

CURRENT_ROUTE_STATE:
LAST_ROUTE_EVENT_ID:
LAST_ROUTE_EVENT_SEQUENCE:
LAST_ROUTE_EVENT_AT:

CURRENT_ACTOR_ROLE:
CURRENT_ACTOR_AGENT_ID:
CURRENT_ACTOR_CHAT_ID:

OWNER_GATE_STATUS:
TASK_DELTA:
TERMINAL_STATUS:

ROUTE_TRACE_PATH: .opsx/runs/bug-cases/<CASE_ID>/results/ROUTE-TRACE.jsonl
NEXT_ACTION:
```

Schema: `.cursor/pipeline/contracts/bug-episode/ROUTE_TRACE.md` (SCHEMA_VERSION 2).

```

Keep intake and finding sections in stable registration order.

### intakes/<INTAKE_ID>.md

Write a durable raw intake record:

```text
INTAKE_RECORD

CASE_ID:
INTAKE_ID:
CREATED_AT:
SOURCE_TYPE:
SOURCE_REFERENCE:
RAW_REPORT:
OBSERVED_SYMPTOM:
KNOWN_CONTEXT:
STATUS: intake_recorded
LAST_ACTIVITY_AT:
NEXT_ACTION: /opsx-claim-next-bug case=<CASE_ID> chat_label="<label>"  # or /opsx-classify-bug when claim not required
DISPOSITION:
CANONICAL_INTAKE_ID:
RELATED_FINDING_ID:
RESULT_PATH:
```

For duplicate closure, set `STATUS: closed_duplicate` and fill disposition linkage fields.
### findings/<FINDING_ID>.md

For chat-required or preserved non-FP findings, write an autonomous packet:

```text
FINDING_PACKET

CASE_ID:
FINDING_ID:
SOURCE_INTAKE_ID:
PARENT_FINDING_ID:
TITLE:
PRODUCTION_CLASSIFICATION:
RELATION_TO_ROOT:
STATUS:
CHAT_REQUIRED:
CLAIM_PRIORITY:
PACKET_PURPOSE:
INVARIANT:
ORIGINAL_FINDING:
EVIDENCE:
RUNTIME_PATH:
CAUSAL_BOUNDARY:
WRITE_BOUNDARY:
SOURCE_SNAPSHOT:
DISPOSITION:
NEXT_ACTION:

NEXT_COMMAND (when STATUS=available and CHAT_REQUIRED=true, pre-claim):
/opsx-claim-next-bug case=<CASE_ID> chat_label="<owner-label>"

NEXT_COMMAND (only after claim, before implementation route):
/opsx-classify-bug case=<CASE_ID> finding=<FINDING_ID>

NEXT_COMMAND (only after classify Route A, or TASK_DELTA NO → fix-bug):
/opsx-fix-bug case=<CASE_ID> intake=<SOURCE_INTAKE_ID> finding=<FINDING_ID> claim_token=<CLAIM_TOKEN>

MODE:
READ_ONLY

FORBIDDEN:
- do not edit production files
- do not use GO
- do not claim a second finding
- do not open other chats
- do not promote without /opsx-materialize-bug-queue mode=promote
- do not emit bare /opsx-fix-bug without case=/finding=/claim_token=
```

When `CHAT_REQUIRED=true` and the finding is still `available` (unclaimed), `NEXT_COMMAND` MUST be `/opsx-claim-next-bug case=<CASE_ID> chat_label="…"` — never bare `/opsx-fix-bug`. After claim, `/opsx-claim-next-bug` supplies `/opsx-classify-bug` (mandatory); classify then routes to fix-bug/update. Durable `claim_token=` is still required for later `/opsx-fix-bug`.

`PACKET_PURPOSE` must be one of:

```text
adjudication
disposition_decision
backlog_decision
promotion_decision
root_tracking
audit_preserved
```

For false positives, write `CLOSED_FALSE_POSITIVE_RECORD` with the required preserved fields and no implementation next command.

### handoffs/COMMON_HANDOFF.md

Always write a short shared handoff:

```text
COMMON_HANDOFF

CASE_ID: <CASE_ID>

Paste into a new chat:

/opsx-claim-next-bug case=<CASE_ID> chat_label="<your-label>"

Rules:
- do not include a finding ID
- the claim command selects the next available finding
- do not add GO
- do not start implementation automatically
```

Do not embed a specific finding ID in the common handoff.

### INDEX.md

Maintain a repo-local recovery board.

Every open case MUST expose a recovery row with:

```text
CASE_ID
INTAKE_ID
RAW_SUMMARY
CURRENT_STAGE
LAST_COMMAND
LAST_ACTIVITY_AT
OPEN_FINDINGS
OPEN_CANDIDATES
READY_FOR_FIX
BLOCKERS
NEXT_ACTION
```

Rules for the recovery row:

* `INTAKE_ID` is the primary/latest open intake for continuation;
* `RAW_SUMMARY` is a short durable summary of `RAW_REPORT` (recommended ≤ 200 chars);
* `CURRENT_STAGE` mirrors case stage (`intake_recorded`, `adjudicated`, `hunt_materialized`, etc.);
* `LAST_COMMAND` is the last OPSX command that wrote the case map;
* `NEXT_ACTION` MUST be an exact pasteable command (not prose);
* after chat loss, opening `INDEX.md` MUST be enough to continue;
* `OPEN_CANDIDATES` MUST list every hunt/residual candidate with
  `STATUS ∈ {open_candidate, OPEN_CANDIDATE}` (include `HUNT_CANDIDATE_ID`
  and proposed `FINDING_ID` when known);
* SAME_INVARIANT open candidates are HARD_BLOCK_READY debt: put them in
  `BLOCKERS`, set `NEXT_ACTION` to
  `/opsx-bug-team case=<CASE_ID> mode=resume-family-fanout`
  (or materialize sibling then fanout), and **MUST NOT** imply case is
  closable / READY_FOR_CLOSURE while they remain open;
* after hunt or FANIN that surfaces such residuals, INDEX recovery MUST be
  refreshed in the same operator session (FAN_IN_ASSEMBLER does not write
  INDEX — orchestrator / `mode=update` / closure hop that already owns INDEX
  refresh MUST fulfill this obligation).

Recovery `NEXT_ACTION` may use orchestration stages when companions apply
(still not ACTIVE until GO_ACTIVATE):

```text
finding_claimed          → /opsx-classify-bug case=<CASE_ID> finding=<FINDING_ID>
classified_impl          → /opsx-fix-bug … WITHOUT GO (+ claim_token)
classified_spec          → /opsx-update <change-id> …
task_delta_changed       → /opsx-apply <change-id>   # still needs RED+Owner GO
task_delta_unchanged     → /opsx-fix-bug … WITHOUT GO
red_pending              → /opsx-test case=<CASE_ID> finding=<FINDING_ID>
production_go_ready      → /opsx-fix-bug … GO  or  /opsx-apply   # Owner GO only after RED
FANIN_INCOMPLETE_SAME_INVARIANT_OPEN → /opsx-bug-team case=<CASE_ID> mode=resume-family-fanout
FANIN_READY              → /opsx-learn-from-bug … FANIN_PATH=…
LESSON_CANDIDATE_ONLY    → Owner FINAL / keep candidate-only
```

Also maintain aggregate lists:

```text
FORGOTTEN_OR_STALE_CLAIMS
CLAIMED_NOT_COMPLETED
AVAILABLE_READY_TO_CLAIM
READY_FOR_FIX
OPEN_SAME_INVARIANT_CANDIDATES
BLOCKED
BACKLOG
CLOSED_FALSE_POSITIVES
ABSORBED
PROMOTED
```

A claim is visible as forgotten/stale for operator attention when:

```text
STATUS: claimed
```

and no automatic reclaim is performed.

This command never auto-reclaims.

Corrupt claim (`STATUS=claimed` + empty/absent durable `CLAIM_TOKEN`) is
repaired only via explicit `mode=update` `repair=mint_missing_claim_token`
or `repair=release_corrupt_claim` (see mode=update). Never invent a token
from chat memory without `repair=`.

## Counts

Compute:

```text
TOTAL_INTAKES
TOTAL_FINDINGS
CHATS_REQUIRED
READY_TO_CLAIM
CLOSED_FALSE_POSITIVES
EXISTING_ROOT
BLOCKED_ITEMS
```

Definitions:

* `TOTAL_INTAKES`: all intake records under `intakes/`;
* `TOTAL_FINDINGS`: all ledger findings including root and FPs;
* `CHATS_REQUIRED`: findings with `CHAT_REQUIRED=true` and status not in terminal closed set;
* `READY_TO_CLAIM`: `STATUS=available` and `CHAT_REQUIRED=true`;
* `CLOSED_FALSE_POSITIVES`: `STATUS=closed_false_positive`;
* `EXISTING_ROOT`: true when known root is present in the case;
* `BLOCKED_ITEMS`: `STATUS=blocked`.

Terminal closed set for chat counting:

```text
closed_fixed
closed_false_positive
absorbed_by_parent_fix
promoted_to_root_case
duplicate_ancestor
duplicate_root_observation
```

## Output contract

Return exactly:

```text
CASE_MATERIALIZED

CASE_ID:
INTAKE_ID:
ROOT_FINDING_ID:
CASE_PATH:
STATUS:

TOTAL_INTAKES:
TOTAL_FINDINGS:
CHATS_REQUIRED:
READY_TO_CLAIM:
CLOSED_FALSE_POSITIVES:
EXISTING_ROOT:
BLOCKED_ITEMS:

FINDING_BREAKDOWN:
- <FINDING_ID>: <STATUS> chat_required=<true|false> packet=<path|none> purpose=<...>

FIRST_CLAIM_CANDIDATE:
- <FINDING_ID or none>

COMMON_HANDOFF:
/opsx-claim-next-bug case=<CASE_ID> chat_label="<label>"

COMMAND_RECEIPT:
  COMMAND: /opsx-materialize-bug-queue
  CASE_ID:
  INTAKE_ID:
  FINDING_ID:
  RESULT:
  OUTPUT_PATH:
  NEXT_ACTION:

SOURCE_RESOLUTION:
- mode: exact_path | canonical_id | referenced_source | bounded_fallback
- primary_path:
- fallback_used: true | false
- search_operations: 0
- search_scope: .opsx/runs/bug-cases/<CASE_ID>
- unresolved_gap:
```

For `mode=intake` by default:

* `ROOT_FINDING_ID` and `FINDING_ID` may be empty;
* `TOTAL_FINDINGS` may be `0`;
* `NEXT_ACTION` must be pasteable `/opsx-fix-bug case=<CASE_ID> intake=<INTAKE_ID>`.

`FIRST_CLAIM_CANDIDATE` is informational only. It must equal what `/opsx-claim-next-bug` would currently select, using stored `CLAIM_PRIORITY` and stable order.

## Compatibility

OPSX commands that continue a case SHOULD accept:

```text
case=<CASE_ID>
intake=<INTAKE_ID>
finding=<FINDING_ID>
```

and emit:

```text
COMMAND_RECEIPT:
  COMMAND:
  CASE_ID:
  INTAKE_ID:
  FINDING_ID:
  RESULT:
  OUTPUT_PATH:
  NEXT_ACTION:
```

`/opsx-fix-bug` without `GO` MUST use this command's `mode=intake` contract to create a missing intake, then `mode=update` to persist the adjudicated finding. It must not invent a second storage layout.

`/opsx-fanout-bug-hunt` remains an intermediate chat-packet helper. Durable
ownership and recursion live in this case map. Durable `CHAT_REQUIRED` /
claimable `STATUS` assignments **must** stay aligned with fanout
`CREATE_CHILD_CHAT` eligibility and forbids: backlog-class findings
(adjacent / dead legacy / tests-only) and separate-root candidates must not
become claimable chats merely because this map owns persistence.

## Acceptance anchor

For case `BUGCASE-ABHOLD-WBSYNC-001` after hunt-result materialization, expected durable outcomes:

```text
ROOT-001  -> existing root, no new chat
CHILD-001 -> packet preserved, absorbed_by_parent_fix, chat_required=false
CHILD-002 -> packet created, available, chat_required=true
ADJ-001   -> packet created, backlog, chat_required=false
DUP-001   -> STATUS=duplicate_root_observation, chat_required=false, never available
FP-001    -> closed_false_positive, no working chat packet
FP-002    -> closed_false_positive, no working chat packet
```

Expected counts:

```text
TOTAL_FINDINGS: 7
CHATS_REQUIRED: 1
READY_TO_CLAIM: 1
BACKLOG: 1
CLOSED_FALSE_POSITIVES: 2
EXISTING_ROOT: true
FIRST_CLAIM_CANDIDATE: CHILD-002
```

Corrupt-claim repair:

* `CHILD-002` `STATUS=claimed`, `OWNER_CHAT` set, `CLAIM_TOKEN` empty →
  `mode=update … repair=mint_missing_claim_token` writes non-empty
  `CLAIM_TOKEN=CLAIM/…` and keeps ownership; next is fix-bug with that token.
* Same row with empty `OWNER_CHAT` → mint blocked; `repair=release_corrupt_claim`
  returns `STATUS=available` (when `CHAT_REQUIRED=true`) for a later claim-next.
* Without exact `repair=` → no auto mint / no auto reclaim.

## Hard rules

* No repository re-analysis for new bugs.
* No classification mutation.
* No finding loss.
* No working chat for proven false positives.
* No claimable chat (`CHAT_REQUIRED=true` + `STATUS=available`) for fanout backlog-class forbids: adjacent / dead legacy / tests-only; nor for different-invariant as a child claim on this case.
* No claimable chat for `duplicate_root` / same-causal-path duplicates of the known root / `DUP-*` observations (fanout `duplicate_root_emitted_as_new_finding` class); durable STATUS MUST be `duplicate_root_observation`.
* No nested case directories.
* No cycle creation when ancestor fingerprint matches.
* No deep promote at `DEPTH >= 5` without `CONFIRM_DEEP_PROMOTE`.
* No production edits.
* No `GO` in handoffs.
* No automatic claim.
* No automatic stale-claim takeover.
* Corrupt claimed rows (empty durable `CLAIM_TOKEN`) repair only via explicit `repair=mint_missing_claim_token` or `repair=release_corrupt_claim`; never invent tokens without `repair=`.
* `mode=intake` stores raw intake before adjudication and does not create a finding by default.
* Do not update an existing finding whose `SOURCE_INTAKE_ID` differs from the current intake unless `relation=duplicate_intake` is explicit; then leave the canonical finding unchanged.
* Reject cross-intake finding patches without relation with blocker `cross_intake_finding_update_without_relation`.
* Do not migrate or rewrite existing cases unless explicitly requested by a later command.
* Do not invent a second authoritative storage outside `.opsx/runs/bug-cases/**`.
