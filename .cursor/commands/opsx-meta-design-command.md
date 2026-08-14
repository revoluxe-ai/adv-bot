---
component_id: opsx.commands.meta_design_command
component_version: 0.4.0
ownership: EMBEDDED_SHARED
runtime_class: ACTIVE
source_commit: a71601dba3b9f5cd0076ea7185bdbbe56eaf2e3f
source_path: .cursor/commands/opsx-meta-design-command.md
source_blob_sha: 409430b17ff6b8f875b6fdd26a1354d3eec6f852
embedded_canonical_sha256: 46e18e403cccf152c6bd58e4d737917bf03a596b6961390289df51149f388baa
upstream_snapshot: .opsx/upstream/a71601dba3b9/.cursor/commands/opsx-admin-command-design-command.md
required_adapters: ["opsx-lite"]
local_modification_note: "Projectize 2026-08-07: vue-npm dropped; poetry-python adapter; OPSX-WB-META-SURFACE-01"
local_override_policy: TARGET_OVERRIDE_HIGHEST_PRIORITY
contract_id: OPSX-WB-META-SURFACE-01
newline_normalization: none
---

# TARGET OVERRIDE — HIGHEST PRIORITY

**Contract:** `OPSX-WB-META-SURFACE-01`  
**Runtime class:** `ACTIVE`  
**Precedence:** This override wins over the canonical source body for target paths, capabilities, safety stops, and authority.

### Target authority paths

- Changes: `openspec/changes/**`
- Policies: `openspec/policies/**`
- Decisions: `openspec/decisions/**`
- Schemas/templates: `openspec/schemas/**`
- Activation/provenance: `.opsx/registry/**`
- Frozen upstream: `.opsx/upstream/a71601dba3b9/`
- Adapter: `.opsx/adapters/poetry-python/README.md`
- Quality gates: `.opsx/project/quality-gates.md`

### Hard target bans

- Do not install dependencies / modify `package.json` or lockfile.
- Do not access production / Kubernetes / secrets.
- Do not push, open PR, rebase, force, or deploy.
- Do not activate WB/product domain assumptions from the source body.
- Replace Poetry/pytest/pyright/kubectl execution with capability checks; missing capability => unavailable or FAIL_CLOSED, never PASS-by-absence.
- Mandatory declared executable checks: per `.opsx/project/quality-gates.md` (poetry-python). `npm run build` is UNAVAILABLE / not applicable (vue-npm dropped; no root build script).
- Smoke/acceptance/lint/typecheck/frontend tests: UNAVAILABLE unless adapter says otherwise.

### Projectization gate

Read `.opsx/projectization.yaml` before any write.
If `status` != `COMPLETE` or `normal_commands_enabled` is false:

```text
STATUS: FAIL_CLOSED
REASON: OPSX_PROJECTIZATION_REQUIRED
NEXT_COMMAND: /opsx-projectize
```

Exempt: `/opsx-projectize` and `/opsx-projectize:GO`.

### ACTIVE allow

Owner unblocked this former-DEFERRED command (2026-08-03): execute canonical source-body semantics **after** remapping paths to target authority above.

Hard bans still apply. Missing Poetry/pytest/pyright/kubectl (and other undeclared source capabilities) => UNAVAILABLE or FAIL_CLOSED — never PASS-by-absence. Do not invent missing adapters or import source product dumps. File/process operations only on target authority paths.

### Write boundary (TARGET — highest priority)

**Rule:** this command touches **only its own uncommitted** paths.

- **Own** = the proposed new command’s identity files (typically
  `.cursor/commands/<proposed-name>.md` and only other paths introduced for
  that same new command).
- **Uncommitted** = path **not in `HEAD`** (never committed). Create or edit
  those freely after GO. Paths already in `HEAD` are **forbidden** even if
  the working tree is dirty — that is fix territory →
  `/opsx-meta-fix-command-defects`.

After Owner GO for **create-new** or **resume-uncommitted** only:

- MAY create/edit own uncommitted files only.
- MUST NOT touch any path present in `HEAD`.
- MUST NOT apply companion / IMPROVE / GRAPH / registry / openspec edits on
  committed files.
- Needs on committed paths → READ_ONLY here; `REQUIRED_EXTERNAL_FIXES` +
  `NEXT_ACTION: /opsx-meta-fix-command-defects`.
- Central reuse → `/opsx-meta-import-command` (no merge here).
- Resuming an unfinished uncommitted command in a **new chat** is a
  **separate option** (`RESUME_UNCOMMITTED_COMMAND`) — never silently fold
  into `NEW_COMMAND_REQUIRED` or `IMPROVE_EXISTING_COMMAND`.

# BEGIN CANONICAL SOURCE BODY
# /opsx-meta-design-command

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
- can be written as own uncommitted command file(s) without touching
  committed neighbors (companions → fix-command-defects).

## When not to use (front-door)

If the human only needs to discuss how existing commands relate, triage odd
admin/pipeline behavior, or discover which process command to run next —
route to `/opsx-meta-consult` first. Use this command when the
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
SOURCE: opsx-meta-promote-process-lesson
...
```

Treat `DESIGN_BRIEF_READY` as structured problem input for Phase 1 need
analysis. It does **not** skip IMPROVE_EXISTING_COMMAND vs
NEW_COMMAND_REQUIRED vs RESUME_UNCOMMITTED_COMMAND adjudication.
Process-only briefs stay on process surfaces (commands / rules /
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
   - improve an existing **committed** command (→ fix-command-defects);
   - update a shared process rule or contract (→ fix / other owners);
   - create a new command (path not in HEAD yet);
   - **resume** an unfinished **uncommitted** command (often in a new chat).

Do not design a new command before this verdict.

When an uncommitted own command draft already exists (path not in `HEAD`),
offer resume vs create-another as **distinct** Owner options — do not assume
either.

---

# Need-analysis verdicts

Return exactly one:

```text
NO_CHANGE_REQUIRED
IMPROVE_EXISTING_COMMAND
PROCESS_CONTRACT_UPDATE_REQUIRED
NEW_COMMAND_REQUIRED
RESUME_UNCOMMITTED_COMMAND
BLOCKED_NEEDS_EVIDENCE
```

- `NEW_COMMAND_REQUIRED` — no suitable uncommitted draft; create a new path.
- `RESUME_UNCOMMITTED_COMMAND` — continue a named unfinished command file that
  is **not in `HEAD`** (typical: new chat picking up prior design work).
- `IMPROVE_EXISTING_COMMAND` — target path **is in `HEAD`** → design may
  analyze, but writes go to `/opsx-meta-fix-command-defects`.

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
- do not preload `opsx-meta-analyze-pipeline.md`, `opsx-learn-from-bug.md`, or
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
- `COMPATIBLE_WITH_REQUIRED_COMPANION_UPDATES` — a new command is designable, but
  committed neighbors also need edits. **This command must not apply those
  edits.** List them as `REQUIRED_EXTERNAL_FIXES` and hand off to
  `/opsx-meta-fix-command-defects`. Phase 4 may still create only NEW files
  if Owner GO is for create-new; companions remain external.
- `CONFLICTS_FOUND` — implementation is prohibited until the conflict is resolved.
- `BLOCKED_NEEDS_EVIDENCE` — fresh repo evidence is insufficient.

Never edit committed companion files from this command.

## Independent verifier / gate companion wire-up (mandatory)

When the proposed command is an **independent READ_ONLY verifier or
lifecycle gate** (exemplar: `/opsx-planning-review` +
`.cursor/pipeline/contracts/PLANNING_REVIEW.md`):

1. State **soft vs hard gate** explicitly (v1 soft recommend vs hard block).
2. `REQUIRED_EXTERNAL_FIXES` MUST list at least:
   - (a) handoff consumer on the repair writer (e.g. `/opsx-update`
     `MODE: REPAIR_*` + handoff token) — **executable** early Mode
     detection + Steps, not description/guardrail-only; when the writer is
     dual-mode, skill/prompt mirrors must advertise the same Mode branch;
   - (b) soft `NEXT_ACTION` on producers that previously jumped to apply
     (e.g. `/opsx-continue` / `/opsx-ff` after tasks complete);
   - (c) `GRAPH` state and/or transition edge for the hop;
   - (d) soft preflight note on `/opsx-apply` when applicable.
3. Do **not** claim `COMPATIBLE` when those companions are missing for this
   command class — use `COMPATIBLE_WITH_REQUIRED_COMPANION_UPDATES` and hand
   off to `/opsx-meta-fix-command-defects`. Companions are never applied
   in this command's Phase 4.

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

REQUIRED_EXTERNAL_FIXES:
(committed paths / IMPROVE work → /opsx-meta-fix-command-defects; not applied here)
(for independent verifier/gate proposals: mandatory checklist items (a)–(d)
 under Integration verdict → Independent verifier / gate companion wire-up)

REGRESSION_CHECKS:
```

---

# Required option analysis

When an unfinished uncommitted command draft is present, always include a
distinct option, for example:

```text
OPTION: RESUME_UNCOMMITTED
DESCRIPTION: Continue <path> (not in HEAD) in this chat
...
```

Do not merge resume into «create new» or «improve committed».

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

GO (or an explicit request to create the proposed **new** artifact) authorizes
writes to **own uncommitted** paths only (not in `HEAD`). It does **not**
authorize fixes to committed files, companion updates, or IMPROVE_EXISTING.

If need verdict is `IMPROVE_EXISTING_COMMAND` or only committed paths must
change → do not offer Phase-4 write; `NEXT_ACTION` =
`/opsx-meta-fix-command-defects`.

For resume in a new chat, Owner GO must name the option explicitly, e.g.
`GO RESUME_UNCOMMITTED` / `GO OPTION_RESUME` with the draft path.

---

# Phase 4 — Own uncommitted files after GO

After explicit GO **and** need verdict `NEW_COMMAND_REQUIRED` or
`RESUME_UNCOMMITTED_COMMAND` (or equivalent create/resume option): write
**only own uncommitted** paths.

Before each write: if `git cat-file -e HEAD:<path>` succeeds → path is
committed → `FAIL_CLOSED` / `BLOCKED_COMMITTED_PATH` (even if dirty).
If it fails → uncommitted → create or edit allowed for own identity only.

Before writing, return:

```text
APPROVED_IMPLEMENTATION_PACKET:

SELECTED_OPTION:

OWN_UNCOMMITTED_FILES:
(only paths not in HEAD, owned by the new command)

EXISTING_FILES_TO_UPDATE:
none (committed paths out of scope)

REQUIRED_EXTERNAL_FIXES:
(optional; handoff list for /opsx-meta-fix-command-defects)

PIPELINE_BEFORE:

PIPELINE_AFTER:

EXPECTED_HUMAN_WORKFLOW:

REGRESSION_CHECKS:
```

Then:

1. Reject any path in `HEAD`.
2. Create/edit only own uncommitted approved files.
3. Preserve naming and output conventions of the command plane.
4. Recheck producer/consumer compatibility **in the report** (do not patch
   neighbors).
5. Recheck authority / lifecycle placement **in the report**.
6. Report exact files written.
7. Zero modifications to committed paths.

If GO arrives for IMPROVE / companion-only work → no writes; route to
`/opsx-meta-fix-command-defects`.

---

# Post-implementation verification

Return:

```text
STATUS:
IMPLEMENTED | PARTIALLY_IMPLEMENTED | BLOCKED

FILES_CHANGED:
(own uncommitted paths only)

COMMAND_CREATED_OR_UPDATED:
(own uncommitted create/edit; never committed paths)

REQUIRED_EXTERNAL_FIXES:
none | <list — not applied here>

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

- approved **own uncommitted** command file(s) were written;
- **no** path in `HEAD` was modified;
- external/companion fixes are listed (if any), not silently applied;
- no new bypass exists;
- authority remains unambiguous;
- the next human action is explicit.

When own uncommitted process-surface files were written,
`NEXT_ACTION` MUST point to `/opsx-meta-commit` (not `/opsx-commit`).
If `REQUIRED_EXTERNAL_FIXES` is non-empty, also point Owner to
`/opsx-meta-fix-command-defects` (ALSO_OK / follow-up), without applying them.

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

REQUIRED_EXTERNAL_FIXES:
(include independent verifier/gate checklist (a)–(d) when applicable)

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
- Required external/committed fixes are listed for handoff, not applied here.
- No authority duplication was introduced.
- No safety gate was bypassed.
- If proposing a sole front-door plus an obsolete thin redirect: every
  safety stop / `BLOCKED_*` / `DO_NOT_DO_YET` on the alias MUST also appear
  on the live front-door (GRAPH or nav prose alone is insufficient; agents
  follow the SoT command body).
- Human next action is explicit.
- Writes remain blocked until GO; GO touches only own uncommitted paths.
# END CANONICAL SOURCE BODY

# TARGET ADAPTATION NOTES

- upstream_snapshot: `.opsx/upstream/a71601dba3b9/.cursor/commands/opsx-admin-command-design-command.md`
- runtime_class: `ACTIVE`
- active_name: `/opsx-meta-design-command`
- openspec_store: `openspec/changes/**` (not source multi-store / not `.opsx/changes` SoT)
- quality: poetry-python gates per `.opsx/project/quality-gates.md` when in scope; `npm run build` UNAVAILABLE; smoke/frontend UNAVAILABLE
- write_boundary: own uncommitted paths only; committed →
  `/opsx-meta-fix-command-defects`
- resume_uncommitted: separate need verdict / Owner option for new-chat pickup
  of unfinished drafts (not folded into NEW or IMPROVE)
- unresolved_source_sections: any Poetry/pytest/pyright/kubectl/WB-domain steps in the body are blocked by TARGET OVERRIDE until adapters exist
- manual_review: `.opsx/project/manual_review.md`
- central_discovery: before `NEW_COMMAND_REQUIRED`, search local then fresh catalog index
  (`.opsx/shared/command-discovery.md`). Stale negative search →
  `BLOCKED_NEEDS_FRESH_INDEX` → `/opsx-meta-update-index`. Central reuse →
  `ADOPTION_PACKET` → `/opsx-meta-import-command` (do not merge here).
- orientation: emit `ORIENTATION_HINT` with `NEXT_META: /opsx-meta`
