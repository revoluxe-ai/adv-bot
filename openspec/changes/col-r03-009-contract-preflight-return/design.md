## Context

Stage A пилот Web COLLECTOR ждёт primary
`REQ-…_COL-R03-009_RETURN.zip` (+ `.sha256`). Текущий
`wb_api_readonly_ops` + Job умеют L0 `wb_readonly_research.zip`
(`--mode preflight|collect`), без `--contract` / `--artifact-class` /
packager. Smoke Job 20260805 сдал только L0 (exit 0) — COLLECTOR пакет
«взять негде»; `report.archive_sha256` мог не совпадать с файлом.

Stakeholders: implementer (CLI + packager + unit); Owner / `/opsx-scripts`
для live Job после green; Navigator несёт PRIMARY в COLLECTOR.
Constraints: `READ_ONLY_NO_MUTATION`; no invent URL; Cursor→prod WB
FORBIDDEN; honest REFUSED допустим; retrofit L0→PASS запрещён.

## Evolution Context

- **Link state:** `CANDIDATE` → Title (STAR_ID) «Безопасный постоянный сбор
  WB API-данных» (`wb-safe-readonly-collect`)
- **INCREMENT_ID:** не привязан к ACTIVE card increment (сейчас на карточке
  ACTIVE = INC-RO-03 API Master; INC-RO-07 DELIVERED явно исключал
  COL-R03-009 RETURN / Web PASS). Formal `EVOLUTION_HANDOFF` / новый
  increment — optional Owner `/opsx-evolution`; не блокер apply-ready.
- **Contribution (soft):** закрывает пробел «L0 smoke ≠ COLLECTOR handoff»
  на том же scripts/Job контуре без объявления Web PASS из Job.
- **Forward-compat:** packager attestation-only; L0 side остаётся; clean_dump
  gate готовит Stage B без реализации CLEAN_DUMP / PASS внутри этого change.

## Goals / Non-Goals

**Goals:**

- CLI: `--contract COL-R03-009`, `--artifact-class
  contract_preflight|l0_research|clean_dump`, `--bound-alias`,
  `--period-start` / `--period-end`, `--require-preflight-pass` для
  clean_dump.
- Packager primary RETURN + sidecar по COL-R03-009 (exact file list /
  `00_STATUS.yaml`); exit ≠ 0 если primary отсутствует.
- L0 только side/opt-in; не Web handoff.
- `clean_dump` / collect под require-pass без
  `READ_ONLY_PREFLIGHT_PASS=YES` → exit ≠ 0, 0 API calls.
- Report/SCRIPTS_REPORT: `ARTIFACT_CLASS`, `PRIMARY_ARTIFACT`,
  `PRIMARY_SHA256`, `L0_SIDE_ARTIFACT`, `WEB_COLLECTOR_HANDOFF`,
  `CONTRACT_ID`; `archive_sha256` / PRIMARY_SHA256 == digest primary zip.
- Unit/fixture без live prod API.

**Non-Goals:**

- Live Owner-bot Job / kubectl cp как apply DoD (scripts lane follow-up)
- Объявление `READ_ONLY_PREFLIGHT_PASS` / Final Review из Job
- Stage B permanent CLEAN_DUMP collect / pagination
- API Master swagger map / invent URL / raw HTTP
- Cursor→prod WB; finance/write; upload в ChatGPT
- `battle_tested=YES`

## Architecture Decision References

- `openspec/decisions/scripts-wb-api-ops-stack/decision.md` — Job-only
  execution, existing `wb/api`, secret-strip, запрет Web PASS из ops-класса
- `openspec/decisions/orders-or-sales-reports-read-identity/decision.md` —
  ORDERS identity (не substitute); context для honest mapping gaps
- `openspec/decisions/wb-api-master-local-swagger-map/decision.md` —
  local swagger map authority; не invent URL
- **Proposed (this change):**
  `decisions/wb-readonly-contract-return-vs-l0/decision.md` — primary
  RETURN vs L0 side; RETURN redaction; honest REFUSED; clean_dump gate

Checklist lookup: accepted stack decision не разделял RETURN vs L0 →
proposed decision создан (не Architecture Decision Missing).

## Ownership & Placement

| Layer | Role |
|-------|------|
| **Owner (this change)** | `scripts/wb_api_readonly_ops` — CLI flags, contract packager, fail-closed gates, report fields, unit tests |
| **Allowed** | Existing `app/core/mp/wb/api` managers/adapters; secret-strip helpers; fixture-based packaging |
| **Scripts lane (not apply DoD)** | `/opsx-scripts` PLAN_RUN/RUN, known outputs, SCRIPTS_REPORT schema alignment, registry notes, live Job |
| **Forbidden** | Raw HTTP / invent URL; Cursor→prod WB; retrofit L0→PASS; shop_id/token/raw rows in RETURN; declaring Web PASS from Job |

Rationale: совпадает с `scripts-wb-api-ops-stack` + proposed RETURN-vs-L0.

## Decisions

1. **Один entrypoint, явный artifact-class**  
   Почему: два продукта (RETURN vs L0) без молчаливого default collect.
   Альтернатива: отдельный script — отвергнута (дублирует access/ceiling).

2. **Packager в `wb_api_readonly_ops`, не в `/opsx-scripts` command code**  
   Почему: contract shape — product/script behavior; scripts lane проверяет
   presence/sha после Job.  
   Альтернатива: только report wrapper без zip — отвергнута (COLLECTOR
   ждёт файл).

3. **Honest REFUSED всё равно собирает RETURN**  
   Почему: COL-R03-009 допускает REFUSED; COLLECTOR нужен пакет, не silent
   skip. Mapping gaps (ORDERS/STATISTICS/CARDS) → exact blockers; campaigns
   может PASS_MAP через existing promotion/count — без invent URL.

4. **SCRIPTS_REPORT имена: TZ + command compat**  
   Emit `L0_SIDE_ARTIFACT` и `WEB_COLLECTOR_HANDOFF` как в TZ; при
   необходимости зеркалить `SIDE_ARTIFACT` /
   `EXTERNAL_HANDOFF_READY` для текущего opsx-scripts schema (одинаковая
   семантика). Align command doc — optional scripts/process follow-up, не
   блокер packager.

5. **Apply DoD = unit green + CLI/packager; Job = Owner follow-up**  
   Почему: Cursor→prod forbidden; vault binding Owner-local.

## Risks / Trade-offs

- [Неверный состав RETURN] → reject в COLLECTOR → fixture exact file list +
  status field checks
- [L0 снова принят за handoff] → fail-closed primary gate + report fields
- [Sha mismatch] → sidecar и report digest от одного write path
- [Over-claim PASS_MAP] → only existing mapped GET; else exact REFUSED
  blocker
- [Schema field rename opsx-scripts] → dual emit / short process note; не
  блокирует RETURN

## Migration Plan

1. Implement CLI + packager + gates + tests (this change).
2. Optional: registry default note / opsx-scripts field alias.
3. Owner: `/opsx-scripts RUN GO` contract_preflight (Dilera vault).
4. Navigator: PRIMARY → Web COLLECTOR.
5. Rollback: не передавать `--contract`; прежний L0 collect path intact.

## Open Questions

- Formal `/opsx-evolution` increment link для packager (optional Owner).
- Нужен ли process-only align имён полей в `.cursor/commands/opsx-scripts.md`
  в том же PR или follow-up `/opsx-admin-command-fix-command-defects`.

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing
- [x] implementation layer matches decision
