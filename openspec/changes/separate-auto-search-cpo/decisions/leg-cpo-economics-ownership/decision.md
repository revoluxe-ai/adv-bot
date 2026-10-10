# Decision: leg-cpo-economics-ownership

## Status

Proposed

## Context

WB Sky управляет связкой из двух ролей: Auto — якорная рекламная нога с `adv_id`, Search — связанная нога по `search_adv_id`.
Accepted decision `billing-fair-leg-metering-write-path` уже фиксирует структурную идентичность этих ног и запрещает определять их по WB marketing type 8/9.

Сейчас runtime `fact_pay_for_order` может представлять общую экономику комплекса Auto + Search. При использовании этого значения внутри leg-level управления плохая экономика одной ноги способна изменить решение другой.

Отдельного accepted decision, который определяет ownership фактического CPO Auto/Search и его consumers, в registry нет.

## Decision

1. Фактический CPO становится leg-scoped read-model: Auto CPO принадлежит ноге Auto, Search CPO принадлежит ноге Search.
2. Идентичность ног определяется структурно: Auto = anchor `AdvSetting.adv_id`; Search = linked `AdvSetting.search_adv_id`, если он существует.
3. Leg CPO рассчитывается из рекламной статистики той же ноги: spend этой ноги / orders этой ноги с сохранением существующей защиты от нулевого denominator.
4. Общий CPO комплекса остаётся отдельной aggregate-метрикой и MUST NOT использоваться как скрытый fallback для leg-level управляющего решения.
5. Один shared read-provider MUST быть источником leg CPO для runtime consumers и UI; UI MUST NOT независимо пересчитывать другую формулу.
6. Auto decision paths MUST читать Auto CPO; Search/keyword decision paths MUST читать Search CPO.
7. Missing Search-нога даёт Search CPO = unavailable; система MUST NOT подменять его Auto/common CPO.
8. Target/Max/resolve CPO остаются общими плановыми порогами кампании, если отдельный change не изменит их семантику.

## Semantic Write Target

```text
SEMANTIC_WRITE_TARGET_STATUS: RESOLVED
BUSINESS_TERM: leg-level фактический CPO для управления связкой Auto + Search
TARGET_ENTITY_OR_LEG: AUTO consumers -> AUTO CPO; SEARCH consumers -> SEARCH CPO
ALLOWED_ADAPTERS: shared leg-CPO read provider; AutoShelfBidControl/Auto activity consumers for AUTO; V3 Search/keyword consumers for SEARCH; paid UI read-only rendering from the same snapshot
FORBIDDEN_ADAPTERS: common fact CPO as leg-level fallback; Search CPO in Auto decision; Auto CPO in Search decision; WB marketing type 8/9 as leg identity; UI-local divergent CPO formula
TARGET_EVIDENCE: owner-contract.md + billing-fair-leg-metering-write-path accepted decision + current ComplexAdv auto/search structural mapping
OWNER_DECISION_SOURCE: openspec/changes/separate-auto-search-cpo/owner-contract.md
REQUIRED_PAIRED_TESTS: bad Auto/good Search -> Search uses Search CPO; bad Search/good Auto -> Auto uses Auto CPO; UI shows both values from same snapshot; missing Search does not fallback to Auto/common
```

## Applies to

- Runtime economics/read-model for connected Auto + Search campaigns.
- Auto shelf/activity consumers that compare fact CPO with plan thresholds.
- V3 Search/keyword consumers that compare fact CPO with plan thresholds.
- Paid campaign/keyword UI that displays campaign economics.
- Regression tests around cross-leg non-effect.

## Allowed

- Preserve common aggregate CPO for plan/fact reporting that is not a leg-level decision.
- Add explicit fields/snapshot for Auto CPO and Search CPO.
- Reuse exact-leg advertising statistics already stored in ClickHouse.
- Keep existing Target/Max/resolve thresholds while changing only the fact input owned by each leg.

## Forbidden

- Использовать общий `fact_pay_for_order` как источник Search CPO только потому, что он уже доступен в `ComplexAdv`.
- Использовать Search CPO для Auto или Auto CPO для Search.
- При missing leg CPO автоматически подставлять CPO другой ноги или комплекса.
- Рассчитывать значения для UI отдельной формулой, отличающейся от runtime provider.
- Определять Auto/Search роль по WB type 8/9 вместо structural pair mapping.
- Удалять общий plan/fact CPO в рамках этого change.

## Examples

Good: Auto CPO выше max, Search CPO ниже target — Search keyword logic видит Search CPO и не ухудшается только из-за Auto.

Good: Search CPO выше max, Auto CPO ниже target — Auto shelf logic продолжает работать по Auto CPO.

Bad: `complex_adv.fact_pay_for_order` остаётся общим и напрямую передаётся в Search `AdvState.fact_pay_for_order`.

Bad: UI показывает `spend/orders` за один период, а runtime принимает решение по другому leg CPO без явного контракта.

## Related specs

- `openspec/changes/separate-auto-search-cpo/specs/leg-cpo-economics/spec.md`
- Orthogonal: `openspec/specs/auto-shelf-exhausted-pause/spec.md`
- Orthogonal: `openspec/specs/auto-bid-module-coexistence/spec.md`

## Related changes

- `separate-auto-search-cpo`

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed because accepted decision was missing
- [x] implementation layer matches decision
