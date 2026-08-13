---
description: "Atomic local commits for product/code/OpenSpec/docs. AI/process surfaces redirect to /opsx-meta-commit."
argument-hint: "[FULL_CHECK|FAST_CHECK] GO [optional change-id / base=<ref> / context]"
---

# /opsx-commit

You are allowed to create local git commits ONLY when the user input contains the exact token `GO`.

If `GO` is absent:
- do not modify files;
- do not stage files;
- do not commit;
- output only the proposed commit plan (include `CHECK_MODE` + per-group check matrix; do **not** run the matrix).

Never push, merge, rebase, force-push, deploy, restart services, run migrations against production, or touch secrets.

## User input

```text
$ARGUMENTS
```

## Check mode (mandatory)

Parse exact case-sensitive tokens in `$ARGUMENTS`:

| Token | Meaning |
|---|---|
| `FULL_CHECK` | Full pre-commit matrix (also the **default** when neither token is present) |
| `FAST_CHECK` | Fast pre-commit matrix (overrides default) |

Rules:

1. If **both** `FULL_CHECK` and `FAST_CHECK` are present → `STATUS: BLOCKED_AMBIGUOUS_CHECK_MODE`; do not stage or commit.
2. If neither is present → `CHECK_MODE=FULL_CHECK`.
3. `CHECK_MODE` is **not** commit authorization. `GO` is still required to stage/commit.
4. Check tokens do not authorize process-surface commits (still `/opsx-meta-commit`).

Optional `base=<ref>` in `$ARGUMENTS` is used by `FULL_CHECK` AI soft-chain steps. If absent, resolve merge-base against upstream tracking branch, else `stage`, else `main` / `master`; document the chosen ref. If base cannot be resolved on `FULL_CHECK` when AI steps apply → do not commit that group (`BLOCKED` for AI steps).

`FAST_CHECK` is **not** equivalent to `/opsx-static-check FAST` (this FAST omits mypy by design).

## Purpose

Analyze the current working tree and create safe atomic local commits by logical zones
for **product/code/OpenSpec/docs** changes.

Process surfaces (AI/process artifacts: commands, rules, skills, agents,
static-check, prompt/skill mirrors, root agent guides) are **out of scope**.
They belong exclusively to `/opsx-meta-commit`.

**Source resolution:** Follow `.cursor/commands/opsx-source-resolution.md`. If an OpenSpec change-id is provided or exactly one `openspec/changes/<id>/` is touched, read that change via canonical paths only; do not inventory all changes.

## Process-surface exclusion (mandatory)

Never stage or commit these paths; leave them untouched and redirect:

```text
.cursor/commands/**
.cursor/rules/**
.cursor/skills/**
.cursor/agents/**
.cursor/static-check/**
.cursor/pipeline/**
.cursor/antipattern-gate/**
.cursor/devops/**
.cursor/opsx-resolve-conflict/**
.cursor/opsx-review-commands
.agents/**
.github/skills/**
.github/prompts/**
.github/copilot-instructions.md
.github/git-commit-instructions.md
AGENTS.md
```

If any of these are dirty:

```text
OUT_OF_SCOPE_REDIRECT:
NEXT_ACTION: /opsx-meta-commit
```

If the dirty tree is **only** process surfaces, do not invent product commits:

```text
STATUS: OUT_OF_SCOPE_REDIRECT
NEXT_ACTION: /opsx-meta-commit
DO_NOT_DO_YET: commit process files via /opsx-commit
```

### Allowlist sync (mandatory companion)

Process-exclusion above is **not** enough for `/opsx-meta-commit` in-scope.
Meta-commit SoT is `.opsx/sources.yaml` allowlist.

When **adding or renaming** an entry in this Process-surface exclusion list,
the **same coherent packet** MUST also add the matching
`.opsx/sources.yaml` `allowlist:` line (or fail closed). Exclusion alone
with a missing allowlist row produces `ALLOWLIST_GAP` on meta-commit
(dead-end if redirected back here).

Do **not** remove an allowlist row while the exclusion list still names
that prefix, unless a deliberate dual-surface retirement is documented in
the same packet.

Commit subjects MUST be in English with a short Russian explanation in parentheses:

```text
type(scope): English summary (русское пояснение)
```

Commit bodies MUST be detailed and useful for review:
- what changed;
- why it changed;
- how it was verified;
- OpenSpec change-id, if detected;
- risk notes, if any.

Primary body text should be English. Russian may appear in parentheses for clarity.

## Mandatory preflight

Follow `.cursor/commands/opsx-execution-preflight.md`.

These git ops are **REQUIRED_FOR** commit planning (branch protection + change inventory). Apply budgets; on timeout return `blocked_preflight_timeout` rather than hanging.

```text
OPERATION_REASON: atomic commit plan + protected-branch gate
REQUIRED_FOR: commit decision
SKIP_IF: never for /opsx-commit when GO path is taken (preview may use status/diff only)
TIME_BUDGET: branch 5s; status 10s; each diff 15s
FAILURE_BEHAVIOR: blocked_preflight_timeout / report missing fact; no retry loop
```

Run the smallest set that answers the need:

```bash
git branch --show-current
git status --short
git diff --stat
git diff --name-status
git diff --cached --stat
git diff --cached --name-status
```

Do not run `git fetch` here unless remote state becomes REQUIRED_FOR.
Block execution if current branch is:

```text
main
master
prod
production
```

unless the user input contains:

```text
GO_ON_PROTECTED_BRANCH
```

Even with `GO_ON_PROTECTED_BRANCH`, never push.

## Detect OpenSpec change

Inspect changed OpenSpec files:

```powershell
Get-ChildItem -Path .\openspec\changes -Recurse -File -Depth 2 |
  Sort-Object FullName |
  ForEach-Object { $_.FullName }
```

If exactly one `openspec/changes/<change-id>/` is touched, use that as the OpenSpec change-id.

If the user provided a change-id in `$ARGUMENTS`, prefer it.

If multiple change-ids are touched:
- do not commit automatically;
- output the split plan;
- ask the user to rerun with the exact change-id.

When available, read:

```text
openspec/changes/<change-id>/proposal.md
openspec/changes/<change-id>/design.md
openspec/changes/<change-id>/tasks.md
openspec/changes/<change-id>/specs/**/*.md
```

Use these files to detect unrelated changes.

## Classification zones

Classify every **in-scope** changed file into one zone.
Process-surface paths listed above are never classified here — report redirect only.

```text
1. openspec-specs
2. db-models-migrations
3. domain-business-logic
4. bot-ui-callbacks-messages
5. async-jobs-workers
6. tests
7. docs
8. ci-infra
9. unrelated-or-suspicious
```

Zone `docs` means ordinary project documentation only.
It does **not** include `.cursor/commands/**`, `.cursor/skills/**`,
`.cursor/rules/**`, `.cursor/agents/**`, `.cursor/static-check/**`,
`.cursor/pipeline/**`, `.cursor/antipattern-gate/**`, `.cursor/devops/**`,
`.cursor/opsx-resolve-conflict/**`,
`.agents/**`, `.github/prompts/**`, `.github/skills/**`,
`.github/copilot-instructions.md`, `.github/git-commit-instructions.md`,
or `AGENTS.md`.

## Automatic commit grouping

Create commits in this preferred order:

```text
1. spec(openspec)
2. db/models/migrations
3. domain/business logic
4. bot UI/callbacks/messages
5. async jobs/workers
6. tests
7. docs
8. chore/cleanup
```

Do not include `unrelated-or-suspicious` files in any automatic commit.
Do not include process-surface files in any automatic commit.

If suspicious files exist:
- leave them unstaged;
- report them at the end.

## Staging rules

Prefer whole-file staging when all changes in the file belong to one logical group.

Use interactive patch staging when a file mixes zones:

```bash
git add -p <file>
```

If interactive staging is not practical in the current agent environment:
- do not stage that file;
- report it as `requires manual git add -p`;
- continue with safe whole-file commits only.

Before every commit, run:

```bash
git diff --cached --stat
git diff --cached --name-status
git diff --cached
```

If the staged diff contains unrelated changes, unstage and stop:

```bash
git restore --staged <file>
```

## Verification rules

Pre-commit checks are gated by `CHECK_MODE`. Scope = files **staged for the current commit group** (not the whole dirty tree).

### When checks run

| Path | Behavior |
|---|---|
| Preview (`GO` absent) | List `CHECK_MODE` + per-group matrix; **do not run** checks |
| Execute (`GO` present) | After staging each group and inspecting staged diff, **run** the matrix for that group before `git commit` |

Any FAIL / BLOCKED / non-zero exit / FAIL_CLOSED → **COMMIT STOP** for the entire `/opsx-commit` run:
- do **not** commit the current group;
- do **not** start or continue any later groups;
- leave working tree as-is (including already-created earlier commits in this run, if any);
- report the failing step + commands + result;
- do not auto-fix production.
One failed check ends the commit operation.

### Infer related tests

From staged production / test paths, infer related tests under `tests/` (same module/package, adjacent `test_*` files, explicit paired paths). Prefer Poetry:

```bash
poetry run pytest -m unit <related_unit_paths> -q
poetry run pytest -m integration <related_integration_paths> -q
```

Use `bash .cursor/static-check/bin/run.sh -- pyright-strict` and
`bash .cursor/static-check/bin/run.sh -- mypy .` (or the registry-equivalent human cmds) for typing tools so the venv runner matches `/opsx-static-check`.

### Non-Python / docs / OpenSpec-only groups

If the staged set has **no** production or test Python (`.py`):

- skip pyright / mypy / pytest with an explicit Verification note;
- `FAST_CHECK` → `Verification: not_applicable_no_python` is allowed;
- `FULL_CHECK` → still run applicable AI soft-chain steps on the staged diff (at least antipattern SCAN when base resolves); skip steps that cannot apply.

### Production Python present — FAIL_CLOSED on missing tests

If staged production `.py` changed and no related tests can be inferred:

- under both `FULL_CHECK` and `FAST_CHECK` → **COMMIT STOP** (do not commit; do not continue later groups);
- report `Verification: FAIL_CLOSED - no related tests inferred for production Python`;
- legacy “commit allowed if no focused test inferred” does **not** apply.

### FAST_CHECK matrix

When production/test Python is present:

1. `pyright-strict` (path-scoped when the tool allows; else project `pyright-strict`)
2. Related **unit** tests only (`pytest -m unit …`)

Do **not** run: mypy, integration tests, AI soft-chain.

### FULL_CHECK matrix (default)

When production/test Python is present:

1. Related **unit** tests, then related **integration** tests (path-focused; honor existing markers; do not invent live/destructive runs beyond project norms)
2. `pyright-strict`
3. `mypy`
4. AI soft-chain audits — run **inline** as READ_ONLY procedures (do not require a separate owner chat hop), scoped to the staged/product diff vs resolved `base=`:
   - a) `/opsx-pyright-strict-coverage` semantics (changed production Python ⊆ strict include)
   - b) `/opsx-external-call-coverage` semantics
   - c) `/opsx-performance-review` when that command’s existing trigger applies; else record `NOT_APPLICABLE`
   - d) `/opsx-antipattern-gate` SCAN semantics

If `base=` cannot be resolved → BLOCKED for AI steps → **COMMIT STOP** (do not commit; do not continue later groups).

### High-risk zones (report visibility)

When these zones change, they must be visible in the final report (checks still follow `CHECK_MODE`):

- campaign state;
- paid/free boundary;
- bid/cost/reallocation logic;
- DB model/migration behavior;
- async/concurrency;
- bot callbacks/messages.

### Commit message Verification

Must list `CHECK_MODE`, commands run, and PASS/FAIL/SKIP/NOT_APPLICABLE per step. Do not claim equivalence to `/opsx-static-check` MODE labels.

## Commit message format

Use this subject format:

```text
type(scope): English summary (русское пояснение)
```

Allowed types:

```text
spec
feat
fix
refactor
test
docs
chore
ci
perf
```

Examples:

```text
spec(openspec): document invite partner rollout (описать запуск партнёрских инвайтов)
feat(invites): add invite activation flow (добавить поток активации инвайтов)
fix(campaigns): preserve bot_active on landing open (сохранить bot_active при открытии лендинга)
test(invites): cover invite activation regressions (покрыть регрессии активации инвайтов)
chore(docs): refresh contributor setup notes (обновить заметки по setup)
```

Use detailed body:

```text
What:
- ...

Why:
- ...

How:
- ...

Verification:
- ...

OpenSpec:
- change-id: ...

Risk:
- ...
```

Create commits with multiple `-m` arguments:

```bash
git commit \
  -m "type(scope): English summary (русское пояснение)" \
  -m "What:
- ...

Why:
- ...

How:
- ...

Verification:
- ...

OpenSpec:
- change-id: <change-id>

Risk:
- ..."
```

## Execution mode

If `GO` is absent, output only:

```text
Commit plan:
- CHECK_MODE: FULL_CHECK | FAST_CHECK
- base_ref: <resolved or pending>
- proposed commits
- files per commit
- check matrix per commit (commands that WOULD run; not executed)
- suspicious files
- process-surface files left for /opsx-meta-commit
```

If `GO` is present, execute the commit plan.

For each commit:
1. Stage files for that group.
2. Inspect staged diff.
3. Run the `CHECK_MODE` matrix for that group's staged paths (see Verification rules).
4. On all required steps PASS (or allowed SKIP / NOT_APPLICABLE) → commit with detailed message.
5. On any FAIL / BLOCKED / FAIL_CLOSED → **COMMIT STOP**: do not commit this group; do not process later groups; report and end the run.
6. Continue to the next group only after the current group's full check matrix passed.

If a verification command fails (or any check step is FAIL / BLOCKED / FAIL_CLOSED):
- **COMMIT STOP** immediately for the whole run;
- do not commit the failing group;
- do not continue with remaining groups;
- leave working tree as-is;
- report what failed.

If a group requires manual `git add -p`:
- skip that group;
- continue with safe groups;
- report skipped files.

## Final report

After execution, output:

```text
Done:
- commits created:

Skipped:
- files requiring manual add -p:
- suspicious/unrelated files:
- groups not committed:

OUT_OF_SCOPE_REDIRECT:
- process-surface files left for /opsx-meta-commit:

CHECK_MODE:
- FULL_CHECK | FAST_CHECK

Verification:
- passed:
- failed:
- blocked:
- skipped / not_applicable:

Next:
- if process surfaces remain dirty: /opsx-meta-commit
- optional later: /opsx-pipeline UPDATE (refresh /opsx-commit graph node for check modes)
- recommended PR command, but do not push
```

## Absolute prohibitions

Never run:

```bash
git push
git push --force
git rebase
git merge
git reset --hard
git clean -fd
git checkout .
docker compose up
kubectl
alembic upgrade
alembic downgrade
```
