# Decision: Strict single-NMID audit evidence ownership

## Status

Accepted

## Context

Принятые решения о scripts→WB API ownership и identity семьи
`ORDERS_OR_SALES_REPORTS_READ` задают execution stack и source identity, но не
определяют reusable ownership для bounded single-NMID audit и правила
authoritative attribution/spend evidence. Без отдельного решения audit может
смешать данные разных contour, подменить association догадкой или посчитать
один physical spend дважды.

Bounded Job `ops-script-strict-nmid-186069402-20260920t1048` (execution SHA
`b3be48bcf2b74ff6489d53c2d9cee435ccab5896`) подтвердил read-only contract,
нулевой write budget и легитимный `decision.status=PARTIAL` при GAP/runtime
ошибках отдельных evidence sections без нарушения output contract.

## Decision

Strict single-NMID audit должен быть operator-owned read-only orchestration в
scripts/Job-контуре. Он обязан передавать точную audit identity во все
источники и сохранять provenance каждого результата. Association, topology и
attribution считаются authoritative только при наличии поддержанного
источника/признака; отсутствие доказательства остаётся GAP, а не выводом по
смыслу полей. Physical spend имеет единственную canonical representation в
итоговой экономике, а конкурирующие источники должны быть reconciled или
явно исключены с причиной.

### Output semantics (`PARTIAL`)

Успешное bounded read-only execution MAY emit `decision.status=PARTIAL` when:

- audit identity и execution contract валидны;
- machine-readable output проходит `validate_output_contract`;
- `write_budget.writes=0`;
- одна или несколько evidence sections не могут быть заполнены
  authoritatively (GAP, `NONE`, `unsupported`, `missing`, reader/runtime
  errors с явным provenance в gaps).

`PARTIAL` MUST NOT означать infrastructure failure, invalid Job wiring или
нарушение read-only safety, если output contract и write budget доказаны.

### `BLOCKED` semantics

`decision.status=BLOCKED` зарезервирован для случаев, когда audit contract
нельзя безопасно/валидно завершить или результат нельзя доверять, например:

- identity ambiguity или mismatch;
- substituted/unrelated target (A1 fallback, unrelated collector);
- write-capable или mutating execution path;
- invalid output contract (validation fails);
- missing mandatory execution provenance для bounded Job artifact;
- fail-closed conditions, явно определённые spec (identity-safe routing).

`BLOCKED` MUST NOT использоваться только потому, что отдельные evidence sections
имеют GAP или runtime errors при валидном output contract и нулевом write budget.

### Evidence gaps and reader/runtime failures

Ошибки reader/runtime, мешающие заполнить отдельную section, MUST быть
отражены явно в section status, gaps и/или provenance и MAY приводить к
`PARTIAL`, если aggregate output contract остаётся valid. Это не доказывает
полноту Owner-bot evidence plane; completeness отдельных sources — follow-up,
не acceptance criterion bounded strict-single-NMID contract.

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
- `PARTIAL` output при нехватке authoritative evidence при valid contract.
- `BLOCKED` только при fail-closed contract violations выше.

## Forbidden

- A1 fallback, unrelated collector/package substitution или silent identity
  widening.
- Inference association/topology из одного совпавшего ID без authoritative
  support.
- Суммирование physical spend из overlapping sources.
- Новый raw HTTP WB client, local Cursor→production API path или mutation
  write; это также запрещено decision
  `openspec/decisions/scripts-wb-api-ops-stack/decision.md`.
- Смешение `PARTIAL` (evidence gaps) с infrastructure/runtime contract failure.

## Examples

Good: bounded Job завершился, `validate_output_contract` OK, `writes=0`,
`decision.status=PARTIAL` с явными GAP/RuntimeError в gaps для orders/attribution;
identity `confirmed`.

Bad: трактовать тот же результат как `BLOCKED` только из-за GAP sections;
или выдавать `PARTIAL` при failed output contract validation или `writes>0`.

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
- [x] accepted before archive with operational evidence (t1048 handoff)
