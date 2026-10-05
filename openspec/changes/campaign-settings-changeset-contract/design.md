## Context

На `origin/stage` `23c0671f372f0435b13a3573ec8990b4303b3e4a` реестр
`app/modules/campaign_settings_contract/registry.py` уже классифицирует
поля settings-owned sources (`SemanticRole`, `HistoryPolicy`, `ExcelPolicy`,
`NormalizationPolicy`) и `canonical.normalize_value` детерминированно
нормализует значения. PostgreSQL читается через
`PostgresCampaignSettingsReader`. История сравнивает canonical hash с
ClickHouse, а не proposed value с current value. `ChangeSet` / `ChangeSetV1`
в Python отсутствуют. `app/modules/wb_sky_control_plane/` на baseline нет.
`CampaignSettingsSnapshotV1` — read-only export и не является mutation
contract. Excel import пишет через `apply_adv_excel_rows`.

Ограничение постановки: не начинать production implementation в этом
planning change и не восстанавливать local-only WIP control plane по догадке.

## Goals / Non-Goals

**Goals:**

- Зафиксировать `ChangeSetV1`, `mutation_policy`, порядок validation и diff
  `NO_CHANGE | CHANGE | REJECTED`.
- Сделать ChangeSet атомарным.
- Оставить проверку чистой функцией без I/O и без writers.
- Переиспользовать registry и `normalize_value`.

**Non-Goals:**

- WB API, PostgreSQL, ClickHouse, Redis writes.
- Apply executor, approval, change-event persistence, post-write observation.
- MCP, public API, Telegram UI, Excel redesign, full AI Package integration.
- Durable idempotency store и distributed locking.
- Создание `app/modules/wb_sky_control_plane/`.

## Architecture Decision References

- `openspec/decisions/campaign-settings-contract-ownership/decision.md` —
  registry владеет классификацией; PG — authority текущих настроек; Excel
  и ClickHouse — проекции; unknown field fail closed.
- `openspec/decisions/shop-data-source-strategy/decision.md` — collectors
  не меняют `bot_active` и не делают ad writes. Этот change тоже не пишет.
- `openspec/decisions/ai-package-v1-exporter-ownership/decision.md` — export
  read-only и не является write authority.
- `openspec/decisions/mode-defaults-policy-ownership/decision.md` — mode
  defaults остаются отдельным overlay и не становятся ChangeSet policy.
- Proposed: `openspec/changes/campaign-settings-changeset-contract/decisions/campaign-settings-changeset-ownership/decision.md`.
  Accepted decision не размещает ChangeSetV1. Это не отсутствие lookup:
  placement закрывается proposed decision этого change.

Context-first lookup выполнен: user scope, `openspec/decisions/index.md`,
затем cited decisions выше. Полный рекурсивный обход decisions не делался.

## Ownership & Placement

Owner layer: `app/modules/campaign_settings_contract/`.

Allowed: новые модули рядом с registry — типы ChangeSetV1, `mutation_policy`,
`validate_changeset_v1`, diff. Unit-тесты в `tests/unit/`.

Forbidden: `app/modules/wb_sky_control_plane/**`; вызов
`apply_adv_excel_rows`; shop-runner writers; WB clients; CH inserts;
изменение `CampaignSettingsSnapshotV1` как mutation schema; отдельный
Excel whitelist mutable fields.

Реализация совпадает с proposed decision: контракт расширяет существующий
settings contract, а не заводит второй control-plane пакет.

## Decisions

### ChangeSetV1 shape

Envelope: `schema_version=changeset.v1`, `changeset_id`, `shop_id`,
`source` (transport-neutral origin label plus optional external reference),
`actor` (producer kind and id; LLM is a producer, not a write authority),
`created_at`, optional `intent`, `operations`.

Operation: `operation_id`, `target`, `field`, `requested_value`,
`expected_current_value`. Target: `source` (registered source name),
`adv_setting_id`, `leg_role` (`AUTO` | `SEARCH` | `ROW`). Keyword and
other child sources add the registry identity field already used as
metadata (`text`, `nmid`, `dow`) inside `target.locator`. Не использовать
`cmp_*` и не использовать Excel column alias как field name.

### mutation_policy

Отдельная таблица, ключ `(source, field)`, не дублирует `FieldPolicy`.
Запись обязана содержать: `mutable`, `target_scope`
(`auto_leg` | `search_leg` | `row` | `keyword` | `shelf` | `schedule`),
ссылку на registry normalization, `required_capabilities`, и флаг
`precondition_required=true` для каждой mutable записи. Allowed domain
берётся из `FieldPolicy.allowed_values` и типа `NormalizationPolicy`.

Поле без записи не mutable. Excel `editable` не копируется в mutable
автоматически. Первая implementation slice классифицирует только те
`semantic_role=setting` поля, для которых target scope доказан кодом
registry/snapshot; остальные settings остаются unsupported и дают
`REJECTED`.

Закрытый каталог capabilities v1: `settings_mutation`,
`campaign_lifecycle`. Неизвестный token в policy или в grant → отказ
загрузки policy либо `REJECTED` на запросе. `campaign_lifecycle`
требуется для `bot_active`, `auto_adv_target_status`,
`auction_adv_target_status`, если эти поля вообще получат mutable entry.

Межполевые инварианты (связки бюджетов, режимов) не кодируются строкой
policy. Именной domain-validator hook: нет объявленного инварианта —
single-field проверки достаточно; объявленный инвариант без реализации
→ `REJECTED`.

### Pipeline

1. structural/schema validation
2. identity resolution against the injected snapshot
3. registry field validation
4. normalization (`normalize_value`)
5. domain validation
6. capability validation
7. current-state/precondition validation
8. deterministic diff

Любой unknown/unsupported → `REJECTED` всего ChangeSet.

### Diff

`NO_CHANGE` — каждая операция нормализуется в текущее значение.
`CHANGE` — все операции приняты и хотя бы одна normalized value отличается.
Для принятой мутации: `field`, `old_value`, `requested_value`,
`normalized_value`.
`REJECTED` — нет actionable change entries.

### Atomicity

Решение: ChangeSet **atomic**. Смесь valid/invalid → `REJECTED`.
Частичный accept запрещён.

### Idempotency

Внутри документа повтор `operation_id` или повтор той же пары
target+field → `REJECTED`.

Между вызовами durable store не создаётся. Контрактная семантика
проверяется инъекцией `PriorChangeSetRecord | None`:
тот же `changeset_id` и тот же canonical hash → детерминированный повтор
прежнего `NO_CHANGE` или `CHANGE` без записи; тот же id и другой hash →
`REJECTED`. `None` означает, что память о прошлых id у вызывающего нет,
и чистая функция не притворяется, что проверила кластер.

### Concurrency

`expected_current_value` обязателен. Сравнение после нормализации.
Mismatch → `REJECTED` (stale). Нет снимка цели → `REJECTED` (missing
state). Пропуск ключа не равен null. Lock не берётся. Будущий apply
обязан повторить тот же precondition на записи; этот change apply не
делает.

### SoT, write, recovery

```text
WHAT is durable: current campaign settings only (existing PostgreSQL). ChangeSet outcomes are not stored.
WHO owns canonical state: PostgreSQL settings rows, classification owned by campaign_settings_contract registry.
WHERE canonical state lives: PostgreSQL. The validator receives an in-memory snapshot argument and does not open a session.
WHO may write it: nobody in this change. ALLOWED_ADAPTERS is only validate_changeset_v1. Forbidden adapters are listed in the proposed decision.
HOW it is read / recovered: caller supplies a snapshot from the existing PG reader. There is no changeset epoch to recover; a retry recomputes the diff. Identical id+hash replay does not append state.
```

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

## Lifecycle

LIFECYCLE_STATUS: DERIVED

- L1. Принять конверт `changeset.v1` и отбраковать пустой, чужой version, повтор `operation_id` и конфликт `changeset_id`. SOURCE: owner-contract «как поймём» и spec envelope.
- L2. Разрешить target, отделить Auto от Search, проверить registry, normalization, domain и capability. SOURCE: owner-contract fail-closed и порядок pipeline из постановки.
- L3. Сравнить `expected_current_value` с переданным снимком; missing и stale отклоняют пакет. SOURCE: owner-contract precondition и «отсутствие текущего снимка».
- L4. Вернуть один статус `NO_CHANGE`, `CHANGE` или `REJECTED` на весь пакет. SOURCE: owner-contract атомарный результат и решение atomicity в этом design.
- L5. Не вызывать production writer ни на одном статусе. SOURCE: owner-contract «Чего сейчас не делаем».

## Risks / Trade-offs

- [Большая часть settings останется non-mutable, пока нет target_scope] → это fail closed, а не дыра; apply-change не получит молчаливый полный список.
- [Local WIP может уже содержать другой ChangeSet] → этот change не создаёт `wb_sky_control_plane`; implementation tasks запрещают код до сверки WIP.
- [Чистая функция не видит гонки после diff] → precondition contract обязателен для будущего apply; lock сознательно вне scope.
- [Gap report file отсутствует в git] → семантика взята из текста постановки, не из отсутствующего path.

## Migration Plan

Код этого planning change не деплоится. Будущий implementation — только
новые pure modules и unit tests. Rollback — удалить модули; PG, Excel и
history paths не меняются. Feature flag не нужен, потому что нет runtime
entry.

## Open Questions

Нет implementation-critical вопросов. Имена файлов внутри
`campaign_settings_contract` фиксированы задачами, не выбором SoT.

Будущий перенос orchestration в control plane после сверки WIP — отдельный
change, не открытый вопрос этого design.

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing
- [x] implementation layer matches decision
