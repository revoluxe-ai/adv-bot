---
component_id: opsx.commands.meta_fix_command_defects
component_version: 0.4.0
ownership: EMBEDDED_SHARED
runtime_class: ACTIVE
source_commit: a71601dba3b9f5cd0076ea7185bdbbe56eaf2e3f
source_path: .cursor/commands/opsx-meta-fix-command-defects.md
source_blob_sha: b4aa7e232b2632e72dbdc3bce4006cc50cdc03cb
embedded_canonical_sha256: f02553f3fe064eca1c74425afc49dbcc96d6306f0b80c4b9e911e0a912ab8274
upstream_snapshot: .opsx/upstream/a71601dba3b9/.cursor/commands/opsx-admin-command-fix-command-defects.md
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

# BEGIN CANONICAL SOURCE BODY
---
name: /opsx-meta-fix-command-defects
id: opsx-meta-fix-command-defects
category: Workflow
description: Plan (READ_ONLY) or apply (GO / AUTHORIZE_COMMAND_FIX) command-contract defect fixes with narrow sequential I/O
argument-hint: "[optional packet or defect notes] [GO | AUTHORIZE_COMMAND_FIX]"
---

# /opsx-meta-fix-command-defects

Plan or apply confirmed command-contract defects on **process contracts only**
(`.cursor/commands/**`, `.cursor/rules/**`, `.cursor/skills/**`,
`.cursor/agents/**`, `.cursor/static-check/**`, `.agents/**`, related shared
OPSX contracts, and mirrors when listed).

This command never edits production code, product tests, migrations,
product specifications, or product tasks. An input packet cannot expand
this boundary.

This command never stages, commits, pushes, or invokes a commit command.
Commits are performed separately by the owner using the repository's
dedicated commit command.

If the human is still unsure whether the issue is a contract defect, a
pipeline redesign topic, a new-command need, or only a relationship question
→ `/opsx-meta-consult` first. Use this command when the defect target
is already identified (or a usable `FIX_PLAN_READY` / review packet exists).

Follow `.cursor/commands/opsx-source-resolution.md` and
`.cursor/commands/opsx-execution-preflight.md` (including **Read / tool I/O budgets**).

## User input

```text
$ARGUMENTS
```

Argument is **optional**. Invoking the command with an empty argument is valid.

## Modes

| Input | Mode | Writes |
|---|---|---|
| no apply token (default) | `READ_ONLY` | never |
| exact token `GO` **or** `AUTHORIZE_COMMAND_FIX` + usable `FIX_PLAN_READY` / approved plan | `APPLY` | listed process files only |

`AUTHORIZE_COMMAND_FIX` and `GO` authorize command-contract edits only.
They are not interchangeable with feature-command tokens such as
`AUTHORIZE_PROTECTED_INFRA_EDIT`, `AUTHORIZE_DESIGN_IMPLEMENTATION`, or
`AUTHORIZE_ONE_LIVE_RUN`. They do not authorize live/destructive tests.

### READ_ONLY (default — no mandatory argument)

When apply tokens are absent:

- do not edit files;
- do not stage, commit, or push;
- do not require a pasted `FIX_PLAN_READY` packet;
- build or refine a fix plan from whatever is available:
  1. optional `$ARGUMENTS` / pasted packet;
  2. else the latest completed review / analyze output in this chat
     (`CONFIRMED_DEFECTS`, `FIX_PLAN_READY`, or equivalent);
  3. else a short free-form defect note in `$ARGUMENTS` or the latest user
     message.
- If none of those exist → ask **one** narrow question for the defect source
  (review output, file list, or short description). Do not invent defects.
- Output a `STATUS: FIX_PLAN_READY` packet (or `BLOCKED_NEEDS_EVIDENCE` if
  evidence is insufficient).
- End with exact next owner action. If the user asked for copy-paste / exact
  commands / «go», also print `OWNER_RUN_COMMAND` (see Output).
- Default end line remains usable as
  `Reply: AUTHORIZE_COMMAND_FIX` (or legacy `GO`) to apply the packet.

### APPLY (requires `GO` or `AUTHORIZE_COMMAND_FIX`)

You may edit files **only** when user input contains the exact token `GO`
**or** `AUTHORIZE_COMMAND_FIX`
**and** a usable `FIX_PLAN_READY` / approved plan packet is present (in
`$ARGUMENTS` or the immediately preceding plan output in this chat).

If an apply token is present but there is no usable plan → stop with
`BLOCKED_NEEDS_FIX_PLAN` (still no writes).

## Packet shape

```text
STATUS: FIX_PLAN_READY
DEFECTS_TO_FIX:
...
FILES:
...
PROPOSED_BEHAVIOR:
...
```

For APPLY: if `STATUS` is not `FIX_PLAN_READY` (or equivalent approved plan
with explicit `APPROVED_FILES` / defects) or the fix list is empty →
`BLOCKED_NEEDS_FIX_PLAN`.

## Hard I/O rules (mandatory — hang prevention)

Do **not** reproduce the failure mode of bulk parallel Reads.

1. Build the work list **only** from `FILES:` / `APPROVED_FILES` entries in
   the packet (plus shared contracts those FILES already cite by exact path).
   In READ_ONLY without a packet, derive a provisional file list only from
   cited paths in the chat evidence — never from a full command-set dump.
2. Never open `opsx-meta-analyze-pipeline.md`, `opsx-learn-from-bug.md`,
   `opsx-meta-design-command.md`, or other large siblings unless they
   appear in `FILES:` or are an exact cited dependency required for the current
   defect.
3. Process **one defect at a time**, and within a defect **one file at a time**:
   - `Read` that exact path (use `limit`/`offset` or Grep-first for files > ~200 lines);
   - in APPLY: patch for `PROPOSED_BEHAVIOR`; in READ_ONLY: only inspect;
   - only then open the next file.
4. Max **2** concurrent `Read` calls — prefer **1** for this command.
5. Prefer `Grep` over full-file Read when locating a token.
6. No Task/subagent “extract all opsx commands”. Fix/plan from packet or chat
   evidence only.
7. If a Read stalls/times out → stop stacking Reads; report
   `blocked_preflight_timeout` for that path; continue other listed files only
   if independent.

## Speckit hook parity sweep (mandatory when in scope)

When the defect or evidence touches `**/speckit-*/SKILL.md` and Spec Kit
`HookExecutor` / hook `condition` / `extension` binding semantics:

**Trigger:** any cited path under `speckit-*/SKILL.md` plus hook-related
tokens (`HookExecutor`, `condition`, `extension`, `EXECUTE_COMMAND`,
`compare string forms`).

**Canonical reference:** `.agents/skills/speckit-analyze/SKILL.md` (or an
already-compliant sibling named in the packet).

**Budget:** grep/spot-check **only** `**/speckit-*/SKILL.md` under `.agents/`
and `.cursor/` — never a full command-set dump.

### READ_ONLY (plan expansion)

Before returning `FIX_PLAN_READY`, run bounded grep:

1. `compare string forms` under `**/speckit-*/SKILL.md` — every hit is a
   stale hook block;
2. files missing `Resolve the hook entry's \`extension\` field` among the same
   paths when the defect is HookExecutor-related.

Every hit MUST appear in `FILES:` for both `.agents` and `.cursor` mirrors.
Do not close the plan on a single cited skill when sibling hits remain.

### APPLY (verification)

After patching all listed `FILES:`:

1. Re-run the same bounded greps;
2. If any stale hit remains → `STATUS: PARTIAL` (not
   `READY_FOR_COMMAND_DIFF_REVIEW`); list remaining paths in output;
3. Each patched file must update **all** hook sections in that file
   (`before_*` and `after_*` keys).

## Steps

### READ_ONLY

1. Resolve evidence source (optional args → chat packet → free-form note).
2. Parse or draft `DEFECTS_TO_FIX` + `FILES` + `PROPOSED_BEHAVIOR`.
   When in scope, apply **Speckit hook parity sweep** (READ_ONLY) to expand
   `FILES` before step 4.
3. Optionally spot-check listed files (narrow Grep/Read) to validate the plan;
   do not write.
4. Return `FIX_PLAN_READY` (or blocked status) +
   `NEXT_ACTION: Reply: AUTHORIZE_COMMAND_FIX` (legacy `GO` still accepted).

### APPLY

1. Parse `DEFECTS_TO_FIX` / approved plan into an ordered list. Announce count
   and the exact file set (deduped). Edit **only** listed exact process paths.
2. For each defect:
   - Restate `CURRENT_BEHAVIOR` → `PROPOSED_BEHAVIOR` in one short line.
   - For each path in that defect’s `FILES:` / `APPROVED_FILES`:
     - resolve exact path (no rediscovery);
     - Grep/Read narrowly;
     - patch to match proposed behavior;
     - skip if already compliant (record `already_fixed`).
3. When in scope, run **Speckit hook parity sweep** (APPLY verification);
   stale sibling hits ⇒ `PARTIAL`, not `READY_FOR_COMMAND_DIFF_REVIEW`.
4. After all listed files: quick self-check that no new unbounded
   “read all / search all decisions” instruction was introduced.
5. Do **not** stage, commit, push, or invoke any commit command.
6. Enter **Post-APPLY diff review gate** (mandatory) and stop.

## Post-APPLY diff review gate (mandatory)

After successful APPLY edits:

1. This command never stages, commits, pushes, or invokes a commit command.
2. Return:

   ```text
   STATUS: READY_FOR_COMMAND_DIFF_REVIEW
   ```

3. Must show:
   - `git status --short`
   - list of changed files
   - full diff of **ONLY** approved FILES from the fix packet
   - simulation results (static/dry-run matrix for touched command contracts)
   - confirmation: no changes outside approved FILES
   - confirmation: no commit / push / stage performed
4. Stop.

Final `NEXT_ACTION`:

```text
Review the diff. Commit is performed separately by the owner using the
repository's dedicated commit command.
```

Do **not** print a commit command automatically.
Do **not** accept, wait for, or manage commit-authorization tokens.

## Out of scope

- Production / app code, product tests, migrations, product specs, product tasks
  (packet cannot expand this boundary)
- `openspec/decisions/**` content (unless listed in FILES as a process mirror —
  still never product tasks)
- Running `/opsx-review-commands` or full command-set re-audit mid-fix
- “While I’m here” refactors of unrelated commands
- Any write while apply tokens are absent
- Feature implementation / unit / integration / live / destructive project tests
- Docker, real PG/CH, network/API as part of this command
- Staging, committing, pushing, or invoking any commit command

## Output

### READ_ONLY

```text
STATUS: FIX_PLAN_READY | BLOCKED_NEEDS_EVIDENCE | blocked_preflight_timeout
MODE: READ_ONLY

DEFECTS_TO_FIX:
- id/title:
  - CURRENT_BEHAVIOR:
  - PROPOSED_BEHAVIOR:
  - FILES:

READ_IO:
- paths_opened:
- parallel_max_used:
- timeouts:

NEXT_ACTION:
- Reply: AUTHORIZE_COMMAND_FIX
  (legacy GO still accepted; or provide missing evidence if blocked)

OWNER_RUN_COMMAND:
```

```text
/opsx-meta-fix-command-defects AUTHORIZE_COMMAND_FIX
```

```text
APPLY_INPUT_PACKET:
- STATUS: FIX_PLAN_READY
- (repeat DEFECTS_TO_FIX / FILES / PROPOSED_BEHAVIOR above — ready to paste)
```

When the owner asks for «точные команды» / copy-paste / go:

1. Always print the fenced `OWNER_RUN_COMMAND` block above (literal command,
   no placeholders).
2. Optionally print `APPLY_INPUT_PACKET` so APPLY does not require hunting the
   prior chat plan.
3. Do not replace the run command with only prose «Reply: GO» — keep both.

### APPLY (after edits — stop here)

```text
STATUS: READY_FOR_COMMAND_DIFF_REVIEW | PARTIAL | BLOCKED_NEEDS_FIX_PLAN | blocked_preflight_timeout
MODE: APPLY

DEFECTS_APPLIED:
- id/title:
  - files_changed:
  - already_fixed:
  - skipped_reason:

CHANGED_FILES:
- <exact path>
OUTSIDE_APPROVED_FILES: none | <list>

SIMULATION_RESULTS:
- <matrix rows>

STAGE_COMMIT_PUSH: not_performed
TESTS_LIVE_DOCKER_NETWORK: not_run

READ_IO:
- paths_opened:
- parallel_max_used:
- timeouts:

FILES_NOT_TOUCHED:
- (explicit: production, product tests, migrations, specs, tasks, unlisted commands)

NEXT_ACTION:
Review the diff. Commit is performed separately by the owner using the
repository's dedicated commit command.

(optional later, transferable process class?): /opsx-meta-promote-process-lesson
  (separate from product /opsx-learn-from-bug; never auto-print a commit command)
```

After a successful APPLY that reaches `READY_FOR_COMMAND_DIFF_REVIEW`, if the
defect class looks transferable (missing guardrail, wrong branch,
durable-handoff omission, ADL/exhaust gap, etc.), prefer hinting
`/opsx-meta-promote-process-lesson` as an optional later step —
do not mix into the forced stop before diff review, and do not print a
commit command.

## Self-review

Before returning:

- mode matches input (`GO` / `AUTHORIZE_COMMAND_FIX` ⇒ APPLY, else READ_ONLY);
- READ_ONLY never wrote files and never required a mandatory packet argument;
- every APPLY edit maps to a packet defect + listed process file;
- no production / product-test / migration / product-spec / product-task edits;
- no bulk preload of the command set;
- decision lookup changes stay context-first / bounded fallback;
- I/O stayed within execution-preflight Read budgets;
- when Speckit hook parity was in scope: no stale `compare string forms` /
  missing `extension` binding remains under `**/speckit-*/SKILL.md`;
- APPLY ends at `READY_FOR_COMMAND_DIFF_REVIEW` with no stage/commit/push and
  no commit-command handoff;
- when owner asked for copy-paste/exact commands in READ_ONLY:
  `OWNER_RUN_COMMAND` for apply token is printed (never a commit command).
# END CANONICAL SOURCE BODY

# TARGET ADAPTATION NOTES

- upstream_snapshot: `.opsx/upstream/a71601dba3b9/.cursor/commands/opsx-admin-command-fix-command-defects.md`
- runtime_class: `ACTIVE`
- active_name: `/opsx-meta-fix-command-defects`
- openspec_store: `openspec/changes/**` (not source multi-store / not `.opsx/changes` SoT)
- quality: poetry-python gates per `.opsx/project/quality-gates.md` when in scope; `npm run build` UNAVAILABLE; smoke/frontend UNAVAILABLE
- unresolved_source_sections: any Poetry/pytest/pyright/kubectl/WB-domain steps in the body are blocked by TARGET OVERRIDE until adapters exist
- manual_review: `.opsx/project/manual_review.md`
- central_discovery: when identity is missing/uncertain or a central replacement
  may close the defect, compare BASE/LOCAL/CENTRAL using a fresh index. Stale
  negative → `BLOCKED_NEEDS_FRESH_INDEX`. Valid central fix → hand off to
  `/opsx-meta-import-command`. Do not merge command bodies in this command.
- orientation: emit `ORIENTATION_HINT` with `NEXT_META: /opsx-meta`
- process lesson handoff: `/opsx-meta-promote-process-lesson`
