# Инцидент: артикул 138252141 — «в очереди», кампании не созданы

**Дата расследования:** 2026-09-30  
**Статус:** **RESOLVED** (Owner 2026-09-30) — техдолг не P0: PAT-ADV-003, OPS_STATE/`complete_release` (`DOTO/WORKLOG.md` в репо)  
**Режим:** `/opsx-devops` INVESTIGATE (READ_ONLY)  
**Кластер:** `prod-adv-bot` (доступ с vkita-pc через kubectl)

## Симптомы (со слов пользователя)

| Поле | Значение |
|------|----------|
| Артикул (nmid) | `138252141` |
| Сценарий | Подключение существующих РК → кампании не найдены → «Да, создать обе» (аукцион + авто) |
| Ответ бота | «Задача на создание обеих кампаний добавлена в очередь. Ожидайте уведомления.» (~17:56 МСК) |
| Итог | Кампании на WB не появились, финального уведомления о создании нет |

## Что показало расследование

### 1. Очередь и воркер — задача **была** принята

- Обработчик: `app/client_bot/user_interface/handlers/connect_existing_advs.py` → `connect_existing_create_both` ставит в ARQ задачу `create_complex_advs(nmid, shop_id, hard_mode=False, user_telegram_id)`.
- Подтверждение callback `ce_create_both:confirm` в логах `wb-sky-bot`: **18:00:32** МСК (пользователь нажал «Да» около **18:00:11**, обработка с задержкой; в middleware — `callback answer skipped (stale)`).
- Воркер `adv-bot-asq-worker` стартовал задачу: **18:00:32** → `create_complex_advs(138252141, shop_id=5339e9ad-cbfe-50fc-8d77-b9f337a80417, …)`.
- Job id (ARQ): `dfad3e8199064aa3bb258fca0aacf723`.

**Вывод:** Redis/ARQ и постановка в очередь работали. Проблема не в «задача не попала в очередь».

### 2. Задача **упала до создания кампаний на WB**

По логам воркера за ~18:00:35–18:00:41 успешно прошли:

- загрузка доступа к кабинету;
- синхронизация объявлений с WB API (`get_advs`, HTTP 200).

На **18:01:41** — первая ошибка в `create_complex_advs`. Стек указывает на **`tasks.py` строка 347** — это `await bot.send_message(..., "Создаю комплексную кампанию для артикула …")`, то есть **промежуточное уведомление в Telegram**, а не вызов `MainAdvManager.create_complex_advs` / WB create.

**Первая meaningful ошибка:**

- `python_socks._errors.ProxyTimeoutError: Proxy connection timed out: 60`
- при попытке HTTP к `api.telegram.org` (через SOCKS-прокси в aiohttp/aiogram);
- обёртка: `aiogram.exceptions.TelegramNetworkError: HTTP Client says - Request timeout error`.

На **18:02:42** задача завершилась с ошибкой (~129 с). Повторная отправка уведомления об ошибке (`_notify_unknown_task_error`) **тоже** упала с тем же классом ошибки (прокси/Telegram).

Настройки ARQ: `max_tries = 1` — **автоматического повтора нет**.

**Вывод:** кампании на Wildberries с высокой вероятностью **не создавались**, потому что код не дошёл до `manager.create_complex_advs(...)` после падения на `send_message`.

### 3. Контекст UI (артикул и кабинет)

- `wb-sky-bot`, **17:56:58**: `connect_existing candidates for nmid=138252141 shop_id=5339e9ad-cbfe-50fc-8d77-b9f337a80417: auction=1 auto=0` (до фильтра «подключаемых» кандидатов в handler).
- Пользователь Telegram id в логах: `373435337` (внутренний тестовый/owner-контекст; в отчёт без PII для внешней рассылки).

### 4. Локальные логи на ПК

- `C:\Users\vkita\my_code\meta-repo\adv-bot\logs\` — только `.gitkeep`, записей инцидента нет. Источник истины — логи pod в k8s.

### 5. Смежная инфраструктура

- В том же 10-часовом окне в `adv-bot-asq-worker` зафиксировано **8** вхождений `Proxy connection timed out` (не только этот nmid) — возможна общая нестабильность пути **воркер → SOCKS → Telegram**, при том что **WB API из того же job отвечал нормально**.
- В namespace есть `bebra-shared-proxy`, `xray-client` (детальная диагностика прокси — отдельный DevOps-фокус, см. ниже).

## Вероятная причина (root cause)

**Продуктовая уязвимость + сетевой сбой:** фоновая задача `create_complex_advs` трактует неудачную отправку **необязательного** статусного сообщения в Telegram как фатальную ошибку и прерывает сценарий **до** создания РК на WB. Триггер — таймаут SOCKS-прокси при обращении к Telegram API.

Это **не** симптом «воркер не запущен» и **не** отсутствие job в Redis.

## Evidence (пути и команды, без секретов)

| Источник | Как воспроизвести read-only |
|----------|-----------------------------|
| Код постановки в очередь | `app/client_bot/user_interface/handlers/connect_existing_advs.py` (~1566–1576) |
| Код задачи | `app/modules/adv_creator/backend/tasks.py` (`create_complex_advs`, `_create_complex_advs`, ~347) |
| ARQ worker | `app/arq_workers/workers.py` (`create_complex_advs`, `max_tries = 1`) |
| Логи бота | `kubectl logs deployment/wb-sky-bot -n prod-adv-bot --since=10h` → фильтр `138252141`, `ce_create_both` |
| Логи воркера | `kubectl logs deployment/adv-bot-asq-worker -n prod-adv-bot --since=10h` → фильтр `138252141`, `dfad3e8199064aa3bb258fca0aacf723`, `Ошибка задачи create_complex_advs` |
| DevOps память | `adv-bot/.cursor/devops/OPS_STATE.md` (namespace `prod-adv-bot`, deployment `adv-bot-asq-worker`) |

**Важно:** в сырых логах kubectl может попасть URL Telegram API с токеном бота — при копировании логов **редактировать** токен.

## Рекомендуемые следующие шаги (OPSX, не ручной прод-фикс)

### Основной маршрут (продукт)

```text
/opsx-fix-bug symptom=create_complex_advs падает на send_message «Создаю комплексную кампанию» (ProxyTimeout→Telegram) до вызова WB create; nmid=138252141; job dfad3e8199064aa3bb258fca0aacf723; evidence=adv-bot-asq-worker 2026-09-30 18:00–18:02 MSK
```

Ожидаемый фикс-кандидат (для обсуждения в bug-episode): не ронять задачу из-за статусного Telegram-сообщения (try/except + логирование, создание РК в первую очередь); опционально отдельный путь уведомлений; рассмотреть retry только для идемпотентных шагов с учётом `AdvExistsForNmidError`.

После фикса и выката — **повторить сценарий в боте** для `138252141` (или одноразовый штатный re-enqueue через UI «создать обе»), не ручной `kubectl exec` без runbook.

### Дополнительно (инфра, если повторяется массово)

```text
/opsx-devops INVESTIGATE ns=prod-adv-bot focus=logs symptom=ProxyTimeoutError adv-bot-asq-worker telegram SOCKS bebra-shared-proxy xray-client
```

Только READ_ONLY: корреляция ошибок Telegram vs WB, события pod, не `rollout restart` без `PLAN_WRITE` + `GO`.

## DevOps return contract

```text
STATUS: INVESTIGATION_DONE
MODE: INVESTIGATE
WRITE_CLASS: NONE
FORBIDDEN_HIT: NONE
OPS_STATE_READ: yes
OPS_STATE_UPDATED: no

WHAT_HAPPENED: Задача create_complex_advs для 138252141 выполнялась в adv-bot-asq-worker и упала на таймауте прокси к Telegram при промежуточном send_message до создания РК на WB.
WHY: Жёсткая зависимость бизнес-задачи от доставки Telegram-статуса + ProxyTimeoutError 60s на пути к api.telegram.org.
CURRENT_STATE: Кампании не созданы; пользователь не получил ни успех, ни явную ошибку (уведомление об ошибке тоже не ушло).
OWNER_DECISION_REQUIRED: yes
NEXT_ACTION: /opsx-fix-bug (см. выше); при массовых таймаутах — /opsx-devops INVESTIGATE на прокси.
DO_NOT_DO_YET: kubectl rollout restart воркера «наугад»; ручное создание РК вне бота без GO; публикация сырых логов с токеном бота.
```

## Классификация

| Вопрос | Ответ |
|--------|--------|
| DevOps vs продукт | **REDIRECT_PRODUCT** (корневая логика `tasks.py`); инфра — сопутствующий фактор (прокси/Telegram) |
| Очередь ARQ | Работала |
| WB API в этом job | До ошибки — успешная синхронизация списка РК |

---

## Повтор ~19:45 МСК (2026-09-30)

| Поле | Значение |
|------|----------|
| Контекст | Повторный enqueue «создать обе» для того же nmid после первого падения (~18:00) |
| ARQ job id | `fd6348da0b3e4fd6ae220e76371c7a3d` |
| Симптом | Тот же класс: `ProxyTimeoutError` (~60s CONNECT) на пути воркера к Telegram через SOCKS; pods `bebra-shared-proxy`, `xray-client` в Running |
| Итог | Кампании снова не созданы — job снова прервался на промежуточном `send_message` до `MainAdvManager.create_complex_advs` (до выката фикса) |

**Product fix:** `_send_user_message_best_effort` (`93669ece7` / `3693e936e` на `stage`, `tasks.py` + test).

| PR | Назначение |
|----|------------|
| [#443](https://github.com/revoluxe-ai/adv-bot/pull/443) | **Раздут:** hotfix + merge ветки `scripts` (~363 файла, +85k LOC); не использовать для инцидент-merge |
| [#445](https://github.com/revoluxe-ai/adv-bot/pull/445) | **Узкий draft:** только hotfix, `cursor/create-complex-advs-telegram-only-6147` |

Policy в репо: `.cursor/rules/scripts-ops-lane.mdc`, draft [PR #446](https://github.com/revoluxe-ai/adv-bot/pull/446) (migration-gates только DB jobs).

**Merge blocker (2026-09-30):** CI `migration-ephemeral-pg` на #443 — широкий diff (merge `scripts`; `k8s/jobs/ops-script-runner.yaml` под старым `k8s/jobs/**` в migration-gates). #445 не трогает scripts; hotfix уже на tip `origin/stage` (`3693e936e`) — выкат образа с `stage` без merge #443.

**Prod (2026-09-30 ~21:20 MSK):** выкат **3693e936e-r1** — CONTROL token=12, migrate SUCCESS_NOOP, CAS всех entrypoint’ов на `3693e936ea95871004749a9af688ba040afd6f1f`; `adv-bot-asq-worker` Running. **Проверка сценария Owner:** повтор «создать обе» для `138252141`. OPS_STATE/LAST.json и `complete_release` (Job pending по taint) — дожать при следующем ops-hop.

**Rollback policy (2026-09-30):** при failed CAS нового образа — откат на master LKG из `OPS_STATE` ([store](/cursor/stores/self/internal/deploy-rollback-policy.md), draft [PR #444](https://github.com/revoluxe-ai/adv-bot/pull/444)).

**Контекст proxy:** [PAT-ADV-002](/cursor/stores/self/internal/recurring-patterns.md) — асимметрия `HTTP_PROXY` у asq-worker vs `wb-sky-bot`; инфра xray/Telegram — `/opsx-devops INVESTIGATE` + runbook `bebra-location-switch`, без blind restart.

**Acceptance ~22:08 MSK:** stale confirm → not handled ([PAT-ADV-003](/cursor/stores/self/internal/recurring-patterns.md)).

**Resolution (2026-09-30 ~22:14 MSK, [Check latest create both attempt](bc-d3d3159f-26b4-5cd8-8939-1ae620f3e7e8)):** свежий сценарий (артикул → confirm) → **handled**; ARQ `4f32c326712d4bc5826e9d7d254d90ce`; `create_complex_advs` **~152s OK** на образе `3693e936e`. WB: авто **40593981**, поиск **40593988** (депозит 1000 ₽ каждая). Клики **22:08 / 22:11** без FSM — **not handled** ([PAT-ADV-003](/cursor/stores/self/internal/recurring-patterns.md)).

**Status:** **RESOLVED** (product path + deploy).

**Повтор ~22:45–22:55 MSK ([Urgent create both failure logs](bc-214b912c-d9bb-522d-9079-59178201ab2d)):** снова **stale** confirm → not handled; **не регресс воркера** — РК уже есть (`40593981`/`40593988`). Draft [#447](https://github.com/revoluxe-ai/adv-bot/pull/447) → merge + выкат **`wb-sky-bot`**.

**Техдолг (ops):** OPS_STATE/LAST после `3693e936e-r1`, `complete_release` — [adv-bot-tech-debt-post-138252141.md](/cursor/stores/self/internal/adv-bot-tech-debt-post-138252141.md).
