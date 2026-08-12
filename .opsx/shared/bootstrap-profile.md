# OPSX bootstrap profile

Shared contract for `/opsx-meta-bootstrap` and
`/opsx-meta-export-pack scope=bootstrap_profile`.

## Purpose

Define the allowlisted **first-contact / bind / default-install** process packet
for any OPSX state (absent → complete).

Default Owner path `/opsx-meta-bootstrap GO` (= `PROFILE_KEEP=recommended`
≡ `STEP=next`) advances **one** incomplete recommended step toward
**working OPSX** (destination = CORE + `DEFAULT_INSTALL` across
`1 bind → 2 meta → 3 lifecycle → 4 support`). Bare `GO` must **not**
apply all four steps in one turn. One-shot full set:
`/opsx-meta-bootstrap GO STEP=all` (or `PROFILE_KEEP=all`).
After recommended steps complete, a separate `/opsx-meta-import-command`
is **optional** — only for commands outside this profile (extras /
later catalog picks).

Every bootstrap run **loads central requirements first** when present; otherwise
`REQUIREMENTS_SOURCE: EMBEDDED_DEFAULT`. Optional `/opsx-meta-bootstrap SAVE`
writes lesson reports under central `bootstrap/reports/` for later centralized
updates to `bootstrap/requirements.md` / instruction (not auto-merged).

This is still **not** a silent whole-repo dump: bare `GO` applies the next
disclosed recommended step only; `STEP=all` applies all incomplete
recommended steps; `SAVE` writes reports only.

## Local state tokens

```text
LOCAL_STATE: OPSX_ABSENT | OPSX_PARTIAL | PROJECTIZATION_REQUIRED | PROJECTIZATION_COMPLETE
```

| Token | Meaning | Bootstrap job (`recommended` destination) |
|---|---|---|
| `OPSX_ABSENT` | No `.opsx/` | Reach CORE + DEFAULT_INSTALL + bind via repeated `GO` or one `STEP=all` |
| `OPSX_PARTIAL` | Some surfaces; lock incomplete | Fill missing CORE/DEFAULT step-by-step; bind; preserve TARGET OVERRIDE |
| `PROJECTIZATION_REQUIRED` | lock not COMPLETE | Same fill + bind; handoff projectize |
| `PROJECTIZATION_COMPLETE` | lock COMPLETE | Rebind; seed **missing** CORE/DEFAULT steps only; no wipe; no COMPLETE downgrade |

## KEEP aliases

| Token | Expands to |
|---|---|
| `PROFILE_KEEP=recommended` | ≡ `STEP=next` / bare `GO`: **one** incomplete recommended step toward CORE + DEFAULT_INSTALL (not big-bang) |
| `PROFILE_KEEP=all` | ≡ `STEP=all`: all incomplete CORE + DEFAULT_INSTALL steps in one APPLY |
| `PROFILE_KEEP=core` | CORE_REQUIRED gaps only (minimal bind / step 1) |
| `PROFILE_KEEP=…` | explicit ids/paths |

## CORE_REQUIRED

Minimum coherent seed (importer + orient + projectize + bind stubs):

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

## DEFAULT_INSTALL

Usable process plane after recommended steps complete (repeated bare `GO`
or one `STEP=all`). Includes CORE paths by reference, plus:

### Commands — product lifecycle gates

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

### Commands — meta / central plane

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

### OPSX project-local support

```text
.opsx/adapters/**
.opsx/project/manual_review.md
.opsx/import/README.md
.opsx/shared/lifecycle.md
.opsx/shared/evidence-contract.md
```

Skip any path absent from central (note in DIFF; do not FAIL whole plan).

## Full `BOOTSTRAP_PROFILE` (inventory / export scope)

`CORE_REQUIRED` + `DEFAULT_INSTALL` plus optional companions (only when Owner
explicitly KEEP or central publish includes them):

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

## Central resolution order

Used by `/opsx-meta-bootstrap` (including bare `GO` / `SAVE`):

1. `central=` argument (dir / profile root / `.zip`)
2. Local `.opsx/sources.yaml` → `central_root`
3. Env `OPSX_CENTRAL_ROOT`
4. Repo-relative `../opsx-central` (+ `bootstrap/profile` or unambiguous `sources/*/*`)
5. Else unresolved → `BLOCKED_NEEDS_CENTRAL` for `GO`/`SAVE`

### Portable central bind (committed files)

Never persist machine-absolute or user-home `central_root` into committed
`.opsx/sources.yaml` / `.opsx/projectization.yaml` / `.opsx/MERGE_RECEIPT.md`.
Prefer omit the key and bind via `central=` / `OPSX_CENTRAL_ROOT` /
`default_relative`. Relative persist only when it matches `../opsx-central`.
Receipts use `CENTRAL_RESOLVE:` + redacted `CENTRAL: <CENTRAL>` (and
`<CENTRAL>/…` in Actions).

```text
sources/<repo_family_id>/<branch>/
catalog/
bootstrap/profile/
bootstrap/requirements.md      # preferred instruction pack
bootstrap/instruction.md       # optional alternate
bootstrap/reports/             # SAVE lesson reports (append-only)
```

## Requirements load

```text
REQUIREMENTS_SOURCE: CENTRAL | EMBEDDED_DEFAULT
```

Try, in order, under resolved central: `bootstrap/requirements.md`,
`bootstrap/instruction.md`, `bootstrap/profile/.opsx/shared/bootstrap-profile.md`,
profile-root `.opsx/shared/bootstrap-profile.md`. If none → EMBEDDED_DEFAULT
(command-embedded CORE/DEFAULT lists). Missing requirements file alone must
not block default execution.

Happy path: hand-copy `opsx-meta-bootstrap.md` → repeat
`/opsx-meta-bootstrap GO` until steps 1–4 complete (or one
`GO STEP=all`). Lesson path: `/opsx-meta-bootstrap SAVE` →
`bootstrap/reports/<UTC>_<repo_family_or_unknown>.md`.

## Future central freeze (not enforced yet)

Publish bootstrap + import + this profile + processed requirements to central as
authoritative; local drift without central update discouraged. Hash-pin deferred.
SAVE reports feed human/central processing into `bootstrap/requirements.md`.

## Staging

```text
.tmp/opsx-bootstrap/<UTC>/
  SOURCE.txt
  BOOTSTRAP_DIFF_PACKET.md
  MERGE_RECEIPT.md
```

## Handoffs

| After | Separate import needed? | NEXT_ACTION |
|---|---|---|
| bare `GO`, more steps remain | n/a | `/opsx-meta-bootstrap GO` |
| recommended steps done (repeated `GO` or `STEP=all`), lock incomplete | **No** for DEFAULT_INSTALL | `/opsx-projectize` |
| recommended steps done, COMPLETE | **No** for DEFAULT; **yes** only for extras | import extras if wanted |
| `SAVE` → REPORT_SAVED | n/a | none (central later folds reports) |
| `PROFILE_KEEP=core` only | Yes for non-CORE | bare `GO` again or import |
| process dirty after `GO` | — | `/opsx-meta-commit` |
