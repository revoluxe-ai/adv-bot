---
description: "Write targeted tests from the user's request without changing production code."
argument-hint: "<test request / bug / behavior> [optional OpenSpec change-id]"
---

# /opsx:test

Write or update targeted tests based on the user's request.

You are allowed to edit tests only.

User input:

```text
$ARGUMENTS
```

## Hard rules

- Do not modify production code.
- Do not modify OpenSpec artifacts unless the user explicitly asks.
- Do not commit, push, merge, rebase, deploy, restart services, touch secrets, run migrations, or change Kubernetes/CI.
- If the requested test cannot be written without changing production code, stop and explain the smallest required production seam/change. Do not implement it.
- Prefer minimal targeted tests over broad rewrites.
- Do not create fake passing tests that only assert trivial behavior.

## Allowed edits

Allowed:

- `tests/**`
- test fixtures under `tests/**`
- test factories under `tests/**`
- test-only helpers under `tests/**`

Forbidden unless explicitly approved:

- `app/**`
- `alembic/**`
- `.github/**`
- `.cursor/**`
- `openspec/**`
- Docker/Kubernetes/infra files
- production config
- secrets

## Pre-check

Before writing tests, inspect the current repo state read-only:

```bash
git branch --show-current
git status --short
find tests -maxdepth 5 -type f | sort
find app -maxdepth 6 -type f | sort
```

Then inspect only relevant owner files, existing tests, fixtures, factories, and pytest config.

## Classify the request

Classify the requested test as one or more:

- regression test;
- characterization test;
- write-gate / no-write test;
- positive/negative gate pair;
- Telegram UI/message test;
- SQLAlchemy/query behavior test;
- async/concurrency test;
- Redis/PostgreSQL/ClickHouse consistency test;
- paid/free boundary test;
- Excel/UI parity test.

## Test quality requirements

Every new or changed test must make clear:

- what behavior is protected;
- what regression risk is being prevented;
- which owner function/module is involved;
- why the assertion would fail if the intended behavior is removed.

Use clear test names. Add comments only where the invariant is non-obvious.

## Regression tests

For regression tests:

- The test must fail on the broken behavior.
- The assertion must target the actual risk, not an incidental implementation detail.
- If you cannot prove the test fails before the fix, say so explicitly.

## Write-gate tests

For write-gate / no-write tests:

- Do not only assert `assert_not_called()` or `count == 0`.
- Prove that the forbidden entity is filtered before candidate selection, handler execution, or write-adapter boundary.
- Add a paired positive allowed case when possible.
- Check that the allowed path still writes or proceeds.

## Async tests

For async tests:

- Do not manually mutate shared module-level dependencies around `await`.
- Forbidden pattern: assigning `module.attr = fake` before `await` with manual `try/finally` restore.
- Prefer dependency injection, instance-level patching, write-adapter seams, external API client fakes, or pytest `monkeypatch` with justification.
- Avoid sleeps unless testing timeout behavior directly.

## Telegram UI/message tests

If the request touches Telegram messages, callbacks, keyboards, or bot UI:

- Check text length limits where relevant.
- Check parse mode / HTML validity.
- Check key phrases.
- Check buttons.
- Check callback data.
- Check keyboard shape.
- Check absence of raw technical text.
- If messages are parameterized, use realistic max-length substituted values, not tiny toy strings.

## Paid/free boundary tests

If the request touches paid/free behavior:

- Test free denial path.
- Test paid allowed path.
- Check that paid-only automation is not reachable from free UI/API path.
- Check that the user-facing explanation is present where relevant.

## SQLAlchemy/query tests

If the request touches ORM/query behavior:

- Test the exact filter/join/load behavior.
- Avoid tests that only check that a query object exists.
- Prefer fixtures with both matching and non-matching rows.
- Include edge cases for empty result, inactive rows, or unrelated shop/campaign where relevant.

## Verification

Run the most focused pytest command first.

Example:

```bash
poetry run pytest tests/path/to/test_file.py::test_specific_case -vv
```

If useful, also provide a broader command:

```bash
poetry run pytest tests/path/to/test_file.py -vv
```

Do not run unrelated slow suites unless required by the request.

## Output format

Return:

```text
Result:
- changed test files:
- behavior covered:
- why the test fails without the intended behavior:
- targeted command:
- broader command, if needed:
- remaining risks:
```

If tests fail because production code is currently wrong, do not fix production code. Report:

```text
Failing test result:
- command:
- failure:
- likely production issue:
- suggested next step:
```
