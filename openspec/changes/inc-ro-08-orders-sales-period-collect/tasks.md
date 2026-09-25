# Tasks — inc-ro-08-orders-sales-period-collect

Owed scope (this change / `/opsx-apply`): **period collect + cursor follow**
для `ORDERS_OR_SALES_REPORTS_READ` на existing Reports stack (окно
`2026-07-04..2026-08-02` Europe/Moscow), finite ceiling, honest attestation,
unit/smoke без live WB; документированный invoke plan для `/opsx-scripts`.

Не включать в apply как blocked DoD:
- обязательный live Job / kubectl cp в момент apply (Supervisor may defer;
  capability + invoke plan — owed; live evidence — scripts lane follow-up);
- `battle_tested=YES`;
- закрытие Web PASS / RETURN / COL-R03-009.

Не включать вообще (FUTURE / OUT_OF_SCOPE): Stage B CLEAN_DUMP / accept;
swagger sync; API Master; token hardening; invent URL / raw HTTP;
Cursor→prod WB; другие семьи как DoD.

Evolution: `wb-safe-readonly-collect` / `INC-RO-08`.
Decisions: `decisions/REUSE.md` + accepted
`scripts-wb-api-ops-stack`, `orders-or-sales-reports-read-identity`.

## 1. Tests-first (characterization + period cursor)

- [ ] 1.1 Characterization: зафиксировать текущий Stage A ORDERS path
      (`next_page_followed=NO`, no cursor follow) как baseline — не ломать
      при добавлении period collect (spec: Stage A first-page path unchanged)
- [ ] 1.2 Добавить failing/target unit: `--mode collect` period path MUST
      запросить continuation / `lastChangeDate` когда mock pages дают next
      cursor (spec: Collect follows cursor within period window)
- [ ] 1.3 Добавить unit: finite ceiling → stop reason ceiling-hit (или
      equivalent), rows retained, не silent full-period success
      (spec: Ceiling stops pagination honestly; Distinct stop reasons)
- [ ] 1.4 Добавить residual/repeated-invocation unit: после ceiling stop
      повторный collect не заявляет silent full coverage без новых pages
      (spec: Targeted automated coverage for ORDERS period cursor collect)
- [ ] 1.5 Paired: orders OK + sales fail в period collect → PARTIAL + sales
      gap + orders evidence retained; orders fail → family non-success
- [ ] 1.6 Anti-substitution: funnel/fullstats/FBS по-прежнему не закрывают
      семью; period collect не invent URL / raw HTTP

## 2. Period collect + cursor orchestration

- [ ] 2.1 В `wb_api_readonly_ops` ORDERS family: для `--mode collect` включить
      cursor/`lastChangeDate` follow от `dateFrom=2026-07-04` с research end
      `2026-08-02` Europe/Moscow; Stage A/preflight оставить first-page
- [ ] 2.2 Пробросить cursor param через existing Reports adapter/manager
      **только если** ещё не проброшен; без regen client / invent URL
- [ ] 2.3 Dual finite ceiling (max pages и/или wall-time); stop reasons:
      ceiling | empty/no-continuation | error | window heuristic; attestation
      `DATE_FROM_CURSOR`, `next_page_followed`, stop reason в report
- [ ] 2.4 Orders + sales оба в period collect; shop_id только аргументом
      (Dilera / WB-TEST-CABINET-001); L0 archive path secret-strip, без Web
      PASS/RETURN claim (spec: Bound Dilera…; Owner-local L0…)
- [ ] 2.5 Обновить `MAPPING.md` / module docstrings (русский) со ссылкой на
      delta `wb-api-read-only-preflight` / INC-RO-08 period collect
- [ ] 2.6 Прогнать targeted unit:
      `poetry run pytest -m unit tests/unit/scripts/wb_api_readonly_ops/ -v`

## 3. Local smoke + scripts invoke plan

- [ ] 3.1 Узкий CLI/`--help` или import smoke entrypoint (без Cursor→prod WB)
- [ ] 3.2 Зафиксировать в change note / design-adjacent short plan pasteable
      `/opsx-scripts PLAN_RUN` и `RUN GO` для Dilera period collect (title из
      registry); **не** требовать live Job complete как apply checkbox
- [ ] 3.3 При необходимости обновить notes в `scripts/REGISTRY.md` по
      local evidence only — без `battle_tested=YES` и без ложного cluster claim

## 4. Evolution link + gates

- [ ] 4.1 Проверить card INC-RO-08 `LINKED_CHANGES` включает
      `inc-ro-08-orders-sales-period-collect` (через `/opsx-evolution` если
      нужно; не invent Future Increments)
- [ ] 4.2 `poetry run pyright-strict` на затронутые in-policy пути +
      `git diff --check`; pyrightconfig include hygiene для новых production `.py`
- [ ] 4.3 Self-check: нет Web PASS/RETURN/`contract_preflight`; нет Stage B
      CLEAN_DUMP; нет infinite pagination; нет raw HTTP / swagger regen /
      token hardening в diff; Stage A first-page intact
