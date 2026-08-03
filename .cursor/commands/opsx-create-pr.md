# /opsx-create-pr

Create a GitHub pull request with a Russian PR title and body.

This is a local WB Sky OpenSpec workflow command.
It is not an upstream OpenSpec command.

## Policy source

Before preparing or creating the PR, inspect and follow:

- `openspec/policies/pr-context.md`

Read that exact path directly (`.cursor/commands/opsx-source-resolution.md`). Do not search the repo to rediscover the policy when the path is known.
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
- what Bugbot/reviewer should inspect (**residual** only — see project hunt gate);
- how the change was verified.

## Project bug-hunt gate (pre-Bugbot)

External Bugbot is a **residual** safety net. Primary discovery for product /
behavioral diffs belongs to `/opsx-project-bug-hunt`.

Before preparing or creating a PR that changes product/runtime behavior
(not pure docs/process-only):

1. Prefer a same-chat or pasted `PROJECT_BUG_HUNT_RECEIPT` from
   `/opsx-project-bug-hunt` for this `base..head` (target/base = PR base,
   head = current branch tip).
2. If the receipt is missing:
   - do **not** push/create the PR even when `GO` is present;
   - set pasteable `NEXT_ACTION` to
     `/opsx-project-bug-hunt base=<target> head=<current-branch> …`;
   - allow skip only when the user message contains the exact token
     `OVERRIDE_SKIP_PROJECT_BUG_HUNT` (record that override in the PR body
     risks section).
3. Pure process/docs PRs (only `.cursor/**`, `docs/**`, `openspec/**` with no
   `app/` / `tests/` product runtime) may omit the receipt.
4. In `## Что проверить Bugbot / reviewer`, list only **residual** risks the
   project hunt marked unclear / low-risk / out-of-budget — not a full first-pass
   audit dump.

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
- `GO` is absent;
- working tree has unmerged paths (`UU` / `AA` / …) or merge|rebase is in
  progress — especially on process surfaces
  (`.cursor/commands/**`, rules, skills, mirrors, …):
  set `NEXT_ACTION: /opsx-admin-command-resolve-conflicts` and do not open a PR.

## Required read-only checks before PR

Follow `.cursor/commands/opsx-execution-preflight.md`.

Git ops below are typically **REQUIRED_FOR** PR creation. Still apply TIME_BUDGET and FAILURE_BEHAVIOR; never hang silently.

```text
TIME_BUDGET: branch/status 5s/10s; log 10s; fetch 30s; diff/log vs target 15s; gh 20s
FAILURE_BEHAVIOR: blocked_preflight_timeout or stop with named missing fact; no retry loop
```

Preferred order — local facts first; remote only when needed:

```bash
git branch --show-current
git status --short
git remote -v
git log --oneline -10
```

Check target branch (REQUIRED_FOR base validation):

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

Skip or defer any step whose result is already known from a fresh prior receipt in the same invocation.
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
2. Enforce **Project bug-hunt gate** (receipt or
   `OVERRIDE_SKIP_PROJECT_BUG_HUNT` or process/docs-only exception).
3. Run all required checks again.
4. Rebuild/confirm PR title and body.
5. Write PR body to a temporary file.
6. Push current branch.
7. Create PR with `gh pr create`.
8. Run **Post-PR Bugbot report** (below) unless noted escapes.
9. Emit final output including dual-channel `BUGBOT_POST_PR`.

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

## Post-PR Bugbot report (mandatory after successful create)

Runs **only** after a successful `gh pr create` that returned a PR URL/number.
Does **not** replace `/opsx-project-bug-hunt` (pre-PR primary). Does **not**
auto-fix findings.

Two **different channels** must not be collapsed into one silent zero:

| Channel | What it is |
|---|---|
| `cursor_task` | One in-chat Cursor Task (`subagent_type: bugbot`) on branch diff vs PR base |
| `github_cursor_bot` | Review/issue comments posted on the PR by GitHub user `cursor[bot]` |

`cursor_task` alone is **not** authority that GitHub Bugbot is empty.
A thin chat reply «Bugbot found no bugs» while PR UI shows findings is a
contract failure of the report shape — fix the report, do not tell Owner
«0 findings» without a `github_cursor_bot` status.

Does **not** treat unbounded waiting on GitHub CI as a substitute for
`cursor_task`. Bounded fetch of already-posted `cursor[bot]` comments is
required (see below).

### Escape: `SKIP_BUGBOT_POST_PR`

If user `GO` message contains the exact token `SKIP_BUGBOT_POST_PR`,
skip the Cursor Task **and** skip GitHub fetch; emit:

```text
BUGBOT_POST_PR:
- cursor_task:
  - invoked: no
  - ran: n/a
  - findings_count: n/a
  - findings_envelope: n/a
  - skip_reason: SKIP_BUGBOT_POST_PR
- github_cursor_bot:
  - status: skipped
  - findings_count: n/a
  - skip_reason: SKIP_BUGBOT_POST_PR
```

### Otherwise (default)

1. Launch **exactly one** Task with:
   - `subagent_type: bugbot`
   - `description: "Bugbot"`
   - `run_in_background: false`
   - prompt shape (Cursor `review-bugbot` skill contract):

```text
Full Repository Path: <absolute workspace / repo root>
Diff: branch changes
Base Branch: <PR target/base branch>
```

2. Retry policy: follow `review-bugbot` (one retry on bad invocation; one
   natural-language Diff fallback only if diff could not be computed; then stop).
3. Classify `cursor_task.findings_envelope`:
   - `complete` — reply includes usable Severity | Location | Finding rows
     (or an explicit empty table / «none» with structured fields);
   - `incomplete` — prose-only empty claim (e.g. «Bugbot found no bugs»)
     without that table shape → **must not** be presented as definitive
     empty without `github_cursor_bot` status.
4. **Bounded GitHub `cursor[bot]` fetch** (required; not a CI wait loop):
   - TIME_BUDGET: ≤60s total; at most **2** attempts; sleep ≤15s between
     attempts if first returns no comments;
   - Prefer: `gh api` pull review comments + issue comments / reviews for
     the new PR number, filter `user.login == cursor[bot]` (or equivalent);
   - Map each finding to Severity | Location | Finding when parseable;
   - Status values:
     - `findings` — ≥1 comment/finding mapped (`findings_count` = N);
     - `pending` — PR exists, no `cursor[bot]` comments yet after attempts
       (**not** the same as zero findings);
     - `unavailable` — `gh`/API error or auth gap (record short `error`);
     - `skipped` — only with `SKIP_BUGBOT_POST_PR`.
5. Emit in the create-pr reply (before product-fix handoffs):

```text
BUGBOT_POST_PR:
- cursor_task:
  - invoked: yes
  - ran: yes | no | failed
  - findings_count: <N or n/a>
  - findings_envelope: complete | incomplete | n/a
  - findings: none | <markdown table Severity | Location | Finding>
  - error: <short blocker if ran=failed; else omit>
- github_cursor_bot:
  - status: findings | pending | unavailable | skipped
  - findings_count: <N or n/a>
  - findings: none | <markdown table Severity | Location | Finding>
  - error: <short blocker if unavailable; else omit>
```

Priority of the report for the owner:

1. Were **both** channels reported? (`cursor_task` + `github_cursor_bot`)
2. Did Cursor Task run? (`cursor_task.invoked` / `ran` / `findings_envelope`)
3. What does GitHub `cursor[bot]` show? (`github_cursor_bot.status` / count)
4. Tables for whichever channel has findings — do not invent rows.

Do not invent findings. Do not open a second Bugbot Task in the same create-pr
turn after a completed `cursor_task` report. Do not claim «0 Bugbot findings»
when `github_cursor_bot.status=pending` or `unavailable`, or when
`cursor_task.findings_envelope=incomplete` and GitHub was not fetched.

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
6. BUGBOT_POST_PR: (dual-channel `cursor_task` + `github_cursor_bot`)
7. Next recommended action:
