## Why

AI и внешние клиенты могут сформулировать намерение изменить настройки
кампании, но на `origin/stage` нет версионированного ChangeSet, который
WB Sky проверяет детерминированно и который заканчивается diff без записи.
Реестр полей уже запрещает молчаливый drift истории и Excel, однако не
описывает mutation intent, precondition и отказ на stale state.

Файл `docs/ai-control-loop-gap-report.md` на `origin/stage`
`23c0671f372f0435b13a3573ec8990b4303b3e4a` отсутствует (`EVIDENCE_GAP` пути).
Основание этого change — явно переданный вывод того отчёта: ChangeSet
contract = GAP, цепочка proposal → diff → dry-run → apply = GAP, change
events и deterministic post-check = GAP, schema/capability и unified write
authority = PARTIAL. Этот increment закрывает только контракт, проверку и
deterministic diff.

## What Changes

- Добавляется capability `campaign-settings-changeset-contract`: доменный
  `ChangeSetV1`, extension `mutation_policy` поверх существующего field
  registry, чистый validation pipeline и diff `NO_CHANGE | CHANGE | REJECTED`.
- ChangeSet атомарен: одна негодная операция отклоняет весь пакет.
- Precondition `expected_current_value` обязателен; расхождение и отсутствие
  текущего снимка дают `REJECTED`.
- Durable idempotency store, apply executor и production writes не добавляются.
- Пакет `app/modules/wb_sky_control_plane/` не создаётся: на baseline его нет,
  а локальный WIP этого пути разбирается отдельно.

## Capabilities

### New Capabilities
- `campaign-settings-changeset-contract`: versioned mutation intent, fail-closed validation, deterministic diff, no apply.

### Modified Capabilities

Нет. Требования `campaign-settings-history` и
`ai-package-campaign-settings-snapshot` не меняются. Excel policy и history
hash остаются проекциями текущего registry.

## Impact

Затрагивается только планируемый чистый слой
`app/modules/campaign_settings_contract/` (типы, extension policy, validator,
diff) и unit-тесты этого слоя. PostgreSQL остаётся authority текущего
состояния и в этом change только как внешний снимок, который вызывающий
передаёт в чистую функцию. `apply_adv_excel_rows`, shop-runner и WB writers
не вызываются.
