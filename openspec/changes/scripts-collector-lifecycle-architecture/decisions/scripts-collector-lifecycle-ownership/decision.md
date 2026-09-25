# Decision: Scripts collector lifecycle ownership

## Status

Proposed

## Context

Collectors и `/opsx-scripts` разделяют execution (Job + image SHA), registry
matching и VCS lifecycle, но accepted decision `scripts-wb-api-ops-stack` покрывает
только WB API access plane, не resolution, registry SoT и branch topology.
Без reusable правила агенты создают project-bound дубликаты и скрыто расширяют
collectors в RUN GO.

## Decision

1. **Operational boundary:** `/opsx-scripts RUN GO` MUST NOT create or modify
   collector code, registry source, tests, commands, or Git history. Its only
   outcomes are `REUSE`, `COMPOSE`, `FORMAL_CHANGE_REQUIRED`, and `BLOCKED`.
2. **Formal change types:** `EXTEND` and `CREATE` are formal-change types only.
   Missing capability MUST return `FORMAL_CHANGE_REQUIRED` with a complete
   pasteable `/opsx-ff` or `/opsx-update` request. The old `CREATED` outcome is
   not produced.
3. **Machine resolver ownership:** `tools/scripts/resolver.py` is mandatory.
   `/opsx-scripts PLAN_RUN/RUN` MUST invoke it; command-only reasoning or an
   optional helper is forbidden. The resolver is not placed in `app/**`.
4. **Machine registry SoT:** `scripts/REGISTRY.yaml` is the only machine
   registry source. `scripts/REGISTRY.md` is generated human-readable output
   and MUST NOT be edited as an independent source. Legacy rows MAY use
   `resolution_enabled: false`; R1 does not backfill all legacy entrypoints.
5. **Canonical worktree:** resolver MUST parse `git worktree list --porcelain`,
   select exact branch `refs/heads/scripts`, and verify that the selected
   worktree belongs to the same Git common directory. `SCRIPTS_CANONICAL_ROOT`
   is an explicit override only; precedence is CLI flag, environment variable,
   then topology, and an invalid explicit candidate returns `BLOCKED` without
   fallback. No relative default is allowed.
6. **COMPOSE execution:** resolver emits an ordered acyclic child plan.
   PLAN_RUN displays every child collector, args, and outputs. RUN executes
   required child Jobs sequentially; each child has its own artifact/checksum
   gate. The composite primary is `COMPOSE_MANIFEST.json`, containing child
   Job, execution SHA, artifact path, and SHA-256. No hidden semantic merge is
   allowed. Any required child failure means composite failure; partial
   artifacts remain available but handoff is not ready.
7. **Compatibility:** matching MUST distinguish data capabilities/sources from
   presentation identity. `REUSE` is selected when capabilities and schema are
   compatible even if consumer/report identity differs. The previous
   `EXISTING` label is an output alias for `REUSE`.
8. **R1 migration boundary:** only the strict collector, cabinet401 v1,
   cabinet401 v2, and multi-client preflight collector are reference migration
   candidates. Explicit `script=` keeps deprecated cabinet401 entrypoints
   available.
9. **Hardcoding gate:** verification applies only to new/changed collectors
   with `resolution_enabled: true`. Legacy `resolution_enabled: false` rows
   do not block R1. The only special scope token is
   `tenant_scope=SPECIAL_PURPOSE`.
10. **Provenance and compatibility:** new provenance fields are additive;
    existing consumers MUST continue to parse reports. Caller branch/worktree
    and execution/registry SHA MUST be recorded separately.
11. **CLI contract:** resolver modes are exactly `PLAN_RUN` and `RUN`, both
    accepting `--request-file <path>` and optional explicit
    `--canonical-root <path>`. The resolver is stdout-only and has fixed exit
    codes: `0` for REUSE/COMPOSE, `10` for FORMAL_CHANGE_REQUIRED, `20` for
    BLOCKED, `2` for malformed input, and `30` for unexpected failure.
12. **Registry maintenance contract:** validation, rendering, and drift check
    use the fixed `tools/scripts/registry.py` commands defined in design.
    Rendering is the only generated-Markdown write and is never called by
    operational PLAN_RUN/RUN.
13. **Evidence contracts:** COMPOSE uses the normative
    `opsx.compose-manifest.v1`; FORMAL_CHANGE_REQUIRED uses
    `opsx.formal-change-handoff.v1` persisted under the run receipt path.
    Both contracts are machine-readable and retain failure evidence.
14. **Explicit selection:** `script=` still invokes the resolver and may select
    a disabled/deprecated row only after registry and safety validation.
    Explicit selection never bypasses READ_ONLY, artifact, checksum, or
    provenance gates.
15. **Field coverage:** resolution-enabled rows MUST declare
    `provided_fields`; REUSE requires
    `request.required_fields ⊆ entry.provided_fields`; COMPOSE requires the
    union of child `provided_fields` to cover the request with compatible
    sources, capabilities, and output contracts.
16. **Invocation flags:** every row has `resolution_enabled` and
    `explicit_invocation_enabled`. The first controls automatic matching; the
    second controls exact explicit selection. Cabinet401 v1/v2 use
    `false/true`; ledger-only legacy rows use `false/false`.
17. **Manifest checksum:** `COMPOSE_MANIFEST.json` MUST NOT contain its own
    SHA-256. The finalized manifest is checksummed in
    `COMPOSE_MANIFEST.json.sha256`, recorded in SCRIPTS_REPORT as
    `COMPOSE_MANIFEST_SHA256`, and that sidecar plus the manifest pass the
    ordinary artifact gate.
18. **Canonical cleanliness:** canonical `refs/heads/scripts` MUST have no
    tracked staged or unstaged changes. Registry and execution inputs are read
    from the fixed HEAD, not the worktree. A dirty canonical worktree returns
    `BLOCKED`.
19. **Verification timing:** apply-stage Git integration uses temporary feature
    and scripts worktrees; real post-merge PLAN_RUN smoke is separate. R1
    implementation handoff ends at `READY_FOR_MERGE_REVIEW`.
20. **Canonical bootstrap:** `/opsx-scripts` performs only a thin read-only
    bootstrap in the caller worktree. It records caller identity, selects an
    exact `refs/heads/scripts` candidate using canonical-root precedence, and
    launches the resolver from that candidate. It does not read Registry,
    match, select collectors, or interpret outcomes.
21. **Canonical executable:** the resolver executable and Poetry working
    directory are always `<canonical-root>/tools/scripts/resolver.py` and
    `<canonical-root>`. A caller-local or stale resolver is never used.
22. **Caller contract:** resolver CLI requires absolute `--caller-root`; the
    command surface passes absolute request and canonical paths plus
    `--caller-root`. Resolver recomputes caller provenance and verifies the
    caller and canonical roots share one Git common directory.
23. **Command rollout:** the bootstrap contract applies only after the
    revised `/opsx-scripts` command is installed in the active command surface;
    it does not auto-update old branches or imply canonical runtime rollout.

## Applies to

- `/opsx-scripts`, `/opsx-scripts-prepare`
- `tools/scripts/resolver.py`
- `scripts/REGISTRY.yaml` and generated `scripts/REGISTRY.md`
- collector entrypoints under `scripts/`
- `k8s/jobs/ops-script-runner.yaml`, SCRIPTS_REPORT provenance fields
- Unit tests for resolution, worktree discovery, composition, and hardcoding gates

## Allowed

- Parameterized collectors (`multi_client_*`, `wb_api_readonly_ops/run.py`) с CLI identity.
- COMPOSE plans из нескольких registry rows с `composable=true`, executed as
  ordered child Jobs with independent artifact gates.
- Deprecated collectors with `deprecated_by`, still invokable by explicit
  `script=`, and additive compatibility adapters.
- READ_ONLY Job execution через Harbor proxy-cache SHA image.

## Forbidden

- Any operational collector code or registry write during RUN GO.
- `EXTEND` or `CREATE` as an operational outcome.
- Matching only by caller cwd or feature branch without validated canonical topology.
- Any relative parent-worktree path as an implicit canonical-root default.
- Mutable `:scripts` tag as the only Job image reference.
- Undeclared hardcoded identity in a resolution-enabled collector.
- Hidden semantic merge of child artifacts in a COMPOSE run.

## Examples

Good:

- Feature branch: `PLAN_RUN request=…` invokes `tools/scripts/resolver.py`,
  discovers the validated `refs/heads/scripts` worktree, and returns
  `COLLECTOR_RESOLUTION=COMPOSE` with ordered children.

Bad:

- `RUN GO` finds a missing capability and writes a new collector in the caller
  worktree instead of returning a formal-change request.

## Related specs

- `scripts-collector-resolution`
- `scripts-registry-contract`
- `scripts-branch-independent-invocation`

## Related changes

- `scripts-collector-lifecycle-architecture`

## Review checklist

- [x] existing decisions searched (`scripts-wb-api-ops-stack` cited, gaps covered)
- [x] relevant decisions cited
- [x] new decision proposed because accepted decision was missing
- [x] implementation layer matches decision
