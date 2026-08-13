---
description: "Atomic local commits for product/code/OpenSpec/docs. AI/process surfaces redirect to /opsx-admin-command-commit."
argument-hint: "[FULL_CHECK|FAST_CHECK] GO [optional change-id / base=<ref> / context]"
---

# /opsx-commit

You are allowed to create local git commits ONLY when the user input contains the exact token `GO`.

If `GO` is absent:
- do not modify files;
- do not stage files;
- do not commit;
- output only the proposed commit plan (include `CHECK_MODE` + per-group check matrix; do **not** run the matrix).

## Commit-only git allowlist (mandatory)

This command may mutate git **only** to create local commits. Nothing else.

**Allowed mutating git:**
- `git add` / path staging for the current commit group
- `git commit` (authorized only with exact token `GO`)
- `git restore --staged <file>` only to unstage unsafe / out-of-scope / unrelated staged paths before stopping a group

**Allowed read-only git:** preflight `branch` / `status` / `diff` / `log` (and merge-base resolution for `FULL_CHECK` `base=<ref>` when required).

**Forbidden (non-exhaustive — if it advances history, remotes, or a sequencer, it is forbidden):**
- any `git rebase` form, including `--continue`, `--skip`, `--abort`, `--edit-todo`, `--autosquash`
- any `git merge` / `git cherry-pick` progression (`--continue`, `--skip`, `--abort`)
- `git push` / force-push / remote updates
- `git reset --hard`, `git clean -fd`, destructive checkout that discards work or advances a rebase todo
- deploy, restart services, production migrations, secrets access

## Content-edit ban (mandatory — GO does not heal)

This command may change the **git index / local commit history** only.
It must **not** rewrite working-tree **content** to make verification pass.

**Forbidden on the GO path (and preview):**
- `Write` / `StrReplace` / patch / format of `app/**`, `tests/**`, `alembic_/**`,
  `openspec/**`, `pyrightconfig*.json`, `pyproject.toml`, or any other product /
  config / test file to satisfy pyright, mypy, pytest, coverage, or soft-chain
- “heal-to-green”: editing production or configs after a red check, then
  re-running the matrix in the same `/opsx-commit` turn
- applying `/opsx-pyright-strict-coverage` **GO** (include writes),
  `/opsx-fix-types`, `/opsx-test`, or any other writer command as a side effect
- inventing product semantics while clearing conflict markers

**Allowed content operations:** none for product/config. Staging (`git add`)
may include paths that are **already** dirty or **already** conflict-resolved
in the working tree before this command started. Any still-unmerged path, or
any conflict marker in the commit-group files → **COMMIT STOP** (see
**Unresolved conflicts hard gate**). Never clear markers or invent resolution
semantics here; leave that to the owner (or a separate fix command).

`GO` authorizes commit creation only. It does **not** authorize heal-to-green.

After the authorized commit(s) finish, **stop**. Do not “finish the rebase”, “keep going”, or drive any in-progress sequencer.

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
4. Check tokens do not authorize process-surface commits (still `/opsx-admin-command-commit`).

Optional `base=<ref>` in `$ARGUMENTS` is used by `FULL_CHECK` AI soft-chain steps. If absent, resolve merge-base against upstream tracking branch, else `stage`, else `main` / `master`; document the chosen ref. If base cannot be resolved on `FULL_CHECK` when AI steps apply → do not commit that group (`BLOCKED` for AI steps).

`FAST_CHECK` is **not** equivalent to `/opsx-static-check FAST` (this FAST omits mypy by design).

## Purpose

Analyze the current working tree and create safe atomic local commits by logical zones
for **product/code/OpenSpec/docs** changes.

Process surfaces (AI/process artifacts: commands, rules, skills, agents,
static-check, prompt/skill mirrors, root agent guides) are **out of scope**.
They belong exclusively to `/opsx-admin-command-commit`.

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
NEXT_ACTION: /opsx-admin-command-commit
```

If the dirty tree is **only** process surfaces, do not invent product commits:

```text
STATUS: OUT_OF_SCOPE_REDIRECT
NEXT_ACTION: /opsx-admin-command-commit
DO_NOT_DO_YET: commit process files via /opsx-commit
```

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

### Unresolved conflicts hard gate (mandatory)

After `git status --short` (and before any `git add` / `git commit`), **COMMIT STOP**
if either condition holds:

1. **Unmerged paths** — porcelain status shows any unmerged index state
   (`UU`, `AA`, `DD`, `AU`, `UA`, `DU`, `UD`) or status text reports
   `Unmerged paths` / both-modified without resolution.
2. **Conflict markers** — any file in the current commit group (already staged
   or about to be staged) contains unresolved conflict marker lines
   (`<<<<<<<`, `=======`, `>>>>>>>`).

On hit:

```text
STATUS: COMMIT_STOP
WHY: unresolved_conflicts
DO_NOT_DO_YET: clear/choose conflict markers inside /opsx-commit; git add of unmerged paths; rebase/merge/cherry-pick --continue/--skip/--abort; push; force-push
```

- do **not** stage or commit;
- do **not** clear, edit, or invent resolution for conflict markers;
- leave resolution to the owner (or a separate fix command).

Already-resolved paths (no unmerged state, no markers) may still be staged.

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

### Sequencer / rebase in progress (mandatory)

Detect an in-progress git sequencer from `git status` and/or presence of
`.git/rebase-merge`, `.git/rebase-apply`, `MERGE_HEAD`, `CHERRY_PICK_HEAD`,
`REVERT_HEAD`.

If a sequencer is in progress:
- the **Unresolved conflicts hard gate** still applies first (any unmerged /
  markers → **COMMIT STOP**, no stage/commit);
- only when that gate is clear: planning and (with `GO`) creating the
  authorized local commit(s) remain allowed;
- after those commits (or after plan-only output), **hard stop** this command;
- never run rebase/merge/cherry-pick `--continue|--skip|--abort` or otherwise
  advance the sequencer;
- include in the report:

```text
REBASE_OR_SEQUENCER_IN_PROGRESS_LEFT_TO_OWNER: yes
DO_NOT_DO_YET: git rebase/--continue/--skip/--abort; merge/cherry-pick progression; push; force-push
```

Owner continues, skips, or aborts the sequencer **outside** this command.

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
`.cursor/pipeline/**`, `.agents/**`, `.github/prompts/**`, `.github/skills/**`,
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
- do **not** auto-fix production, tests, migrations, or configs
  (see **Content-edit ban**);
- do **not** edit `pyrightconfig*.json` / includes to clear coverage FAIL;
- emit the **human-native exit** block below (mandatory; not prose-only).

One failed check ends the commit operation. No heal-to-green inside this command.

### Human-native exit (COMMIT STOP / PARTIAL — mandatory)

On every **COMMIT STOP**, and on **PARTIAL** end when blockers remain, print this
block **as the owner-facing entrance** (bookkeeping `Done`/`Skipped` may appear
above it, but must not replace it):

```text
STATUS: COMMIT_STOP | PARTIAL
WHAT_HAPPENED: <1–2 lines what this run did / stopped on>
WHY: <blocker class: typing | MISSING_FROM_INCLUDE | HIT_EXCLUDE | test_fail | FAIL_CLOSED | blocked_preflight | …>
FAILED_STEP: <exact command + short result>
CHECK_MODE: FAST_CHECK | FULL_CHECK
```

For **typing / pyright / mypy FAIL** (and likewise for **unit/test FAIL** with
known nodeids), the entrance MUST also include an actionable diagnostic block
**above** `OWNER_RUN_COMMAND` — not only a bare next-command name:

```text
ERROR_SUMMARY: <N> errors (show ≤12 lines; if more, say "+<remaining> more")
- <path>:<line> - <code> - <short message>
STAGED_HITS: <paths from the current staged commit group that appear in FAIL>
OUTSIDE_STAGED_HITS: <other dirty/include paths that appear in FAIL, or none>
```

Rules for that block:

1. Prefer **STAGED_HITS** lines first in `ERROR_SUMMARY`; then outside hits.
2. Cap at **12** diagnostic lines; never dump an unbounded tool log into chat.
3. Keep bare project `pyright-strict` SoT (do **not** path-scope to invent a
   second type gate). Attribution is mandatory so the owner sees whether the
   staged group itself is red vs poisoned by unstaged dirty include files.
4. If **any** `STAGED_HITS` → `WHY: typing` (or `test_fail` for pytest) as usual.
5. If **only** `OUTSIDE_STAGED_HITS` → still **COMMIT STOP** (working tree is
   red vs owner SoT), but `WHAT_HAPPENED` / `WHY` MUST state the blocker is
   **outside the staged commit group** (e.g. unstaged production / dirty
   `pyrightconfig_strict.json` include). Put staging-order / remaining dirty
   notes under `ALSO_OK` only; primary remains the heal command below.
6. Do **not** heal-to-green inside this command.

Then print:

```text
OWNER_RUN_COMMAND:
```

Then **one** fenced literal command (fill known args; no empty placeholders when
paths/nodeids/diagnostics are known):

| WHY / class | Primary `OWNER_RUN_COMMAND` |
|---|---|
| typing / pyright / mypy errors | `/opsx-fix-types tool=<pyright-strict\|mypy> command="<exact failed command>" scope=<STAGED_HITS paths>` then paste the same `ERROR_SUMMARY` lines as raw diagnostic text in the fence (so `/opsx-fix-types` can triage without re-hunt). Bare `/opsx-fix-types` alone is **not** sufficient when diagnostics are known. |
| `MISSING_FROM_INCLUDE` / `HIT_EXCLUDE` | `/opsx-pyright-strict-coverage` (list OUT paths in body above fence) |
| unit/test FAIL | `/opsx-test-triage` (include failing path / nodeid when known; put failing nodeids in `ERROR_SUMMARY`) |
| `FAIL_CLOSED` (no related tests) | `/opsx-test-triage` + list uncovered production paths |
| heal already done; finish commits | `/opsx-commit FAST_CHECK GO` or `/opsx-commit FULL_CHECK GO` (match this run’s mode) |
| process surfaces only | `/opsx-admin-command-commit` |

Then:

```text
NEXT_ACTION: <same literal as OWNER_RUN_COMMAND>
ALSO_OK: <optional secondary commands; never replace primary>
DO_NOT_DO_YET: heal-to-green inside /opsx-commit; rebase --continue/--skip/--abort; push; force-push
```

When multiple leftover classes exist, pick **one primary** by priority:

1. FAIL that stopped the run
2. `MISSING_FROM_INCLUDE` / `HIT_EXCLUDE` leftovers
3. test / triage leftovers
4. `/opsx-commit … GO` for remaining in-include groups

Put all other heal/finish commands under `ALSO_OK` only. Do not bury the primary
entrance in a bullet list without a fenced `OWNER_RUN_COMMAND`.

### Infer related tests

From staged production / test paths, infer related tests under `tests/` (same module/package, adjacent `test_*` files, explicit paired paths). Prefer Poetry.

Path-focused related suites (default for commit gates — **no** xdist):

```bash
poetry run pytest -m unit <related_unit_paths> -q
poetry run pytest -m integration <related_integration_paths> -q
```

Only if a commit group explicitly needs the **full** unit marker suite (no path filter):

```bash
poetry run pytest -m unit -n 8 --dist=worksteal -q
```

Use `bash .cursor/static-check/bin/run.sh -- pyright-strict` and
`bash .cursor/static-check/bin/run.sh -- mypy .` (or the registry-equivalent human cmds) for typing tools so the venv runner matches `/opsx-static-check`.

### pyright-strict SoT (include[] — mandatory)

Commit-gate `pyright-strict` MUST match owner terminal / `/opsx-static-check`:

```bash
bash .cursor/static-check/bin/run.sh -- pyright-strict
```

**Default: no path arguments.** Bare project run uses
`pyrightconfig_strict.json` `include[]` only (same as owner alias).

**Forbidden:** passing staged (or any) paths that are **outside** strict
`include[]` into `run.sh -- pyright-strict …`. Explicit path args make
pyright typecheck files the project SoT intentionally skips, which causes
false `COMMIT STOP` vs owner `pyright-strict` → 0 errors.

**Optional path-scope (rare):** only
`intersection(staged_production_py, strict_include)`. Never pass
`MISSING_FROM_INCLUDE` / out-of-include paths to pyright.

**Out-of-include staged production `.py`:** coverage disposition, **not** a
path-scoped type FAIL:

- report `MISSING_FROM_INCLUDE` (or `HIT_EXCLUDE`);
- **COMMIT STOP** with `NEXT_ACTION: /opsx-pyright-strict-coverage`
  (owner may later `GO` to extend `include[]`);
- do **not** invent type errors by forcing pyright on those paths;
- do **not** edit `pyrightconfig*.json` from this command.

Under `FAST_CHECK`, run a **lightweight include-intersection** check on staged
production Python (same dispositions as coverage SCAN) before or beside bare
`pyright-strict`. Under `FULL_CHECK`, the soft-chain coverage SCAN remains
authoritative for the same rule.

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

1. Lightweight strict-include intersection on staged production `.py`
   (`MISSING_FROM_INCLUDE` / `HIT_EXCLUDE` → **COMMIT STOP** →
   `/opsx-pyright-strict-coverage`; never path-scoped pyright on those paths)
2. Bare project `pyright-strict` (no path args; see **pyright-strict SoT**)
3. Related **unit** tests only (`poetry run pytest -m unit <related_unit_paths> …` — path-focused, no `-n`)

Do **not** run: mypy, integration tests, AI soft-chain (except the lightweight
include check above).

### FULL_CHECK matrix (default)

When production/test Python is present:

1. Related **unit** tests, then related **integration** tests (path-focused; honor existing markers; do not invent live/destructive runs beyond project norms)
2. Bare project `pyright-strict` (no path args; see **pyright-strict SoT**)
3. `mypy`
4. AI soft-chain audits — run **inline** as **report-only / READ_ONLY**
   procedures (do not require a separate owner chat hop), scoped to the
   staged/product diff vs resolved `base=`:
   - a) `/opsx-pyright-strict-coverage` **SCAN** semantics only
     (changed production Python ⊆ strict include) — **never** write `include[]`
   - b) `/opsx-external-call-coverage` semantics (report only)
   - c) `/opsx-performance-review` when that command’s existing trigger applies; else record `NOT_APPLICABLE`
   - d) `/opsx-antipattern-gate` SCAN semantics (report only)

Soft-chain FAIL / `MISSING_FROM_INCLUDE` / `HIT_EXCLUDE` → **COMMIT STOP**
(same rules as other check FAIL). Do **not** apply coverage `GO` or edit
`pyrightconfig*.json` from this command.

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
- process-surface files left for /opsx-admin-command-commit
```

If `GO` is present, execute the commit plan.

For each commit:
1. Stage files for that group.
2. Inspect staged diff.
3. Run the `CHECK_MODE` matrix for that group's staged paths (see Verification rules).
4. On all required steps PASS (or allowed SKIP / NOT_APPLICABLE) → commit with detailed message.
5. On any FAIL / BLOCKED / FAIL_CLOSED → **COMMIT STOP**: do not commit this group; do not process later groups; emit **human-native exit** and end the run.
6. Continue to the next group only after the current group's full check matrix passed.

If a verification command fails (or any check step is FAIL / BLOCKED / FAIL_CLOSED):
- **COMMIT STOP** immediately for the whole run;
- do not commit the failing group;
- do not continue with remaining groups;
- leave working tree as-is;
- emit **human-native exit** (`STATUS: COMMIT_STOP` + fenced `OWNER_RUN_COMMAND`).

If a group requires manual `git add -p`:
- skip that group;
- continue with safe groups;
- report skipped files.

When a sequencer/rebase is in progress: after the last authorized commit group
for this run (or immediately after plan-only), end the run. Do not continue the
sequencer. Do not interpret remaining dirty tree or rebase stops as work for
this command beyond the commit allowlist.

## Final report

After execution, output bookkeeping **plus** the human-native exit when status is
`COMMIT_STOP` or `PARTIAL` with remaining blockers.

```text
STATUS: COMMITTED | PARTIAL | COMMIT_STOP | BLOCKED

Done:
- commits created:

Skipped:
- files requiring manual add -p:
- suspicious/unrelated files:
- groups not committed:

OUT_OF_SCOPE_REDIRECT:
- process-surface files left for /opsx-admin-command-commit:

CHECK_MODE:
- FULL_CHECK | FAST_CHECK

Verification:
- passed:
- failed:
- blocked:
- skipped / not_applicable:

REBASE_OR_SEQUENCER_IN_PROGRESS_LEFT_TO_OWNER:
- yes | no
```

When `STATUS` is `COMMIT_STOP` or `PARTIAL` (blockers remain), **also** emit the
mandatory human-native exit (see **Human-native exit** above), including
`ERROR_SUMMARY` / `STAGED_HITS` / `OUTSIDE_STAGED_HITS` when the FAIL class is
typing or test_fail:

```text
WHAT_HAPPENED:
WHY:
FAILED_STEP:
ERROR_SUMMARY:   # required for typing / test_fail when diagnostics known
STAGED_HITS:
OUTSIDE_STAGED_HITS:
OWNER_RUN_COMMAND:
```

```text
<one fenced primary heal/finish command — for typing: filled /opsx-fix-types + raw errors>
```

```text
NEXT_ACTION: <same as OWNER_RUN_COMMAND>
ALSO_OK:
DO_NOT_DO_YET:
- heal-to-green inside /opsx-commit
- git rebase (any form, including --continue/--skip/--abort/--edit-todo)
- merge/cherry-pick progression; push; force-push
```

When `STATUS` is `COMMITTED` with a clean in-scope tree, a short success note is
enough; still list sequencer handoff under `DO_NOT_DO_YET` / ALSO_OK if rebase
is in progress (owner continues outside this command).

## Absolute prohibitions

Never run (including during an in-progress rebase/merge/cherry-pick):

```bash
git push
git push --force
git rebase
git rebase --continue
git rebase --skip
git rebase --abort
git rebase --edit-todo
git merge
git merge --continue
git merge --abort
git cherry-pick --continue
git cherry-pick --skip
git cherry-pick --abort
git reset --hard
git clean -fd
git checkout .
docker compose up
kubectl
alembic upgrade
alembic downgrade
```

Never “keep going” on a rebase after `git commit`. Sequencer control belongs to the owner.

Never heal-to-green: no `Write` / `StrReplace` on product, tests, migrations,
or `pyrightconfig*.json` to clear a red check; no applying writer commands
(`/opsx-fix-types`, `/opsx-pyright-strict-coverage GO`, etc.) from this command.
On FAIL → **COMMIT STOP** + mandatory human-native exit (`OWNER_RUN_COMMAND` /
`NEXT_ACTION` fenced; see Content-edit ban and **Human-native exit**).
