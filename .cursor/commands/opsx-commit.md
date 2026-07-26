---
description: "Atomic local commits for product/code/OpenSpec/docs. Process surfaces (commands/rules/skills) redirect to /opsx-admin-command-commit."
argument-hint: "GO [optional OpenSpec change-id / context]"
---

# /opsx-commit

You are allowed to create local git commits ONLY when the user input contains the exact token `GO`.

If `GO` is absent:
- do not modify files;
- do not stage files;
- do not commit;
- output only the proposed commit plan.

Never push, merge, rebase, force-push, deploy, restart services, run migrations against production, or touch secrets.

## User input

```text
$ARGUMENTS
```

## Purpose

Analyze the current working tree and create safe atomic local commits by logical zones
for **product/code/OpenSpec/docs** changes.

Process surfaces (commands, rules, skills, prompt/skill mirrors) are **out of scope**.
They belong exclusively to `/opsx-admin-command-commit`.

**Source resolution:** Follow `.cursor/commands/opsx-source-resolution.md`. If an OpenSpec change-id is provided or exactly one `openspec/changes/<id>/` is touched, read that change via canonical paths only; do not inventory all changes.

## Process-surface exclusion (mandatory)

Never stage or commit these paths; leave them untouched and redirect:

```text
.cursor/commands/**
.cursor/rules/**
.cursor/skills/**
.cursor/opsx-review-commands
.github/skills/**
.github/prompts/**
.agents/skills/**
```

If any of these are dirty:

```text
OUT_OF_SCOPE_REDIRECT:
NEXT_ACTION: /opsx-admin-command-commit
```

If the dirty tree is **only** process surfaces, do not invent product commits:

```text
STATUS: OUT_OF_SCOPE_REDIRECT
NEXT_ACTION: /opsx-admin-command-commit
DO_NOT_DO_YET: commit process files via /opsx-commit
```

Commit subjects MUST be in English with a short Russian explanation in parentheses:

```text
type(scope): English summary (русское пояснение)
```

Commit bodies MUST be detailed and useful for review:
- what changed;
- why it changed;
- how it was verified;
- OpenSpec change-id, if detected;
- risk notes, if any.

Primary body text should be English. Russian may appear in parentheses for clarity.

## Mandatory preflight

Follow `.cursor/commands/opsx-execution-preflight.md`.

These git ops are **REQUIRED_FOR** commit planning (branch protection + change inventory). Apply budgets; on timeout return `blocked_preflight_timeout` rather than hanging.

```text
OPERATION_REASON: atomic commit plan + protected-branch gate
REQUIRED_FOR: commit decision
SKIP_IF: never for /opsx-commit when GO path is taken (preview may use status/diff only)
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

Do not run `git fetch` here unless remote state becomes REQUIRED_FOR.
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

## Detect OpenSpec change

Inspect changed OpenSpec files:

```powershell
Get-ChildItem -Path .\openspec\changes -Recurse -File -Depth 2 |
  Sort-Object FullName |
  ForEach-Object { $_.FullName }
```

If exactly one `openspec/changes/<change-id>/` is touched, use that as the OpenSpec change-id.

If the user provided a change-id in `$ARGUMENTS`, prefer it.

If multiple change-ids are touched:
- do not commit automatically;
- output the split plan;
- ask the user to rerun with the exact change-id.

When available, read:

```text
openspec/changes/<change-id>/proposal.md
openspec/changes/<change-id>/design.md
openspec/changes/<change-id>/tasks.md
openspec/changes/<change-id>/specs/**/*.md
```

Use these files to detect unrelated changes.

## Classification zones

Classify every **in-scope** changed file into one zone.
Process-surface paths listed above are never classified here — report redirect only.

```text
1. openspec-specs
2. db-models-migrations
3. domain-business-logic
4. bot-ui-callbacks-messages
5. async-jobs-workers
6. tests
7. docs
8. ci-infra
9. unrelated-or-suspicious
```

Zone `docs` means ordinary project documentation only.
It does **not** include `.cursor/commands/**`, `.cursor/skills/**`, `.cursor/rules/**`,
`.github/prompts/**`, `.github/skills/**`, or `.agents/skills/**`.

## Automatic commit grouping

Create commits in this preferred order:

```text
1. spec(openspec)
2. db/models/migrations
3. domain/business logic
4. bot UI/callbacks/messages
5. async jobs/workers
6. tests
7. docs
8. chore/cleanup
```

Do not include `unrelated-or-suspicious` files in any automatic commit.
Do not include process-surface files in any automatic commit.

If suspicious files exist:
- leave them unstaged;
- report them at the end.

## Staging rules

Prefer whole-file staging when all changes in the file belong to one logical group.

Use interactive patch staging when a file mixes zones:

```bash
git add -p <file>
```

If interactive staging is not practical in the current agent environment:
- do not stage that file;
- report it as `requires manual git add -p`;
- continue with safe whole-file commits only.

Before every commit, run:

```bash
git diff --cached --stat
git diff --cached --name-status
git diff --cached
```

If the staged diff contains unrelated changes, unstage and stop:

```bash
git restore --staged <file>
```

## Verification rules

For each commit group, infer focused verification commands.

Examples:

```bash
pytest path/to/test_file.py -q
pytest tests/path -q
```

If no focused test is obvious:
- commit is allowed;
- include `Verification: not run - no focused test inferred`;
- mark it in the final report.

If risky zones changed, strongly prefer tests before commit:
- campaign state;
- paid/free boundary;
- bid/cost/reallocation logic;
- DB model/migration behavior;
- async/concurrency;
- bot callbacks/messages.

These are high-risk WB Sky zones and must be visible in the final report.

## Commit message format

Use this subject format:

```text
type(scope): English summary (русское пояснение)
```

Allowed types:

```text
spec
feat
fix
refactor
test
docs
chore
ci
perf
```

Examples:

```text
spec(openspec): document invite partner rollout (описать запуск партнёрских инвайтов)
feat(invites): add invite activation flow (добавить поток активации инвайтов)
fix(campaigns): preserve bot_active on landing open (сохранить bot_active при открытии лендинга)
test(invites): cover invite activation regressions (покрыть регрессии активации инвайтов)
chore(docs): refresh contributor setup notes (обновить заметки по setup)
```

Use detailed body:

```text
What:
- ...

Why:
- ...

How:
- ...

Verification:
- ...

OpenSpec:
- change-id: ...

Risk:
- ...
```

Create commits with multiple `-m` arguments:

```bash
git commit \
  -m "type(scope): English summary (русское пояснение)" \
  -m "What:
- ...

Why:
- ...

How:
- ...

Verification:
- ...

OpenSpec:
- change-id: <change-id>

Risk:
- ..."
```

## Execution mode

If `GO` is absent, output only:

```text
Commit plan:
- proposed commits
- files per commit
- commands that would be run
- suspicious files
- tests to run
- process-surface files left for /opsx-admin-command-commit
```

If `GO` is present, execute the commit plan.

For each commit:
1. Stage files for that group.
2. Inspect staged diff.
3. Run focused verification if inferred.
4. Commit with detailed message.
5. Continue to next group.

If a verification command fails:
- stop immediately;
- do not commit the failing group;
- leave working tree as-is;
- report what failed.

If a group requires manual `git add -p`:
- skip that group;
- continue with safe groups;
- report skipped files.

## Final report

After execution, output:

```text
Done:
- commits created:

Skipped:
- files requiring manual add -p:
- suspicious/unrelated files:
- groups not committed:

OUT_OF_SCOPE_REDIRECT:
- process-surface files left for /opsx-admin-command-commit:

Verification:
- passed:
- failed:
- not run:

Next:
- if process surfaces remain dirty: /opsx-admin-command-commit
- recommended final verify command
- recommended PR command, but do not push
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
git checkout .
docker compose up
kubectl
alembic upgrade
alembic downgrade
```
