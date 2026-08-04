---
name: /opsx-scripts
id: opsx-scripts
category: Workflow
description: "Daily scripts/ ops: inventory, readiness ledger, local test, PLAN_RUN/RUN Job via scripts-branch image, battle-tested recording."
argument-hint: "[INVENTORY|STATUS|TEST_LOCAL|PLAN_RUN|RUN|RECORD_BATTLE] [script=…] [args=…] [ns=…] [GO]"
---

# /opsx-scripts

Side-lane **daily** operator command for `scripts/` lifecycle:

* inventory current entrypoints;
* track readiness (`runnable` / `tests` / `battle_tested`);
* local workability checks (reuse project pytest / smoke; do not invent a new framework);
* plan and (with `GO`) run via **image from branch `scripts` → Kubernetes Job → report**.

Infra bootstrap / repair → `/opsx-scripts-prepare` (keep that out of daily context).

Follow `.cursor/commands/opsx-source-resolution.md` and
`.cursor/commands/opsx-execution-preflight.md` (PowerShell kubectl per
`.cursor/rules/terminal.mdc`).

## What this is

* Front door for script inventory, ledger updates, local checks, and script Jobs.
* Consumer of `SCRIPTS_INFRA_READY` artifacts from `/opsx-scripts-prepare`.
* Emitter of `SCRIPTS_REPORT` with explicit human next action.

## What this is NOT

* NOT one-shot infra materialize → `/opsx-scripts-prepare`.
* NOT generic cluster diagnose → `/opsx-devops`.
* NOT bug-episode RED/GREEN writer → `/opsx-test` / `/opsx-fix-bug`.
* NOT OpenSpec feature implement / verify / archive.
* NOT silent rewrite of working scripts.
* NOT CSI / port-forward / secret dump / prod DB migration.

## When to use

* “What scripts exist and what is their readiness?”
* “Check this script locally / cover with a smoke test.”
* “Plan or run script X via image + Job.”
* “Mark script as battle-tested after real use.”

## When not to use

* Missing workflow / Job template / registry schema → `/opsx-scripts-prepare`.
* Pod/node/alert diagnosis unrelated to a script Job → `/opsx-devops`.
* Product behavioral bug → `/opsx-fix-bug`.
* Need a new process command → `/opsx-admin-command-design-command`.

## Preconditions

Before `PLAN_RUN` / `RUN`:

1. `scripts/REGISTRY.md` exists (else redirect prepare).
2. `.github/workflows/deploy_scripts.yml` exists (else redirect prepare).
3. `k8s/jobs/ops-script-runner.yaml` exists (else redirect prepare).

If any missing → `STATUS=BLOCKED` / `REDIRECT_PREPARE` with pasteable
`/opsx-scripts-prepare CHECK` (or `GO` if gaps already known).

## User input

```text
$ARGUMENTS
```

| Token | Effect |
|-------|--------|
| `INVENTORY` (default if bare) | Reconcile `scripts/**` entrypoints ↔ registry |
| `STATUS` | Show ledger for `script=` or summary |
| `TEST_LOCAL` | Local workability / targeted pytest; update ledger |
| `PLAN_RUN` | Build Job plan from template; no cluster mutate |
| `RUN` | Requires `GO`; apply one Job; collect report |
| `RECORD_BATTLE` | Requires Owner evidence; set `battle_tested=YES` |
| `script=<path>` | Target under `scripts/` |
| `args=…` | Extra CLI args for the script (PLAN_RUN/RUN) |
| `ns=<namespace>` | Job namespace; default from template |
| `image=<ref>` | Override image ref (else latest scripts-branch tag/sha) |
| `GO` | Authorize allowlisted write / cluster mutate for this mode |
| unknown conflicting mode | `STATUS=BLOCKED` |

Examples:

```text
/opsx-scripts INVENTORY
/opsx-scripts STATUS script=scripts/export_non_zero_balance_users.py
/opsx-scripts TEST_LOCAL script=scripts/test_path.py
/opsx-scripts PLAN_RUN script=scripts/export_non_zero_balance_users.py
/opsx-scripts RUN GO script=scripts/export_non_zero_balance_users.py
/opsx-scripts RECORD_BATTLE GO script=scripts/export_non_zero_balance_users.py evidence=job/ops-script-…
```

## Ledger contract (`scripts/REGISTRY.md`)

Authoritative readiness fields per entrypoint:

| Field | Values |
|-------|--------|
| `path` | repo-relative path |
| `runnable` | `UNKNOWN` \| `WORKS` \| `BROKEN` |
| `tests` | `NONE` \| `PARTIAL` \| `COVERED` |
| `battle_tested` | `NO` \| `YES` |
| `last_local_at` | ISO UTC or `-` |
| `last_cluster_at` | ISO UTC or `-` |
| `last_image_ref` | image ref or `-` |
| `notes` | short |

Rules:

* `INVENTORY` adds missing entrypoints as `UNKNOWN` / `NONE` / `NO`; does not
  delete Owner notes without cause; marks vanished paths in notes.
* `TEST_LOCAL` may set `runnable` + `tests` + `last_local_at` from evidence.
* `RUN` completion may set `runnable` + `last_cluster_at` + `last_image_ref`
  from Job result; does **not** set `battle_tested=YES`.
* `battle_tested=YES` only via `RECORD_BATTLE` + Owner `GO` + evidence ref.
* Support modules (`set_path.py`, `template_script.py`, `__init__.py`, pure
  helpers) are not Job entrypoints unless Owner promotes them.

## Modes

### INVENTORY — ledger reconcile (may write registry)

Default mode. Scan `scripts/` for entrypoint candidates (top-level runnable
scripts + clear package entrypoints; skip `__init__` / pure helpers).
Update `scripts/REGISTRY.md`. No cluster mutate.

### STATUS — READ_ONLY

Read registry (+ optional script path). No writes.

### TEST_LOCAL — local check (may write registry + tests)

1. Prefer existing project infra: `.venv` pytest, `scripts/test_path.py`,
   narrow smoke import/`--help` if safe.
2. Do **not** invent a parallel test stack.
3. Optional handoff: if substantial new tests needed → recommend `/opsx-test`
   with a concrete request (this command may still record `tests=NONE|PARTIAL`).
4. Update ledger from results.
5. Do not change production `app/**`. Do not rewrite the target script unless
   Owner explicitly scoped a fix (out of default).

### PLAN_RUN — READ_ONLY plan

Produce `SCRIPTS_RUN_PLAN` from `k8s/jobs/ops-script-runner.yaml` with
substituted placeholders. May `kubectl apply --dry-run=client` when paths
ready. No live mutate.

Requires infra preconditions. If image for branch `scripts` is unknown,
state how to obtain it (push to `scripts` / `workflow_dispatch` / pass `image=`).

### RUN — GO cluster execute

1. GO gate must pass.
2. Restate plan; dry-run when apply; create **one** Job.
3. Wait/bounded poll for completion; collect logs / exit code / output paths
   if the script writes known artifacts.
4. Update ledger (`runnable`, cluster timestamps, image ref).
5. Stop on first unexpected failure; no mutate retry loop.
6. Emit `SCRIPTS_REPORT`.

Hard forbids identical in spirit to `/opsx-devops` (CSI, port-forward,
secret dump, namespace delete, uncontrolled force-delete, prod DB migration).

### RECORD_BATTLE — Owner attestation

Set `battle_tested=YES` only with `GO` + `script=` + `evidence=` (Job name,
report path, or Owner note). No cluster mutate required.

## Authority surfaces

```text
LEDGER:     scripts/REGISTRY.md
PREPARE:    /opsx-scripts-prepare
CLUSTER_GENERIC: /opsx-devops
TEST_AUTHORING_HANDOFF: /opsx-test (optional)
KNOWLEDGE_FORBIDS: .cursor/rules/devops.mdc
```

Decision owner: **Owner** for `RUN GO` and `RECORD_BATTLE GO`.
This command must not re-decide verify/archive/product GO.

## GO gate (RUN / RECORD_BATTLE / registry-repair writes that need GO)

For **RUN**:

1. Exact token `GO`.
2. Scoped `SCRIPTS_RUN_PLAN` in this turn **or** enough `script=` + `image=` /
   resolvable scripts-branch image + namespace.
3. Infra preconditions hold.
4. No `FORBIDDEN_HIT`.
5. PowerShell-safe kubectl.

For **RECORD_BATTLE**:

1. Exact `GO` + `script=` + non-empty `evidence=`.

Acknowledgement alone is not GO.

## SCRIPTS_RUN_PLAN (PLAN_RUN / RUN)

```text
SCRIPTS_RUN_PLAN:
SCRIPT:
IMAGE_REF:
NS:
JOB_NAME:
TEMPLATE_PATH: k8s/jobs/ops-script-runner.yaml
COMMAND:
ARGS:
DRY_RUN_RESULT:
ROLLBACK_HINT: delete job/<JOB_NAME> if still present
FORBIDDEN_CHECK: PASS | FAIL
OWNER_GO_LINE:
```

## Return contract (mandatory)

```text
STATUS: INVENTORY_DONE | STATUS_DONE | TEST_DONE | RUN_PLAN_READY | RUN_DONE |
        LEDGER_UPDATED | BLOCKED | REDIRECT_PREPARE | REDIRECT_DEVOPS | REDIRECT_TEST
MODE: INVENTORY | STATUS | TEST_LOCAL | PLAN_RUN | RUN | RECORD_BATTLE
SCRIPTS_INFRA: READY | GAP | UNKNOWN
FORBIDDEN_HIT: NONE | <id>

WHAT_HAPPENED:
WHY:
CURRENT_STATE:
OWNER_DECISION_REQUIRED: yes | no
NEXT_ACTION:
DO_NOT_DO_YET:
```

Optional durable receipt: `.tmp/opsx-scripts/<UTC_TS>/SCRIPTS_REPORT.md`

When process-surface command files change (rare here): commit via
`/opsx-admin-command-commit`. Ledger-only updates under `scripts/REGISTRY.md`
are operated here; Owner decides commit cadence.

## Failure / recovery

* Local test fail → ledger `runnable=BROKEN` or keep `UNKNOWN` with notes;
  `NEXT_ACTION` fix or stop.
* Job fail → `BLOCKED`; leave Job for inspect; suggest
  `/opsx-devops INVESTIGATE` if cluster-generic.
* Same mutate error ≥ 3 → stop; escalate Owner.

## Pipeline position

```text
ENTRY_STATE: SCRIPTS_INFRA_READY + owner intent
PREVIOUS: /opsx-scripts-prepare | prior /opsx-scripts | consult
COMMAND_ACTION: inventory | test | plan/run | record battle
EXIT_STATE: REPORT_READY | LEDGER_UPDATED | BLOCKED | REDIRECT_*
NEXT: Owner | next /opsx-scripts … | /opsx-devops | stop
FAILURE: no bypass of prepare infra or devops forbids
```

## Self-check before finish

- [ ] Infra gap → REDIRECT_PREPARE (not improvised workflow invent in daily mode)
- [ ] RUN without GO → BLOCKED
- [ ] battle_tested not set from RUN alone
- [ ] Working scripts not rewritten by default
- [ ] master/stage deploy workflows not touched
- [ ] NEXT_ACTION + DO_NOT_DO_YET present
