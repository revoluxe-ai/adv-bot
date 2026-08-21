# /opsx-create-pr

Create a GitHub pull request — **publication and review container only**.
This command does **not** own product quality verification and does **not**
authorize merge/integration.

## Architectural invariant (mandatory)

```text
PR creation MUST NOT be blocked by absence, staleness, or failure of product
verification.

Allowed: create PR when verification=PENDING | FAIL | ABSENT.
Forbidden: require verify PASS, static-check receipt, tests/build/browser/
security/scenario PASS; requiring ledger COMPLETE; or archive readiness as a PR
precondition.
```

Merge/integration gates remain on `/opsx-verify`, `/opsx-archive`, CI, and
human merge approval — not here.

## Policy source

Before preparing or creating the PR, inspect when present:

- `openspec/policies/pr-context.md`

Read via `.cursor/commands/opsx-source-resolution.md`. Policy wins on conflict;
stop before PR if policy blocks publication for non-verification reasons.

## Purpose

Create a GitHub PR from the current branch:

- validate source/target branches and remote mechanics;
- push branch when `GO` is present (existing explicit contract);
- build Russian title/body from task intent and diff;
- return PR URL/identity;
- reference OpenSpec change/commits when available.

The PR explains the task — it does **not** certify quality or merge readiness.

## Verification boundary (mandatory)

This command **must not**:

- running or requiring `/opsx-static-check`, pytest, build, browser, security,
  scenario coverage, or `/opsx-verify`;
- requiring `PROJECT_BUG_HUNT_RECEIPT`, verification ledger, or archive PASS;
- blocking PR because verification is PENDING/FAIL/ABSENT.

Optional non-blocking PR body content:

- Owner-supplied test commands/results;
- `VERIFICATION: not evaluated by /opsx-create-pr`;
- links to existing artifacts — never invent PASS.

## Language

- PR title MUST be in Russian.
- PR body MUST be in Russian.
- Technical names, paths, branch names, commands, and change IDs may stay English.

## Required input

The user MUST provide:

- `Target/base branch`;
- `Task`.

The user MAY provide: `User PR context`, reviewer focus, OpenSpec change-id,
known risks, what must not change, related issue.

## Target branch rule

PR MUST have an explicitly provided target/base branch.

If missing, stop and ask:

```text
На какую target/base branch открыть PR?
```

Do not infer from `main`, `master`, current branch, memory, or repo default.

## GO rule

Push/create PR **only** when user input contains exact token `GO`.

Without `GO`: read-only plan — title, body, branch facts — no push, no PR, no
file edits.

## User PR context handling

1. Inspect commits and diff against target/base branch.
2. Compare `User PR context` with actual diff.
3. Build title/body from intent + diff + OpenSpec context.

If context conflicts with diff → stop and ask Owner before PR creation.

Do not create a generic PR when author intent is unclear.

## Hard stop conditions (publication safety only)

Stop before PR creation if:

- target/base branch is missing;
- current branch is unknown;
- current branch is `main`, `master`, `stage`, `prod`, or `production`;
- working tree has uncommitted changes (unless explicit contract allows otherwise);
- remote is not configured;
- `gh` CLI unavailable or not authenticated;
- target branch does not exist on origin;
- no commits ahead of target/base branch;
- open PR already exists for current branch;
- PR title/body would be generic or meaningless;
- `GO` is absent.

**Not** hard stops: verification PENDING/FAIL/ABSENT, missing static-check
receipt, missing bug-hunt receipt, incomplete verification ledger.

## Required read-only checks before PR

Follow `.cursor/commands/opsx-execution-preflight.md`.

```bash
git branch --show-current
git status --short
git remote -v
git log --oneline -10
git fetch --all --prune
git rev-parse --verify origin/<TARGET_BRANCH>
git diff --stat origin/<TARGET_BRANCH>...HEAD
git diff --name-only origin/<TARGET_BRANCH>...HEAD
git log --oneline origin/<TARGET_BRANCH>..HEAD
gh pr list --head "$(git branch --show-current)" --state open
gh auth status
```

## PR title rules

Describe behavior or intent, not files.

## PR body template

```md
## Цель

[Ожидаемое поведение после merge.]

## Контекст от автора

[User PR context или «Не указан».]

## Почему это нужно

[Проблема / требование.]

## Что изменено

- …

## Как это работает после изменения

[Краткий flow.]

## Что не должно измениться

- …

## Риски

- …

## Что проверить reviewer / Bugbot

- [Конкретные residual-риски для human/CI review — не quality gate этой команды]

## Проверки (информационно)

VERIFICATION: not evaluated by /opsx-create-pr

[Опционально: Owner-supplied команды/результаты без ложного PASS.]

## OpenSpec

- Change: [change-id или «нет»]
- Specs/tasks: [путь или «нет»]

## Статус интеграции

PR creation ≠ merge authorization. Integration gates: /opsx-verify, CI, Owner merge.
```

## Bugbot/reviewer focus

Section `## Что проверить reviewer / Bugbot` must be specific when Owner
provided focus or diff implies concrete risks. This is guidance for reviewers,
not a command-owned quality gate.

## PR creation flow

**Without `GO`:** validate inputs → read-only checks → title/body plan → wait.

**With `GO`:** validate → read-only checks → confirm title/body → write body
file → `git push -u origin <branch>` → `gh pr create`.

## Commands after explicit GO only

```bash
CURRENT_BRANCH="$(git branch --show-current)"

cat > /tmp/pr_body.md <<'EOF'
<FINAL_PR_BODY>
EOF

git push -u origin "$CURRENT_BRANCH"

gh pr create \
  --base "<TARGET_BRANCH>" \
  --head "$CURRENT_BRANCH" \
  --title "<PR_TITLE>" \
  --body-file /tmp/pr_body.md
```

Do not push or `gh pr create` before `GO`. No force-push unless Owner
explicitly authorizes.

## Output format before GO

1. Target/base branch
2. Current/head branch
3. Commits to include
4. Changed files
5. User PR context
6. Diff/context conflicts
7. PR title
8. PR body
9. Waiting for GO

## Output format after PR creation

1. PR URL
2. Target/base branch
3. Head branch
4. PR title
5. Next recommended action (optional `/opsx-verify`, `/opsx-project-bug-hunt`,
   `/opsx-static-check` — **not** prerequisites for this PR)
