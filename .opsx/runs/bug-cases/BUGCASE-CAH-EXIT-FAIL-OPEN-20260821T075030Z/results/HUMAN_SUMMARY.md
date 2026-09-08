# Что произошло

В обработчике Telegram EXIT для `card_ab_hold` отсутствующий идентификатор
пользователя мог пройти дальше границы проверки владения. Исправление внесено,
проверено независимым GREEN-проходом, а bug family закрыта как
`CLOSED_FIXED_VERIFIED`.

# Что было сломано

Публичный `disable_card_ab_hold` мог открыть write-сессию при отсутствующем или
некорректном actor ID. Низкоуровневый внутренний seam трактовал `None` как
разрешение пропустить проверку владения.

# Почему это было проблемой

Внешний callback с невалидным actor ID мог дойти до отключения режима и очистки
эпохи. Это нарушало fail-closed инвариант и создавало риск PostgreSQL-мутации
без подтвержденного владельца.

# Что мы изменили

Публичный EXIT-обработчик теперь извлекает и проверяет actor ID до открытия
write-сессии. При невалидном actor ID обработчик завершает работу без вызова
session seam, мутации PostgreSQL или commit. Явное поведение внутреннего seam
для доверенных внутренних вызовов сохранено.

# Какие файлы изменены

## Изменения этого bug episode

- `app/modules/shop_runner/service_manager/services/auto_updater_v3/card_ab_hold/telegram/handlers.py`
- `.opsx/runs/bug-cases/BUGCASE-CAH-EXIT-FAIL-OPEN-20260821T075030Z/results/OWNER-CLOSURE-ROOT-001.md`
- `.opsx/runs/bug-cases/BUGCASE-CAH-EXIT-FAIL-OPEN-20260821T075030Z/results/HUMAN_SUMMARY.md`
- `.opsx/runs/bug-cases/BUGCASE-CAH-EXIT-FAIL-OPEN-20260821T075030Z/CASE.md`
- `.opsx/runs/bug-cases/BUGCASE-CAH-EXIT-FAIL-OPEN-20260821T075030Z/LEDGER.md`
- `.opsx/runs/bug-cases/BUGCASE-CAH-EXIT-FAIL-OPEN-20260821T075030Z/findings/ROOT-001.md`
- `.opsx/runs/bug-cases/BUGCASE-CAH-EXIT-FAIL-OPEN-20260821T075030Z/family/FAMILY.json`
- `.opsx/runs/bug-cases/BUGCASE-CAH-EXIT-FAIL-OPEN-20260821T075030Z/INDEX.md`
- `.opsx/runs/bug-cases/BUGCASE-CAH-EXIT-FAIL-OPEN-20260821T075030Z/results/ROUTE-TRACE.jsonl`
- `.opsx/runs/bug-cases/BUGCASE-CAH-EXIT-FAIL-OPEN-20260821T075030Z/team/heartbeats/WEX_CLOSURE_OPERATOR_37a699a3bf.json`
- `.opsx/runs/bug-cases/BUGCASE-CAH-EXIT-FAIL-OPEN-20260821T075030Z/team/packets/WEX_CLOSURE_OPERATOR_37a699a3bf.out.json`

## Ранее существовавшие несвязанные изменения

Они не анализировались и не включались в решение этого bug episode.

# Как мы проверили

Независимая GREEN-проверка подтвердила фиксированный тест, соседние unit-тесты,
целостность frozen test и `git diff --check`.

## Какие тесты прошли

- `poetry run pytest -m unit tests/unit/auto_updater_v3/card_ab_hold/test_exit_rejects_missing_actor.py` — 4 passed.
- `poetry run pytest -m unit tests/unit/auto_updater_v3/card_ab_hold/test_pg_session_handoff_seams.py tests/unit/auto_updater_v3/card_ab_hold/test_telegram_menu_open_hotfix.py` — 31 passed.
- `git diff --check` — PASS.
- Frozen test SHA-256 совпал с ожидаемым значением.

# Какие дополнительные проверки сделали

Bounded hunt проверил публичные EXIT callback paths в области
`card_ab_hold`. Результат `HUNT_RESULT: CLEAR`: других нарушений того же
actor-before-write инварианта в заявленном scope не найдено. Family fan-in
подтвердил `READY_FOR_FAMILY_CLOSURE`, family-wide green `PASS` и отсутствие
blocking findings. Learning decision выполнен и завершен с verdict
`EXISTING_POLICY_COMPLIANCE_FAILURE` и `RESOLVED_NO_PROMOTE`.

# Что не изменяли

Не изменялись fan-in отчет, OpenSpec, тесты, глобальные правила и несвязанные
грязные файлы рабочего дерева. Git commit, push и deployment не выполнялись.

# Оставшиеся риски

Проверка bounded hunt ограничена заявленными файлами и публичными callback
путями; несвязанные callback-зоны вне scope не проверялись. Изменения остаются
не закоммиченными до решения владельца.

# Что проверить перед коммитом

Просмотрите полный diff, убедитесь, что в него не попали несвязанные файлы, и
отдельно подтвердите корректность actor validation до открытия write-сессии.
После этого владелец решает, создавать ли commit.

# Технические детали

- CASE_ID: `BUGCASE-CAH-EXIT-FAIL-OPEN-20260821T075030Z`
- FINDING_ID: `ROOT-001`
- BUG_FAMILY_ID: `BFAM/BUGCASE-CAH-EXIT-FAIL-OPEN-20260821T075030Z/ROOT-001/EXIT-FAIL-CLOSED`
- INVARIANT_ID: `INV/BUGCASE-CAH-EXIT-FAIL-OPEN-20260821T075030Z/ROOT-001/EXIT-FAIL-CLOSED`
- CASE_STATUS=CLOSED
- FAMILY_STATUS=CLOSED_FIXED_VERIFIED
- WORKTREE_STATUS=UNCOMMITTED_CHANGES_AWAITING_USER_REVIEW
- COMMIT_CREATED=NO
- USER_ACTION_REQUIRED=REVIEW_DIFF_AND_DECIDE_COMMIT
