# PR Context Policy

## Purpose

Every PR must explain the intended change, not only list changed files.

The PR description is context for human review, CI review, and Bugbot review.

## Required PR language

PR title and body MUST be written in Russian.

Technical names, commands, file paths, enum names, test names, branch names and OpenSpec change IDs may stay in English.

## Required target branch

A PR MUST have an explicitly provided target/base branch.

If target branch is missing, stop and ask the user:

"На какую target/base branch открыть PR?"

Do not infer the target branch from `main`, `master`, current branch, previous PRs, or memory.

## Required PR body

Every PR body MUST include:

1. Цель изменения
2. Почему это нужно
3. Что изменено
4. Как это работает после изменения
5. Что не должно измениться
6. Риски
7. Что проверить Bugbot / reviewer
8. Тесты и проверки
9. OpenSpec change/spec/tasks, если есть

## Bugbot context rule

The PR must describe the desired behavior and review risks.

Bad:
- "Fixed tests"
- "Updated files"
- "Refactor"

Good:
- "Цель: сохранить неизменным campaign.bot_active при открытии paid landing."
- "Bugbot/reviewer: проверь, что landing не активирует paid automation и не меняет состояние кампании."
- "Не должно измениться: existing activation flow, invite checks, campaign menu navigation."

## Forbidden shortcuts

Do not create PR if:

- target/base branch is missing;
- current branch is unknown;
- current branch is `main`, `master`, `stage`, or production branch;
- there are uncommitted changes not explicitly approved;
- tests were not run and this is not stated clearly;
- PR body only describes files, not intent;
- PR body is in English.

## Rule

A PR is not a changelog.

A PR is a review contract: what behavior must be true after merge, why it matters, and what risks the reviewer/Bugbot must inspect.
