## Context

На `origin/stage` `23c0671f372f0435b13a3573ec8990b4303b3e4a` реестр
`app/modules/campaign_settings_contract/` классифицирует поля и
`canonical.normalize_value` детерминированно нормализует значения. PostgreSQL —
authority текущих настроек. `ChangeSetV1` в git **отсутствует**; локальный
незакоммиченный WIP уже содержит пакет `app/modules/wb_sky_control_plane/` с
`ChangeSetV1` (`models/changeset.py`), `validate_changeset` (`kernel/validate.py`),
resource/`cmp_*` моделью и типизированными операциями (например
`SetBudgetPolicyOperation`) — см.
[`changeset-local-wip-reconciliation.md`](/cursor/stores/bc-18f0b34a-df7b-4a06-b47a-7bfd4a10a089/docs/changeset-local-wip-reconciliation.md).

**REUSE_DECISION:** `EXTEND_EXISTING` — не создавать второй `ChangeSetV1` и не
размещать owner в `campaign_settings_contract`.

**IMPLEMENTATION_BLOCKER:** `LOCAL_FOUNDATION_ADOPTION_REQUIRED` — explicit
preservation checkpoint, привязывающий owned paths WIP к change, **до** product
implementation. Локальный WIP **не** считается уже принадлежащим PR #449.

Ограничение постановки: этот change — **planning only**; не коммитить WIP по
догадке и не трогать HOME-PC dirty worktree.

## Goals / Non-Goals

**Goals:**

- Зафиксировать расширение существующего `ChangeSetV1`, `mutation_policy`,
  порядок validation и dry-run diff `NO_OP | OK | REJECTED` с
  `SemanticDiffEntryV1`.
- ChangeSet атомарен; unknown/unsupported capability fail closed на tri-state.
- Idempotency contract без durable store; precondition под `state_token`.
- Reuse `campaign_settings_contract.normalize_value` для registered settings fields.

**Non-Goals:**

- WB API, PostgreSQL settings, ClickHouse, Redis writes; apply executor;
  change-event persistence; post-check; MCP; public API; Telegram; Excel redesign;
  full AI Package; durable idempotency; distributed locks.
- MIXED adapter `app/core/mp/wb/api/adapter/promotion_client/campaigns_info_v2/adapter.py`.
- Параллельный `validate_changeset_v1` в `campaign_settings_contract`.

## Architecture Decision References

- `openspec/decisions/campaign-settings-contract-ownership/decision.md` —
  registry owns classification; PG — current settings authority.
- `openspec/decisions/shop-data-source-strategy/decision.md` — collectors не ad writes.
- `openspec/decisions/ai-package-v1-exporter-ownership/decision.md` — export read-only.
- `openspec/decisions/mode-defaults-policy-ownership/decision.md` — mode defaults overlay.
- Proposed: `openspec/changes/campaign-settings-changeset-contract/decisions/campaign-settings-changeset-ownership/decision.md`.
- Reconciliation evidence:
  `/cursor/stores/bc-18f0b34a-df7b-4a06-b47a-7bfd4a10a089/docs/changeset-local-wip-reconciliation.md`.

## Ownership & Placement

| Layer | Owner |
|-------|--------|
| `ChangeSetV1`, dry-run, diff, `validate_changeset` | `app/modules/wb_sky_control_plane/` |
| Field registry, `normalize_value`, `FieldPolicy` | `app/modules/campaign_settings_contract/` (reuse only) |

**Allowed after adoption:** extend WIP modules under `wb_sky_control_plane`;
`mutation_policy` semantics; domain validators; unit tests
`tests/unit/wb_sky_control_plane/`; optional bridge import of `normalize_value`.

**Forbidden:** второй `ChangeSetV1`; owner ChangeSet в `campaign_settings_contract`;
`validate_changeset_v1` duplicate; `apply_adv_excel_rows`; shop-runner/WB/CH writers;
MIXED `campaigns_info_v2/adapter.py`; production implementation до
`LOCAL_FOUNDATION_ADOPTION_REQUIRED`.

## Decisions

### REUSE_DECISION

`EXTEND_EXISTING`. Canonical: `app/modules/wb_sky_control_plane/models/changeset.py:ChangeSetV1`.

### ChangeSetV1 shape (extend, do not redefine)

Envelope and operations per local WIP at adoption (reconciliation cites
`schema_version`, `changeset_id`, shop scope, actor/source metadata, operation list).
Operations are **typed bounded policy operations** (three bounded kinds in WIP;
example name in reconciliation: `SetBudgetPolicyOperation`; any additional op class
names — read from `changeset.py` at checkpoint, not invented here).

Target identity: **`CampaignResourceRef`** resolved through **`cmp_*`** campaign
resource registry (Alembic revision identity in WIP:
`e8a1b2c3d4e5_add_wb_sky_campaign_resource_registry.py`). Auto/Search separation,
если нужна, выражается через ресурсы/ноги в той же модели WIP, **не** через
параллельную схему `adv_setting_id` + `leg_role` как ChangeSet target owner.

Concurrency: envelope carries **`state_token`** for the snapshot generation.

Optional per-operation **`expected_current_value`** — field-level semantic
precondition (see Concurrency).

### mutation_policy

Extension semantics keyed to existing bounded operations / settings fields:
mutability, normalization (delegate to registry where applicable), allowed value
domain, capability requirements, precondition requirements, unsupported/unknown
handling. Cross-field invariants → named domain validators, not JSON Schema alone.

### Capability

Extend existing **tri-state** capability model in control-plane WIP. Unknown or
unsupported capability tokens → fail closed → whole ChangeSet `REJECTED`.

### Pipeline

1. structural / Pydantic validation
2. `state_token` and snapshot generation binding
3. `CampaignResourceRef` / `cmp_*` resolution
4. registry + `mutation_policy`
5. normalization (`normalize_value` for registered settings fields)
6. deterministic domain validation
7. capability validation
8. `expected_current_value` precondition (when present)
9. deterministic diff → `SemanticDiffEntryV1`

Any failure → atomic `REJECTED`.

### Diff / dry-run status

- **`NO_OP`** — after normalization, no semantic change vs snapshot at `state_token`.
- **`OK`** — all operations accepted; at least one `SemanticDiffEntryV1` differs.
- **`REJECTED`** — no actionable diff; whole set rejected.

Entries use **`SemanticDiffEntryV1`** (foundation type from WIP); fields include
old, requested, normalized representations as modeled there.

### Atomicity

Whole ChangeSet **atomic**. Mixed valid/invalid → `REJECTED`.

### Idempotency (contract only)

Duplicate `operation_id` in one ChangeSet → `REJECTED`.
Duplicate `changeset_id` + different canonical body (injected prior record) →
`REJECTED`. Same id + same body → deterministic replay of same `NO_OP` or `OK`.
No new durable table.

### Concurrency / precondition

**Master rule** (reconciliation report does not state an alternate rule):

- **`state_token`** is the only concurrency / optimistic-generation contract.
- **`expected_current_value`** is **not** a second lock. It is a field-level semantic
  precondition evaluated only against the snapshot generation identified by
  `state_token`.
- Missing, unknown, or mismatched **`state_token`** → reject whole ChangeSet.
- If **`expected_current_value`** is present and disagrees with the value in that
  generation (after normalization) → reject whole ChangeSet.
- Omitting **`expected_current_value`** does **not** bypass **`state_token`**.

### ADOPTION_DECISION

Adopt/extend local `wb_sky_control_plane` foundation only after
`LOCAL_FOUNDATION_ADOPTION_REQUIRED` checkpoint binds exact owned paths to this
change. WIP remains uncommitted and not owned by PR #449 until then.

### SoT, write, recovery

```text
WHAT is durable: PostgreSQL current settings only. Dry-run outcomes are not stored.
WHO owns ChangeSet types: wb_sky_control_plane ChangeSetV1 (after adoption).
WHO owns field classification: campaign_settings_contract registry.
WHERE validator reads state: injected in-memory snapshot + state_token; no PG session in validator.
WHO may write: nobody in this change. ALLOWED_ADAPTERS: validate_changeset dry-run only.
HOW recovery works: retry recomputes dry-run; same changeset id+hash → deterministic replay.
```

```text
DESIGN_READINESS
REUSE_DECISION: EXTEND_EXISTING
IMPLEMENTATION_BLOCKER: LOCAL_FOUNDATION_ADOPTION_REQUIRED
PRODUCT_SEMANTICS_RESOLVED: yes
STATE_OWNERSHIP_RESOLVED: yes
DURABLE_SOT_RESOLVED: yes
WRITE_AUTHORITY_RESOLVED: yes
RECOVERY_SEMANTICS_RESOLVED: yes
NORMATIVE_CONFLICTS: none
NORMATIVE_MODALITY_PRESERVED: yes
IMPLEMENTATION_CRITICAL_OPEN_QUESTIONS: none
DESIGN_STATUS: READY
REASON: semantics resolved; implementation gated by LOCAL_FOUNDATION_ADOPTION_REQUIRED (checkpoint, not unresolved SoT)
```

## Lifecycle

LIFECYCLE_STATUS: DERIVED

- L1. Accept envelope; validate `state_token`; reject duplicate ids / schema mismatch.
- L2. Resolve `CampaignResourceRef`; registry; normalization; domain; capability.
- L3. Evaluate `expected_current_value` under `state_token` generation.
- L4. Emit one of `NO_OP`, `OK`, `REJECTED` for whole ChangeSet.
- L5. No production writer on any status.

## Risks / Trade-offs

- [WIP not on origin/stage] → adoption checkpoint обязателен; planning не притворяется implementation.
- [Bounded ops only] → fail closed для неподдерживаемых мутаций — ожидаемо.
- [Pure dry-run] → гонки после diff остаются на будущий apply (out of scope).

## Migration Plan

Planning artifacts only on PR #449. Post-adoption: commit/bind WIP paths; extend
modules; unit tests. Rollback — revert control-plane modules; PG/Excel unchanged.

## Open Questions

Имена всех трёх bounded operation types в WIP — фиксируются при checkpoint
чтением `models/changeset.py`, не в этом planning commit.

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing
- [x] implementation layer matches decision
