# OPSX bootstrap profile

Shared contract for `/opsx-meta-bootstrap` and
`/opsx-meta-export-pack scope=bootstrap_profile`.

## Purpose

First-contact / bind / **stepped install** for any OPSX state (absent → complete).

Bare `/opsx-meta-bootstrap GO` applies **one small step** (the next incomplete
install step), not the whole working set. Repeat `GO` until steps are done, then
`/opsx-projectize` if the lock is incomplete.

`/opsx-meta-import-command` is for **extras** outside these steps.

Optional `/opsx-meta-bootstrap SAVE` → central `bootstrap/reports/` (lessons;
not auto-merged into requirements).

## Local state tokens

```text
LOCAL_STATE: OPSX_ABSENT | OPSX_PARTIAL | PROJECTIZATION_REQUIRED | PROJECTIZATION_COMPLETE
```

On each `GO`, fill **only the current STEP** gaps; preserve TARGET OVERRIDE;
never downgrade COMPLETE → REQUIRED.

## Install steps (small)

Apply in order. Bare `GO` = next incomplete step only.

| STEP | Alias | What |
|---|---|---|
| `1` | `bind` | `STEP_1_BIND` (= former CORE_REQUIRED) |
| `2` | `meta` | `STEP_2_META` |
| `3` | `lifecycle` | `STEP_3_LIFECYCLE` |
| `4` | `support` | `STEP_4_SUPPORT` |

| Token | Expands to |
|---|---|
| bare `GO` / `STEP=next` | next incomplete step’s gaps only |
| `STEP=1` / `bind` / `PROFILE_KEEP=core` | step 1 only |
| `STEP=2` / `meta` | step 2 only |
| `STEP=3` / `lifecycle` | step 3 only |
| `STEP=4` / `support` | step 4 only |
| `STEP=all` / `PROFILE_KEEP=all` | all incomplete steps in **one** APPLY (large; opt-in) |
| `PROFILE_KEEP=…` | explicit ids/paths (still one APPLY) |

`PROFILE_KEEP=recommended` is **retired** as “everything”; treat as `STEP=next`
(same as bare `GO`) for compatibility.

## STEP_1_BIND (core)

Importer + orient + projectize + bind stubs:

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

## STEP_2_META

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

## STEP_3_LIFECYCLE

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

## STEP_4_SUPPORT

```text
.opsx/adapters/**
.opsx/project/manual_review.md
.opsx/import/README.md
.opsx/shared/lifecycle.md
.opsx/shared/evidence-contract.md
```

Skip paths absent from central (note in DIFF; do not FAIL whole step).

## Optional companions (explicit KEEP / STEP=all companions only)

```text
.cursor/pipeline/GRAPH.md
.cursor/pipeline/META.md
.cursor/rules/documentation.mdc
.cursor/rules/architecture-decisions.mdc
.opsx/tools/**
.cursor/commands/opsx-evolution.md
.cursor/commands/opsx-test.md
.cursor/commands/opsx-browser-check.md
.cursor/commands/opsx-security-review.md
```

## Hard excludes (never PROFILE_KEEP)

```text
src/**
public/**
backend/**
.env
.env.*
openspec/changes/**
openspec/archive/**
openspec/specs/**
.opsx/upstream/**
node_modules/**
**/.git/**
```

## Central resolution / requirements

Same as `/opsx-meta-bootstrap`: `central=` → sources.yaml → `OPSX_CENTRAL_ROOT`
→ `../opsx-central`; requirements-first else EMBEDDED_DEFAULT.

```text
sources/<repo_family_id>/<branch>/
catalog/
bootstrap/profile/
bootstrap/requirements.md
bootstrap/instruction.md
bootstrap/reports/
```

## Legacy names

| Old | New |
|---|---|
| `CORE_REQUIRED` | `STEP_1_BIND` |
| `DEFAULT_INSTALL` | steps 2+3+4 (not one APPLY by default) |
| `PROFILE_KEEP=recommended` (big bang) | use `STEP=all` if Owner really wants one shot |

## Staging

```text
.tmp/opsx-bootstrap/<UTC>/
  SOURCE.txt
  BOOTSTRAP_DIFF_PACKET.md
  MERGE_RECEIPT.md
```

## Handoffs

| After | NEXT_ACTION |
|---|---|
| step applied, later steps incomplete | `/opsx-meta-bootstrap GO` |
| all steps complete, lock incomplete | `/opsx-projectize` |
| all steps complete, COMPLETE | import only for extras; or `/opsx-meta-commit` if dirty |
| `SAVE` → REPORT_SAVED | none |
