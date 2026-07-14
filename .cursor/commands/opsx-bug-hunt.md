---
description: "Wide invariant-focused bug hunt beyond the current diff, with reachability proof and cheap-first model policy."
argument-hint: "base=<branch> head=<branch> invariant=<contract> [scope=<paths>] [deep] [GO]"
---

# /opsx-bug-hunt

You are performing a read-only invariant-focused bug hunt.

This command is NOT a normal diff review.
This command is NOT an implementation command.
This command is NOT allowed to fix code unless the user input contains the exact token:

```text
GO
```

If `GO` is absent:

- do not modify files;
- do not stage files;
- do not commit;
- do not push;
- do not run migrations;
- do not deploy;
- do not restart services;
- output only findings and a fix plan.

Even with `GO`, only apply minimal fixes for findings classified as `confirmed production bug`.

Never fix `dead legacy`, `tests-only`, `unreachable`, `unclear reachability`, or `false positive` findings by adding defensive code just to satisfy static review.

## User input

```text
$ARGUMENTS
```

## Purpose

Find invariant bypasses that may exist outside the current diff.

Use this command when a feature or bugfix introduced, clarified, or relied on an invariant, and old or adjacent code paths may bypass the same invariant.

Examples:

- A/B Hold structural freeze must block all structural WB writes for `PENDING_SETUP` / `ACTIVE`.
- Free mode must not call paid automation.
- Campaign state transitions must not skip setup gates.
- Telegram UI changes must preserve parse mode, message length limits, buttons, and callback contracts.
- DB writes must preserve Redis/PostgreSQL/ClickHouse consistency.

## Required inputs

Extract from `$ARGUMENTS`:

- `base`: branch to compare against, usually `main`, `master`, `develop`, or PR target branch.
- `head`: current feature branch.
- `invariant`: exact behavioral contract to hunt for.
- `scope`: optional paths/modules to scan.
- `deep`: optional flag allowing deeper reasoning after cheap scan.
- `GO`: optional permission for minimal edits.

If `base`, `head`, or `invariant` is missing, stop and report the missing value.

Do not run a wide scan without a named invariant.

## Cost policy

Use cheap-first workflow.

### Pass 1 — cheap/static scan

Use fast grep/static inspection first.

Do not do broad expensive reasoning yet.

Find:

- definitions;
- call sites;
- mutation/write boundaries;
- scheduler/runtime entrypoints;
- adjacent functions with similar responsibilities;
- tests that imply intended coverage.

Recommended commands:

```bash
git branch --show-current
git status --short
git diff --name-only <base>...<head>
rg -n "<invariant keywords>" app tests
rg -n "<known function/class/callback names>" app tests scripts
```

### Pass 2 — focused reasoning

Only after Pass 1 finds concrete suspects, inspect the strongest 3–7 candidates.

For each candidate, prove or reject reachability.

### Pass 3 — deep mode

Only if `deep` is present or the user explicitly asks.

Deep mode may inspect broader adjacent modules, but still only under the same invariant.

Do not turn this into general repository review.

## Scope rules

Wide scan is allowed only after the invariant is named.

Allowed scan expansion:

- same invariant;
- same write/mutation boundary type;
- same manager/service family;
- same scheduler/runtime path;
- same UI/API callback class;
- same DB/Redis/ClickHouse consistency boundary.

Forbidden scan expansion:

- unrelated business logic;
- unrelated refactors;
- style cleanup;
- speculative architecture rewrites;
- dead code fixes without production reachability;
- files outside declared scope unless needed to prove call chain.

## Required analysis order

For each suspected bug:

1. State the invariant.
2. Identify the mutation/write boundary.
3. Locate exact file and function.
4. Find all call sites.
5. Prove production reachability:
   - scheduler/worker path;
   - bot callback/manual path;
   - API path;
   - CLI/admin path;
   - tests-only path;
   - no caller/dead legacy.
6. Classify the finding.
7. Recommend action.

## Classification

Use exactly one classification per finding:

```text
confirmed production bug
reachable but low-risk
unclear reachability
tests-only
dead legacy
false positive
```

### Classification rules

`confirmed production bug` requires:

- invariant mismatch;
- reachable runtime path;
- realistic production state;
- mutation/write/read side effect that violates the invariant.

`reachable but low-risk` means:

- runtime path exists;
- invariant mismatch is plausible;
- production impact is limited, rare, or blocked by another guard.

`unclear reachability` means:

- static search found partial evidence;
- call chain is incomplete;
- do not fix yet;
- ask for targeted investigation or runtime confirmation.

`tests-only` means:

- code path is used only by tests or fixtures;
- no production entrypoint found.

`dead legacy` means:

- function/code exists;
- no production caller found;
- no scheduler/bot/API/manual path found.

For `dead legacy`, recommend removal or cleanup task, not defensive patching.

`false positive` means:

- invariant is not violated;
- or another proven guard already prevents the issue;
- or the finding is based on an invalid assumption.

## Fix policy

If `GO` is absent:

- output only plan.

If `GO` is present:

- fix only `confirmed production bug`;
- keep patch minimal;
- add or update regression test;
- do not touch unrelated files;
- do not clean dead legacy unless the user explicitly asked for cleanup;
- do not commit.

Before editing, print:

```text
APPLYING ONLY CONFIRMED PRODUCTION BUG FIXES
```

## Regression test rules

Every confirmed production bug must have a regression test that fails before the fix.

Prefer testing real runtime entrypoint/wiring over isolated dead helper functions.

Acceptable tests:

- entrypoint excludes frozen candidates;
- manager wires invariant filter before write boundary;
- callback cannot trigger forbidden transition;
- worker tick skips forbidden mutation;
- API path rejects invalid state.

Weak tests:

- source-code string checks only;
- count-only tests;
- tests that directly call dead legacy helpers;
- tests that assert implementation detail without runtime meaning.

Source-string tests are allowed only as a temporary wiring guard if no better seam exists.

## Output format

Return exactly this structure:

```text
Verdict:
- plan_only / applied / blocked

Base/head:
- base:
- head:
- current branch:
- dirty files:

Invariant:
- ...

Scan scope:
- inspected:
- expanded:
- skipped:

Findings:
1. [classification] short title
   File:
   Function:
   Boundary:
   Evidence:
   Reachability:
   Risk:
   Recommended action:
   Regression test:

Confirmed production bugs:
- ...

Dead legacy / false positives:
- ...

Minimal fix plan:
1.
2.
3.

Tests:
- regression test path:
- verification command:

Risks:
- ...

Need from user:
- none / exact question
```

## Hard rules

- No invariant → no wide scan.
- No reachability → no production bug.
- No production bug → no code fix.
- Dead legacy is cleanup, not hotfix.
- Do not patch unreachable code to silence Bugbot.
- Do not use expensive deep reasoning until cheap scan finds concrete suspects.
- Do not mix diff review and invariant bug hunt.
- Do not commit, push, deploy, restart, migrate, or touch secrets.
