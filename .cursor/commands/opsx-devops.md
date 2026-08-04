---
description: "DevOps side-lane: default READ_ONLY Kubernetes/manifest investigation; PLAN_WRITE then GO for allowlisted cluster mutations."
argument-hint: "[INVESTIGATE] [ns=…] [focus=…] [paths=…] [symptom=…] | PLAN_WRITE … | GO …"
---

# /opsx-devops

Side-lane **DevOps assistant** for cluster and infra work.

Default is **READ_ONLY** investigation (kubectl read verbs + repo manifests/docs).
Cluster **write** mutations run only under explicit `GO` against an allowlisted
`DEVOPS_WRITE_PLAN`.

Knowledge source of truth for project DevOps facts remains
`.cursor/rules/devops.mdc`. This command owns **workflow, modes, and gates** —
not a second copy of domain docs.

Follow `.cursor/commands/opsx-source-resolution.md` and
`.cursor/commands/opsx-execution-preflight.md` (purpose-driven shells; PowerShell
kubectl paths per `.cursor/rules/terminal.mdc`).

## What this is

* Front door for safe Kubernetes / monitoring / `k8s/**` ops help.
* Modes: `INVESTIGATE` (default) → `PLAN_WRITE` → `GO` (apply).
* Enforcer of hard forbids already in
  `local-production-entrypoints.mdc`, `debug-runtime.mdc`, and CSI policy in
  `devops.mdc`.
* Emitter of pasteable human next-action blocks.

## What this is NOT

* NOT product bug fix (→ `/opsx-fix-bug` / bug-episode).
* NOT OpenSpec change implement (→ `/opsx-apply`).
* NOT process-command design (→ `/opsx-admin-command-design-command`).
* NOT `scripts/` inventory, readiness ledger, local script test, or script Job
  lifecycle (→ `/opsx-scripts`; infra bootstrap → `/opsx-scripts-prepare`).
* NOT archive / verify / sync gate.
* NOT a hard edge on `.cursor/pipeline/GRAPH.md` (side-lane; optional soft
  register via `/opsx-pipeline UPDATE GO` later).
* NOT license to port-forward, dump secrets, or apply CSI manifests.

## When to use

* Pod / log / event / resource / alert diagnosis in cluster.
* Review `k8s/**` or monitoring manifests before a change.
* Planned safe apply / rollout restart / bounded scale after `PLAN_WRITE` + `GO`.

## When not to use

* Behavioral product bug → `/opsx-fix-bug` (`STATUS=REDIRECT_PRODUCT`).
* Feature / OpenSpec work → `/opsx-new` / `/opsx-ff` / `/opsx-apply`.
* `scripts/` inventory / readiness / local check / script image+Job run →
  `/opsx-scripts` (`STATUS=REDIRECT_PROCESS` with that next action).
* Missing scripts workflow / Job template / registry → `/opsx-scripts-prepare`.
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
| unknown conflicting mode | `STATUS=BLOCKED` |

Examples:

```text
/opsx-devops symptom=CrashLoop shop-runner
/opsx-devops INVESTIGATE ns=default focus=logs
/opsx-devops PLAN_WRITE intent=restart deploy/adv-bot ns=default
/opsx-devops GO intent=restart deploy/adv-bot ns=default
```

## Modes

### INVESTIGATE (default) — READ_ONLY

Allowed cluster reads (PowerShell kubectl):

* `kubectl get` / `describe` / `logs` / `top` / `events` / `api-resources`
* `kubectl get … -o yaml` for non-Secret resources (redact Secret **data** values
  if accidentally fetched — never print secret payloads)

Allowed repo reads:

* `.cursor/rules/devops.mdc`, `terminal.mdc`, `local-production-entrypoints.mdc`,
  `debug-runtime.mdc`
* `DEVOPS_*.md`, referenced `k8s/**`, monitoring docs

Forbidden in this mode:

* Any mutating kubectl (`apply`, `delete`, `patch`, `scale`, `rollout restart`,
  `exec` that changes state, `create`, …)
* `port-forward`, Secret value dumps, CSI apply

Optional durable receipt (not required):
`.tmp/opsx-devops/<UTC_TS>/INVESTIGATION.md`

### PLAN_WRITE — READ_ONLY plan

Produce a structured `DEVOPS_WRITE_PLAN` only. May run
`kubectl apply --dry-run=client` against listed paths. No live mutate.

Without enough scope (`intent` / `paths` / `resource`) → `STATUS=BLOCKED` with
the exact missing fields.

### GO — allowlisted write

Mutate **only** after GO gate passes (below). Restate the plan before each
mutating step. Stop on first unexpected failure; do not retry mutating ops in a
loop.

## Authority surfaces

```text
KNOWLEDGE:  .cursor/rules/devops.mdc
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
| `PROD_DB_MIGRATION` | No production DB migrations via this command |
| `PRODUCT_APP_FIX` | No `app/**` bugfixes here → `REDIRECT_PRODUCT` |

On hit → `STATUS=BLOCKED`, `FORBIDDEN_HIT=<id>`, no mutate.

## WRITE allowlist (GO only)

```text
WRITE_CLASS:
  MANIFEST_APPLY | ROLLOUT | SCALE | CONFIG_PATCH | OTHER_ALLOWLISTED
```

Allowed only when named in the active plan:

1. `MANIFEST_APPLY` — `kubectl apply -f <listed paths>` after successful
   `--dry-run=client` (PowerShell `.\path\` style).
2. `ROLLOUT` — `kubectl rollout restart` / `status` for named
   `deployment|statefulset` + namespace.
3. `SCALE` — `kubectl scale` for named workload + **bounded** replica count in plan.
4. `CONFIG_PATCH` — non-CSI ConfigMap / AlertmanagerConfig (or equivalent)
   changes explicitly listed; prefer manifest apply over ad-hoc patch.
5. `OTHER_ALLOWLISTED` — only if plan lists exact commands and Owner GO restates
   them; still subject to hard forbids.

Always: backup note (`kubectl get … -o yaml` to a local path under `.tmp/` or
plan-stated path) before destructive-ish applies when practical.

## GO gate

`GO` is valid only when **all** hold:

1. User input contains exact token `GO`.
2. A scoped plan is present in this turn (pasted `DEVOPS_WRITE_PLAN` **or**
   explicit `intent=` + enough `ns=` / `resource=` / `paths=` to uniquely
   identify one allowlisted action class).
3. Acknowledgement / “ok” / “OPTION A” is **not** GO.
4. Plan does not include any `FORBIDDEN_HIT`.
5. Commands use PowerShell-safe kubectl invocation (no `grep`/`&&`/Unix-only paths).

If any check fails → `STATUS=BLOCKED`; show the exact pasteable GO command.

## Algorithm

1. Parse mode (`INVESTIGATE` default; else `PLAN_WRITE` / `GO`).
2. If symptom is clearly a product bug → `REDIRECT_PRODUCT` (do not deepen cluster
   write planning).
3. Load knowledge rules (bounded Read; Grep-first).
4. `INVESTIGATE`: run bounded RO kubectl + manifest reads; summarize evidence.
5. `PLAN_WRITE`: emit `DEVOPS_WRITE_PLAN` + dry-run if paths given.
6. `GO`: restate plan → dry-run when apply → mutate once per planned step →
   verify with RO kubectl.
7. Always end with human return contract.

## DEVOPS_WRITE_PLAN (required fields)

```text
DEVOPS_WRITE_PLAN:
WRITE_CLASS:
NS:
RESOURCES:
PATHS:
EXACT_COMMANDS:
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
WRITE_CLASS: NONE | MANIFEST_APPLY | ROLLOUT | SCALE | CONFIG_PATCH | OTHER_ALLOWLISTED
FORBIDDEN_HIT: NONE | <id>

WHAT_HAPPENED:
WHY:
CURRENT_STATE:
OWNER_DECISION_REQUIRED: yes | no
NEXT_ACTION:
DO_NOT_DO_YET:
```

`NEXT_ACTION` must be pasteable (next `/opsx-devops …`, product redirect, or stop).

## Failure / recovery

* Mutating failure → stop; `STATUS=BLOCKED`; leave cluster as-is; no silent retry loop.
* Recovery: `/opsx-devops INVESTIGATE` → new `PLAN_WRITE` → new `GO`.
* Same mutating error ≥ 3 times → stop; escalate to Owner (do not invent a fourth approach that widens write scope).

## Pipeline position

```text
ENTRY_STATE: ops_question | cluster_symptom | manifest_change_intent
EXIT_STATE: INVESTIGATION_DONE | WRITE_PLAN_READY | WRITE_APPLIED | BLOCKED | REDIRECT_*
PREVIOUS: owner prompt | consult route
NEXT: owner GO | product command | stop
FAILURE: OWNER_DECISION_REQUIRED; no bypass of product/verify gates
```

Not a bug-episode or archive hard gate.

## Self-check before finish

- [ ] Default / INVESTIGATE did not mutate cluster
- [ ] GO without scoped plan → BLOCKED
- [ ] CSI / port-forward / secret dump rejected if requested
- [ ] Product bug → REDIRECT_PRODUCT
- [ ] PowerShell path / filter rules preserved
- [ ] Human block includes NEXT_ACTION and DO_NOT_DO_YET
