## DESIGN_READINESS

```text
DESIGN_READINESS

PRODUCT_SEMANTICS_RESOLVED: yes
STATE_OWNERSHIP_RESOLVED: yes
DURABLE_SOT_RESOLVED: yes
WRITE_AUTHORITY_RESOLVED: yes
RECOVERY_SEMANTICS_RESOLVED: yes
NORMATIVE_CONFLICTS: none
NORMATIVE_MODALITY_PRESERVED: yes
IMPLEMENTATION_CRITICAL_OPEN_QUESTIONS: none

DESIGN_STATUS: READY
REASON: none
```

## Context

Change `shop-wide-campaign-data-collection` требует **полную аналитическую картину рекламы** подключённого магазина: кампании с product enrollment в WB Sky (PG anchor) и кампании **только в WB API**, без изменения management state и без forbidden executor.

Owner revision (2026-09-26): **временный dual-path** внутри shop-runner — **не** единый unified collector и **не** большой рефактор legacy managed runtime.

**Доказательства runtime (bounded inventory):**

- Исполнитель — **shop-runner**: `WBShop.run()` → `CoroutinesManager` (`app/modules/shop_runner/wb_shop.py`, `service_manager/manager.py`).
- **Collection ownership (legacy RECORD)** сегодня задаётся не «enrollment anchor», а фактическим loader'ом `get_complex_advs` → `__get_advs`: `AdvSetting` JOIN `WBCabinet` по `shop_id`, `active_status != 'done'` (включая `refused` — см. §B.1), опционально `bot_active` при `only_bot_active=True`; post-filter `nmids` непустые (`wb_shop_data_manager.py`).
- Часть корутин уже с `only_bot_active=False` в `WBShop.run()` (full stat, cluster stats, common sale funnel и др.), но **universe по-прежнему только через `ComplexAdv`**, построенный из PG rows.
- WB discovery: `CampaignsInfoV2Adapter.get_all_campaigns()`, `get_advertIds()` (promotion stack).
- `update_advs_data_from_wb_to_pg` → `ShopDataUpdater.update_advs_data` → `wb_db_manager.update_advs_in_db` **может создавать/обновлять** `AdvSetting` для уже известных id; **FORBIDDEN** вызывать этот путь **ради** shop-wide discovery / расширения universe (`design` §Forbidden).
- `connect_existing_advs` — user connect: upsert `AdvSetting` с `bot_active=False`, `active_status` из WB (`connect_existing_advs.py`).

**Architectural debt:** [`openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md`](../../architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md).

Specs/tasks **отсутствуют** — при создании **MUST** ссылаться на debt path выше.

## Evolution Context (optional)

Standalone change; EVOLUTION_HANDOFF не применяется.

## Goals / Non-Goals

**Goals:**

- Два **временных** coexisting маршрута сбора в shop-runner (managed + unmanaged minimal read-only), вместе дающие shop-wide картину на analytical read-side.
- Deterministic routing `MANAGED` | `UNMANAGED` | `UNKNOWN` с handoff при появлении/закрытии PG enrollment anchor.
- Durable inventory WB-discovered кампаний; связь campaign↔nm_id из WB; рекламная статистика в пределах token rights и **доказанно safe** writers.
- Явная фиксация недоступности на CH plane (`default_db`).

**Non-Goals:**

- Единый unified shop-wide collector (debt repayment).
- Автоматическое натягивание `ComplexAdv` / `fact_stat_states` на unconnected кампании.
- Крупный рефактор managed coroutines, AI Package, CSV, Telegram UI, scripts/Job executor.
- Автоподключение к управлению, изменение `bot_active`, billing/metering semantics.

## Architecture Decision References

- [`openspec/changes/shop-wide-campaign-data-collection/decisions/shop-runner-shop-wide-collection/decision.md`](decisions/shop-runner-shop-wide-collection/decision.md) — **Proposed**: shop-runner; scripts/Job **FORBIDDEN**; temporary dual-path.
- [`openspec/decisions/clickhouse-sql-database-qualification/decision.md`](../../decisions/clickhouse-sql-database-qualification/decision.md) — CH SQL **MUST** `default_db.<object>`.
- [`openspec/decisions/billing-fair-leg-metering-write-path/decision.md`](../../decisions/billing-fair-leg-metering-write-path/decision.md) — `bot_active` = billing/metering; **MUST NOT** gate shop-wide discovery/unmanaged inclusion.
- [`openspec/decisions/empty-keywords-pause-write-path/decision.md`](../../decisions/empty-keywords-pause-write-path/decision.md) — management write capabilities; **FORBIDDEN** из collection paths.

## Cross-change dependency: shop-wide-common-sales-collection

Owner boundary (2026-10-05 reconciliation): change **`shop-wide-common-sales-collection`**
является **единственным** owner shop-wide product/funnel expansion по grain `(nmid, date)`:

- assortment universe и uncovered `(nmid, date)` routing;
- common collector и `wb_common_stat` writer;
- common-sales coverage и coordinator legacy `CommonSaleStatUpdater`.

**Campaign change (`shop-wide-campaign-data-collection`) owns:**

- WB campaign discovery, `default_db.shop_campaign_inventory` /
  `default_db.shop_campaign_collection_availability`;
- campaign advertising universe и per-campaign day statistics
  `default_db.full_adv_wb_stat` grain `(adv_id, date)`;
- managed-only `default_db.clusters_adv_stats` (legacy `ClustersAdvStatUpdater`).

**Campaign change MUST NOT:**

- создавать или планировать **второй independent** `wb_common_stat` writer;
- включать `get_sales_funnel_products_history` / `ClickHouseCommonStatManager.insert`
  в unmanaged minimal slice;
- resolver/routing для grain `(nmid, date)` — это common-sales change.

**Legacy handoff:** существующий managed маршрут `CoroutinesManager.update_common_sale_stat`
→ `CommonSaleStatUpdater` для loader universe §B.1 **остаётся** без нового campaign writer;
координация shop-wide `(nmid, date)` expansion — **`shop-wide-common-sales-collection`**.

## Ownership & Placement

| Роль | Компонент | Rationale |
|------|-----------|-----------|
| **Orchestration** | `app/modules/shop_runner/` | Proposed decision |
| **MANAGED collection** | Существующие coroutines на `ComplexAdv` | Без large refactor |
| **UNMANAGED collection** | Новый minimal slice (orchestrator + safe seams only) | Read-only WB; без `ComplexAdv` |
| **Routing** | `CampaignCollectionRouteResolver` (рабочее имя) | Per shop tick |
| **Durable ad facts** | Существующие CH writers + inventory/availability | `default_db.*` |
| **Forbidden** | scripts/Job; discovery через `update_advs_in_db`; management adapters | Owner + decisions |

Checklist: context-first decisions cited — да; proposed decision — да; layer shop-runner; unified collector **не** заявлен.

## Decisions

### A. Временные два path

**MANAGED path (legacy RECORD)** — существующие coroutines; universe сбора = §B.1 **collection ownership** (код loader'а), не доказанная management-связь.

**UNMANAGED path** — minimal read-only slice (§D): WB discovery минус соответствующий **ownership set** per collector grain (§B.1, §F).

**Shared read-side:** потребители читают `default_db` по grain каждой таблицы (§F); orchestration dual-path зафиксирован в debt.

### B. Deterministic routing: MANAGED, UNMANAGED, UNKNOWN

На каждом shop tick resolver **MUST** выдать ровно одну **collection route** per `(shop_id, wb_adv_id)` **для каждого campaign collector grain** (§F: `full_adv_wb_stat`, managed-only `clusters_adv_stats`), не смешивая legacy RECORD writers и unmanaged writers на одном grain. Grain `(nmid, date)` / `wb_common_stat` **вне** resolver этого change — owner **`shop-wide-common-sales-collection`**.

**Две оси (не смешивать):**

| Ось | Вопрос | Источник истины в planning |
|-----|--------|----------------------------|
| **Collection ownership** | Какой path **имеет право** писать fact grain для обнаруженной WB-кампании? | §B.1 — фактический universe legacy RECORD collectors |
| **Management relationship** | Пользователь **подключил** кампанию к управлению WB Sky? | **Не доказуемо** по одной строке `AdvSetting`; provenance gap §B.3 |

Resolver routing **MUST** опираться только на **collection ownership** (§B.1). Management rules Owner contract **не** меняются; новое PG-поле **не** вводится.

#### B.1 Collection ownership = legacy RECORD universe (evidence-based)

**MANAGED (collection route)** для grain G — `wb_adv_id` (или `nmid` для funnel) входит в **ownership set**, который соответствующий legacy collector **уже обрабатывает сегодня** при `WBShop.run()` с `only_bot_active=False` для RECORD-корутин (см. `wb_shop.py`).

**Общий loader (shared predicate)** — цепочка `CoroutinesManager` → `WBShopDataManager.get_complex_advs(only_bot_active=False, load_extras=False)`:

1. **`__get_advs(session, shop_id, only_bot_active=False)`** (`wb_shop_data_manager.py`):
   - `select(AdvSetting).join(AdvSetting.wb_cabinet).where(WBCabinet.shop_id == shop_id, AdvSetting.active_status != 'done')`;
   - при `only_bot_active=True` добавляется `AdvSetting.bot_active.is_(True)` — **не** применяется к shop-wide RECORD корутинам ниже.
2. **`get_pre_complex_advs` → `_build_pre_complex_adv`**: для каждой parent-строки подтягивается search-leg через `AdvSetting.search_adv_id` → **`__get_adv_id_to_search_adv_map`**: `AdvSetting.adv_id.in_(search_adv_ids)` **без** join на `WBCabinet` и **без** фильтра `active_status` на search-row.
3. **`get_complex_advs` post-filter**: остаются только `ComplexAdv` с непустым `nmids` (`complex_advs = [adv for adv in complex_advs if adv.nmids]`).

**Ownership sets per legacy RECORD collector** (shop-wide initial slice):

| Collector / grain | Coroutine | Ownership set (код) |
|-------------------|-----------|---------------------|
| `default_db.full_adv_wb_stat` — grain `(adv_id, date)` | `CoroutinesManager.update_full_adv_stat` | `⋃ adv.all_adv_ids` для каждого `ComplexAdv` из loader'а выше; `ComplexAdv.all_adv_ids` = `{adv_setting.adv_id}` ∪ `{search_adv.adv_id}` если `_search_adv` загружен (`complex_adv.py`) |
| `default_db.wb_common_stat` — grain `(nmid, date)` | `CoroutinesManager.update_common_sale_stat` (legacy managed only) | `⋃ adv.main_nmid` для того же списка `ComplexAdv` (funnel **не** per-campaign). Shop-wide `(nmid, date)` expansion **не** в campaign unmanaged slice — owner **`shop-wide-common-sales-collection`**; campaign **MUST NOT** второй writer |
| `default_db.clusters_adv_stats` | `CoroutinesManager.update_clusters_adv_stats_today/history` → `ClustersAdvStatUpdater` | Тот же список `ComplexAdv` (managed path only для shop-wide; **вне** unmanaged initial slice §D.4) |

**Важно:** predicate **`active_status != 'done'`** в loader'е **не** совпадает с UI connect helper `EXISTING_ADV_ACTIVE_STATUS_NOT_IN = ('refused', 'done')` (`connect_existing_advs.py`): строки со статусом **`refused` остаются в legacy RECORD universe** и owned managed path для full stat / common stat / clusters.

**UNMANAGED (collection route):** `wb_adv_id` присутствует в WB discovery для `shop_id`, но **не** входит в ownership set для campaign advertising grain G (`full_adv_wb_stat`). Unmanaged slice **MUST NOT** инициировать CH write на grain, который legacy collector уже owns в том же tick (duplicate ownership forbidden). **MUST NOT** писать `wb_common_stat` — funnel ownership в **`shop-wide-common-sales-collection`**.

**UNKNOWN:** WB payload / id map не классифицированы однозначно после bounded retry:

- **MUST** upsert discovery inventory (§D.1);
- **MUST** пробовать unmanaged-safe collectors где ownership однозначен;
- **MUST NOT** create `AdvSetting`, **MUST NOT** management writes.

#### B.2 Case matrix: ownership vs management (код)

Management relationship для всех строк **UNKNOWN / unproven** без отдельного durable provenance (§B.3). Таблица — только **collection ownership** для shop-wide RECORD grains.

| Case | Collection ownership (legacy RECORD vs UNMANAGED) | Management relationship |
|------|---------------------------------------------------|-------------------------|
| Sync-created `AdvSetting` (`update_advs_data_from_wb_to_pg` / `wb_db_manager`, не user connect) | **Legacy RECORD**, если строка проходит `__get_advs` (`active_status != 'done'`, shop join) и `ComplexAdv` с `nmids` — те же ownership sets §B.1 | **UNKNOWN** (строка PG ≠ user connect) |
| `active_status == 'refused'` | **Legacy RECORD** (в loader'е **нет** исключения `refused`, в отличие от connect UI) | **UNKNOWN** |
| `active_status == 'done'` | **Не** в `__get_advs` → **UNMANAGED** для WB-discovered id (legacy coroutines не пишут) | **UNKNOWN** |
| Нет строки `AdvSetting` для WB id | **UNMANAGED** при наличии в WB discovery | **N/A** (нет PG anchor); не трактовать как «не управляется» |
| Linked Search leg (`AdvSetting.search_adv_id` → `__get_adv_id_to_search_adv_map`) | Search `adv_id` **Legacy RECORD** на grain `full_adv_wb_stat`, если parent `ComplexAdv` в loader'е и search row найдена в map (`all_adv_ids`); clusters/full stat используют тот же `ComplexAdv` list | **UNKNOWN** для обеих ног |

#### B.3 Explicit exclusions + provenance gap

Следующие поля **MUST NOT** использоваться как **самодостаточный** классификатор collection route или как **доказательство** user connect:

| Field | Role in code | Collection routing |
|-------|----------------|-------------------|
| `AdvSetting.bot_active` | Billing / paid auto runtime | **MUST NOT** gate shop-wide RECORD ownership (`only_bot_active=False` на full/common/clusters в `wb_shop.py`) |
| Наличие строки `AdvSetting` alone | Может быть sync, refused, без user connect | **MUST NOT** equate to MANAGED **management**; ownership только через §B.1 loader |
| `bidder_active`, `parsing_active`, coroutines с `only_bot_active=True` | Automation, не shop-wide RECORD expansion | **Out of** unmanaged MVP scope |

**Provenance gap (accepted, debt):** в PG **нет** поля «management source = user connect vs sync». Apply **MUST NOT** добавлять колонку и **MUST NOT** использовать `bot_active` как surrogate proof of connect.

WB lifecycle (active/paused/finished) — ось inventory (`wb_lifecycle`); unmapped → `unknown`, **не** silent drop.

### C. Transitions UNMANAGED ↔ MANAGED (non-atomic handoff)

**Нет** в коде единой атомарной транзакции «PG connect/disconnect + Redis lock + все collectors». Handoff описывается как **eventually consistent** orchestration.

| Phase | Behavior |
|-------|----------|
| **Routing decision** | Перед каждым collector run resolver вычисляет §B.1 ownership sets + последний WB discovery snapshot; выбирает route **до** WB read / CH write. |
| **Connect (UNMANAGED→MANAGED collection)** | После commit user connect (`connect_existing_advs` upsert) строка **может** попасть в `__get_advs` (если `active_status != 'done'`) → следующий tick **MUST** классифицировать затронутые `adv_id` / search legs как MANAGED **collection**; unmanaged **MUST NOT** новые writes на owned grains; legacy coroutines **MAY** писать со следующего tick. **Management relationship остаётся unproven** без provenance field. |
| **Disconnect / terminal PG** | `active_status` → `done` → строка выпадает из `__get_advs` → UNMANAGED collection для WB-discovered id; legacy перестаёт писать. `refused` **не** выпадает из loader'а — ownership **остаётся legacy** (§B.1). |
| **In-flight overlap** | Два path **могут** пересечься в окне одного tick или между decorator periods: unmanaged run начат до commit connect, managed ещё не включил id. Единственный durable **route epoch** — monotonic `default_db.shop_campaign_inventory.route_version` (§D.1). Redis **MAY** держать координационный lock, но **MUST NOT** быть вторым источником истины epoch. Перед WB read / CH write collector **MUST** прочитать актуальный `route_version` и collection ownership; маршрут с устаревшим epoch **MUST NOT** выполнять запись. Availability row **MUST** нести тот же `route_version`. |
| **Retry** | Ошибка WB/CH на одном collector **MUST NOT** block others; следующий decorator cycle повторяет. |
| **Reconciliation** | Post-switch job (apply): для grains с dual-leg history compare `argMax`/latest timestamp (§F); расхождение → `shop_campaign_collection_availability.reason_code=route_transition_reconcile`. |

**History:** идентичность кампании в CH = **`adv_id`** (и при необходимости leg id); connect/disconnect **MUST NOT** fork new surrogate campaign id.

### D. Minimal read-only unmanaged slice

#### D.1 Inventory

Append/upsert **`default_db.shop_campaign_inventory`**: `shop_id`, `adv_id`, `nm_ids`, `wb_status`, `wb_lifecycle`, `route`, `discovered_at`, `last_seen_at`, `route_version`, `version`. Qualification `default_db.` обязательна.

**Route epoch SoT:** `route_version` в этой таблице — **единственный** durable источник route epoch (§C). Альтернативы «Redis или inventory» нет. Redis не хранит конкурирующий epoch.

#### D.2 Campaign ↔ nm_id

Из WB campaign payload (`CampaignsInfoV2` / batched info); gaps → inventory + availability.

#### D.3 Initial advertising statistics (safe seams only)

| Dataset | WB read (evidence) | CH write | Grain (evidence) | Campaign change scope |
|---------|-------------------|----------|------------------|----------------------|
| Full adv day stat | `wb_data_getter.get_full_adv_stat_for_adv_ids(wb_data_manager, adv_ids, ...)` (`manager.update_full_adv_stat`) | `full_wb_adv_stat.insert` → `default_db.full_adv_wb_stat` | `(adv_id, date)` + `version`; **нет** `shop_id` (`full_wb_adv_stat.py` insert; test DDL `destructive_ch_reset.py`) | **In scope** (unmanaged) — feed `adv_ids` from inventory, без `ComplexAdv` |
| Shop/product funnel | `WBDataManager.get_sales_funnel_products_history(nmids=...)` (`CommonSaleStatUpdater.update_last_week_stats`) | `ClickHouseCommonStatManager.insert` → `default_db.wb_common_stat` | `(nmid, date)` ReplacingMergeTree(`version`); **не per-campaign** (`destructive_ch_reset.py`) | **Out of campaign change** — owner **`shop-wide-common-sales-collection`**. Legacy managed `CommonSaleStatUpdater` на loader universe §B.1 остаётся; campaign **MUST NOT** второй writer |
| Cluster / normquery stat | `get_norn_query_stat_for_date_range(complex_advs=...)` inside `ClustersAdvStatUpdater` | `click_house_clusters_stat_manager.update_clusters_adv_stats` → `default_db.clusters_adv_stats` | `(adv_id, nmid, norm_query, date, timestamp)`; **нет** `shop_id` (`click_house_clusters_stat_manager.py` columns) | **Out of unmanaged slice** — managed-only; см. §D.4 |
| Availability | errors / skips | `default_db.shop_campaign_collection_availability` | diagnostic | **In scope** |

#### D.4 Cluster stats — coverage gap and future safe seam

**FORBIDDEN for UNMANAGED initial slice:** вызов **`ClustersAdvStatUpdater`** целиком (`clusters_adv_stat_updater.py`):

- после CH insert **всегда** вызывает `KeywordsManager.create_new_keyword_settings_for_complex_advs` (`_create_keyword_setting`, `update_past_days_stats`);
- WB read требует `list[ComplexAdv]` (`get_norn_query_stat_for_date_range`);
- managed path additionally maps `original_adv_setting_id` / Redis cluster timestamps keyed by PG id (`manager.update_clusters_adv_stats_today`).

**Future safe seam (apply, not this planning slice):** отдельный helper «WB normquery read by `(adv_id, nmids)` → **only** `ch.update_clusters_adv_stats(stats)`» **без** KeywordSetting side effects; до реализации и тестов cluster stats **не** входят в shop-wide unmanaged MVP.

#### D.5 Forbidden unmanaged

`KeywordSetting` create/update; `complex_adv.get_keywords()` hard dependency; `update_advs_in_db` для discovery; WB pause/start/bid; целый `ClustersAdvStatUpdater`.

### E. Coverage gaps (managed vs unmanaged)

**Managed path** retains full legacy coverage for §B.1 **collection ownership** sets via `ComplexAdv`, including `update_clusters_adv_stats_*` with KeywordSetting side effects.

**Explicitly outside unmanaged initial slice:**

- `default_db.clusters_adv_stats` (§D.4).
- `default_db.fact_stat_states` / `increment_fact_data_stats` — PG `complex_adv_id`, Redis keywords.
- Keyword positions, minus-phrases, plan_fact plan columns tied to `AdvSetting`.
- `only_bot_active=True` coroutines (auto-update, bids, trimmer) — automation, not RECORD expansion.

### F. Identity, CH grains, dedup, recovery

#### F.1 Keys

- Shop scope in orchestration: `shop_id` (WBShop / WBCabinet).
- Campaign advertising facts: **`adv_id`** (+ leg ids where applicable); PG `AdvSetting.id` — managed-only enrichment.
- Product funnel: **`nmid`** — shared across campaigns; shop picture = union nmids on read-side. Write ownership shop-wide `(nmid, date)` — **`shop-wide-common-sales-collection`**; campaign change пишет только `(adv_id, date)` advertising facts.

#### F.2 Read-latest / dedup (not idempotency)

| Table | Write pattern | Read-side latest | Idempotency note |
|-------|---------------|------------------|------------------|
| `full_adv_wb_stat` | Insert row per day with new `version` (`time.time()` string) | `argMax(metric, version)` per `(adv_id, date)` (e.g. `get_total_spend_by_advs.sql`) | Re-run inserts **new version**; readers dedup; duplicate versions **не** double-count in argMax path |
| `wb_common_stat` | ReplacingMergeTree(`version`) via common stat inserter | `argMax(..., version)` per `(nmid, date)` (`clickhouse_manager.get_cart_to_order_ratio_from_common_items_stat`) | Re-run **may** leave multiple rows until merge; readers use argMax |
| `clusters_adv_stats` | Insert; sort key includes `timestamp` | Latest by max `timestamp` per business grain (apply must document exact GROUP BY) | **Overlap window** on route switch can produce two timestamps for same logical day — reconciliation §C |
| `shop_campaign_inventory` | Upsert by `(shop_id, adv_id)` | single current row | `version` monotonic for optimistic concurrency |

**Version/timestamp alone ≠ business idempotency:** они задают **read-latest** после retries и dual-leg overlap; acceptance **MUST** prove no double count on declared read queries (specs/tasks).

#### F.3 Recovery after errors

- **Partial collector failure:** append `shop_campaign_collection_availability` with `reason_code`; other collectors continue (Owner partial success).
- **Successful path freshness:** managed cluster/full stat coroutines update Redis timestamp managers **only after** successful write (`manager.update_clusters_adv_stats_today` sets `_redis_cluster_stat_timestamp_manager` per `original_adv_setting_id`; common stat per `adv_id` derived from nmid map).
- **Unmanaged recovery:** next tick re-attempts from inventory `last_seen_at`; route change **MUST NOT** delete CH history.
- **Post-error availability:** read-side **MUST** treat last success timestamp / argMax row as valid until superseded — not «data missing» only because later attempt failed.

## Semantic Write Target (dual persistence legs)

```text
SEMANTIC_WRITE_TARGET_STATUS: RESOLVED

BUSINESS_TERM: shop-wide рекламные факты (RECORD) для кампании магазина

TARGET_ENTITY_OR_LEG:
  LEG_MANAGED: существующие shop-runner CH insert paths для кампаний в §B.1 legacy RECORD ownership sets (incl. ClustersAdvStatUpdater on managed path; legacy CommonSaleStatUpdater без нового campaign writer)
  LEG_UNMANAGED: minimal slice — full_wb_adv_stat.insert, inventory/availability writers; **not** ClustersAdvStatUpdater; **not** ClickHouseCommonStatManager / funnel WB read
  SHARED_SOT: default_db.full_adv_wb_stat, default_db.shop_campaign_inventory, default_db.shop_campaign_collection_availability; default_db.wb_common_stat (nmid grain) — read-side shared; write coordinator **`shop-wide-common-sales-collection`**

ALLOWED_ADAPTERS:
  LEG_MANAGED: CoroutinesManager managed coroutines (manager.py); full_wb_adv_stat.insert; ClustersAdvStatUpdater + ch.update_clusters_adv_stats; CommonSaleStatUpdater (legacy route only — не second writer)
  LEG_UNMANAGED: CampaignsInfoV2Adapter / wb_data_getter.get_full_adv_stat_for_adv_ids; full_wb_adv_stat.insert; inventory/availability writers

FORBIDDEN_ADAPTERS:
  ClustersAdvStatUpdater (whole class) on LEG_UNMANAGED
  KeywordsManager.create_new_keyword_settings_for_complex_advs on LEG_UNMANAGED
  wb_db_manager.update_advs_in_db / ShopDataUpdater for discovery universe
  ApplyManager / pause / start / bid mutation adapters
  scripts/ Job collector entrypoints

TARGET_EVIDENCE: clusters_adv_stat_updater.py; manager.update_full_adv_stat / update_common_sale_stat; wb_shop_data_manager.__get_advs / get_complex_advs / ComplexAdv.all_adv_ids; destructive_ch_reset CH DDL

OWNER_DECISION_SOURCE: Owner revision TEMPORARY DUAL COLLECTION (planning chat 2026-09-26)

REQUIRED_PAIRED_TESTS:
  - unmanaged full stat → no AdvSetting create, bot_active unchanged
  - route MANAGED → unmanaged leg idle for same adv_id on full_adv_wb_stat grain
  - connect overlap window → argMax read no double count sample
  - UNKNOWN → inventory + availability, no management write
  - unmanaged → clusters_adv_stats not written (coverage gap enforced)
```

## Derived Lifecycle

`LIFECYCLE_STATUS: DERIVED`

| Step | Поведение | SOURCE |
|-----|-----------|--------|
| L1 Discover WB | `get_all_campaigns` / fallback advert ids + batch info | owner-contract |
| L2 Route | §B.1 collection ownership MANAGED / UNMANAGED / UNKNOWN | Owner dual-path |
| L3 Inventory | Upsert `default_db.shop_campaign_inventory` | design §D.1 |
| L4 Collect managed | Legacy coroutines, §B.1 ownership only | proposed decision + debt |
| L5 Collect unmanaged | §D.3 campaign advertising safe seams only (full_adv; **not** wb_common_stat) | Owner minimal read-only |
| L6 Availability | Append availability rows | owner-contract |
| L7 Handoff | §C eventual consistency | Owner ownership transfer |
| L8 Invariants | No AdvSetting create, no bot_active, no WB mgmt writes | owner-contract |

## Risks / Trade-offs

- Dual-path complexity → debt safeguards §C, F.
- Unmanaged **without cluster stats** until safe seam → incomplete keyword-level shop picture (accepted gap §D.4).
- WB/CH volume ↑.
- Enrollment provenance gap §B.3 → mis-route rare sync rows mitigated UNKNOWN + future resolver (debt); **не** путать с ownership по loader'у.

## Migration Plan (planning-level)

1. Feature flag per shop: routing + unmanaged slice.
2. DDL (ClickHouse migration control plane ledger, **not** PG):
   `scripts/clickhouse_migrations/007_create_shop_campaign_inventory_and_availability.sql`
   → `shop_campaign_inventory`, `shop_campaign_collection_availability`.
   Sequence **007** avoids stage collision with merged
   `006_create_campaign_settings_history.sql`. PostgreSQL remains advisory-lock
   coordinator only for migrate Jobs, not CH DDL ledger/target.
3. Pilot; rollback flag → managed-only behavior; CH retained.
4. Verify: WB cardinality vs inventory; no duplicate full_adv argMax grain post-handoff; clusters absent on unmanaged path.

## Open Questions (non-blocking)

- Exact class name (`CampaignCollectionRouteResolver`).
- Literal `reason_code` / `collector_id` enums — specs/tasks.

## Review Checklist

- [x] existing decisions searched (change + ≤3 accepted)
- [x] relevant decisions cited
- [x] temporary dual-path + debt linked
- [x] shop-runner placement; unified collector not claimed
- [x] SWT dual-leg documented
- [x] cluster initial slice gap explicit
- [x] handoff non-atomic honest
- [x] collection ownership vs management split (§B)
- [x] CH grains without false shop_id on fact tables
