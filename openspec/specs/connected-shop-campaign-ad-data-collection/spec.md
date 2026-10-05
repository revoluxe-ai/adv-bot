# connected-shop-campaign-ad-data-collection Specification

## Purpose
TBD - created by archiving change shop-wide-campaign-data-collection. Update Purpose after archive.
## Requirements
### Requirement: Исполнитель сбора — shop-runner

Система MUST выполнять shop-wide сбор рекламных данных по подключённому магазину
в контуре **shop-runner** (per-shop runtime). Система MUST NOT использовать
отдельное задание **scripts/Job** как исполнитель этого shop-wide сбора.

#### Scenario: Сбор при активном shop-runner

- **WHEN** для подключённого магазина выполняется периодический цикл shop-runner
- **THEN** система MUST инициировать обнаружение кампаний и сбор доступных
  рекламных фактов в рамках этого цикла
- **AND** MUST NOT делегировать primary shop-wide сбор отдельному Job-collector
  в scripts/

### Requirement: Временный dual-path без единого unified collector

До погашения debt `TEMPORARY_DUAL_CAMPAIGN_COLLECTION` система MUST сосуществовать
два маршрута сбора внутри shop-runner:

- **Managed (legacy RECORD)** — существующий контур сбора для кампаний в
  **collection ownership** legacy RECORD (см. отдельное requirement);
- **Unmanaged (minimal read-only)** — новый минимальный контур для WB-обнаруженных
  кампаний вне ownership set для данного grain.

Оба маршрута MUST вместе формировать аналитическую картину магазина на read-side.
Система MUST NOT в рамках этого change заменять dual-path единым unified
shop-wide collector и MUST NOT выполнять крупный рефактор managed runtime ради
расширения universe.

#### Scenario: Кампания только в WB API

- **WHEN** кампания обнаружена через WB API для подключённого магазина
- **AND** она не входит в legacy RECORD ownership set для grain G
- **THEN** система MUST собирать доступные факты для G через unmanaged path
- **AND** MUST NOT создавать запись управления кампанией ради включения в managed path

### Requirement: Universe — все WB-обнаруженные кампании

«Все кампании» подключённого магазина MUST означать все кампании, **обнаруживаемые
через WB API**, включая активные, приостановленные и завершённые, **независимо**
от наличия строки enrollment в продукте и значения billing-флага активности бота.

Неизвестное или неоднозначное состояние кампании в ответе WB MUST NOT молча
трактоваться как отсутствие кампании; такие случаи MUST фиксироваться явно
(inventory / availability).

#### Scenario: Завершённая кампания в WB

- **WHEN** WB API возвращает кампанию магазина в завершённом или ином lifecycle-состоянии
- **THEN** система MUST учитывать её в shop-wide discovery
- **AND** MUST NOT исключать её только потому, что она не подключена к управлению WB Sky

### Requirement: Collection ownership отделён от management relationship

Система MUST различать две оси:

| Ось | Смысл |
|-----|--------|
| **Collection ownership** | Какой маршрут сбора имеет право писать факт данного **grain** для обнаруженной WB-кампании |
| **Management relationship** | Подключил ли пользователь кампанию к **управлению** WB Sky |

Маршрутизация сбора MUST опираться **только** на collection ownership.
Наличие строки enrollment или billing-флага MUST NOT считаться доказательством
user connect. Система MUST NOT вводить новое PG-поле provenance в рамках этого change.

#### Scenario: Sync-created enrollment без user connect

- **WHEN** для кампании существует строка enrollment, созданная синхронизацией с WB,
  а не явным подключением пользователя
- **AND** кампания попадает в legacy RECORD ownership set
- **THEN** система MUST направлять сбор фактов на managed path
- **AND** MUST NOT трактовать enrollment как подтверждённое управление пользователем

### Requirement: Legacy RECORD collection ownership

Managed path MUST сохранять universe сбора, эквивалентный фактическому legacy
loader enrollment для shop-wide RECORD-корутин с **отключённым** фильтром
«только bot_active»:

- строки enrollment магазина с `active_status` **отличным от** `done` (включая
  **`refused`**);
- post-filter: только кампании с непустым набором nm_id;
- для per-campaign advertising statistics grain: идентификаторы parent и связанной
  search-ноги, если search-leg загружена для parent в loader.

Billing-флаг `bot_active` MUST NOT быть gate включения кампании в shop-wide
RECORD ownership.

#### Scenario: Refused enrollment остаётся на managed path

- **WHEN** у кампании enrollment со статусом `refused` для подключённого магазина
- **AND** кампания проходит legacy loader predicate (не `done`, непустые nm_id)
- **THEN** система MUST классифицировать collection ownership для legacy RECORD
  grains как **managed**
- **AND** unmanaged path MUST NOT дублировать сбор того же fact grain для этой кампании

#### Scenario: Done enrollment выпадает из managed path

- **WHEN** у кампании enrollment со статусом `done`
- **AND** кампания по-прежнему обнаруживается через WB API
- **THEN** система MUST NOT включать её в legacy RECORD ownership set
- **AND** MUST классифицировать collection ownership для shop-wide RECORD grains
  как **unmanaged** (при успешном WB discovery)

#### Scenario: Нет enrollment — unmanaged при WB discovery

- **WHEN** для идентификатора кампании WB нет строки enrollment
- **AND** идентификатор присутствует в WB discovery для магазина
- **THEN** система MUST классифицировать collection ownership как **unmanaged**
- **AND** MUST NOT трактовать отсутствие enrollment как «кампания не существует»

#### Scenario: Search-нога на managed path для full advertising grain

- **WHEN** parent-кампания в legacy RECORD ownership set
- **AND** для parent известна связанная search-кампания по идентификатору search-leg
- **THEN** система MUST собирать per-campaign advertising statistics для search-leg
  на **managed** path на том же grain, что и parent legs
- **AND** MUST NOT передавать search-leg на unmanaged path для этого grain

### Requirement: Unmanaged path — оставшиеся кампании без дублирования grain

Unmanaged path MUST собирать WB-обнаруженные кампании по **campaign advertising**
grains (`full_adv_wb_stat`), которые **не** входят в legacy RECORD ownership set
для данного collector grain. Product funnel grains `(nmid, date)` **MUST NOT**
быть в scope unmanaged path этого change — owner **`shop-wide-common-sales-collection`**.

Unmanaged path MUST NOT инициировать запись fact grain, который managed path уже
owns в том же tick. Система MUST NOT дублировать один и тот же fact grain двумя
активными writers.

#### Scenario: Исключение overlap ownership

- **WHEN** resolver определил managed ownership для `(магазин, adv_id, grain G)`
- **THEN** unmanaged collector MUST NOT выполнять CH write для G по этому adv_id
  в том же цикле сбора

### Requirement: Запрет изменения management state из сбора

Сбор рекламных данных MUST NOT:

- создавать enrollment (`AdvSetting`);
- менять `bot_active`;
- подключать или отключать кампании от управления WB Sky;
- выполнять WB management writes (ставки, pause/start, ключи и т.п.);
- расширять существующие write permissions;
- вызывать синхронизацию enrollment **ради** расширения universe shop-wide discovery.

Кампания, не подключённая к управлению до сбора, MUST оставаться не подключённой
после сбора.

#### Scenario: Unmanaged сбор без enrollment side effect

- **WHEN** unmanaged path успешно собрал рекламные факты для WB-only кампании
- **THEN** система MUST NOT создать новую строку enrollment
- **AND** MUST NOT изменить `bot_active` существующих строк

### Requirement: Частичный успех и явная недоступность

Система MUST собирать все доступные данные в пределах **фактических прав токена**
магазина. Ошибка или отсутствие прав на **один** источник или collector MUST NOT
останавливать сбор остальных.

Причина недоступности MUST сохраняться явно (availability / diagnostic plane),
чтобы read-side мог отличить «данных нет» от «сбор не удался после последнего
успеха».

#### Scenario: Сбой одного collector

- **WHEN** один collector shop-wide сбора завершился ошибкой WB или хранилища
- **THEN** система MUST зафиксировать причину для затронутого источника
- **AND** MUST продолжить или повторить другие collectors в том же или следующем цикле

#### Scenario: Read-side после ошибки

- **WHEN** последняя попытка сбора для grain завершилась ошибкой
- **AND** более ранняя успешная запись fact grain существует
- **THEN** аналитический read-side MUST трактовать последний успешный fact как
  доступный до появления более новой успешной версии
- **AND** MUST NOT считать историю потерянной только из-за последней ошибки

### Requirement: Grains начального shop-wide slice

Система MUST различать grains хранения и MUST NOT смешивать shop scope с fact keys
там, где продуктовая модель grain иная:

| Dataset | Grain | Campaign change — managed | Campaign change — unmanaged |
|---------|-------|---------------------------|----------------------------|
| Per-campaign day advertising statistics | `(adv_id, date)` | In scope | In scope |
| Product / shop funnel statistics | `(nmid, date)` — **не** per-campaign | Legacy managed loader only (не новый writer) | **Out of scope** — owner **`shop-wide-common-sales-collection`** |
| Cluster / normquery statistics | per adv_id, nmid, norm_query, date | In scope (managed only) | **Out of scope** |

Unmanaged initial slice MUST NOT записывать cluster / normquery statistics,
потому что legacy writer создаёт side effects управления ключами; gap MUST
оставаться явным до отдельного safe seam (debt §Limits).

Unmanaged initial slice MUST NOT записывать `wb_common_stat` и MUST NOT
вызывать `get_sales_funnel_products_history` / `ClickHouseCommonStatManager.insert`
как independent writer — shop-wide `(nmid, date)` expansion owner
**`shop-wide-common-sales-collection`**.

Product funnel MUST NOT атрибутироваться к отдельному `adv_id` на write path.
Read-side shop picture по funnel = union nm_id с dedup на read-latest; write
coordination — common-sales change.

#### Scenario: WB-only кампания без cluster stats

- **WHEN** кампания собирается только через unmanaged path
- **THEN** система MUST записывать доступные per-campaign day statistics
  (`full_adv_wb_stat`)
- **AND** MUST NOT записывать cluster / normquery statistics для этой кампании
  в initial slice
- **AND** MUST NOT записывать `wb_common_stat` / funnel facts из campaign
  unmanaged path (owner **`shop-wide-common-sales-collection`**)

#### Scenario: Managed refused с полным legacy coverage

- **WHEN** кампания на managed path с enrollment `refused`
- **THEN** система MAY продолжать managed сбор включая cluster statistics
  в рамках legacy RECORD ownership
- **AND** unmanaged path MUST NOT дублировать full advertising grain для того же adv_id

### Requirement: Маршрут UNKNOWN

Когда WB payload или карта идентификаторов не классифицированы однозначно после
ограниченного retry, система MUST:

- upsert discovery inventory;
- пробовать unmanaged-safe collectors только где ownership однозначен;
- MUST NOT создавать enrollment и MUST NOT выполнять management writes.

#### Scenario: Неоднозначная классификация

- **WHEN** после retry кампания остаётся с маршрутом UNKNOWN
- **THEN** система MUST обновить inventory с явным статусом
- **AND** MUST append availability с кодом причины
- **AND** MUST NOT создавать enrollment «для прояснения маршрута»

### Requirement: Handoff collection ownership (non-atomic)

Переход collection ownership между unmanaged и managed MUST NOT предполагать
единую атомарную транзакцию «подключение пользователя + все collectors».

Система MUST:

- вычислять маршрут **до** WB read / записи fact grain на каждом collector run;
- при user connect, после которого кампания попадает в legacy ownership set,
  на следующем tick MUST классифицировать затронутые adv_id как managed collection;
  unmanaged MUST NOT выполнять новые writes на owned grains;
- при terminal enrollment `done` MUST переводить WB-discovered кампанию на unmanaged
  collection; **`refused` MUST NOT** выводить кампанию из managed ownership;
- допускать in-flight overlap между path в окне одного tick; единственный durable
  источник route epoch MUST быть `shop_campaign_inventory.route_version`
  (monotonic). Redis MAY использоваться для координации или lock и MUST NOT быть
  вторым источником истины epoch. Перед записью collector MUST сверить актуальный
  `route_version` и collection ownership; маршрут с устаревшим epoch MUST NOT
  выполнять запись. Writer MUST включать этот `route_version` в availability;
- при retry ошибки одного collector MUST NOT блокировать остальные;
- после смены маршрута MUST выполнять reconciliation read-latest grains и
  фиксировать расхождения в availability (`route_transition_reconcile`).

Идентичность кампании в истории фактов MUST сохраняться по **adv_id** (и leg id
где применимо); connect/disconnect MUST NOT вводить surrogate campaign id.

Version/timestamp на write MUST NOT трактоваться как полная business idempotency;
read-side MUST использовать documented read-latest (например argMax по version)
и MUST NOT double-count при overlap window.

#### Scenario: User connect переводит collection на managed

- **WHEN** пользователь подключил кампанию к управлению (upsert enrollment)
- **AND** после commit кампания попадает в legacy ownership set
- **THEN** на следующем shop-runner tick система MUST классифицировать collection
  как managed для затронутых grains
- **AND** unmanaged MUST NOT писать новые facts на grains, уже owned managed path

#### Scenario: Overlap window при connect

- **WHEN** unmanaged batch начат до commit connect
- **AND** collector готов записать fact grain
- **THEN** перед записью fact grain collector MUST сверить актуальные `shop_campaign_inventory.route_version` и collection ownership
- **AND** если epoch устарел или ownership не совпадает с маршрутом collector, collector MUST NOT выполнить запись fact grain
- **AND** in-flight MAY завершиться только если на момент write `route_version` всё ещё актуален и ownership соответствует маршруту collector
- **AND** availability row этой попытки MUST нести тот же `route_version` и MUST NOT заменять запрет записи fact grain
- **AND** read-latest MUST NOT double-count declared grains

#### Scenario: Disconnect done переводит на unmanaged

- **WHEN** enrollment переведён в terminal `done`
- **AND** кампания всё ещё видна в WB discovery
- **THEN** система MUST прекратить managed collection для legacy RECORD grains
- **AND** MUST начать (или продолжить) unmanaged collection для доступных facts
- **AND** MUST NOT удалять историю CH по adv_id

#### Scenario: Refused не меняет managed ownership при disconnect-like событиях

- **WHEN** enrollment имеет статус `refused`
- **THEN** система MUST сохранять managed collection ownership для legacy RECORD
- **AND** MUST NOT переводить кампанию на unmanaged path только из-за статуса refused

#### Scenario: Reconciliation read-latest при уже переключённом маршруте

- **GIVEN** маршрут кампании уже переключён и для grain существует dual-leg history
- **AND** в этом сценарии нет нового события connect или disconnect
- **WHEN** выполняется periodic или reconcile entry
- **THEN** система MUST сверить read-latest grains этой dual-leg history
- **AND** расхождение MUST быть зафиксировано в availability с `reason_code` `route_transition_reconcile`
- **AND** read-latest MUST NOT double-count declared grains
- **AND** если сверенный `route_version` устарел или collection ownership не совпадает с маршрутом, система MUST NOT записать fact grain
- **AND** availability row MUST нести сверенный `route_version`

### Requirement: Lifecycle shop-wide сбора (observable)

Для каждого цикла shop-runner по подключённому магазину система MUST выполнять
наблюдаемую последовательность:

1. **Discover WB** — получить множество кампаний магазина из WB API;
2. **Route** — для каждого `(adv_id, collector grain)` определить MANAGED |
   UNMANAGED | UNKNOWN по collection ownership;
3. **Inventory** — upsert durable inventory обнаруженных кампаний;
4. **Collect managed** — legacy RECORD collectors только для § ownership set;
5. **Collect unmanaged** — minimal read-only collectors для оставшихся **campaign
   advertising** grains initial slice (`full_adv_wb_stat` only; **not** `wb_common_stat`);
6. **Availability** — append строк диагностики partial success / skip / error;
7. **Handoff** — применить правила eventual consistency § handoff requirement;
8. **Invariants** — проверить отсутствие management writes из шагов 4–6.

Отдельный сценарий для шага 7 покрыт requirement Handoff; шаги 1–6 и 8 покрыты
сценариями выше и не требуют дублирующего scenario-only requirement.

#### Scenario: Полный цикл с WB-only и managed кампаниями

- **WHEN** у магазина есть кампании и в legacy ownership set, и только в WB API
- **THEN** один shop-runner tick MUST пройти discover → route → inventory
- **AND** MUST выполнить managed collectors для owned set
- **AND** MUST выполнить unmanaged collectors для оставшихся без duplicate grain
- **AND** MUST записать availability при любых partial failures

### Requirement: Provenance gap (accepted compromise)

Система MUST NOT закрывать gap «user connect vs sync-created enrollment» новым
полем в PG в этом change. Debt MUST оставаться открытым (`ACCEPTED_TEMPORARY_COMPROMISE`,
repayment date unset). Спеки и задачи change MUST ссылаться на
[`openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md`](../../../../architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md).

#### Scenario: Отсутствие surrogate proof of connect

- **WHEN** продукту нужно отличить user connect от sync enrollment
- **THEN** система MUST NOT использовать `bot_active` или mere presence enrollment
  как единственное доказательство connect для shop-wide routing
- **AND** MUST NOT добавлять новую колонку provenance в рамках этого change

