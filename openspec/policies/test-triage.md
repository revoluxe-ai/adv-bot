# Test Triage Policy

## Purpose

Failing tests must be diagnosed before any fix.

Do not immediately change production code or tests just to make CI green.

## Required classification

Every failing test must be classified as exactly one:

- CODE_BUG: production code violates accepted behavior.
- TEST_OBSOLETE: test expectation is outdated because accepted behavior changed.
- SPEC_CHANGED_BUT_NOT_UPDATED: behavior changed but OpenSpec/spec/tasks were not updated.
- BAD_TEST: test checks the wrong thing or does not catch the real regression.
- FLAKY_OR_ENV: failure is caused by async timing, ordering, DB, Redis, ClickHouse, fixtures, or environment.
- AMBIGUOUS: evidence is insufficient.

## Required evidence

A good triage must include:

- failing command;
- failing test and assertion/error;
- protected behavior;
- related OpenSpec change/spec/tasks, if present;
- recent diff or affected files;
- classification;
- minimal next action;
- verification command;
- copy-pasteable next prompt for the implementation agent.

## Forbidden shortcuts

Do not:

- delete assertions to make tests pass;
- weaken behavior checks into shallow implementation checks;
- update snapshots without explaining accepted behavior;
- mock away the real risk;
- change unrelated files;
- fix production code before proving CODE_BUG;
- change tests before proving TEST_OBSOLETE or BAD_TEST.

## Rule

A failing test is evidence, not an automatic instruction to fix code.

First triage. Then apply the verdict.
