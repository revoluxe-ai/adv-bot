# Tasks — col-r03-009-contract-preflight-return

Owed scope (`/opsx-apply`): CLI contract/artifact-class surface; COL-R03-009
primary RETURN packager + sha sidecar; L0 side-only; clean_dump fail-closed
gate; report fields; unit/fixture без live WB.

Не включать в apply как blocked DoD:
- обязательный live Owner-bot Job / kubectl cp;
- `battle_tested=YES`;
- объявление Web `READ_ONLY_PREFLIGHT_PASS` / Final Review.

Не включать вообще: Stage B CLEAN_DUMP collect; invent URL / raw HTTP;
Cursor→prod WB; finance/write; retrofit L0→PASS.

Evolution: `CANDIDATE` → `wb-safe-readonly-collect` (formal increment link
optional via `/opsx-evolution`).
Decisions: `decisions/wb-readonly-contract-return-vs-l0/decision.md` +
accepted `scripts-wb-api-ops-stack`, `orders-or-sales-reports-read-identity`,
`wb-api-master-local-swagger-map`.

## 1. Tests-first (packager + gates)

- [x] 1.1 Characterization: зафиксировать текущий CLI (`--shop-id`, `--mode`
      preflight|collect, L0 `wb_readonly_research.zip`) как baseline без
      contract flags — не ломать L0 path (spec: Default L0 research remains
      available without contract)
- [x] 1.2 Failing/target unit: `--contract COL-R03-009` +
      `--artifact-class contract_preflight` MUST писать primary
      `…_COL-R03-009_RETURN.zip` + `.sha256`; exact required file list из
      COL-R03-009 (spec: Contract preflight emits primary RETURN and sidecar)
- [x] 1.3 Unit: contract mode без primary RETURN → exit ≠ 0 (spec: Contract
      preflight produces COL-R03-009 primary RETURN)
- [x] 1.4 Unit: honest REFUSED / mapping blockers всё равно собирают RETURN;
      запрет retrofit L0→PASS (spec: Honest REFUSED still packages RETURN)
- [x] 1.5 Unit: L0 alone при contract_preflight → не handoff ready / fail
      primary gate (spec: L0 cannot satisfy Web handoff)
- [x] 1.6 Unit: `clean_dump` / `--require-preflight-pass` без
      `READ_ONLY_PREFLIGHT_PASS=YES` → exit ≠ 0 и 0 API calls (spec: Clean
      dump without pass fails closed)
- [x] 1.7 Unit: sha sidecar == digest zip; report `PRIMARY_SHA256` /
      archive digest совпадает с primary на диске (spec: Archive digest
      matches primary zip)
- [x] 1.8 Unit: RETURN не содержит shop_id / token / raw rows (spec: RETURN
      has no shop_id or token material)
- [x] 1.9 Paired: L0 research mode (`l0_research` или без contract) всё ещё
      может писать research zip (regression INC-RO-07 path)

## 2. CLI + packager + report fields

- [x] 2.1 Добавить CLI: `--contract`, `--artifact-class`
      (contract_preflight|l0_research|clean_dump), `--bound-alias`,
      `--period-start` / `--period-end`, `--require-preflight-pass`
      (spec: Explicit contract and artifact-class CLI surface)
- [x] 2.2 Реализовать packager COL-R03-009: exact zip name, file set,
      `00_STATUS.yaml` fields, SHA256SUMS; api_preflight
      PASS_CANDIDATE|REFUSED с exact blockers; mapping только из existing
      local adapters (campaigns GET promotion/count может PASS_MAP; ORDERS /
      STATISTICS / CARDS — honest REFUSED при gaps) — без invent URL
- [x] 2.3 Wiring: contract_preflight path собирает primary; L0 только
      side/opt-in; fail-closed если primary missing
- [x] 2.4 Gate clean_dump / require-pass: до API calls проверить accept;
      0 calls при fail (spec: Collect without accept cannot claim clean dump
      readiness)
- [x] 2.5 Report / operator fields: `ARTIFACT_CLASS`, `PRIMARY_ARTIFACT`,
      `PRIMARY_SHA256`, `L0_SIDE_ARTIFACT`, `WEB_COLLECTOR_HANDOFF`,
      `CONTRACT_ID`; при необходимости зеркало
      `SIDE_ARTIFACT` / `EXTERNAL_HANDOFF_READY` для opsx-scripts compat
      (spec: Operator report exposes contract artifact fields)
- [x] 2.6 Обновить module docstrings / `MAPPING.md` (русский) со ссылкой на
      delta specs и proposed decision RETURN vs L0
- [x] 2.7 Прогнать targeted unit:
      `poetry run pytest -m unit tests/unit/scripts/wb_api_readonly_ops/ -v`

## 3. Local smoke + scripts invoke plan

- [x] 3.1 Узкий CLI `--help` / import smoke (без Cursor→prod WB)
- [x] 3.2 Зафиксировать pasteable `/opsx-scripts PLAN_RUN` / `RUN GO` args
      для Dilera contract_preflight (period 2026-07-04..2026-08-02,
      bound-alias WB-TEST-CABINET-001); live Job — Owner follow-up, не apply
      checkbox
- [x] 3.3 При необходимости notes в `scripts/REGISTRY.md` (local evidence
      only) — без `battle_tested=YES` и без ложного «COLLECTOR closed»

## 4. Gates

- [x] 4.1 `poetry run pyright-strict` на затронутые in-policy пути +
      `git diff --check`; pyrightconfig include hygiene для новых `.py`
- [x] 4.2 Self-check: нет Web PASS claim из Job; нет invent URL / raw HTTP;
      нет shop_id/token/raw rows в RETURN; L0 не primary при COL-R03-009;
      L0 path без contract сохранён
