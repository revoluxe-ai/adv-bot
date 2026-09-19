# Decision: Strict single-NMID audit evidence ownership

## Status

Proposed

## Context

Принятые решения о scripts→WB API ownership и identity семьи
`ORDERS_OR_SALES_REPORTS_READ` задают execution stack и source identity, но не
определяют reusable ownership для bounded single-NMID audit и правила
authoritative attribution/spend evidence. Без отдельного решения audit может
смешать данные разных contour, подменить association догадкой или посчитать
один physical spend дважды.

## Decision

Strict single-NMID audit должен быть operator-owned read-only orchestration в
scripts/Job-контуре. Он обязан передавать точную audit identity во все
источники и сохранять provenance каждого результата. Association, topology и
attribution считаются authoritative только при наличии поддержанного
источника/признака; отсутствие доказательства остаётся GAP, а не выводом по
смыслу полей. Physical spend имеет единственную canonical representation в
итоговой экономике, а конкурирующие источники должны быть reconciled или
явно исключены с причиной.

## Applies to

- Generic bounded single-NMID audits.
- Operator Job collectors, reports and machine-readable audit outputs.
- Identity, topology, attribution and physical-spend aggregation boundaries.

## Allowed

- Оркестрация и contract validation в scripts/Job.
- Доступ к WB через существующий Owner-bot access plane и `app/core/mp/wb/api`.
- Раздельные evidence records для direct и associated attribution.
- `NONE`, `GAP`, `NULL` и `UNDEFINED` как честные результаты, когда источник
  отсутствует, значение null, capability unsupported или denominator не задан.
- PARTIAL/blocked output при нехватке authoritative evidence.

## Forbidden

- A1 fallback, unrelated collector/package substitution или silent identity
  widening.
- Inference association/topology из одного совпавшего ID без authoritative
  support.
- Суммирование physical spend из overlapping sources.
- Новый raw HTTP WB client, local Cursor→production API path или mutation
  write; это также запрещено decision
  `openspec/decisions/scripts-wb-api-ops-stack/decision.md`.

## Examples

Good: direct campaign spend и associated spend имеют отдельные provenance,
overlap reconciliation и один canonical physical-spend total; unsupported stock
возвращается как GAP.

Bad: взять spend из A1 или другого NMID «для полноты», считать association по
текстовому совпадению и сложить campaign total с уже включённым physical total.

## Related specs

- `openspec/changes/prod-adv-bot-strict-read-only-gap/specs/strict-single-nmid-read-only-audit/spec.md`
- `openspec/specs/wb-api-read-only-preflight/spec.md`

## Related changes

- `prod-adv-bot-strict-read-only-gap`

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed because accepted decision was missing
- [x] implementation layer matches decision
