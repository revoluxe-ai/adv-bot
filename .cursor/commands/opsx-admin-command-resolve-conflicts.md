---
name: /opsx-admin-command-resolve-conflicts
id: opsx-admin-command-resolve-conflicts
category: Workflow
description: "Plan (READ_ONLY) or apply (GO) semantic git conflict resolution on OPSX allowlist surfaces; finish merge/rebase continue"
argument-hint: "GO [optional topic] | ABORT_MERGE GO | ABORT_REBASE GO"
---

# /opsx-admin-command-resolve-conflicts

Exclusive owner of **git conflict resolution** on **OPSX process surfaces**
(allowlisted Cursor/agent trees, `.opsx` project/registry/adapters/tools,
devops memory, resolve-conflict package, prompt/skill mirrors, and root
agent guides).

Use when merge or rebase left conflict markers / unmerged paths on
allowlisted process surfaces, or when another command redirected here
because the tree is conflicted.

This command does **not** own ordinary semantic commits after a clean tree
(`/opsx-meta-commit`; `/opsx-admin-command-commit` = obsolete redirect only),
product conflict resolution (`app/**`, product `openspec/**`, etc.), push,
or force-push.

You may mutate the working tree / index / finish merge|rebase **only** when
user input contains the exact token `GO`.

If `GO` is absent:
- do not edit files;
- do not `git add`;
- do not run `merge --continue` / `rebase --continue` / abort;
- output only the conflict plan and owner decisions required.

Follow `.cursor/commands/opsx-source-resolution.md` and
`.cursor/commands/opsx-execution-preflight.md` (git-mutating class on GO).

## User input

```text
$ARGUMENTS
```

## Purpose

1. **Plan** (no `GO`) — inventory unmerged allowlisted paths, classify each
   conflict, propose resolutions, list Owner decisions.
2. **Execute** (`GO`) — apply approved resolutions, `git add` resolved
   allowlisted paths, finish `git merge --continue` or `git rebase --continue`
   when safe.
3. **Recheck** — after resolve, spot producer/consumer and dual-authority
   breakage; hand off to fix-defects when needed.

## When to use

- `git status` shows unmerged paths (`UU`, `AA`, `DU`, `UD`, `AU`, `UA`, `DD`)
  under `.opsx/sources.yaml` allowlist surfaces (including `.opsx/project/**`,
  `.cursor/devops/**`, `.cursor/opsx-resolve-conflict/**`, command/rule trees).
- Merge or rebase is in progress and allowlisted process files are conflicted.
- `/opsx-meta-commit` (or obsolete `/opsx-admin-command-commit`),
  `/opsx-create-pr`, or `/opsx-split-for-pr` redirected here.
- Operator asks how to finish merging OPSX process / projectize edits across
  branches.

## When not to use

- Clean working tree / no merge|rebase in progress → nothing to resolve;
  if dirty process files need commits → `/opsx-meta-commit`.
- Only **true product / hard_exclude** paths conflicted → stop with
  `BLOCKED_MIXED_SCOPE` or product-only note; do not rewrite `app/**` /
  product tests as “process success”.
- Unmerged paths that are process-looking but missing from the allowlist
  → this command still owns the inventory (`ALLOWLIST_GAP`); do **not**
  redirect those to `/opsx-commit`.
- Designing a new command → `/opsx-meta-design-command`.
- Contract defect after a clean merge → `/opsx-meta-fix-command-defects`.
- Day-to-day navigation → `/opsx-pipeline`.
- Unclear which admin command applies (no conflict evidence) →
  `/opsx-admin-command-consult`.

## In-scope surfaces (exclusive write/resolve)

**Process allowlist SoT:** `.opsx/sources.yaml` (`allowlist` / `hard_exclude`) —
same class-(A) rule as `/opsx-meta-commit`. Resolve / `git add` /
finish-merge may touch a path only when it matches `allowlist` and does
**not** match `hard_exclude`.

Classify **every** unmerged path into exactly one inventory class (mirror
`/opsx-meta-commit`):

| Inventory | When | Resolve / `git add` / finish? |
|---|---|---|
| `(A) IN_SCOPE` | Matches allowlist and not `hard_exclude` | Yes (subject to conflict class) |
| `(B) ALLOWLIST_GAP` | Matches the legacy template below **or** `/opsx-commit` process-exclusion prefixes, but **not** on the allowlist | **No** — emit `ALLOWLIST_GAP`; never `MIXED_SCOPE`; never `/opsx-commit` |
| `(C) OUT_OF_SCOPE` | True product / hard_exclude / other non-process | **No** — `BLOCKED_MIXED_SCOPE` when present with any in-scope UU |

The legacy prefix list below is documentation + Class (B) detector only;
on mismatch for Class (A), `sources.yaml` wins. Exclusion from
`/opsx-commit` alone does **not** make a path Class (A) until the
allowlist lists it.

Legacy template (keep aligned with allowlist; do not treat as a second SoT):

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
WORKLOG.md
.opsx/adapters/**
.opsx/registry/**
.opsx/shared/**
.opsx/project/**
.opsx/import/**
.opsx/manifest.yaml
.opsx/projectization.yaml
.opsx/sources.yaml
.opsx/lock.yaml
.opsx/tools/**
```

Never resolve or stage (even if dirty): Class (B) until allowlist is fixed,
`hard_exclude` entries (e.g. `.opsx/upstream/**`, `.opsx/changes/**`,
`.env*`), nor true product trees (`app/**`, product `openspec/**`, etc.)
unless they appear on the allowlist (they must not).

## Authority boundary (mandatory)

- Owns: conflict classification (including `ALLOWLIST_GAP` inventory),
  proposed/applied file resolutions on Class (A) paths, `git add` of those
  paths, `merge --continue` / `rebase --continue` when every unmerged path
  is Class (A) and resolved (no remaining Class B/C UU).
- Does **not** own: ordinary post-merge semantic commits (→ `/opsx-meta-commit`),
  product commits (→ `/opsx-commit`), PR creation, push, force-push,
  verify/archive/approval gates, silent redesign of command contracts,
  resolving or staging Class (B) paths before allowlist sync.
- Does **not** silently re-decide another command’s ownership tokens.
- `AUTHORITY_TOKEN` conflicts require explicit Owner choice in the plan
  (or in `$ARGUMENTS` on the GO turn) before apply.
- Class (B) handoff: `NEXT_ACTION: /opsx-meta-fix-command-defects`
  (proposed `sources.yaml` allowlist lines). Do **not** use
  `OUT_OF_SCOPE_REDIRECT` → `/opsx-commit` for Class (B).

## Conflict classes (exactly one per path)

Per-path conflict class applies to Class (A) paths after inventory. Class
(B)/(C) are inventory outcomes, not textual merge strategies.

| Class | Meaning | Auto-propose? | Apply without per-path Owner note? |
|---|---|---|---|
| `TRIVIAL_TEXTUAL` | Non-overlapping hunks / whitespace / import-order noise | yes | yes under GO if plan showed them |
| `SECTION_OVERLAP` | Same markdown/code section edited both sides | semantic merge proposal | yes under GO if plan proposal accepted (no OWNER_DECISION left) |
| `AUTHORITY_TOKEN` | OWNER / STATUS / GATE / disposition / forbid-list / denylist / exclusive-owner prose diverged | propose options only | **no** — need Owner choice |
| `CROSS_FILE_CONTRACT` | Merge would break producer/consumer or create dual authority across files (includes META/GRAPH fingerprint attestation without regenerating `inventory_path`) | propose + warn | GO may merge text; must set handoff to fix-defects when broken |
| `ALLOWLIST_GAP` | Unmerged path is Class (B): process-looking (legacy template or `/opsx-commit` exclusions) but not on `sources.yaml` allowlist | propose allowlist lines only | **no** — do not resolve/add; `FINISH_OP: none` while any Class B UU remains |
| `MIXED_SCOPE` | Same conflict set includes Class (C) true product / hard_exclude unmerged paths | do not resolve those paths | **stop** — `BLOCKED_MIXED_SCOPE` (Class B alone is **not** MIXED_SCOPE) |

## Prevention note (operator)

Prefer fewer conflicts upstream:

- avoid editing the same process file on two long-lived branches;
- serialize shared contracts (`opsx-execution-preflight`,
  `opsx-source-resolution`, pipeline GRAPH/META);
- never attest META/GRAPH fingerprint fields without regenerating
  `inventory_path` in the same apply;
- merge process PRs shared-contracts → consumers → routing/consult.

Prevention does not replace this command when `UU` already exists.

## Modes

| Input | Mode | Writes |
|---|---|---|
| default (no `GO`) | `READ_ONLY` / plan | never |
| exact `GO` + usable plan (this chat or `$ARGUMENTS`) | `APPLY` | in-scope resolves + git continue |
| `ABORT_MERGE GO` | `ABORT` | `git merge --abort` only |
| `ABORT_REBASE GO` | `ABORT` | `git rebase --abort` only |

Abort tokens without `GO` → plan-only explanation; no abort.

## Mandatory preflight

```text
OPERATION_REASON: detect merge/rebase + unmerged path inventory
REQUIRED_FOR: plan and apply decisions
SKIP_IF: never when this command runs
TIME_BUDGET: status 10s; rev-parse/head checks 5s; per-file conflict Read ≤30s
FAILURE_BEHAVIOR: blocked_preflight_timeout / EVIDENCE_GAP; no retry loop
```

Run the smallest set:

```bash
git branch --show-current
git status --short
git rev-parse -q --verify MERGE_HEAD
git rev-parse -q --verify REBASE_HEAD
```

Optional when needed for side labels:

```bash
git diff --name-only --diff-filter=U
```

Do not `git fetch` unless REQUIRED_FOR a stated decision.
Do not push.

Protected branches (`main` / `master` / `prod` / `production`): may plan.
Apply / continue / abort on protected branches requires
`GO_ON_PROTECTED_BRANCH` in addition to `GO`. Even then, never push.

## Plan steps (READ_ONLY)

1. Confirm merge and/or rebase in progress, or unmerged paths present.
2. Read `.opsx/sources.yaml` allowlist / `hard_exclude` (bounded). List every
   unmerged path; classify each into inventory **(A) IN_SCOPE** /
   **(B) ALLOWLIST_GAP** / **(C) OUT_OF_SCOPE** (same rules as
   `/opsx-meta-commit`; legacy template + `/opsx-commit` exclusions detect B).
3. If any Class (C) unmerged path exists → `BLOCKED_MIXED_SCOPE` (or
   product-only status). Do not propose resolving Class (C) here.
   Allowlisted `.opsx/**` UU (e.g. `.opsx/project/manual_review.md`) are
   Class (A), not MIXED_SCOPE.
4. If any Class (B) unmerged path exists → emit mandatory non-empty
   `ALLOWLIST_GAP:` (paths + proposed `sources.yaml` allowlist lines).
   Do **not** treat Class (B) as MIXED_SCOPE or redirect to `/opsx-commit`.
   Overall STATUS: `ALLOWLIST_GAP` whenever any Class (B) UU remains
   (never `PLAN_READY`, even if Class (A) paths are still plannable).
   Class (A) draft resolutions may still appear in the plan body under
   that STATUS. If Class (A) also needs Owner choices, list them in
   `OWNER_DECISION_REQUIRED` under `ALLOWLIST_GAP` (gap blocks finish
   first; do not emit `BLOCKED_OWNER` while Class B UU remains).
   `FINISH_OP: none` while any Class (B) UU remains.
   `NEXT_ACTION`: allowlist handoff (`/opsx-meta-fix-command-defects`),
   not `GO`.
5. For each Class (A) path: Grep/Read only that file (section budget);
   classify exactly one conflict class; draft resolution text or options.
6. List `OWNER_DECISIONS_REQUIRED` for every `AUTHORITY_TOKEN` path.
7. State intended finish op: `merge --continue` | `rebase --continue` | none
   (must be `none` if any Class B or C UU remains).
8. Emit output contract. Stop.

I/O: parallel Read max **2**; no full `.cursor/commands/**` dump.

## Apply steps (`GO`)

Preconditions:

- usable plan from this chat or `$ARGUMENTS`;
- every `AUTHORITY_TOKEN` item has an Owner choice;
- no unresolved Class (C) / `MIXED_SCOPE` unmerged paths;
- no remaining Class (B) / `ALLOWLIST_GAP` unmerged paths (allowlist must
  already list them so they reclassify as Class A, or they must be cleared);
- protected-branch rule satisfied if applicable.

Then:

1. Write resolved content for each planned Class (A) path (no conflict
   markers left).
2. **Pipeline fingerprint ↔ inventory guard (mandatory when triggered):**
   If this GO touched `.cursor/pipeline/META.md` and/or GRAPH inventory
   attestation fields (`inventory_count`, `source_fingerprint`,
   `fingerprint_*`, `inventory_content_sha256`, or notes claiming a
   recomputed fingerprint), then **before** `git add`:
   - run `graph_fingerprint.write_inventory` on META `inventory_path`
     (default `.cursor/pipeline/bug-team/controlled-tests/INVENTORY.json`);
   - align META `inventory_count` / `source_fingerprint` /
     `inventory_content_sha256` to the regenerated artifact and
     `graph_fingerprint.reproduce()`;
   - include the regenerated `INVENTORY.json` among in-scope paths to add.
   Do **not** claim `RESOLVED` while `inventory_path` disagrees with
   `reproduce()` or META attestation.
3. `git add -- <in-scope-resolved-paths>` only (Class A only).
4. Re-check `git status --short`: no `U` paths remain.
5. If merge in progress → `git merge --continue` (non-interactive; if the
   editor would open, use a simple merge message describing process-surface
   conflict resolution — do not invent product behavior claims).
6. If rebase in progress → `git rebase --continue` under the same rules.
7. Contract recheck (bounded): skim changed command handoff/ownership
   tokens for dual-authority or producer-without-consumer; **and** verify
   `inventory_path` count/fingerprint/`INVENTORY_CONTENT_SHA256` agree with
   META attestation and `graph_fingerprint.reproduce()` when META/GRAPH
   attestation was in scope for this GO (or when those files are dirty).
   If broken → `CONTRACT_BROKEN_AFTER_MERGE` and `NEXT_ACTION` =
   `/opsx-meta-fix-command-defects`.
8. If tree still has ordinary (non-conflict) process dirt →
   `NEXT_ACTION: /opsx-meta-commit`.
9. Never `git push`, `rebase` onto remote as a new op, `reset --hard`,
   or `clean -fd`.

## Hard prohibitions

Never run:

```bash
git push
git push --force
git reset --hard
git clean -fd
```

Never:

- `-X ours` / `-X theirs` / checkout --ours|--theirs on `AUTHORITY_TOKEN`
  without explicit Owner choice recorded in the plan output;
- resolve or stage Class (B) ALLOWLIST_GAP, Class (C), hard_exclude, or
  product paths;
- claim `RESOLVED` while unmerged paths remain;
- claim `RESOLVED` while META/GRAPH fingerprint attestation disagrees with
  `inventory_path` / `graph_fingerprint.reproduce()`;
- treat Class (B) as `BLOCKED_MIXED_SCOPE` or redirect Class (B) to
  `/opsx-commit`;
- treat abort as success without `ABORT_* GO`;
- open PRs or call `/opsx-create-pr` as a side effect.

## Output contract (every run)

```text
STATUS:
MODE: READ_ONLY | APPLY | ABORT
WHAT_HAPPENED:
WHY:
GIT_STATE: merge_in_progress | rebase_in_progress | conflicted_paths | clean | unknown
IN_SCOPE_CONFLICTS:
- path:
  class: TRIVIAL_TEXTUAL | SECTION_OVERLAP | AUTHORITY_TOKEN | CROSS_FILE_CONTRACT | ALLOWLIST_GAP | MIXED_SCOPE
  proposal:
  owner_decision: pending | <choice> | n/a
ALLOWLIST_GAP:
- paths:
- proposed_sources_yaml_allowlist_lines:
OUT_OF_SCOPE_UNMERGED:
OWNER_DECISIONS_REQUIRED:
FINISH_OP: merge --continue | rebase --continue | none | abort
CONTRACT_RECHECK: not_run | ok | CONTRACT_BROKEN_AFTER_MERGE
CURRENT_STATE:
OWNER_DECISION_REQUIRED:
NEXT_ACTION:
DO_NOT_DO_YET:
```

Omit `ALLOWLIST_GAP:` when none; when Class (B) present it is mandatory
non-empty.

### STATUS values

```text
PLAN_READY
RESOLVED
BLOCKED_OWNER
BLOCKED_MIXED_SCOPE
ALLOWLIST_GAP
BLOCKED_NEEDS_EVIDENCE
CONTRACT_BROKEN_AFTER_MERGE
ABORTED_BY_OWNER
blocked_preflight_timeout
```

### Typical NEXT_ACTION

| STATUS | NEXT_ACTION |
|---|---|
| `PLAN_READY` (no owner gaps; no Class B UU) | Reply: `GO` |
| `BLOCKED_OWNER` (no Class B UU) | Owner answers listed decisions, then `GO` |
| `ALLOWLIST_GAP` (any Class B UU; Class A drafts optional in body) | `/opsx-meta-fix-command-defects` (add proposed allowlist lines); re-run this command — not `GO` |
| `BLOCKED_MIXED_SCOPE` | finish Class (C) product conflicts first; re-run this command |
| `RESOLVED` | `/opsx-meta-commit` if dirty; else optional `/opsx-create-pr` |
| `CONTRACT_BROKEN_AFTER_MERGE` | `/opsx-meta-fix-command-defects` |
| `ABORTED_BY_OWNER` | operator chooses next branch action; not create-pr |

`DO_NOT_DO_YET` must include at least: push; force-push; admin-commit while
unmerged paths remain; create-pr while conflicted; `/opsx-commit` for
Class (B) paths.

## Failure / recovery

| Condition | Behavior |
|---|---|
| No conflicts / not in merge|rebase | `PLAN_READY` or short no-op; redirect commit if dirty |
| Missing Owner choices (and no Class B UU) | `BLOCKED_OWNER`; no writes |
| Class (B) UU present (alone or with Class A) | `ALLOWLIST_GAP` only (never `PLAN_READY`); Class (A) drafts allowed in body; `FINISH_OP: none`; no resolve/add of Class B; hand off allowlist fix (not `GO`) |
| Class (C) + Class (A) unmerged together | `BLOCKED_MIXED_SCOPE`; no allowlist apply until product UU cleared |
| Continue fails | report git error; leave tree; do not force |
| Read timeout on required conflict file | `blocked_preflight_timeout` / `EVIDENCE_GAP` |

## Self-review checklist

- [ ] Allowlist SoT (`.opsx/sources.yaml`) respected; no product / hard_exclude writes
- [ ] Class (B) never treated as MIXED_SCOPE or redirected to `/opsx-commit`
- [ ] Class (B) UU never yields `PLAN_READY` (STATUS `ALLOWLIST_GAP`; `FINISH_OP: none`; not `GO`)
- [ ] No apply without `GO`
- [ ] No silent `AUTHORITY_TOKEN` ours/theirs
- [ ] No push / force-push / hard reset / clean -fd
- [ ] Unmerged paths cleared before claiming `RESOLVED`
- [ ] NEXT_ACTION pasteable and single
- [ ] admin-commit / fix-defects / create-pr not stolen
