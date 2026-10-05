## Why

AI Package v1 уже экспортирует campaign stat, funnel и settings snapshot, но не
содержит query-level keyword performance, позиций и готовых analytical windows.
Сильной LLM после одной выгрузки нельзя честно ответить «что было вчера / за
7–365 дней / YTD / за всю доступную историю» без ручного join десятков
неописанных CH/UI источников. UI-пути агрегируют физические `adv_id`, смешивают
Auto/Search, реконструируют spend и подменяют missing позиции — их нельзя
использовать как canonical export authority.

## What Changes

- Вводится семейство read-only datasets **keyword performance history** под
  `keyword_performance/` в существующем AI Package: `keyword_daily`,
  `keyword_windows`, `keyword_current_state`, `keyword_changes`, optional
  `keyword_positions`, root `DATA_MAP.json`, `coverage.json`.
- Keyword datasets MUST экспортировать **всю реально доступную историю** из
  persisted CH (MIN/MAX по scope); caller `ExportPeriod` документируется в
  DATA_MAP как отдельный bounded context и MUST NOT обрезать keyword history.
- Canonical daily grain: shop × logical resource (`adv_setting_id`) × physical
  `adv_id` × leg where proven × nmid × normalized query × date — без silent
  cross-adv_id rollup.
- Conservative spend semantics (`QUERY_SPEND_STATUS`); UI `CPM×views/1000` MUST
  NOT экспортироваться как factual `spend_rub`.
- Deterministic window engine с Owner catalog (1d…365d, MTD/QTD/YTD, comparable
  prev, `all_available`); partial coverage при недостаточной history.
- Scope expansion для rebound/rebind adv_ids через keyword-specific scope reader
  (PG `AdvSetting.id` + Redis membership read); без изменения публичного
  `ExportScopeAdv` DTO.
- Интеграция в существующий `ExportService` (reuse pattern
  `campaign_settings_snapshot`); root `DATA_MAP.json` участвует в manifest
  descriptor hash и tamper validation; второй exporter запрещён.
- Export path остаётся read-only: без WB API writes, collectors, PG/Redis/
  control-plane writes.

## Capabilities

### New Capabilities

- `ai-package-keyword-performance-history`: доменный контракт keyword/query
  daily facts, ready windows, current state, change deltas, position
  observations, coverage/DATA_MAP semantics, scope/rebind identity, time/window
  rules, volume/chunking model.

### Modified Capabilities

- `ai-package-v1-exporter`: ADDED requirements для keyword performance datasets,
  DATA_MAP/coverage integration, full-history bounds vs ExportPeriod, scope
  rebound expansion seam; сохранение read-only и four-dimension completeness.
- `ai-package-v1-contract-tests`: ADDED contract tests — keyword export seam,
  deterministic hash, tamper detection, no WB/PG/Redis writes, default export
  includes keyword cards; legacy tests inject fake keyword assembler explicitly
  (settings-assembler pattern).

## Impact

- Модуль `app/modules/ai_package_v1/` — новые readers/assemblers/window engine
  под `keyword_performance/` (**apply**, не этот planning hop).
- Redis read-only seam: `get_rebound_wb_adv_ids` для scope expansion (**read
  only**, no writes).
- ClickHouse read-only SQL на `default_db.clusters_adv_stats`,
  `keyword_position_from_api`, `mv_clusters_last_state`, optional
  `bid_decision_log`.
- **Не затрагивает:** WB API write path, shop-runner updaters, Telegram/graph
  presentation, Control Plane A1, Redis snapshot DTO, Alembic/DDL, canonical
  `openspec/decisions/` promotion в этом hop.

## Out of scope

- Store DRR, shop-wide sales, campaign discovery, prices, stocks, promo, finance,
  Control Plane, ChangeSet, recommendations, automated bid writes, campaign
  management, production WB writes.
- Второй exporter; Excel как canonical format; AI labels (GOOD/BAD/STOP).
- Merge, push, PR, deploy; app/tests implementation в этом planning hop.

## Risk

- Semantic drift если implementer использует UI SQL rollup или Telegram graph
  как source — mitigated через forbidden-source ADR и contract tests.
- Volume full-history export — mitigated через bounded fetch/chunk design и
  optional physical partition без урезания logical history.
- norm_query vs keyword_setting.text collision — mitigated через explicit
  ambiguity/coverage flags, не silent merge.
- argMax timestamp ties — mitigated через deterministic tie-break or fail-closed.

## Rollback idea

Planning-only: удалить change directory. Post-apply: ops-only emergency kill-switch
may disable keyword family; default production wiring keeps keyword export enabled
via default `KeywordPerformanceAssembler`.
