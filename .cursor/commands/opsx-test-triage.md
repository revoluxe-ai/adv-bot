# /opsx-test-triage

This is a local WB Sky OpenSpec workflow command.
It is not an upstream OpenSpec command.

Diagnose failing tests before any fix.

## Purpose

This command only analyzes why tests failed.

Do not edit files.
Do not fix code.
Do not fix tests.
Do not commit.
Do not update snapshots.
Do not weaken assertions.

First classify the failure and produce a copy-pasteable NEXT PROMPT.

## Type-check routing

If the failure packet is `pyright` / `pyright-strict` / `mypy` diagnostics (not a pytest assertion failure) — do **not** classify it with the pytest taxonomy below.

Return immediately:

```text
NEXT_ACTION: /opsx-fix-types
```

Owner command: `.cursor/commands/opsx-fix-types.md`.

## Policy source

Before triage, inspect and follow:

- `openspec/policies/test-triage.md`

Read that exact path directly (`.cursor/commands/opsx-source-resolution.md`). If failing test paths are provided, open those exact paths first; do not inventory all tests to rediscover them.
If this policy file exists, treat it as the source of truth for test failure classification rules.

If the command and policy conflict:
- follow `openspec/policies/test-triage.md`;
- mention the conflict in the response;
- do not modify files.

## Language

- Final response MUST be in Russian.
- Keep classification enum values in English.
- Be concise and strict.

## Classification

Classify the failure as exactly one:

- CODE_BUG: production code is wrong.
- TEST_OBSOLETE: test is outdated because accepted behavior changed.
- SPEC_CHANGED_BUT_NOT_UPDATED: behavior changed but OpenSpec/spec/tasks were not updated.
- BAD_TEST: test checks the wrong thing or does not catch the real regression.
- FLAKY_OR_ENV: async/env/timing/db/redis/clickhouse/order problem.
  Connection refused / missing laptop services on `5433`|`8124`|`6390` →
  NEXT `/opsx-test-env UP` (pytest session `REDIS_PORT=6390`; not `/opsx-devops`).
  Host `:6379` is out of test-compose scope.
- AMBIGUOUS: not enough evidence.

## Required work

1. Find the failing test.
2. Find the exact assertion/error.
3. Explain what behavior the test protects.
4. Compare:
   - test expectation;
   - current code behavior;
   - recent diff;
   - OpenSpec/spec/tasks, if provided.
5. Decide what is wrong: code, test, spec, env, or evidence.
6. Do not fix anything yet.

## Output format

1. Вердикт:
2. Упавший тест:
3. Команда, которая упала:
4. Что тест защищает:
5. Использованная policy:
6. Доказательства:
7. Классификация:
8. Риск:
9. Минимальное следующее действие:
10. Что нельзя делать:

11. Prompt для следующего агента:

[BEGIN NEXT PROMPT]
Задача:
[точное действие после triage]

Triage verdict:
[CODE_BUG / TEST_OBSOLETE / SPEC_CHANGED_BUT_NOT_UPDATED / BAD_TEST / FLAKY_OR_ENV / AMBIGUOUS]

Evidence:
[доказательства]

Allowed files:
[какие файлы можно менять]

Forbidden actions:
- no unrelated changes
- no commit/push/deploy without GO
- no weakening assertions
- no snapshot update without explanation
- no DB/migration/infra changes unless explicitly approved

Required behavior:
[что должно быть верно после фикса]

Required tests:
[какие тесты добавить/исправить/запустить]

Verification commands:
[команды проверки]

Stop conditions:
- stop if evidence contradicts the triage verdict
- stop if affected scope expands
- stop if DB/infra/paid boundary/campaign state risk appears unexpectedly
[END NEXT PROMPT]

11. Команда проверки:


## Continuation from `/opsx-commit` or Supervisor (mandatory)

When invoked after `COMMIT_STOP` / `PARTIAL` with `WHY=test_fail` or when
Supervisor forwards an upstream handoff:

1. Accept `ERROR_SUMMARY`, nodeids, and `STAGED_HITS` from the handoff as
   **primary evidence** — do not re-run full pytest discovery if diagnostics
   are already present.
2. Classify per policy (`openspec/policies/test-triage.md`).
3. Emit `[BEGIN NEXT PROMPT]` for the implementation agent:
   - `CODE_BUG` / `TEST_OBSOLETE` / `BAD_TEST` → `/opsx-test` (scoped write)
   - typing diagnostics in handoff → `/opsx-fix-types` (see Type-check routing)
4. Do **not** route to `/opsx-bug-team` from triage unless triage explicitly
   maps to bug-episode lifecycle (rare; see Orchestration RED mapping below).

If handoff is ambiguous (missing nodeids, contradictory WHY), return
classification `AMBIGUOUS` and recommend Owner run `/opsx-admin-command-consult`
or `/opsx-pipeline NAVIGATE` before fix.


## Orchestration RED status mapping (light)

When triage feeds a bug-episode RED path, map classes:

| Triage class | Typical RED / next |
|---|---|
| CODE_BUG | continue RED authoring toward `RED_CONFIRMED` |
| BAD_TEST / wrong assertion | `RED_WRONG_REASON` or rewrite test via `/opsx-test` |
| FLAKY_OR_ENV / setup | `TEST_SETUP_DEFECT` / `BLOCKED`; if PG/CH/Redis ports → `/opsx-test-env UP` |
| TEST_OBSOLETE | do not force production GO |

Do **not** emit production GO from triage.
