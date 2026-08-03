---
name: /opsx-admin-command-resolve-conflicts
id: opsx-admin-command-resolve-conflicts
category: Workflow
description: "Plan (READ_ONLY) or apply (GO) semantic git conflict resolution on AI/process surfaces only; finish merge/rebase continue"
argument-hint: "GO [optional topic] | ABORT_MERGE GO | ABORT_REBASE GO"
---

# /opsx-admin-command-resolve-conflicts

Exclusive owner of **git conflict resolution** on **AI / process surfaces**
(Cursor/agent commands, rules, skills, agents, static-check, pipeline graph,
antipattern-gate, prompt/skill mirrors, and root agent guides).

Use when merge or rebase left conflict markers / unmerged paths on process
surfaces, or when another command redirected here because the tree is
conflicted.

This command does **not** own ordinary semantic commits after a clean tree
(`/opsx-admin-command-commit`), product conflict resolution, push, or
force-push.

You may mutate the working tree / index / finish merge|rebase **only** when
user input contains the exact token `GO`.

If `GO` is absent:
- do not edit files;
- do not `git add`;
- do not run `merge --continue` / `rebase --continue` / abort;
- output only the conflict plan and owner decisions required.

Follow `.cursor/commands/opsx-source-resolution.md` and
`.cursor/commands/opsx-execution-preflight.md` (git-mutating class on GO).

## User input

```text
$ARGUMENTS
```

## Purpose

1. **Plan** (no `GO`) — inventory unmerged process paths, classify each
   conflict, propose resolutions, list Owner decisions.
2. **Execute** (`GO`) — apply approved resolutions, `git add` resolved
   process paths, finish `git merge --continue` or `git rebase --continue`
   when safe.
3. **Recheck** — after resolve, spot producer/consumer and dual-authority
   breakage; hand off to fix-defects when needed.

## When to use

- `git status` shows unmerged paths (`UU`, `AA`, `DU`, `UD`, `AU`, `UA`, `DD`)
  under process surfaces.
- Merge or rebase is in progress and process files are conflicted.
- `/opsx-admin-command-commit`, `/opsx-create-pr`, or `/opsx-split-for-pr`
  redirected here.
- Operator asks how to finish merging command/rule edits across branches.

## When not to use

- Clean working tree / no merge|rebase in progress → nothing to resolve;
  if dirty process files need commits → `/opsx-admin-command-commit`.
- Only **product** paths conflicted → stop with `BLOCKED_MIXED_SCOPE` or
  product-only note; do not rewrite app/tests as “process success”.
- Designing a new command → `/opsx-admin-command-design-command`.
- Contract defect after a clean merge → `/opsx-admin-command-fix-command-defects`.
- Day-to-day navigation → `/opsx-pipeline`.
- Unclear which admin command applies (no conflict evidence) →
  `/opsx-admin-command-consult`.

## In-scope surfaces (exclusive write/resolve)

Same process set as `/opsx-admin-command-commit`:

```text
.cursor/commands/**
.cursor/rules/**
.cursor/skills/**
.cursor/agents/**
.cursor/static-check/**
.cursor/pipeline/**
.cursor/antipattern-gate/**
.cursor/opsx-review-commands
.agents/**
.github/skills/**
.github/prompts/**
.github/copilot-instructions.md
.github/git-commit-instructions.md
AGENTS.md
```

Everything else is **out of scope** for resolution writes.

## Authority boundary (mandatory)

- Owns: conflict classification, proposed/applied file resolutions on
  in-scope paths, `git add` of those paths, `merge --continue` /
  `rebase --continue` when all in-scope conflicts are cleared and no
  out-of-scope unmerged paths remain.
- Does **not** own: ordinary post-merge semantic commits (→ admin-commit),
  product commits (→ `/opsx-commit`), PR creation, push, force-push,
  verify/archive/approval gates, silent redesign of command contracts.
- Does **not** silently re-decide another command’s ownership tokens.
- `AUTHORITY_TOKEN` conflicts require explicit Owner choice in the plan
  (or in `$ARGUMENTS` on the GO turn) before apply.

## Conflict classes (exactly one per path)

| Class | Meaning | Auto-propose? | Apply without per-path Owner note? |
|---|---|---|---|
| `TRIVIAL_TEXTUAL` | Non-overlapping hunks / whitespace / import-order noise | yes | yes under GO if plan showed them |
| `SECTION_OVERLAP` | Same markdown/code section edited both sides | semantic merge proposal | yes under GO if plan proposal accepted (no OWNER_DECISION left) |
| `AUTHORITY_TOKEN` | OWNER / STATUS / GATE / disposition / forbid-list / denylist / exclusive-owner prose diverged | propose options only | **no** — need Owner choice |
| `CROSS_FILE_CONTRACT` | Merge would break producer/consumer or create dual authority across files | propose + warn | GO may merge text; must set handoff to fix-defects when broken |
| `MIXED_SCOPE` | Same conflict set includes out-of-scope (product) paths | do not resolve product | **stop** — `BLOCKED_MIXED_SCOPE` |

## Prevention note (operator)

Prefer fewer conflicts upstream:

- avoid editing the same process file on two long-lived branches;
- serialize shared contracts (`opsx-execution-preflight`,
  `opsx-source-resolution`, pipeline GRAPH/META);
- merge process PRs shared-contracts → consumers → routing/consult.

Prevention does not replace this command when `UU` already exists.

## Modes

| Input | Mode | Writes |
|---|---|---|
| default (no `GO`) | `READ_ONLY` / plan | never |
| exact `GO` + usable plan (this chat or `$ARGUMENTS`) | `APPLY` | in-scope resolves + git continue |
| `ABORT_MERGE GO` | `ABORT` | `git merge --abort` only |
| `ABORT_REBASE GO` | `ABORT` | `git rebase --abort` only |

Abort tokens without `GO` → plan-only explanation; no abort.

## Mandatory preflight

```text
OPERATION_REASON: detect merge/rebase + unmerged path inventory
REQUIRED_FOR: plan and apply decisions
SKIP_IF: never when this command runs
TIME_BUDGET: status 10s; rev-parse/head checks 5s; per-file conflict Read ≤30s
FAILURE_BEHAVIOR: blocked_preflight_timeout / EVIDENCE_GAP; no retry loop
```

Run the smallest set:

```bash
git branch --show-current
git status --short
git rev-parse -q --verify MERGE_HEAD
git rev-parse -q --verify REBASE_HEAD
```

Optional when needed for side labels:

```bash
git diff --name-only --diff-filter=U
```

Do not `git fetch` unless REQUIRED_FOR a stated decision.
Do not push.

Protected branches (`main` / `master` / `prod` / `production`): may plan.
Apply / continue / abort on protected branches requires
`GO_ON_PROTECTED_BRANCH` in addition to `GO`. Even then, never push.

## Plan steps (READ_ONLY)

1. Confirm merge and/or rebase in progress, or unmerged paths present.
2. List every unmerged path; partition **in-scope** vs **out-of-scope**.
3. If any out-of-scope unmerged path exists → `BLOCKED_MIXED_SCOPE` (or
   product-only status). Do not propose resolving product files here.
4. For each in-scope path: Grep/Read only that file (section budget);
   classify exactly one conflict class; draft resolution text or options.
5. List `OWNER_DECISIONS_REQUIRED` for every `AUTHORITY_TOKEN` path.
6. State intended finish op: `merge --continue` | `rebase --continue` | none.
7. Emit output contract. Stop.

I/O: parallel Read max **2**; no full `.cursor/commands/**` dump.

## Apply steps (`GO`)

Preconditions:

- usable plan from this chat or `$ARGUMENTS`;
- every `AUTHORITY_TOKEN` item has an Owner choice;
- no unresolved `MIXED_SCOPE` / out-of-scope unmerged paths;
- protected-branch rule satisfied if applicable.

Then:

1. Write resolved content for each planned in-scope path (no conflict
   markers left).
2. `git add -- <in-scope-resolved-paths>` only.
3. Re-check `git status --short`: no `U` paths remain.
4. If merge in progress → `git merge --continue` (non-interactive; if the
   editor would open, use a simple merge message describing process-surface
   conflict resolution — do not invent product behavior claims).
5. If rebase in progress → `git rebase --continue` under the same rules.
6. Contract recheck (bounded): skim changed command handoff/ownership
   tokens for dual-authority or producer-without-consumer. If broken →
   `CONTRACT_BROKEN_AFTER_MERGE` and `NEXT_ACTION` =
   `/opsx-admin-command-fix-command-defects`.
7. If tree still has ordinary (non-conflict) process dirt →
   `NEXT_ACTION: /opsx-admin-command-commit`.
8. Never `git push`, `rebase` onto remote as a new op, `reset --hard`,
   or `clean -fd`.

## Hard prohibitions

Never run:

```bash
git push
git push --force
git reset --hard
git clean -fd
```

Never:

- `-X ours` / `-X theirs` / checkout --ours|--theirs on `AUTHORITY_TOKEN`
  without explicit Owner choice recorded in the plan output;
- resolve or stage out-of-scope product paths;
- claim `RESOLVED` while unmerged paths remain;
- treat abort as success without `ABORT_* GO`;
- open PRs or call `/opsx-create-pr` as a side effect.

## Output contract (every run)

```text
STATUS:
MODE: READ_ONLY | APPLY | ABORT
WHAT_HAPPENED:
WHY:
GIT_STATE: merge_in_progress | rebase_in_progress | conflicted_paths | clean | unknown
IN_SCOPE_CONFLICTS:
- path:
  class: TRIVIAL_TEXTUAL | SECTION_OVERLAP | AUTHORITY_TOKEN | CROSS_FILE_CONTRACT | MIXED_SCOPE
  proposal:
  owner_decision: pending | <choice> | n/a
OUT_OF_SCOPE_UNMERGED:
OWNER_DECISIONS_REQUIRED:
FINISH_OP: merge --continue | rebase --continue | none | abort
CONTRACT_RECHECK: not_run | ok | CONTRACT_BROKEN_AFTER_MERGE
CURRENT_STATE:
OWNER_DECISION_REQUIRED:
NEXT_ACTION:
DO_NOT_DO_YET:
```

### STATUS values

```text
PLAN_READY
RESOLVED
BLOCKED_OWNER
BLOCKED_MIXED_SCOPE
BLOCKED_NEEDS_EVIDENCE
CONTRACT_BROKEN_AFTER_MERGE
ABORTED_BY_OWNER
blocked_preflight_timeout
```

### Typical NEXT_ACTION

| STATUS | NEXT_ACTION |
|---|---|
| `PLAN_READY` (no owner gaps) | Reply: `GO` |
| `BLOCKED_OWNER` | Owner answers listed decisions, then `GO` |
| `BLOCKED_MIXED_SCOPE` | split/finish product conflicts first; re-run this command |
| `RESOLVED` | `/opsx-admin-command-commit` if dirty; else optional `/opsx-create-pr` |
| `CONTRACT_BROKEN_AFTER_MERGE` | `/opsx-admin-command-fix-command-defects` |
| `ABORTED_BY_OWNER` | operator chooses next branch action; not create-pr |

`DO_NOT_DO_YET` must include at least: push; force-push; admin-commit while
unmerged paths remain; create-pr while conflicted.

## Failure / recovery

| Condition | Behavior |
|---|---|
| No conflicts / not in merge|rebase | `PLAN_READY` or short no-op; redirect commit if dirty |
| Missing Owner choices | `BLOCKED_OWNER`; no writes |
| Product + process unmerged | `BLOCKED_MIXED_SCOPE`; no process apply |
| Continue fails | report git error; leave tree; do not force |
| Read timeout on required conflict file | `blocked_preflight_timeout` / `EVIDENCE_GAP` |

## Self-review checklist

- [ ] Process-only write scope respected
- [ ] No apply without `GO`
- [ ] No silent `AUTHORITY_TOKEN` ours/theirs
- [ ] No push / force-push / hard reset / clean -fd
- [ ] Unmerged paths cleared before claiming `RESOLVED`
- [ ] NEXT_ACTION pasteable and single
- [ ] admin-commit / fix-defects / create-pr not stolen
