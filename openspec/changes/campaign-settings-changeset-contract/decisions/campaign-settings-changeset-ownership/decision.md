# Decision: Ownership of campaign settings ChangeSetV1

## Status

Proposed

## Context

Accepted decision `openspec/decisions/campaign-settings-contract-ownership/decision.md`
уже назначает settings/control-domain registry единственным владельцем
классификации полей. PostgreSQL — authority текущих настроек. Excel и
ClickHouse — проекции. На `origin/stage` нет типа ChangeSet и нет пакета
`app/modules/wb_sky_control_plane/`. Архив
`ai-package-campaign-settings-snapshot` упоминает этот пакет как будущий
дом apply, но код не закоммичен. Рядом существует отдельный local-only WIP
того же пути. Placement контракта «intent → validate → diff» без apply
существующими accepted decisions не закрыт.

## Decision

Чистый доменный контракт `ChangeSetV1`, extension `mutation_policy`,
детерминированный validator и deterministic diff принадлежат модулю
`app/modules/campaign_settings_contract/`. Они переиспользуют
`FieldPolicy`, `NormalizationPolicy` и `normalize_value`. Они не являются
transport schema и не выполняют production writes.

`mutation_policy` — явное расширение registry, а не второй whitelist.
Поле mutable только при отдельной записи policy. Отсутствие записи,
роль не `setting`, Excel `editable` без mutation entry и неизвестный
target scope означают отказ, а не best-effort. Excel policy не выдаёт
право мутации.

Пакет `app/modules/wb_sky_control_plane/` этот change не создаёт и не
заполняет. Перенос orchestration/apply в этот пакет допустим только
отдельным change после сверки local WIP.

ChangeSet атомарен. Durable idempotency store и distributed lock в этот
контракт не входят. Precondition сравнивается с переданным снимком
текущих настроек; снимок не записывается.

```text
SEMANTIC_WRITE_TARGET_STATUS: RESOLVED
BUSINESS_TERM: campaign settings mutation intent, diff only
TARGET_ENTITY_OR_LEG: each operation names settings source, adv_setting_id, and leg_role AUTO | SEARCH | ROW; KeywordSetting and other registered sources add their own identity fields. Auto and Search are never a single implicit target.
ALLOWED_ADAPTERS: app.modules.campaign_settings_contract validate_changeset_v1 pure function (no I/O, no writer)
FORBIDDEN_ADAPTERS: WB API write clients; PostgreSQL settings writes; ClickHouse writes; apply_adv_excel_rows; shop-runner mutation; Telegram UI; MCP; public HTTP apply
TARGET_EVIDENCE: openspec/decisions/campaign-settings-contract-ownership/decision.md (PG current-settings authority, registry owns classification); origin/stage has no wb_sky_control_plane package; CampaignLegRole AUTO/SEARCH in app/modules/ai_package_v1/domain/settings_enums.py
OWNER_DECISION_SOURCE: owner-contract.md of change campaign-settings-changeset-contract (no production write, fail closed, one semantics for JSON/API/MCP, Excel is not the control protocol)
REQUIRED_PAIRED_TESTS: Auto versus Search target separation must assert the other leg is untouched in the diff; every REJECTED scenario must assert no forbidden adapter is invoked
```

## Applies to

- Доменные типы и проверка campaign settings mutation intent.
- Будущие JSON/API/MCP адаптеры, которые обязаны вызвать тот же validator.
- Не применяется к history collector, AI export snapshot и Excel import apply.

## Allowed

- Расширять `campaign_settings_contract` типами ChangeSetV1, mutation policy,
  validator и diff.
- Принимать текущий снимок аргументом чистой функции.
- Оставлять поле неклассифицированным для мутации, пока нет явной policy:
  запрос тогда `REJECTED`.
- Хранить межполевые инварианты отдельными именованными функциями
  domain validator, не только в JSON Schema и не только в таблице policy.

## Forbidden

- Создавать или изменять `app/modules/wb_sky_control_plane/` в этом change.
- Считать Excel editable списком mutable fields.
- Принимать пакет частично.
- Писать в WB, PostgreSQL, ClickHouse, Redis или Excel из validator/diff.
- Подменять отсутствие текущего значения пропуском precondition.
- Кодировать сложный cross-field инвариант только записью registry.

## Examples

Хорошо: операция `AdvSetting` + `adv_setting_id` + `leg_role=SEARCH` меняет
поле, у которого `mutation_policy.target_scope=search_leg`, expected value
совпадает со снимком, diff содержит old/requested/normalized, writers не
вызываются.

Плохо: положить ChangeSet в несуществующий control-plane пакет, принять
годные операции из смешанного пакета, или считать колонку mutable потому
что она editable в Excel.

## Related specs

- openspec/changes/campaign-settings-changeset-contract/specs/campaign-settings-changeset-contract/spec.md
- openspec/specs/campaign-settings-history/spec.md
- openspec/specs/ai-package-campaign-settings-snapshot/spec.md

## Related changes

- openspec/changes/campaign-settings-changeset-contract

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed because accepted decision was missing
- [x] implementation layer matches decision
