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
- **Sole process-commit front-door:** `/opsx-admin-command-commit` is a thin
  redirect/deprecate surface only — do not treat it as a second allowlist SoT.
- **Process allowlist SoT:** `.opsx/sources.yaml` (`allowlist` / `hard_exclude`) —
  единый список с `/opsx-meta-update-snapshot` и process-exclusion у `/opsx-commit`.
  Canonical «In-scope surfaces» ниже — legacy template; при расхождении побеждает
  `sources.yaml` + этот OVERRIDE. Includes `.cursor/devops/**` (OPS_STATE /
  LAST.json; never secrets/DSN) and `.cursor/opsx-resolve-conflict/**`.
- **ALLOWLIST_GAP (mandatory inventory class):** dirty paths that match
  `/opsx-commit` process-exclusion prefixes (or this command’s «In-scope
  surfaces» prefixes) but are **not** on `sources.yaml` allowlist are **not**
  true product out-of-scope. Never stage them; never redirect them to
  `/opsx-commit` (dead-end: commit excludes them too). **STATUS precedence:**
  eligible Class A in this run → keep overall `PLAN_READY` /
  `COMMITTED|PARTIAL` and emit a **mandatory non-empty** `ALLOWLIST_GAP`
  block; no eligible Class A → overall `STATUS: ALLOWLIST_GAP` (no GO).
  Gap remediation: `NEXT_ACTION: /opsx-meta-fix-command-defects` (or Owner
  edit of `.opsx/sources.yaml`).
- **Local-only:** never update central snapshot or catalog repos. After success, if snapshot may be stale, recommend `/opsx-meta-update-snapshot` only.
- Every terminal report must include `ORIENTATION_HINT` with `NEXT_META: /opsx-meta`.
- **Owner scope map (mandatory mental model):**
  - **Default (no `ALL`):** all dirty allowlisted `.cursor/commands/**`, PLUS
    current-chat-attributed dirty paths under other allowlisted process roots;
    leave other non-commands leftovers as `LEFT_UNSTAGED_OUTSIDE_CHAT_SCOPE`;
    never invent a full allowlist dirty-tree plan without `ALL` /
    `INCLUDE_FULL_DIRTY_TREE`. Report `CHAT_SCOPE: DEFAULT_COMMANDS_DIR`.
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
| `/opsx-meta-commit` / `… GO` (no `ALL`) | **Default:** all dirty `.cursor/commands/**` + chat-attributed other roots |
| `/opsx-meta-commit ALL` / `… ALL GO` | **All** in-scope dirty — post-chat cleanup: split into logical meaning groups, then commit |
| `+ FULL_CHECK` | Optional stronger verify (default remains `FAST_CHECK`) |

**Defaults (no `ALL`):** `CHAT_SCOPE=DEFAULT_COMMANDS_DIR` — all dirty
allowlisted paths under `.cursor/commands/**` (no chat-provenance filter for
that directory), plus current-chat-attributed dirty paths under other
allowlisted process roots; additive chat coherent-signal for non-commands
roots; `CHECK_MODE=FAST_CHECK`. Never expand to the whole allowlist dirty
tree to “finish leftovers” without `ALL` / `INCLUDE_FULL_DIRTY_TREE`. Keep
meaning-group splits (do not dump unrelated commands into one silent blob).

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
| `ALL` | Full dirty-tree scope; chat-provenance fully absent (see Default commit scope) |

Rules:

1. If **both** `FULL_CHECK` and `FAST_CHECK` are present → `STATUS: BLOCKED_AMBIGUOUS_CHECK_MODE`; do not stage or commit.
2. If neither is present → `CHECK_MODE=FAST_CHECK` (including when `ALL` alone is present).
3. `CHECK_MODE` / `ALL` are **not** commit authorization. `GO` is still required to stage/commit.
4. Check tokens do not authorize product/OpenSpec commits (still `/opsx-commit`).

## Purpose

Analyze dirty **process-surface** files and create safe atomic local commits
**by meaning** — **defaulting to dirty `.cursor/commands/**` plus
current-chat-attributed other roots**, not the entire allowlist dirty tree.

Two phases:

1. **Plan** (no `GO`) — group files, propose commit subjects/bodies, report redirects.
2. **Execute** (`GO`) — stage and commit approved in-scope groups only.

**Source resolution:** Follow `.cursor/commands/opsx-source-resolution.md`.
**Execution budgets:** Follow `.cursor/commands/opsx-execution-preflight.md` (git-mutating class).

## Default commit scope (`DEFAULT_COMMANDS_DIR`)

**Default selection** (no `ALL` / `INCLUDE_FULL_DIRTY_TREE`):

1. **All** dirty allowlisted paths under `.cursor/commands/**` — no
   chat-provenance filter for that directory.
2. **Plus** in-scope dirty process-surface files under other allowlisted roots
   that are attributable to work done in the **current chat** (agent edits in
   this conversation, explicit paths named here, or other clear chat evidence).

Plan, stage, and commit that union. Report `CHAT_SCOPE: DEFAULT_COMMANDS_DIR`.

In-scope dirty files outside that default set (e.g. dirty rules/skills/devops
not attributed to this chat):

- leave unstaged;
- do not expand selection to “finish the allowlist tree”;
- report as `LEFT_UNSTAGED_OUTSIDE_CHAT_SCOPE`.

**Overrides (full dirty tree):**

| Token | Selection | Chat coherent-signal |
|---|---|---|
| `ALL` | Full in-scope dirty tree | **Absent** — chat-provenance fully off |
| `INCLUDE_FULL_DIRTY_TREE` | Full in-scope dirty tree (scope-only) | **Present** (additive; prefer grouping chat-attributed files as coherent commit(s) within the full set) |

Still never stage product/OpenSpec paths. Keep meaning-group splits and other
gates — `ALL` is post-chat in-scope dirty cleanup, not a silent one-blob dump.
Default still forbids dumping unrelated `.cursor/commands/**` intents into one
commit when meaning groups differ.

If both `ALL` and `INCLUDE_FULL_DIRTY_TREE` are present → treat as `ALL`
(full scope + chat-provenance absent).

**Ambiguous attribution (non-commands roots only):** if `ALL` /
`INCLUDE_FULL_DIRTY_TREE` are absent and the **non-commands** current-chat set
cannot be resolved with confidence → omit uncertain non-commands paths (report
them under `LEFT_UNSTAGED_OUTSIDE_CHAT_SCOPE` or ask one narrow path list). Do
**not** `BLOCKED_NEEDS_CHAT_SCOPE` when dirty `.cursor/commands/**` alone
supplies a usable default set. Only if the default set is empty (no dirty
commands and no confident chat-attributed other roots) →
`STATUS: BLOCKED_NEEDS_CHAT_SCOPE`; ask one narrow path list or require `ALL` /
`INCLUDE_FULL_DIRTY_TREE`.

**Coherent-commit signal (additive):** when **not** in `ALL` mode:
- dirty `.cursor/commands/**` in the default set are selected without chat
  provenance, but still split by meaning groups;
- for non-commands roots and under `INCLUDE_FULL_DIRTY_TREE`, treat “same
  current-chat work set” as an **additional** verification factor that those
  files deserve a **separate coherent commit**.
Under `ALL`, this signal is **absent** (do not invent chat-provenance). The
signal must **not** cancel or down-weight existing factors: meaning groups,
unrelated process splits, out-of-scope redirect, mixed-file `git add -p`
rules, protected-branch / `GO` gates, or `CHECK_MODE` rules.

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

Shared OPSX process contracts that live under `.cursor/commands/` (for example
`opsx-execution-preflight.md`, `opsx-source-resolution.md`) are in scope.
Materialized operator pipeline graph under `.cursor/pipeline/` (from
`/opsx-pipeline UPDATE GO`) is in scope.
Static-check infra under `.cursor/static-check/` is in scope in full:
contracts, check packs, registry, base prompts/rules, **and** agent runner
scripts (e.g. `bin/run.sh`).
Antipattern-gate companions under `.cursor/antipattern-gate/` (catalog,
`PRACTICE_LEDGER.jsonl`, README) are in scope with `/opsx-antipattern-gate`.
Durable DevOps ops memory under `.cursor/devops/**` (`OPS_STATE.md`,
`LAST.json`, …) is in scope with `/opsx-devops` (never secrets/DSN values).
`/opsx-resolve-conflict` package under `.cursor/opsx-resolve-conflict/**`
(runtime, MANIFEST/TRUST_ANCHOR, scripts, tests) is in scope with that command.
All files under `.agents/**` (not only `skills/`) are in scope.

Everything else is **out of scope** for this command.

## Dirty-path three-way classify (mandatory)

On every inventory (plan or `GO`), classify **each** dirty path into exactly one:

| Class | When | Action |
|---|---|---|
| `(A) IN_SCOPE` | Matches `.opsx/sources.yaml` allowlist and not `hard_exclude` | Eligible for this command’s selection / commit groups |
| `(B) ALLOWLIST_GAP` | Matches `/opsx-commit` process-exclusion prefixes **or** the «In-scope surfaces» prefixes above, but **not** on the allowlist | Do **not** stage. Emit `ALLOWLIST_GAP` per STATUS precedence (below). Do **not** use `OUT_OF_SCOPE_REDIRECT` → `/opsx-commit` |
| `(C) OUT_OF_SCOPE` | True product/app/other (not process-looking) | `OUT_OF_SCOPE_REDIRECT` → `/opsx-commit` |

`sources.yaml` wins over the legacy «In-scope surfaces» template for (A).
Exclusion from `/opsx-commit` alone does **not** make a path meta-commit
in-scope until the allowlist lists it.

### (B) ALLOWLIST_GAP output

When any dirty path is class (B): **never stage** those paths. Emit the
`ALLOWLIST_GAP` block (paths + proposed `sources.yaml` lines). Do **not**
treat Class B as Class C / `OUT_OF_SCOPE_REDIRECT`.

**STATUS precedence (mandatory — resolves PLAN_READY vs ALLOWLIST_GAP):**

1. **Eligible Class A in this run’s selection** → overall STATUS stays
   `PLAN_READY` (no `GO`) or `COMMITTED` / `PARTIAL` (with `GO`). Include a
   **mandatory non-empty** `ALLOWLIST_GAP:` block. `GO` may commit Class A
   only; Class B stays unstaged. Also note
   `NEXT_ACTION: /opsx-meta-fix-command-defects` for the gap (plan may still
   offer `/opsx-meta-commit GO` for Class A).
2. **No eligible Class A** (only Class B, or B+C) → overall
   `STATUS: ALLOWLIST_GAP`; do **not** emit `PLAN_READY`; do **not** run `GO`.

Gap-only overall status shape:

```text
STATUS: ALLOWLIST_GAP
ALLOWLIST_GAP:
- paths:
- proposed_sources_yaml_allowlist_lines:
NEXT_ACTION: /opsx-meta-fix-command-defects
DO_NOT_DO_YET: /opsx-commit for these paths; invent product commits; stage them under meta-commit
```

Leave Class B untouched until allowlist is fixed (separate
`/opsx-meta-fix-command-defects` / Owner edit of `.opsx/sources.yaml`).
Class A commits must not wait on that fix when precedence rule 1 applies.

### (C) Out of scope (redirect)

Never stage or commit:

- product/app/code
- tests
- DB/migrations
- CI/infra (including `.github/workflows/**`, except the surfaces listed above)
- local IDE prefs such as `.cursor/settings.json`
- archives / junk under `.cursor/` (e.g. `commands.zip`)
- `openspec/changes/**` product change packets
- ordinary project docs outside the surfaces above

If such files are dirty (class C only):

```text
OUT_OF_SCOPE_REDIRECT:
NEXT_ACTION: /opsx-commit
```

Leave them untouched.

## Mandatory preflight

These git ops are **REQUIRED_FOR** commit planning (conflicted-tree +
branch protection + inventory). Apply budgets; on timeout return
`blocked_preflight_timeout` rather than hanging.

```text
OPERATION_REASON: process-surface commit plan + conflicted-tree + protected-branch gate
REQUIRED_FOR: commit decision
SKIP_IF: never when GO path is taken (preview may use status/diff only)
TIME_BUDGET: branch 5s; status 10s; each diff 15s
FAILURE_BEHAVIOR: blocked_preflight_timeout / report missing fact; no retry loop
```

Run the smallest set that answers the need:

```bash
git branch --show-current
git status --short
git ls-files -u
git diff --stat
git diff --name-status
git diff --cached --stat
git diff --cached --name-status
```

Do not run `git fetch` unless remote state becomes REQUIRED_FOR.

### Conflicted-tree gate (mandatory — plan and GO)

If the working tree has **unmerged paths** (status codes with `U`, e.g.
`UU`, `AA`, `DU`, `UD`, `AU`, `UA`, `DD`) **or** a merge/rebase is in
progress, do **not** propose ordinary commits, do not stage, and do not
commit. Stop with:

```text
STATUS: BLOCKED_CONFLICTED_TREE
NEXT_ACTION: /opsx-admin-command-resolve-conflicts
DO_NOT_DO_YET: stage; commit; push; create-pr
```

Product-only conflicts (no process-surface unmerged paths) are out of
scope here too — report them and do not invent a product merge workflow;
still do not ordinary-commit while any unmerged paths or merge|rebase
remains in progress.

This gate applies on **both** plan-only and `GO` paths. It is the sole
front-door counterpart of the obsolete `/opsx-admin-command-commit`
alias stop (GRAPH: do not use `/opsx-meta-commit` while unmerged).

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

### Unresolved conflict gate (mandatory — PLAN and GO)

Before proposing commit groups **or** staging/committing, inspect the
**planned in-scope set** (default `DEFAULT_COMMANDS_DIR` union, or full
in-scope dirty under `ALL` / `INCLUDE_FULL_DIRTY_TREE`). This gate is a safety
stop: it applies in both `FAST_CHECK` and `FULL_CHECK`.

1. **Unmerged index** — if any planned/staged in-scope path appears in
   `git ls-files -u` output → stop.
2. **Conflict markers** — Grep those text paths (working tree and staged
   blob) for lines matching `^<<<<<<<`, `^=======`, or `^>>>>>>>`. Any hit
   → stop.

On either hit: do **not** stage, do **not** commit, do **not** invent a local
merge or strip markers.

```text
STATUS: BLOCKED_UNRESOLVED_CONFLICT
UNMERGED_OR_MARKED_PATHS:
- <path>
NEXT_ACTION: /opsx-admin-command-resolve-conflicts
DO_NOT_DO_YET: /opsx-meta-commit GO; strip markers; Accept Both
```

Exclusive process-surface conflict front-door from this command (both
`BLOCKED_CONFLICTED_TREE` and `BLOCKED_UNRESOLVED_CONFLICT`) is
`/opsx-admin-command-resolve-conflicts`. `/opsx-resolve-conflict` is the
packaged typed runtime under `.cursor/opsx-resolve-conflict/**` (its own
PREVIEW/GO lane) — not a second meta-commit owner of allowlisted process
UU/markers, and not a substitute for that front-door.

## Semantic grouping rules

Classify every **in-scope** file in the **default commit set**
(`DEFAULT_COMMANDS_DIR` union) — or full in-scope dirty tree when `ALL` or
`INCLUDE_FULL_DIRTY_TREE` is present — into
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
8. devops durable memory (.cursor/devops/**) — with `/opsx-devops` OPS_STATE
   / LAST.json updates (never secrets); separate from product `/opsx-commit`
9. resolve-conflict package (.cursor/opsx-resolve-conflict/**) — with
   `/opsx-resolve-conflict` hash/MANIFEST/runtime packet when it changes
10. unrelated process edits — separate commits by concern
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

- unresolved-conflict gate MUST pass for the planned/staged in-scope set
  (`git ls-files -u` empty for those paths; no `<<<<<<<` / `=======` /
  `>>>>>>>` markers). Failure → `STATUS: BLOCKED_UNRESOLVED_CONFLICT`
  (COMMIT STOP); see Mandatory preflight;
- focused automated tests are usually not inferred;
- commit is allowed with `Verification: not run - process contract change`
  only after the unresolved-conflict gate passes;
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

**STATUS precedence with Class B:** if this run has eligible Class A →
`STATUS: PLAN_READY` and a **mandatory non-empty** `ALLOWLIST_GAP` block
(Class B never staged). If no eligible Class A and Class B present → emit
overall `STATUS: ALLOWLIST_GAP` only (see Class B section); do **not** use
the `PLAN_READY` template below.

```text
STATUS: PLAN_READY

Commit plan:
- CHAT_SCOPE: DEFAULT_COMMANDS_DIR | ALL | INCLUDE_FULL_DIRTY_TREE
- CHECK_MODE: FAST_CHECK | FULL_CHECK  (default FAST_CHECK)
- proposed commits (subject + files + why this split) — Class A only
- commands that would be run
- LEFT_UNSTAGED_OUTSIDE_CHAT_SCOPE:
- ALLOWLIST_GAP: omit when none; when Class B present — mandatory non-empty
  (paths + proposed sources.yaml lines; never optional/skip)
- out-of-scope files (redirect to /opsx-commit) — class C only
- files requiring manual git add -p
- suspicious/unrelated process files

WHAT_HAPPENED:
WHY:
CURRENT_STATE:
OWNER_DECISION_REQUIRED: yes — accept plan or adjust groups
NEXT_ACTION: /opsx-meta-commit GO
  (when ALLOWLIST_GAP non-empty, also note /opsx-meta-fix-command-defects
   for the gap — GO still allowed for Class A only)
DO_NOT_DO_YET: push; /opsx-commit for in-scope process files; mix product files into GO; stage Class B
```

### With `GO` → execute plan

For each in-scope group in the default-scoped (or override) plan:

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
- Class B leftovers use nested `ALLOWLIST_GAP:` under overall
  `COMMITTED` / `PARTIAL` / `BLOCKED*` — they do **not** replace that overall
  STATUS (see Class B STATUS precedence). Omit the block when empty.

```text
STATUS: COMMITTED | PARTIAL | BLOCKED | BLOCKED_UNRESOLVED_CONFLICT

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
- files left for /opsx-commit:  (class C only)

ALLOWLIST_GAP:
- paths:  (class B; omit entire block when none — when present, mandatory non-empty)
- proposed_sources_yaml_allowlist_lines:
- NEXT_ACTION: /opsx-meta-fix-command-defects  (when non-empty)

CHAT_SCOPE:
- DEFAULT_COMMANDS_DIR | ALL | INCLUDE_FULL_DIRTY_TREE

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
- if ALLOWLIST_GAP non-empty: /opsx-meta-fix-command-defects
- if product files remain dirty: /opsx-commit
- else if snapshot may be stale: /opsx-meta-update-snapshot
- else optional: /opsx-create-pr (do not push)
DO_NOT_DO_YET: push; rebase; force-push; /opsx-commit for ALLOWLIST_GAP paths
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
- process_allowlist_sot: `.opsx/sources.yaml` (shared with snapshot + `/opsx-commit` exclusion; includes `.cursor/devops/**` and `.cursor/opsx-resolve-conflict/**`)
- sole_front_door: `/opsx-meta-commit`; `/opsx-admin-command-commit` = thin redirect only
- local_only: never writes central snapshot/catalog; next may be `/opsx-meta-update-snapshot`
- orientation: emit `ORIENTATION_HINT` with `NEXT_META: /opsx-meta`
