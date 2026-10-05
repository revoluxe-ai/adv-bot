## Why

AI Package v1 зафиксировал карточку `campaign_settings_snapshot` только как
минимальный PG inventory/relations (`AdvSetting` + `WBCabinet`, ids, связь
Auto/Search) и явно отложил **детальный** field-level snapshot на отдельный
change. Без машинно-читаемого снимка настроек рекламных кампаний downstream AI
и аналитика не могут различать авторитетное WB-состояние, локальную политику
бота и неполноту источников — при этом в репозитории уже существуют три разных
read-side DTO (`AdvSettingsSnapshotDTO`, `CampaignResourceSnapshotV1`, v1
inventory card), которые нельзя случайно смешать в один контракт.

## What Changes

- Вводится отдельный доменный контракт **AI Package Campaign Settings Snapshot**
  (`CampaignSettingsSnapshotV1`): read-only, machine-readable, transport-agnostic
  dataset с явным зерном, leg identity, классами источника, provenance,
  freshness и completeness.
- Разрешается seam между тремя существующими представлениями: AI export snapshot
  **не является** `CampaignResourceSnapshotV1` (A1 control plane) и **не является**
  `AdvSettingsSnapshotDTO` (Redis tick shop-runner); допускается переиспользование
  **нижнеуровневых** read/normalization primitives только при семантической
  совместимости.
- Карточка manifest `campaign_settings_snapshot` эволюционирует от v1 minimal
  inventory к detailed settings export с независимыми `collection_outcome`,
  `coverage`, `reason_codes`, `freshness` (per `coverage-provenance`).
- Auto (полки) и Search (ключи) MUST оставаться различимыми legs в snapshot;
  `cmp_*` resource identity A1 MUST NOT подменять dataset identity AI Package
  без явного mapping metadata.
- Missing/null/unknown/unsupported WB и local state MUST оставаться явными;
  fabricated defaults и generated-client injection запрещены; downstream mutation
  eligibility MUST fail-closed на `UNKNOWN`/`UNSUPPORTED`.
- Export path остаётся read-only: только накопленные PG (и при наличии evidence —
  CH) на пути AI Package; без WB API, collectors, control-plane apply, Redis
  snapshot tick writes, lifecycle/budget/bid/bot_active mutations.

## Capabilities

### New Capabilities

- `ai-package-campaign-settings-snapshot`: доменный контракт detailed campaign
  settings snapshot — grain, leg model, field authority classes, provenance,
  freshness/completeness, unknown/null semantics, exposure как AI Package dataset
  card без transport coupling.

### Modified Capabilities

- `ai-package-v1-exporter`: requirement `PostgreSQL campaign inventory and relations (minimal v1)` — расширение карточки `campaign_settings_snapshot` до detailed settings snapshot при выполнении discovery; сохранение read-only и four-dimension completeness.
- `ai-package-v1-contract-tests`: requirement `Contract test — PG inventory not detailed settings snapshot` — новые contract tests на detailed settings semantics, leg separation и fail-closed unknown handling.

## Impact

- Модуль `app/modules/ai_package_v1/` (readers/assembler для
  `campaign_settings_snapshot` detailed payload) — **apply**, не этот planning hop.
- Потенциальный shared read helper слой (extract из A1 normalizer/local_policy)
  — только после явного seam ADR; первый code slice MAY быть PG-only без A1 merge.
- **Не затрагивает:** WB Sky Control Plane apply path, `snapshot_data_updater`
  Redis namespace, collectors, Alembic, `openspec/decisions/index.md`, canonical
  spec promotion, `tools/openspec/openspec_guard.yaml` §0.3 debt.

## Out of scope

- Mutations WB / AdvSetting / Redis / queues / campaign lifecycle / budgets / bids /
  `bot_active`.
- Control-plane preview/apply, ChangeSet resolver, registry writes.
- Transport/API/MCP поверх ZIP; GUI/TG export entrypoints.
- Назначение источника shop product orders/sales.
- Canonical promotion ADR/index и §0.3 guard debt.

## Risk

- Semantic drift если implementer alias'ит AI snapshot к A1 DTO или Redis DTO.
- Partial PG WB-sync columns могут дать ложное ощущение полного WB authority без
  accumulation evidence — mitigated через field-level provenance и `PARTIAL`/`UNKNOWN`.
- Dirty A1 overlap в worktree — mitigated через sequenced tasks: PG-only first slice
  или explicit dependency gate на A1 landing.

## Rollback idea

Planning-only: удалить change directory. Post-apply: feature-flag detailed card off
в exporter manifest builder; v1 minimal inventory card semantics восстанавливаются
из archived `ai-package-v1-contract` delta.
