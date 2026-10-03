## Context

После INC-RO-06/07 семья `ORDERS_OR_SALES_REPORTS_READ` в
`wb_api_readonly_ops` работает как Stage A: `dateFrom` на старт пилотного
окна, по одной first page для supplier orders и supplier sales,
`next_page_followed=NO`, period model `DATE_FROM_CURSOR`. Live Job уже
доказал реальные rows на first page (INC-RO-07).

INC-RO-08 owed: period-covered collect по окну
`2026-07-04..2026-08-02` Europe/Moscow с follow cursor/`lastChangeDate`
при finite page/time budget и честной attestation stop reason → Owner-local
L0 research zip (не Stage A smoke).

Stakeholders: implementer (cursor loop + attestation + unit/smoke);
Owner/scripts lane для Job invoke. Constraints: `READ_ONLY_NO_MUTATION`,
no invent URL, reuse generated Reports + identity decision; Cursor→prod WB
запрещён.

## Evolution Context

- **Title (STAR_ID):** Безопасный постоянный сбор WB API-данных
  (`wb-safe-readonly-collect`)
- **INCREMENT_ID:** `INC-RO-08`
- **CURRENT_INCREMENT:** ORDERS_OR_SALES_REPORTS_READ collect with
  cursor/pagination over `2026-07-04..2026-08-02` Europe/Moscow for Дилера /
  WB-TEST-CABINET-001 → Owner-local L0 research zip with real rows (not
  Stage A first page)
- **CONTRIBUTION_TO_NORTH_STAR:** period-covered ORDERS/sales research dump;
  first-page smoke alone is not enough for research over COL-R03 window
- **CARD_PATH:** `openspec/evolution/wb-safe-readonly-collect.md`

Как design уважает forward-compat без Future Increments:

- Calls только через existing generated Reports + narrow adapters/managers
  (не raw HTTP, не swagger sync / API Master / token hardening).
- Period attestation остаётся `DATE_FROM_CURSOR` (не classic exact start+end).
- Finite page/time ceiling обязателен; Web PASS / RETURN /
  `READ_ONLY_PREFLIGHT_PASS` / CLEAN_DUMP **не** объявляются (INC-RO-04).
- L0 research archive остаётся расширяемым к будущему Web CLEAN_DUMP без
  требования L2 в этом increment.
- Live Job evidence через `/opsx-scripts` планируется; Supervisor policy
  может отложить live run — capability + invoke plan всё равно owed в
  артефактах/apply, но live Job не блокирует apply-ready артефактов.

## Goals / Non-Goals

**Goals:**

- В `--mode collect` для семьи `ORDERS_OR_SALES_REPORTS_READ` follow
  pagination/`lastChangeDate` от `dateFrom=2026-07-04` до покрытия окна
  `2026-07-04..2026-08-02` Europe/Moscow **или** честного stop
  (ceiling | empty page | API error).
- Attestation: `next_page_followed`, stop reason, period model, counts
  ORDERS и/или sales; не silent yesterday→today.
- Bound «Дилера» / `WB-TEST-CABINET-001` только аргументом Job/`--shop-id`.
- Targeted unit/smoke на cursor loop + ceiling без live prod WB.
- Документированный `/opsx-scripts` invoke plan для Job + L0 zip delivery.

**Non-Goals:**

- COL-R03-009 RETURN / `contract_preflight` / Web COLLECTOR
- Stage B CLEAN_DUMP / accept / `READ_ONLY_PREFLIGHT_PASS`
- Другие семьи как DoD этого change
- Swagger sync (INC-RO-02), API Master, token hardening (INC-RO-05)
- Invent URL / raw HTTP; finance/mutation; Cursor→prod WB
- Бесконечный pagination без ceiling
- Обязательный live Job в момент apply-ready артефактов (Supervisor may
  defer; evidence path всё равно описан)

## Architecture Decision References

- `openspec/decisions/scripts-wb-api-ops-stack/decision.md` — Job-only
  execution, existing `wb/api`, finite retries + upper run ceiling,
  secret-strip L0, `READ_ONLY_NO_MUTATION`
- `openspec/decisions/orders-or-sales-reports-read-identity/decision.md` —
  identity ORDERS = statistics-api supplier orders/sales; honest
  dateFrom/cursor; Stage A first-page ≠ period-collect follow; запрет
  funnel/FBS/fullstats substitute
- Change-local lookup: `decisions/REUSE.md` — **Architecture Decision Missing**
  нет; новый proposed decision не нужен

## Ownership & Placement

| Layer | Role |
|-------|------|
| **Owner (this change)** | `scripts/wb_api_readonly_ops` — period collect orchestration, cursor loop, ceilings, report/attestation; узкое расширение Reports adapter/manager **только** если нужен проброс cursor/`lastChangeDate` параметра уже существующего GET |
| **Allowed** | Existing generated Reports client; `ReportsManager` / adapter; unit tests under `tests/unit/scripts/wb_api_readonly_ops/` (и смежные); MAPPING attestation update |
| **Scripts lane (planned invoke)** | `/opsx-scripts PLAN_RUN` / `RUN GO` script=`wb_api_readonly_ops` (или registry title), `--mode collect`, `--shop-id` Dilera/`WB-TEST-CABINET-001`, period args; Job → `kubectl cp` L0 zip |
| **Forbidden** | Raw HTTP / invent statistics URL; funnel/search-report/fullstats/FBS as ORDERS; Cursor→prod WB; Web PASS/RETURN; infinite pagination; mass swagger regen |

Rationale: identity и stack ownership уже accepted; INC-RO-08 добавляет
режим period+cursor в orchestration, не меняя identity семьи и не вводя
новый client.

## Decisions

1. **Period collect — отдельный режим поведения от Stage A**  
   Preflight/Stage A сохраняет first-page / `next_page_followed=NO`.
   `--mode collect` для ORDERS family включает cursor follow.  
   Альтернатива: всегда paginate — отвергнута (ломает Stage A attestation
   и identity Forbidden про «pagination under guise of first page»).

2. **Честная модель периода: `DATE_FROM_CURSOR`, не exact start+end**  
   API end date отсутствует как classic range; окно
   `..2026-08-02` — research target / stop heuristic (cursor time /
  lastChangeDate vs window end), не claim «API вернул exact closed range».  
   Альтернатива: silent claim start+end — запрещена identity decision.

3. **Finite dual ceiling: max pages + max wall time (или equivalent budget)**  
   Исчерпание → stop reason `CEILING_HIT` + PARTIAL/honest attestation;
   накопленные rows сохраняются в L0.  
   Альтернатива: только page count или только time — допустимы как
   реализация dual budget, но «без ceiling» запрещено.

4. **Orders и sales оба в period collect**  
   Как Stage A: оба GET; раздельные cursor loops/counts; failure orders →
   non-success семьи; sales fail при OK orders → PARTIAL + gap.  
   Альтернатива: orders-only period — отвергнута (ломает family contract
   INC-RO-07).

5. **Не regen Reports client «на всякий случай»**  
   Reuse existing generated client; adapter расширяется только если
   cursor param ещё не проброшен.  
   Альтернатива: INC-RO-02 swagger sync — out of scope.

6. **Live Job — scripts lane; apply owns capability**  
   Apply реализует code + unit/smoke + invoke plan note.
   Live `/opsx-scripts RUN GO` evidence — Supervisor/scripts; deferred Job
   не блокирует apply-ready артефактов.

### Planned `/opsx-scripts` invoke (evidence path)

```text
/opsx-scripts PLAN_RUN script=<WB readonly ops title> args=--mode collect --shop-id <Dilera|WB-TEST-CABINET-001> --date-from 2026-07-04 …
/opsx-scripts RUN GO script=<same> args=…
```

Ожидаемые outputs: L0 research zip (+ sha256) с ORDERS и/или sales rows;
attestation `next_page_followed` / stop reason / period model в report.
Точный registry `title` резолвится из `scripts/REGISTRY.md` на scripts lane.

## Risks / Trade-offs

- [Risk] Cursor loop hang / rate-limit → Mitigation: dual finite ceiling +
  reuse stack retries; stop with honest `CEILING_HIT`.
- [Risk] Window end mis-attested as exact API range → Mitigation: keep
  `DATE_FROM_CURSOR` in report; document stop heuristic.
- [Risk] Empty pages mid-window mistaken for period complete → Mitigation:
  empty-page stop reason distinct; unit covers residual/repeated invoke.
- [Risk] Live Job deferred → Mitigation: apply-ready без live Job; evidence
  remains scripts/Supervisor follow-up, not silent Web PASS.
- [Risk] Scope creep into RETURN/CLEAN_DUMP → Mitigation: explicit Non-Goals
  + Evolution OUT_OF_SCOPE.

## Migration Plan

1. Implement period+cursor path behind collect mode; Stage A unchanged.
2. Unit/smoke green without live WB.
3. Optional: `/opsx-scripts` Job when Supervisor authorizes.
4. Rollback: disable period-follow flag/path; Stage A first-page remains.

## Open Questions

- Точные числовые defaults max pages / wall-time ceiling — выбрать при
  apply по существующим Job timeouts / WB rate limits (не блокирует design).
- Точный CLI flag surface (`--period-end`, collect-depth enum) — apply
  выбирает минимальный UX, совместимый с текущим `cli.py`.

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing (не нужен; см. `decisions/REUSE.md`)
- [x] implementation layer matches decision
