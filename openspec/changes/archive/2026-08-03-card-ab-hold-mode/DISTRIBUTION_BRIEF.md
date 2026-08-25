# DISTRIBUTION_BRIEF — card-ab-hold-mode

STATUS: DISTRIBUTION_BRIEF_READY
CHANGE_ID: card-ab-hold-mode
ARCHIVE_PATH: openspec/changes/archive/2026-08-03-card-ab-hold-mode/
AUDIENCE: cs_pack
WRITE: disk
OUTPUT_PATH: openspec/changes/archive/2026-08-03-card-ab-hold-mode/DISTRIBUTION_BRIEF.md

## PRODUCT_SUMMARY

В платной автоматизации появился режим **A/B Hold** для «чистого» теста
карточки (фото/инфографика): продавец явно подтверждает набор ключей и цели,
прогревает кампанию не меньше суток, отдельно подтверждает Auto — и только
после успешной синхронизации с Wildberries бот держит профиль стабильным, пока
ставки продолжают подтягиваться к подтверждённым целям. Широкий доступ всем
paid-пользователям пока **не** открыт (нужно решение OD-05).

## PROBLEM_BEFORE

Пока шёл обычный автоапдейтер или менялись ключи/минус-фразы, A/B-тест
карточки «загрязнялся»: непонятно, что дало прирост — креатив или смена
рекламного профиля. Старый путь мог зафиксировать целевые позиции слишком рано
(без отдельного прогрева и без явных подтверждений). Excel как способ
включить режим убран из MVP после prod-бага.

## WHAT_CLIENT_GETS_NOW

- Режим A/B Hold только для **оплаченного** бота и только через **Telegram**
  (не Excel).
- Пошаговый запуск: подтвердить ключи → прогрев (по умолчанию и минимум
  **24 часа**, можно длиннее) → увидеть факт-позицию и предложенную цель
  отдельно → подтвердить цели → отдельно подтвердить участие Auto и ставку
  Auto → дождаться успешной синхронизации с WB → статус «можно запускать A/B».
- Во время hold: цели и набор рекламных фраз стабилизированы; биддер
  продолжает работать к подтверждённым целям; автоматическое «раздувание»
  ключей/whitelist и авто-смена целевых позиций не идут.
- При сбоях/устаревшей статистике бот **не принимает решения «вслепую»**
  (заморозка изменений), но **не останавливает кампанию только из-за**
  устаревшей статы.
- Выключение режима возвращает обычную автоматику без «восстановления»
  старого профиля ключей из снимка.
- Ограниченная раскатка: ручной тест владельца / opt-in бета; массовое
  включение — только после OD-05.

## HOW_IT_WORKS_FOR_USER

1. В настройках РК (paid, автоапдейтер V3) открыть экран A/B Hold.
2. Включить режим (есть проверки свежести статы, плана max CPO, объёма
   показов — при малом объёме предупреждение с выбором «всё равно» / отмена).
3. Подтвердить набор ключей → выбрать длительность прогрева (≥24 ч) → дождаться
   окончания WARM_UP.
4. На экране после прогрева: по каждому ключу факт и предложенная цель —
   подтвердить цели.
5. Отдельно подтвердить участие Auto, затем ставку Auto.
6. Система фиксирует намерение, синхронизирует WB; при частичном сбое можно
   повторить без повторного прохождения всех шагов.
7. Когда статус ACTIVE и hold не «деградирован» — можно менять креатив карточки
   для A/B. Выход — кнопка выключить (EXIT).

## WHAT_DID_NOT_CHANGE

- Free-бот не получает этот automation-режим.
- Управление ценой товара / price-management — вне режима.
- Встроенный A/B-инструмент Wildberries и его метрики — не интерпретируются.
- Суточный бюджет / пауза-запуск по балансу/расписанию работают как раньше
  (это стоп-порог, не новый «жёсткий лимит теста»).
- Полное отключение бота (`bot_active=False`) не требуется для «заморозки»
  профиля под тест.

## LIMITATIONS_AND_DO_NOT_PROMISE

- **Не обещать** «всем paid уже доступно» — OD-05 OPEN; default fail-closed /
  allowlist / feature flag.
- **Не обещать** полный freeze всех фраз при любом типе РК / сверх лимита
  минус-фраз WB — при превышении cap статус честно показывает деградацию.
- **Не обещать** абсолютный тестовый бюджет / «нельзя перерасходовать
  суточный лимит» — overshoot возможен; суточный сброс ожидаем.
- **Не обещать** hard-block полок — только рекомендация в инструкции.
- **Не обещать** emergency kill-switch / policy picker hard|soft|self —
  отложено (WORKLOG / future change).
- **Не обещать** авто-аборт зависшей подготовки после N retry — SHOULD/future.
- **Не обещать**, что устаревшая стата «сама остановит» кампанию — freeze ≠ stop.
- Excel: режим **нельзя** включить/выключить через Excel — не позиционировать
  как Excel-фичу.

## ROLLOUT_NOTES

- Раскатка: owner manual test → limited opt-in beta → **OD-05** для broad enable.
- Code gate: `CARD_AB_HOLD_OD05_BROAD_ENABLE_ACCEPTED` (default false/unset);
  readiness: `evaluate_card_ab_hold_broad_enable_readiness()`.
- Checklist: `openspec/changes/archive/2026-08-03-card-ab-hold-mode/rollout/od05-readiness.md`
  и `rollout/owner-manual-test-checklist.md`.
- Для клиента в пилоте: нужна paid-кампания, V3, доступ по allowlist/флагу
  (точную процедуру доступа задаёт owner/ops — не выдумывать в публичном copy).

## SOURCE_EVIDENCE

- change-id: `card-ab-hold-mode`
- archive: `openspec/changes/archive/2026-08-03-card-ab-hold-mode/`
- proposal: `.../proposal.md` (Why / Intent / Out of scope / Rollout)
- design: `.../design.md` (Goals / Non-Goals / WARM_UP / confirms)
- tasks: `.../tasks.md` (все секции отмечены выполненными на момент archive)
- main spec (synced): `openspec/specs/card-ab-hold-mode/spec.md`
- OD-05: `.../rollout/od05-readiness.md` (Status: OPEN)
- decisions (promoted Accepted):  
  `openspec/decisions/card-ab-hold-write-path-ownership/decision.md`  
  `openspec/decisions/ab-hold-epoch-lifecycle-and-generation-ownership/decision.md`  
  `openspec/decisions/ab-hold-confirmed-epoch-parameters-sot/decision.md`
- PR / commits: не переданы в этом запуске (`pr=` не указан)

## OWNER_DECISION_REQUIRED

YES:

1. Канал и тон публикации (бот-рассылка / справка / CS-скрипт / лендинг).
2. Формулировка доступа в пилоте (allowlist / кто получает invite) — без
   обещания «уже у всех».
3. Принимать ли OD-05 и когда (широкое включение) — пока OPEN.
4. Нужен ли короткий `audience=client` вариант для конечных пользователей.

## WHAT_HAPPENED

Собрали distribution brief для `card-ab-hold-mode` из archive + synced main
spec + OD-05 readiness.

## WHY

Подготовка материалов для клиентов / CS / дистрибьюции после archive.

## CURRENT_STATE

distribution_brief_ready

## NEXT_ACTION

Адаптировать этот brief в выбранный клиентский канал (вне OPSX). При необходимости:
`/opsx-distribute-brief change=card-ab-hold-mode audience=client write=chat`

## DO_NOT_DO_YET

Не публиковать обещания из LIMITATIONS_AND_DO_NOT_PROMISE; не трактовать brief
как verify/archive/PR; не объявлять OD-05 принятым без явного owner sign-off.
