---
description: "Fix a scoped Bugbot/Codex/GitHub review bug with mandatory diagnosis, regression test, and verification. Without GO, output only a plan."
argument-hint: "[GO] <bug report / review comment / failing test / log>"
---

# /fix-bug

You handle scoped bugfixes reported by Bugbot, Codex, GitHub review, CI, or targeted tests.

You are allowed to modify files ONLY when the user input contains the exact standalone token:

```text
GO
```

Valid write-mode examples:

```text
/fix-bug GO Bugbot says Redis client is not closed on error path
/fix-bug GO <paste bug report>
```

Plan-only examples:

```text
/fix-bug Bugbot says Redis client is not closed on error path
/fix-bug <paste bug report>
```

Invalid write-mode examples:

```text
/fix-bug:GO
/fix-bug --go
/fix-bug yes
/fix-bug apply
```

If `GO` is absent:

- do not modify files;
- do not stage files;
- do not commit;
- do not run destructive commands;
- output only a scoped bugfix plan.

Never push, merge, rebase, force-push, deploy, restart services, run production migrations, edit secrets, or touch Kubernetes/infra files unless the user explicitly gives a separate command for that.

## User input

```text
$ARGUMENTS
```

## Purpose

Convert a bug report into a minimal, reviewable bugfix.

The goal is not to clean up the surrounding code.

The goal is to fix the reported bug with the smallest safe diff and a regression test that would fail before the fix.

## Required workflow

### 1. Classify the bug

Identify:

- source: Bugbot / Codex / GitHub review / CI / user report / test failure;
- symptom;
- likely root cause or hypothesis;
- affected behavior;
- affected modules;
- whether this is a lightweight bugfix or requires OpenSpec SPEC.

Use lightweight bugfix only when the fix is local and does not change public contracts.

Escalate to OpenSpec SPEC if the bug affects:

- paid/free boundary;
- bid/cost/reallocation logic;
- campaign state transitions;
- DB schema;
- async/concurrency behavior;
- Redis/PostgreSQL/ClickHouse consistency;
- Telegram public UI/callback contracts;
- pricing/paid logic;
- cross-layer refactor.

### 2. Inspect before editing

Before changing anything, inspect the smallest relevant set of files.

Prefer:

- the file named in the bug report;
- nearby tests;
- related fixtures;
- code owner module;
- failing test output, if provided.

Do not search the whole repository unless the bug cannot be scoped locally.

### 3. Plan-only mode

If `GO` is absent, output exactly:

```text
Verdict:
- plan_only / needs_spec / unclear

Symptom:
Likely cause:
Affected files:
Forbidden files:
Minimal fix plan:
Regression test plan:
Verification command:
Risks:
Need from user:
```

`Need from user` must be `none` unless the bug report is genuinely insufficient.

### 4. Write mode

If `GO` is present:

- apply only the minimal fix;
- add or update regression test;
- avoid unrelated refactor;
- avoid formatting churn;
- avoid changing public behavior beyond the bug;
- preserve existing style;
- add comments/docstrings only if they clarify a non-obvious invariant;
- do not commit.

### 5. Regression test requirement

Every fix must include one of:

- a new regression test that fails before the fix;
- an updated existing test that would fail before the fix;
- a clear explanation why no automated test is possible.

Weak tests are not acceptable.

Bad tests:

- only check `count == 0`;
- only check that function does not crash;
- mock away the actual bug;
- assert implementation details unrelated to the symptom.

Good tests:

- reproduce the reported failure;
- protect the behavior that broke;
- use realistic boundary data;
- verify the externally relevant result.

### 6. Verification

Run the narrowest useful verification command.

Prefer targeted tests first:

```bash
poetry run pytest path/to/test_file.py::test_name -vv
```

Then optionally broader related tests if risk justifies it.

Do not run full CI unless necessary.

### 7. Stop conditions

Stop and report instead of continuing if:

- the fix requires broad architecture changes;
- the bug report contradicts current code;
- the fix touches paid/free, DB schema, campaign state, async job orchestration, or infra unexpectedly;
- tests require unavailable services;
- regression test cannot be written without changing test architecture;
- the required edit would affect unrelated modules.

## Final response in write mode

After applying changes, output:

```text
Verdict:
- fixed / partial / blocked

Changed files:
Regression test:
Verification:
Risk notes:
What was intentionally not changed:
```

Do not include huge diffs unless asked.


## Mandatory diagnosis challenge

Before proposing a fix, explicitly separate:

1. Bugbot evidence:
   - symptom
   - observed failure mode
   - affected code path

2. Generated hypothesis:
   - likely root cause
   - proposed fix
   - assumptions

3. Domain invariants:
   - campaign state transitions
   - stats freshness requirements
   - paid/free boundary
   - Redis/PG consistency
   - scheduler eligibility
   - user-visible failure reason

4. Safety check:
   - Could the minimal fix allow an invalid state?
   - Could it bypass an intentional guard?
   - Could it turn a stuck bug into an unsafe action?
   - Is there a precondition that should block entry earlier?

If the minimal fix violates an invariant, reject or rewrite the fix plan.
