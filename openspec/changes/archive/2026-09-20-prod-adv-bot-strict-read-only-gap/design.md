## Context

Это standalone change для generic bounded single-NMID audit. Текущая
`wb-api-read-only-preflight` покрывает семейства API и их доступность, но не
гарантирует строгую identity, authoritative attribution/topology, отсутствие
двойного physical spend или единый decision-ready output для одного NMID.

Вход audit фиксирует `shop_id`, cabinet, `nmid`, `size_id` и timezone. Для
пилотной проверки используются `5586b2ff-449c-4151-9518-60f46d32b7d9`, `573`,
`186069402`, `305698863`, `Europe/Moscow`; эти значения являются примером
входа, а не hardcode capability. Окно — 14 календарных дней, включая текущий
день, в локальной timezone.

Поток должен выполняться только в Owner-bot Job-контуре. Локальный агент
планирует и проверяет контракт, но не вызывает production WB API и не меняет
WB, DB, Redis, Excel, кампании или shared infrastructure.

## Goals / Non-Goals

**Goals:**

- Fail-closed проверка точной audit identity до любого сбора.
- Раздельные evidence records для current contour, orders/units/GMV,
  physical spend, direct/associated attribution и stock.
- Authoritative-only topology/association и provenance каждого значения.
- Единая reconciliation-модель без физического double count.
- Явная семантика `NONE`, `GAP`, `missing`, `null`, `unsupported`, `NULL` и
  `UNDEFINED`.
- Машинный контракт, human summary и decision block, пригодные для
  последующей проверки и targeted tests.
- Конечный retry/run budget и нулевой write budget.

**Non-Goals:**

- Реализация конкретного Job, production-кода или live run в этом change.
- ProKraft-specific logic, A1 fallback, multi-NMID fan-out или campaign
  mutation.
- Утверждение Web PASS/CLEAN_DUMP.
- Вывод association/topology по догадке, glue inference или implicit
  denominator.
- Расширение существующего `wb-api-read-only-preflight` requirements.

## Architecture Decision References

- `openspec/decisions/scripts-wb-api-ops-stack/decision.md` — scripts/Job
  ownership, existing `app/core/mp/wb/api` stack, finite retries and
  `READ_ONLY_NO_MUTATION`.
- `openspec/decisions/orders-or-sales-reports-read-identity/decision.md` —
  authoritative supplier orders/sales identity, statistics Reports stack and
  honest period attestation.
- `openspec/decisions/strict-single-nmid-audit-evidence/decision.md`
  — **Accepted** reusable ownership, evidence invariant, `PARTIAL` vs `BLOCKED`
  semantics for strict audit.

Context-first lookup выполнен: сначала прочитан `openspec/decisions/index.md`,
затем declared applicable accepted decisions и
`strict-single-nmid-audit-evidence`. Decision **Accepted** (registry +
change artifact) closes identity-safe evidence/reconciliation invariant for
archive verification.

## Ownership & Placement

Owner layer — operator orchestration и output contract в `scripts/`, запускаемые
через `/opsx-scripts` Job. Доступ к кабинету и WB API остаётся в существующем
Owner-bot access plane и `app/core/mp/wb/api`; audit orchestration не создаёт
новый transport или второй access plane.

Разрешённые слои:

- scripts/Job orchestration, identity validator, bounded collector coordinator;
- существующие WB managers/adapters/generated clients;
- pure normalization/reconciliation и report serialization;
- targeted unit/contract tests с fake responses.

Запрещённые слои и пути:

- local Cursor → production WB API;
- raw HTTP client, invent URL или новый бесконечный retry;
- WB/DB/Redis/Excel/campaign/shared-infrastructure writes;
- unrelated collector/package или A1 fallback;
- product paid automation paths и Web acceptance gates.

Такое размещение совпадает с accepted scripts ownership decision; proposed
evidence decision добавляет только недостающую domain invariant часть:
точная identity, provenance, authoritative association и canonical
physical-spend representation.

## Decisions

### 1. Сначала валидировать identity, затем собирать evidence

Контекстом каждого source request является immutable tuple
`shop_id/cabinet/nmid/size_id/timezone/window`. Несовпадение или отсутствие
любого обязательного элемента останавливает соответствующую ветку как
`GAP`/blocked; подмена входа недопустима.

### 2. Разделить discovery, collection и reconciliation

Сначала фиксируется current contour и topology evidence, затем независимо
собираются orders/economics/stock, после чего reconciliation формирует totals.
Это не позволяет успешному одному источнику скрыть gap другого и облегчает
проверку provenance.

### 3. Период описывать по реальной семантике источника

Для `ORDERS_OR_SALES_REPORTS_READ` применяется accepted Reports identity и
attestation `dateFrom`/cursor. Если источник не поддерживает точное
14-дневное окно, результат не расширяется glue inference: поле получает GAP с
описанием фактически покрытого периода.

### 4. Канонизировать physical spend до расчёта totals

Каждая spend evidence имеет source, scope, period, identity и overlap key.
Reconciliation выбирает одну canonical representation; overlapping records
не складываются повторно. При невозможности безопасно reconciliate total
получает GAP/UNDEFINED, а не приблизительное число.

### 5. Считать производные только при валидном знаменателе

CPO и DRR получают числовой результат только если numerator и denominator
подтверждены и совместимы по периоду/identity. Нулевой denominator даёт
`UNDEFINED`, отсутствующий или null source — соответственно `missing`/`NULL`,
unsupported capability — `unsupported`; значения не подменяются нулём.

### 6. Сделать output contract первым классом

Machine-readable output содержит schema/version, audit identity, period,
per-section status, evidence provenance, gaps, totals, denominator states,
stock split and decision block. Human summary строится из тех же normalized
records и не может добавлять факты, отсутствующие в machine output.

## Risks / Trade-offs

- [Risk] API family покрывает не весь календарный период →
  [Mitigation] period attestation и GAP вместо ложного exact total.
- [Risk] похожие IDs создают cross-contour contamination →
  [Mitigation] immutable identity tuple, exact-match tests и no-fallback gate.
- [Risk] direct/associated sources overlap →
  [Mitigation] provenance + overlap key + single canonical physical total.
- [Risk] много `GAP` делает отчёт менее удобным →
  [Mitigation] human decision block явно разделяет confirmed, NONE, GAP и
  `UNDEFINED`, не скрывая неопределённость.
- [Risk] Job зависает на внешнем API →
  [Mitigation] existing finite retries, per-source timeout и whole-run ceiling.

## Migration Plan

В рамках этого change только планирование и artifact creation; rollout не
выполняется. Следующий implementation должен:

1. реализовать capability в разрешённом scripts/Job и existing WB API stack;
2. добавить targeted unit/contract tests до любого live Job;
3. провести static/read-only preflight, убедившись в нулевом write path;
4. выполнить только явно разрешённый bounded Job и проверить output contract.

Rollback для реализации — отключить entrypoint/Job capability и удалить только
её локальные output artifacts; production/shared state не требует rollback,
поскольку writes запрещены.

## Open Questions disposition

Все бывшие Open Questions имеют явную disposition; implicit archive blockers
сняты. Evidence-plane completeness (reader/runtime errors в t1048) не входит в
acceptance criterion bounded contract — см. scope boundary ниже.

| Question | Disposition | Answer / follow-up | Location |
|----------|-------------|-------------------|----------|
| Authoritative endpoint families for direct/associated attribution | `DEFERRED_TO_FOLLOWUP` | t1048: attribution/orders sections GAP + RuntimeError; bounded contract требует honest GAP, не выбор endpoint family. Follow-up: evidence-plane hardening для Owner-bot readers (отдельный track, не этот change). | `design.md` (here); `openspec/decisions/strict-single-nmid-audit-evidence/decision.md` |
| Authoritative FBO/FBS/TOTAL stock source | `DEFERRED_TO_FOLLOWUP` | t1048: stock `unsupported`/GAP без authoritative view; audit MUST NOT invent stock. Follow-up: identify/implement stock reader when source proven. | same |
| Canonical overlap key per physical-spend source | `DEFERRED_TO_FOLLOWUP` | Reconciliation invariant принят (single canonical total, no double count); per-source overlap key catalog не доказан runtime evidence. Follow-up: document keys per wired source when spend readers stabilize. | `openspec/decisions/strict-single-nmid-audit-evidence/decision.md` |
| Decision block `PARTIAL` vs `BLOCKED` | `RESOLVED_IN_THIS_CHANGE` | `PARTIAL`: valid identity + output contract + `writes=0` with evidence gaps. `BLOCKED`: fail-closed contract violations only (identity/substitution/write/invalid contract/missing provenance). | `openspec/decisions/strict-single-nmid-audit-evidence/decision.md`; delta spec scenarios below |

## Scope boundary (acceptance)

This change proves strict single-NMID identity, read-only bounded execution,
injected Owner-bot readers, explicit GAP/`PARTIAL` behavior, artifact handoff
validation and zero write budget. It does **not** require every Owner-bot
reader to succeed without runtime errors unless spec explicitly made that an
acceptance criterion (it did not). Cross-loop PG / reader errors remain a
separate follow-up track.

Bounded Job evidence (task 4.4): `SCRIPTS_REPORT_t1048_handoff.md` supersedes
legacy failed `SCRIPTS_REPORT.md`.

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing
- [x] implementation layer matches decision
