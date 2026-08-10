---
description: "DevOps side-lane: default READ_ONLY Kubernetes/manifest investigation; PLAN_WRITE then GO for allowlisted cluster mutations; durable OPS_STATE memory for safe prod release."
argument-hint: "[INVESTIGATE] [ns=…] [focus=…] [paths=…] [symptom=…] | PLAN_WRITE … | GO …"
---

# /opsx-devops

Side-lane **DevOps assistant** for cluster and infra work.

Default is **READ_ONLY** investigation (kubectl read verbs + repo manifests/docs).
Cluster **write** mutations run only under explicit `GO` against an allowlisted
`DEVOPS_WRITE_PLAN`.

Knowledge source of truth for project DevOps facts remains
`.cursor/rules/devops.mdc`. Durable **ops memory** (infra snapshot + past
actions) lives in `.cursor/devops/OPS_STATE.md` (+ `LAST.json`). This command
owns **workflow, modes, and gates** — not a second copy of domain docs.

Follow `.cursor/commands/opsx-source-resolution.md` and
`.cursor/commands/opsx-execution-preflight.md` (purpose-driven shells; PowerShell
kubectl paths per `.cursor/rules/terminal.mdc`).

## What this is

* Front door for safe Kubernetes / monitoring / `k8s/**` ops help.
* Modes: `INVESTIGATE` (default) → `PLAN_WRITE` → `GO` (apply).
* Enforcer of hard forbids already in
  `local-production-entrypoints.mdc`, `debug-runtime.mdc`, and CSI policy in
  `devops.mdc`.
* Staff path for **safe prod image + DB migrate** (`SAFE_PROD_RELEASE`) that
  continues from durable `OPS_STATE` (not from empty chat).
* Emitter of pasteable human next-action blocks.

## What this is NOT

* NOT product bug fix (→ `/opsx-fix-bug` / bug-episode).
* NOT OpenSpec change implement (→ `/opsx-apply`).
* NOT process-command design (→ `/opsx-admin-command-design-command`).
* NOT archive / verify / sync gate.
* NOT a hard edge on `.cursor/pipeline/GRAPH.md` (side-lane; optional soft
  register via `/opsx-pipeline UPDATE GO` later).
* NOT license to port-forward, dump secrets, or apply CSI manifests.
* NOT flip `PROD_AUTOMATION_ENABLEMENT_ALLOWED=YES` (Owner + runbook only).
* NOT laptop/`alembic upgrade` against production.

## When to use

* Pod / log / event / resource / alert diagnosis in cluster.
* Review `k8s/**` or monitoring manifests before a change.
* Planned safe apply / rollout restart / bounded scale after `PLAN_WRITE` + `GO`.
* Safe prod release: CONTROL → Migrate Job → Deployment CAS →
  `complete_release` (when lease acquired) → OPS_STATE refresh
  (`intent=safe_prod_release` | `migrate_rollout` | `image_cas`).

## When not to use

* Behavioral product bug → `/opsx-fix-bug` (`STATUS=REDIRECT_PRODUCT`).
* Feature / OpenSpec work → `/opsx-new` / `/opsx-ff` / `/opsx-apply`.
* Process/admin routing ambiguity → `/opsx-admin-command-consult`.
* Local app debug via kubectl port-forward → forbidden; use
  `.cursor/rules/local-production-entrypoints.mdc`.
* CSI / provider PVC issues → escalate to provider; never apply `k8s/**csi**`.

## User input

```text
$ARGUMENTS
```

| Token | Effect |
|-------|--------|
| (default) / `INVESTIGATE` | READ_ONLY investigation |
| `PLAN_WRITE` | Produce `DEVOPS_WRITE_PLAN`; no cluster mutate |
| `GO` | Apply only the scoped allowlisted plan (see GO gate) |
| `ns=<namespace>` | Bound namespace focus |
| `focus=pods\|logs\|events\|resources\|alerts\|manifests` | Investigation focus; default `pods` |
| `paths=a,b` | Exact manifest / doc paths |
| `symptom=…` | Free-text symptom (rest of args after token OK) |
| `intent=…` | Write intent for `PLAN_WRITE` / `GO` |
| `resource=deploy/name` | Named workload for restart/scale plans |
| `image=…` / `digest=sha256:…` | Target RELEASE image for safe prod release |
| `CONTROL_DRY_RUN=0\|1` | CONTROL Job dry-run (no lease) when planning migrate path |
| unknown conflicting mode | `STATUS=BLOCKED` |

Recognized `intent=` values (non-exhaustive):

| intent | WRITE_CLASS (typical) |
|--------|------------------------|
| `restart` / scale / apply paths | `ROLLOUT` / `SCALE` / `MANIFEST_APPLY` |
| `safe_prod_release` | `SAFE_PROD_RELEASE` (CONTROL→Migrate→CAS→complete_release→OPS_STATE) |
| `migrate_rollout` | `SAFE_PROD_RELEASE` (same order; emphasize migrate) |
| `image_cas` | `SAFE_PROD_RELEASE` (CAS [+ complete_release if lease held] when schema already at target) |

Examples:

```text
/opsx-devops symptom=CrashLoop shop-runner
/opsx-devops INVESTIGATE ns=default focus=logs
/opsx-devops PLAN_WRITE intent=restart deploy/adv-bot ns=default
/opsx-devops GO intent=restart deploy/adv-bot ns=default
/opsx-devops PLAN_WRITE intent=safe_prod_release ns=prod-adv-bot image=harbor…/adv-bot:<sha> digest=sha256:…
/opsx-devops GO intent=safe_prod_release ns=prod-adv-bot image=harbor…/adv-bot:<sha> digest=sha256:…
```

## Durable memory (mandatory)

```text
OPS_STATE:     .cursor/devops/OPS_STATE.md
OPS_LAST:      .cursor/devops/LAST.json
PROCEDURE:     DEVOPS_DB_MIGRATIONS.md
KNOWLEDGE:     .cursor/rules/devops.mdc
EPHEMERAL:     .tmp/opsx-devops/<UTC_TS>/   (optional; NOT source of truth)
```

Rules:

1. At start of **every** mode, Read `OPS_STATE.md` + `LAST.json` (if present)
   **before** inventing infra facts or release steps.
2. For `intent=safe_prod_release|migrate_rollout|image_cas`, also Read
   `DEVOPS_DB_MIGRATIONS.md` (Command contract + release order).
3. PLAN must continue from OPS_STATE (e.g. skip Migrate when
   `alembic_head` already equals target; skip CONTROL acquire when dry-run only).
4. After successful `GO` that changes cluster release posture, **update**
   `OPS_STATE.md` + `LAST.json` in the same turn (no secrets/DSN/passwords).
5. Durable memory that must survive sessions = committed OPS_STATE / LAST.json /
   runbook / devops.mdc — never chat history, never `.tmp` alone.
6. Commit ownership after updates:
   - `.cursor/devops/**` (OPS_STATE / LAST.json) + `.cursor/commands/opsx-devops.md`
     + `.cursor/rules/devops.mdc` → `/opsx-meta-commit` (not `/opsx-commit`;
     `/opsx-admin-command-commit` is obsolete redirect-only);
   - `DEVOPS_DB_MIGRATIONS.md` (ordinary project docs) → `/opsx-commit`.

## Modes

### INVESTIGATE (default) — READ_ONLY

Allowed cluster reads (PowerShell kubectl):

* `kubectl get` / `describe` / `logs` / `top` / `events` / `api-resources`
* `kubectl get … -o yaml` for non-Secret resources (redact Secret **data** values
  if accidentally fetched — never print secret payloads)

Allowed repo reads:

* `.cursor/devops/OPS_STATE.md`, `.cursor/devops/LAST.json`
* `.cursor/rules/devops.mdc`, `terminal.mdc`, `local-production-entrypoints.mdc`,
  `debug-runtime.mdc`
* `DEVOPS_*.md`, referenced `k8s/**`, monitoring docs

Forbidden in this mode:

* Any mutating kubectl (`apply`, `delete`, `patch`, `scale`, `rollout restart`,
  `exec` that changes state, `create`, …)
* `port-forward`, Secret value dumps, CSI apply

Optional ephemeral receipt (not SoT):
`.tmp/opsx-devops/<UTC_TS>/INVESTIGATION.md`

### PLAN_WRITE — READ_ONLY plan

Produce a structured `DEVOPS_WRITE_PLAN` only. May run
`kubectl apply --dry-run=client` against listed paths. No live mutate.

Without enough scope (`intent` / `paths` / `resource`) → `STATUS=BLOCKED` with
the exact missing fields.

For `SAFE_PROD_RELEASE` intents: plan **ordered** steps only
(CONTROL → Migrate → CAS → `complete_release` when lease acquired →
OPS_STATE). Out-of-order plans → `STATUS=BLOCKED`.

### GO — allowlisted write

Mutate **only** after GO gate passes (below). Restate the plan before each
mutating step. Stop on first unexpected failure; do not retry mutating ops in a
loop.

After success on release intents: refresh OPS_STATE / LAST.json.

## Authority surfaces

```text
KNOWLEDGE:  .cursor/rules/devops.mdc
MEMORY:     .cursor/devops/OPS_STATE.md + LAST.json
PROCEDURE:  DEVOPS_DB_MIGRATIONS.md
SHELL:      .cursor/rules/terminal.mdc
LOCAL_DEBUG_BAN: .cursor/rules/local-production-entrypoints.mdc
DEBUG_RUNTIME:   .cursor/rules/debug-runtime.mdc
WORKFLOW:   this command
```

Exactly one write decision owner: **Owner** via `GO`.
This command must not re-decide `/opsx-verify`, archive, or product GO gates.

## Hard forbid list (all modes)

| FORBIDDEN_HIT | Rule |
|---------------|------|
| `CSI` | Never apply/edit `k8s/**csi**` in provider cluster |
| `PORT_FORWARD` | Never `kubectl port-forward` (any service) |
| `CLUSTER_REDIS_TUNNEL` | Never tunnel/use cluster Redis for local shop-runner debug |
| `SECRET_DUMP` | Never print Secret `data` values / tokens / passwords |
| `NAMESPACE_DELETE` | Never delete a namespace |
| `UNCONTROLLED_FORCE_DELETE` | No force-delete cascades without Owner explicit plan field |
| `PROD_DB_MIGRATION_UNSAFE` | No laptop/`alembic upgrade` on prod; no migrate in startup/initContainer; no exec RELEASE as provenance extractor; no blind retry after PARTIAL_OR_UNKNOWN |
| `BARE_SET_IMAGE` | No `kubectl set image` without JSON Patch `test`+`replace` CAS |
| `PRODUCT_APP_FIX` | No `app/**` bugfixes here → `REDIRECT_PRODUCT` |

On hit → `STATUS=BLOCKED`, `FORBIDDEN_HIT=<id>`, no mutate.

**Note:** Job-path CONTROL/Migrate under `WRITE_CLASS=SAFE_PROD_RELEASE` after
Owner `GO` is **allowed**. That is not `PROD_DB_MIGRATION_UNSAFE`.

## WRITE allowlist (GO only)

```text
WRITE_CLASS:
  MANIFEST_APPLY | ROLLOUT | SCALE | CONFIG_PATCH | SAFE_PROD_RELEASE | OTHER_ALLOWLISTED
```

Allowed only when named in the active plan:

1. `MANIFEST_APPLY` — `kubectl apply -f <listed paths>` after successful
   `--dry-run=client` (PowerShell `.\path\` style).
2. `ROLLOUT` — `kubectl rollout restart` / `status` for named
   `deployment|statefulset` + namespace.
3. `SCALE` — `kubectl scale` for named workload + **bounded** replica count in plan.
4. `CONFIG_PATCH` — non-CSI ConfigMap / AlertmanagerConfig (or equivalent)
   changes explicitly listed; prefer manifest apply over ad-hoc patch.
5. `SAFE_PROD_RELEASE` — ordered staff path only:
   - apply/render CONTROL Job from `k8s/jobs/app-db-control.yaml` (optional
     `CONTROL_DRY_RUN=1`);
   - apply/render Migrate Job from `k8s/jobs/app-db-migrate.yaml` (skip if
     OPS_STATE already at target revision / prior SUCCESS_NOOP for same head);
   - Deployment CAS: JSON Patch `test`+`replace` on container image for listed
     entrypoints (never bare `set image`);
   - `complete_release` (SECURITY DEFINER / control SQL) to free singleton lease
     when CONTROL acquired a lease (`CONTROL_DRY_RUN≠1`); **skip** when
     `CONTROL_DRY_RUN=1` or no lease was taken (dry-run / image_cas-only with
     no active lease per OPS_STATE);
   - RO log/rollout verify; update OPS_STATE.md + LAST.json.
6. `OTHER_ALLOWLISTED` — only if plan lists exact commands and Owner GO restates
   them; still subject to hard forbids.

Always: backup note (`kubectl get … -o yaml` to a local path under `.tmp/` or
plan-stated path) before destructive-ish applies when practical.

## GO gate

`GO` is valid only when **all** hold:

1. User input contains exact token `GO`.
2. A scoped plan is present in this turn (pasted `DEVOPS_WRITE_PLAN` **or**
   explicit `intent=` + enough `ns=` / `resource=` / `paths=` / `image=` to
   uniquely identify one allowlisted action class).
3. Acknowledgement / “ok” / “OPTION A” is **not** GO.
4. Plan does not include any `FORBIDDEN_HIT`.
5. Commands use PowerShell-safe kubectl invocation (no `grep`/`&&`/Unix-only paths).
6. For `SAFE_PROD_RELEASE`: OPS_STATE + `DEVOPS_DB_MIGRATIONS.md` were read this
   turn; step order is CONTROL → Migrate → CAS → `complete_release` (if lease
   acquired) → OPS_STATE (omitting only steps justified by OPS_STATE /
   `CONTROL_DRY_RUN`).

If any check fails → `STATUS=BLOCKED`; show the exact pasteable GO command.

## Algorithm

1. Parse mode (`INVESTIGATE` default; else `PLAN_WRITE` / `GO`).
2. If symptom is clearly a product bug → `REDIRECT_PRODUCT` (do not deepen cluster
   write planning).
3. Load memory + knowledge (OPS_STATE, LAST.json, devops.mdc; runbook when
   release intent).
4. `INVESTIGATE`: run bounded RO kubectl + manifest reads; summarize vs OPS_STATE.
5. `PLAN_WRITE`: emit `DEVOPS_WRITE_PLAN` continuing from OPS_STATE + dry-run if paths given.
6. `GO`: restate plan → dry-run when apply → mutate once per planned step →
   verify with RO kubectl → update OPS_STATE/LAST.json on success.
7. Always end with human return contract.

## DEVOPS_WRITE_PLAN (required fields)

```text
DEVOPS_WRITE_PLAN:
WRITE_CLASS:
NS:
RESOURCES:
PATHS:
EXACT_COMMANDS:
OPS_STATE_BASIS: <one-line summary of what memory justified skips/includes>
DRY_RUN_RESULT:
ROLLBACK_HINT:
FORBIDDEN_CHECK: PASS | FAIL
RISKS:
OWNER_GO_LINE:
```

`OWNER_GO_LINE` must be a pasteable `/opsx-devops GO …` invoking the same scope.

## Return contract (mandatory)

Every completion:

```text
STATUS: INVESTIGATION_DONE | WRITE_PLAN_READY | WRITE_APPLIED | BLOCKED | REDIRECT_PRODUCT | REDIRECT_PROCESS
MODE: INVESTIGATE | PLAN_WRITE | APPLY
WRITE_CLASS: NONE | MANIFEST_APPLY | ROLLOUT | SCALE | CONFIG_PATCH | SAFE_PROD_RELEASE | OTHER_ALLOWLISTED
FORBIDDEN_HIT: NONE | <id>
OPS_STATE_READ: yes | no
OPS_STATE_UPDATED: yes | no

WHAT_HAPPENED:
WHY:
CURRENT_STATE:
OWNER_DECISION_REQUIRED: yes | no
NEXT_ACTION:
DO_NOT_DO_YET:
```

`NEXT_ACTION` must be pasteable (next `/opsx-devops …`, `/opsx-meta-commit`,
product redirect, or stop).

## Failure / recovery

* Mutating failure → stop; `STATUS=BLOCKED`; leave cluster as-is; no silent retry loop.
* Migrate started then failed → treat as `PARTIAL_OR_UNKNOWN`; do **not** blind re-apply.
* Recovery: `/opsx-devops INVESTIGATE` → new `PLAN_WRITE` → new `GO`.
* Same mutating error ≥ 3 times → stop; escalate to Owner (do not invent a fourth approach that widens write scope).

## Pipeline position

```text
ENTRY_STATE: ops_question | cluster_symptom | manifest_change_intent | ops_release_intent
EXIT_STATE: INVESTIGATION_DONE | WRITE_PLAN_READY | WRITE_APPLIED | BLOCKED | REDIRECT_*
PREVIOUS: owner prompt | consult route
NEXT: owner GO | admin-commit (process/memory files) | product command | stop
FAILURE: OWNER_DECISION_REQUIRED; no bypass of product/verify gates
```

Not a bug-episode or archive hard gate.

## Self-check before finish

- [ ] Default / INVESTIGATE did not mutate cluster
- [ ] OPS_STATE read at start (when files exist)
- [ ] Release intents read DEVOPS_DB_MIGRATIONS.md
- [ ] GO without scoped plan → BLOCKED
- [ ] CSI / port-forward / secret dump / bare set image / laptop alembic rejected
- [ ] Product bug → REDIRECT_PRODUCT
- [ ] PowerShell path / filter rules preserved
- [ ] Successful SAFE_PROD_RELEASE GO: `complete_release` when lease acquired;
      skipped only for CONTROL_DRY_RUN=1 / no lease
- [ ] Successful SAFE_PROD_RELEASE GO updated OPS_STATE.md + LAST.json
- [ ] Human block includes NEXT_ACTION and DO_NOT_DO_YET
