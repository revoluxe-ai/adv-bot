---
name: /opsx-scripts-prepare
id: opsx-scripts-prepare
category: Workflow
description: "One-shot/rare readiness check and GO materialization for scripts/ ops infra (GHA image on branch scripts, K8s Job template, REGISTRY)."
argument-hint: "[CHECK] | GO [paths=…] [intent=materialize_missing]"
---

# /opsx-scripts-prepare

Side-lane **one-shot / rare** command: check whether `scripts/` can be run via
the project path **branch `scripts` → GitHub Action image build (no PR) →
Kubernetes Job → report**, and with explicit `GO` materialize only missing
allowlisted infra.

Default is **READ_ONLY** check. Writes only under exact `GO`.

Daily inventory / local test / Job run → `/opsx-scripts` (not this command).

Follow `.cursor/commands/opsx-source-resolution.md` and
`.cursor/commands/opsx-execution-preflight.md`.

## What this is

* Infra readiness gate for the scripts ops path.
* Emitter of `SCRIPTS_INFRA_REPORT` and pasteable next action.
* Materializer (GO only) of missing workflow / Job template / registry schema.

## What this is NOT

* NOT daily script inventory, local test, or Job run → `/opsx-scripts`.
* NOT generic cluster diagnose/apply → `/opsx-devops`.
* NOT product bug fix / OpenSpec apply / verify / archive.
* NOT license to rewrite working `scripts/*.py`.
* NOT CSI / port-forward / secret dump / prod DB migration.

## When to use

* First time enabling scripts ops on this repo.
* After deleting or breaking the scripts workflow, Job template, or registry.
* Owner asks “are we ready to run scripts via image + Job?”

## When not to use

* Inventory / status / local test / run a script → `/opsx-scripts`.
* Pod crash / generic k8s symptom → `/opsx-devops`.
* Authoring pytest for a script behavior → `/opsx-test` (optional handoff).
* Process routing ambiguity → `/opsx-admin-command-consult`.

## User input

```text
$ARGUMENTS
```

| Token | Effect |
|-------|--------|
| (default) / `CHECK` | READ_ONLY readiness check |
| `GO` | Materialize only missing allowlisted paths (see GO gate) |
| `intent=materialize_missing` | Explicit prepare intent for GO |
| `paths=a,b` | Optional exact paths to create/update under GO |
| unknown conflicting mode | `STATUS=BLOCKED` |

Examples:

```text
/opsx-scripts-prepare
/opsx-scripts-prepare CHECK
/opsx-scripts-prepare GO intent=materialize_missing
```

## Required infra checklist

All must be present and coherent for `SCRIPTS_INFRA=READY`:

For a `PLAN_RUN` / `RUN` request, this checklist is evaluated against the
canonical `refs/heads/scripts` snapshot selected by the thin bootstrap. The
caller worktree is not a Registry source and need not contain
`scripts/REGISTRY.yaml` or `scripts/REGISTRY.md`.

1. **GHA workflow** — push (and preferably `workflow_dispatch`) on branch
   `scripts` builds+pushes image from existing `dockers/Dockerfile` without
   requiring a PR. Canonical path:
   `.github/workflows/deploy_scripts.yml`
2. **Job template** — parameterized one-shot Job for running
   `python <script>` (or equivalent) from the built image. Canonical path:
   `k8s/jobs/ops-script-runner.yaml`
3. **Registry** — machine source at canonical
   `scripts/REGISTRY.yaml`, validated with
   `tools/scripts/registry.py`, plus generated readiness view at
   `scripts/REGISTRY.md`. `title` is required (human primary label); `path`
   is the secondary hint (see `.cursor/commands/opsx-human-label-display.md`).
   CHECK treats missing/invalid YAML or generated drift as
   `REGISTRY_STATUS=INVALID` (GAP) until repaired.
4. **Reuse, do not reinvent** — existing Dockerfile, imagePullSecrets /
   envFrom patterns from `k8s/jobs/app-db-migrate.yaml` where applicable;
   do not rewrite working scripts.

Do **not** change `deploy.yml` (master) or `deploy_stage.yml` (stage) unless
Owner explicitly lists those paths in GO (default: leave them alone).

## Modes

### CHECK (default) — READ_ONLY

1. Resolve the canonical `refs/heads/scripts` snapshot before checking the
   Registry; never require or read a caller-local Registry for bootstrap.
2. Verify presence and minimal shape of the three artifacts above in that
   canonical snapshot.
3. Grep/read bounded sections only; do not dump whole `.cursor/commands/**`.
4. Emit `SCRIPTS_INFRA_REPORT` with gaps and pasteable GO if needed.
5. Never write files. Never apply Jobs. Never push.

### GO — materialize missing

Mutate **only** after GO gate passes. Create or repair allowlisted missing
files. Prefer additive create over rewriting working content.

Do not run Kubernetes Jobs here. Do not push to remote from prepare.
Image-publish push of branch `scripts` belongs to `/opsx-scripts PUSH GO`
(intentional no-PR path), not this command.

## Authority surfaces

```text
KNOWLEDGE:  .cursor/rules/devops.mdc (forbids / cluster facts)
SHELL:      .cursor/rules/terminal.mdc
WORKFLOW:   this command (prepare only)
OPERATE:    /opsx-scripts
CLUSTER_GENERIC: /opsx-devops
```

Exactly one write decision owner: **Owner** via `GO`.
Must not re-decide `/opsx-verify`, archive, or product GO gates.

## Hard forbid list (all modes)

Same class as `/opsx-devops` where applicable:

| FORBIDDEN_HIT | Rule |
|---------------|------|
| `CSI` | Never apply/edit `k8s/**csi**` |
| `PORT_FORWARD` | Never `kubectl port-forward` |
| `SECRET_DUMP` | Never print Secret data values |
| `PROD_DB_MIGRATION` | No production DB migrations here |
| `REWRITE_WORKING_SCRIPTS` | Do not “improve” working `scripts/**` unless path explicitly in GO |
| `MASTER_STAGE_HIJACK` | Do not alter master/stage deploy workflows by default |
| `PRODUCT_APP_FIX` | No `app/**` bugfixes → product commands |

On hit → `STATUS=BLOCKED`, `FORBIDDEN_HIT=<id>`, no mutate.

## WRITE allowlist (GO only)

```text
WRITE_CLASS: SCRIPTS_INFRA_MATERIALIZE
```

Allowed paths (create/update only when missing or Owner-listed gap):

1. `.github/workflows/deploy_scripts.yml`
2. `k8s/jobs/ops-script-runner.yaml`
3. `scripts/REGISTRY.yaml` and generated `scripts/REGISTRY.md` (Registry v2
   schema including required `title` + `path`, seed rows; reconcile missing
   entrypoints / backfill missing titles)

Optional companion soft redirects only if already part of an approved packet
(normally already present): `.cursor/commands/opsx-devops.md`,
`.cursor/commands/opsx-admin-command-consult.md`.

## GO gate

`GO` is valid only when **all** hold:

1. User input contains exact token `GO`.
2. Intent is prepare/materialize (`intent=materialize_missing` **or** CHECK
   report in this turn listed concrete gaps).
3. Acknowledgement / “ok” / “OPTION A” is **not** GO for this command’s writes
   unless this turn restates scoped materialize intent.
4. Plan does not include any `FORBIDDEN_HIT`.
5. Scope limited to write allowlist.

If any check fails → `STATUS=BLOCKED`; show pasteable GO line.

## Algorithm

1. Parse mode (`CHECK` default; else `GO`).
2. Inspect the three required artifacts (bounded Read/Grep).
3. Classify `SCRIPTS_INFRA`: `READY` | `GAP` | `BLOCKED`.
4. If `CHECK` → report only; `NEXT_ACTION` = operate or pasteable prepare GO.
5. If `GO` → materialize missing allowlisted files → re-check → report.
6. Always end with human return contract.

## SCRIPTS_INFRA_REPORT (required fields)

```text
SCRIPTS_INFRA_REPORT:
SCRIPTS_INFRA: UNKNOWN | GAP | READY | BLOCKED
WORKFLOW_PATH:
WORKFLOW_STATUS: PRESENT | MISSING | INVALID
JOB_TEMPLATE_PATH:
JOB_TEMPLATE_STATUS: PRESENT | MISSING | INVALID
REGISTRY_PATH: scripts/REGISTRY.yaml + scripts/REGISTRY.md
REGISTRY_STATUS: PRESENT | MISSING | INVALID
GAPS:
REUSED_EXISTING:
FORBIDDEN_CHECK: PASS | FAIL
OWNER_GO_LINE:
```

## Return contract (mandatory)

```text
STATUS: INFRA_READY | INFRA_GAP | INFRA_MATERIALIZED | BLOCKED | REDIRECT_OPERATE | REDIRECT_DEVOPS
MODE: CHECK | APPLY
SCRIPTS_INFRA: UNKNOWN | GAP | READY | BLOCKED
FORBIDDEN_HIT: NONE | <id>

WHAT_HAPPENED:
WHY:
CURRENT_STATE:
OWNER_DECISION_REQUIRED: yes | no
NEXT_ACTION:
DO_NOT_DO_YET:
```

`NEXT_ACTION` must be pasteable (`/opsx-scripts-prepare GO …`,
`/opsx-scripts INVENTORY`, `/opsx-devops …`, or stop).

When process-surface files changed in this turn:
`NEXT_ACTION` → `/opsx-admin-command-commit` (not `/opsx-commit`).

## Failure / recovery

* Materialize failure → stop; `BLOCKED`; no partial silent invent beyond allowlist.
* Recovery: `CHECK` → new scoped `GO`.
* Cluster symptoms discovered during check → `REDIRECT_DEVOPS`.

## Pipeline position

```text
ENTRY_STATE: SCRIPTS_INFRA_UNKNOWN | SCRIPTS_INFRA_GAP
PREVIOUS: owner prompt | consult route
COMMAND_ACTION: check + optional GO materialize
EXIT_STATE: SCRIPTS_INFRA_READY | GAP | BLOCKED
NEXT: /opsx-scripts INVENTORY
FAILURE: OWNER_DECISION_REQUIRED; no Job run; no product gate bypass
```

Not a bug-episode or archive hard gate.

## Self-check before finish

- [ ] Default CHECK did not write
- [ ] GO without scope → BLOCKED
- [ ] master/stage workflows untouched by default
- [ ] No Job apply from prepare
- [ ] Working scripts not rewritten
- [ ] Human block includes NEXT_ACTION and DO_NOT_DO_YET
