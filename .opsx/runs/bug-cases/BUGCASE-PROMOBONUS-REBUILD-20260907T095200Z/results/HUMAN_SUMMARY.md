# Что произошло

FINDING-006 закрыт как ложное срабатывание (`closed_false_positive` / Route C / `FALSE_POSITIVE`). Review описал контракт журнала WBAutoBudgetTopUp (только бот-пополнения) как дефект: ручные seller-portal депозиты там не видны. Это не баг: журнал — SoT бот-аллокаций; remaining кампании = verified bot allocations минус UPD spend; неиспользованный wallet promo остаётся на live WB cashbacks[] / pool_usable. Hunt CLEAR, sibling нет. Residual intake пуст (пункт 6 был последним). Очередь исчерпана. CASE закрыт (`CASE_STATUS=CLOSED`, `MISSION_COMPLETE=yes`).

# Что было сломано

Ничего в production. Сообщённый эффект «journal-only-bot / manual deposits invisible» — документированный контракт таблицы, не пропущенный persist seller-portal депозитов.

# Почему это не дефект

WBAutoBudgetTopUp пишет только `_create_topup_entry` бота. `load_success_tranches` читает success-строки с `promo_amount>0`. Ручные депозиты вне этого журнала. Unused wallet promo — live WB cashbacks[], не строки журнала.

# Что мы изменили

В этом hop — только артефакты closure. Production / tests не менялись. Git commit / push / deploy не выполнялись. `COMMIT_CREATED=NO`. `USER_ACTION_REQUIRED=REVIEW_DIFF_AND_DECIDE_COMMIT`. `WORKTREE_STATUS=UNCOMMITTED_CHANGES_AWAITING_USER_REVIEW`.

# Какие файлы изменены

## Артефакты closure (этот hop)

- `.opsx/runs/bug-cases/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/results/OWNER-CLOSURE-FINDING-006.md`
- `.opsx/runs/bug-cases/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/results/HUMAN_SUMMARY.md`
- `.opsx/runs/bug-cases/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/CASE.md`
- `.opsx/runs/bug-cases/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/LEDGER.md`
- `.opsx/runs/bug-cases/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/findings/FINDING-006.md`
- `.opsx/runs/bug-cases/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/INDEX.md`
- `.opsx/runs/bug-cases/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/results/ROUTE-TRACE.jsonl`

## Уже закрыто отдельно (не этот hop; не переоткрывалось)

- ROOT-001 Telegram rec-bid overlay: `closed_fixed`. Evidence: `results/OWNER-CLOSURE-ROOT-001.md` (не перезаписывался).
- FINDING-002 + HC-001 pool-fail false-empty Redis: `closed_fixed`. Evidence: `results/OWNER-CLOSURE-FINDING-002.md` (не перезаписывался).
- FINDING-003 90d leftover cutoff: `closed_false_positive` / Route C. Evidence: `results/OWNER-CLOSURE-FINDING-003.md` (не перезаписывался).
- FINDING-004 + HC-FINDING-004-STALE-TEST FEFO expired-spend: `closed_fixed` / INTEGRATED. Evidence: `results/OWNER-CLOSURE-FINDING-004.md` (не перезаписывался).
- FINDING-005 leftover fraction tranche.amount: `closed_fixed`. Evidence: `results/OWNER-CLOSURE-FINDING-005.md` (не перезаписывался).

## Ранее существовавшие несвязанные изменения

Они не анализировались и не входили в решение FINDING-006.

# Как мы проверили

FINDING-006: CLASSIFIER FALSE_POSITIVE / ROUTE_C. Hunt CLEAR (`CANDIDATES=[]`). FANIN: `FANIN_READY`, `HARD_BLOCK_READY=false` (gate PASS), residual empty. Learning: `evaluate_closure_learning_gate` PASS, `LOCAL_CASE_NOTE_ONLY` / `COMPLETE` / `RESOLVED_NO_PROMOTE`. Все prior findings уже terminal. Очередь пуста.

# Какие дополнительные проверки сделали

Scan `findings/` на `STATUS ∈ {open_candidate, OPEN_CANDIDATE}` + SAME_INVARIANT: пусто. Семьи ROOT-001 / FINDING-002 / FINDING-003 / FINDING-004 / FINDING-005 не переоткрывались.

# Что не изменяли

`results/FANIN.md`, `family/LEARNING_DECISION.json`, OpenSpec, `app/**`, `tests/**`, `intakes/`. Git commit / push / deploy не выполнялись. FINDING-007 не создавался. Checkpoint не финализировался.

# Оставшиеся риски

Нет residual intake. CASE закрыт. Worktree всё ещё uncommitted. Owner смотрит diff и решает, делать ли commit.

# Что проверить перед коммитом

Production diff этого hop нет (closure only). Не включайте несвязанные грязные файлы. Затем Owner решает, делать ли commit.

NEXT_ACTION: none (CASE CLOSED; RECOVERY_CLASS=TERMINAL)

SOFT:

```text
/opsx-bug-debt-board case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
```

# Технические детали

- CASE_ID: `BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z`
- FINDING_ID: `FINDING-006`
- SIBLING: none (HUNT_RESULT=CLEAR)
- CLASSIFICATION: `FALSE_POSITIVE`
- CHOSEN_ROUTE: `ROUTE_C`
- FINDING_STATUS: `closed_false_positive`
- FINDING_TERMINAL: `yes`
- FINDING_TERMINAL_KIND: `CLOSED_FALSE_POSITIVE`
- EPISODE_TERMINAL: `FALSE_POSITIVE`
- CLOSURE_STATUS: `CLOSED_FALSE_POSITIVE`
- CASE_STATUS: `CLOSED`
- LEAVE_OPEN_REASON: (empty)
- RESIDUAL_INTAKE_ITEMS: (empty)
- OPEN_SAME_INVARIANT_CANDIDATES: `NONE`
- HARD_BLOCK_READY: `PASS`
- LEARNING_VERDICT: `LOCAL_CASE_NOTE_ONLY`
- PROMOTION_DECISION: `RESOLVED_NO_PROMOTE`
- WORKTREE_STATUS: `UNCOMMITTED_CHANGES_AWAITING_USER_REVIEW`
- COMMIT_CREATED: `NO`
- USER_ACTION_REQUIRED: `REVIEW_DIFF_AND_DECIDE_COMMIT`
- MISSION_COMPLETE: `yes`
- ROOT-001: `closed_fixed` (do not reopen)
- FINDING-002 / HC-001: `closed_fixed` (do not reopen)
- FINDING-003: `closed_false_positive` (do not reopen)
- FINDING-004 / HC-FINDING-004-STALE-TEST: `closed_fixed` (do not reopen)
- FINDING-005: `closed_fixed` (do not reopen)
