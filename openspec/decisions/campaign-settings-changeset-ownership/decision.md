# Decision: Ownership of campaign settings ChangeSetV1

## Status

Accepted

## Context

Accepted decision `openspec/decisions/campaign-settings-contract-ownership/decision.md`
назначает `campaign_settings_contract` владельцем **классификации** полей и
нормализации, не ChangeSet.

На `origin/stage` (после archive change `campaign-settings-changeset-contract`)
канонический пакет **`app/modules/wb_sky_control_plane/`** содержит `ChangeSetV1`
(`models/changeset.py`), `validate_changeset` (`kernel/validate.py`),
`CampaignResourceRef` / `cmp_*`, bounded typed operations (`SetBudgetPolicyOperation`,
`SetSalesPolicyOperation`, `SetBidControlPolicyOperation`), dry-run pipeline
(`kernel/pipeline.dry_run`), `semantic_digest` (`sd1`), `state_token` (`st1`).

Ранний draft размещал контракт в `campaign_settings_contract` → **CONFLICT**.
Reconciliation: **EXTEND_EXISTING** — один owner в control plane.

## Decision

Канонический **`ChangeSetV1`**, dry-run validator **`validate_changeset`**, deterministic
diff (`SemanticDiffEntryV1`, statuses `NO_OP | OK | REJECTED`), и extension
`mutation_policy` принадлежат **`app/modules/wb_sky_control_plane/`**.

`campaign_settings_contract` **переиспользуется** только как registry /
`normalize_value` / `FieldPolicy` для зарегистрированных settings-полей. Он **не**
владеет ChangeSet, **не** экспортирует `validate_changeset_v1`.

ChangeSet атомарен на dry-run. Durable dry-run receipt store и Apply Authority —
отдельный change `changeset-apply-authority`. Precondition: **`state_token`** +
optional **`expected_current_value`**. Validator / dry-run — transport-independent,
**no production writes**.

```text
SEMANTIC_WRITE_TARGET_STATUS: RESOLVED
BUSINESS_TERM: campaign settings mutation intent, dry-run diff only
TARGET_ENTITY_OR_LEG: CampaignResourceRef / cmp_* campaign resource registry
ALLOWED_ADAPTERS: app.modules.wb_sky_control_plane kernel validate_changeset and pipeline dry_run (read-only validation)
FORBIDDEN_ADAPTERS: WB API write clients; PostgreSQL settings writes; ClickHouse writes; apply_adv_excel_rows; shop-runner mutation; Telegram UI apply; MCP/REST apply; app/core/mp/wb/api/adapter/promotion_client/campaigns_info_v2/adapter.py (MIXED)
TARGET_EVIDENCE: openspec/specs/campaign-settings-changeset-contract/spec.md; tests/unit/wb_sky_control_plane/
OWNER_DECISION_SOURCE: archived campaign-settings-changeset-contract owner-contract
REQUIRED_PAIRED_TESTS: cmp_* identity; REJECTED scenarios assert no forbidden writer
```

## Applies to

- Доменные типы и dry-run проверка campaign settings mutation intent в control plane.
- Будущие JSON/API/MCP адаптеры, обязанные вызвать тот же `validate_changeset` / `dry_run`.
- Не применяется к Apply Authority execution, history collector, AI export snapshot, Excel import apply.

## Allowed

- Расширять `wb_sky_control_plane` для dry-run / read path.
- Импортировать `normalize_value` из `campaign_settings_contract`.
- Именованные domain validators для cross-field invariants.

## Forbidden

- Второй `ChangeSetV1` или parallel package owner в `campaign_settings_contract`.
- `validate_changeset_v1` в `campaign_settings_contract`.
- Частичный accept ChangeSet на dry-run.
- Production settings writes из validator/diff/dry-run pipeline.
- MIXED `campaigns_info_v2/adapter.py` на write/validate path.

## Examples

Хорошо: bounded op на `CampaignResourceRef` с валидным `state_token`, diff `OK`,
writers не вызываются.

Плохо: дублировать ChangeSet в `campaign_settings_contract` или вызвать forbidden adapter.

## Related specs

- `openspec/specs/campaign-settings-changeset-contract/spec.md`

## Related changes

- `openspec/changes/archive/2026-10-07-campaign-settings-changeset-contract`
- Archived: `openspec/changes/archive/*-changeset-apply-authority` (apply only; does not alter dry-run semantics)

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] implementation layer matches decision
