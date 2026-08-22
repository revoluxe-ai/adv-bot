---
component_id: opsx.commands.meta_commit
component_version: 0.4.1
ownership: EMBEDDED_SHARED
runtime_class: ACTIVE
source_commit: a71601dba3b9f5cd0076ea7185bdbbe56eaf2e3f
source_path: .cursor/commands/opsx-meta-commit.md
source_blob_sha: 89aec347dfabd8b6999c1ea4021d5c0c520a5330
embedded_canonical_sha256: 94fae56b5cf1d6690784c7ea9c922ff4c2fccc81ec309c4595dfd6bd404ec10c
upstream_snapshot: .opsx/upstream/a71601dba3b9/.cursor/commands/opsx-admin-command-commit.md
required_adapters: ["opsx-lite"]
local_modification_note: "Projectize 2026-08-07: vue-npm dropped; poetry-python; clarify COMMITTED vs NOT_COMMITTED_THIS_RUN"
local_override_policy: TARGET_OVERRIDE_HIGHEST_PRIORITY
contract_id: OPSX-WB-META-SURFACE-01
newline_normalization: none
---

# TARGET OVERRIDE — HIGHEST PRIORITY

**Contract:** `OPSX-WB-META-SURFACE-01`  
**Runtime class:** `ACTIVE`  
**Precedence:** This override wins over the canonical source body for target paths, capabilities, safety stops, and authority.

### Target authority paths

- Changes: `openspec/changes/**`
- Policies: `openspec/policies/**`
- Decisions: `openspec/decisions/**`
- Schemas/templates: `openspec/schemas/**`
- Activation/provenance: `.opsx/registry/**`
- Frozen upstream: `.opsx/upstream/a71601dba3b9/`
- Adapter: `.opsx/adapters/poetry-python/README.md`
- Quality gates: `.opsx/project/quality-gates.md`

### Hard target bans

- Do not install dependencies / modify `package.json` or lockfile.
- Do not access production / Kubernetes / secrets.
- Do not push, open PR, rebase, force, or deploy.
- Do not activate WB/product domain assumptions from the source body.
- Replace Poetry/pytest/pyright/kubectl execution with capability checks; missing capability => unavailable or FAIL_CLOSED, never PASS-by-absence.
- Mandatory declared executable checks: per `.opsx/project/quality-gates.md` (poetry-python). `npm run build` is UNAVAILABLE / not applicable (vue-npm dropped; no root build script).
- Smoke/acceptance/lint/typecheck/frontend tests: UNAVAILABLE unless adapter says otherwise.

### Projectization gate

Read `.opsx/projectization.yaml` before any write.
If `status` != `COMPLETE` or `normal_commands_enabled` is false:

```text
STATUS: FAIL_CLOSED
REASON: OPSX_PROJECTIZATION_REQUIRED
NEXT_COMMAND: /opsx-projectize
```

Exempt: `/opsx-projectize` and `/opsx-projectize:GO`.

### ACTIVE allow

Owner unblocked this former-DEFERRED command (2026-08-03): execute canonical source-body semantics **after** remapping paths to target authority above.

Hard bans still apply. Missing Poetry/pytest/pyright/kubectl (and other undeclared source capabilities) => UNAVAILABLE or FAIL_CLOSED — never PASS-by-absence. Do not invent missing adapters or import source product dumps. File/process operations only on target authority paths.

### Target-local meta commit extensions (`OPSX-WB-META-COMMIT-01`)

- Canonical active name: `/opsx-meta-commit` (upstream body may still say admin-command-commit).
- **Process allowlist SoT:** `.opsx/sources.yaml` (`allowlist` / `hard_exclude`) —
  единый список с `/opsx-meta-update-snapshot` и process-exclusion у `/opsx-commit`.
  Canonical «In-scope surfaces» ниже — legacy template; при расхождении побеждает
  `sources.yaml` + этот OVERRIDE.
- **Local-only:** never update central snapshot or catalog repos. After success, if snapshot may be stale, recommend `/opsx-meta-update-snapshot` only.
- Every terminal report must include `ORIENTATION_HINT` with `NEXT_META: /opsx-meta`.
- **Owner scope map (mandatory mental model):**
  - **Default (no `ALL`):** ONLY current-chat in-scope process files; leave
    `LEFT_UNSTAGED_OUTSIDE_CHAT_SCOPE`; never invent a full-tree plan.
  - **`ALL`:** intentional cleanup of leftover in-scope process dirty tree after
    chats — inventory all in-scope dirty, split into logical meaning groups,
    propose/commit those groups (still not one silent blob); chat-provenance
    absent.
  - **`FULL_CHECK` / `FAST_CHECK`:** optional verify; default `FAST_CHECK` with
    or without `ALL`; neither replaces `GO`.
  - **`INCLUDE_FULL_DIRTY_TREE`:** secondary full-tree override that **keeps**
    chat coherent-signal; prefer `ALL` for post-chat debris cleanup.

# BEGIN CANONICAL SOURCE BODY
---
description: "Propose and (with GO) create semantic local commits for AI/process artifacts (commands, rules, skills, agents, static-check, mirrors)."
argument-hint: "[ALL] [FAST_CHECK|FULL_CHECK] [INCLUDE_FULL_DIRTY_TREE] GO [optional topic hint]"
---

# /opsx-meta-commit

## Owner scope map

| Invoke | What gets committed (in-scope process only) |
|---|---|
| `/opsx-meta-commit` / `… GO` (no `ALL`) | **Current chat only** — default |
| `/opsx-meta-commit ALL` / `… ALL GO` | **All** in-scope dirty — post-chat cleanup: split into logical meaning groups, then commit |
| `+ FULL_CHECK` | Optional stronger verify (default remains `FAST_CHECK`) |

**Defaults (no `ALL`):** current-chat commit scope + additive chat
coherent-signal + `CHECK_MODE=FAST_CHECK`. Never expand to the whole dirty
tree to “finish leftovers” without `ALL` / `INCLUDE_FULL_DIRTY_TREE`.

**`ALL` mode (post-chat debris cleanup):** full in-scope dirty tree;
**chat-provenance fully absent** (no current-chat selection filter, no
coherent-commit signal). Inventory leftovers → meaning-group splits →
plan/commit those groups. Not a silent one-blob dump. Check mode stays
`FAST_CHECK` unless `FULL_CHECK` / `FAST_CHECK` is explicit (`FULL_CHECK` is
optional — “можно проверять, если есть”).

**`INCLUDE_FULL_DIRTY_TREE`:** secondary — full dirty tree but **keeps**
additive chat coherent-signal. Prefer `ALL` when the Owner wants cleanup of
junk after chats.

Exclusive owner of local commits for **AI / process surfaces** (Cursor/agent commands,
rules, skills, agents, static-check, prompt/skill mirrors, and root agent guides).

You are allowed to create local git commits ONLY when the user input contains the exact token `GO`.

If `GO` is absent:
- do not modify files;
- do not stage files;
- do not commit;
- output only the proposed commit plan (include `CHAT_SCOPE` + `CHECK_MODE`).

Never push, merge, rebase, force-push, deploy, restart services, run migrations against production, or touch secrets.

Product/code/OpenSpec product commits belong to `/opsx-commit`, not this command.

## User input

```text
$ARGUMENTS
```

## Check mode (mandatory)

Parse exact case-sensitive tokens in `$ARGUMENTS`:

| Token | Meaning |
|---|---|
| `FAST_CHECK` | Light process verification (**default** when neither check token is present) |
| `FULL_CHECK` | Stronger process self-check before commit (opt-in) |
| `ALL` | Full dirty-tree scope; chat-provenance fully absent (see Current-chat scope) |

Rules:

1. If **both** `FULL_CHECK` and `FAST_CHECK` are present → `STATUS: BLOCKED_AMBIGUOUS_CHECK_MODE`; do not stage or commit.
2. If neither is present → `CHECK_MODE=FAST_CHECK` (including when `ALL` alone is present).
3. `CHECK_MODE` / `ALL` are **not** commit authorization. `GO` is still required to stage/commit.
4. Check tokens do not authorize product/OpenSpec commits (still `/opsx-commit`).

## Purpose

Analyze dirty **process-surface** files and create safe atomic local commits
**by meaning** — **defaulting to the current-chat work set**, not the entire
dirty tree.

Two phases:

1. **Plan** (no `GO`) — group files, propose commit subjects/bodies, report redirects.
2. **Execute** (`GO`) — stage and commit approved in-scope groups only.

**Source resolution:** Follow `.cursor/commands/opsx-source-resolution.md`.
**Execution budgets:** Follow `.cursor/commands/opsx-execution-preflight.md` (git-mutating class).

## Current-chat commit scope (default)

**Default selection:** only in-scope process-surface files attributable to work
done in the **current chat** (agent edits in this conversation, explicit paths
named here, or other clear chat evidence). Plan, stage, and commit only that set.

In-scope dirty files outside the current-chat set:

- leave unstaged;
- do not expand selection to “finish the tree”;
- report as `LEFT_UNSTAGED_OUTSIDE_CHAT_SCOPE`.

**Overrides (full dirty tree):**

| Token | Selection | Chat coherent-signal |
|---|---|---|
| `ALL` | Full in-scope dirty tree | **Absent** — chat-provenance fully off |
| `INCLUDE_FULL_DIRTY_TREE` | Full in-scope dirty tree (scope-only) | **Present** (additive; prefer grouping chat-attributed files as coherent commit(s) within the full set) |

Still never stage product/OpenSpec paths. Keep meaning-group splits and other
gates — `ALL` is post-chat in-scope dirty cleanup, not a silent one-blob dump.

If both `ALL` and `INCLUDE_FULL_DIRTY_TREE` are present → treat as `ALL`
(full scope + chat-provenance absent).

**Ambiguous attribution:** if `ALL` / `INCLUDE_FULL_DIRTY_TREE` are absent and
the current-chat set is empty or cannot be resolved with confidence →
`STATUS: BLOCKED_NEEDS_CHAT_SCOPE`; do not invent a full-tree commit plan; ask
one narrow path list or require `ALL` / `INCLUDE_FULL_DIRTY_TREE`.

**Coherent-commit signal (additive):** when **not** in `ALL` mode (including
default current-chat selection and `INCLUDE_FULL_DIRTY_TREE`), treat “same
current-chat work set” as an **additional** verification factor that those
files deserve a **separate coherent commit**. Under `ALL`, this signal is
**absent** (do not invent chat-provenance). The signal must **not** cancel or
down-weight existing factors: meaning groups, unrelated process splits,
out-of-scope redirect, mixed-file `git add -p` rules, protected-branch / `GO`
gates, or `CHECK_MODE` rules.

## In-scope surfaces (exclusive)

Only these paths may be staged/committed by this command:

```text
.cursor/commands/**
.cursor/rules/**
.cursor/skills/**
.cursor/agents/**
.cursor/static-check/**
.cursor/pipeline/**
.cursor/antipattern-gate/**
.cursor/opsx-review-commands
.agents/**
.github/skills/**
.github/prompts/**
.github/copilot-instructions.md
.github/git-commit-instructions.md
AGENTS.md
```

Shared OPSX process contracts that live under `.cursor/commands/` (for example
`opsx-execution-preflight.md`, `opsx-source-resolution.md`) are in scope.
Materialized operator pipeline graph under `.cursor/pipeline/` (from
`/opsx-pipeline UPDATE GO`) is in scope.
Static-check infra under `.cursor/static-check/` is in scope in full:
contracts, check packs, registry, base prompts/rules, **and** agent runner
scripts (e.g. `bin/run.sh`).
Antipattern-gate companions under `.cursor/antipattern-gate/` (catalog,
`PRACTICE_LEDGER.jsonl`, README) are in scope with `/opsx-antipattern-gate`.
All files under `.agents/**` (not only `skills/`) are in scope.

Everything else is **out of scope** for this command.

## Out of scope (redirect)

Never stage or commit:

- product/app/code
- tests
- DB/migrations
- CI/infra (including `.github/workflows/**`, except the surfaces listed above)
- local IDE prefs such as `.cursor/settings.json`
- archives / junk under `.cursor/` (e.g. `commands.zip`)
- `openspec/changes/**` product change packets
- ordinary project docs outside the surfaces above

If such files are dirty:

```text
OUT_OF_SCOPE_REDIRECT:
NEXT_ACTION: /opsx-commit
```

Leave them untouched.

## Mandatory preflight

These git ops are **REQUIRED_FOR** commit planning (branch protection + inventory).
Apply budgets; on timeout return `blocked_preflight_timeout` rather than hanging.

```text
OPERATION_REASON: process-surface commit plan + protected-branch gate
REQUIRED_FOR: commit decision
SKIP_IF: never when GO path is taken (preview may use status/diff only)
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

Do not run `git fetch` unless remote state becomes REQUIRED_FOR.

### Unresolved conflicts hard gate (mandatory)

After `git status --short` (and before any `git add` / `git commit`), **stop**
with `STATUS: BLOCKED` / `WHY: unresolved_conflicts` if either condition holds:

1. **Unmerged paths** — porcelain status shows any unmerged index state
   (`UU`, `AA`, `DD`, `AU`, `UA`, `DU`, `UD`) or status text reports
   `Unmerged paths` / both-modified without resolution.
2. **Conflict markers** — any file in the current commit group (already staged
   or about to be staged) contains unresolved conflict marker lines
   (`<<<<<<<`, `=======`, `>>>>>>>`).

On hit:

- do **not** stage or commit;
- do **not** clear, edit, or invent resolution for conflict markers;
- leave resolution to the owner (or a separate fix command);
- include in the report:

```text
WHY: unresolved_conflicts
DO_NOT_DO_YET: clear/choose conflict markers inside /opsx-meta-commit; git add of unmerged paths; rebase/merge/cherry-pick --continue/--skip/--abort; push; force-push
```

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

## Semantic grouping rules

Classify every **in-scope** file in the **current-chat commit set** (or full
in-scope dirty tree when `ALL` or `INCLUDE_FULL_DIRTY_TREE` is present) into
meaning groups. Prefer fewer clear commits over noise, but never merge
unrelated concerns. Files listed under `LEFT_UNSTAGED_OUTSIDE_CHAT_SCOPE` are
not classified for automatic commits. (`ALL` does **not** require a product
`/opsx-static-check` receipt — that gate belongs only to `/opsx-commit`.)

Preferred grouping:

```text
1. one logical OPSX/Cursor command + its mirrors/companions
   (e.g. .cursor/commands/opsx-verify.md + .github/prompts/opsx-verify.prompt.md
    + matching skill copies that changed for the same intent)
2. admin-command family packet that was designed/fixed together
3. shared process contracts (preflight, source-resolution, review pointers)
   — separate commit if they changed independently
4. rules / AGENTS.md / github agent instruction files — separate if not tied
   to a single command change
5. agents skills/guides (.agents/**, .cursor/agents/**) — by intent
6. static-check infra (.cursor/static-check/**) — separate unless companion
   to the same disclosed packet
7. antipattern-gate companions (.cursor/antipattern-gate/**) — with the
   `/opsx-antipattern-gate` command packet when they change together
8. unrelated process edits — separate commits by concern
```

Do **not**:

- dump all `.cursor/commands/**` into one commit when intents differ;
- mix verify/apply/archive lifecycle edits with unrelated admin-tooling edits
  unless they are one disclosed companion packet;
- include out-of-scope files to “finish the tree”.

If a file mixes independent concerns and interactive staging is impractical:

- leave it unstaged;
- report `requires manual git add -p`;
- continue with safe whole-file groups.

Empty `add -p` is **not** a commit stop: when no file needed interactive
staging, do **not** invent a leftover finding (omit that bullet; see Final report).

## Staging rules

Prefer whole-file staging when the file belongs to one meaning group.

Before every commit:

```bash
git diff --cached --stat
git diff --cached --name-status
git diff --cached
```

If the staged diff contains out-of-scope or unrelated process changes, unstage and stop that group:

```bash
git restore --staged <file>
```

## Commit message format

Subjects MUST be English with a short Russian explanation in parentheses:

```text
type(scope): English summary (русское пояснение)
```

Preferred types for this command:

```text
docs
chore
fix
refactor
```

Preferred scopes:

```text
commands
rules
skills
agents
prompts
static-check
opsx-admin
opsx-process
```

Examples:

```text
chore(commands): split verify handoff contract (разделить контракт handoff verify)
fix(opsx-admin): clarify defect fix NEXT_ACTION (уточнить NEXT_ACTION после fix)
docs(skills): mirror openspec-apply skill updates (синхронизировать skill openspec-apply)
```

Body (English primary; Russian allowed in parentheses):

```text
What:
- ...

Why:
- ...

How:
- ...

Verification:
- ...

Risk:
- ...
```

Create commits with multiple `-m` arguments (same pattern as `/opsx-commit`).

## Verification rules

Pre-commit checks are gated by `CHECK_MODE`. Scope = files **staged for the
current commit group** (not the whole dirty tree).

### FAST_CHECK matrix (default)

For process-only commits:

- focused automated tests are usually not inferred;
- commit is allowed with `Verification: not run - process contract change`;
- if the change claims a redirect/GO gate, do a quick Grep self-check that the
  named tokens exist in the touched files before committing that group.

### FULL_CHECK matrix (opt-in)

In addition to FAST_CHECK:

- mandatory Grep/self-check that claimed gate/redirect/status tokens exist in
  the staged files for that group;
- confirm no unbounded “read all / search all decisions” instruction was
  introduced in the staged diff;
- on any FAIL / missing claimed token → **COMMIT STOP** for the run.

## Execution mode

### No `GO` → plan only

```text
STATUS: PLAN_READY

Commit plan:
- CHAT_SCOPE: current-chat | ALL | INCLUDE_FULL_DIRTY_TREE
- CHECK_MODE: FAST_CHECK | FULL_CHECK  (default FAST_CHECK)
- proposed commits (subject + files + why this split)
- commands that would be run
- LEFT_UNSTAGED_OUTSIDE_CHAT_SCOPE:
- out-of-scope files (redirect to /opsx-commit)
- files requiring manual git add -p
- suspicious/unrelated process files

WHAT_HAPPENED:
WHY:
CURRENT_STATE:
OWNER_DECISION_REQUIRED: yes — accept plan or adjust groups
NEXT_ACTION: /opsx-meta-commit GO
DO_NOT_DO_YET: push; /opsx-commit for in-scope process files; mix product files into GO
```

### With `GO` → execute plan

For each in-scope group in the chat-scoped (or override) plan:

1. Stage files for that group only.
2. Inspect staged diff.
3. Run the `CHECK_MODE` matrix for that group's staged paths.
4. Commit with detailed message.
5. Continue to next group.

If a group requires manual `git add -p`:
- skip that group;
- continue with safe groups;
- report skipped files.

Stop immediately on staging/commit failure; leave working tree as-is; report.

## Final report (after GO)

`STATUS: COMMITTED` means one or more commits were created. Do **not** treat
any residual inventory block as “commit skipped”.

Use `NOT_COMMITTED_THIS_RUN:` (not a bare `Skipped:`) for leftovers that were
intentionally left out of this run. Empty under `COMMITTED` means every
planned group landed.

When `STATUS=COMMITTED` and every `NOT_COMMITTED_THIS_RUN` bucket is empty,
print a one-liner instead of empty skip noise:

```text
NOT_COMMITTED_THIS_RUN: none — all planned groups committed
```

Only expand the detailed buckets when something was actually left out
(`PARTIAL` / `BLOCKED`, or non-empty leftovers).

**Skipped / leftover condensation (mandatory):**

- Print a leftover bullet **only** when that subsection has real paths/items.
- Do **not** print `files requiring manual add -p: none` (or other `…: none`
  bullets) — empty subsections are omitted entirely.
- Empty `add -p` is **not** a gate and must not look like one.

```text
STATUS: COMMITTED | PARTIAL | BLOCKED

Done:
- commits created:
  (hashes + subjects; required when STATUS=COMMITTED)

NOT_COMMITTED_THIS_RUN: none — all planned groups committed
  (OR, only non-empty bullets among:)
- files requiring manual add -p: <paths>
- LEFT_UNSTAGED_OUTSIDE_CHAT_SCOPE: <paths>
  (in-scope dirty outside this run’s selection — not a failed commit)
- groups not committed: <names>

OUT_OF_SCOPE_REDIRECT:
- files left for /opsx-commit:

CHAT_SCOPE:
- current-chat | ALL | INCLUDE_FULL_DIRTY_TREE

CHECK_MODE:
- FAST_CHECK | FULL_CHECK

Verification:
- passed:
- failed:
- not run:

WHAT_HAPPENED:
WHY:
CURRENT_STATE:
OWNER_DECISION_REQUIRED:
NEXT_ACTION:
- if product files remain dirty: /opsx-commit
- else if snapshot may be stale: /opsx-meta-update-snapshot
- else optional: /opsx-create-pr (do not push)
DO_NOT_DO_YET: push; rebase; force-push
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
```

Never commit paths outside the in-scope surfaces list.
Never re-decide product commit grouping for `/opsx-commit`.
# END CANONICAL SOURCE BODY

# TARGET ADAPTATION NOTES

- upstream_snapshot: `.opsx/upstream/a71601dba3b9/.cursor/commands/opsx-admin-command-commit.md`
- runtime_class: `ACTIVE`
- active_name: `/opsx-meta-commit`
- openspec_store: `openspec/changes/**` (not source multi-store / not `.opsx/changes` SoT)
- quality: poetry-python gates per `.opsx/project/quality-gates.md` when in scope; `npm run build` UNAVAILABLE; smoke/frontend UNAVAILABLE
- unresolved_source_sections: any Poetry/pytest/pyright/kubectl/WB-domain steps in the body are blocked by TARGET OVERRIDE until adapters exist
- manual_review: `.opsx/project/manual_review.md`
- process_allowlist_sot: `.opsx/sources.yaml` (shared with snapshot + `/opsx-commit` exclusion)
- local_only: never writes central snapshot/catalog; next may be `/opsx-meta-update-snapshot`
- orientation: emit `ORIENTATION_HINT` with `NEXT_META: /opsx-meta`
