---
description: "Triage and fix bug reports with reachability, invariant, write-boundary and regression-test gates."
argument-hint: "GO [bug report / Bugbot verdict / CI failure / manual finding]"
---

# /opsx-fix-bug

Use this command to triage and, only when safe, fix a concrete bug report from Bugbot, Cursor, Codex, CI, manual review, logs, or user observation.

A bug report is a hypothesis, not a fix instruction.

The command must validate reachability, invariant ownership, write-boundary impact, and regression-test quality before changing production code.

## User input

```text
$ARGUMENTS
```

## Write permission

You may modify files only when the user input contains the exact standalone token:

```text
GO
```

If `GO` is absent:

- do not modify files;
- do not stage files;
- do not commit;
- do not push;
- do not run destructive commands;
- output only analysis, plan, tests, and the next exact prompt/action.

Even when `GO` is present, do not edit production code unless the final verdict is `fix_now`.

Never deploy, restart services, touch production data, run migrations, edit secrets, merge, rebase, force-push, change Kubernetes/infra/CI, or perform unrelated refactors.

## Primary objective

Do not patch the function named by the report until you prove that it is the correct runtime boundary.

Before fixing, determine whether the reported path is:

1. reachable from a real runtime entrypoint;
2. reachable only from tests/dev scripts;
3. dead or legacy code;
4. unreachable, but pointing to a real missing invariant in a sibling path;
5. already guarded elsewhere;
6. a false positive caused by stale code, stale tests, or incomplete static analysis.

If runtime reachability is unknown, stop before implementation.

## Mandatory first pass: report forensics

Inspect, read-only first:

1. the reported file/function/class;
2. all direct callers;
3. all indirect callers up to runtime entrypoints;
4. scheduler/job/bot/API entrypoints;
5. tests that call the reported function directly;
6. feature flags, modes, guards, enum states and eligibility filters;
7. write boundaries: WB API writes, DB writes, Redis writes, ClickHouse writes, Telegram writes;
8. existing regression tests around the same invariant.

Use repository search. Do not rely on sibling code similarity as reachability evidence.

Suggested read-only commands:

```bash
git branch --show-current
git status --short
rg -n "<reported_function>|<reported_class>|<reported_symbol>" .
rg -n "<related_invariant_symbol>|<write_adapter>|<handler_name>" app tests openspec .cursor .github
```

## Reachability classification

Every bug report must include this classification before any fix plan:

```text
Reachability:
- runtime_reachable: yes/no/unknown
- runtime_entrypoints:
  - ...
- direct_callers:
  - ...
- indirect_callers:
  - ...
- test_only_callers:
  - ...
- dead_or_legacy_path: yes/no/unknown
- write_boundary_reachable: yes/no/unknown
- evidence_chain:
  - entrypoint -> caller -> reported function -> handler/write boundary
```

If the evidence chain is missing, the verdict must not be `fix_now`.

## Hard stop: reachability unknown

If the report claims a missing guard in a function, but runtime reachability is not proven, verdict must be:

```text
needs_entrypoint_map
```

In this case:

- do not output `fix_now`;
- do not suggest `GO to apply`;
- do not propose production code changes as the primary next step;
- output the exact searches/files needed to prove or disprove reachability;
- consider updating the bug-hunter rule to require entrypoint evidence.

Required evidence before a fix:

```text
Entrypoint chain:
- scheduler/job/bot/API entrypoint:
- manager coroutine caller:
- direct call site:
- runtime condition:
- handler/write boundary:
```

If no such chain is found:

```text
Decision:
- reported path is not proven runtime-reachable
- do not patch the reported helper/coroutine yet
- update bug-hunter to check reachability before reporting
- optionally add dead-code or entrypoint-inventory task
```

## Bugbot report validation

Bugbot reports are suspicious until proven.

Before accepting Bugbot severity:

1. Search all call sites of the reported function.
2. Classify each call site:
   - runtime scheduler/job;
   - bot/API handler;
   - service/manager production path;
   - test-only;
   - dev script;
   - dead/legacy;
   - unknown.
3. If only test-only/dead/unknown callers exist, downgrade to `false_positive` or `needs_entrypoint_map`.
4. Do not use sibling methods as reachability evidence.
5. Do not treat a missing local guard as a production bug unless a real write boundary can be reached.
6. Do not patch dead code just to silence Bugbot.

## Mandatory invariant analysis

Extract the domain invariant behind the report.

Bad framing:

```text
Add filter X inside function Y.
```

Good framing:

```text
During protected state Z, no structural mutation may reach candidate construction, handler creation, adapter call, or external write boundary from any runtime-reachable path.
```

Always distinguish:

- reported local symptom;
- real domain invariant;
- owner module of the invariant;
- all known write paths that could violate it;
- existing guards;
- missing guards;
- sibling paths that only suggest a pattern;
- tests that prove the invariant at the correct boundary.

## Decision matrix

### Case A: reachable bug

Use verdict `fix_now` only if:

- the path is runtime-reachable;
- the invariant is violated;
- a write boundary or externally visible side effect is reachable;
- the fix can be scoped to the current bug;
- a regression test can fail before the fix and pass after it.

Then:

- add or update the regression test;
- patch the narrowest correct boundary;
- prefer shared guard/candidate filter over duplicated local checks;
- verify both blocked and allowed behavior.

### Case B: unreachable reported path, invariant protected elsewhere

Use verdict `false_positive` or `plan_only`.

Do not change production logic just to satisfy the report.

Correct actions may be:

- update bug-hunter rules;
- add entrypoint inventory;
- remove or document dead code only under a separate explicit task;
- update stale tests.

### Case C: unreachable reported path, sibling path may violate same invariant

Use verdict `needs_entrypoint_map` or `plan_only`.

Do not patch the literal reported function yet.

Instead:

- inspect sibling runtime entrypoints;
- identify real write paths;
- fix only the reachable violating path;
- add regression tests against the real entrypoint/write boundary.

### Case D: direct unit-test-only path

If only tests call the function:

- do not assume production impact;
- decide whether the test represents intended public behavior;
- if yes, rewrite the test around a real entrypoint or documented boundary;
- if no, update/delete the stale test with explanation.

### Case E: process gap, not code bug

If the main issue is missing ownership/entrypoint documentation, use verdict `needs_openspec_update`.

Do not hide the process gap by making a local code patch.

## Output before GO

When `GO` is absent, output exactly this structure:

```text
Verdict:
- fix_now / plan_only / false_positive / needs_entrypoint_map / needs_openspec_update

Bug classification:
- source:
- reported file/function:
- reported severity:
- accepted severity:
- symptom:
- invariant:
- affected write boundary:

Reachability:
- runtime_reachable:
- runtime_entrypoints:
- direct_callers:
- indirect_callers:
- test_only_callers:
- dead_or_legacy_path:
- write_boundary_reachable:
- evidence_chain:

Decision:
- why this is or is not a real production bug:
- why the reported fix is or is not at the right boundary:

Minimal fix plan:
- files allowed:
- files forbidden:
- exact behavior change:
- no-op/dead-code handling:

Regression tests:
- failing-before-fix test:
- blocked case:
- allowed case:
- mutation/write-boundary assertion:
- weak tests to avoid:

Verification commands:
- ...

Bug-hunter / OpenSpec updates:
- entrypoint inventory update needed: yes/no
- hunter rule update needed: yes/no
- source-of-truth update needed: yes/no

Stop conditions:
- ...

Next action:
- exact command or prompt to run next
```

If verdict is `needs_entrypoint_map`, `Next action` must not be `GO to apply`.

It must be a read-only entrypoint discovery prompt/command.

## Behavior with GO

When `GO` is present:

1. perform the same forensics first;
2. if verdict is not `fix_now`, do not edit production code;
3. if verdict is `fix_now`, add/update regression tests before or with the fix;
4. keep the diff minimal;
5. do not patch dead code unless explicitly justified;
6. do not touch forbidden files/actions;
7. run the targeted verification command if available;
8. report changed files, tests run, and unresolved risks.

If the bug requires broader behavior changes than the current report covers, stop and request/spec an OpenSpec change instead of expanding scope silently.

## Testing rules

Regression tests must prove the invariant at the correct boundary.

For write-gate bugs, tests must prove that the forbidden entity does not reach one of:

- candidate list;
- handler construction;
- write adapter;
- WB API call;
- DB mutation;
- Redis mutation;
- ClickHouse mutation;
- Telegram output;
- scheduler/runtime entrypoint.

Weak tests are forbidden as the main proof:

- only `assert_not_called()` without proving the call path;
- only `count == 0`;
- mocking the guard/filter being tested;
- direct testing of a dead helper without proving runtime reachability;
- source-inspection-only tests as the only regression;
- tests that still pass if the intended guard is removed.

Prefer paired tests:

- blocked case: protected entity must not reach the write boundary;
- allowed case: normal entity still reaches the write boundary.

Source-inspection wiring tests are allowed only as secondary guardrails. They are not enough to prove production impact.

## WB Sky high-risk areas

For bugs touching these areas, be stricter:

- campaign state;
- bidding;
- CPO/CPA/budget logic;
- whitelist/blacklist mutations;
- keyword structural mutations;
- WB API writes;
- Redis/PostgreSQL/ClickHouse consistency;
- async jobs/schedulers/workers;
- paid/free boundary;
- Telegram callback/UI write behavior.

For these areas, always identify:

```text
runtime entrypoint -> manager/service -> candidate/filter -> handler/adapter -> write boundary
```

Do not accept a fix plan that only says вЂњadd guard in helperвЂќ.

## Specific rule: A/B Hold / structural freeze

For A/B Hold, freeze, setup, pending, active, hold, structural-act, whitelist, blacklist, keyword or bid mutation reports:

- identify the state/mode being protected;
- identify whether the campaign can reach the mutation path from a runtime tick;
- identify the exact mutation boundary;
- verify protected states are blocked;
- verify normal states still proceed;
- do not use sibling ACT paths as proof of reachability;
- do not patch service internals if the invariant belongs at manager/candidate/write-boundary level.

## Specific rule: entrypoint inventory

If the bug exposes that entrypoints are not documented, propose an entrypoint inventory update.

The inventory should record:

```text
Entrypoint name:
- scheduler/job/bot/API source:
- manager method:
- service/handler path:
- write boundaries:
- protected invariants:
- tests covering it:
```

Do not create a large documentation refactor inside a bugfix unless explicitly requested.

## Specific rule: hunter feedback loop

If Bugbot, opsx-hunt-bug, or another hunter misses or misclassifies the issue, output a hunter update note:

```text
Hunter feedback:
- missed/misclassified condition:
- required new check:
- example false positive/false negative:
- suggested rule:
- suggested fixture/test:
```

The goal is to prevent the same class of bug from reaching Bugbot again.

## Final output after GO

When changes were made, output:

```text
Verdict:
- fixed / not_fixed

Changed files:
- ...

What changed:
- ...

Regression tests:
- ...

Verification:
- command:
- result:

Remaining risks:
- ...

Follow-up:
- bug-hunter update:
- OpenSpec/source update:
- review checklist:
```

When no changes were made because the verdict was not `fix_now`, output:

```text
Verdict:
- no_code_change

Reason:
- ...

Next correct action:
- ...
```

## Review checklist

Before finishing, verify:

- the diff matches the invariant, not just the report text;
- reachability was proven or explicitly marked unknown;
- no unrelated files changed;
- no dead-code-only patch was made without justification;
- regression test fails before the fix;
- test reaches the real boundary;
- allowed behavior still works;
- forbidden behavior is blocked;
- source-inspection test is not the only proof for a production bug;
- Bugbot/hunter/OpenSpec updates are proposed when the gap is process-level.
