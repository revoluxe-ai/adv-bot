# /opsx-admin-command-design-command

## Purpose

Design a new OpenSpec/OPSX Cursor command only when a real process gap has been demonstrated.

The user may describe the problem in ordinary language. The command must translate that description into an evidence-based process analysis.

This command must not treat “I want a new command” as proof that a new command is needed.

A new command is acceptable only when it:

- removes a confirmed process gap;
- reduces uncertainty for the human operator;
- is consistent with existing commands;
- fits the current OpenSpec/OPSX lifecycle;
- does not duplicate authority;
- does not introduce an undocumented bypass;
- has compatible producer/consumer contracts;
- can be safely implemented as one coherent change packet.

## When not to use (front-door)

If the human only needs to discuss how existing commands relate, triage odd
admin/pipeline behavior, or discover which process command to run next —
route to `/opsx-admin-command-consult` first. Use this command when the
question is specifically “do we need a new/changed command?” (need analysis
through design proposal), including after a `DESIGN_BRIEF_READY` packet.

---

# Human input contract

The user may provide only a short description such as:

```text
I have this problem:
after verify I do not understand what to do next.

I think I need a new command.
```

**Also accepted** (preferred when coming from process-contract learning):

```text
STATUS: DESIGN_BRIEF_READY
SOURCE: opsx-admin-command-promote-process-lesson
...
```

Treat `DESIGN_BRIEF_READY` as structured problem input for Phase 1 need
analysis. It does **not** skip IMPROVE_EXISTING_COMMAND vs NEW_COMMAND_REQUIRED
adjudication. Process-only briefs stay on process surfaces (commands / rules /
skills / static-check contracts) — never product `/opsx-learn-from-bug` scope.

Do not require the user to know:

- internal command names;
- lifecycle state identifiers;
- authority sources;
- producer/consumer terminology;
- exact pipeline placement.

The command must perform that analysis itself.

Ask a question only when a missing fact materially prevents a safe decision.

---

# Operating phases

## Phase 1 — Need analysis

Always start here.

Mode:

```text
READ_ONLY
```

Determine:

1. What human problem is being reported.
2. What process state or transition is involved.
3. Which existing commands already participate.
4. Whether the problem is caused by:
   - missing command responsibility;
   - weak output UX;
   - ambiguous next action;
   - missing handoff;
   - conflicting contracts;
   - duplicated ownership;
   - missing process rule;
   - an actual missing command.
5. Whether the safest solution is:
   - no change;
   - improve an existing command;
   - update a shared process rule or contract;
   - create a new command.

Do not design a new command before this verdict.

---

# Need-analysis verdicts

Return exactly one:

```text
NO_CHANGE_REQUIRED
IMPROVE_EXISTING_COMMAND
PROCESS_CONTRACT_UPDATE_REQUIRED
NEW_COMMAND_REQUIRED
BLOCKED_NEEDS_EVIDENCE
```

A new command must not be proposed when an existing command can solve the problem without creating an incoherent responsibility boundary.

---

# Mandatory evidence review

Use the minimum sufficient evidence.

Follow `.cursor/commands/opsx-execution-preflight.md` **Read / tool I/O budgets**
and `.cursor/commands/opsx-source-resolution.md`.

Review, when relevant:

- exact related command paths (not the whole `.cursor/commands/**` dump);
- the current lifecycle/process model;
- command outputs and handoffs;
- authority ownership;
- approval semantics;
- task packet contract;
- freshness rules;
- not-migrate constraints.

I/O rules for Phase 1–2:

- Grep-first across `.cursor/commands/opsx-*.md` for ownership / handoff tokens;
- parallel Read max **2**;
- large files: section Read ≤ 120 lines or Grep ± context;
- do not preload `opsx-admin-command-analyze-pipeline.md`, `opsx-learn-from-bug.md`, or
  other large siblings unless they are related-command hits;
- Phase 1 evidence budget: ≤ **5** substantive section-Reads unless
  `EVIDENCE_GAP` is recorded.

Do not infer current repo behavior from old snapshots when the process may have changed.

When fresh evidence is missing, return a narrow read-only extraction request.

Boundary for extraction:

```text
Read-only.
Do not edit files.
Do not create patches.
Do not solve live tasks.
Do not produce an implementation plan.
Return structured extraction only.
Prefer Grep + bounded section Read; no parallel full-file dumps.
```

---

# Phase 2 — Ecosystem and pipeline compatibility

This phase is mandatory before proposing either:

- a new command;
- an extension to an existing command.

The proposal must prove that it is compatible with the current command ecosystem.

## 2.1 Related-command map

Identify:

```text
RELATED_COMMAND:

CURRENT_RESPONSIBILITY:

CURRENT_INPUT:

CURRENT_OUTPUT:

CURRENT_OWNER:

OVERLAP_WITH_PROPOSAL:

COMPATIBILITY_RISK:
```

Include all directly affected upstream, downstream, evaluator, verifier, archive, recovery, or routing commands.

Do not perform an unbounded repository walk.

Use context-first lookup and bounded gap-filling under the Phase 1–2 Read I/O
budget. Prefer Grep hits → sequential section Read of directly related commands
only.

---

## 2.2 Pipeline placement

Show the relevant workflow before and after the proposal.

```text
PIPELINE_BEFORE:
...

PIPELINE_AFTER:
...
```

The proposed command must have a clear lifecycle position.

Specify:

```text
ENTRY_STATE:

PREVIOUS_ALLOWED_STEP:

COMMAND_ACTION:

EXIT_STATE:

NEXT_ALLOWED_STEP:

FAILURE_OR_RECOVERY_STEP:
```

A command with no explicit pipeline position is not ready for implementation.

---

## 2.3 Producer/consumer compatibility

Check all relevant contracts:

```text
UPSTREAM_PRODUCER:

PRODUCED_ARTIFACT_OR_TOKEN:

PROPOSED_COMMAND_CONSUMES:

PROPOSED_COMMAND_PRODUCES:

DOWNSTREAM_CONSUMER:

DOWNSTREAM_EXPECTATION:
```

Detect:

- producer without consumer;
- consumer without producer;
- incompatible field names;
- incompatible status values;
- incompatible disposition values;
- artifact path drift;
- different meanings under the same token;
- required output that is never persisted;
- persisted output that no command consumes;
- advertised MODE / durable handoff consumer in description, intro, or
  guardrails without early Mode detection + executable Steps before the
  default path → class `ADVERTISED_MODE_WITHOUT_EXECUTABLE_BRANCH`
  (exemplar: `/opsx-new` `REPAIR_EXISTING_OWNER_CONTRACT` gap).

---

## 2.4 Authority and ownership compatibility

Verify:

- exactly one owner for each decision;
- no second authoritative source;
- no command silently re-decides another command’s verdict;
- no bypass around verification, approval, arbitration, sync, or archive gates;
- no hidden promotion of draft evidence into policy;
- no role-boundary violation.

Return:

```text
AUTHORITY_CONFLICTS:
NONE | <details>

OWNERSHIP_CONFLICTS:
NONE | <details>

NEW_BYPASS_PATHS:
NONE | <details>
```

Any unresolved authority conflict blocks implementation.

---

## 2.5 Human workflow compatibility

Evaluate the proposal as part of the full pipeline, not as an isolated command.

A person must be able to understand:

- when to run it;
- why to run it;
- what it reads;
- what it may change;
- what result appears;
- what status means success;
- what happens next;
- what to do when blocked;
- which decision still belongs to the owner.

The command must not force the user to remember hidden ordering rules.

The output must say:

```text
WHAT_HAPPENED:

WHY:

CURRENT_STATE:

OWNER_DECISION_REQUIRED:

NEXT_ACTION:

DO_NOT_DO_YET:
```

---

# Integration verdict

Before command design, return exactly one:

```text
COMPATIBLE
COMPATIBLE_WITH_REQUIRED_COMPANION_UPDATES
CONFLICTS_FOUND
BLOCKED_NEEDS_EVIDENCE
```

Rules:

- `COMPATIBLE` — the proposal fits without changing neighboring contracts.
- `COMPATIBLE_WITH_REQUIRED_COMPANION_UPDATES` — the command is valid only as one coherent packet with specified changes to existing commands or shared contracts.
- `CONFLICTS_FOUND` — implementation is prohibited until the conflict is resolved.
- `BLOCKED_NEEDS_EVIDENCE` — fresh repo evidence is insufficient.

Do not implement only the new file when companion updates are required.

## Independent verifier / gate companion wire-up (mandatory)

When the proposed command is an **independent READ_ONLY verifier or
lifecycle gate** (exemplar: `/opsx-planning-review` +
`.cursor/pipeline/contracts/PLANNING_REVIEW.md`):

1. State **soft vs hard gate** explicitly (v1 soft recommend vs hard block).
2. `REQUIRED_COMPANION_UPDATES` / `EXISTING_FILES_TO_UPDATE` MUST list at least:
   - (a) handoff consumer on the repair writer (e.g. `/opsx-update`
     `MODE: REPAIR_*` + handoff token) — **executable** early Mode
     detection + Steps, not description/guardrail-only; when the writer is
     dual-mode, skill/prompt mirrors must advertise the same Mode branch;
   - (b) soft `NEXT_ACTION` on producers that previously jumped to apply
     (e.g. `/opsx-continue` / `/opsx-ff` after tasks complete);
   - (c) `GRAPH` state and/or transition edge for the hop;
   - (d) soft preflight note on `/opsx-apply` when applicable.
3. Do **not** claim `COMPATIBLE` when those companions are missing for this
   command class — use `COMPATIBLE_WITH_REQUIRED_COMPANION_UPDATES` and
   disclose the full checklist before GO. Apply companions only when the
   approved packet lists them (same coherent change); never leave wire-up
   undisclosed.

---

# Phase 3 — Design proposal

Only after a positive need verdict and a non-blocking integration verdict.

Do not edit files in this phase.

Return:

```text
COMMAND_DESIGN_PROPOSAL:

PROPOSED_NAME:

PROBLEM_SOLVED:

WHY_A_NEW_COMMAND_IS_NEEDED:

WHY_EXISTING_COMMANDS_ARE_NOT_ENOUGH:

PURPOSE:

WHEN_TO_USE:

WHEN_NOT_TO_USE:

PIPELINE_POSITION:

ENTRY_STATE:

EXIT_STATE:

UPSTREAM_COMMANDS:

DOWNSTREAM_COMMANDS:

INPUTS:

OUTPUTS:

ARTIFACTS_READ:

ARTIFACTS_WRITTEN:

STATUS_AND_DISPOSITION_TOKENS:

DECISION_OWNER:

READ_BOUNDARY:

WRITE_BOUNDARY:

GO_GATE:

FAILURE_BEHAVIOR:

RECOVERY_PATH:

HANDOFF_CONTRACT:

RETURN_CONTRACT:

HUMAN_BENEFIT:

COGNITIVE_LOAD_IMPACT:

RISKS:

REQUIRED_COMPANION_UPDATES:
(for independent verifier/gate proposals: mandatory checklist items (a)–(d)
 under Integration verdict → Independent verifier / gate companion wire-up)

REGRESSION_CHECKS:
```

---

# Required option analysis

When more than one safe design is possible, provide bounded options.

For each option:

```text
OPTION:

DESCRIPTION:

PIPELINE_EFFECT:

HUMAN_EFFECT:

FILES_AFFECTED:

ADVANTAGES:

RISKS:

WHY_CHOOSE_OR_REJECT:
```

Then provide one recommendation.

Do not silently select and implement it.

The owner must choose the design.

---

# Owner approval gate

Before explicit owner approval:

```text
READ_ONLY
```

Do not:

- create the command file;
- edit existing commands;
- create patches;
- modify process sources;
- commit;
- push;
- merge;
- perform live implementation.

The design proposal must end with one exact owner action, for example:

```text
NEXT_ACTION:
Reply: GO OPTION_A
```

A general discussion, acknowledgement, or request for explanation is not GO.

An explicit request to create the specifically proposed artifact counts as approval for that artifact and its disclosed companion updates.

It does not authorize unrelated repository changes.

---

# Phase 4 — Implementation after GO

After explicit GO, implement the approved design only.

The implementation scope must equal the approved packet.

If the integration verdict requires companion updates, apply them in the same coherent change.

Do not leave the command ecosystem in a partially compatible state.

Before writing, return:

```text
APPROVED_IMPLEMENTATION_PACKET:

SELECTED_OPTION:

NEW_FILE:

EXISTING_FILES_TO_UPDATE:

CONTRACTS_CHANGED:

PIPELINE_BEFORE:

PIPELINE_AFTER:

EXPECTED_HUMAN_WORKFLOW:

REGRESSION_CHECKS:
```

Then:

1. Create or update only approved files.
2. Preserve existing naming and output conventions.
3. Recheck producer/consumer compatibility.
4. Recheck authority ownership.
5. Recheck lifecycle placement.
6. Recheck human next-action clarity.
7. Report exact files changed.

---

# Post-implementation verification

Return:

```text
STATUS:
IMPLEMENTED | PARTIALLY_IMPLEMENTED | BLOCKED

FILES_CHANGED:

COMMAND_CREATED_OR_UPDATED:

COMPANION_UPDATES_APPLIED:

PIPELINE_INTEGRATION_VERDICT:

CONTRACT_COMPATIBILITY_VERDICT:

AUTHORITY_CONFLICTS:
NONE | <details>

NEW_BYPASS_PATHS:
NONE | <details>

HUMAN_WORKFLOW_RESULT:

REGRESSION_CHECK_RESULTS:

NEXT_ACTION:

DO_NOT_DO_YET:
```

`IMPLEMENTED` is allowed only when:

- the approved command exists;
- all required companion updates are complete;
- relevant contracts are compatible;
- no new bypass exists;
- authority remains unambiguous;
- the next human action is explicit.

When process-surface files changed (`.cursor/commands/**`, rules, skills, agents,
static-check, mirrors, `AGENTS.md`),
`NEXT_ACTION` MUST point to `/opsx-meta-commit` (not `/opsx-commit`).

---

# Anti-pattern rejection rules

Reject or redirect the proposal when:

- another command already owns the same responsibility;
- the change belongs in an existing command’s output;
- the problem is a missing error message, not a missing command;
- the proposal creates a second route to the same lifecycle state;
- the proposal is only a renamed version of existing behavior;
- the proposal is useful only to an AI agent but unclear to a person;
- the proposal requires hidden chat history;
- the proposal creates a second authoritative source;
- the proposal adds bureaucracy without measurable reduction in uncertainty.

Do not create a new status, role, source, ceremony, or file unless it has a specific function that cannot be served by an existing authority.

---

# Final analysis output

Before GO, always return:

```text
STATUS:

USER_PROBLEM:

CONFIRMED_FACTS:

GAPS:

NEED_VERDICT:

NEED_REASON:

EXISTING_COMMANDS_REVIEWED:

INTEGRATION_VERDICT:

PIPELINE_BEFORE:

PIPELINE_AFTER:

UPSTREAM_COMMANDS:

DOWNSTREAM_COMMANDS:

PRODUCER_CONSUMER_COMPATIBILITY:

AUTHORITY_CONFLICTS:

OWNERSHIP_CONFLICTS:

NEW_BYPASS_PATHS:

REQUIRED_COMPANION_UPDATES:

DESIGN_OPTIONS:

RECOMMENDED_OPTION:

HUMAN_WORKFLOW_IMPACT:

RISKS:

OWNER_DECISION_REQUIRED:

NEXT_ACTION:

DO_NOT_DO_YET:
```

---

# Self-review checklist

Before returning any proposal, confirm:

- The user’s plain-language problem was preserved.
- The need for a new command was not assumed.
- Existing commands were checked first.
- Pipeline position is explicit.
- Upstream and downstream contracts are compatible.
- Required companion changes are included.
- No authority duplication was introduced.
- No safety gate was bypassed.
- Human next action is explicit.
- Implementation remains blocked until GO.
