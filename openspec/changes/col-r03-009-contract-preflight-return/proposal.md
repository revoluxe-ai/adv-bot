## Why

Stage A пилот не закрывается в Web COLLECTOR: accept-gate ждёт контрактный
primary pack `…_COL-R03-009_RETURN.zip` (+ `.sha256`), а текущий Job отдаёт
только L0 `wb_readonly_research.zip`. Без режима `contract_preflight` и
packager по COL-R03-009 Owner вынужден вручную собирать RETURN или тащить
неверный артефакт — инцидент уже зафиксирован на Job smoke.

## What Changes

- **Intent:** один контракт — CLI/Job режим `contract_preflight` по
  `--contract COL-R03-009`, который собирает **primary** RETURN.zip (+ sha256)
  для Web COLLECTOR; L0 research zip остаётся только side-артефактом.
- **Current behavior:** `wb-api-read-only-preflight` умеет `preflight` /
  `collect`, Stage A ORDERS+sales и Owner-local L0 archive (secret-strip).
  Primary delivery для Web COLLECTOR / COL-R03-009 **не** специфицирован;
  L0 zip не является PASS-артефактом COLLECTOR.
- **Desired behavior:** оператор запускает Job с явными
  `--contract COL-R03-009`, `--artifact-class contract_preflight` (и
  bound-alias / period по TZ); система MUST собрать primary RETURN.zip и
  `.sha256` по контракту COL-R03-009, MUST NOT выдавать L0 research zip как
  primary; gates и SCRIPTS_REPORT MUST отражать contract/artifact-class /
  primary path. Unit-покрытие packager/CLI — часть DoD apply; живой Job —
  через `/opsx-scripts` после green кода, не внутри Cursor→prod.
- **In scope:** contract_preflight CLI surface; packager primary RETURN;
  L0 как side-only; fail-closed gates при неверной паре contract/artifact;
  поля отчёта для Operator/SCRIPTS_REPORT; unit tests.
- **Out of scope:** Stage B / Web CLEAN_DUMP permanent collect; API Master
  swagger map (INC-RO-03); live Cursor→prod WB; браузерный upload в
  COLLECTOR; finance/mutation writes; смена access plane; L0 как единственный
  accept-артефакт.

## Capabilities

### New Capabilities

- `wb-readonly-contract-preflight-return`: контрактный режим
  `contract_preflight` для COL-R03-009 — primary RETURN.zip + `.sha256`,
  side-only L0, gates и отчётные поля; без выдачи research zip как Web
  COLLECTOR PASS.

### Modified Capabilities

- `wb-api-read-only-preflight`: расширить требования CLI/режимов так, чтобы
  существовал явный путь `contract_preflight` / `--contract COL-R03-009` /
  `--artifact-class`, и чтобы L0 Owner-local archive **не** считался primary
  accept-артефактом Web COLLECTOR при этом контракте. Базовые
  preflight/collect и Stage A ORDERS+sales без контракта сохраняют текущий
  смысл.

## Impact

- **Затронутые зоны:** scripts entrypoint read-only preflight/collect;
  упаковка артефактов Job; schema/поля SCRIPTS_REPORT для contract /
  artifact-class / primary path. Runtime access и существующий WB API stack
  остаются теми же; новый raw HTTP client запрещён принятыми decisions
  scripts→WB.
- **Architecture:** placement packager/CLI и граница primary vs side —
  в design; при reusable ownership артефактов (RETURN vs L0) — proposed
  decision в change `decisions/` до apply-ready. Delivery Job остаётся за
  `/opsx-scripts`, не за product apply DoD.
- **Risk:** неверный naming/состав RETURN → reject в COLLECTOR; смягчается
  контрактными gates и unit-тестами на имя/класс артефакта. Риск принять L0
  за PASS — fail-closed: L0 MUST NOT быть primary при COL-R03-009.
- **Rollback:** отключить/не вызывать `--contract COL-R03-009`; прежние
  `preflight`/`collect` + L0 archive продолжают работать без Web COLLECTOR
  accept-пути.
