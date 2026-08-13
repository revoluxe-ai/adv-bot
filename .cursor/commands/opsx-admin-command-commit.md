---
description: "Propose and (with GO) create semantic local commits for AI/process artifacts (commands, rules, skills, agents, static-check, mirrors)."
argument-hint: "GO [optional topic hint]"
---

# /opsx-admin-command-commit

Exclusive owner of local commits for **AI / process surfaces** (Cursor/agent commands,
rules, skills, agents, static-check, prompt/skill mirrors, and root agent guides).

You are allowed to create local git commits ONLY when the user input contains the exact token `GO`.

If `GO` is absent:
- do not modify files;
- do not stage files;
- do not commit;
- output only the proposed commit plan.

Never push, merge, rebase, force-push, deploy, restart services, run migrations against production, or touch secrets.

Product/code/OpenSpec product commits belong to `/opsx-commit`, not this command.

## User input

```text
$ARGUMENTS
```

## Purpose

Analyze dirty **process-surface** files and create safe atomic local commits **by meaning**.

Two phases:

1. **Plan** (no `GO`) — group files, propose commit subjects/bodies, report redirects.
2. **Execute** (`GO`) — stage and commit approved in-scope groups only.

**Source resolution:** Follow `.cursor/commands/opsx-source-resolution.md`.
**Execution budgets:** Follow `.cursor/commands/opsx-execution-preflight.md` (git-mutating class).

## In-scope surfaces (exclusive)

Only these paths may be staged/committed by this command:

```text
.cursor/commands/**
.cursor/rules/**
.cursor/skills/**
.cursor/agents/**
.cursor/static-check/**
.cursor/pipeline/**
.cursor/antipattern-gate/**
.cursor/opsx-export/**
.cursor/opsx-review-commands
.agents/**
.github/skills/**
.github/prompts/**
.github/copilot-instructions.md
.github/git-commit-instructions.md
AGENTS.md
```

Shared OPSX process contracts that live under `.cursor/commands/` (for example
`opsx-execution-preflight.md`, `opsx-source-resolution.md`) are in scope.
Materialized operator pipeline graph under `.cursor/pipeline/` (from
`/opsx-pipeline UPDATE GO`) is in scope.
Static-check infra under `.cursor/static-check/` is in scope in full:
contracts, check packs, registry, base prompts/rules, **and** agent runner
scripts (e.g. `bin/run.sh`).
Antipattern-gate companions under `.cursor/antipattern-gate/` (catalog,
`PRACTICE_LEDGER.jsonl`, README) are in scope with `/opsx-antipattern-gate`.
OPSX export packer under `.cursor/opsx-export/` is in scope with
`/opsx-admin-command-export-bundle` (the zip artifacts under `.tmp/` are not).
All files under `.agents/**` (not only `skills/`) are in scope.

Everything else is **out of scope** for this command.

## Out of scope (redirect)

Never stage or commit:

- product/app/code
- tests
- DB/migrations
- CI/infra (including `.github/workflows/**`, except the surfaces listed above)
- local IDE prefs such as `.cursor/settings.json`
- archives / junk under `.cursor/` (e.g. `commands.zip`)
- portable OPSX export artifacts under `.tmp/opsx-export/` (produced by
  `/opsx-admin-command-export-bundle` — never commit those zips)
- `openspec/changes/**` product change packets
- ordinary project docs outside the surfaces above

If the operator needs a portable zip of OPSX trees (not a git commit):

```text
OUT_OF_SCOPE_REDIRECT:
NEXT_ACTION: /opsx-admin-command-export-bundle GO
```

If such (other) files are dirty:

```text
OUT_OF_SCOPE_REDIRECT:
NEXT_ACTION: /opsx-commit
```

Leave them untouched.

## Mandatory preflight

These git ops are **REQUIRED_FOR** commit planning (branch protection + inventory).
Apply budgets; on timeout return `blocked_preflight_timeout` rather than hanging.

```text
OPERATION_REASON: process-surface commit plan + protected-branch gate
REQUIRED_FOR: commit decision
SKIP_IF: never when GO path is taken (preview may use status/diff only)
TIME_BUDGET: branch 5s; status 10s; each diff 15s
FAILURE_BEHAVIOR: blocked_preflight_timeout / report missing fact; no retry loop
```

Run the smallest set that answers the need:

```bash
git branch --show-current
git status --short
git diff --stat
git diff --name-status
git diff --cached --stat
git diff --cached --name-status
```

Do not run `git fetch` unless remote state becomes REQUIRED_FOR.

### Unresolved conflicts hard gate (mandatory)

After `git status --short` (and before any `git add` / `git commit`), **stop**
with `STATUS: BLOCKED` / `WHY: unresolved_conflicts` if either condition holds:

1. **Unmerged paths** — porcelain status shows any unmerged index state
   (`UU`, `AA`, `DD`, `AU`, `UA`, `DU`, `UD`) or status text reports
   `Unmerged paths` / both-modified without resolution.
2. **Conflict markers** — any file in the current commit group (already staged
   or about to be staged) contains unresolved conflict marker lines
   (`<<<<<<<`, `=======`, `>>>>>>>`).

On hit:

- do **not** stage or commit;
- do **not** clear, edit, or invent resolution for conflict markers;
- leave resolution to the owner (or a separate fix command);
- include in the report:

```text
WHY: unresolved_conflicts
DO_NOT_DO_YET: clear/choose conflict markers inside /opsx-admin-command-commit; git add of unmerged paths; rebase/merge/cherry-pick --continue/--skip/--abort; push; force-push
```

Already-resolved paths (no unmerged state, no markers) may still be staged.

Block execution if current branch is:

```text
main
master
prod
production
```

unless the user input contains:

```text
GO_ON_PROTECTED_BRANCH
```

Even with `GO_ON_PROTECTED_BRANCH`, never push.

## Semantic grouping rules

Classify every **in-scope** changed file into meaning groups. Prefer fewer clear commits over noise, but never merge unrelated concerns.

Preferred grouping:

```text
1. one logical OPSX/Cursor command + its mirrors/companions
   (e.g. .cursor/commands/opsx-verify.md + .github/prompts/opsx-verify.prompt.md
    + matching skill copies that changed for the same intent)
2. admin-command family packet that was designed/fixed together
3. shared process contracts (preflight, source-resolution, review pointers)
   — separate commit if they changed independently
4. rules / AGENTS.md / github agent instruction files — separate if not tied
   to a single command change
5. agents skills/guides (.agents/**, .cursor/agents/**) — by intent
6. static-check infra (.cursor/static-check/**) — separate unless companion
   to the same disclosed packet
7. antipattern-gate companions (.cursor/antipattern-gate/**) — with the
   `/opsx-antipattern-gate` command packet when they change together
8. unrelated process edits — separate commits by concern
```

Do **not**:

- dump all `.cursor/commands/**` into one commit when intents differ;
- mix verify/apply/archive lifecycle edits with unrelated admin-tooling edits
  unless they are one disclosed companion packet;
- include out-of-scope files to “finish the tree”.

If a file mixes independent concerns and interactive staging is impractical:

- leave it unstaged;
- report `requires manual git add -p`;
- continue with safe whole-file groups.

## Staging rules

Prefer whole-file staging when the file belongs to one meaning group.

Before every commit:

```bash
git diff --cached --stat
git diff --cached --name-status
git diff --cached
```

If the staged diff contains out-of-scope or unrelated process changes, unstage and stop that group:

```bash
git restore --staged <file>
```

## Commit message format

Subjects MUST be English with a short Russian explanation in parentheses:

```text
type(scope): English summary (русское пояснение)
```

Preferred types for this command:

```text
docs
chore
fix
refactor
```

Preferred scopes:

```text
commands
rules
skills
agents
prompts
static-check
opsx-admin
opsx-process
```

Examples:

```text
chore(commands): split verify handoff contract (разделить контракт handoff verify)
fix(opsx-admin): clarify defect fix NEXT_ACTION (уточнить NEXT_ACTION после fix)
docs(skills): mirror openspec-apply skill updates (синхронизировать skill openspec-apply)
```

Body (English primary; Russian allowed in parentheses):

```text
What:
- ...

Why:
- ...

How:
- ...

Verification:
- ...

Risk:
- ...
```

Create commits with multiple `-m` arguments (same pattern as `/opsx-commit`).

## Verification rules

For process-only commits:

- focused automated tests are usually not inferred;
- commit is allowed with `Verification: not run - process contract change`;
- if the change claims a redirect/GO gate, do a quick Grep self-check that the
  named tokens exist in the touched files before committing that group.

## Execution mode

### No `GO` → plan only

```text
STATUS: PLAN_READY

Commit plan:
- proposed commits (subject + files + why this split)
- commands that would be run
- out-of-scope files (redirect to /opsx-commit)
- files requiring manual git add -p
- suspicious/unrelated process files

WHAT_HAPPENED:
WHY:
CURRENT_STATE:
OWNER_DECISION_REQUIRED: yes — accept plan or adjust groups
NEXT_ACTION: /opsx-admin-command-commit GO
DO_NOT_DO_YET: push; /opsx-commit for in-scope process files; mix product files into GO
```

### With `GO` → execute plan

For each in-scope group:

1. Stage files for that group only.
2. Inspect staged diff.
3. Optional Grep self-check when gate/redirect tokens are claimed.
4. Commit with detailed message.
5. Continue to next group.

If a group requires manual `git add -p`:
- skip that group;
- continue with safe groups;
- report skipped files.

Stop immediately on staging/commit failure; leave working tree as-is; report.

## Final report (after GO)

```text
STATUS: COMMITTED | PARTIAL | BLOCKED

Done:
- commits created:

Skipped:
- files requiring manual add -p:
- groups not committed:

OUT_OF_SCOPE_REDIRECT:
- files left for /opsx-commit:

Verification:
- passed:
- failed:
- not run:

WHAT_HAPPENED:
WHY:
CURRENT_STATE:
OWNER_DECISION_REQUIRED:
NEXT_ACTION:
- if product files remain dirty: /opsx-commit
- else optional: /opsx-create-pr (do not push)
DO_NOT_DO_YET: push; rebase; force-push
```

## Absolute prohibitions

Never run:

```bash
git push
git push --force
git rebase
git merge
git reset --hard
git clean -fd
```

Never commit paths outside the in-scope surfaces list.
Never re-decide product commit grouping for `/opsx-commit`.
