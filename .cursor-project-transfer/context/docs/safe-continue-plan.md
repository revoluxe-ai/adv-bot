# Safe continue plan (read-only scan)

**Сгенерировано:** 2026-09-30 (vkita-pc, composer-2.5)  
**База:** `C:/Users/vkita/my_code/meta-repo/adv-bot` @ `stage`  
**Стратегия:** [chatgpt-strategy-adv-bot-6abd1faa.md](chatgpt-strategy-adv-bot-6abd1faa.md)  
**Процесс:** [opsx-working-instruction.md](opsx-working-instruction.md)  
**Правила collision:** shop-wide не стартовать без `READY_TO_START_OPSX`; DRR CPO ≠ `separate-auto-search-cpo`; CH migrations блокируют расширение CH в shop-wide до готовности control plane.

**Критерий auto-continue:** ровно один workstream с явным `NEXT_COMMAND` в durable receipt (verification JSON, `COMMAND_RECEIPT`, tasks с непротиворечивым gate) и без Owner-вопроса / collision.

**Итог скана:** **0** safe tracks → **ни одна** primary OPSX-команда не запускалась.

---

| workstream | worktree | change id | status | next command | auto-continue safe? | blocker |
| --- | --- | --- | --- | --- | --- | --- |
| Shop-wide campaign collection | `meta-repo/shop-wide-campaign-data-collection` | `shop-wide-campaign-data-collection` | **in-flight apply** (~6/36 tasks; dirty `wb_shop.py`, `env.sample`) | — (рано) | **нет** | Стратегия §4: preflight → `READY_TO_START_OPSX` до старта; collision с CH/`wb_shop.py`; `plan.receipt.json` есть (`PLAN_STATUS: ready`), но нет `NEXT_COMMAND`; §7–9 tasks открыты |
| Separate Auto/Search CPO | `meta-repo/fix-search-cpc` | `separate-auto-search-cpo` | **in-flight verify-prep** (36/39 tasks; dirty UI/CPO files) | tasks §8.6: `/opsx-verify mode=impl separate-auto-search-cpo` | **нет** | Открыты §8.3 (CH integration), §8.5 (scenario audit) **до** §8.6; не единственный однозначный receipt; изоляция от DRR соблюдена, но порядок tasks не закрыт |
| ClickHouse migrations control plane | `meta-repo/clickhouse-migrations-control-plane` | `clickhouse-migrations-control-plane` | **apply complete** (`TASKS_COMPLETE: 31/31`, reconcile 2026-09-30) | типично `/opsx-verify mode=impl clickhouse-migrations-control-plane` (GRAPH/apply spine) | **нет** | Нет поля `NEXT_COMMAND` в `verification/*.json` или tasks; несколько кандидатов на verify; shop-wide CH expansion всё ещё ждёт этот поток |
| AI Package v1 contract | `meta-repo/ai-package-v1-contract` | `ai-package-v1-contract` | **planning/apply boundary** (`APPLY_READY: no`; `OPSX_VERIFY_STATUS: IMPL_OK` 2026-09-27) | §10 apply/archive gates; не один receipt | **нет** | `TASKS_STATUS: PLANNING_READY`; §0.3 infra debt (openspec guard); §10.1–10.2 не закрыты; Owner GO на apply не в receipt |
| Scripts collector lifecycle | `meta-repo/adv-bot` (+ canonical `meta-repo/scripts`) | `scripts-collector-lifecycle-architecture` | **verify / merge-pending** (`verification/READY_FOR_REVERIFY.json`: `PASS_READY_FOR_MERGE`, blockers `[]`) | tasks §6.4: independent reverify (нет одной slash-строки в JSON) | **нет** | Canonical implementation на ветке `scripts` / worktree `scripts-fix`; не product workstream из стратегии; ambiguous с `stage` checkout |
| DRR → CPO economics | — | *(change не найден)* | **BLOCKED / not started** | новый change + отдельный чат (стратегия §5) | **нет** | Нет `openspec/changes/*drr*` в meta-repo; нельзя смешивать с `fix-search-cpc` |
| AI contracts v1 (`wt-ai-contracts-v1`) | — | *(worktree/change не найден)* | **BLOCKED** | `/opsx-new` / planning после Owner | **нет** | Стратегия: blocking gate до параллельных AI worktrees; каталога нет |
| OPSX command transfer | `meta-repo/adv-bot-full-command-transfer` | `feature/opsx-full-command-transfer` | **BLOCKED** (surface materialized, merge forbidden) | manifest: live runs / `opsx-doctor` (не начат без Owner GO) | **нет** | [adv-bot-transfer-holds.md](adv-bot-transfer-holds.md); не product merge; PR #26 вне scope |
| Shop NMID access scope | `meta-repo/shop-nmid-access-scope` | `shop-nmid-access-scope` | **planning / untracked** (`?? openspec/changes/shop-nmid-access-scope/`) | — | **нет** | Нет durable `NEXT_COMMAND`; dirty/untracked |
| Base `stage` checkout | `meta-repo/adv-bot` | *(multi-change tree)* | **dirty** (`ahead 161`; untracked bounded-verify commands) | — | **нет** | Не выделенный workstream; не auto-continue без Owner |

---

## Команда в этом hop

**Не выполнялась** (0 safe tracks).

## Следующий шаг Owner (если нужен один поток)

Выбрать один ряд таблицы и явно назначить primary command в чате, например:

- shop-wide: завершить preflight / collision map, затем **одна** команда на continue apply;
- fix-search-cpc: закрыть §8.3–8.5, затем `/opsx-verify mode=impl separate-auto-search-cpo` в `fix-search-cpc`;
- clickhouse: `/opsx-verify mode=impl clickhouse-migrations-control-plane` в dedicated worktree.
