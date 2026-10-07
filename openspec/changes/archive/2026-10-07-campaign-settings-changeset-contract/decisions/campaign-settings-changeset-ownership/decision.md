# Decision: Ownership of campaign settings ChangeSetV1

## Status

Proposed

## Context

Accepted decision `openspec/decisions/campaign-settings-contract-ownership/decision.md`
назначает `campaign_settings_contract` владельцем **классификации** полей и
нормализации, не ChangeSet. На `origin/stage` нет закоммиченного
`wb_sky_control_plane`, но локальный незакоммиченный WIP уже содержит
`ChangeSetV1` (`models/changeset.py`), `validate_changeset` (`kernel/validate.py`),
`CampaignResourceRef` / `cmp_*`, и bounded typed operations (например
`SetBudgetPolicyOperation`) —
[`changeset-local-wip-reconciliation.md`](/cursor/stores/bc-18f0b34a-df7b-4a06-b47a-7bfd4a10a089/docs/changeset-local-wip-reconciliation.md).

Ранний draft #449 размещал контракт в `campaign_settings_contract` и запрещал
control plane → **CONFLICT**. Owner reconciliation: **EXTEND_EXISTING**; реализация
блокируется **LOCAL_FOUNDATION_ADOPTION_REQUIRED**, не отсутствием семантики.

## Decision

Канонический **`ChangeSetV1`**, dry-run validator **`validate_changeset`**, deterministic
diff (`SemanticDiffEntryV1`, statuses `NO_OP | OK | REJECTED`), и extension
`mutation_policy` принадлежат **`app/modules/wb_sky_control_plane/`**.

`campaign_settings_contract` **переиспользуется** только как registry /
`normalize_value` / `FieldPolicy` для зарегистрированных settings-полей. Он **не**
владеет ChangeSet, **не** экспортирует `validate_changeset_v1`.

ChangeSet атомарен. Durable idempotency store и distributed lock не входят.
Precondition: **`state_token`** + optional **`expected_current_value`** (master rule
в `design.md`). Validator — transport-independent, no production writes.

**ADOPTION_DECISION:** foundation принимается только после checkpoint
`LOCAL_FOUNDATION_ADOPTION_REQUIRED`. Локальный WIP не принадлежит PR #449 до
binding.

```text
SEMANTIC_WRITE_TARGET_STATUS: RESOLVED
BUSINESS_TERM: campaign settings mutation intent, dry-run diff only
TARGET_ENTITY_OR_LEG: CampaignResourceRef / cmp_* campaign resource registry (local WIP; reconciliation doc §Why it conflicts)
ALLOWED_ADAPTERS: app.modules.wb_sky_control_plane kernel validate_changeset (dry-run / validate only; no I/O, no writer)
FORBIDDEN_ADAPTERS: WB API write clients; PostgreSQL settings writes; ClickHouse writes; apply_adv_excel_rows; shop-runner mutation; Telegram UI; MCP; public HTTP apply; app/core/mp/wb/api/adapter/promotion_client/campaigns_info_v2/adapter.py (MIXED)
TARGET_EVIDENCE: changeset-local-wip-reconciliation.md; campaign-settings-contract-ownership ADR (PG + registry); e8a1b2c3d4e5_add_wb_sky_campaign_resource_registry.py (WIP Alembic identity)
OWNER_DECISION_SOURCE: owner-contract.md ADOPTION_DECISION + REUSE_DECISION EXTEND_EXISTING
REQUIRED_PAIRED_TESTS: cmp_* identity resolution; every REJECTED scenario asserts no forbidden adapter invoked
```

## Applies to

- Доменные типы и dry-run проверка campaign settings mutation intent в control plane.
- Будущие JSON/API/MCP адаптеры, обязанные вызвать тот же `validate_changeset`.
- Не применяется к history collector, AI export snapshot, Excel import apply.

## Allowed

- Расширять `wb_sky_control_plane` после `LOCAL_FOUNDATION_ADOPTION_REQUIRED`.
- Импортировать `normalize_value` из `campaign_settings_contract`.
- Именованные domain validators для cross-field invariants.

## Forbidden

- Второй `ChangeSetV1` или parallel package owner в `campaign_settings_contract`.
- `validate_changeset_v1` в `campaign_settings_contract`.
- Частичный accept ChangeSet.
- Production writes из validator/diff.
- MIXED `campaigns_info_v2/adapter.py` на write/validate path этого change.
- Считать локальный WIP уже принадлежащим PR #449 без checkpoint.

## Examples

Хорошо: операция из bounded WIP set на `CampaignResourceRef` с валидным
`state_token`, capability grant, diff `OK`, writers не вызываются.

Плохо: дублировать ChangeSet в `campaign_settings_contract`, принять смешанный
пакет частично, или вызвать forbidden adapter.

## Related specs

- openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md

## Related changes

- openspec/changes/campaign-settings-changeset-contract

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed because placement was missing on stage
- [x] implementation layer matches decision
