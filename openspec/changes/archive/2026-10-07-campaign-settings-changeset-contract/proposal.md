## Why

AI и внешние клиенты могут сформулировать намерение изменить настройки кампании,
но на `origin/stage` нет закоммиченного ChangeSet, который WB Sky проверяет
детерминированно и который заканчивается dry-run diff без записи. Локальный
незакоммиченный WIP уже содержит `app/modules/wb_sky_control_plane/` с
`ChangeSetV1` (`models/changeset.py`) и `validate_changeset` (`kernel/validate.py`)
— см. project store
[`changeset-local-wip-reconciliation.md`](/cursor/stores/bc-18f0b34a-df7b-4a06-b47a-7bfd4a10a089/docs/changeset-local-wip-reconciliation.md).

Ранний draft #449 планировал второй контракт в `campaign_settings_contract` и
блокировал implementation из-за **CONFLICT**. Owner reconciliation:
**REUSE_DECISION = EXTEND_EXISTING**; **IMPLEMENTATION_BLOCKER =
LOCAL_FOUNDATION_ADOPTION_REQUIRED** (preservation checkpoint, не отсутствие SoT).

[`docs/ai-control-loop-gap-report.md`](https://github.com/revoluxe-ai/adv-bot/blob/stage/docs/ai-control-loop-gap-report.md)
на baseline отсутствует в git; опора — store-копия и явная постановка: контракт +
validate + deterministic diff без apply.

## What Changes

- Replan capability `campaign-settings-changeset-contract` на **расширение**
  существующего `ChangeSetV1` в `app/modules/wb_sky_control_plane` после adoption
  checkpoint; reuse `campaign_settings_contract` только как registry/normalization.
- Зафиксировать `mutation_policy` semantics, pipeline, capability tri-state
  (unknown/unsupported fail closed), idempotency **contract** без durable store,
  atomic whole-ChangeSet rejection, precondition под `state_token`.
- Dry-run статусы: **`NO_OP` | `OK` | `REJECTED`**; diff entries:
  **`SemanticDiffEntryV1`**.
- Entrypoint: расширить существующий **`validate_changeset`** (control-plane
  dry-run/validator), **не** дублировать `validate_changeset_v1` в
  `campaign_settings_contract`.
- Identity: **`CampaignResourceRef` / `cmp_*`** registry; убрать из плана вторую
  схему target `adv_setting_id` + `leg_role` как owner ChangeSet target.
- **Planning only** на PR #449; product код после `LOCAL_FOUNDATION_ADOPTION_REQUIRED`.

## Capabilities

### New Capabilities

- `campaign-settings-changeset-contract`: versioned mutation intent on existing
  control-plane `ChangeSetV1`, fail-closed validation, deterministic dry-run diff,
  no apply.

### Modified Capabilities

Нет. `campaign-settings-history` и `ai-package-campaign-settings-snapshot` не
меняются.

## Impact

После adoption: `app/modules/wb_sky_control_plane/**` (extend), unit tests
`tests/unit/wb_sky_control_plane/**`, reuse
`app/modules/campaign_settings_contract/normalize_value`. Alembic identity из WIP:
`e8a1b2c3d4e5_add_wb_sky_campaign_resource_registry.py` (только при adoption, не
в этом planning commit). PostgreSQL остаётся authority текущего состояния;
validator/dry-run — чистая функция с injected snapshot + `state_token`. Forbidden:
WB/PG/CH writers, `apply_adv_excel_rows`, shop-runner mutation, MIXED
`campaigns_info_v2/adapter.py`.
