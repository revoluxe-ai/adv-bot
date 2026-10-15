# AI control loop — gap report

Source: [Архитектура ai контура](bc-73b65580-0cb8-5c44-9729-5fc605722c4a). Read-only. Authority: `origin/stage` `23c0671f372f0435b13a3573ec8990b4303b3e4a`. Local `751e7bd` is not authority. No product code.

## Gaps

| | |
|---|---|
| A ChangeSet | GAP. No ChangeSet in `app/` or specs. Control plane module absent. |
| B schema → domain → capability → precondition | PARTIAL. Registry, canonical normalize, export validator, Excel checks. No mutation runner. |
| C proposal → diff → dry-run → apply | GAP. Excel commits directly. Dry-run flags are feature-local. |
| D Write authority | PARTIAL. PG is settings SoT. Many direct writers. No application service. ADR for AI apply owner missing. Export stays read-only. |
| E Change events | GAP. History is hash snapshots, not old/requested/applied/observed + actor. |
| F Post-check | GAP. ~5m poll, not per write. |
| G Full AI Package | Current settings YES. Settings history NO (`campaign_settings_history` in family gaps). Change events NO. |

## Recommended next change

`campaign-settings-changeset-contract`

Problem: AI has a read package and no versioned settings intent WB Sky can accept or reject.

Scope: `ChangeSetV1` + `FieldPolicy.mutation_policy` (fail closed) + pure validate: schema → domain → capability → precondition. Success is a diff (old from canonical snapshot, requested normalized). No I/O.

Out of scope: apply, WB/PG writes, Telegram, Excel behavior, HTTP/MCP, migrations, change events, post-check, history-in-ZIP, shop-runner, live bids.

Reuse: campaign settings registry/canonical/inventory; ADRs campaign-settings-contract-ownership, ai-package-v1-exporter-ownership, card-ab-hold-write-path-ownership.

New: `app/modules/campaign_settings_changeset/`; mutation_policy; proposed decision campaign-settings-changeset-validation-ownership.

Migrations: none. Tests: unit fixtures. Dependencies: registry on this SHA. Do not reopen the six closed changes.

`IMPLEMENTATION_READY: YES`. Apply-authority ADR is explicitly later.

Preserve uncommitted local control-plane WIP. Do not clean it into this change.
