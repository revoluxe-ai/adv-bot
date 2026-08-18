---
description: "Committed or dirty-worktree over-report scan of code/test/process antipatterns; optional practice ledger accept/reject."
argument-hint: "base=<branch|ref> [head=<ref>|working] [focus=all|prod|tests|process] [change=<name>] [accept=CLASS|reject=CLASS GO]"
---

# /opsx-antipattern-gate

Просканируй `base...target` на **классы антипаттернов** (code / tests / process
smell). Default — **over-report**: лучше лишний `SUSPECT`, чем пропуск.

Цель: нельзя спокойно идти в `/opsx-static-check` / `/opsx-verify`, не видя
типовых костылей (prod test-double sniff, weak write-gate, source-only RED, …).

## What this is

* Diff-scoped antipattern inventory (sibling UX к
  `/opsx-external-call-coverage`).
* Soft quality step **после** `/opsx-external-call-coverage` PASS (и optional
  performance review), **до** `/opsx-static-check` / `/opsx-verify`.
* Default **READ_ONLY** scan.
* Optional durable practice memory:
  `.cursor/antipattern-gate/PRACTICE_LEDGER.jsonl`
  via `accept=<CLASS_ID> GO` / `reject=<CLASS_ID> GO`.

## What this is NOT

* NOT archive `GO` / `NO_GO` (→ `/opsx-verify`).
* NOT запуск pyright/mypy/pytest (→ `/opsx-static-check`).
* NOT external-call coverage (→ `/opsx-external-call-coverage`).
* NOT bug residual / OPEN_CANDIDATE board (→ `/opsx-bug-debt-board` / INDEX).
* NOT auto-edit of `.cursor/rules/testing-rules.mdc` (promote separately).
* NOT product bug hunt (→ `/opsx-project-bug-hunt` / `/opsx-fix-bug`).

## User input

```text
$ARGUMENTS
```

| Token | Effect |
|-------|--------|
| `base=<ref>` | обязательный comparison base |
| `head=<ref>` | optional immutable comparison target |
| `head=working` | explicit dirty-worktree target |
| `focus=all\|prod\|tests\|process` | optional; default `all` |
| `change=<name>` | optional context |
| `accept=<CLASS_ID>` | with `GO` — append ACCEPTED_IN_PROJECT to ledger |
| `reject=<CLASS_ID>` | with `GO` — append REJECTED_AS_ANTIPATTERN to ledger |
| `GO` | required for ledger write only |
| unknown token | `STATUS=BLOCKED`, не менять файлы |

Примеры:

```text
/opsx-antipattern-gate base=stage
/opsx-antipattern-gate base=origin/main head=HEAD focus=prod
/opsx-antipattern-gate base=origin/main head=working focus=prod
/opsx-antipattern-gate base=stage accept=AP_PROD_TEST_DOUBLE_SNIFF GO
/opsx-antipattern-gate base=stage reject=AP_SOURCE_TOKEN_PROOF GO
```

## Required input

Если `base=` отсутствует или ref не резолвится → `STATUS=BLOCKED`.

```text
На какую base branch/ref сверять antipattern gate?
Пример: /opsx-antipattern-gate base=stage
```

Не выдумывай base.

## Modes

### Default — SCAN (READ_ONLY)

* Не менять репозиторий (кроме чтения).
* Только отчёт + pasteable `NEXT_ACTION`.
* Если `head=` не задан, target по умолчанию — текущий `WORKTREE`, а не
  committed `HEAD`; staged, unstaged и релевантные untracked paths должны
  попасть в audit.

### Practice write — `accept=` / `reject=` + `GO`

* Писать **только** append в
  `.cursor/antipattern-gate/PRACTICE_LEDGER.jsonl`.
* Без `GO` при `accept=`/`reject=` → `BLOCKED` (покажи точную команду с GO).
* Не трогать production, tests, rules, commands (кроме ledger).

## Authority surfaces

```text
CATALOG:  .cursor/antipattern-gate/catalog.md
LEDGER:   .cursor/antipattern-gate/PRACTICE_LEDGER.jsonl
README:   .cursor/antipattern-gate/README.md
POLICY:   .cursor/rules/testing-rules.mdc (partial overlap; not sole SoT)
```

Ledger = triage memory (`TEMPORARY_SAFETY_NET`). Promotion into
`testing-rules` / static-check = separate Owner path
(`/opsx-admin-command-promote-process-lesson` or explicit rule edit).

## Seed classes (over-report; extend catalog freely)

| CLASS_ID | Signal (non-exhaustive) |
|----------|-------------------------|
| `AP_PROD_TEST_DOUBLE_SNIFF` | `app/**` references `unittest.mock` / `__module__ == "unittest.mock"` / type(x).__module__ mock sniff |
| `AP_WEAK_WRITE_GATE` | write-gate test only `assert_not_called` / `call_count == 0` without pre-boundary proof |
| `AP_SOURCE_TOKEN_PROOF` | `inspect.getsource` / token-in-source as sole behavioral proof |
| `AP_FROZEN_RED_SIBLING_PROD_SKIP` | production skips real write because sibling is a test double |
| `AP_ASYNC_MODULE_ATTR_MUTATION` | `module.attr = fake` around `await` with manual restore |
| `AP_DEAD_SURFACE_TEST_ONLY` | new/changed exported symbol callers only under `tests/**` |
| `AP_PROCESS_TEST_ONLY_BRANCH_COMMENT` | comments documenting prod behavior only for tests |

When unsure → emit `SUSPECT`, not silence.

## Target resolution

1. Resolve `base` to an immutable commit.
2. Resolve target:
   - explicit `head=<ref>` → immutable ref target;
   - explicit `head=working` or omitted `head=` → current worktree target.
3. For the worktree target use the base-to-working diff, not
   `base...HEAD`; include staged and unstaged tracked changes, deletions, and
   relevant untracked in-policy paths as added paths.
4. Report:

```text
AUDIT_TARGET: WORKTREE | REF
BASE_SHA: <sha>
TARGET_REF: WORKTREE | <sha>
WORKTREE_TRACKED_CHANGED: <n>
WORKTREE_UNTRACKED_IN_POLICY: <n>
WORKTREE_DELETED: <n>
```

5. A clean worktree target may be equivalent to `HEAD`, but the report must
   still state `AUDIT_TARGET: WORKTREE`. No commit is required for a
   read-only worktree re-audit.

## Scan algorithm

1. Resolve `base` / `head` and the target (`git rev-parse`). Fail → `BLOCKED`.
2. Read catalog + ledger (if ledger missing → treat as empty).
3. Inventory the base-to-target changed paths, including relevant untracked
   worktree paths.
4. Filter paths by `focus=`:
   - `prod` → `app/**`, top-level production `*.py` (not tests)
   - `tests` → `tests/**`
   - `process` → `.cursor/commands/**`, `.cursor/pipeline/**`, `.cursor/rules/**`
   - `all` → union of above in-policy paths from the diff
5. For each in-focus changed file, use
   `git diff <base>...<head> -- <path>` for `AUDIT_TARGET: REF` or
   `git diff <base> -- <path>` for `AUDIT_TARGET: WORKTREE`; for untracked
   paths, inspect the file as an added hunk. Use bounded Grep/Read for class
   signals and prefer added/changed hunks.
6. For every hit emit `LOC_LINK: path:line` (see
   `.cursor/rules/opsx-clickable-loc-link-contract.mdc`).
7. Apply ledger:
   - `ACCEPTED_IN_PROJECT` for CLASS_ID → disposition
     `MATCHES_ACCEPTED_PRACTICE` (still listed; does not FAIL alone)
   - `REJECTED_AS_ANTIPATTERN` → keep/force `CONFIRMED_HIT`
8. Print Final report + pasteable exits.
9. Default: do not write files.

## Practice ledger schema (one JSON object per line)

```json
{
  "timestamp_utc": "ISO-8601",
  "class_id": "AP_…",
  "decision": "ACCEPTED_IN_PROJECT|REJECTED_AS_ANTIPATTERN|DEFERRED",
  "base": "ref-or-null",
  "head": "ref-or-null",
  "note": "short owner/agent note",
  "actor": "owner|agent"
}
```

Append-only. Latest decision for a `class_id` wins.
Do not rewrite history; to change mind, append a new line.

## Status

| STATUS | Когда |
|--------|--------|
| `PASS` | no `CONFIRMED_HIT` (only none / `MATCHES_ACCEPTED_PRACTICE` / empty scope) |
| `PASS_WITH_SUSPECTS` | no `CONFIRMED_HIT`, but ≥1 `SUSPECT` / `NEEDS_OWNER` |
| `FAIL` | ≥1 `CONFIRMED_HIT` |
| `BLOCKED` | missing/bad `base`, unknown token, accept/reject without `GO`, git error |

`PASS` with zero in-policy paths is allowed (`nothing in policy scope`).

## Authority boundaries

* Не объявляй archive `GO` / `NO_GO`.
* Не подменяй `/opsx-verify`, `/opsx-static-check`, `/opsx-test`.
* `MATCHES_ACCEPTED_PRACTICE` ≠ proof that testing-rules allow the pattern.
* Soft recommend from `/opsx-apply` — this command is not a hard archive gate in v1.
* Over-report is intentional; use `focus=` and `accept=` to tame noise.

## Final report (required)

```text
STATUS: PASS | PASS_WITH_SUSPECTS | FAIL | BLOCKED

BASE: <ref>
HEAD: <ref>
AUDIT_TARGET: WORKTREE | REF
BASE_SHA: <sha>
TARGET_REF: WORKTREE | <sha>
WORKTREE_TRACKED_CHANGED: <n>
WORKTREE_UNTRACKED_IN_POLICY: <n>
WORKTREE_DELETED: <n>
FOCUS: all | prod | tests | process
CHANGE: <name|none>
CATALOG: .cursor/antipattern-gate/catalog.md
LEDGER: .cursor/antipattern-gate/PRACTICE_LEDGER.jsonl

IN_POLICY_CHANGED: <n>
HITS_CONFIRMED: <n>
HITS_SUSPECT: <n>
MATCHES_ACCEPTED_PRACTICE: <n>
OUT_OF_FOCUS: <n>

HITS:
- CLASS_ID: <id>
  DISPOSITION: CONFIRMED_HIT | SUSPECT | NEEDS_OWNER | MATCHES_ACCEPTED_PRACTICE
  PATH: <path>
  LOC_LINK: <path>:<line>
  SIGNAL: <short>
  FIX_EXIT: <pasteable command>
  NOTE: <short>

GAPS:
- <CLASS_ID> @ <LOC_LINK>: <DISPOSITION> → <FIX_EXIT>

PRACTICE_ACTIONS (if Owner wants memory):
- accept: /opsx-antipattern-gate base=<BASE> accept=<CLASS_ID> GO
- reject: /opsx-antipattern-gate base=<BASE> reject=<CLASS_ID> GO

WHAT_HAPPENED:
WHY:
CURRENT_STATE:
OWNER_DECISION_REQUIRED: none | accept/reject class | fix code
NEXT_ACTION:
DO_NOT_DO_YET:
```

### Typical FIX_EXIT map

| CLASS_ID | Pasteable next |
|----------|----------------|
| `AP_PROD_TEST_DOUBLE_SNIFF` | `/opsx-fix-bug` or targeted cleanup change; remove sniff |
| `AP_WEAK_WRITE_GATE` | strengthen test to prove pre-boundary filter |
| `AP_SOURCE_TOKEN_PROOF` | assert real writer/call / observable behavior |
| `AP_FROZEN_RED_SIBLING_PROD_SKIP` | patch both seams in test; remove prod skip |
| `AP_ASYNC_MODULE_ATTR_MUTATION` | narrow monkeypatch / inject dependency |
| `AP_DEAD_SURFACE_TEST_ONLY` | wire production caller or drop export |
| `AP_PROCESS_TEST_ONLY_BRANCH_COMMENT` | delete branch or fix harness |

After `PASS` | `PASS_WITH_SUSPECTS` (Owner may continue with suspects):

```text
NEXT_ACTION: /opsx-static-check
THEN: /opsx-verify <change>
```

## Self-check

- [ ] `base=` required; missing → BLOCKED
- [ ] Over-report: uncertain → SUSPECT
- [ ] Every code hit has `LOC_LINK`
- [ ] No archive GO/NO_GO claimed
- [ ] Ledger write only with accept/reject + GO
- [ ] Latest ledger decision per class_id applied
