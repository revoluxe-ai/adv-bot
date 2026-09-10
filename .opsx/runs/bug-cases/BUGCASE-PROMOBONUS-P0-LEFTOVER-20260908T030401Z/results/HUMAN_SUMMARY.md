# Что произошло

На multi-tranche кампании overlay fraction f ошибочно считался как remaining/last_tranche.amount → f≈1 и M~1e6.

# Что было сломано

apply_spend_fefo использовал last tranche amount как знаменатель для f.

# Почему это было проблемой

Overlay multiplier взрывался; CPO/лимиты ломались на живом promo.

# Что мы изменили

f берётся из package percent (promo_amount/amount) через promo_fraction_from_amounts.

# Какие файлы изменены

- app/shared/domains/wb/utils/promo_accounting.py

## Изменения этого bug episode

- app/shared/domains/wb/utils/promo_accounting.py

## Ранее существовавшие несвязанные изменения

- (нет)

# Как мы проверили

RED/GREEN test_campaign_ledger_multi_tranche_fraction_uses_package_percent_not_leftover_over_last_tranche PASS; hunt CLEAR.

## Какие тесты прошли

pytest 1/1 PASS on frozen RED node

# Какие дополнительные проверки сделали

Bounded hunt CLEAR — SAME_INVARIANT siblings none.

# Что не изменяли

P1 not reopened; RaisePlanOnPromobonuses not enabled; no commit/push/deploy

# Оставшиеся риски

Owner must review uncommitted worktree.

# Что проверить перед коммитом

Owner reviews uncommitted promo_accounting.py diff

# Технические детали

CASE_ID=BUGCASE-PROMOBONUS-P0-LEFTOVER-20260908T030401Z FINDING_ID=P0-001 STATUS=closed_fixed FINDING_TERMINAL_KIND=CLOSED_GREEN FAMILY_STATUS=CLOSED_FIXED_VERIFIED
