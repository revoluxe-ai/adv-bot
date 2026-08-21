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

Never heal-to-green. Never advance rebase/merge/cherry-pick sequencers.
