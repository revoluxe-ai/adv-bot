# Architectural Debt: TEMPORARY_DUAL_CAMPAIGN_COLLECTION

## ID и заголовок

- **ID:** `TEMPORARY_DUAL_CAMPAIGN_COLLECTION`
- **Title:** Временный dual-path сбор кампаний в shop-runner (managed + unmanaged)

## Status

`ACCEPTED_TEMPORARY_COMPROMISE` (не `CLOSED`)

## Owner decision и rationale

Owner (2026-09-26, revision `/opsx-update` change `shop-wide-campaign-data-collection`):

1. Существующий **managed (legacy RECORD)** контур сбора остаётся без крупного рефакторинга; его universe = **фактический loader** `get_complex_advs` / `__get_advs` (design §B.1), **не** surrogate predicate «PG enrollment anchor».
2. Кампании **вне** legacy ownership sets per grain получают отдельный **minimal read-only** shop-wide контур в том же shop-runner.
3. Оба маршрута **временно сосуществуют** и вместе формируют аналитическую картину магазина.
4. При смене PG-состояния, из‑за которой id входит/выходит из loader'а, **collection ownership** переходит между path; CH history по `adv_id` **непрерывна** (non-atomic handoff — design §C).
5. Сбор **не** создаёт `AdvSetting`, **не** меняет `bot_active`, **не** выполняет WB management writes.
6. **Management relationship** (user connect к WB Sky) **не** доказывается наличием `AdvSetting`; provenance gap сохраняется (design §B.3). Routing **не** использует `bot_active` как gate RECORD ownership.
7. История одной кампании: без double count на read-latest grains, без потери данных, без двух конфликтующих product representations.
8. **Не** автоматически расширять legacy `ComplexAdv` / `fact_stat_states` на unconnected кампании; **не** большой рефактор managed runtime.

**Rationale:** закрыть product gap «полная картина магазина» без риска paid/management контура и без forbidden executor (`scripts/Job`).

## Current vs target architecture

| | Current (до apply) | Target (end-state, вне debt) |
|---|------------------|-------------------------------------|
| Universe сбора | PG-bound через `get_complex_advs` / `__get_advs` (`active_status != 'done'`, incl. `refused`; + search legs via `search_adv_id`) | Единый shop-wide read-side collector |
| Вне legacy ownership | Не попадают в RECORD collectors | Временно: unmanaged read-only slice |
| Executor | shop-runner managed only | shop-runner, один маршрут |

## Оба path и границы ownership

| Path | Collection ownership | Universe (код) | Writes |
|------|---------------------|----------------|--------|
| **MANAGED (legacy RECORD)** | Существующие корутины на `ComplexAdv` | §B.1 design: `get_complex_advs(only_bot_active=False, load_extras=False)` → ownership sets per collector (full_adv `all_adv_ids`, common `main_nmid`, clusters same list) | Legacy CH writers incl. `ClustersAdvStatUpdater` + KeywordSetting side effects |
| **UNMANAGED** | Новый minimal orchestration slice (campaign change) | WB discovery \ ownership set для **campaign advertising** grain `(adv_id, date)` | `full_adv_wb_stat`, inventory/availability; **без** `ClustersAdvStatUpdater`, **без** KeywordSetting, **без** independent `wb_common_stat` writer |

**Management relationship:** для обоих path user connect **может** быть UNKNOWN при sync-created / refused rows; debt **не** закрывает provenance новым PG-полем.

**Shared analytical read-side:** `default_db.*` по grain таблицы. Product funnel (`wb_common_stat`, grain `(nmid, date)`) — **не** per-campaign; shop-wide expansion и единственный coordinator writer для `(nmid, date)` — change **`shop-wide-common-sales-collection`** (legacy `CommonSaleStatUpdater` на managed loader universe остаётся существующим маршрутом под этим coordinator; campaign change **MUST NOT** создавать второй independent `wb_common_stat` writer).

## Limits и incomplete coverage

- **Cluster / normquery stats (`default_db.clusters_adv_stats`):** **вне** unmanaged initial slice. Legacy writer `ClustersAdvStatUpdater` создаёт `KeywordSetting` и требует `ComplexAdv` (`clusters_adv_stat_updater.py`). Будущий safe seam: WB normquery read → **only** `ch.update_clusters_adv_stats` без KeywordSetting.
- `fact_stat_states`, keyword positions, plan columns, minus-phrases, auto-shelf control — managed-only (legacy loader universe).
- `update_advs_data_from_wb_to_pg` / `update_advs_in_db` **не** механизм unmanaged discovery.
- Dual-path ↑ WB API / CH volume.
- **`refused` в PG:** остаётся в legacy loader → managed **collection**; не трактовать как «только unmanaged».

## Risks

- **Double collection** в overlap window handoff (non-atomic — design §C).
- **Duplicated CH rows** same grain until read-latest / reconciliation.
- **Freshness divergence** между decorator periods managed vs unmanaged ticks.
- **Provenance gap:** нет PG поля «connect vs sync»; `AdvSetting` ≠ user connect (design §B.3).

## Mandatory safeguards и acceptance tests

1. Deterministic routing по §B.1 **collection ownership** per `(shop_id, adv_id, collector_id)` / nmid grain для funnel.
2. Route epoch / stale write discard on handoff (design §C).
3. Read-latest documented per table (`argMax(version)` full_adv / wb_common; cluster timestamp grain).
4. Reconciliation job after route switch.
5. Regression: unmanaged → no new `AdvSetting`; id entering loader ownership → unmanaged idle on same grain; **unmanaged does not write clusters_adv_stats** in initial slice; **refused** row still legacy-owned — unmanaged must not duplicate full_adv for that id.
6. Owner contract: shop picture = union managed + unmanaged facts on read-side with correct grains.

## Later workstream dependencies

- Durable `CampaignManagementRelationship` / enrollment provenance field (**beyond** collection ownership; **no** new column in this change).
- Safe normquery seam split from `ClustersAdvStatUpdater`.
- Consolidation single orchestration entry.
- **`shop-wide-common-sales-collection`** — единственный owner shop-wide product/funnel expansion `(nmid, date)`, assortment universe, uncovered routing, common collector и `wb_common_stat` writer; campaign change **MUST NOT** дублировать эти обязанности.
- Specs/tasks change **MUST** cite this file when created.

## Target

Один shop-wide read-side collector в shop-runner; managed semantics — specialization, не второй tick owner.

## Measurable exit criteria

- 100% WB-discovered campaigns одним orchestration entry per shop tick.
- Zero overlapping active collection ownership per `(shop_id, adv_id, collector_id)` за окно N days.
- Unmanaged path removed or no-op без потери read continuity.
- Debt → `CLOSED` после Owner sign-off + verify archived change.

## Repayment date

Не установлена.

## Related artifacts

- `openspec/changes/shop-wide-campaign-data-collection/design.md`
- `openspec/changes/shop-wide-campaign-data-collection/decisions/shop-runner-shop-wide-collection/decision.md`
- Specs/tasks: **отсутствуют**; при создании **MUST** ссылаться на этот path.
