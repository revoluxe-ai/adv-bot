## 1. Tests-first: leg CPO contract

- [x] 1.1 Добавить unit regression для общего CPO calculator/snapshot: разные Auto/Search spend+orders дают разные CPO; zero-orders сохраняет denominator floor; missing Search даёт `None`.
- [x] 1.2 Добавить CH boundary-integration для batch exact-leg read: строки группируются по concrete `adv_id`, Auto/Search не смешиваются, observation window одинаков.
- [x] 1.3 Добавить DTO regression: aggregate `fact_pay_for_order`, Auto CPO и Search CPO одновременно различимы; legacy aggregate property не меняет семантику.

## 2. Tests-first: Search consumers

- [x] 2.1 Добавить paired V3 keyword regression: bad Auto/good Search использует Search CPO; missing Search CPO не подставляет aggregate/Auto.
- [x] 2.2 Добавить paired regression для Search common-bid updater: direction зависит от Search CPO, а не aggregate/Auto CPO.
- [x] 2.3 Добавить paired regression для bidder V3 safety-cap: Search cap gate читает Search CPO; плохой Auto сам по себе cap не включает.
- [x] 2.4 Добавить paired regression для cluster-bid safety-cap с тем же Search-only CPO contract.
- [x] 2.5 Добавить paired regression для A/B Hold overspend keyword protection: campaign-level Search mutation использует Search CPO и не реагирует только на плохой Auto.

## 3. Tests-first: Auto consumers

- [x] 3.1 Добавить paired regression Auto Shelf Bid Control: bad Search/good Auto передаёт Auto CPO в fact-CPO decision/view и не переключает поведение только из-за Search.
- [x] 3.2 Добавить regression Auto activity/cost confirmation: Auto-specific cost path использует Auto CPO, а aggregate/Search CPO не служит подтверждающим fallback.
- [x] 3.3 Добавить missing-Auto-CPO regression: Auto consumers остаются на безопасной existing missing-data ветке без Search/common substitute.

## 4. Production read-model

- [x] 4.1 Реализовать typed `LegCpoSnapshot` и shared pure CPO calculator с явным observation window и русскими docstrings по spec `leg-cpo-economics`.
- [x] 4.2 Реализовать batch ClickHouse read по concrete adv_id без N+1; сохранить существующие `full_adv_wb_stat` данные и не менять aggregate plan/fact storage.
- [x] 4.3 Расширить `ComplexAdv` явными Auto/Search CPO полями/attach seam, оставив существующий `fact_pay_for_order` aggregate-compatible.
- [x] 4.4 Расширить `WBAdvDTO` explicit Auto/Search CPO accessors; запретить новым Search consumers использовать `dto.fact_pay_for_order` как leg CPO.
- [x] 4.5 Подключить batch attach leg snapshot в shop-runner orchestration, где DTO не строится через уже загруженный `CommonAdvsStatData`; UI/DTO path переиспользует имеющиеся exact-leg stats.

## 5. Production Search routing

- [x] 5.1 Переключить V3 Search/keyword `AdvState.fact_pay_for_order` на Search CPO без изменения Target/Max/resolve semantics.
- [x] 5.2 Переключить Search common-bid updater на Search CPO.
- [x] 5.3 Переключить bidder V3 safety-cap и cluster-bid safety-cap на Search CPO.
- [x] 5.4 Переключить A/B Hold CPO-dependent overspend keyword protection на Search CPO.
- [x] 5.5 Выполнить bounded inventory runtime-reachable Search `fact_pay_for_order` consumers и зафиксировать каждый как migrated Search или intentionally aggregate.

## 6. Production Auto routing

- [x] 6.1 Переключить Auto Shelf Bid Control manager/snapshot/view factual CPO на Auto CPO, сохранив существующие plan-distance/CPC/CTR алгоритмы.
- [x] 6.2 Переключить Auto activity/cost confirmation paths на Auto CPO там, где решение принадлежит Auto leg.
- [x] 6.3 Выполнить bounded inventory runtime-reachable Auto `fact_pay_for_order` consumers и зафиксировать каждый как migrated Auto или intentionally aggregate.

## 7. Paid UI

- [x] 7.1 Добавить в campaign/keyword paid UI отдельные строки `CPO Auto` и `CPO Search`, используя shared leg snapshot/stat projection; missing значение показывать как недоступное без fallback.
- [x] 7.2 Обновить/добавить renderer tests: оба разных значения, одна missing нога, отсутствие подмены aggregate CPO, корректный parse/escaping.
- [x] 7.3 Добавить Telegram payload-limit regression для worst-case сообщения после новых строк согласно `openspec/policies/telegram_bot_api_limits.md`; проверить, что callback_data surfaces этим change не меняются.

## 8. Validation and evidence

- [x] 8.1 Прогнать targeted tests для leg provider/DTO и всех Search/Auto paired regressions.
- [x] 8.2 Прогнать adjacent feature suites для V3 updater, bidder/cluster bids, Auto Shelf Control, activity-control и изменённого UI.
- [x] 8.3 Прогнать CH integration proof изменённого batch read через project test provider.
- [x] 8.4 Прогнать `poetry run pyright-strict` и `git diff --check`.
- [x] 8.5 Выполнить scenario coverage audit по durable plan `SCPLAN-49f4ee71d860e462b991` и закрыть найденные evidence gaps до archive verify.
- [x] 8.6 Выполнить `/opsx-verify mode=impl separate-auto-search-cpo`; archive/commit выполнять только отдельными последующими gates.

## Telegram UI / Message Safety

- [x] Identify every changed Telegram payload surface.
- [x] Add/update tests with worst-case dynamic placeholder data.
- [x] Assert Telegram Bot API limits from `openspec/policies/telegram_bot_api_limits.md`.
- [x] Assert valid parse_mode / escaping.
- [x] Assert callback_data length in UTF-8 bytes or record not_applicable because callback_data is unchanged. — not_applicable: callback_data не менялся.
- [x] Assert no raw technical text leaks to user.

## TASK_GENERATION_READINESS

```text
UNRESOLVED_DESIGN_CHOICES: none
UNRESOLVED_PRODUCT_CHOICES: none
UPSTREAM_NORMATIVE_CONFLICTS: none
NORMATIVE_MODALITY_PRESERVED: yes
CONDITIONAL_BRANCHES_PRESERVED: yes
SCENARIO_REQUIREMENTS_CONSUMED: yes
SCENARIO_PLAN_EVIDENCE_ID: SCPLAN-49f4ee71d860e462b991
SCENARIO_PLAN_STATUS: ready
SCENARIO_PLAN_FRESHNESS: current
TASKS_STATUS: READY
```
