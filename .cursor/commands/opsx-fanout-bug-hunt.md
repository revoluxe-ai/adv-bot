---

description: "Normalize a root-aware bug-hunt result into deterministic child cases and chat-start packets without re-investigating or modifying the repository."
argument-hint: "root_case_id=<id> [root_chat_url=<url>] [source=<artifact-or-preceding-output>] [max_children=<n>]"
-------------------------------------------------------------------------------------------------------------------

# /opsx-fanout-bug-hunt

You are performing deterministic fan-out of a completed root-aware `/opsx-bug-hunt`.

This command is NOT a bug hunt.

This command is NOT a diff review.

This command is NOT an implementation command.

This command MUST NOT inspect new repository scope, prove new reachability, fix code, create Git branches, or run learning.

Its only purpose is to transform an already structured bug-hunt result into:

1. a stable finding registry;
2. actionable child-case packets;
3. deterministic child-chat titles;
4. a manifest for an external browser or coordinator layer.

The command itself does not physically create chats unless a separate browser automation explicitly consumes its manifest.

## Source resolution (mandatory)

Follow `.cursor/commands/opsx-source-resolution.md` and `.cursor/commands/opsx-execution-preflight.md`.

If `root_case_id` / source artifact / preceding hunt output path is provided:

* read that exact source only;
* do not open a new repository investigation to rediscover findings;
* do not run git status/branch;
* if source is missing, return blocker / `blocked_needs_exact_source` rather than exploring.

## Durable case-map gate (mandatory)

Implements Durable Handoff Readiness (section **F**) in
`.cursor/commands/opsx-source-resolution.md` for this command.

Before emitting `Verdict: ready` or any claimable `/opsx-claim-next-bug`
handoff (including coordinator "open child chat" instructions):

1. Check the exact path `.opsx/runs/bug-cases/<ROOT_CASE_ID>/` exists
   (canonical path only; do not search the wider repository).
   This existence check is allowed process I/O — it is **not** production-code
   inspection and does **not** authorize rediscovery of findings.
2. If the path is absent:
   - `Verdict: blocked`
   - `Blocker: durable_case_map_missing`
     (same class as claim’s `case_not_materialized`)
   - Input validation: `case_map_present: false`
   - `Next action`: exact pasteable
     `/opsx-materialize-bug-queue mode=hunt-result case=<ROOT_CASE_ID> source=<same hunt source>`
   - Do **not** instruct the browser/coordinator layer to open claim chats
   - Draft registry / packets may still be shown for preview, but every
     `CREATE_CHILD_CHAT` packet `NEXT_COMMAND` MUST be the materialize
     command above — never `/opsx-claim-next-bug` while the case map is absent
3. If the path is present: `case_map_present: true`; proceed with the normal
   ready → claim / `FANOUT_MANIFEST` coordinator flow.

A packet PREREQ note alone is **not** sufficient. Missing case map must block
readiness and route to materialize.

## User input

```text
$ARGUMENTS
```
## Purpose

After `/opsx-bug-hunt`:

* preserve the known root finding;
* exclude the known root from child-case creation;
* preserve all new findings without losing their relationship to the root;
* create one child-case packet for every finding that requires separate adjudication;
* prevent false positives, adjacent observations, dead legacy, and tests-only items from entering the implementation queue;
* prepare deterministic input for chat-opening automation;
* prepare a stable registry for later `/opsx-learn-from-bug`.

## Required inputs

Extract from `$ARGUMENTS` or from the explicitly referenced source:

* `root_case_id`: stable ID of the overall root bug case.
* `source`: structured result of the root-aware `/opsx-bug-hunt`.
* `root_chat_url`: optional URL of the existing root chat.
* `max_children`: optional maximum number of child chats to prepare.

If `source` is omitted, the command MAY use the immediately preceding complete `/opsx-bug-hunt` output in the same chat.

It MUST NOT reconstruct the source from distant chat history.

Default:

```text
max_children=10
```

Episode orchestration hard cap (stricter when companions apply):

```text
MAX_ACTIVE_BRANCHES=3
```

Use the **stricter** of `max_children` and `MAX_ACTIVE_BRANCHES` for
`CREATE_CHILD_CHAT` / claimable working branches. Excess →
`DEFERRED_CHILD_QUEUE` (not silent drop).

```text
IMPLEMENTATION_STATUS: LIVE_ACTIVATED
VALIDATION_STATUS: INDEPENDENT_TEST_PASS
RUNTIME_ENFORCEMENT: ACTIVE
LIVE_COMMAND_BEHAVIOR_CHANGED: YES
GO_ACTIVATE: ISSUED
```

If `root_case_id` is missing, stop.

If the source does not contain all of the following sections, stop:

```text
KNOWN_ROOT_RESULT
NEW_FINDINGS
FANOUT_INPUT
```

If the source does not contain a stable root finding ID, stop.

Return:

```text
Verdict:
- blocked

Blocker:
- incomplete_bug_hunt_result
```

and list the missing fields.

## Input contract

The source bug-hunt result must provide:

```text
ROOT_FINDING_ID
INVARIANT
KNOWN_ROOT_RESULT
NEW_FINDINGS
```

Every item in `NEW_FINDINGS` should provide:

```text
FINDING_ID
TITLE
PRODUCTION_CLASSIFICATION
RELATION_TO_ROOT
EVIDENCE
RUNTIME_PATH
CAUSAL_BOUNDARY
WRITE_BOUNDARY
SOURCE_SNAPSHOT
ADJUDICATION_REQUIRED
CHILD_CHAT_RECOMMENDED
```

Optional fields:

```text
RISK
REGRESSION_TEST
RECOMMENDED_ACTION
OWNER_MODULE
ORIGINAL_FINDING
```

Do not silently invent missing evidence.

If a field required for a child packet is missing, mark the item:

```text
ACTION: BLOCKED_INCOMPLETE_PACKET
```

Do not discard it.

## Trust boundary

Treat the structured `/opsx-bug-hunt` output as the authoritative input for this fan-out operation.

This command may:

* validate structural completeness;
* normalize IDs and titles;
* preserve classifications;
* preserve relationships to root;
* decide the routing action using the rules below;
* prepare child packets.

This command must not:

* inspect code again;
* change a production classification;
* change a relationship to root;
* promote `unclear reachability` to a production bug;
* turn an adjacent observation into a child bug;
* merge findings based only on file or patch overlap;
* split one finding into several speculative findings;
* repeat the bug hunt.

If the source contains an internal contradiction, do not resolve it by guessing.

Return:

```text
ACTION: NEEDS_SOURCE_CORRECTION
```

with the exact conflicting fields.

## Root handling

The known root finding is never a child.

Create exactly one root registry entry:

```text
ROOT_CASE:
  ROOT_CASE_ID:
  ROOT_FINDING_ID:
  ROOT_CHAT_URL:
  TITLE:
  STATUS:
  INVARIANT:
  SOURCE_SNAPSHOT:
```

Allowed root statuses:

```text
reconfirmed
not_reproduced_on_inspected_snapshot
evidence_changed
blocked_by_snapshot_uncertainty
```

The root entry must preserve the status returned by `/opsx-bug-hunt`.

The root entry must not receive:

* a child chat;
* a new child ID;
* a duplicate adjudication packet;
* a second implementation queue entry.

If the hunt accidentally includes the known root inside `NEW_FINDINGS`, return:

```text
Verdict:
- blocked

Blocker:
- root_emitted_as_new_finding
```

If the hunt accidentally includes a `duplicate_root` suspect inside
`NEW_FINDINGS` (same causal path as the known root, relationship
`duplicate_root`, or a `DUP-*` / same-root observation promoted to a
claimable child), return:

```text
Verdict:
- blocked

Blocker:
- duplicate_root_emitted_as_new_finding
```

Do not fan out until the bug-hunt result is corrected.
Do not `CREATE_CHILD_CHAT` for the known root or for any `duplicate_root`
suspect.

## Routing actions

Assign exactly one action to every item in `NEW_FINDINGS`.

Allowed actions:

```text
CREATE_CHILD_CHAT
BACKLOG_ONLY
CLOSE_FALSE_POSITIVE
CLEANUP_BACKLOG
TEST_COVERAGE_BACKLOG
CREATE_SEPARATE_ROOT_CANDIDATE
BLOCKED_INCOMPLETE_PACKET
NEEDS_SOURCE_CORRECTION
```

### CREATE_CHILD_CHAT

Use when all are true:

* `CHILD_CHAT_RECOMMENDED=true`;
* item is not the known root;
* item is not a `duplicate_root` suspect (same causal path as the known root);
* relationship is `same_invariant_different_path`;
* production classification is:

  * `confirmed production bug`;
  * `reachable but low-risk`;
  * `unclear reachability`;
* separate adjudication is useful or explicitly required.

A child chat is for read-only adjudication first.

It is not implementation authorization.

Cross-contract (durable materialize): `/opsx-materialize-bug-queue` owns
persistence, but its `CHAT_REQUIRED` / claimable `STATUS` **must not**
override these forbids. For `BACKLOG_ONLY`, `CLEANUP_BACKLOG`, and
`TEST_COVERAGE_BACKLOG`, materialize MUST write `CHAT_REQUIRED=false` and
`STATUS=backlog` (packet/record allowed; not `READY_TO_CLAIM`). For
`CREATE_SEPARATE_ROOT_CANDIDATE`, do not mark the finding as a child claim
chat on this case (`CHAT_REQUIRED=false` here). Only `CREATE_CHILD_CHAT`-
eligible items may become `CHAT_REQUIRED=true` + `STATUS=available`.

### BACKLOG_ONLY

Use when:

* relationship is `adjacent_out_of_scope`;
* item may be useful but does not violate the current invariant;
* no immediate child adjudication is required.

Durable handoff: materialize as backlog, not a claimable child chat.

### CLOSE_FALSE_POSITIVE

Use when:

* production classification is `false positive`;
* or relationship is `false_positive`.

Preserve the reason and evidence.

Do not create a child chat.

### CLEANUP_BACKLOG

Use when:

* production classification is `dead legacy`.

Do not treat cleanup as a production bug fix.

Durable handoff: materialize as backlog (`CHAT_REQUIRED=false`), not a
claimable child chat.

### TEST_COVERAGE_BACKLOG

Use when:

* production classification is `tests-only`;
* the item represents a potentially useful test or fixture concern but has no production path.

Durable handoff: materialize as backlog (`CHAT_REQUIRED=false`), not a
claimable child chat.

### CREATE_SEPARATE_ROOT_CANDIDATE

Use when:

* relationship is `different_invariant_candidate`.

This is not a child of the current invariant for implementation purposes.

Prepare a separate root-candidate packet.

Do not automatically launch another bug hunt.

Durable handoff: do not mark as a child claim chat on this case
(`CHAT_REQUIRED=false` here; separate-root tracking / backlog only).

### BLOCKED_INCOMPLETE_PACKET

Use when:

* routing is clear;
* but required evidence or fields for a reliable child packet are missing.

### NEEDS_SOURCE_CORRECTION

Use when:

* source fields contradict one another;
* for example:

  * `false positive` with `CHILD_CHAT_RECOMMENDED=true`;
  * `adjacent_out_of_scope` with a requested current-scope implementation fix;
  * missing root relationship;
  * duplicate finding IDs;
  * `duplicate_root` (or same-causal-path duplicate of the known root)
    present in `NEW_FINDINGS` or carrying a `CHILD-*` ID.

## Stable IDs

Preserve IDs returned by `/opsx-bug-hunt`.

Do not renumber:

```text
CHILD-001
CHILD-002
ADJ-001
FP-001
LEGACY-001
TEST-001
DUP-001
```

If the source does not provide an ID, assign one deterministically by source order and category.

Allowed prefixes:

```text
CHILD-
ADJ-
FP-
LEGACY-
TEST-
DUP-
ROOTCAND-
```

`DUP-*` are observation IDs for `duplicate_root` evidence only.
Never treat `DUP-*` as claimable children or `CREATE_CHILD_CHAT` targets.

Use three-digit numbering.

Before assigning a new ID, verify it does not collide with another source item.

## Chat title policy

For every `CREATE_CHILD_CHAT`, generate:

```text
<ROOT_CASE_ID> · <FINDING_ID> · <slug>
```

Example:

```text
BUGCASE-ABHOLD-WBSYNC-001 · CHILD-001 · stale-stats-blocks-activation
```

Slug rules:

* lowercase Latin characters;
* numbers allowed;
* hyphens instead of spaces;
* no file paths;
* no punctuation except hyphens;
* maximum 64 characters;
* preserve the meaning of the finding;
* do not include severity unless necessary to distinguish duplicate titles.

If two titles collide, append the finding ID to the slug.

## Child case packet

For every `CREATE_CHILD_CHAT`, generate exactly one packet:

```text
CHILD_CASE_PACKET

ROOT_CASE_ID:
ROOT_FINDING_ID:
ROOT_CHAT_URL:
FINDING_ID:
PARENT_FINDING_ID:
CHAT_TITLE:

STATUS:
needs_adjudication

SOURCE:
opsx-bug-hunt

SOURCE_SNAPSHOT:
PRODUCTION_CLASSIFICATION:
RELATION_TO_ROOT:

INVARIANT:
<verbatim invariant>

ORIGINAL_FINDING:
<verbatim or lossless normalized finding>

EVIDENCE:
<source evidence>

RUNTIME_PATH:
CAUSAL_BOUNDARY:
WRITE_BOUNDARY:
OWNER_MODULE:

RISK:
REGRESSION_TEST:
RECOMMENDED_ACTION:

PREREQ:
GATE: `.opsx/runs/bug-cases/<ROOT_CASE_ID>/` must exist (see Durable case-map gate).
If absent → overall Verdict blocked (`durable_case_map_missing`); do not claim.
Durable findings must exist on disk via
/opsx-materialize-bug-queue mode=hunt-result (or already materialized).
Do not adjudicate from a chat-only packet without case-map rows.

NEXT_COMMAND:
(when case map present)
/opsx-claim-next-bug case=<ROOT_CASE_ID> chat_label="<CHAT_TITLE>"
(when case map absent — preview packet only)
/opsx-materialize-bug-queue mode=hunt-result case=<ROOT_CASE_ID> source=<same hunt source>

MODE:
READ_ONLY

FORBIDDEN:
- do not edit files;
- do not use GO;
- do not create patches;
- do not commit;
- do not push;
- do not deploy;
- do not restart services;
- do not run migrations;
- do not modify or restore Git stashes;
- do not expand beyond this finding and inherited invariant;
- do not emit bare /opsx-fix-bug without case=/finding=/claim_token=;
- do not skip /opsx-claim-next-bug when the finding is chat_required and unclaimed.

REQUIRED_RETURN:
- literal verdict;
- production reachability;
- exact relationship to the root finding;
- whether the finding is independent or coupled to the root fix;
- spec impact;
- minimal fix delta;
- required regression test;
- routing recommendation;
- exact next command.
```

The inherited invariant must be copied verbatim.

The original finding must be preserved without silently strengthening or weakening it.

Do not include `GO`.

`NEXT_COMMAND` for `CREATE_CHILD_CHAT` MUST be
`/opsx-claim-next-bug case=<ROOT_CASE_ID> chat_label="<CHAT_TITLE>"`
(or the case that owns `FINDING_ID` after hunt-result) **only when** the
durable case map exists (`case_map_present: true`). When
`durable_case_map_missing`, `NEXT_COMMAND` MUST be
`/opsx-materialize-bug-queue mode=hunt-result case=<ROOT_CASE_ID> source=<same hunt source>`
instead — never a claimable claim-next-bug handoff. After a successful claim,
`/opsx-claim-next-bug` emits `/opsx-classify-bug` with `case=` / `finding=` / (then Route A uses `/opsx-fix-bug` with `case=` / `intake=` /
`finding=` / `claim_token=`. Never hand a child chat bare `/opsx-fix-bug`.

## Separate root candidate packet

For every `CREATE_SEPARATE_ROOT_CANDIDATE`, generate:

```text
ROOT_CANDIDATE_PACKET

SOURCE_ROOT_CASE_ID:
SOURCE_ROOT_FINDING_ID:
CANDIDATE_ID:
TITLE:
SOURCE_SNAPSHOT:
OBSERVATION:
EVIDENCE:
CANDIDATE_INVARIANT:
STATUS:
needs_independent_adjudication

NEXT:
Run /opsx-fix-bug WITHOUT GO as a new root candidate, with durable IDs when known
(case=<…> intake=<…>) or as a true first-run raw report that materializes intake —
never bare `/opsx-fix-bug` alone.
Do not treat this as a confirmed child of the current invariant.
```

If the source did not provide a candidate invariant, write:

```text
CANDIDATE_INVARIANT:
not_materialized
```

Do not invent one.

## Child limit

If the number of `CREATE_CHILD_CHAT` actions exceeds `max_children`:

* do not silently drop findings;
* select the highest-priority findings for chat creation;
* place the remainder in `DEFERRED_CHILD_QUEUE`.

Priority order:

1. `confirmed production bug`;
2. `reachable but low-risk`;
3. `unclear reachability`;
4. higher risk;
5. stronger evidence;
6. closer causal proximity to the protected boundary;
7. finding ID as a stable tie-breaker.

Deferred findings remain open.

They are not false positives or backlog-only.

## Fan-out manifest

Return a machine-readable manifest:

```text
FANOUT_MANIFEST:

ROOT_CASE:
  root_case_id:
  root_finding_id:
  root_chat_url:
  root_status:
  source_snapshot:

CHILD_CHATS:
  - finding_id:
    parent_finding_id:
    chat_title:
    action:
    production_classification:
    relationship_to_root:
    packet_status:
    packet:

SEPARATE_ROOT_CANDIDATES:
  - candidate_id:
    title:
    action:
    packet:

BACKLOG:
  - finding_id:
    category:
    action:
    reason:

CLOSED:
  - finding_id:
    category:
    action:
    reason:

BLOCKED:
  - finding_id:
    action:
    missing_or_conflicting_fields:

DEFERRED_CHILD_QUEUE:
  - finding_id:
    reason:
```

The manifest is the contract for the external browser or coordinator layer.

The external layer may create chats only for:

```text
action=CREATE_CHILD_CHAT
```

## Learning handoff

This command does not run `/opsx-learn-from-bug`.

### LEARNING_READY ≠ FANIN_READY (HARD)

```text
LEARNING_READY != FANIN_READY
```

Fanout `LEARNING_READY` means children have stable adjudication readiness
for a learning **registry preview** only.

It does **NOT** mean:

* all started branches are episode-terminal;
* RED/GREEN/GO linkage is complete;
* `FANIN.md` exists or `FANIN_READY`;
* class-level lesson is allowed;
* the episode is finished.

This command MUST NOT:

* assemble or write `results/FANIN.md`;
* declare episode completion;
* perform fan-in;
* treat `LEARNING_READY=true` as lesson-gate pass.

Fan-in is only via `/opsx-materialize-bug-queue mode=fanin_assemble`.

It must return a preliminary learning registry:

```text
LEARNING_REGISTRY:

ROOT:
  root_finding_id:
  root_status:

CHILDREN:
  - finding_id:
    action:
    adjudication_status:
    include_in_learning:

OBSERVATIONS:
  - finding_id:
    action:
    include_in_learning:

LEARNING_READY:
  true | false

BLOCKERS:
  - ...
```

Set `include_in_learning=true` for:

* the known root;
* confirmed children;
* reachable low-risk children;
* false positives with useful detection lessons;
* adjacent observations that clarify scope boundaries.

Set `LEARNING_READY=false` while any `CREATE_CHILD_CHAT` item remains unadjudicated.

This does not mean all bugs must already be fixed.

It means every actionable finding must first have a stable verdict and relationship to the root.

## Output format

Return exactly this structure:

```text
Verdict:
- ready / blocked

Root case:
- root case id:
- root finding id:
- root status:
- root chat URL:
- source snapshot:

Input validation:
- source complete:
- root anchored:
- duplicate IDs:
- contradictions:
- child limit:
- case_map_present:

Finding registry:

1. FINDING_ID:
   TITLE:
   PRODUCTION_CLASSIFICATION:
   RELATION_TO_ROOT:
   ACTION:
   CHAT_REQUIRED:
   REASON:

2. ...

FANOUT_MANIFEST:
...

CHILD_CASE_PACKETS:
...

ROOT_CANDIDATE_PACKETS:
...

LEARNING_REGISTRY:
...

Summary:
- total source findings:
- child chats to create:
- separate root candidates:
- backlog items:
- closed false positives:
- blocked items:
- deferred children:

Next action:
- if `case_map_present: false`: exact
  `/opsx-materialize-bug-queue mode=hunt-result case=<ROOT_CASE_ID> source=<same hunt source>`
  (do not pass claim chats to the browser/coordinator yet);
- else pass FANOUT_MANIFEST to the browser/coordinator layer;
- or exact blocker to resolve.
```

## Hard rules

* `MAX_ACTIVE_BRANCHES=3` — stricter active claimable-branch cap;
  excess deferred, not dropped.
* `LEARNING_READY != FANIN_READY` — never claim fan-in / episode done.
* Do not write FANIN.md or run fan-in from this command.
* No root case ID → no fan-out.
* No structured root-aware bug-hunt result → no fan-out.
* Do not infer the root from the invariant alone.
* Do not inspect repository code (exact-path check of
  `.opsx/runs/bug-cases/<ROOT_CASE_ID>/` is allowed process I/O only).
* No `Verdict: ready` and no claimable `/opsx-claim-next-bug` handoff when
  `.opsx/runs/bug-cases/<ROOT_CASE_ID>/` is absent — block with
  `durable_case_map_missing` and route Next action / packet `NEXT_COMMAND` to
  `/opsx-materialize-bug-queue mode=hunt-result`. A PREREQ note alone is not enough.
* Do not repeat production reachability analysis.
* Do not alter source classifications.
* Do not alter source relationships to root.
* Do not emit the known root as a child.
* Do not emit a `duplicate_root` suspect (same causal path as the known root)
  as a child or `CREATE_CHILD_CHAT` target; block with
  `duplicate_root_emitted_as_new_finding` if present in `NEW_FINDINGS`.
* Do not create a child chat for false positives.
* Do not create a child chat for adjacent out-of-scope observations.
* Do not create a child chat for dead legacy or tests-only findings.
* Durable materialize must not override the three forbids above: those
  findings get `CHAT_REQUIRED=false` + `STATUS=backlog`, never claimable
  child chats (`READY_TO_CLAIM`).
* Do not merge findings merely because one patch may fix both.
* Do not split findings without source evidence.
* Do not include GO in generated packets.
* Do not edit files.
* Do not stage, commit, push, deploy, restart, or migrate.
* Do not create Git branches or worktrees.
* Do not restore, apply, pop, drop, or modify Git stashes.
* Do not run learning.
* Do not promote a lesson into policy.
* Physical chat creation belongs to an external browser/coordinator layer.


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

