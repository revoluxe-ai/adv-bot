---

description: "Root-aware invariant-focused bug hunt beyond the current diff, with production reachability proof, known-root anchoring, and cheap-first model policy."
argument-hint: "base=<branch> head=<branch> invariant=<contract> root_finding=<packet-or-reference> [scope=<paths>] [deep] [GO]"
--------------------------------------------------------------------------------------------------------------------------------

# /opsx-bug-hunt

You are performing a root-aware, read-only, invariant-focused bug hunt.

This command is NOT a normal diff review.

This command is NOT a general repository audit.

This command is NOT the primary pre-PR / Bugbot-analogue project hunter
(`/opsx-project-bug-hunt` owns that). Use this command for **root-aware**,
single-invariant sibling discovery after a known root packet.

This command is NOT an implementation command.

This command MUST distinguish:

1. the already known and confirmed root finding;
2. new invariant bypasses discovered by the hunt;
3. adjacent observations;
4. false positives;
5. findings whose production reachability is still unclear.

The known root finding MUST NOT be returned as a new child finding.

This command is not allowed to fix code unless the user input contains the exact standalone token:

```text
GO
```

If `GO` is absent:

* do not modify files;
* do not stage files;
* do not commit;
* do not push;
* do not run migrations;
* do not deploy;
* do not restart services;
* do not create branches or worktrees;
* do not restore, apply, pop, drop, or modify Git stashes;
* output only structured hunt results and a fix plan.

Even with `GO`, only apply minimal fixes for findings classified as `confirmed production bug`.

Never fix `dead legacy`, `tests-only`, `unreachable`, `unclear reachability`, `adjacent`, or `false positive` findings by adding defensive code merely to satisfy static review.

## User input

```text
$ARGUMENTS
```

## Purpose

Find invariant bypasses that may exist outside the current diff while preserving the identity of the already known root bug.

Use this command when:

* a feature or bugfix introduced, clarified, or relied on an invariant;
* one root bug has already been confirmed;
* the root bug has an established causal boundary and production reachability chain;
* old or adjacent code paths may violate the same invariant through a different path;
* the user needs to distinguish the known root from genuinely new findings.

Do **not** use this command as the first hunter before PR / Bugbot. For
primary project-tuned discovery on `base..head` without a known root, use
`/opsx-project-bug-hunt` first; return here only for same-invariant fan-out
after a confirmed root.

Examples:

* A/B Hold structural freeze must block all structural WB writes for `PENDING_SETUP` / `ACTIVE`.
* After durable synchronization is marked complete, later ticks must finish activation without re-entering the external write path.
* Free mode must not call paid automation.
* Campaign state transitions must not skip setup gates.
* Telegram UI changes must preserve parse mode, message length limits, buttons, and callback contracts.
* DB writes must preserve Redis/PostgreSQL/ClickHouse consistency.

## Required inputs

Extract from `$ARGUMENTS`:

* `base`: branch or commit used as the comparison base.
* `head`: branch or commit whose implementation is being inspected.
* `invariant`: exact behavioral contract to hunt for.
* `root_finding`: structured packet or explicit reference describing the already known root bug.
* `scope`: optional paths or modules to scan.
* `deep`: optional flag allowing deeper reasoning after the cheap scan.
* `GO`: optional permission for minimal edits.

If `base`, `head`, `invariant`, or `root_finding` is missing, stop and report the missing value.

Do not infer the root finding only from the invariant.

Do not infer the root finding only from chat history.

Do not run a wide scan without both:

* a named invariant;
* an explicit root finding anchor.

## Root finding packet

The `root_finding` input MUST provide, directly or by an unambiguous reference, the following fields:

```text
ROOT_FINDING_ID:
TITLE:
LITERAL_CLAIM:
CONFIRMED_VERDICT:
CLASSIFICATION:
RUNTIME_PATH:
CAUSAL_BOUNDARY:
WRITE_BOUNDARY:
INVARIANT:
PRE_FIX_REF:
```

Optional fields:

```text
OWNER_MODULE:
REPORTED_SEVERITY:
ACCEPTED_SEVERITY:
REGRESSION_SCENARIO:
KNOWN_FIX_BOUNDARY:
ROOT_FIX_STATUS:
```

The packet may be supplied inline or by reference to a previously materialized artifact.

## Source resolution (mandatory)

Follow `.cursor/commands/opsx-source-resolution.md`.
Also follow `.cursor/commands/opsx-execution-preflight.md`.

If `root_finding` is a path, `case+finding`, or packet reference:

1. read that exact source first;
2. do not rediscover the root packet via repo-wide search;
3. use packet-provided symbols/paths to bound Pass 1 searches;
4. respect optional `scope=`;
5. do **not** require `git status` before packet resolution; run git only when `base`/`head`/dirty-tree facts are REQUIRED_FOR the hunt decision;
6. Pass 1 search budget: ≤ 3 targeted `rg` operations per unresolved symbol/boundary class before stopping or asking for `EVIDENCE_GAP` / `deep`;
7. include `SOURCE_RESOLUTION` and `EXECUTION_PREFLIGHT` in the final hunt output.

A chat-only recollection is not a reliable root packet.

If the packet is incomplete in a way that prevents deterministic root matching, stop with:

```text
Verdict:
- blocked

Blocker:
- incomplete_root_finding_packet
```

List the missing fields.

## LOC_LINK contract (mandatory)

Authority: `.cursor/rules/opsx-clickable-loc-link-contract.mdc`.

For every report item that references a concrete code location, include:

`LOC_LINK: <repo-relative-path>:<line>`

Rules:

* Use plain `path:line` (Cursor-clickable), not `file://` as the only format.
* If exact boundary line is unknown, fallback to symbol definition line
  (`def` / `class`) and note fallback in that item.
* `File:`/`Function:`/`Evidence:` without `LOC_LINK` is insufficient for
  claimable/new findings.

## Root anchoring rules

Treat the root finding as an existing case, not as a candidate new finding.

For every suspected invariant violation, compare it with the root packet using:

1. forbidden observable effect;
2. runtime path;
3. causal gate or branch;
4. owner module;
5. mutation/write/read boundary;
6. triggering production state;
7. regression scenario;
8. expected fix boundary.

Classify a suspect as `duplicate_root` only when the evidence shows the same underlying violation, not merely the same file or invariant.

A finding is usually `duplicate_root` when it has:

* the same forbidden effect;
* the same causal path or gate;
* the same relevant production state;
* the same write boundary;
* substantially the same regression scenario.

When a suspect is `duplicate_root`:

* omit it from `NEW_FINDINGS` entirely;
* do **not** assign a `CHILD-*` ID;
* fold evidence into `KNOWN_ROOT_RESULT` (and optionally list under
  `DUPLICATE_ROOT_OBSERVATIONS` with `DUP-NNN` observation IDs);
* treat it as part of the known root case — never as a claimable child.

A finding is NOT a root duplicate merely because:

* it affects the same file;
* it affects the same function;
* it violates the same invariant;
* it may be fixed by the same patch;
* it occurs during the same scheduler tick.

A different gate, early return, adapter, callback, scheduler path, or state transition is a distinct candidate finding even when it shares the same invariant and owner module.


## Episode hunt bounds (orchestration MVP)

Schema/policy: `.cursor/pipeline/ORCHESTRATION_MVP.md` §3;
`.cursor/pipeline/contracts/bug-episode/BRANCH_REGISTRY.md`.

```text
MAX_HUNT_PASSES=3
MAX_DEPTH_FROM_ROOT=3
MAX_ACTIVE_BRANCHES=3
PASS_3=MANDATORY_STOP
NEW_INVARIANT_FROM_BRANCH=FORBIDDEN
IMPLEMENTATION_STATUS: LIVE_ACTIVATED
VALIDATION_STATUS: INDEPENDENT_TEST_PASS
RUNTIME_ENFORCEMENT: ACTIVE
LIVE_COMMAND_BEHAVIOR_CHANGED: YES
GO_ACTIVATE: ISSUED
```

| Limit | Meaning |
|-------|---------|
| `MAX_HUNT_PASSES` | At most three hunt expansion passes per episode |
| `PASS_3=MANDATORY_STOP` | After the third pass, **no new working branches** of the current episode are created |
| `MAX_DEPTH_FROM_ROOT` | Child/finding causal depth from root ≤ 3 |
| `MAX_ACTIVE_BRANCHES` | Concurrent claimable/working branches ≤ 3 (enforced with fanout) |

After pass 3, residual findings that cannot continue as working branches:

```text
DEFERRED | BLOCKED | TIMEOUT
```

`different_invariant_candidate` / another invariant from a child branch:

```text
CREATE_SEPARATE_ROOT_CANDIDATE
```

Do **not** retarget the current episode invariant mid-flight
(`NEW_INVARIANT_FROM_BRANCH=FORBIDDEN`). The separate-root candidate is
**not** started inside the current episode.

Echo pass/depth counters into durable BRANCH_REGISTRY via materialize when
materializing hunt results.

## Cost policy

Use a cheap-first workflow.

### Pass 1 — root anchor and cheap/static scan

First materialize the known root identity.

Then use fast grep and static inspection.

Do not do broad expensive reasoning yet.

Find:

* root function and boundary;
* definitions;
* all relevant call sites;
* mutation/write/read boundaries;
* scheduler and runtime entrypoints;
* adjacent functions with similar responsibility;
* alternative gates and early returns;
* tests that imply intended coverage;
* accepted or proposed OpenSpec requirements and decisions.

Recommended commands (purpose-driven):

```bash
# REQUIRED_FOR base/head identity only when those args are used
git rev-parse <base>
git rev-parse <head>
git diff --name-only <base>...<head>

# OPTIONAL: branch/status — SKIP_IF not required for hunt decision; TIME_BUDGET 5s/10s
# git branch --show-current
# git status --short

# after root packet resolved; prefer packet-scoped roots / scope=
rg -n "<invariant keywords>" <scoped-roots>
rg -n "<root function/class/callback names>" <scoped-roots>
rg -n "<write boundary names>" <scoped-roots>
```

Do not start with repo-wide rediscovery of the root finding id/path or with unconditional `git status`.
Do not assume that a clean working tree means the inspected snapshot is the intended pre-fix snapshot.

Confirm `PRE_FIX_REF` from the root packet where relevant.

### Pass 2 — focused reasoning

Only after Pass 1 finds concrete suspects, inspect the strongest 3–7 candidates.

For each candidate:

1. compare it with the root finding;
2. prove or reject production reachability;
3. determine whether it is the same causal path or a distinct bypass;
4. classify it;
5. determine whether separate adjudication is required.

### Pass 3 — deep mode

Episode orchestration: pass index 3 is also `PASS_3=MANDATORY_STOP` —
after this expansion pass, do not create new working branches for the
current episode (residuals → `DEFERRED`/`BLOCKED`/`TIMEOUT`).

Only if `deep` is present or the user explicitly asks.

Deep mode may inspect broader adjacent modules, but still only under the same invariant.

Do not turn deep mode into a general repository review.

## Scope rules

Wide scan is allowed only after both the invariant and root finding are named.

Allowed scan expansion:

* same invariant;
* same write, mutation, transition, or read boundary type;
* same manager or service family;
* same scheduler or runtime path;
* alternative gates before the known boundary;
* sibling adapters or callbacks;
* same DB/Redis/ClickHouse consistency boundary;
* lifecycle states that can reach the same terminal or write boundary.

Forbidden scan expansion:

* unrelated business logic;
* unrelated refactors;
* style cleanup;
* speculative architecture rewrites;
* dead code fixes without production reachability;
* files outside declared scope unless needed to prove a call chain;
* unrelated UI polish;
* unrelated lifecycle redesign;
* new invariants invented during the hunt.

If a suspect appears to rely on a different invariant, report it as `different_invariant_candidate`. Do not silently expand the current hunt.

## Required analysis order

For the known root:

1. Restate the root finding ID and title.
2. Confirm the supplied invariant matches the root packet.
3. Locate the known causal and write boundaries.
4. Determine whether the inspected snapshot:

   * reconfirms the root;
   * no longer contains the root;
   * contains materially changed evidence.
5. Return it only under `KNOWN_ROOT_RESULT`.

For every additional suspect:

1. State the invariant.
2. Identify the mutation/write/read/transition boundary.
3. Locate the exact file and function.
4. Find all relevant call sites.
5. Prove production reachability:

   * scheduler or worker path;
   * bot callback or manual path;
   * API path;
   * CLI or admin path;
   * tests-only path;
   * no caller or dead legacy.
6. Compare it with the root packet.
7. Assign one production classification.
8. Assign one relationship to root.
9. Recommend action.
10. State whether separate adjudication is required.

## Production classification

Use exactly one production classification per finding:

```text
confirmed production bug
reachable but low-risk
unclear reachability
tests-only
dead legacy
false positive
```

### Classification rules

`confirmed production bug` requires:

* invariant mismatch;
* reachable runtime path;
* realistic production state;
* mutation, write, transition, or read side effect that violates the invariant.

`reachable but low-risk` means:

* runtime path exists;
* invariant mismatch is plausible;
* production impact is limited, rare, or blocked by another proven guard.

`unclear reachability` means:

* static search found partial evidence;
* the call chain or production state is incomplete;
* do not fix yet;
* require targeted adjudication or runtime confirmation.

`tests-only` means:

* code path is used only by tests or fixtures;
* no production entrypoint was found.

`dead legacy` means:

* function or code exists;
* no production caller was found;
* no scheduler, bot, API, CLI, admin, or manual path was found.

For `dead legacy`, recommend a cleanup task, not a defensive patch.

`false positive` means:

* the invariant is not violated;
* or another proven guard already prevents the issue;
* or the finding depends on an invalid assumption;
* or an accepted decision explicitly allows this exact path and boundary.

For an allowed exception:

* cite the exact source path and relevant section or line;
* apply the exception only to that boundary;
* do not weaken detection for new mutations on the same path.

No authoritative citation means the suspect remains a finding or `unclear reachability`.

## Relationship to root

Use exactly one relationship value for every item in `NEW_FINDINGS`:

```text
same_invariant_different_path
different_invariant_candidate
adjacent_out_of_scope
false_positive
```

`duplicate_root` is a classification used during root comparison only.
It is **not** a valid `NEW_FINDINGS` relationship.

The known root itself is not placed in `NEW_FINDINGS`.
`duplicate_root` suspects are also not placed in `NEW_FINDINGS`.

Only items with a listed relationship above may appear in `NEW_FINDINGS`.
Only `same_invariant_different_path` (and other non-duplicate relationships
that remain after classification) may receive `CHILD-*` IDs when otherwise
eligible — never a same-causal-path duplicate of the known root.

### Relationship rules

`same_invariant_different_path` means:

* the same invariant is violated;
* but through a different gate, branch, callback, adapter, scheduler path, state transition, early return, or causal mechanism.

`different_invariant_candidate` means:

* the suspect may be a valid bug;
* but it is not governed by the supplied invariant;
* do not expand the current hunt;
* recommend a separate root case after adjudication.

`adjacent_out_of_scope` means:

* the observation is reachable or relevant;
* but it does not violate the supplied invariant;
* it may be backlog-worthy;
* it must not enter the current implementation queue automatically.

`false_positive` means:

* the observation was inspected and disproved;
* no child case is required.

## Known root result

The command MUST return exactly one `KNOWN_ROOT_RESULT`.

Allowed root statuses:

```text
reconfirmed
not_reproduced_on_inspected_snapshot
evidence_changed
blocked_by_snapshot_uncertainty
```

Definitions:

`reconfirmed`:

* inspected evidence still demonstrates the known root violation.

`not_reproduced_on_inspected_snapshot`:

* inspected snapshot no longer contains the root violation;
* this may mean the hunt is running against a post-fix snapshot.

`evidence_changed`:

* the root still exists or remains relevant, but its path, state, or boundary differs materially from the packet.

`blocked_by_snapshot_uncertainty`:

* the command cannot determine whether it is inspecting the correct pre-fix state.

The known root result MUST include:

```text
ROOT_FINDING_ID:
STATUS:
SNAPSHOT:
MATCHED_EFFECT:
MATCHED_CAUSAL_PATH:
MATCHED_WRITE_BOUNDARY:
EVIDENCE:
ACTION:
```

The root result is evidence for the root case. It is not a new child finding.

## Child finding IDs

Assign deterministic IDs only to new findings:

```text
CHILD-001
CHILD-002
CHILD-003
```

Order IDs by:

1. production severity;
2. confidence;
3. causal proximity to the protected boundary;
4. source path as a stable tie-breaker.

Do not assign child IDs to:

* the known root;
* `duplicate_root` suspects (same causal path as the known root);
* false positives;
* dead legacy;
* tests-only findings;
* adjacent out-of-scope observations.

Use separate observation IDs where useful:

```text
ADJ-001
FP-001
LEGACY-001
TEST-001
DUP-001
```

`DUP-*` IDs are for `DUPLICATE_ROOT_OBSERVATIONS` / `KNOWN_ROOT_RESULT`
evidence only. They must never appear in `NEW_FINDINGS` as claimable children.

## Child adjudication policy

Set `ADJUDICATION_REQUIRED: true` when:

* production reachability remains unclear;
* relationship to root is uncertain;
* a different invariant may govern the finding;
* fix independence is unclear;
* evidence conflicts with OpenSpec;
* the finding is confirmed but should receive a separate case before implementation.

Set `CHILD_CHAT_RECOMMENDED: true` only when:

* the item is not the known root;
* the item is not a `duplicate_root` suspect;
* it is a confirmed or plausibly reachable new finding;
* separate adjudication or ownership is useful;
* it is not merely adjacent, dead, tests-only, or false positive.

Do not create or open the chat in this command.

Only return the packet needed by a later fan-out step.

## Fix policy

If `GO` is absent:

* output only the structured hunt result and plan.

If `GO` is present:

* fix only `confirmed production bug` findings;
* do not fix the known root unless the user explicitly includes it in the requested apply scope;
* keep the patch minimal;
* add or update regression tests;
* do not touch unrelated files;
* do not clean dead legacy unless explicitly requested;
* do not commit.

Before editing, print:

```text
APPLYING ONLY CONFIRMED PRODUCTION BUG FIXES
```

`GO` does not authorize:

* lifecycle redesign;
* automatic child-case creation;
* automatic learning;
* Git branch creation;
* stash restoration;
* commit, push, deploy, restart, or migration.

## Regression test rules

Every confirmed production bug must have a regression test that fails before the fix.

Prefer tests that exercise a real runtime entrypoint or meaningful orchestration seam.

Acceptable tests:

* entrypoint excludes forbidden candidates;
* manager wires invariant filtering before the write boundary;
* callback cannot trigger a forbidden transition;
* worker tick skips a forbidden mutation;
* completed state reaches activation despite an unrelated mutation freeze;
* API path rejects an invalid state;
* paired tests distinguish the allowed retry state from the forbidden completed state.

Weak tests:

* source-code string checks only;
* count-only tests;
* direct calls to dead legacy helpers;
* tests that only assert an implementation detail;
* tests that prove a sibling path but not the reported path;
* `assert_not_called` without constructing the actual protected production state.

Source-string tests are allowed only as a temporary wiring guard when no better seam exists.

## Output format

Return exactly this structure:

```text
Verdict:
- plan_only / applied / blocked

Base/head:
- base:
- head:
- current branch:
- inspected snapshot:
- dirty files:

Invariant:
- ...

Root finding packet:
- root finding id:
- title:
- confirmed verdict:
- classification:
- causal boundary:
- write boundary:
- pre-fix ref:

Scan scope:
- inspected:
- expanded:
- skipped:

KNOWN_ROOT_RESULT:
- ROOT_FINDING_ID:
- STATUS:
- SNAPSHOT:
- LOC_LINK:
- MATCHED_EFFECT:
- MATCHED_CAUSAL_PATH:
- MATCHED_WRITE_BOUNDARY:
- EVIDENCE:
- ACTION:

DUPLICATE_ROOT_OBSERVATIONS:
- (optional; DUP-* only; never CHILD-*; never claimable)
- DUP-001: ... (LOC_LINK: <path>:<line>)

NEW_FINDINGS:

1. [classification] [relationship_to_root] short title
   FINDING_ID:
   File:
   LOC_LINK:
   Function:
   Boundary:
   Evidence:
   Reachability:
   Production state:
   Difference from root:
   Risk:
   Recommended action:
   Regression test:
   ADJUDICATION_REQUIRED:
   CHILD_CHAT_RECOMMENDED:

2. ...

Confirmed new production bugs:
- ...

Findings requiring adjudication:
- ...

Different-invariant candidates:
- ...

Adjacent / dead legacy / tests-only / false positives:
- ...

Minimal fix plan:
1.
2.
3.

Tests:
- regression test paths:
- verification commands:

FANOUT_INPUT:
- ROOT_FINDING_ID:
- INVARIANT:
- NEW_FINDING_IDS:
- CHILD_CHAT_CANDIDATES:
- ITEMS_NOT_REQUIRING_CHAT:

LEARNING_INPUT_STATUS:
- ready / not_ready
- blockers:
- evidence available:

Risks:
- ...

Need from user:
- none / exact question
```

## Fan-out handoff requirements

For every finding with `CHILD_CHAT_RECOMMENDED: true`, append a structured handoff.
Align with `/opsx-fanout-bug-hunt` and `/opsx-materialize-bug-queue`: claim-first
after durable materialization — never bare `/opsx-fix-bug`.

```text
CHILD_CASE_PACKET:
- CASE_ID: / ROOT_CASE_ID:
- ROOT_FINDING_ID:
- FINDING_ID:
- PARENT_FINDING_ID:
- LOC_LINK:
- TITLE:
- RELATION_TO_ROOT:
- PRODUCTION_CLASSIFICATION:
- INVARIANT:
- ORIGINAL_FINDING:
- EVIDENCE:
- RUNTIME_PATH:
- CAUSAL_BOUNDARY:
- WRITE_BOUNDARY:
- SOURCE_SNAPSHOT:
- PREREQ:
- ADJUDICATION_COMMAND:
- FORBIDDEN_ACTIONS:
```

`PREREQ`: `.tmp/opsx-bug-cases/<CASE_ID>/` must exist (durable case map via
`/opsx-materialize-bug-queue mode=hunt-result`, or already materialized). Do not
adjudicate from a chat-only packet without case-map rows.

`ADJUDICATION_COMMAND` / next command:

* when case map present:

```text
/opsx-claim-next-bug case=<CASE_ID> chat_label="<label>"
```

* when case map absent (preview only — not claimable):

```text
/opsx-materialize-bug-queue mode=hunt-result case=<CASE_ID> source=<same hunt source>
```

Never emit bare `/opsx-fix-bug` (without `case=` / `finding=` / `claim_token=`).
After a successful claim, `/opsx-claim-next-bug` supplies `/opsx-classify-bug` first; after classify Route A, `/opsx-fix-bug` with
durable ARGS including `claim_token=` — the hunt handoff must not skip that step.

Do not include `GO` in a generated child handoff.

`FORBIDDEN_ACTIONS` must include at least:

* do not use `GO`;
* do not emit bare `/opsx-fix-bug` without `case=` / `finding=` / `claim_token=`;
* do not skip `/opsx-claim-next-bug` when the finding is chat-required and unclaimed;
* do not adjudicate before durable materialization when the case map is absent.

## Learning readiness

Do not run learning in this command.

Set `LEARNING_INPUT_STATUS: ready` only when:

* the known root is anchored;
* every new finding has a production classification;
* every new finding has a relationship to root;
* no finding remains ambiguously mixed with the root;
* unresolved items are explicitly marked for adjudication.

`ready` means the hunt result is structured enough to feed a later learning or fan-out step.

It does not mean:

* all child bugs are fixed;
* policy promotion is approved;
* the root case may be closed.

## Hard rules

* `MAX_HUNT_PASSES=3` / `MAX_DEPTH_FROM_ROOT=3` / `PASS_3=MANDATORY_STOP` —
  no new working branches after pass 3; residuals terminal as
  `DEFERRED`/`BLOCKED`/`TIMEOUT`.
* `NEW_INVARIANT_FROM_BRANCH=FORBIDDEN` — different invariant ⇒
  `CREATE_SEPARATE_ROOT_CANDIDATE` only (out of episode).
* No invariant → no wide scan.
* No root finding packet → no root-aware hunt.
* No reachability → no production bug.
* The known root must never be emitted as a new child finding.
* A `duplicate_root` suspect (same causal path as the known root) must never
  enter `NEW_FINDINGS`, receive a `CHILD-*` ID, or become a claimable child.
* Same file does not mean same bug.
* Same invariant does not mean duplicate root.
* Same proposed patch does not mean duplicate root.
* A different causal gate or early return is a distinct candidate finding.
* No production bug → no code fix.
* Dead legacy is cleanup, not hotfix.
* Adjacent observations do not enter the implementation queue automatically.
* Do not patch unreachable code to silence Bugbot.
* Do not use expensive deep reasoning until the cheap scan finds concrete suspects.
* Do not mix diff review and invariant bug hunt.
* Do not create branches, worktrees, child chats, or learning records.
* Do not restore or modify Git stashes.
* Do not commit, push, deploy, restart, migrate, or touch secrets.
* Treat an empty or degenerate captured collection that still reaches a success, terminal, transition, or write boundary as a candidate finding rather than a safe no-op.
* Require a behavioral regression test on every sibling path that can independently violate the same invariant.
* Do not emit claimable finding packets with code location but missing `LOC_LINK`.


## Route-trace event requirements (SCHEMA_VERSION 2)

Authority: `.cursor/pipeline/contracts/bug-episode/ROUTE_TRACE.md`.

On every significant hop that touches a durable case map, append **one**
JSONL event to:

```text
.tmp/opsx-bug-cases/<CASE_ID>/results/ROUTE-TRACE.jsonl
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

