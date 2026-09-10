# Что произошло

На overlay промобонусов живой leftover на кампании мог «пропасть» из ledger из‑за окна 90 дней. Overlay AND-stop (usable=false / консервативный M=1), хотя leftover на кампании ещё оставался, в том числе при пустом общем пуле.

# Что было сломано

`load_campaign_ledgers` применял `PROMO_LOOKBACK_DAYS` (90d) как cutoff к leftover success-tranches и spend. Транш с `remaining>0` и не истёкшим `expires_at`, но с `created_at` старше 90 дней, выпадал из кампанийного ledger. Overlay считал leftover исчерпанным — ложный stop.

# Почему это было проблемой

Кампания могла останавливать overlay и резать CPO/лимиты, пока на ней ещё лежал usable leftover. Это runtime-баг на пути shop-runner → auto_budget_watchdog → PromoStateService.refresh → Redis overlay.

# Что мы изменили

В `app/modules/auto_budget_manager/promo_ledger.py` leftover и spend читаются без 90d cutoff. Живой leftover держит `campaign_usable=true` вне окна 90 дней при `pool=0`. Окна allocation и spend выровнены (оба без cutoff на PG load). Окно UPD ingest не расширялось. FINDING-H2..H6 не трогали.

# Какие файлы изменены

- app/modules/auto_budget_manager/promo_ledger.py

## Изменения этого bug episode

- app/modules/auto_budget_manager/promo_ledger.py (uncommitted)

## Ранее существовавшие несвязанные изменения

Worktree уже был грязный до этого episode; Owner смотрит полный git diff, не только leftover-патч.

# Как мы проверили

RED: frozen node падал на старом cutoff. GREEN: тот же TEST_ID и тот же `TEST_CONTENT_SHA256` проходит после патча.

- `tests/unit/auto_budget_manager/test_promo_ledger.py::test_leftover_older_than_lookback_keeps_campaign_usable_when_pool_zero` — PASS (GREEN_CONFIRMED)
- adjacent `tests/unit/auto_budget_manager/test_promo_ledger.py` — 4 passed
- Bounded hunt CLEAR: клонов того же инварианта (SAME_INVARIANT) не найдено
- Learning: LOCAL_CASE_NOTE_ONLY, PROMOTION_DECISION=NONE — глобальные правила не активировались

# Что остаётся открытым на этом кейсе

FINDING-H2, FINDING-H3, FINDING-H4, FINDING-H5, FINDING-H6 — другие инварианты, backlog. Кейс не закрыт. ROOT-001 закрыт как closed_fixed / CLOSED_GREEN. Миссия кейса не complete.

# Что не изменяли

Git commit / push / PR / deploy из этой команды не делались. Alembic не применялся. RaisePlanOnPromobonuses не включался. FINDING-H2..H6 не закрывались и не claim-ились.

# Что проверить перед коммитом

Owner смотрит uncommitted git diff (в первую очередь `promo_ledger.py`) и сам решает, коммитить ли. Из этой команды коммит не создавать.

# Технические детали

CASE_ID=BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z
FINDING_ID=ROOT-001
STATUS=closed_fixed
FINDING_TERMINAL_KIND=CLOSED_GREEN
CASE_CLOSED=no
MISSION_COMPLETE=no
WORKTREE_STATUS=UNCOMMITTED_CHANGES_AWAITING_USER_REVIEW
COMMIT_CREATED=NO
FAMILY_STATUS=CLOSED_FIXED_VERIFIED
NEXT_COMMAND=/opsx-claim-next-bug case=BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z chat_label="SUP-PROMOBONUS-FIX-20260907"
