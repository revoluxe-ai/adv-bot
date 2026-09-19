---
name: /opsx-scripts
id: opsx-scripts
category: Workflow
description: "Read-only scripts/ ops with canonical resolver and auditable runtime."
argument-hint: "[INVENTORY|STATUS|TEST_LOCAL|PUSH|PLAN_RUN|RUN|RECORD_BATTLE] [script=<title|path>] [args=…] [ns=…] [GO]"
---

# /opsx-scripts

Side-lane **daily** operator command for `scripts/` lifecycle:

* inventory current entrypoints with human `title` + path hint;
* track readiness (`runnable` / `tests` / `battle_tested`);
* local workability checks (reuse project pytest / smoke; do not invent a new framework);
* with `PUSH GO`, publish current branch `scripts` to origin (no PR) so GHA can build the image;
* plan and (with `RUN GO`) run only a resolver-approved REUSE/COMPOSE plan via
  **image from branch `scripts` → Kubernetes Job → report**.

Owner must not need to memorize repo paths: every human-facing list and
status line uses **`Title (scripts/…/file.py)`** — title first, path only as
a secondary hint in parentheses.

Shared display SoT (cite): `.cursor/commands/opsx-human-label-display.md`.
This command specializes it for `scripts/` (`title` ledger field + path).

Infra bootstrap / repair → `/opsx-scripts-prepare` (keep that out of daily context).

Follow `.cursor/commands/opsx-source-resolution.md`,
`.cursor/commands/opsx-execution-preflight.md`,
`.cursor/commands/opsx-human-label-display.md`, and
`.cursor/commands/opsx-command-role-ownership.md` (PowerShell kubectl per
`.cursor/rules/terminal.mdc`).

**Role ownership:** While this command is `ACTIVE_COMMAND`, stay inside scripts
ops modes (`INVENTORY`/`STATUS`/`TEST_LOCAL`/`PUSH`/`PLAN_RUN`/`RUN`/
`RECORD_BATTLE`). Plain-text «добавь фичу в скрипт / подключи клиент /
реализуй» that needs OpenSpec product change →
`STATUS: ROLE_BOUNDARY_REFUSAL` + pasteable `/opsx-new|/opsx-ff|/opsx-update`
then `/opsx-apply`. Do not silently become product apply. `GO` here authorizes
only this command's allowlisted collector, test, registry, push, and Job paths.
For a factual data-collection goal, `RUN GO` may only reuse or compose rows
already declared in the canonical `scripts/REGISTRY.yaml` snapshot. Missing
capability is a
`FORMAL_CHANGE_REQUIRED` handoff; operational RUN never creates or rewrites
collector code.

## What this is

* Front door for script inventory, ledger updates, local checks, and script Jobs.
* Consumer of `SCRIPTS_INFRA_READY` artifacts from `/opsx-scripts-prepare`.
* Owner of the intentional **no-PR** `git push` of branch `scripts` for image publish
  (`PUSH GO` only — not `/opsx-commit`, not prepare).
* Goal executor: one `RUN GO` owns the safe chain from resolver-approved
  resolution through image readiness, GHA/Job monitoring, logs, known output
  retrieval, and final report.
* The resolver is mandatory; missing capability produces a
  `FORMAL_CHANGE_REQUIRED` handoff instead of a collector write.
* Collector, registry, test, command, branch and Git-history writes are never
  operational RUN paths.
* Emitter of `SCRIPTS_REPORT` with explicit human next action.

## What this is NOT

* NOT one-shot infra materialize → `/opsx-scripts-prepare`.
* NOT generic cluster diagnose → `/opsx-devops`.
* NOT bug-episode RED/GREEN writer → `/opsx-test` / `/opsx-fix-bug`.
* NOT OpenSpec feature implement / verify / archive.
* NOT a collector authoring surface. New or changed collector code belongs to
  `/opsx-ff` or `/opsx-update`, followed by `/opsx-apply`.
* NOT general commit owner → `/opsx-commit` (product) and
  `/opsx-admin-command-commit` (process) own commits outside this lane.
* NOT force-push, push of non-`scripts` branches, merge, rebase, or reset.
* NOT CSI / port-forward / secret dump / prod DB migration.
* NOT a substitute for external handoff packs: research/side dumps ≠ declared
  primary contract artifacts.

## When to use

* “What scripts exist and what is their readiness?”
* “Check this script locally / cover with a smoke test.”
* “Publish branch scripts so GHA builds `:scripts` image.”
* “Plan or run script X via image + Job.”
* “Collect a declared factual data contract: reuse or compose a matching
  collector plan and run it.”
* “Mark script as battle-tested after real use.”

## When not to use

* Missing workflow / Job template / registry schema → `/opsx-scripts-prepare`.
* Pod/node/alert diagnosis unrelated to a script Job → `/opsx-devops`.
* Product behavioral bug → `/opsx-fix-bug`.
* Need a new process command → `/opsx-admin-command-design-command`.

## Preconditions

For `PLAN_RUN` / `RUN`, the command surface performs only the thin bootstrap
preflight before starting the canonical resolver:

1. determine the absolute caller root;
2. select an exact clean `refs/heads/scripts` worktree using the documented
   canonical-root precedence;
3. create an absolute request path and launch the canonical bootstrap.

Before that bootstrap completes, the caller-local `scripts/REGISTRY.yaml`,
`scripts/REGISTRY.md`, collector inventory, matching, and outcome selection
are not read or required. The canonical resolver reads and validates the
Registry from its fixed canonical HEAD. Canonical workflow/template gaps are
reported only after canonical selection and redirect to
`/opsx-scripts-prepare CHECK`.

## User input

```text
$ARGUMENTS
```

| Token | Effect |
|-------|--------|
| `INVENTORY` (default if bare) | Reconcile `scripts/**` entrypoints ↔ registry |
| `STATUS` | Show ledger for `script=` or summary |
| `TEST_LOCAL` | Local workability / targeted pytest; update ledger |
| `PUSH` | Requires `GO`; push branch `scripts` to origin for image build |
| `PLAN_RUN` | Build Job plan from template; no cluster mutate |
| `RUN` | Requires `GO`; execute one resolver-approved REUSE/COMPOSE plan, apply one Job, collect report |
| `RECORD_BATTLE` | Requires Owner evidence; set `battle_tested=YES` |
| `script=<title\|path>` | Optional target by human `title` (preferred) or repo path; required outside goal-driven RUN |
| `request=<goal\|artifact contract>` | Requested data goal and exact output contract; defaults to the current user request |
| `args=…` | Extra CLI args for the script (PLAN_RUN/RUN) |
| `ns=<namespace>` | Job namespace; default from template |
| `image=<ref>` | Override image ref (else latest scripts-branch tag/sha) |
| `GO` | Authorize the allowlisted push or cluster Job path for this mode; never collector/Registry writes |
| unknown conflicting mode | `STATUS=BLOCKED` |

### Script identity and display (mandatory)

Follow `.cursor/commands/opsx-human-label-display.md`. Local rules:

* Ledger field `title` is required for every entrypoint.
* Resolve `script=` as: exact path match, else case-insensitive exact title
  match, else unique case-insensitive title substring.
* For `PLAN_RUN` / `RUN` with `request=` (or a current user request) and no
  `script=`, create the exact request file and invoke the canonical resolver:
  - `REUSE` when one row covers the declared source, capability, fields,
    output and zero-write contracts;
  - `COMPOSE` when an ordered child plan covers the union without semantic
    merge;
  - `FORMAL_CHANGE_REQUIRED` when a new capability or extension is needed;
  - `BLOCKED` when the request or topology is unsafe or ambiguous.
* For `STATUS`, `TEST_LOCAL`, `PUSH`, and `RECORD_BATTLE`, `script=` remains
  mandatory and an ambiguous or missing target returns `STATUS=BLOCKED` with
  candidates listed as `Title (path)`.
* Every human-facing inventory / status / report / `NEXT_ACTION` line names a
  script as **`Title (path)`**. Path alone is not the primary label.
* Pasteable commands may use `script=<Title>` when the title is unique; still
  show `Title (path)` once in `WHAT_HAPPENED` / plan body.
* Job template / kubectl still use the resolved `path` internally.

Examples:

```text
/opsx-scripts INVENTORY
/opsx-scripts STATUS script=Export non-zero balance users
/opsx-scripts TEST_LOCAL script=Path smoke
/opsx-scripts PUSH GO
/opsx-scripts PLAN_RUN script=Export non-zero balance users
/opsx-scripts RUN GO script=Export non-zero balance users
/opsx-scripts RECORD_BATTLE GO script=Export non-zero balance users evidence=job/ops-script-…
```

(Paths remain valid: `script=scripts/export_non_zero_balance_users.py`.)

## Canonical resolver contract

`PLAN_RUN` and `RUN` always create an absolute UTF-8 request file and invoke
the thin canonical bootstrap. The bootstrap is read-only: it records caller
root/worktree/branch/HEAD, selects exact `refs/heads/scripts` using
`--canonical-root` → `SCRIPTS_CANONICAL_ROOT` → `git worktree list
--porcelain`, and launches only the canonical resolver. It does not read
Registry, match collectors, execute Jobs, or interpret outcomes.

The canonical invocation is:

```text
poetry run python <canonical-root>/tools/scripts/bootstrap.py \
  PLAN_RUN|RUN \
  --request-file <absolute-request-path> \
  --caller-root <absolute-caller-root> \
  --canonical-root <absolute-canonical-root>
```

Bootstrap passes the same absolute paths to:

```text
poetry run python <canonical-root>/tools/scripts/resolver.py \
  PLAN_RUN|RUN \
  --request-file <absolute-request-path> \
  --caller-root <absolute-caller-root> \
  --canonical-root <absolute-canonical-root>
```

The resolver independently checks common Git directory, exact branch,
tracked-clean canonical state and fixed HEAD. It reads
`scripts/REGISTRY.yaml` only from that HEAD. A caller-local or stale resolver
is never used. The caller receives no tracked writes.

Automatic matching uses only `resolution_enabled: true` rows and returns one
of `REUSE`, `COMPOSE`, `FORMAL_CHANGE_REQUIRED`, or `BLOCKED`. `REUSE` is also
the machine result for an exact explicit cabinet selection; `EXISTING` is only
a display alias. `CREATED` is never produced.

`REGISTRY_SHA` always means the lowercase 40-hex Git commit containing the
Registry snapshot at or before `EXECUTION_SHA`. If a content digest is
reported, it is additive and named `REGISTRY_SHA256`; it never replaces
`REGISTRY_SHA`.

For `FORMAL_CHANGE_REQUIRED`, persist exactly
`.tmp/opsx-scripts/<run_id>/FORMAL_CHANGE_REQUIRED.json` with schema
`opsx.formal-change-handoff.v1`. `CREATE` selects `/opsx-ff`; `EXTEND` selects
`/opsx-update <owner_change_id>` only when that change exists, otherwise
`/opsx-ff <change_name>`. The prompt includes request/evidence/safety data and
never implicitly authorizes `/opsx-apply`.

## COMPOSE runtime

For `COMPOSE`, the resolver result is passed unchanged to the runtime. The
parent creates `.tmp/opsx-scripts/<run_id>/COMPOSE_MANIFEST.json` with
`schema_version=opsx.compose-manifest.v1` and `status=RUNNING` before the
first child Job. Children execute sequentially in resolver order; every child
must pass its own primary artifact and checksum gate before the next required
child starts.

`tools/scripts/compose_runtime.py` owns manifest evidence only. It never
semantically merges child data. Required failure stops later required children
and marks them `SKIPPED`; optional failure continues and finalizes
`PARTIAL_FAILURE`. Any failure sets `accepted=false` and
`external_handoff_ready=false`. Finalization writes only
`COMPOSE_MANIFEST.json` and the external
`COMPOSE_MANIFEST.json.sha256`; the manifest contains no self-SHA. The final
digest is recorded as `COMPOSE_MANIFEST_SHA256` in `SCRIPTS_REPORT`.

## Ledger contract (`scripts/REGISTRY.md`)

Authoritative readiness fields per entrypoint:

| Field | Values |
|-------|--------|
| `title` | short human name (required; Owner may edit) |
| `path` | repo-relative path (hint / machine id) |
| `runnable` | `UNKNOWN` \| `WORKS` \| `BROKEN` |
| `tests` | `NONE` \| `PARTIAL` \| `COVERED` |
| `battle_tested` | `NO` \| `YES` |
| `last_local_at` | ISO UTC or `-` |
| `last_cluster_at` | ISO UTC or `-` |
| `last_image_ref` | image ref or `-` |
| `notes` | short |

Rules:

* `INVENTORY` adds missing entrypoints as `UNKNOWN` / `NONE` / `NO` and
  **must assign `title`** when missing (prefer module docstring first line;
  else humanize filename / parent package; keep stable once set unless Owner
  renames). Does not delete Owner notes/titles without cause; marks vanished
  paths in notes.
* Table column order for humans: `title`, `path`, then readiness fields.
* `TEST_LOCAL` may set `runnable` + `tests` + `last_local_at` from evidence.
* `RUN` completion reports `runnable` + `last_cluster_at` + `last_image_ref`
  evidence; it does **not** write Registry or set `battle_tested=YES`.
* `battle_tested=YES` only via `RECORD_BATTLE` + Owner `GO` + evidence ref.
* Support modules (`set_path.py`, `template_script.py`, `__init__.py`, pure
  helpers) are not Job entrypoints unless Owner promotes them.

## Modes

### INVENTORY — read-only ledger reconcile

Default mode. Scan `scripts/` for entrypoint candidates (top-level runnable
scripts + clear package entrypoints; skip `__init__` / pure helpers).
Compare entrypoints with the machine Registry and report missing/unregistered
paths. Do not write `REGISTRY.yaml` or generated Markdown from this mode.
Registry changes use `poetry run python tools/scripts/registry.py render`.
Emit the inventory summary as lines of `Title (path)` plus readiness columns.
No cluster mutate.

### STATUS — READ_ONLY

Read registry (+ optional `script=` title or path). Show `Title (path)` as
the primary label. No writes.

### TEST_LOCAL — local check

1. Prefer existing project infra: `.venv` pytest, `scripts/test_path.py`,
   narrow smoke import/`--help` if safe.
2. Do **not** invent a parallel test stack.
3. Optional handoff: if substantial new tests needed → recommend `/opsx-test`
   with a concrete request (this command may still record `tests=NONE|PARTIAL`).
4. Report evidence; do not modify collector, Registry source, or generated
   Markdown from this mode.
5. Do not change production `app/**`. Do not rewrite the target script unless
   Owner explicitly scoped a fix (out of default).

### PLAN_RUN — READ_ONLY plan

Create the request file under `.tmp/opsx-scripts/<run_id>/`, invoke the
canonical bootstrap, and display the exact machine result. `REUSE` displays
one selected entry; `COMPOSE` displays every ordered child, args and outputs;
`FORMAL_CHANGE_REQUIRED` writes its single handoff artifact; `BLOCKED` shows
evidence and next safe action. PLAN_RUN never creates a Job, reads a caller
Registry copy, writes code, or interprets a missing capability as an operational success.

The command is equivalent to the canonical bootstrap invocation above. The
request and all paths are absolute. `RUN` may consume only this result; it
must not re-match or semantically merge it.

### PUSH — GO publish branch `scripts` for image build

Intentional **no-PR** publish path for scripts ops (triggers
`.github/workflows/deploy_scripts.yml` on remote).

1. GO gate for PUSH must pass.
2. `git branch --show-current` MUST be exactly `scripts` → else `STATUS=BLOCKED`.
3. Execution-critical tracked files must be clean. A dirty
   `scripts/REGISTRY.md` created by this command does not block image publish;
   any other tracked dirty path → `STATUS=BLOCKED`, because it may be missing
   from the pushed image. Never commit or stash automatically.
4. Allowed command only:
   `git push -u origin HEAD` (equivalent: `git push -u origin scripts`).
5. **Forbidden:** `--force` / `--force-with-lease`, push to other remotes or
   branch names, `git merge`, `git rebase`, `git reset`, commit from this mode.
6. On success: report remote tip; remind GHCR publish tags `:scripts` and sha,
   and the cluster Job pull ref
   `harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:<sha>`;
   `STATUS=PUSHED`; `NEXT_ACTION` wait for workflow then
   `/opsx-scripts PLAN_RUN` or `RUN GO` with `image=`.
7. On push failure: `STATUS=BLOCKED`; no retry loop; leave remote as-is.

`/opsx-scripts-prepare` and `/opsx-commit` remain no-push.

### RUN — GO operational execution

`RUN GO` may execute only a resolver-approved `REUSE` or `COMPOSE` result. It
never creates or modifies collector code, Registry, tests, commands, branches,
or Git history. `FORMAL_CHANGE_REQUIRED` stops before image preparation and
persists the handoff artifact.

#### Operational create/extend search gate

Before accepting `RUN GO`, the command contract and the selected execution
branch MUST pass a bounded static search gate. Any operational instruction
that creates, extends, rewrites, auto-commits, or auto-updates a collector,
Registry, test, command, or branch is forbidden and yields `BLOCKED`.
`CREATE`/`EXTEND` are permitted only as `formal_type` values inside the
machine handoff after execution has stopped; they are never operational
outcomes or Job actions.

1. Validate the RUN GO gate and restate one `SCRIPTS_RUN_PLAN`.
2. Resolve the collector before image preparation:
   - with `script=`, validate the named collector against the declared
     request contract;
   - without `script=`, perform bounded inventory and compatibility matching;
   - reuse one compatible collector and set `RESOLUTION_OUTCOME=REUSE`;
   - if none is compatible, persist `FORMAL_CHANGE_REQUIRED` and stop before
     image preparation or Job creation;
   - operational RUN has no collector creation, extension, rewrite, or
     auto-commit path;
   - if the contract is incomplete or matching is ambiguous, return
     `RESOLUTION_OUTCOME=BLOCKED` and do not create a Job.
3. Resolve image readiness (Harbor proxy-cache only for cluster Jobs):
   - default `IMAGE_REF`:
     `harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:<commit-sha>`;
   - GHCR `ghcr.io/revoluxe-ai/adv-bot:<sha>` is CI publication only — **never**
     use it in Job YAML and **never** create a GHCR pull secret;
   - when `image=` is supplied, it must already be a Harbor proxy-cache ref
     (or another cluster-pullable ref Owner explicitly scoped); do not silently
     rewrite `ghcr.io/...` to Harbor or vice versa;
   - otherwise, inspect an already authorized immutable execution SHA; a
     missing image is `BLOCKED`, not a reason to push from RUN;
   - after GHA GHCR publish succeeds, treat Harbor proxy pull-through as ready;
     if Job still hits `ErrImagePull`/`ImagePullBackOff` after the one allowed
     image-race retry, stop with explicit image-readiness failure — no fallback
     to direct GHCR.
4. Monitor the matching GHA run to terminal state (default timeout **20 min**).
   Stay in this invocation; use bounded polling / `gh run watch`, not a
   “wait and invoke me again” response. On success use the immutable Harbor
   proxy ref `harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:<pushed-commit-sha>`
   (not mutable `:scripts`, not `ghcr.io/...`).
5. Render the Job, run client dry-run, and create one uniquely named Job.
6. Monitor Job/pod to terminal state (default timeout **30 min**), collecting
   concise status, events, logs, and container exit code.
7. One controlled recovery is allowed only for the expected image-availability
   race: if this invocation's pod reaches `ErrImagePull` /
   `ImagePullBackOff` while its matching GHA build is still running, finish
   waiting for GHA, delete only this invocation's Job, and create it once more
   with the immutable SHA image. No retry for script/runtime/cluster errors.
8. **Artifact retrieval (general, mandatory when outputs declared):**
   - render Job with `__HOLD_SECONDS__=900` (15 min) unless Owner scoped shorter;
   - default output dir: `.tmp/opsx-scripts/<UTC_TS>/outputs/`;
   - after script success is visible in logs (`ops-script: success; holding`) or
     container still `Running`, start `scripts/ops_script_job_cp.ps1` **in parallel
     with hold** — do not wait for pod `Succeeded`;
   - helper copies each declared file with **retry + exponential backoff**
     (default 36 attempts / up to ~15 min); survives transient `TLS handshake
     timeout` and single cp failures;
   - when primary is declared: pass `-PrimaryFile` and optional
     `-ExpectedPrimarySha256` from logs/report; gate requires local primary +
     matching digest (sidecar or expected);
   - `LOCAL_ARTIFACT_HANDOFF=PASS` **only** when all declared files exist locally
     **and** primary sha256 gate passes;
   - `EXTERNAL_HANDOFF_READY=YES` / `RUN_DONE` for contract runs **only** when
     `LOCAL_ARTIFACT_HANDOFF=PASS`; container exit 0 alone is insufficient;
   - if hold expires and `LOCAL_ARTIFACT_HANDOFF=FAIL` → `FAIL_ARTIFACT_CONTRACT`
     (not `RUN_DONE`), even when in-pod artifacts existed.
   When the plan declares a **primary** contract/handoff artifact (see
   **Artifact contract** below), that primary (+ checksum sidecar if declared)
   is the success criterion — research/side dumps alone never suffice.
9. **Artifact-contract gate** (when primary is declared): if primary file
   missing, required sidecar missing, or `PRIMARY_SHA256` ≠ on-disk digest →
   do **not** emit `RUN_DONE` as handoff success; set
   `STATUS=FAIL_ARTIFACT_CONTRACT` (even if container exit 0 / script-reported
   partial OK). Do not set `battle_tested` from this path.
10. Update ledger only with terminal evidence:
   - true success (gates pass) → `runnable=WORKS`, timestamp, immutable image,
     concise note (include `ARTIFACT_CLASS` when set; do not claim external
     handoff closed from side/research artifacts only);
   - `FAIL_ARTIFACT_CONTRACT` → note primary missing/mismatch; do **not**
     imply handoff ready;
   - script/runtime failure → `runnable=BROKEN`;
   - pre-start image/infra failure → keep `runnable=UNKNOWN`.
11. Emit one terminal `SCRIPTS_REPORT` (including artifact schema fields when
    applicable); do not ask for another GO between the authorized stages.

The command may stop early on incomplete/ambiguous request, resolver
`BLOCKED`/`FORMAL_CHANGE_REQUIRED`, missing immutable image, definitive
GHA/Job failure, authentication or authorization denial, hard-forbid hit,
artifact-contract failure, or bounded timeout. A queued/running workflow is an
expected wait, not a request to bypass the resolver.

Hard forbids identical in spirit to `/opsx-devops` (CSI, port-forward,
secret dump, namespace delete, uncontrolled force-delete, prod DB migration).

### RECORD_BATTLE — Owner attestation

Set `battle_tested=YES` only with `GO` + `script=` (title or path) +
`evidence=` (Job name, report path, or Owner note). Confirm target as
`Title (path)` before writing. No cluster mutate required.

## Authority surfaces

```text
LEDGER:     scripts/REGISTRY.md
PREPARE:    /opsx-scripts-prepare
CLUSTER_GENERIC: /opsx-devops
TEST_AUTHORING_HANDOFF: /opsx-test (optional)
KNOWLEDGE_FORBIDS: .cursor/rules/devops.mdc
```

Decision owner: **Owner** for `PUSH GO`, `RUN GO`, and `RECORD_BATTLE GO`.
This command must not re-decide verify/archive/product GO.

## GO gate (PUSH / RUN / RECORD_BATTLE / registry-repair writes that need GO)

For **PUSH**:

1. Exact token `GO`.
2. Mode is `PUSH`.
3. Current branch is exactly `scripts`.
4. Tracked working tree clean (see PUSH mode).
5. Push command is only the allowlisted non-force `git push -u origin HEAD`.

For **RUN**:

1. Exact token `GO`.
2. Request or exact `script=` selection is valid and resolver returns
   `REUSE` or `COMPOSE`; `FORMAL_CHANGE_REQUIRED` and `BLOCKED` stop safely.
3. Infra preconditions hold and immutable image is already available.
4. No `FORBIDDEN_HIT`.
5. No tracked collector/Registry/test/command/branch/Git-history writes.
6. PowerShell-safe kubectl.

For **RECORD_BATTLE**:

1. Exact `GO` + `script=` + non-empty `evidence=`.

Acknowledgement alone is not GO.

## SCRIPTS_RUN_PLAN (PLAN_RUN / RUN)

```text
SCRIPTS_RUN_PLAN:
SCRIPT_TITLE:
SCRIPT_PATH:
SCRIPT_DISPLAY: Title (path)
REQUEST_CONTRACT:
RESOLUTION_OUTCOME: REUSE | COMPOSE | FORMAL_CHANGE_REQUIRED | BLOCKED
RESOLUTION_PLAN:
IMAGE_REF:
IMAGE_SOURCE: supplied | existing | built_by_run
GHA_RUN:
NS:
JOB_NAME:
TEMPLATE_PATH: k8s/jobs/ops-script-runner.yaml
COMMAND:
ARGS:
KNOWN_OUTPUTS:
HOLD_SECONDS: 900
ARTIFACT_CP_HELPER: scripts/ops_script_job_cp.ps1
DRY_RUN_RESULT:
GHA_TIMEOUT:
JOB_TIMEOUT:
MAX_IMAGE_RACE_RETRIES: 1
ROLLBACK_HINT: delete job/<JOB_NAME> if still present
FORBIDDEN_CHECK: PASS | FAIL
OWNER_GO_LINE:
```

## Artifact contract (declared primary vs side dumps)

When a RUN declares an artifact class and/or a **primary** handoff artifact
(via ARGS, script docs, registry note, or `KNOWN_OUTPUTS`), this command must
not treat container exit 0 alone as handoff success.

* **Primary** = the file(s) named as the required deliverable for that run
  (often a contract/return pack + checksum sidecar).
* **Side / research** artifacts = optional dumps next to primary. They never
  satisfy a declared-primary run by themselves and are not uploaded as the
  handoff pack.
* Product CLI must enforce its own accept/preflight gates; this command must
  not re-label a side dump as an accepted primary.
* If the product packager/flags required by the plan are missing → report the
  gap; do not invent a primary from a research dump.

### SCRIPTS_REPORT artifact schema (mandatory when applicable)

When the run declares `ARTIFACT_CLASS`, `--contract` / `--artifact-class`
(or equivalent), or a named primary in `KNOWN_OUTPUTS`, the durable
`SCRIPTS_REPORT.md` and terminal report **MUST** include:

```text
CALLER_BRANCH=<refs/heads/...|HEAD>
CALLER_WORKTREE=<absolute path>
CALLER_SHA=<40-hex|NONE>
EXECUTION_SHA=<40-hex|NONE>
REGISTRY_SHA=<40-hex Git commit SHA|NONE>
REGISTRY_SHA256=<64-hex content digest|NONE>
RESOLUTION_OUTCOME=REUSE|COMPOSE|FORMAL_CHANGE_REQUIRED|BLOCKED
RESOLUTION_PLAN=<JSON>
COMPOSE_MANIFEST_SHA256=<hex|NONE>
ARTIFACT_CLASS=<script-declared class or NONE>
PRIMARY_ARTIFACT=<filename|NONE>
PRIMARY_SHA256=<hex|NONE>
SIDE_ARTIFACT=<filename|NONE>
EXTERNAL_HANDOFF_READY=YES|NO
PREFLIGHT_ACCEPT_INPUT=YES|NO|N_A
CONTRACT_ID=<id|NONE>
LOCAL_ARTIFACT_HANDOFF=PASS|FAIL|N_A
LOCAL_PRIMARY_PATH=<abs path|NONE>
LOCAL_REPORT_PATH=<abs path|NONE>
```

Rules:

1. `EXTERNAL_HANDOFF_READY=YES` **only** if `LOCAL_ARTIFACT_HANDOFF=PASS` —
   primary exists locally after retry cp **and** `PRIMARY_SHA256` matches that
   file’s digest (when a sha is required).
2. If primary was declared and only side/research output exists →
   `EXTERNAL_HANDOFF_READY=NO` and `STATUS=FAIL_ARTIFACT_CONTRACT`.
3. Do not claim handoff/ready-for-consumer YES without (1).

## Return contract (mandatory)

```text
STATUS: INVENTORY_DONE | STATUS_DONE | TEST_DONE | PUSHED | RUN_PLAN_READY | RUN_DONE |
        RUN_DONE_WITH_OUTPUT_GAP | FAIL_ARTIFACT_CONTRACT | LEDGER_UPDATED | BLOCKED |
        REDIRECT_PREPARE | REDIRECT_DEVOPS | REDIRECT_TEST
MODE: INVENTORY | STATUS | TEST_LOCAL | PUSH | PLAN_RUN | RUN | RECORD_BATTLE
SCRIPTS_INFRA: READY | GAP | UNKNOWN
FORBIDDEN_HIT: NONE | <id>

WHAT_HAPPENED:
WHY:
CURRENT_STATE:
RESOLUTION_OUTCOME: REUSE | COMPOSE | FORMAL_CHANGE_REQUIRED | BLOCKED
RESOLUTION_PLAN:
OWNER_DECISION_REQUIRED: yes | no
NEXT_ACTION:
DO_NOT_DO_YET:
```

When a script is named in any of the human fields above, use `Title (path)`.
Pasteable `NEXT_ACTION` may use `script=<Title>` if unique.

Optional durable receipt: `.tmp/opsx-scripts/<UTC_TS>/SCRIPTS_REPORT.md`

RUN report additionally includes:

```text
GHA_RUN:
GHA_RESULT:
JOB:
JOB_RESULT:
CONTAINER_EXIT_CODE:
ATTEMPTS:
LOG_SUMMARY:
OUTPUTS:
LEDGER_RESULT:
ARTIFACT_CLASS:
PRIMARY_ARTIFACT:
PRIMARY_SHA256:
SIDE_ARTIFACT:
EXTERNAL_HANDOFF_READY:
PREFLIGHT_ACCEPT_INPUT:
CONTRACT_ID:
LOCAL_ARTIFACT_HANDOFF:
LOCAL_PRIMARY_PATH:
LOCAL_REPORT_PATH:
```

When process-surface command files change (rare here): commit via
`/opsx-admin-command-commit`. Registry source and collector changes are
committed only through their owning OpenSpec/apply or admin command;
operational RUN never commits them.

## Failure / recovery

* Local test fail → ledger `runnable=BROKEN` or keep `UNKNOWN` with notes;
  `NEXT_ACTION` fix or stop.
* Image missing before RUN → `BLOCKED`; do not push or rewrite branches from RUN.
* ImagePullBackOff during matching build → one controlled immutable-image retry.
* GHA queued/running → keep monitoring; do not return a human wait step.
* GHA terminal failure / timeout → `BLOCKED` with run URL and concise failure.
* Job fail → `BLOCKED`; leave Job for inspect; suggest
  `/opsx-devops INVESTIGATE` if cluster-generic.
* Script succeeds but known output copy fails → `RUN_DONE_WITH_OUTPUT_GAP`;
  preserve success evidence and state the exact retrieval gap.
* Declared primary missing or sha mismatch after exit 0 →
  `FAIL_ARTIFACT_CONTRACT`; do not treat as external handoff success; do not
  promote side/research dumps as primary.
* Push auth failure or unrelated dirty tree → `BLOCKED`;
  no force.
* Same mutate error ≥ 3 → stop; escalate Owner.

## Pipeline position

```text
ENTRY_STATE: SCRIPTS_INFRA_READY + owner intent
PREVIOUS: /opsx-scripts-prepare | prior /opsx-scripts | consult
COMMAND_ACTION: inventory | test | push | autonomous run-to-result | record battle
EXIT_STATE: PUSHED | RUN_DONE | RUN_DONE_WITH_OUTPUT_GAP | FAIL_ARTIFACT_CONTRACT |
            REPORT_READY | LEDGER_UPDATED | BLOCKED | REDIRECT_*
NEXT: Owner | next /opsx-scripts … | /opsx-devops | stop
FAILURE: no bypass of prepare infra or devops forbids; no force-push;
         no side-dump-as-primary handoff success
```

## Self-check before finish

- [ ] Infra gap → REDIRECT_PREPARE (not improvised workflow invent in daily mode)
- [ ] RUN / PUSH without GO → BLOCKED
- [ ] PUSH only on branch `scripts`; never `--force`
- [ ] PUSH does not commit
- [ ] RUN GO never writes collector/Registry/test/command code or Git history
- [ ] RUN GO consumes only resolver REUSE/COMPOSE and immutable execution evidence
- [ ] Matching GHA queued/running is monitored, not returned as a blocker
- [ ] Only one image-readiness retry; no generic Job retry
- [ ] Known outputs copied and reported after success
- [ ] When primary declared: artifact schema fields present; primary gate applied
- [ ] Side/research dumps not treated as external handoff success
- [ ] battle_tested not set from RUN alone
- [ ] Working scripts not rewritten by default
- [ ] master/stage deploy workflows not touched
- [ ] Human lists/status use `Title (path)` (path not sole primary label)
- [ ] Missing/ambiguous title resolution → BLOCKED with candidate list
- [ ] NEXT_ACTION + DO_NOT_DO_YET present
