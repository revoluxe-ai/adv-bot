---
component_id: opsx.commands.meta_bootstrap
component_version: 0.5.0
ownership: TARGET_ONLY
runtime_class: ACTIVE
canonical_source_body: none
required_adapters: ["opsx-lite"]
local_modification_note: "v0.5: central requirements-first else EMBEDDED_DEFAULT; SAVE → central bootstrap/reports; AUTHORIZE_COMMAND_FIX 2026-08-07"
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

### Projectization gate

**EXEMPT** from `OPSX_PROJECTIZATION_REQUIRED` so empty repos can seed.
After seed, if lock not `COMPLETE` → hand off `/opsx-projectize` (do not auto-GO).

---

# /opsx-meta-bootstrap

## Happy path (Owner)

1. Copy **only** this file into the other repo:
   `.cursor/commands/opsx-meta-bootstrap.md`
2. Prefer a central tree at default location (see Central resolution).
3. Run:

```text
/opsx-meta-bootstrap GO
```

Every run **starts** by loading central requirements when available; otherwise
uses **EMBEDDED_DEFAULT** (path sets in this file / shared profile contract).
Exact `GO` alone = requirements load → plan → apply recommended
(CORE + DEFAULT_INSTALL) in the **same turn**.

Send reusable chat lessons to central (no local seed):

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
DEFAULT_SCOPE: CORE_REQUIRED + DEFAULT_INSTALL
HAPPY_PATH: /opsx-meta-bootstrap GO
LESSON_PATH: /opsx-meta-bootstrap SAVE
```

## Purpose

1. One-file first contact for any local OPSX state (absent → COMPLETE).
2. **Requirements-first:** prefer central instruction/requirements pack; else
   embedded default execution.
3. Bind `central_root` and install the working OPSX set on `GO`.
4. Optional `SAVE`: chat-derived bootstrap lesson report → central
   `bootstrap/reports/` for later centralized instruction updates.
5. Leave `/opsx-meta-import-command` on disk for **extras** only.

## Owner clarity — separate import?

| After `/opsx-meta-bootstrap GO` | Need import? |
|---|---|
| DEFAULT_INSTALL present | **No** for that set |
| Want commands outside DEFAULT_INSTALL | **Yes** |
| Lock not COMPLETE | `/opsx-projectize` next (not import) |

## When to use

- Empty / foreign repo with only this command copied → `GO`.
- Partial / COMPLETE: fill missing DEFAULT_INSTALL + rebind → `GO`.
- Capture reusable bootstrap friction from this chat → `SAVE`.

## When not to use

- Single extra command from catalog → `/opsx-meta-import-command`
- Only finish lock → `/opsx-projectize`
- Publish full allowlisted snapshot → `/opsx-meta-update-snapshot`
- Product work → `/opsx-explore`

## Authority boundary

- No `GO` / no `SAVE`: READ_ONLY plan (requirements load + DIFF).
- Exact `GO`: APPLY recommended seed/bind (local process writes).
- Exact `SAVE`: write **only** central `bootstrap/reports/<UTC>_*.md`.
- Does not own projectize `:GO`, import GO, snapshot/index, or commit.

## User input

```text
$ARGUMENTS
```

### Parameters

| Token | Required | Meaning |
|---|---|---|
| `GO` | happy path seed | Plan + apply recommended |
| `SAVE` | lesson report | Analyze chat → central report only |
| `central=<path\|zip>` | no | Override central; else auto-discover |
| `repo_family_id=` | no | Override when writing `sources.yaml` / report name |
| `PROFILE_KEEP=core` | no | Narrow `GO` apply to CORE only |
| `PROFILE_KEEP=` / `KEEP=` | no | Explicit KEEP list on `GO` |
| `packet=` | no | Reuse prior DIFF on `GO` |

## Modes

| Input | Mode | Writes |
|---|---|---|
| no `GO` / no `SAVE` | `READ_ONLY` | `.tmp/opsx-bootstrap/<UTC>/` DIFF only |
| exact `GO` | `APPLY` | local profile seed/bind + staging receipt |
| exact `SAVE` | `SAVE` | central `bootstrap/reports/**` only |
| `GO` + `SAVE` | `FAIL_CLOSED` | none |

## Central resolution (auto)

First hit wins; record in `CENTRAL:` / `CENTRAL_RESOLVE:`:

1. `central=` argument if present
2. Local `.opsx/sources.yaml` → `central_root` (prefer
   `bootstrap/profile` or `sources/<repo_family_id>/<branch>/` when present)
3. Env `OPSX_CENTRAL_ROOT` (same subpath preference)
4. Repo-relative `../opsx-central` then `../opsx-central/bootstrap/profile`
   then unambiguous `../opsx-central/sources/*/*`
5. Else unresolved (`CENTRAL_RESOLVE: failed`)

## Requirements load (every mode, first)

After central resolution attempt:

1. If central resolved, try read in order:
   - `<central>/bootstrap/requirements.md`
   - `<central>/bootstrap/instruction.md`
   - `<central>/bootstrap/profile/.opsx/shared/bootstrap-profile.md`
   - `<central>/.opsx/shared/bootstrap-profile.md` (when central is a profile root)
2. If any readable → `REQUIREMENTS_SOURCE: CENTRAL` and use that pack to
   refine CORE/DEFAULT path sets / instruction notes (union with embedded
   lists; never shrink below CORE_REQUIRED).
3. If none readable (or central unresolved) →
   `REQUIREMENTS_SOURCE: EMBEDDED_DEFAULT` and use embedded CORE/DEFAULT
   sets in this file (or local `.opsx/shared/bootstrap-profile.md` if present).
4. **Missing requirements file alone must not block** READ_ONLY preview or
   `GO` when a usable profile tree **or** embedded lists can drive APPLY.
5. `GO` still needs a resolvable central **tree/zip** that can supply files to
   copy (or `BLOCKED_NEEDS_CENTRAL`). Embedded defaults define *what* to seek;
   they do not invent file bytes.
6. Always emit `REQUIREMENTS_SOURCE` in the output contract.

## Local state → apply focus (`GO`)

| LOCAL_STATE | On bare `GO` |
|---|---|
| `OPSX_ABSENT` | Seed CORE + DEFAULT_INSTALL; sources bind; projectization `REQUIRED` |
| `OPSX_PARTIAL` / `PROJECTIZATION_REQUIRED` | Fill missing; CONFLICT → skip (local wins) |
| `PROJECTIZATION_COMPLETE` | Rebind; fill **missing** NEW only; never downgrade COMPLETE |

## Steps — READ_ONLY (no `GO`, no `SAVE`)

1. Detect `LOCAL_STATE`.
2. Resolve central (may fail).
3. **Requirements load** (above) → set `REQUIREMENTS_SOURCE`.
4. Inventory + classify; build Recommended KEEP.
5. Stage DIFF; emit `BOOTSTRAP_DIFF_READY`. No live merges.
6. If central unresolved: still emit plan from EMBEDDED_DEFAULT; note
   `OWNER_DECISION_REQUIRED: central=` for APPLY.

## Steps — APPLY (exact `GO`)

1. Exact `GO`; reject if `SAVE` also present.
2. Resolve central; if failed → `BLOCKED_NEEDS_CENTRAL`.
3. **Requirements load** → `REQUIREMENTS_SOURCE`.
4. Same-turn plan (unless `packet=`): staging `BOOTSTRAP_DIFF_PACKET.md`.
5. KEEP = Recommended (or `core` / explicit list). CONFLICT → skip on bare GO.
6. CORE gate: import-command must be obtainable if present in central.
7. Apply KEEP; bind `sources.yaml`; seed projectization `REQUIRED` if absent.
8. Registry stubs; `MERGE_RECEIPT.md`; `SEED_APPLIED` / `BIND_APPLIED`.
9. NEXT: `/opsx-projectize` if lock incomplete; else commit / import extras only.

## Steps — SAVE (exact `SAVE`)

1. Exact `SAVE`; reject if `GO` also present.
2. Resolve central; if failed → `BLOCKED_NEEDS_CENTRAL` (SAVE cannot land).
3. **Requirements load** (informational; still emit `REQUIREMENTS_SOURCE`).
4. Analyze **this chat** for reusable bootstrap lessons / friction only
   (empty-repo, central missing, KEEP pain, import chicken-egg, adapter
   confusion, requirements vs default, etc.). No product bugs, no secrets,
   no src dumps.
5. Write exactly one new file:
   `<central_root>/bootstrap/reports/<UTC>_<repo_family_or_unknown>.md`
   Create `bootstrap/reports/` if needed. Never overwrite prior reports.
6. Report minimum sections:

```markdown
# BOOTSTRAP_LESSON_REPORT
UTC:
REPO_FAMILY:
LOCAL_STATE:
CENTRAL:
REQUIREMENTS_SOURCE:

## SYMPTOMS
## GENERALIZED_LESSON
## PROPOSED_INSTRUCTION_DELTA
## CHAT_EVIDENCE_REFS
## NON_GOALS
```

7. Emit `STATUS: REPORT_SAVED` with `REPORT_PATH:`.
8. Do **not** edit local process files, do not mutate
   `bootstrap/requirements.md`, do not chain snapshot/index/commit.
9. NEXT: none required; optional later human/central process folds reports into
   `bootstrap/requirements.md` / instruction.

## Merge safety rules (`GO`)

1. Preserve local TARGET OVERRIDE.
2. Bare `GO` applies Recommended only.
3. CONFLICT → skip unless explicit KEEP path.
4. No upstream/product/env writes.
5. Partial failure → stop; report applied vs skipped.
6. Do not chain projectize/import/snapshot/index/commit.

## Future central freeze (deferred)

Publish this command + import + profile + processed requirements to central as
authoritative; hash-pin later. SAVE reports feed that process; they are not
auto-merged into requirements.

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
IMPORT_COMMAND_STATUS: MISSING | PRESENT | DIVERGED | n/a
DEFAULT_INSTALL_STATUS: INCOMPLETE | COMPLETE | n/a
SEPARATE_IMPORT_NEEDED_FOR_IMPORTER: no | yes | n/a
SEPARATE_IMPORT_NEEDED_FOR_DEFAULT_SET: no | yes | n/a
REPORT_PATH: none | <central path>
STAGING_DIR:
DIFF_SUMMARY:
USEFUL_CANDIDATES:
SKIP:
CONFLICTS:
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
| central not found on `GO`/`SAVE` | BLOCKED_NEEDS_CENTRAL | `../opsx-central`, env, or `central=` |
| requirements file missing | continue | `REQUIREMENTS_SOURCE: EMBEDDED_DEFAULT` |
| not OPSX central | FAIL_CLOSED | fix tree / zip |
| central missing import-command on `GO` | FAIL_CLOSED | publish DEFAULT_INSTALL |
| after GO seed, lock incomplete | SEED_APPLIED | `/opsx-projectize` |

## Regression checks

- [ ] Every run emits `REQUIREMENTS_SOURCE`
- [ ] Missing requirements.md does not alone block EMBEDDED_DEFAULT execution
- [ ] Hand-copy + `/opsx-meta-bootstrap GO` remains happy path
- [ ] `/opsx-meta-bootstrap SAVE` writes only `bootstrap/reports/**`
- [ ] `GO`+`SAVE` → FAIL_CLOSED ASK_ONE_MODE
- [ ] SAVE does not overwrite requirements/profile
- [ ] `required_adapters: ["opsx-lite"]` only
- [ ] No auto projectize:GO / import GO / commit

## Embedded CORE_REQUIRED (empty-repo / EMBEDDED_DEFAULT)

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

## Embedded DEFAULT_INSTALL extras (EMBEDDED_DEFAULT)

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
.cursor/commands/opsx-meta-commit.md
.cursor/commands/opsx-meta-discover.md
.cursor/commands/opsx-meta-consult.md
.cursor/commands/opsx-meta-design-command.md
.cursor/commands/opsx-meta-fix-command-defects.md
.cursor/commands/opsx-meta-update-snapshot.md
.cursor/commands/opsx-meta-update-index.md
.cursor/commands/opsx-meta-export-pack.md
.opsx/adapters/**
.opsx/project/manual_review.md
.opsx/import/README.md
.opsx/shared/lifecycle.md
.opsx/shared/evidence-contract.md
```

Authoritative list when local shared file exists:
`.opsx/shared/bootstrap-profile.md`.
