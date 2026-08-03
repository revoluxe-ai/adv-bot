# /opsx-split-for-pr

Split an oversized diff into reviewable PR-sized parts and prepare handoff prompts for `/opsx-create-pr`.

This is a local WB Sky OpenSpec workflow command.
It is not an upstream OpenSpec command.

## Purpose

Use this command when the current branch contains a diff that is too large, too mixed, or too risky for one PR.

The command MUST:

- compare the current work against an explicitly provided target/base branch;
- create a temporary split plan artifact;
- split by behavioral boundaries, not by file count;
- preserve traceability from the original oversized diff to child branches/PRs;
- prepare exact `/opsx-create-pr` prompts for each child PR;
- NOT create PRs itself.

PR creation is delegated to `/opsx-create-pr`.

## Usage

```text
/opsx-split-for-pr target=<TARGET_BRANCH>
/opsx-split-for-pr:GO target=<TARGET_BRANCH>
/opsx-split-for-pr:STATUS
/opsx-split-for-pr:DONE
```

Examples:

```text
/opsx-split-for-pr target=customize-openspec
/opsx-split-for-pr:GO target=customize-openspec
```

## Required input

Planning and GO modes require:

- `target=<TARGET_BRANCH>`

If target is missing, stop and ask exactly:

```text
На какую target/base branch делим diff?
```

Do not infer target branch from:

- `main`;
- `master`;
- current branch;
- previous PRs;
- memory;
- repository default branch.

## Modes

### `/opsx-split-for-pr target=<TARGET_BRANCH>`

Read-only planning mode.

MUST NOT edit files.
MUST NOT create branches.
MUST NOT commit.
MUST NOT push.
MUST NOT open PRs.

MUST inspect current branch, target branch, commits, and diff.
MUST output a split plan and proposed plan artifact path.

### `/opsx-split-for-pr:GO target=<TARGET_BRANCH>`

Execution mode.

Allowed only after the user accepted the split plan.

MUST create or update the split plan artifact before changing git state.
MUST create child branches and commits according to the accepted plan.
MUST NOT push.
MUST NOT open PRs.
MUST output `/opsx-create-pr` prompts for each child PR.

### `/opsx-split-for-pr:STATUS`

Status mode.

MUST read the split plan artifact.
MUST compare planned PR parts against current branches, commits, and PR links if present.
MUST report what is done, what is missing, and what is unsafe to continue.

### `/opsx-split-for-pr:DONE`

Closure mode.

Allowed only when every planned child PR exists and is linked in the plan artifact.

MUST verify:

- every planned part has a branch;
- every planned part has a PR link or explicit user-approved reason for no PR;
- no planned part is still marked `todo` or `in_progress`;
- original oversized diff is fully accounted for;
- no unrelated residual diff remains.

Then and only then MAY delete the split plan artifact.

## Target/base branch rules

The provided `target=<TARGET_BRANCH>` is the root base branch.

For independent PRs:

- each child PR base branch MUST be `<TARGET_BRANCH>`.

For stacked PRs:

- PR 1 base branch MUST be `<TARGET_BRANCH>`;
- PR 2 base branch SHOULD be PR 1 branch;
- PR 3 base branch SHOULD be PR 2 branch;
- and so on.

The split plan MUST explicitly show the base branch for every child PR.

## Required read-only checks

Follow `.cursor/commands/opsx-execution-preflight.md` and `.cursor/commands/opsx-source-resolution.md`.

Git ops are **REQUIRED_FOR** split planning, but must be budgeted.

```text
TIME_BUDGET: local git 5–15s each; fetch 30s; on timeout → blocked_preflight_timeout
SKIP_IF: never for core branch/diff facts; skip find inventories when change-id/plan path known
```

Run first (local before remote):

```bash
git branch --show-current
git status --short
git remote -v
git rev-parse --verify origin/<TARGET_BRANCH>
git diff --stat origin/<TARGET_BRANCH>...HEAD
git diff --name-status origin/<TARGET_BRANCH>...HEAD
git log --oneline origin/<TARGET_BRANCH>..HEAD
git log --oneline -12
```

`git fetch --all --prune` only when remote refs are stale or `origin/<TARGET_BRANCH>` is missing locally (`REQUIRED_FOR` remote freshness).

If repository has OpenSpec / Cursor / GitHub process artifacts and an exact change-id or plan path is **not** known, use bounded fallback (`SEARCH_BUDGET <= 3`) instead of full-tree inventory. Prefer:

```text
openspec/changes/<change-id>/...
```

when the change id is known.

Do **not** default to unbounded:

```bash
find openspec -maxdepth 4 -type f | sort
find .cursor -maxdepth 4 -type f | sort
find .github -maxdepth 4 -type f | sort
```

## Split plan artifact

Use this default path unless the repository already has a better worklog directory:

```text
.cursor/worklogs/split-for-pr/<YYYY-MM-DD>-<short-topic>.md
```

If `.cursor/worklogs/` does not exist, ask before creating it unless mode is `:GO`.

The artifact is temporary.

Default behavior:

- create/update locally;
- do not commit the artifact;
- delete it only in `/opsx-split-for-pr:DONE`.

The artifact MAY be committed only if the user explicitly asks to track the split plan in git.

## Split plan template

```markdown
# Split for PR Plan: <topic>

## Source

- original branch:
- root target/base branch:
- created at:
- owner:
- reason for split:
- OpenSpec change-id:

## Original diff snapshot

- comparison: `origin/<TARGET_BRANCH>...HEAD`
- `git diff --stat` summary:
- risky files:
- unrelated files suspected:

## Split strategy

- mode: independent / stacked / mixed
- dependency order:
- why this split is safe:

## PR parts

### PR 1: <Russian PR title draft>

- status: todo / in_progress / branch_created / pr_prompt_ready / pr_opened / merged / skipped
- branch:
- base branch:
- PR link:
- objective:
- files:
- behavior change: yes/no
- tests:
- verification command:
- depends on:
- safe to merge alone: yes/no
- rollback note:
- `/opsx-create-pr` prompt: not_ready / ready

### PR 2: <Russian PR title draft>

- status:
- branch:
- base branch:
- PR link:
- objective:
- files:
- behavior change:
- tests:
- verification command:
- depends on:
- safe to merge alone:
- rollback note:
- `/opsx-create-pr` prompt:

## Residual diff tracking

- files intentionally left for later:
- files explicitly excluded:
- files that must not be included:
- unresolved conflicts:
- open questions:

## PR handoff prompts

### Create PR prompt for PR 1

```text
/opsx-create-pr

Target/base branch: <BASE_BRANCH>
Task:
<task>

User PR context:
<context>

Bugbot/reviewer focus:
<focus>

OpenSpec change-id:
<change-id or нет>

Tests:
<tests>

Known risks:
<risks>

What must not change:
<invariants>
```

### Create PR prompt for PR 2

```text
/opsx-create-pr

Target/base branch: <BASE_BRANCH>
Task:
<task>

User PR context:
<context>

Bugbot/reviewer focus:
<focus>

OpenSpec change-id:
<change-id or нет>

Tests:
<tests>

Known risks:
<risks>

What must not change:
<invariants>
```

## Completion checklist

- [ ] Target/base branch is explicit.
- [ ] Every file from the original diff is assigned to exactly one PR part or explicitly excluded.
- [ ] Each PR has one reviewable objective.
- [ ] Each behavior-changing PR has a regression test.
- [ ] Each PR has a verification command.
- [ ] Stacked PR bases are explicit.
- [ ] `/opsx-create-pr` prompt exists for every child PR.
- [ ] PR links are filled in after PR creation.
- [ ] Original oversized diff has no untracked leftover.
- [ ] Plan artifact can be deleted.
```

## Planning rules

Group changes by behavioral boundary, not by file count.

Prefer this order:

1. Mechanical refactor with no behavior change.
2. Test fixtures or test harness improvements.
3. Core behavior change.
4. UI/API/Excel/Telegram boundary changes.
5. Cleanup/docs/OpenSpec archive.

A PR is too large if it cannot be explained in one sentence.

A PR is invalid if it mixes:

- refactor and behavior change without reason;
- DB migration and unrelated logic;
- UI text and campaign state logic;
- paid/free boundary and unrelated cleanup;
- test-only scaffolding and production behavior;
- OpenSpec archive and active implementation.

## Execution rules for `:GO`

Before changing branches:

```bash
git branch backup/big-diff-before-split
git status --short
git diff --stat origin/<TARGET_BRANCH>...HEAD
git diff --name-status origin/<TARGET_BRANCH>...HEAD
```

MUST NOT continue if working tree contains untracked files that are not classified in the plan.

MUST use interactive staging when splitting existing diff:

```bash
git add -p
```

MAY use path-based staging only when the whole file belongs to exactly one PR part:

```bash
git add <path>
```

MUST commit each PR part separately with a clear message.

For independent PRs:

```bash
git switch -c split/<topic>-part-1 origin/<TARGET_BRANCH>
```

For stacked PRs:

```bash
git switch -c split/<topic>-part-2 split/<topic>-part-1
```

After each part:

```bash
git status --short
git diff --stat origin/<TARGET_BRANCH>...HEAD
git diff --cached --stat
```

## PR creation delegation

This command MUST NOT push or create PRs.

After each child branch is prepared, output a ready-to-copy prompt for `/opsx-create-pr`.

For independent PRs, use:

```text
Target/base branch: <TARGET_BRANCH>
```

For stacked PRs, use:

```text
Target/base branch: <previous_child_branch>
```

The prompt MUST explain:

- what this specific child PR does;
- why it exists as a separate PR;
- what changed;
- what must not change;
- what Bugbot/reviewer should inspect;
- tests and verification commands;
- known risks;
- OpenSpec change-id if present.

Do not include `GO` in the generated `/opsx-create-pr` prompt unless the user explicitly asked to create PRs immediately.

## Required output

For planning mode, output:

```text
Verdict: split / do_not_split / need_more_info

Target/base branch:
Plan artifact:
- path:
- should be committed: yes/no

Split:
1. PR title:
   type:
   branch:
   base:
   files:
   tests:
   risk:
   depends on:
   create-pr prompt ready: yes/no

Commands:
- read-only commands already run:
- proposed execution commands:

Stop conditions:
- ...
```

For `:GO`, output:

```text
Done:
- plan artifact:
- branches created:
- commits created:
- remaining diff:

Create PR handoff:
1. Branch:
   Base:
   Prompt for /opsx-create-pr:
   ...

Next:
- run /opsx-create-pr per branch;
- update plan artifact with PR links;
- run /opsx-split-for-pr:STATUS;
- run /opsx-split-for-pr:DONE only after all PRs are linked.
```

For `:STATUS`, output:

```text
Status:
- root target/base branch:
- completed parts:
- missing branches:
- missing PR links:
- residual diff:
- unsafe items:

Next action:
```

For `:DONE`, output:

```text
Closure:
- all PR links verified:
- residual diff:
- artifact deleted: yes/no
- reason if not deleted:
```

## Stop conditions

Stop immediately and ask the user if:

- target/base branch is missing;
- target/base branch does not exist on origin;
- current branch is `main`, `master`, `stage`, `prod`, or `production`;
- current branch is unknown;
- working tree contains untracked files not classified in the plan;
- diff includes migrations;
- diff includes secrets;
- diff includes production/deploy/k8s/CI changes;
- split requires force push;
- tests fail before any split work;
- a file cannot be assigned to one PR part;
- plan artifact conflicts with existing worklog policy;
- working tree has unmerged paths or merge|rebase is in progress
  → `NEXT_ACTION: /opsx-admin-command-resolve-conflicts` (process surfaces)
  or stop for product-only conflicts; do not split while conflicted.

## Forbidden shortcuts

MUST NOT say “split by files” without explaining behavioral boundaries.
MUST NOT create a PR part without tests or explicit reason why tests are not applicable.
MUST NOT delete the split plan artifact before all PR links are recorded.
MUST NOT treat “branch created” as “PR completed”.
MUST NOT hide leftover diff.
MUST NOT push.
MUST NOT open PRs.
MUST NOT merge.
MUST NOT rebase.
MUST NOT force-push.
MUST NOT include `GO` in `/opsx-create-pr` handoff prompts unless explicitly requested by the user.
