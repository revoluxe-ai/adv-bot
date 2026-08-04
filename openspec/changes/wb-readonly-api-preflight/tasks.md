## Evolution Context (owed)

```text
STAR_ID: wb-safe-readonly-collect
INCREMENT_ID: INC-RO-01
CURRENT_INCREMENT: best-effort 4-family collect + gap report + Owner-local archive (secret-strip only) via /opsx-scripts; optional smallest preflight mode
```

WORKLOG parks / Future Increments (L2 sanitize, quarantine, Web CLEAN_DUMP,
swagger sync, API Master, read-only token) — не owed задачи ниже.

## 1. Tests-first (unit)

- [x] 1.1 Unit: CLI принимает обязательный `--shop-id` и `--mode preflight|collect`; неизвестный mode → non-zero / clear error
- [x] 1.2 Unit: overall status MUST NOT быть full success при наличии family gaps (PARTIAL / failed с gap report)
- [x] 1.3 Unit: secret-strip — token / Authorization / cookie-like strings не попадают в report JSON и archive file names/contents helpers
- [x] 1.4 Unit: unmapped family → gap recorded; no invented URL/call (mock existing stack only)
- [x] 1.5 Unit: mutation-write helper / denylist path refused for this entrypoint (READ_ONLY_NO_MUTATION)
- [x] 1.6 Unit: run ceiling exhausted → stop with honest failure/PARTIAL, no infinite retry loop in orchestrator

## 2. Family mapping (existing stack only)

- [x] 2.1 Зафиксировать mapping ads / cards / analytics / norms → существующие managers/adapters в `app/core/mp/wb/api` (таблица в module docstring или `MAPPING.md` рядом с entrypoint); без новых URL
- [x] 2.2 Для каждой семьи выбрать smallest probe method (preflight) и bounded collect path; gaps явно перечислить, если mapping отсутствует

## 3. Entrypoint + orchestration

- [x] 3.1 Создать scripts package/entrypoint (например `scripts/wb_api_readonly_ops/`) с argparse `--shop-id` / `--mode` и async main
- [x] 3.2 Access только через `get_access_for_wb_cabinet(shop_id)` (или эквивалент); shop_id не хардкодить
- [x] 3.3 Реализовать `preflight`: smallest read-only probe по 4 семьям через existing stack
- [x] 3.4 Реализовать `collect`: best-effort pull с per-family OK/PARTIAL/gap; overall honest status
- [x] 3.5 Reuse shop-runner / production WB retry-rate-limit-timeout на вызовах + верхний finite run ceiling (time and/or call budget) на весь Job
- [x] 3.6 Структурированный report (JSON/Markdown): mode, shop_id, per-family status, gaps, ceiling used; MUST NOT claim Web `READ_ONLY_PREFLIGHT_PASS`

## 4. Owner-local L0 archive

- [x] 4.1 Писать известный output path (payload + report; zip или dir) под `/app/...` совместимый с `/opsx-scripts` kubectl cp
- [x] 4.2 Secret-strip перед записью archive/logs; не логировать Authorization / token
- [x] 4.3 Добавить sha256 манифест или checksum файла архива в report

## 5. Registry + Job wiring

- [x] 5.1 Строка в `scripts/REGISTRY.md` для нового entrypoint (`runnable=UNKNOWN` или `WORKS` только после успешного RUN; `battle_tested=NO`)
- [x] 5.2 Задокументировать known outputs / пример `__SCRIPT_ARGS__` (`--shop-id … --mode collect`) для `/opsx-scripts` (в REGISTRY notes или module docstring)
- [x] 5.3 При необходимости уточнить Job hold/cp path только если текущий `ops-script-runner.yaml` недостаточен (не раздувать шаблон без нужды)

## 6. Verification

- [x] 6.1 Прогнать targeted unit suite нового entrypoint
- [x] 6.2 `poetry run pyright-strict` на затронутых scripts-модулях
- [x] 6.3 Cluster smoke через `/opsx-scripts` PLAN_RUN → RUN GO с arg Dilera shop_id; подтвердить абсолютный локальный путь архива и честный report (PARTIAL допустим)
- [x] 6.4 Отметить в proposed decision checklist «implementation layer matches decision» после размещения кода
