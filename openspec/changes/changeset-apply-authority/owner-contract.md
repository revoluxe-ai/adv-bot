# Owner Contract — changeset-apply-authority

## Что хотим получить

Единый **transport-independent** контракт применения `ChangeSetV1`: клиент
(UI, Telegram, MCP, REST, automation) передаёт **`ApplyRequestV1`**, который
**детерминированно привязан** к ранее просмотренному dry-run (`DryRunReceiptV1`
+ `preview_digest` + `semantic_digest` `sd1_`). **WB Sky Apply Authority**
повторно валидирует, проверяет права, сравнивает `st1` `state_token`,
выполняет запись **только** через writer adapters, перечитывает authoritative
state, выдаёт **неизменяемое** `ApplyEvidenceV1`. Dry-run `OK` **не** является
разрешением на запись.

## Зачем

AI и внешние клиенты предлагают intent; WB Sky — единственный production-write
authority. Без Apply Authority нет общего idempotency, evidence, защиты от stale
state и обхода через transport → writer.

## Что должно остаться неизменным

- `ChangeSetV1`, `validate_changeset`, `dry_run`, `semantic_digest` (`sd1`),
  `state_token` (`st1`), `expected_current_value`, capability tri-state —
  **без изменений** (main spec `campaign-settings-changeset-contract`).
- `campaign_settings_contract` — registry / `normalize_value` only.
- `campaign_settings_history` — **отдельный** authority «что было в истории
  настроек» (ClickHouse projection); не владеет execution receipt.
- Legacy writers (Excel, Telegram, shop-runner) **не** переписываются в planning;
  миграция на Apply — отдельные changes.

## Чего сейчас не делаем

Нет implementation GO: нет PG migrations, нет `apply` Python package, нет REST/MCP,
нет WB HTTP apply, нет production writes, нет deploy. Не меняем archived /
main dry-run spec.

## Как поймём, что получилось (после implementation slices)

- Apply с валидным binding и свежим `state_token` → `VERIFIED` + новый
  `state_token` + immutable evidence.
- Stale token / capability drift / digest mismatch / unauthorized actor →
  **fail closed**, writer не вызывается (или rollback до writer).
- Idempotency: повтор с тем же ключом и тем же semantic request → тот же
  evidence, без второй записи.
- `UNKNOWN_EXTERNAL_STATE` никогда не отображается как успех (V1: reserved for
  Slice D WB; PG-only path uses `FAILED` / `UNKNOWN_INTERNAL_COMMIT`).

## Решения Owner (planning)

- Apply — **отдельный** OpenSpec change от `campaign-settings-changeset-contract`.
- V1 Apply: **PG-only**, три bounded policy ops, **одна транзакция** на shop scope.
- Transport parity: REST и MCP вызывают **один** `ApplyAuthorityService` (будущие
  slices), не writers напрямую.
- Receipt/evidence owner — Apply Authority PG ledger + `ApplyEvidenceV1`, не
  Decision Experiment Memory (может ссылаться позже).
