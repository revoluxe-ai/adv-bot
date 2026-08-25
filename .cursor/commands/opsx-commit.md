---
description: "Atomic local Git commits for product/code/OpenSpec/docs. Git packaging only — not a verification gate. Process surfaces redirect to /opsx-admin-command-commit."
argument-hint: "GO [optional change-id / context / ALL]"
---

# /opsx-commit

**Role:** Git packaging — classify dirty paths, stage exact paths, create atomic
local commits, return commit SHAs. This command does **not** own product quality
verification.

## Architectural invariant (mandatory)

```text
Commit creation MUST NOT be blocked by absence, staleness, or failure of
product verification.

Allowed: commit when verification=PENDING | FAIL | ABSENT.
Forbidden: run or require static-check, tests, build, browser/security/scenario
checks; requiring verification ledger COMPLETE; or verify/archive PASS as a commit
precondition.
```

Quality gates belong to the verification/integration contour (`/opsx-static-check`,
`/opsx-verify`, `/opsx-archive`, merge/land/release). They are **not** replayed
here.

## Authorization

Create local git commits **only** when user input contains the exact token `GO`.

If `GO` is absent:

- do not modify files;
- do not stage files;
- do not commit;
- output only the proposed commit plan.

Optional scope tokens (case-sensitive when present):

| Token | Meaning |
|---|---|
| `ALL` | Commit all in-scope dirty paths per grouping rules (never `git add .` / `-A`) |
| `<change-id>` | Prefer paths under `openspec/changes/<change-id>/` when classifying |

## Commit-only git allowlist (mandatory)

This command may mutate git **only** to create local commits.

**Allowed mutating git:**

- `git add <exact-path>` for the current commit group
- `git commit` (authorized only with exact token `GO`)
- `git restore --staged <file>` only to unstage unsafe / out-of-scope paths

**Allowed read-only git:** `branch`, `status`, `diff`, `log`.

**Forbidden (non-exhaustive):**

- `git add .`, `git add -A`, broad `git add` without explicit paths
- any `git rebase` / `git merge` / `git cherry-pick` progression
- `git push`, force-push, remote updates
- `git reset --hard`, `git clean -fd`, destructive checkout
- deploy, migrations, secrets access

## Verification boundary (mandatory)

This command **must not**:

- run `/opsx-static-check`, pytest, mypy, pyright, build, npm, browser,
  security review, scenario coverage, or any quality gate;
- requiring static-check FULL/FAST receipt or command-bus receipt;
- blocking commit because verification evidence is missing, stale, or failed;
- requiring verification ledger COMPLETE or verify/archive PASS.

If Owner pasted verification results, they may appear **only** as optional
commit-body notes supplied by Owner — never as executable gates.

## Content-edit ban (mandatory)

This command may change the **git index / local commit history** only. It must
**not** rewrite working-tree content to fix product issues.

**Forbidden:** `Write` / `StrReplace` on `app/**`, `tests/**`, `openspec/**`,
configs, or any product file. Never clear conflict markers or invent resolution
semantics here.

Staging may include paths already dirty or already conflict-resolved before
this command started. Unmerged paths or conflict markers in commit-group files
→ **COMMIT STOP** (see **Unresolved conflicts**).

## Purpose

Analyze the working tree and create safe atomic local commits by logical zones
for **product/code/OpenSpec/docs** changes.

Process surfaces (commands, rules, skills, agents, static-check, mirrors,
`AGENTS.md`) are **out of scope** → `/opsx-admin-command-commit`.

**Source resolution:** Follow `.cursor/commands/opsx-source-resolution.md`. If
an OpenSpec change-id is provided or exactly one `openspec/changes/<id>/` is
touched, read that change via canonical paths only.

## Process-surface exclusion (mandatory)

Never stage or commit:

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

If the dirty tree is **only** process surfaces:

```text
STATUS: OUT_OF_SCOPE_REDIRECT
NEXT_ACTION: /opsx-admin-command-commit
```

## Mandatory preflight

Follow `.cursor/commands/opsx-execution-preflight.md`.

```bash
git branch --show-current
git status --short
git diff --stat
git diff --name-status
git diff --cached --stat
git diff --cached --name-status
```

Do not run `git fetch` unless remote state becomes required.

### Unresolved conflicts hard gate

**COMMIT STOP** before any `git add` / `git commit` when:

1. Unmerged index state (`UU`, `AA`, `DD`, `AU`, `UA`, `DU`, `UD`) or
   `Unmerged paths` in status.
2. Conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) in files to be staged.

```text
STATUS: COMMIT_STOP
WHY: unresolved_conflicts
NEXT_ACTION: resolve conflicts outside /opsx-commit, then rerun /opsx-commit GO
```

### Protected branch gate

Block when branch is `main`, `master`, `prod`, or `production` unless input
contains exact token `GO_ON_PROTECTED_BRANCH`. Never push.

### Sequencer / rebase in progress

If rebase/merge/cherry-pick is in progress:

- unresolved-conflicts gate still applies first;
- with `GO`, authorized local commit(s) are allowed when conflicts are clear;
- **hard stop** after commits — never advance the sequencer;
- report `REBASE_OR_SEQUENCER_IN_PROGRESS_LEFT_TO_OWNER: yes`.

## Detect OpenSpec change

If exactly one `openspec/changes/<change-id>/` is touched, use it. If user
provided change-id in `$ARGUMENTS`, prefer it. Multiple change-ids → output
split plan; ask Owner to rerun with one change-id.

## Classification zones

Classify every in-scope changed file:

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

Never classify process-surface paths here — redirect only.

## Automatic commit grouping

Preferred order:

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

Do not include `unrelated-or-suspicious` or process-surface files. Leave
suspicious files unstaged and report them.

## Staging rules (mandatory)

- **Exact-path staging only** — never `git add .` or `git add -A`.
- Prefer whole-file staging when the file belongs to one group.
- Mixed-zone file → `git add -p <file>`; if impractical, skip and report
  `requires manual git add -p`.
- Before each commit: `git diff --cached --stat`, `--name-status`, full cached diff.
- Unrelated staged changes → `git restore --staged <file>` and **COMMIT STOP**
  for that group.

## Commit message format

Subject (English + Russian parenthetical):

```text
type(scope): English summary (русское пояснение)
```

Types: `spec`, `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`, `perf`.

Body sections: What, Why, How, OpenSpec (change-id), Risk.

Optional **Verification** subsection: only Owner-supplied evidence or
`not evaluated by /opsx-commit` — never claim checks were run by this command.

## Execution mode

**Preview (`GO` absent):**

```text
Commit plan:
- proposed commits
- files per commit (exact paths)
- suspicious / unstaged files
- process-surface redirect list
```

**Execute (`GO` present):** for each group:

1. Stage exact paths.
2. Inspect staged diff.
3. Commit with detailed message.
4. Record commit SHA.
5. Continue to next group.

On git-safety blockers → **COMMIT STOP**; do not process later groups unless
earlier groups already committed (report `PARTIAL`).

## Final report

```text
STATUS: COMMITTED | PARTIAL | COMMIT_STOP | BLOCKED | OUT_OF_SCOPE_REDIRECT

Done:
- commits created: <sha> <subject> (paths…)

Remaining uncommitted:
- <paths>

Skipped:
- requires manual git add -p:
- suspicious/unrelated:

OUT_OF_SCOPE_REDIRECT:
- process files → /opsx-admin-command-commit

REBASE_OR_SEQUENCER_IN_PROGRESS_LEFT_TO_OWNER: yes | no

NEXT_ACTION:
- verification (optional, separate contour): /opsx-static-check | /opsx-verify
- PR (optional): /opsx-create-pr
- process commit: /opsx-admin-command-commit
```

PR creation and verification are **optional follow-ups**, not prerequisites.

## Absolute prohibitions

Never run inside `/opsx-commit`:

```bash
git push
git add .
git add -A
poetry run pytest
bash .cursor/static-check/bin/run.sh
/opsx-static-check
/opsx-verify
/opsx-fix-types
/opsx-test
npm run build
docker compose up
kubectl
alembic upgrade
alembic downgrade
```

Never heal-to-green. Never advance rebase/merge/cherry-pick sequencers.description: "Atomic local commits for product/code/OpenSpec/docs. AI/process surfaces redirect to /opsx-meta-commit."
argument-hint: "[FULL_CHECK|FAST_CHECK] GO [optional change-id / base=<ref> / context]"
You are allowed to create local git commits ONLY when the user input contains the exact token `GO`.
- output only the proposed commit plan (include `CHECK_MODE` + per-group check matrix; do **not** run the matrix).
Never push, merge, rebase, force-push, deploy, restart services, run migrations against production, or touch secrets.
## User input
$ARGUMENTS
## Check mode (mandatory)
Parse exact case-sensitive tokens in `$ARGUMENTS`:
| `FULL_CHECK` | Full pre-commit matrix (also the **default** when neither token is present) |
| `FAST_CHECK` | Fast pre-commit matrix (overrides default) |
Rules:
1. If **both** `FULL_CHECK` and `FAST_CHECK` are present → `STATUS: BLOCKED_AMBIGUOUS_CHECK_MODE`; do not stage or commit.
2. If neither is present → `CHECK_MODE=FULL_CHECK`.
3. `CHECK_MODE` is **not** commit authorization. `GO` is still required to stage/commit.
4. Check tokens do not authorize process-surface commits (still `/opsx-meta-commit`).
Optional `base=<ref>` in `$ARGUMENTS` is used by `FULL_CHECK` AI soft-chain steps. If absent, resolve merge-base against upstream tracking branch, else `stage`, else `main` / `master`; document the chosen ref. If base cannot be resolved on `FULL_CHECK` when AI steps apply → do not commit that group (`BLOCKED` for AI steps).
`FAST_CHECK` is **not** equivalent to `/opsx-static-check FAST` (this FAST omits mypy by design).
Analyze the current working tree and create safe atomic local commits by logical zones
Process surfaces (AI/process artifacts: commands, rules, skills, agents,
static-check, prompt/skill mirrors, root agent guides) are **out of scope**.
They belong exclusively to `/opsx-meta-commit`.
**Source resolution:** Follow `.cursor/commands/opsx-source-resolution.md`. If an OpenSpec change-id is provided or exactly one `openspec/changes/<id>/` is touched, read that change via canonical paths only; do not inventory all changes.
Never stage or commit these paths; leave them untouched and redirect:
.cursor/antipattern-gate/**
.cursor/devops/**
.cursor/opsx-resolve-conflict/**
NEXT_ACTION: /opsx-meta-commit
If the dirty tree is **only** process surfaces, do not invent product commits:
NEXT_ACTION: /opsx-meta-commit
DO_NOT_DO_YET: commit process files via /opsx-commit
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
Commit bodies MUST be detailed and useful for review:
- what changed;
- why it changed;
- how it was verified;
- OpenSpec change-id, if detected;
- risk notes, if any.
Primary body text should be English. Russian may appear in parentheses for clarity.
These git ops are **REQUIRED_FOR** commit planning (branch protection + change inventory). Apply budgets; on timeout return `blocked_preflight_timeout` rather than hanging.
OPERATION_REASON: atomic commit plan + protected-branch gate
REQUIRED_FOR: commit decision
SKIP_IF: never for /opsx-commit when GO path is taken (preview may use status/diff only)
TIME_BUDGET: branch 5s; status 10s; each diff 15s
FAILURE_BEHAVIOR: blocked_preflight_timeout / report missing fact; no retry loop
Run the smallest set that answers the need:
Do not run `git fetch` here unless remote state becomes REQUIRED_FOR.
Block execution if current branch is:
main
master
prod
production
unless the user input contains:
GO_ON_PROTECTED_BRANCH
Even with `GO_ON_PROTECTED_BRANCH`, never push.
Inspect changed OpenSpec files:
```powershell
Get-ChildItem -Path .\openspec\changes -Recurse -File -Depth 2 |
  Sort-Object FullName |
  ForEach-Object { $_.FullName }
If exactly one `openspec/changes/<change-id>/` is touched, use that as the OpenSpec change-id.
If the user provided a change-id in `$ARGUMENTS`, prefer it.
If multiple change-ids are touched:
- do not commit automatically;
- output the split plan;
- ask the user to rerun with the exact change-id.
When available, read:
openspec/changes/<change-id>/proposal.md
openspec/changes/<change-id>/design.md
openspec/changes/<change-id>/tasks.md
openspec/changes/<change-id>/specs/**/*.md
Use these files to detect unrelated changes.
Classify every **in-scope** changed file into one zone.
Process-surface paths listed above are never classified here — report redirect only.
Zone `docs` means ordinary project documentation only.
It does **not** include `.cursor/commands/**`, `.cursor/skills/**`,
`.cursor/rules/**`, `.cursor/agents/**`, `.cursor/static-check/**`,
`.cursor/pipeline/**`, `.cursor/antipattern-gate/**`, `.cursor/devops/**`,
`.cursor/opsx-resolve-conflict/**`,
`.agents/**`, `.github/prompts/**`, `.github/skills/**`,
`.github/copilot-instructions.md`, `.github/git-commit-instructions.md`,
or `AGENTS.md`.
Create commits in this preferred order:
Do not include `unrelated-or-suspicious` files in any automatic commit.
Do not include process-surface files in any automatic commit.
If suspicious files exist:
- leave them unstaged;
- report them at the end.
## Staging rules
Prefer whole-file staging when all changes in the file belong to one logical group.
Use interactive patch staging when a file mixes zones:
git add -p <file>
If interactive staging is not practical in the current agent environment:
- do not stage that file;
- report it as `requires manual git add -p`;
- continue with safe whole-file commits only.
Before every commit, run:
git diff --cached
If the staged diff contains unrelated changes, unstage and stop:
git restore --staged <file>
## Verification rules
Pre-commit checks are gated by `CHECK_MODE`. Scope = files **staged for the current commit group** (not the whole dirty tree).
### When checks run
| Path | Behavior |
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
poetry run pytest -m unit <related_unit_paths> -q
poetry run pytest -m integration <related_integration_paths> -q
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
Use this subject format:
Allowed types:
spec
feat
fix
refactor
test
docs
chore
ci
perf
Examples:
spec(openspec): document invite partner rollout (описать запуск партнёрских инвайтов)
feat(invites): add invite activation flow (добавить поток активации инвайтов)
fix(campaigns): preserve bot_active on landing open (сохранить bot_active при открытии лендинга)
test(invites): cover invite activation regressions (покрыть регрессии активации инвайтов)
chore(docs): refresh contributor setup notes (обновить заметки по setup)
Use detailed body:
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
Create commits with multiple `-m` arguments:
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
If `GO` is absent, output only:
- CHECK_MODE: FULL_CHECK | FAST_CHECK
- base_ref: <resolved or pending>
- files per commit
- check matrix per commit (commands that WOULD run; not executed)
- suspicious files
- process-surface files left for /opsx-meta-commit
If `GO` is present, execute the commit plan.
For each commit:
1. Stage files for that group.
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
After execution, output:
- commits created:
- files requiring manual add -p:
- suspicious/unrelated files:
- groups not committed:
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
Never run:
git push --force
git rebase
git merge
git reset --hard
git clean -fd
git checkout .
