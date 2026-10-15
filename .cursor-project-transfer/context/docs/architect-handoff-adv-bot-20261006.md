# Handoff для чата-архитектора — adv-bot (серия разработок)

**Дата снимка:** 2026-10-06 (UTC, Cursor Project coordinator)  
**Репозиторий:** `revoluxe-ai/adv-bot`  
**Authority `origin/stage`:** `d2166b2d805b27a6656f46c6ccb8e56066b4e888` (после revert [#451](https://github.com/revoluxe-ai/adv-bot/pull/451); дерево согласовано с чистым baseline post-bootstrap)

**Режим работы:** OPSX, command-only product changes; merge/deploy/production writes — только явный Owner GO. Координация исполнения — Cursor Project (штаб adv-bot); Web-чат — архитектура/стратегия, не диспетчер промптов в feature-чаты.

---

## 1. Что закрыто / не переоткрывать

- AI Package keyword performance history — merged, archived.
- AI Package full export (базовый) — на stage, closed.
- Cursor Project bootstrap [#448](https://github.com/revoluxe-ai/adv-bot/pull/448) — merged.
- Campaign settings history / snapshot — closed на stage.
- Инцидент campaigns [#447](https://github.com/revoluxe-ai/adv-bot/pull/447) — merged в stage; выкат `wb-sky-bot` через CAS — отдельный ops-трек (worker offline на момент снимка).

---

## 2. Активные product changes (draft PR, не в stage)

### AI Package / экспорт

| Change | PR | HEAD (draft) | Статус | Следующий гейт |
|--------|-----|--------------|--------|----------------|
| `ai-package-full-export-contract-repair` | [#450](https://github.com/revoluxe-ai/adv-bot/pull/450) | `19ec4bf5a` | Реальный ZIP на HOME-PC: validate PASS, GAP coverage | Owner GO на merge (не смержен) |
| `ai-package-multi-window-analysis` | [#453](https://github.com/revoluxe-ai/adv-bot/pull/453) | `e55d94cdd` | Реализация domain layer; formal scenario cert **26/26 PASS**; DoD verify **IMPL_OK** | `/opsx-pyright-strict-coverage`, затем independent verify; merge — NO без GO |
| `telegram-ai-package-export` | [#454](https://github.com/revoluxe-ai/adv-bot/pull/454) | `f33d32587` | Кнопка в shop menu → canonical `PackageZipAssembler`; unit tests green на опубликованном HEAD | Review/merge — NO; параллельно был незапушенный локальный коммит `381fb1d2` на другом worker — не считать authority до push |

**Семантика multi-window (planning в [#453](https://github.com/revoluxe-ai/adv-bot/pull/453)):** `package_cutoff_date` ≠ source completeness; `source_complete_through` отдельно; shop-wide spend / SHOP_DRR fail-closed; CPO/DRR DIRECT/LINKED и shop GMV **заблокированы** до attribution/common sales.

### Control plane / settings

| Change | PR | HEAD | Статус | Следующий гейт |
|--------|-----|------|--------|----------------|
| `campaign-settings-changeset-contract` | [#449](https://github.com/revoluxe-ai/adv-bot/pull/449) | `bf0abd01a` | `ChangeSetV1` validation, pre-I/O preflight, semantic order; **Apply не реализован** | Independent read-only verify на `bf0abd01` (блокировались stale checkout / DNS на cloud) |

**Planning (код не пишем):** [changeset apply authority](/cursor/stores/self/docs/changeset-apply-authority-planning.md) — Apply V1 только PostgreSQL policy, без WB HTTP.

### MCP read interface

| Change | PR | HEAD | Статус | Следующий гейт |
|--------|-----|------|--------|----------------|
| `wb-sky-mcp-read-interface` | [#452](https://github.com/revoluxe-ai/adv-bot/pull/452) | `fb5410ad2` | READ_ONLY tools; OAuth/Telegram consent; scenario plan `SCPV1-f0d1412a12fa9174`; PG gaps **TEST_ONLY** — provider tests authored **локально, не запушены** | HOME-PC: Docker + `/opsx-test-env`, новый re-audit, новый `AUTHORIZE_ONE_LIVE_RUN`, затем certify; **не merge** |

### Ветки без merge в stage

| Change | Ref | Статус |
|--------|-----|--------|
| `separate-auto-search-cpo` | `f6c18bb76` (ветка) | Статика green; live ClickHouse cert не снят (HOME-PC) |
| `campaign-attribution-facts` | planning | [План](/cursor/stores/self/docs/campaign-attribution-facts-planning.md); grain `shop+adv+date+app+nm`; блокирует DIRECT/LINKED CPO/DRR в multi-window |

---

## 3. Принятые architecture decisions (серия)

- **Exporter ownership:** Telegram не authority v1 export; узкое **Accepted** расширение для [#454](https://github.com/revoluxe-ai/adv-bot/pull/454): shop UI MAY call `PackageZipAssembler` as transport adapter после shop auth + read-only `shop_id` resolve.
- **ChangeSet V1:** canonical `app/modules/wb_sky_control_plane`; fail-closed validation; no apply in #449 scope.
- **MCP:** Streamable HTTP, read-only tool surface; ChatGPT CIMD OAuth repair (`none` when supported).

---

## 4. Блокеры и риски

1. **MCP #452:** нет provider receipt (live PG run failed — no Docker in cloud); uncommitted tests; одноразовое live authorization израсходовано.
2. **#449:** independent verify не выполнен на canonical HEAD (environment).
3. **#453:** merge readiness blocked до pyright-strict-coverage + `/opsx-verify` (full package pyright — 7 pre-existing errors вне analysis layer, не regression сценариев).
4. **#450:** ждёт merge decision после real export acceptance.
5. **Attribution facts:** planning готов, implementation не стартовал — держит shop-level economics в multi-window.
6. **Deploy:** post-#447 CAS `wb-sky-bot` — ops lane; self-hosted worker не всегда online.
7. **Full AI Package acceptance (legacy track):** PACKAGE_SUMMARY/join/determinism — FAIL в отчёте; отдельно от #450 repair.

---

## 5. Зависимости (для архитектора)

```text
campaign-attribution-facts (planning)
  └─ blocks: DIRECT/LINKED CPO/DRR, numeric SHOP_DRR в multi-window (#453)

#449 ChangeSet validate
  └─ precedes: apply authority (future), settings write path

#450 export repair
  └─ enables: внешний AI / полный ZIP contract; связан с Telegram #454 (transport only)

#452 MCP read
  └─ depends: PG provider tests + formal certify; не блокирует #453 напрямую

#453 multi-window
  └─ can merge после verify независимо от attribution для nominal leg metrics;
     shop-wide / DRR / direct-linked — fail-closed until facts
```

---

## 6. Что Owner не делал (явно)

- Merge draft #449, #450, #452, #453 в `stage`.
- Production deploy / WB writes / PG business writes в рамках этих changes.
- Повторный live PG run для MCP после ERROR receipt без нового GO.

---

## 7. Рекомендуемый фокус архитектора

1. Приоритет merge-очереди: #450 vs #453 vs #449 vs #452 vs #454 — с учётом зависимостей и готовности гейтов.
2. Порядок включения **attribution facts** относительно multi-window и CPO/DRR narrative.
3. MCP certify path: local test DB policy vs staging (forbidden без GO).
4. Единый narrative AI control loop ([gap report](/cursor/stores/self/docs/ai-control-loop-gap-report.md)) — без reopening merged export/history.

---

*Источник операционного статуса: Cursor Project store `notes.md` + worker reports 2026-10-06.*
