## 1. Контракт и regression tests first

- [x] 1.1 Зафиксировать fixture exact audit identity и тесты, которые передают точные `shop_id`, cabinet, NMID, `size_id`, timezone и 14-дневное окно без silent widening.
- [x] 1.2 Добавить paired tests на отказ при identity mismatch, отсутствие A1 fallback и запрет unrelated collector/package substitution.
- [x] 1.3 Добавить тесты семантики `missing`, `null`, `unsupported`, `GAP`, `NULL` и `UNDEFINED`, включая нулевой и отсутствующий denominator.
- [x] 1.4 Добавить тесты, доказывающие отсутствие duplicate physical spend при overlapping direct/associated evidence и gap при небезопасной reconciliation.
- [x] 1.5 Добавить contract tests machine-readable output, human summary и decision block на согласованность confirmed/gap/partial/blocked статусов.
- [x] 1.6 Добавить regression tests нулевого write budget и конечного retry/timeout budget без live production WB API.

## 2. Identity-safe audit orchestration

- [x] 2.1 Реализовать в разрешённом scripts/Job-контуре валидацию immutable audit identity и построение current-day-inclusive 14-calendar-day period в заявленной timezone.
- [x] 2.2 Реализовать current-contour evidence collection для NMID/OFFER, AdvSetting, Auto, Search, прочих IDs, WB statuses, bot settings, CPO и limits с provenance и per-section status.
- [x] 2.3 Подключить orders/units/GMV collection через существующий Owner-bot access plane и `app/core/mp/wb/api`, сохранив accepted `ORDERS_OR_SALES_REPORTS_READ` identity и честную period attestation.
- [x] 2.4 Реализовать authoritative direct/associated attribution и topology как раздельные evidence classes; unsupported или недоказанная association должна оставаться gap без inference.
- [x] 2.5 Реализовать FBO/FBS/TOTAL stock reporting с отдельным GAP/unsupported статусом для каждой неподтверждённой view.

## 3. Reconciliation и output contract

- [x] 3.1 Реализовать provenance-aware canonical physical-spend reconciliation с overlap protection и отказом от glue inference.
- [x] 3.2 Реализовать totals, CPO и DRR только для identity-safe period-compatible evidence с корректными `NULL`/`UNDEFINED` denominator semantics.
- [x] 3.3 Реализовать versioned machine-readable output contract со схемой identity, period, evidence, provenance, gaps, statuses, totals, stock и decision block.
- [x] 3.4 Реализовать human summary, производимый из тех же normalized facts, без добавления сведений, отсутствующих в machine-readable output.
- [x] 3.5 Добавить публичные docstrings и domain documentation для новых модулей, классов и методов согласно repository documentation policy.

## 4. Verification и bounded rollout

- [x] 4.1 Выполнить targeted unit/contract suite и static проверку write-path до любого Job execution.
- [x] 4.2 Проверить соответствие реализации accepted decisions и proposed strict-audit evidence decision; unresolved placement или conflict должен остановить apply/rollout.
- [x] 4.3 Подтвердить, что запуск возможен только в Owner-bot Job runtime, с finite run ceiling, secret-safe outputs и без local Cursor→production WB calls.
- [x] 4.4 Выполнить только явно разрешённый bounded read-only Job после прохождения тестов и проверить output contract; не менять WB/DB/Redis/Excel/campaign/shared state. Evidence (independent verify): Job `ops-script-strict-nmid-186069402-20260920t1048` namespace `prod-adv-bot`, execution SHA `b3be48bcf2b74ff6489d53c2d9cee435ccab5896`, receipt `.tmp/PROKRAFT_SINGLE_NMID_186069402/SCRIPTS_REPORT_t1048_handoff.md`, primary `.tmp/PROKRAFT_SINGLE_NMID_186069402/STRICT-SINGLE-NMID-AUDIT.json` SHA-256 `8c5414134cb1531f864f7e539c5440100b2bb7d9106b8ba2bd58ac0047f75e57`, `validate_output_contract` OK, `write_budget.writes=0`, `decision.status=PARTIAL` (supersedes legacy failed `SCRIPTS_REPORT.md`).
