---
component_id: opsx.commands.commit_all
component_version: 0.1.1
ownership: TARGET_ONLY
runtime_class: ACTIVE
canonical_source_body: adapted_target_native
source_command_sha256: 9bba12f304a71cd6dea11b539e89c2b65ff4cc321b024d875f86f44d1499e580
required_adapters: ["opsx-lite", "poetry-python"]
local_modification_note: "Imported 20260813T070407Z via /opsx-meta-import-command KEEP=opsx-commit-all OCCURRENCE=9eecc03d30c44e38; WB/Poetry target-native retained; children /opsx-commit + /opsx-meta-commit"
local_override_policy: TARGET_OVERRIDE_HIGHEST_PRIORITY
contract_id: OPSX-WB-COMMIT-ALL-01
newline_normalization: none
---

# TARGET OVERRIDE — HIGHEST PRIORITY

**Contract:** `OPSX-WB-COMMIT-ALL-01`  
**Runtime class:** `ACTIVE`  
**Precedence:** This override wins for target paths, capabilities, safety stops, and authority.

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

- Do not install dependencies / modify `package.json`, Poetry lock, or `pyproject.toml` unless a child command explicitly owns that write.
- Do not access production / Kubernetes / secrets.
- Do not push, open PR, rebase, force, or deploy.
- Do not activate game/Vue/`vue-npm` / `npm run build` assumptions from the donor body.
- Missing undeclared capabilities => UNAVAILABLE or FAIL_CLOSED, never PASS-by-absence.
- Mandatory declared executable checks belong to child matrices (`/opsx-commit`
  Poetry/pytest/pyright gates; `/opsx-meta-commit` process checks). This
  orchestrator does not invent gates and does not run `npm run build`.

### Projectization gate

Read `.opsx/projectization.yaml` before any write-bearing child dispatch.
If `status` != `COMPLETE` or `normal_commands_enabled` is false:

```text
STATUS: FAIL_CLOSED
REASON: OPSX_PROJECTIZATION_REQUIRED
NEXT_COMMAND: /opsx-projectize
```

### Write boundary (orchestrator)

**Parent never stages, commits, or amends.** Git writes belong exclusively to:

- `/opsx-commit` (product / OpenSpec / non-process)
- `/opsx-meta-commit` (process surfaces)

Parent may only: parse tokens, launch Task subagents, forward args, serialize
child-GO, and print a SUMMARY.

---

---
description: "Orchestrate /opsx-commit + /opsx-meta-commit: parallel plan Tasks (mini→auto), then serial child-GO; one SUMMARY."
argument-hint: "[ALL] [FAST_CHECK|FULL_CHECK] [INCLUDE_FULL_DIRTY_TREE] [MODEL=<slug>|MODEL=auto] GO [optional context]"
---

# /opsx-commit-all

Dual-lane commit orchestrator for the WB Sky / Poetry target.

**Purpose:** one Owner slash runs both commit authorities without merging their
ownership, without parallel git writers, and with a single human-facing report.

**Named dependencies (exact paths — may Read):**

- `.cursor/commands/opsx-execution-preflight.md`
- `.cursor/commands/opsx-commit.md`
- `.cursor/commands/opsx-meta-commit.md`

Follow exclusive-active-command: this turn’s PRIMARY is `/opsx-commit-all`.
Child command bodies are executed only inside Task subagents (each child is
PRIMARY of its own Task turn). Do not merge child Steps into the parent turn.

## Default behavior

By default (no lane filter tokens), run **both** lanes:

1. `LANE_PRODUCT` → `/opsx-commit`
2. `LANE_PROCESS` → `/opsx-meta-commit`

Optional future filters are out of scope for v0.1 unless Owner later designs them.

## Critical naming note

Command name `opsx-commit-all` does **not** imply child mode `ALL`.

Child `ALL` / `FAST_CHECK` / `FULL_CHECK` / `INCLUDE_FULL_DIRTY_TREE` apply
**only** when those exact tokens appear in this command’s `$ARGUMENTS`.

## Tokens

Parse case-sensitive tokens from `$ARGUMENTS`:

| Token | Effect |
|---|---|
| `GO` | Authorizes **serial child-GO** after plans (parent still does not git-write) |
| `ALL` | Forwarded to both children (product lane still needs static-check FULL receipt when that child requires it) |
| `FAST_CHECK` / `FULL_CHECK` | Forwarded as child check mode |
| `INCLUDE_FULL_DIRTY_TREE` | Forwarded as child scope token |
| `MODEL=<slug>` | Force child Task model (`auto` = host Auto / omit model) |
| `MODEL=auto` | Explicit Auto fallback (same as FALLBACK_CHILD_MODEL) |

Strip `MODEL=*` from forwarded child args (orchestrator-only token). All other
non-`MODEL=*` tokens that belong to the child argument contracts are forwarded
**identically** to both lanes (same string), except `GO` handling below.

### GO handling (mandatory)

```text
PARENT_HAS_GO: yes | no
PLAN_ARGS: $ARGUMENTS with exact token GO removed and MODEL=* stripped
EXEC_ARGS: PLAN_ARGS + exact token GO
```

- Plan Tasks always receive `PLAN_ARGS` (**never** `GO`).
- Execute Tasks receive `EXEC_ARGS` only when `PARENT_HAS_GO=yes`.
- If `GO` is absent: plan both lanes, print SUMMARY, stop (no execute Tasks).

## Child model (mini default, auto fallback)

```text
DEFAULT_CHILD_MODEL: gpt-5.4-mini-high
FALLBACK_CHILD_MODEL: auto
```

Resolution order:

1. If `MODEL=<slug>` present (including `MODEL=auto`) → use that as
   `RESOLVED_CHILD_MODEL`.
2. Else try Task `model` = `DEFAULT_CHILD_MODEL` (`gpt-5.4-mini-high`).
3. If mini is **not** in the live Task allowlist, or the Task launch fails
   with a model-unavailable / invalid-model error → **one** retry with
   `FALLBACK_CHILD_MODEL: auto`:
   - omit the Task `model` parameter, or pass host-equivalent Auto / `inherit`
     if the live API requires an explicit token;
   - report `CHILD_MODEL_FALLBACK: auto` in SUMMARY.
4. Do **not** silently upgrade to an explicit premium / high-tier slug.
5. Owner `MODEL=<invalid>` that is neither allowlisted nor `auto` →
   `FAIL_CLOSED` / `BLOCKED_INVALID_MODEL` (no invent).

`subagent_type`: `generalPurpose` (children must Read contracts + run git).

## Phase machine

### 0) Preflight

- Projectization gate (above).
- Confirm child command files exist.
- Do **not** run unbounded dirty-tree inventories in the parent; children own
  their preflight under execution-preflight budgets.

### 1) Parallel PLAN fan-out (mandatory)

Launch **two** Task subagents in the **same** parent turn (parallel):

```text
TASK_A:
  PRIMARY: /opsx-commit
  ARGS: PLAN_ARGS
  MODEL: RESOLVED_CHILD_MODEL (mini → auto fallback rules)
  PROMPT_MUST:
    - Read and follow .cursor/commands/opsx-commit.md as PRIMARY
    - Treat ARGS as $ARGUMENTS (no GO)
    - Plan only: no stage/commit/amend
    - Return the child’s normal no-GO plan report verbatim at the end

TASK_B:
  PRIMARY: /opsx-meta-commit
  ARGS: PLAN_ARGS
  MODEL: same as TASK_A
  PROMPT_MUST: analogous for .cursor/commands/opsx-meta-commit.md
```

Do not wait for Owner between the two plan launches.

### 2) Serial EXECUTE (only if PARENT_HAS_GO)

**Child remains the git writer.** Parent never applies the plan itself.

As each plan Task completes successfully with an actionable in-scope plan
(not pure `OUT_OF_SCOPE_REDIRECT` / empty / hard `BLOCKED` that forbids GO):

1. If an execute Task is already running → wait for it to finish (serialize).
2. Launch exactly one execute Task for that ready lane with `EXEC_ARGS`.
3. Prompt MUST:
   - Read/follow the same child command file as PRIMARY
   - Treat `EXEC_ARGS` as `$ARGUMENTS` (includes `GO`)
   - Prefer executing the plan just produced for this lane (attach plan text)
   - Still obey all child gates (receipt, protected branch, matrices, scope)
4. When that execute finishes, start the next ready lane’s execute (if any).

**As-ready order:** first successfully planned actionable lane executes first;
the second waits. If both plans are ready before either execute starts,
prefer order: `LANE_PROCESS` then `LANE_PRODUCT` (stable default).

If a lane’s plan is non-actionable (clean / out-of-scope only / blocked):

```text
LANE_EXECUTE: SKIPPED
LANE_SKIP_REASON: <from child plan>
```

Do not invent commits for skipped lanes.

### 3) Fan-in SUMMARY (mandatory)

Always print a parent SUMMARY after plan phase (and after execute phase when
`GO` was present), even when a lane skipped or failed.

## Authority rules

```text
AUTHORITY:
- /opsx-commit owns product grouping, staging, checks, commits
- /opsx-meta-commit owns process grouping, staging, checks, commits
- /opsx-commit-all owns orchestration + SUMMARY only

FORBIDDEN_FOR_PARENT:
- git add / git commit / git commit --amend
- re-grouping files across lanes
- overriding child BLOCKED / FAIL / receipt gates
- launching /opsx-static-check (product child may only recommend it)
- treating command name as child ALL
- inventing npm / vue-npm gates on this Poetry target
```

## Failure behavior

| Situation | Parent status | Action |
|---|---|---|
| Plan Task errors / times out | `BLOCKED` or `PARTIAL` | Do not execute that lane; continue other lane plan/execute rules |
| Execute Task fails child gate | `PARTIAL` / `BLOCKED` | Surface child report; do not retry silently more than once |
| `index.lock` / git lock on execute | one serial re-dispatch of **that** lane only | Then stop that lane if still failing |
| Both lanes skipped | `COMPLETE_NOOP` | SUMMARY explains clean/out-of-scope |
| Parent args missing required child receipt under forwarded `ALL` | child blocks product lane | Parent surfaces; may still run process lane |

Never mark parent `COMPLETE` if any execute was attempted and failed without a
successful child commit report for that attempted lane — use `PARTIAL` or
`BLOCKED`.

## Recovery

- Re-run `/opsx-commit-all` with same tokens, or
- Run the failed child alone (`/opsx-commit` or `/opsx-meta-commit`).

## Final report (parent)

```text
STATUS: PLAN_READY | COMPLETE | COMPLETE_NOOP | PARTIAL | BLOCKED | FAIL_CLOSED
MODE: PLAN_ONLY | PLAN_THEN_SERIAL_GO
PARENT_HAS_GO: yes | no
FORWARDED_PLAN_ARGS: ...
FORWARDED_EXEC_ARGS: ... | n/a
CHILD_MODEL: gpt-5.4-mini-high | auto | <override>
CHILD_MODEL_FALLBACK: none | auto
WHAT_HAPPENED:
WHY:
CURRENT_STATE:
LANES:
- LANE_PROCESS: PLAN=... EXECUTE=... | SKIPPED | n/a
- LANE_PRODUCT: PLAN=... EXECUTE=... | SKIPPED | n/a
CHILD_REPORTS:
### LANE_PROCESS
<verbatim or condensed child final report>
### LANE_PRODUCT
<verbatim or condensed child final report>
OWNER_DECISION_REQUIRED: yes | no
NEXT_ACTION:
DO_NOT_DO_YET: push; parent git-write; assume ALL from command name
ORIENTATION_HINT:
  LANE: META | PRODUCT
  NEXT_META: /opsx-meta
  NEXT_ACTION:
```

### NEXT_ACTION rules

- `PLAN_ONLY` success → `NEXT_ACTION: /opsx-commit-all GO` (same other tokens)
- `COMPLETE` → usually `none` (or child-surfaced follow-ups if any remain dirty)
- Product blocked on static-check receipt → recommend `/opsx-static-check FULL` then re-run with `ALL GO` if `ALL` was requested
- Process-only leftovers after product success → `/opsx-meta-commit` (should be rare if both lanes ran)

## When to use

- Mixed dirty tree (product + process) after a work session
- Owner wants one slash + one SUMMARY instead of two manual commit commands

## When not to use

- Debugging a single lane’s commit contract
- Redesigning commit ownership (→ `/opsx-meta-design-command` / fix-defects)
- Expecting parent to commit “from plans” without children (forbidden)

## Absolute prohibitions

- Parent git writes
- Parallel execute Tasks (plans may be parallel; GO executes are serial)
- Silent premium model upgrade (auto fallback only; never invent premium slugs)
- Committing process files via product child or product via process child
- Push / PR / rebase / force from this command
- Seeding or requiring `vue-npm` / `npm run build` on this target

## TARGET ADAPTATION NOTES

- active_name: `/opsx-commit-all`
- children: `/opsx-commit`, `/opsx-meta-commit`
- pattern: parallel plan + serial child-GO (option B; not parent-writer)
- child_model: `gpt-5.4-mini-high` default; fallback `auto` (omit/inherit)
- target: WB Sky / Poetry (`opsx-lite` + `poetry-python`)
- donor: game/go-to-prod occurrence `ac2a8c0791763d3f` @ `5ddca9a94f6d87176c64f888511996009f59bedc`
- companions (external): registry activation, `/opsx-meta` router, pipeline GRAPH
  → `/opsx-meta-fix-command-defects` if desired; not required for MVP runtime
