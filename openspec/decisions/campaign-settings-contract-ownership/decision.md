# Decision: Ownership canonical campaign settings contract

## Status

Accepted

## Context

WB Sky хранит настройки кампании в нескольких PostgreSQL сущностях. AdvSetting содержит одновременно настройки, идентичность, WB-synchronized facts и runtime lifecycle state. Отдельно существуют KeywordSetting, AutoShelfBidControlSettings, AdvTimeSettings и AdvTimeWeekMask. Excel export/import сейчас использует собственные ручные наборы editable/read-only колонок.

Такое размещение допускает semantic drift: новая настройка может быть добавлена в ORM и write-path, но отсутствовать в history или Excel без явной ошибки. Accepted architecture decision, который назначает владельца классификации settings-полей и запрещает независимые projection whitelist, отсутствует.

## Decision

Reusable domain contract campaign settings field registry принадлежит settings/control-domain слою WB Sky. Он является единственным владельцем классификации полей, из которой history и human-facing projections получают разрешённую семантику.

Registry MUST описывать каждый candidate field каждого зарегистрированного settings-owned source как минимум по следующим измерениям:
- semantic role: setting | identity | wb_fact | runtime_state | derived | technical;
- history policy: state | metadata | excluded;
- Excel policy: editable | read_only | excluded;
- normalization/type policy;
- exclusion reason для excluded field.

Новый settings-owned source MUST быть зарегистрирован явно. Для зарегистрированного source deterministic inventory test MUST сравнивать runtime/model field inventory с registry. Неизвестное, удалённое или переименованное поле без явного обновления registry MUST fail closed.

PostgreSQL остаётся authority текущих настроек. Registry не является transport contract и не выполняет production writes. ClickHouse history и Excel являются projections/consumers одного domain contract.

History hash MUST вычисляться из canonical versioned history payload, а не из Excel row и не из raw ORM serialization. Timestamp коллектора, диагностические поля и иные non-domain metadata MUST NOT создавать ложные изменения.

## Applies to

- Любые текущие и будущие settings-owned сущности рекламной кампании.
- History snapshot builder/collector.
- Excel export/import schema.
- Будущие API/MCP representations настроек, если они появятся отдельным change.

## Allowed

- Явно исключать runtime/WB-fact/technical поля с reason.
- Иметь history field, который Excel исключает.
- Иметь Excel read-only identity/metadata field.
- Добавлять новое settings-поле только вместе с registry classification и tests.
- Использовать generated projection из registry или parity test, который доказывает полное совпадение.

## Forbidden

- Считать все ORM columns настройками автоматически.
- Silent include неизвестного поля в production history.
- Silent exclude неизвестного поля.
- Держать отдельный ручной history whitelist и отдельный Excel whitelist без parity authority.
- Делать Excel canonical source of truth.
- Делать ClickHouse authority текущих settings writes.
- Кодировать этот инвариант только в prompt, комментарии или JSON Schema без deterministic test.

## Examples

Хорошо:
- В AdvSetting добавляется new_optimizer_limit; contract test падает, пока поле не классифицировано как setting/history-state и Excel editable/read-only/excluded.
- В settings-owned source добавляется last_seen_at; registry явно помечает его technical/history-excluded/Excel-excluded с reason.
- Excel экспортирует только поля, разрешённые registry, сохраняя versioned human-facing template.

Плохо:
- Добавить колонку настройки в ORM и позже «не забыть» вручную внести её в два списка.
- Использовать текущий Excel whitelist как список history fields.
- Хэшировать весь ORM object и тем самым писать новый snapshot из-за runtime timestamp.

## Related specs

- openspec/changes/campaign-settings-history/specs/campaign-settings-history/spec.md

## Related changes

- openspec/changes/campaign-settings-history

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed because accepted decision was missing
- [x] implementation layer matches decision
