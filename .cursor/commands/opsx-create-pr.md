# /opsx-create-pr

Create a GitHub pull request with a Russian PR title and body.

This is a local WB Sky OpenSpec workflow command.
It is not an upstream OpenSpec command.

## Policy source

Before preparing or creating the PR, inspect and follow:

- `openspec/policies/pr-context.md`

If this policy file exists, treat it as the source of truth for PR context rules.

If this command and the policy conflict:

- follow `openspec/policies/pr-context.md`;
- mention the conflict;
- stop before creating the PR.

## Purpose

Create a GitHub PR from the current branch.

The PR must explain the task, not just the diff:

- what the user wanted to achieve;
- why the change is needed;
- what changed;
- how the behavior should work after merge;
- what must not change;
- what Bugbot/reviewer should inspect;
- how the change was verified.

## Language

- PR title MUST be in Russian.
- PR body MUST be in Russian.
- Technical names, file paths, branch names, commands, test names, enum names, and OpenSpec change IDs may stay in English.
- Avoid vague phrases.
- Do not write a PR that only lists changed files.

## Required input

The user MUST provide:

- `Target/base branch`;
- `Task`.

The user MAY provide:

- `User PR context`;
- `Bugbot/reviewer focus`;
- `OpenSpec change-id`;
- `Tests`;
- `Known risks`;
- `What must not change`;
- related issue/task.

## Target branch rule

A PR MUST have an explicitly provided target/base branch.

If target/base branch is missing, stop and ask exactly:

```text
На какую target/base branch открыть PR?
```

Do not infer target branch from:

- `main`;
- `master`;
- current branch;
- previous PRs;
- memory;
- repository default branch.

## GO rule

Creating a PR requires explicit user confirmation.

The PR may be pushed/created ONLY if the current user message contains the exact token:

```text
GO
```

If `GO` is absent:

- do not push;
- do not create PR;
- do not modify files;
- output only the proposed PR plan, title, and body.

## User PR context handling

The user may provide:

```text
User PR context:
[author explanation]
```

Use this as high-priority intent context.

Before preparing the PR:

1. Inspect commits and diff against target/base branch.
2. Compare `User PR context` with actual commits and diff.
3. Build the Russian PR title from:
   - user intent;
   - actual diff;
   - OpenSpec/change context, if present.
4. Build the Russian PR body from:
   - what the user wanted;
   - what actually changed;
   - why it matters;
   - how the behavior should work;
   - what Bugbot/reviewer must check.

If `User PR context` conflicts with actual diff:

- stop;
- explain the conflict;
- ask the user what to do before PR creation.

Do not create PR if author intent is unclear and PR body would become generic.

## Hard stop conditions

Stop before PR creation if:

- target/base branch is missing;
- current branch is unknown;
- current branch is `main`, `master`, `stage`, `prod`, or `production`;
- working tree has uncommitted changes;
- remote is not configured;
- `gh` CLI is unavailable;
- `gh` is not authenticated;
- target branch does not exist on origin;
- no commits exist ahead of target/base branch;
- an open PR already exists for the current branch;
- PR title/body would be generic or meaningless;
- `GO` is absent.

## Required read-only checks before PR

Run:

```bash
git branch --show-current
git status --short
git remote -v
git log --oneline -10
```

Check target branch:

```bash
git fetch --all --prune
git rev-parse --verify origin/<TARGET_BRANCH>
```

Inspect diff and commits:

```bash
git diff --stat origin/<TARGET_BRANCH>...HEAD
git diff --name-only origin/<TARGET_BRANCH>...HEAD
git log --oneline origin/<TARGET_BRANCH>..HEAD
```

Check existing PR:

```bash
gh pr list --head "$(git branch --show-current)" --state open
```

Check GitHub auth:

```bash
gh auth status
```

## PR title rules

Title must describe behavior or intent, not files.

Good examples:

- `Fix: лендинг paid больше не меняет bot_active кампании`
- `Tests: добавлена регрессия для inactive campaign gate`
- `Feature: добавлена проверка invite-доступа перед paid flow`
- `Refactor: упрощена навигация paid landing без изменения поведения`

Bad examples:

- `Fix tests`
- `Update handlers`
- `Changes`
- `PR`
- `Refactor code`

## PR body template

Use this template for the PR body:

```md
## Цель

[Какое поведение или результат должен появиться после merge.]

## Контекст от автора

[Если пользователь дал User PR context — кратко и точно перенести его сюда. Если не дал — написать "Не указан".]

## Почему это нужно

[Какая проблема была: баг, риск регрессии, недостающая проверка, изменение требования.]

## Что изменено

- [Пункт 1]
- [Пункт 2]
- [Пункт 3]

## Как это работает после изменения

[Кратко объяснить новый или исправленный flow.]

## Что не должно измениться

- [Инвариант 1]
- [Инвариант 2]
- [Существующий flow, который нельзя сломать]

## Риски

- [Риск 1]
- [Риск 2]

Если тесты не запускались или риск не проверен — написать прямо.

## Что проверить Bugbot / reviewer

- [Конкретный риск для проверки]
- [Hidden side effect]
- [Paid/free boundary, campaign state, async, DB, Redis, ClickHouse, callbacks, если затронуто]

## Тесты и проверки

```bash
[команда 1]
[команда 2]
```

Результат:

- [passed / failed / not run с причиной]

## OpenSpec

- Change: [change-id или "нет"]
- Specs/tasks: [путь или "нет"]
```

## Bugbot/reviewer focus rule

The section `## Что проверить Bugbot / reviewer` MUST be specific.

Bad:

- `Проверь код`
- `Посмотри PR`
- `Проверь тесты`

Good:

- `Проверь, что paid landing не меняет campaign.bot_active.`
- `Проверь, что free flow не получает доступ к paid automation.`
- `Проверь, что тест не мокает away реальный inactive gate.`
- `Проверь, что SQLAlchemy query не меняет cardinality и не грузит лишние relationships.`
- `Проверь, что callback flow не ломает старую навигацию.`

## PR creation flow

If `GO` is absent:

1. Validate that target/base branch was explicitly provided.
2. Run read-only checks.
3. Inspect commits and diff against target/base branch.
4. Compare user intent with actual diff.
5. Build Russian PR title.
6. Build Russian PR body.
7. Output the final title/body.
8. Stop and wait for `GO`.

If `GO` is present:

1. Validate that target/base branch was explicitly provided.
2. Run all required checks again.
3. Rebuild/confirm PR title and body.
4. Write PR body to a temporary file.
5. Push current branch.
6. Create PR with `gh pr create`.

## Commands after explicit GO only

After user says `GO`, run:

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

Do not run `git push` or `gh pr create` before explicit `GO`.

## Output format before GO

1. Target/base branch:
2. Current/head branch:
3. Commits to include:
4. Changed files:
5. User PR context:
6. Diff/context conflicts:
7. PR title:
8. PR body:
9. Tests:
10. Risks:
11. Waiting for GO:

## Output format after PR creation

1. PR created:
2. Target/base branch:
3. Head branch:
4. PR title:
5. PR URL:
6. Next recommended action:
