## Context

Discovery OPSX-SCRIPTS-ARCH-DISCOVERY-001 зафиксировал branch-bound resolution,
неполный ledger и дублирующие strict/cabinet401/multi-client entrypoints.
R1 уточняет границу: operational RUN GO только исполняет уже разрешённые
collectors; создание или изменение кода всегда выводится в formal change.

Stakeholders: Owner (RUN GO), scripts lane operators и OpenSpec change owners.
WB collectors продолжают использовать accepted
`openspec/decisions/scripts-wb-api-ops-stack/decision.md`.

## Goals / Non-Goals

**Goals**

- Обязательный machine resolver `tools/scripts/resolver.py`, вызываемый из
  `/opsx-scripts PLAN_RUN/RUN`.
- Machine registry SoT в `scripts/REGISTRY.yaml` и generated
  `scripts/REGISTRY.md`.
- Canonical worktree discovery через porcelain topology и exact
  `refs/heads/scripts`.
- Runtime outcomes только REUSE, COMPOSE, FORMAL_CHANGE_REQUIRED, BLOCKED.
- Deterministic COMPOSE child execution, per-child artifact gates и composite
  `COMPOSE_MANIFEST.json`.
- Additive caller/execution provenance и минимальная R1 reference migration.

**Non-Goals**

- Operational code/registry/test/command writes.
- Массовая регистрация legacy entrypoints.
- Product `app/**` behavior, master/stage workflows, client reporting.
- Новый collector service/repository.

## Architecture Decision References

- `openspec/decisions/scripts-wb-api-ops-stack/decision.md` — WB read path,
  Job-only execution, READ_ONLY_NO_MUTATION и secret-strip.
- `openspec/changes/scripts-collector-lifecycle-architecture/decisions/scripts-collector-lifecycle-ownership/decision.md`
  — proposed ownership for resolver, registry, canonical lane and formal-change boundary.

**Checklist**

- [x] context-first decision lookup performed
- [x] relevant decisions cited
- [x] new decision proposed for resolver/registry placement
- [x] implementation layer matches decision (resolver/tooling/commands, not `app/**`)

## Ownership & Placement

| Concern | Owner layer |
|--------|-------------|
| Resolver algorithm and runtime outcomes | mandatory `tools/scripts/resolver.py`, called by `/opsx-scripts` |
| Canonical bootstrap | `/opsx-scripts` command surface, read-only candidate selection only |
| Machine registry | `scripts/REGISTRY.yaml` |
| Human registry view | generated `scripts/REGISTRY.md` |
| Canonical worktree discovery | resolver using `git worktree list --porcelain` |
| Collector execution | existing `/opsx-scripts` Job/image path |
| Composite orchestration | `/opsx-scripts` runtime using resolver child plan |
| Shared WB seam | existing `scripts/wb_api_readonly_ops/` and accepted app API stack |
| Formal change ownership | `/opsx-ff` or `/opsx-update` followed by `/opsx-apply` |

## Resolver design

`tools/scripts/resolver.py` receives a request contract containing sources,
capabilities, fields, output schema, identity arguments and zero-write rules.
It must return a structured result with `outcome`, `execution_sha`,
`registry_sha` (the 40-hex Git commit containing the Registry snapshot),
selected rows/children and, when necessary, a complete formal change request.
Credential-like request names and values are rejected before they can enter
stdout, stderr, JSON, or a pasteable handoff.

## Thin canonical bootstrap

Before invoking any resolver, the installed `/opsx-scripts` command performs a
thin, read-only bootstrap in the caller worktree. The bootstrap:

1. records the caller root/worktree, branch, and HEAD SHA;
2. resolves the canonical candidate with precedence
   `--canonical-root` → `SCRIPTS_CANONICAL_ROOT` → `git worktree list --porcelain`;
3. selects a candidate whose branch is exactly `refs/heads/scripts`;
4. invokes the resolver only from that candidate using its absolute path;
5. passes the required absolute `--caller-root` to the resolver.

The bootstrap MUST NOT read `scripts/REGISTRY.yaml` as a source of truth,
perform matching, select a collector, execute a Job, or interpret a resolver
outcome. If it cannot identify a candidate, it returns `BLOCKED` fail-closed
without attempting a caller-local resolver. A candidate selected by an
explicit CLI or environment root is not replaced by a lower-precedence source
when the explicit candidate is invalid.

The resolver independently repeats caller/canonical branch, common-directory,
tracked-clean, and fixed-HEAD checks. Bootstrap observations are not trusted
as resolver evidence.

The updated `/opsx-scripts` command itself MUST be installed in the active
command surface. Bootstrap does not update old Git branches or disguise command
rollout as canonical runtime synchronization.

### Canonical resolver invocation and CLI contract

The `/opsx-scripts` command invokes the resolver from the canonical worktree,
never from a caller-local or stale copy. The executable, working directory,
Poetry environment, and request path are fixed as follows:

```text
executable: <canonical-root>/tools/scripts/resolver.py
working directory: <canonical-root>
poetry/environment: canonical worktree
request file: <absolute-request-path>
```

The resulting process is equivalent to:

```text
poetry run python <canonical-root>/tools/scripts/resolver.py \
  PLAN_RUN|RUN \
  --request-file <absolute-request-path> \
  --caller-root <absolute-caller-root> \
  --canonical-root <absolute-canonical-root>
```

The resolver CLI has exactly two subcommands, `PLAN_RUN` and `RUN`.
`--caller-root <absolute-path>` is mandatory. `--request-file` is a UTF-8 JSON
file with an absolute path; inline JSON and stdin are not accepted.
`--canonical-root <absolute-path>` is optional for direct resolver use, but is
mandatory in the `/opsx-scripts` bootstrap invocation. When omitted outside
that invocation, the resolver applies the already-defined canonical-root
precedence itself.

The resolver executes with the canonical worktree as its working directory and
must never import or execute a resolver from the caller worktree.

The request MUST have this exact top-level shape:

```json
{
  "schema_version": "scripts-resolver-request.v1",
  "mode": "PLAN_RUN",
  "request_id": "req-20260918-0001",
  "run_id": "20260918-0001",
  "change_name_hint": "scripts-new-capability",
  "capabilities": ["campaign-state"],
  "sources": ["WB_API", "POSTGRES"],
  "required_fields": ["campaign_id", "status"],
  "output_schema_version": "1",
  "primary_artifact_pattern": "*.zip",
  "required_args": {"shop_id": "value"},
  "optional_args": {},
  "zero_write_required": true,
  "explicit_script": null,
  "owning_change_id": null
}
```

Required fields are `schema_version`, `mode`, `request_id`, `run_id`,
`change_name_hint`, `capabilities`, `sources`, `required_fields`,
`output_schema_version`, `primary_artifact_pattern`, `required_args`,
`optional_args`, and `zero_write_required`. `explicit_script` and
`owning_change_id` are nullable strings. `mode` MUST match the CLI subcommand;
`zero_write_required` MUST be `true`; all arrays contain unique non-empty
strings; argument maps contain JSON scalar values; and `change_name_hint` is
kebab-case. The request MUST NOT contain secrets or tokens.

The resolver writes no files, runs no Job, performs no Git write, and emits
exactly one JSON object to stdout. Human diagnostics go to stderr. The result
uses `schema_version: "scripts-resolver-result.v1"` and contains:

```json
{
  "schema_version": "scripts-resolver-result.v1",
  "mode": "PLAN_RUN",
  "request_id": "req-20260918-0001",
  "run_id": "20260918-0001",
  "caller": {
    "root": "C:/repo/feature",
    "branch": "refs/heads/feature",
    "sha": "40-hex-sha",
    "common_dir": "C:/repo/.git"
  },
  "outcome": "REUSE",
  "execution_sha": "40-hex-sha",
  "registry_sha": "40-hex-sha",
  "canonical_worktree": {
    "path": "C:/repo/scripts",
    "branch": "refs/heads/scripts",
    "common_dir": "C:/repo/.git"
  },
  "selection": [
    {
      "registry_id": "campaign-state",
      "collector_path": "scripts/collector.py"
    }
  ],
  "selection_mode": "AUTOMATIC",
  "compose_plan": null,
  "formal_change": null,
  "error": null,
  "operational_write_path": false
}
```

The resolver computes `caller` provenance from `--caller-root`, not from the
resolver's working directory. It MUST verify that caller and canonical roots
belong to the same normalized Git common directory.

`outcome` MUST be exactly `REUSE`, `COMPOSE`, `FORMAL_CHANGE_REQUIRED`, or
`BLOCKED`. `selection` contains one validated row for REUSE. `compose_plan`
contains the ordered child plan for COMPOSE. `formal_change` is present only
for FORMAL_CHANGE_REQUIRED. `selection_mode` is `AUTOMATIC|EXPLICIT|NONE`;
explicit selection returns `REUSE` with `selection_mode=EXPLICIT`. `error` is
present for BLOCKED or malformed input.

Exit codes are fixed: `0` for REUSE/COMPOSE, `10` for
FORMAL_CHANGE_REQUIRED, `20` for a valid request that is BLOCKED, `2` for
malformed CLI/request/JSON/schema, and `30` for an unexpected resolver error.
Codes `2` and `30` still emit a result with `outcome: "BLOCKED"` and a
machine-readable `error.code`; no write is attempted.

For malformed JSON where `request_id` and `run_id` cannot be extracted, the
BLOCKED result uses `request_id: null` and `run_id: null`; `mode` is also null
when the CLI mode cannot be determined. Exit code remains `2`.

The `compose_plan` object is passed from resolver stdout to `/opsx-scripts`
without reinterpretation:

```json
{
  "schema_version": "scripts-compose-plan.v1",
  "children": [
    {
      "order": 1,
      "registry_id": "campaign-state",
      "collector_path": "scripts/collector.py",
      "args": {"shop_id": "value"},
      "outputs": ["result.zip"],
      "required": true
    }
  ]
}
```

```text
request
  → resolver.load_registry_yaml()
  → resolver.discover_canonical_worktree()
  → REUSE
  → COMPOSE
  → FORMAL_CHANGE_REQUIRED (formal_type=EXTEND|CREATE)
  → BLOCKED
```

`EXISTING` remains a presentation alias for `REUSE`; `CREATED` is never emitted.
If capability is missing, the formal request must be pasteable and choose
`/opsx-ff` for a new capability or `/opsx-update` for an existing capability
change. No collector file is written by resolver or RUN GO.

Matching separates data capability/source from presentation identity.
`request.required_fields ⊆ entry.provided_fields` is mandatory for REUSE.
For COMPOSE, the union of `provided_fields` from the ordered children MUST
cover `request.required_fields`; sources, capabilities, and output contracts
must also be mutually compatible. Consumer and report labels alone do not
force a new collector.

Automatic matching considers only rows with `resolution_enabled: true`.
Explicit selection still invokes the resolver but considers only the exact
requested row with `explicit_invocation_enabled: true`; it returns
`REUSE` with `selection_mode=EXPLICIT` and never promotes that row into
automatic matching.

## Canonical worktree resolution

Resolution precedence is fixed:

1. CLI `--canonical-root`;
2. explicitly set `SCRIPTS_CANONICAL_ROOT`;
3. topology discovery from `git worktree list --porcelain`;
4. otherwise `BLOCKED`.

The first available source wins. If a CLI or explicitly set environment root
is present but fails validation, the resolver returns `BLOCKED` and does not
fall through to a lower-precedence source.

Every selected root, including an explicit override, MUST pass all checks:

1. The worktree branch is exactly `refs/heads/scripts`.
2. Its normalized Git common directory equals the caller's common directory.
3. `git -C <root> status --porcelain=v1 --untracked-files=no` is empty.
4. `git -C <root> rev-parse HEAD` supplies the immutable execution SHA.
5. Registry and execution contract are read from that fixed HEAD using
   `git show <execution_sha>:scripts/REGISTRY.yaml` and the corresponding
   collector/template paths, never from dirty working-tree contents.

Any tracked staged or unstaged change in the canonical worktree returns
`BLOCKED`. Untracked files do not affect the clean tracked-state check, but
they are not read as registry or execution inputs.

The caller branch/worktree remains read-only for PLAN_RUN/RUN.

## Verification lifecycle

The apply-stage integration test MUST use a temporary Git fixture containing
one feature worktree and one exact `refs/heads/scripts` worktree in the same
common directory. It MUST cover clean canonical HEAD, tracked dirty
canonical state, wrong branch, and different common directory.

The real canonical worktree is not considered live or updated before
merge/deploy authorization. A post-merge smoke test may run a real PLAN_RUN
from a non-`scripts` worktree only after a separate merge/deploy authorization.
The implementation handoff ends at `READY_FOR_MERGE_REVIEW`; it does not claim
that the production or canonical runtime has already been updated.

## Registry v2 (minimal machine contract)

`scripts/REGISTRY.yaml` is the only machine source. Each resolution-enabled row
contains:

The exact YAML document shape is:

```yaml
schema: scripts-registry
version: 2
generated:
  markdown: scripts/REGISTRY.md
  ordering: id
entries:
  - id: campaign-state
    title: Campaign state
    path: scripts/collector.py
    resolution_enabled: true
    explicit_invocation_enabled: true
    capabilities: [campaign-state]
    sources: [WB_API]
    provided_fields: [campaign_id, status]
    required_args:
      shop_id:
        type: string
        description: Shop identity
        secret: false
    optional_args: {}
    output_schema_version: "1"
    primary_artifact_pattern: "*.zip"
    tenant_scope: PARAMETERIZED
    hardcoded_context:
      identifiers: []
      justification: ""
    composable: false
    compose_with: []
    side_effects: [READ_ONLY, LOCAL_ARTIFACT_WRITE]
    deprecated_by: null
    readiness:
      runnable: UNKNOWN
      tests: NONE
      battle_tested: NO
      last_local_at: "-"
      last_cluster_at: "-"
      last_image_ref: "-"
      notes: ""
```

Top-level keys are exactly `schema`, `version`, `generated`, and `entries`.
`schema` is exactly `scripts-registry`; `version` is integer `2`;
`generated` has exactly `markdown` and `ordering`;
`generated.markdown` is exactly `scripts/REGISTRY.md`; `generated.ordering` is
exactly `id`; `entries` is a non-empty list.

Every entry requires `id`, `title`, `path`, `resolution_enabled`,
`explicit_invocation_enabled`, and
`readiness`. `readiness` has exactly `runnable`, `tests`, `battle_tested`,
`last_local_at`, `last_cluster_at`, `last_image_ref`, and `notes`. `id` is unique kebab-case; `path` is a repository-relative
POSIX path; readiness enums are `UNKNOWN|WORKS|BROKEN`,
`NONE|PARTIAL|COVERED`, and `NO|YES`; timestamp/image fields are ISO UTC,
immutable image references, or `-`.

When `resolution_enabled: true`, all automatic-resolution fields shown above
are mandatory. `capabilities`, `sources`, and `provided_fields` are non-null
lists of unique non-empty strings. `required_args` and `optional_args` are
non-null maps; argument specs require `type`, `description`, and `secret`,
with `type` in `string|integer|number|boolean|date|path|enum`.
`output_schema_version` and `primary_artifact_pattern` are non-empty strings.
`tenant_scope` is exactly `GENERIC|PARAMETERIZED|SPECIAL_PURPOSE`.
`hardcoded_context` has exactly `identifiers` (list of path/line strings) and
`justification` (string). `composable: false` requires `compose_with: []`;
`composable: true` requires a non-empty list of existing entry IDs.
`side_effects` is a non-empty list from
`READ_ONLY|LOCAL_ARTIFACT_WRITE|EXTERNAL_READ`, and resolution-enabled rows
MUST include `READ_ONLY`.
`deprecated_by` is null or an existing entry ID.
The allowed enabled-row keys are exactly the identity, automatic-resolution,
invocation, and readiness fields listed above.

When `resolution_enabled: false`, the row cannot participate in automatic
REUSE/COMPOSE. When `explicit_invocation_enabled: true`, it MUST contain
`provided_fields`, `required_args`, `optional_args`,
`output_schema_version`, `primary_artifact_pattern`, `tenant_scope`,
`hardcoded_context`, `side_effects`, and `deprecated_by`; it MAY be selected
only by exact `explicit_script` after invocation-safety validation.
When both flags are false, the row is ledger-only and requires no invocation
metadata. Its hardcoding does not block R1. R1 does not backfill all legacy
rows.

The allowed disabled explicit-row keys are exactly the identity flags,
`provided_fields`, invocation-safety fields, `deprecated_by`, and `readiness`.
The allowed ledger-only keys are exactly `id`, `title`, `path`,
`resolution_enabled`, `explicit_invocation_enabled`, `deprecated_by`, and
`readiness`.
Unknown keys, missing required keys, invalid enum values, duplicate IDs,
duplicate paths, invalid references, and automatic-resolution fields on a
disabled row are validation errors unless that row has
`explicit_invocation_enabled: true` and the field is part of its invocation
safety metadata.

Deterministic ordering is mandatory: entries sort by `id` ascending; mapping
keys sort lexicographically; scalar lists sort lexicographically except
`compose_with`, which follows the declared dependency order; generated Markdown
uses the same entry order and fixed column order. `provided_fields` is sorted
lexicographically.

Registry commands run from the canonical scripts worktree:

```text
poetry run python tools/scripts/registry.py validate --input scripts/REGISTRY.yaml
poetry run python tools/scripts/registry.py render --input scripts/REGISTRY.yaml --output scripts/REGISTRY.md
poetry run python tools/scripts/registry.py check-drift --input scripts/REGISTRY.yaml --generated scripts/REGISTRY.md
```

`validate` exits `0` on success and `2` on schema/content errors. `render`
exits `0` and is the only command allowed to write generated Markdown.
`check-drift` exits `0` when the projection is byte-identical and `3` on
drift. All commands emit one JSON result to stdout and diagnostics to stderr.
These maintenance commands are not operational `/opsx-scripts` write paths.

## COMPOSE runtime

The resolver emits an ordered acyclic child plan. For every composable row,
`compose_with` declares its predecessors. Self-reference, duplicate,
unknown-dependency, and cyclic graphs are invalid and return `BLOCKED`.
Otherwise the resolver uses deterministic topological ordering, breaking ties
by registry ID. PLAN_RUN displays each child collector, exact args and declared
outputs. RUN creates and executes child Jobs sequentially. Every child
independently requires primary artifact presence and checksum validation.

The parent creates and updates `COMPOSE_MANIFEST.json` after a valid COMPOSE
resolution and before the first child Job. The exact document shape is:

```json
{
  "schema_version": "opsx.compose-manifest.v1",
  "run_id": "20260918-0001",
  "outcome": "COMPOSE",
  "status": "RUNNING",
  "execution_sha": "40-hex-sha",
  "registry_sha": "40-hex-sha",
  "children": [
    {
      "order": 1,
      "registry_id": "campaign-state",
      "required": true,
      "collector_path": "scripts/collector.py",
      "job_name": null,
      "args": {"shop_id": "value"},
      "execution_sha": "40-hex-sha",
      "artifact_path": null,
      "sha256": null,
      "gate_status": "PENDING",
      "status": "PENDING",
      "failure": null
    }
  ],
  "failure_details": [],
  "primary_artifact": {
    "path": "COMPOSE_MANIFEST.json",
    "accepted": false
  },
  "checksum_sidecar_path": "COMPOSE_MANIFEST.json.sha256",
  "external_handoff_ready": false
}
```

`status` is `RUNNING|SUCCEEDED|PARTIAL_FAILURE|FAILED`; `outcome` is always
`COMPOSE`; `children` preserve resolver order. Child `required` is boolean,
`gate_status` is `PENDING|PASS|FAIL|SKIPPED`, and child `status` is
`PENDING|SUCCEEDED|FAILED|SKIPPED`. Failure objects contain exactly
`code`, `message`, and `retryable`; `failure_details` is an ordered list of
the same objects with `child_order`. While the manifest is `RUNNING`, child
`job_name`, `artifact_path`, `sha256`, and `failure` MAY be null. Once a child
is terminal, these fields MUST be non-null: successful/failed children use
actual job and artifact values (or `NOT_AVAILABLE` when a failed gate produced
no artifact); skipped children use `NOT_CREATED`, `NOT_AVAILABLE`,
`NOT_APPLICABLE`, and a non-null skip failure object.

The manifest is created before execution once the plan, run ID, registry SHA,
and execution SHA are validated. It is updated after every child gate and is
also finalized on failure. A required-child failure stops the remaining
required sequence and marks unstarted children `SKIPPED`; an optional-child
failure is recorded, execution continues, and the parent ends
`PARTIAL_FAILURE`. Any child failure makes `accepted: false` and
`external_handoff_ready: false`. Only when every required child and every
declared artifact/checksum gate passes, with no child failure, may the parent
end `SUCCEEDED`, set `accepted: true`, and set
`external_handoff_ready: true`. After the manifest is finalized, its SHA-256
is computed and written to `COMPOSE_MANIFEST.json.sha256`; the sidecar and
manifest pass the ordinary artifact gate. The manifest does not contain its
own SHA-256. The final manifest SHA is also written to SCRIPTS_REPORT.
No semantic merge of child data is performed.

### Controlled correction boundaries

Canonical topology resolution is fail-closed: topology candidates are
validated independently, and only zero or one valid exact
`refs/heads/scripts` candidate is accepted. Multiple valid candidates are
ambiguity evidence, not a reason to choose listing order.

`tools/scripts/compose_runtime.py` owns the child artifact gate. A successful
child result is provisional until runtime validates a relative artifact path
inside the invocation artifact root, rejects symlink/traversal escapes,
confirms the file exists, computes SHA-256 from its bytes, and compares the
reported digest. The manifest stores the runtime-verified digest; missing or
mismatched artifacts are failed child gates and never become an accepted
handoff.

The command surface contract has executable evidence for both `PLAN_RUN` and
`RUN`: each mode routes through the canonical bootstrap and then the absolute
canonical resolver. `REGISTRY_SHA` remains the Git commit containing the
fixed Registry snapshot; optional `REGISTRY_SHA256` is not required by this
correction.

## R1 reference migration

| Entrypoint | R1 action |
|-----------|-----------|
| `a1_strict_read_only_contract_collect.py` | resolution-enabled parameterized row with `provided_fields` |
| `a1_cabinet401_run_go_contract_collect.py` | `resolution_enabled=false`, `explicit_invocation_enabled=true`, deprecated compatibility entrypoint |
| `a1_cabinet401_run_go_contract_collect_v2.py` | `resolution_enabled=false`, `explicit_invocation_enabled=true`, deprecated compatibility entrypoint |
| `multi_client_ad_preflight_collect.py` | resolution-enabled parameterized reference; normalize artifact naming and `provided_fields` |

Deprecated cabinet401 entrypoints remain runnable when selected by explicit
`script=`. No other collector family is migrated in R1.

## Provenance / concurrency

SCRIPTS_REPORT adds fields without removing existing ones:

- `CALLER_BRANCH`, `CALLER_WORKTREE`, `CALLER_SHA`;
- `EXECUTION_SHA`, `REGISTRY_SHA`;
- `REGISTRY_SHA` is the lowercase 40-hex Git commit SHA containing the
  Registry snapshot resolved at or before `EXECUTION_SHA`;
- an optional content digest is named `REGISTRY_SHA256` and never substitutes
  for `REGISTRY_SHA`;
- `RESOLUTION_OUTCOME`, `RESOLUTION_PLAN`;
- for composite runs, `COMPOSE_MANIFEST.json`,
  `COMPOSE_MANIFEST_SHA256`, and child gate results.

Job names and local output directories remain run-id scoped. Child artifacts
must be distinct; the parent manifest records their exact paths and digests.
`run_id` accepts only `^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$`. Runtime output and
receipt paths are derived under the invocation-owned
`.tmp/opsx-scripts/<run_id>/` root. Absolute paths, separators, traversal,
symlink/reparse escapes, and existing output-directory collisions are blocked;
no existing caller directory is removed.

## Formal-change handoff

For `FORMAL_CHANGE_REQUIRED`, `/opsx-scripts` MUST persist the resolver result
as `.tmp/opsx-scripts/<run_id>/FORMAL_CHANGE_REQUIRED.json`. The resolver
itself remains stdout-only; this file is an evidence artifact, not a code or
registry write. Its exact shape is:

```json
{
  "schema_version": "opsx.formal-change-handoff.v1",
  "outcome": "FORMAL_CHANGE_REQUIRED",
  "run_id": "20260918-0001",
  "request_id": "req-20260918-0001",
  "formal_type": "EXTEND",
  "command": "/opsx-update",
  "change_name": "scripts-existing-capability",
  "owner_change_id": "scripts-existing-capability",
  "reason": "Existing capability requires a shared semantic extension",
  "evidence": [
    {
      "path": "scripts/collector.py",
      "line": 42,
      "detail": "required field is not covered"
    }
  ],
  "request_contract": {},
  "constraints": [
    "No operational collector write",
    "Preserve READ_ONLY_NO_MUTATION",
    "Preserve immutable artifact and checksum gates"
  ],
  "pasteable_prompt": "/opsx-update scripts-existing-capability ...",
  "created_at": "2026-09-18T12:00:00Z"
}
```

The object requires `schema_version`, `outcome`, `run_id`, `request_id`,
`formal_type`, `command`, `change_name`, `owner_change_id`, `reason`,
`evidence`, `request_contract`, `constraints`, `pasteable_prompt`, and
`created_at`. `formal_type` is `EXTEND|CREATE`; `command` is
`/opsx-ff|/opsx-update`.

Selection is deterministic: `CREATE` always selects `/opsx-ff`; `EXTEND`
selects `/opsx-update <owner_change_id>` only when the supplied non-null
`owner_change_id` exists under `openspec/changes/`, otherwise it selects
`/opsx-ff <change_name>`. The pasteable prompt includes the workspace,
sanitized request contract, evidence paths/lines, formal type, safety
constraints, and an explicit prohibition on apply until separately authorized
GO; it does not contain an executable `/opsx-apply` command.

## Durable verification receipt

The correction handoff is durable at
`verification/READY_FOR_REVERIFY.json` inside this change. Its minimum
schema is `opsx.change-verification.v1` and records the change id, branch,
HEAD, task evidence, targeted test/Registry checks, OpenSpec validation,
`git diff --check`, and explicit `NONE` values for production writes and
commit/push/merge activity. `generated_at` is ISO-8601 UTC. The receipt is
evidence only; it does not authorize `/opsx-apply`, production execution, or
any Git mutation.

## Hardcoding gate

Static verification scans only new/changed collectors whose YAML row has
`resolution_enabled: true`. Undeclared fixed client/project/branch identity
fails with `path:line` evidence. Legacy `resolution_enabled: false` rows do
not block R1. The sole special tenant token is
`tenant_scope=SPECIAL_PURPOSE`.

## Risks / mitigations

- False REUSE/COMPOSE: resolver fixtures and explicit schema matching.
- Missing canonical worktree: fail-closed BLOCKED, never implicit path fallback.
- Partial COMPOSE: retain child artifacts, reject composite handoff.
- Registry drift: YAML validation and generated Markdown check.

## R1 contract closure

The resolver CLI, Registry v2 YAML schema and maintenance commands,
COMPOSE_MANIFEST schema/lifecycle, formal-change handoff artifact, and explicit
`script=` compatibility path above are normative R1 contracts. They are not
implementation choices left to the apply agent.
