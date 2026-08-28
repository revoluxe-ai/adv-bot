---
component_id: opsx.commands.meta_bootstrap
component_version: 0.6.0
ownership: TARGET_ONLY
runtime_class: ACTIVE
canonical_source_body: none
required_adapters: ["opsx-lite"]
local_modification_note: "v0.6: bare GO = next small STEP only (bind→meta→lifecycle→support); STEP=all opt-in; Owner 2026-08-07"
local_override_policy: TARGET_OVERRIDE_HIGHEST_PRIORITY
contract_id: OPSX-GAME-META-BOOTSTRAP-01
newline_normalization: none
---

# TARGET OVERRIDE — HIGHEST PRIORITY

**Contract:** `OPSX-GAME-META-BOOTSTRAP-01`  
**Runtime class:** `ACTIVE`  
**Precedence:** This override wins for target paths, write boundary, and bans.

### Target authority paths (local)

- Commands / rules / pipeline: `.cursor/commands/**`, `.cursor/rules/**`, `.cursor/pipeline/**`
- OPSX project-local: `.opsx/**` except frozen upstream default
- Staging only: `.tmp/opsx-bootstrap/**`

### Central write authority (SAVE only)

- `central_root/bootstrap/reports/**` only (create dir if needed)
- Never overwrite `bootstrap/requirements.md` / profile trees from SAVE

### Hard target bans

- Do not install dependencies / modify `package.json` or lockfile.
- Do not access production / Kubernetes / secrets.
- Do not push, open PR, rebase, force, or deploy.
- Do not write `src/**`, `public/**`, `backend/**` app code, `.env*`.
- Do not import foreign product dumps: `openspec/changes/**`, `openspec/archive/**`,
  product `openspec/specs/**` content.
- Do not blind-replace `.opsx/upstream/**` unless Owner explicit
  `KEEP=upstream-refresh` in args.
- Do not run `/opsx-projectize:GO` or `/opsx-meta-import-command` GO as a side effect.
- Do not commit. Never PASS-by-absence.
- Do not assume `vue-npm` or any product stack adapter — seed is stack-agnostic.
- `GO` and `SAVE` together → `FAIL_CLOSED` `REASON: ASK_ONE_MODE`.
- Bare `GO` must **not** apply all install steps in one turn (use `STEP=all`).

### Projectization gate

**EXEMPT** from `OPSX_PROJECTIZATION_REQUIRED` so empty repos can seed.
After steps complete, if lock not `COMPLETE` → hand off `/opsx-projectize`
(do not auto-GO).

---

# /opsx-meta-bootstrap

## Happy path (Owner) — small steps

1. Copy **only** this file into the other repo:
   `.cursor/commands/opsx-meta-bootstrap.md`
2. Prefer a central tree at default location (see Central resolution).
3. Repeat until steps are done:

```text
/opsx-meta-bootstrap GO
```

Each bare `GO` applies **one** next incomplete step:

```text
1 bind → 2 meta → 3 lifecycle → 4 support
```

Then, if lock incomplete: `/opsx-projectize`.

One-shot (large, opt-in only):

```text
/opsx-meta-bootstrap GO STEP=all
```

Lessons to central (no local seed):

```text
/opsx-meta-bootstrap SAVE
```

```text
IMPLEMENTATION_STATUS: IMPLEMENTED
RUNTIME_STATUS: ACTIVE
CONTRACT_ID: OPSX-GAME-META-BOOTSTRAP-01
PRODUCT_WRITER: NO
STACK_ADAPTER: none (opsx-lite process only)
UPSTREAM_OVERWRITE_DEFAULT: NO
DEFAULT_SCOPE: next incomplete STEP (1..4)
HAPPY_PATH: /opsx-meta-bootstrap GO   # repeat
OPT_IN_LARGE: /opsx-meta-bootstrap GO STEP=all
LESSON_PATH: /opsx-meta-bootstrap SAVE
```

Shared path sets: `.opsx/shared/bootstrap-profile.md` (or embedded lists below
when that file is not local yet).

## Purpose

1. One-file first contact for any local OPSX state.
2. Requirements-first when central pack exists; else EMBEDDED_DEFAULT.
3. Bind central and install OPSX in **small steps**.
4. Optional `SAVE` → central `bootstrap/reports/`.
5. Import remains for **extras** outside the four steps.

## Owner clarity — separate import?

| After | Need import? |
|---|---|
| Steps 1–4 complete | **No** for those sets |
| Want commands outside steps | **Yes** |
| Only step 1 done | Continue `GO` (or import extras — not required) |
| Lock not COMPLETE after steps | `/opsx-projectize` |

## When to use

- Empty / foreign repo with only this command → repeat `GO`.
- Partial / COMPLETE: fill next missing step + rebind → `GO`.
- Capture bootstrap friction → `SAVE`.

## When not to use

- Single extra from catalog → `/opsx-meta-import-command`
- Only finish lock → `/opsx-projectize`
- Publish snapshot → `/opsx-meta-update-snapshot`
- Product work → `/opsx-explore`

## Authority boundary

- No `GO` / no `SAVE`: READ_ONLY plan.
- Exact `GO`: APPLY **one** step (or `STEP=all` / explicit KEEP).
- Exact `SAVE`: central `bootstrap/reports/` only.
- Does not own projectize `:GO`, import GO, snapshot/index, or commit.

## User input

```text
$ARGUMENTS
```

### Parameters

| Token | Required | Meaning |
|---|---|---|
| `GO` | seed | Plan + apply **next** step (default) |
| `SAVE` | lesson | Chat lesson → central report only |
| `STEP=next` | no | Same as bare `GO` |
| `STEP=1` / `bind` / `PROFILE_KEEP=core` | no | Step 1 only |
| `STEP=2` / `meta` | no | Step 2 only |
| `STEP=3` / `lifecycle` | no | Step 3 only |
| `STEP=4` / `support` | no | Step 4 only |
| `STEP=all` / `PROFILE_KEEP=all` | no | All incomplete steps in one APPLY |
| `central=<path\|zip>` | no | Override central |
| `repo_family_id=` | no | sources.yaml / report name |
| `PROFILE_KEEP=` / `KEEP=` | no | Explicit path list |
| `packet=` | no | Reuse prior DIFF |

`PROFILE_KEEP=recommended` → treat as `STEP=next` (compat; not big-bang).

## Modes

| Input | Mode | Writes |
|---|---|---|
| no `GO` / no `SAVE` | `READ_ONLY` | `.tmp/opsx-bootstrap/<UTC>/` DIFF only |
| exact `GO` | `APPLY` | local seed/bind for selected step(s) |
| exact `SAVE` | `SAVE` | central `bootstrap/reports/**` only |
| `GO` + `SAVE` | `FAIL_CLOSED` | none |

## Central resolution (auto)

First hit wins; record in `CENTRAL:` / `CENTRAL_RESOLVE:`:

1. `central=` argument if present
2. Local `.opsx/sources.yaml` → `central_root`
3. Env `OPSX_CENTRAL_ROOT`
4. Repo-relative `../opsx-central` (+ `bootstrap/profile` / `sources/*/*`)
5. Else unresolved (`CENTRAL_RESOLVE: failed`)

## Requirements load (every mode, first)

1. If central resolved, try:
   - `bootstrap/requirements.md`
   - `bootstrap/instruction.md`
   - `bootstrap/profile/.opsx/shared/bootstrap-profile.md`
   - profile-root `.opsx/shared/bootstrap-profile.md`
2. Readable → `REQUIREMENTS_SOURCE: CENTRAL` (union with embedded; never
   shrink below STEP_1_BIND).
3. Else → `REQUIREMENTS_SOURCE: EMBEDDED_DEFAULT`.
4. Missing requirements file alone must not block preview/`GO`.
5. `GO` still needs a resolvable central tree/zip for file bytes.
6. Always emit `REQUIREMENTS_SOURCE`.

## Step selection (`GO`)

1. Inventory each STEP_1..4: `COMPLETE` if no NEW gaps (CONFLICT/skip ≠ block).
2. `BOOTSTRAP_STEP_STATUS: 1=… 2=… 3=… 4=…`
3. Choose apply set:
   - bare `GO` / `STEP=next` → **first** incomplete step only;
   - `STEP=N` / alias → that step only;
   - `STEP=all` → union of all incomplete steps;
   - explicit KEEP → those paths only (still CORE gate on step 1).
4. If all steps complete → `STATUS: BIND_APPLIED` or no-op seed;
   `NEXT_ACTION: /opsx-projectize` or none / commit.

## Local state notes

| LOCAL_STATE | Behavior |
|---|---|
| `OPSX_ABSENT` | Step 1 first (bind stubs + import); projectization `REQUIRED` |
| `OPSX_PARTIAL` / `PROJECTIZATION_REQUIRED` | Next missing step; CONFLICT → skip |
| `PROJECTIZATION_COMPLETE` | Next missing step NEW only; never downgrade COMPLETE |

## Steps — READ_ONLY

1. Detect `LOCAL_STATE`; resolve central; requirements load.
2. Inventory all four steps; compute next step.
3. Stage DIFF for **next** step (and summarize later steps).
4. Emit `BOOTSTRAP_DIFF_READY` with `APPLY_STEP:` and `NEXT_STEP_AFTER:`.

## Steps — APPLY (exact `GO`)

1. Exact `GO`; reject if `SAVE` also present.
2. Resolve central; if failed → `BLOCKED_NEEDS_CENTRAL`.
3. Requirements load; same-turn plan unless `packet=`.
4. Select step set (above). Bare `GO` ≠ all steps.
5. CORE gate when applying step 1: import-command must be in KEEP if central has it.
6. Apply KEEP for that step only; bind `sources.yaml` when step 1 touches it;
   seed projectization `REQUIRED` if absent; never set/downgrade COMPLETE.
7. Registry stubs as needed; `MERGE_RECEIPT.md`.
8. Emit `SEED_APPLIED` / `BIND_APPLIED` with `APPLY_STEP` and remaining steps.
9. NEXT:
   - later steps incomplete → `/opsx-meta-bootstrap GO`
   - all complete + lock incomplete → `/opsx-projectize`
   - all complete + COMPLETE → import extras only / `/opsx-meta-commit` if dirty

## Steps — SAVE (exact `SAVE`)

1. Exact `SAVE`; reject if `GO` also present.
2. Resolve central; if failed → `BLOCKED_NEEDS_CENTRAL`.
3. Requirements load (informational).
4. Analyze this chat for bootstrap lessons only (no product/secrets/src).
5. Write one new file:
   `<central_root>/bootstrap/reports/<UTC>_<repo_family_or_unknown>.md`
6. Minimum sections: UTC, REPO_FAMILY, LOCAL_STATE, CENTRAL,
   REQUIREMENTS_SOURCE, SYMPTOMS, GENERALIZED_LESSON,
   PROPOSED_INSTRUCTION_DELTA, CHAT_EVIDENCE_REFS, NON_GOALS.
7. `STATUS: REPORT_SAVED`; do not edit local process or requirements.md.

## Merge safety rules (`GO`)

1. Preserve local TARGET OVERRIDE.
2. Bare `GO` = one step only.
3. CONFLICT → skip unless explicit KEEP path.
4. No upstream/product/env writes.
5. Partial failure → stop; report applied vs skipped.
6. Do not chain projectize/import/snapshot/index/commit.

## Output contract (every run)

```text
STATUS:
MODE: READ_ONLY | APPLY | SAVE
WHAT_HAPPENED:
WHY:
LOCAL_STATE:
CENTRAL:
CENTRAL_RESOLVE: arg | sources.yaml | env | default_relative | failed
REQUIREMENTS_SOURCE: CENTRAL | EMBEDDED_DEFAULT
APPLY_STEP: none | 1|2|3|4 | all | explicit
BOOTSTRAP_STEP_STATUS: 1=<ok|gap> 2=… 3=… 4=…
NEXT_STEP_AFTER: none | 1|2|3|4
IMPORT_COMMAND_STATUS: MISSING | PRESENT | DIVERGED | n/a
SEPARATE_IMPORT_NEEDED_FOR_IMPORTER: no | yes | n/a
REPORT_PATH: none | <central path>
STAGING_DIR:
DIFF_SUMMARY:
KEEP_APPLIED: none | <list>
OWNER_DECISION_REQUIRED: none | central=… | …
NEXT_ACTION:
DO_NOT_DO_YET:
ORIENTATION_HINT:
  LANE: META
  STATUS: <same as STATUS>
  NEXT_META: /opsx-meta
  NEXT_ACTION: <same as NEXT_ACTION>
```

### STATUS values

```text
BOOTSTRAP_DIFF_READY
SEED_APPLIED
BIND_APPLIED
REPORT_SAVED
BLOCKED_NEEDS_CENTRAL
FAIL_CLOSED
```

## Failure / recovery

| Condition | STATUS | Recovery |
|---|---|---|
| `GO`+`SAVE` | FAIL_CLOSED | one mode only |
| central missing on `GO`/`SAVE` | BLOCKED_NEEDS_CENTRAL | `central=` / env / `../opsx-central` |
| requirements missing | continue | EMBEDDED_DEFAULT |
| step 1 without import in KEEP | FAIL_CLOSED | include import or bare `GO` on step 1 |
| after step, more steps remain | SEED_APPLIED | `/opsx-meta-bootstrap GO` |
| all steps done, lock incomplete | SEED_APPLIED | `/opsx-projectize` |

## Regression checks

- [ ] Bare `GO` applies at most one of steps 1..4
- [ ] `STEP=all` required for one-shot full set
- [ ] `PROFILE_KEEP=recommended` ≡ `STEP=next` (not big-bang)
- [ ] Every run emits `REQUIREMENTS_SOURCE` + `APPLY_STEP` / step status
- [ ] SAVE writes only `bootstrap/reports/**`
- [ ] `required_adapters: ["opsx-lite"]` only
- [ ] No auto projectize:GO / import GO / commit

## Embedded STEP_1_BIND

```text
.cursor/commands/opsx-meta-bootstrap.md
.cursor/commands/opsx-meta-import-command.md
.cursor/commands/opsx-projectize.md
.cursor/commands/opsx.md
.cursor/commands/opsx-meta.md
.opsx/shared/bootstrap-profile.md
.opsx/shared/meta-orientation.md
.opsx/shared/command-discovery.md
.opsx/sources.yaml
.opsx/projectization.yaml
.opsx/lock.yaml
.opsx/manifest.yaml
.opsx/registry/command_activation.ndjson
.opsx/registry/provenance.ndjson
```

## Embedded STEP_2_META

```text
.cursor/commands/opsx-meta-commit.md
.cursor/commands/opsx-meta-discover.md
.cursor/commands/opsx-meta-consult.md
.cursor/commands/opsx-meta-design-command.md
.cursor/commands/opsx-meta-fix-command-defects.md
.cursor/commands/opsx-meta-update-snapshot.md
.cursor/commands/opsx-meta-update-index.md
.cursor/commands/opsx-meta-export-pack.md
```

## Embedded STEP_3_LIFECYCLE

```text
.cursor/commands/opsx-explore.md
.cursor/commands/opsx-new.md
.cursor/commands/opsx-ff.md
.cursor/commands/opsx-continue.md
.cursor/commands/opsx-update.md
.cursor/commands/opsx-bound-scope.md
.cursor/commands/opsx-apply.md
.cursor/commands/opsx-verify.md
.cursor/commands/opsx-archive.md
.cursor/commands/opsx-commit.md
.cursor/commands/opsx-pipeline.md
.cursor/commands/opsx-source-resolution.md
.cursor/commands/opsx-execution-preflight.md
.cursor/commands/opsx-adapt-project.md
```

## Embedded STEP_4_SUPPORT

```text
.opsx/adapters/**
.opsx/project/manual_review.md
.opsx/import/README.md
.opsx/shared/lifecycle.md
.opsx/shared/evidence-contract.md
```

Authoritative when present: `.opsx/shared/bootstrap-profile.md`.contract_id: OPSX-WB-META-BOOTSTRAP-01
**Contract:** `OPSX-WB-META-BOOTSTRAP-01`  
CONTRACT_ID: OPSX-WB-META-BOOTSTRAP-01
### Portable central bind (committed files)
Hard rule for any write into committed process files
(`.opsx/sources.yaml`, `.opsx/projectization.yaml`, `.opsx/MERGE_RECEIPT.md`):
1. **Never** persist machine-absolute or user-home `central_root`
   (e.g. `C:/Users/…`, `/home/…`, `/Users/…`) — username leak + non-portable.
2. Prefer **omit** `central_root` and bind via `central=` / `OPSX_CENTRAL_ROOT` /
   `default_relative`.
3. Persist a relative `central_root` only when it matches the portable default
   (`../opsx-central`) for that workspace layout.
4. Chat/`CENTRAL:` output may show the resolved absolute path for this machine.
5. `MERGE_RECEIPT.md` records `CENTRAL_RESOLVE:` + redacted `CENTRAL: <CENTRAL>`
   (and `<CENTRAL>/…` in Actions); never raw home paths.
6. Apply KEEP for that step only; bind `sources.yaml` when step 1 touches it
   (portable central bind only — never write machine-absolute `central_root`);
   seed projectization `REQUIRED` if absent; never set/downgrade COMPLETE;
   never add machine-absolute `central_root` to projectization.
7. Registry stubs as needed; `MERGE_RECEIPT.md` with redacted `<CENTRAL>` token.
7. Do not persist machine-absolute / user-home `central_root` into committed
   process files (see Portable central bind).
