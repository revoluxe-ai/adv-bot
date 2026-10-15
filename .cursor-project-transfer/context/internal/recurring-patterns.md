# Повторяющиеся паттерны (OPSX knowledge base)

Append-only журнал для координатора. Новые записи — в конец.  
Формат строки: `id`, симптом, первая ошибка, типичная путаница, OPSX-маршрут, evidence.

---

## PAT-ADV-001 — «В очереди», кампании не созданы (create_complex_advs)

| Поле | Значение |
|------|----------|
| **id** | PAT-ADV-001 |
| **first_seen** | 2026-09-30 |
| **symptom** | Бот: «Задача на создание обеих кампаний добавлена в очередь»; на WB РК нет; уведомления об успехе/ошибке нет |
| **misread** | «Воркер не работает» / «Redis сломан» / «WB отказал» |
| **FACT root cause** | ARQ job **стартовал**; WB sync в job часто **OK**; падение на **`bot.send_message`** (промежуточный статус «Создаю комплексную кампанию…») **до** `MainAdvManager.create_complex_advs`; часто `ProxyTimeoutError` → Telegram через SOCKS |
| **code path** | `connect_existing_advs` → enqueue `create_complex_advs` → `app/modules/adv_creator/backend/tasks.py` ~347 |
| **worker** | `adv-bot-asq-worker`; `max_tries=1` — без авто-retry |
| **OPSX route** | `/opsx-devops INVESTIGATE` (очередь/логи) → **`/opsx-fix-bug`** (product: не ронять WB-create из-за Telegram) |
| **not** | `kubectl rollout restart` без плана; ручное создание РК вне бота без GO; hotfix на месте при failed CAS |
| **rollback (Owner)** | Плохая раскатка нового образа → `/opsx-devops` CAS rollback на **master** LKG (OPS_STATE), затем разбор |
| **evidence** | [adv-bot-incident-138252141-campaigns.md](/cursor/stores/self/docs/adv-bot-incident-138252141-campaigns.md); jobs `dfad3e8199064aa3bb258fca0aacf723`, `fd6348da0b3e4fd6ae220e76371c7a3d`; nmid `138252141` |
| **fix** | `_send_user_message_best_effort` в `app/modules/adv_creator/backend/tasks.py` — progress/success Telegram не роняют job |
| **status** | **CLOSED 2026-09-30** — prod `3693e936e`; job `4f32c326712d4bc5826e9d7d254d90ce`; WB авто `40593981` + поиск `40593988` (nmid `138252141`). Stale-button — PAT-ADV-003 |
| **ops_state drift** | Live `c5d3ecd…` ≠ repo LKG `4d5fae43…` — INVESTIGATE reconcile; open risk in [#444](https://github.com/revoluxe-ai/adv-bot/pull/444) |
| **infra (2026-09-30)** | Эпизодический таймаут **xray-client → api.telegram.org** (~60s); WB через proxy OK. **Не** blind `rollout restart` proxy — см. `k8s/bebra-location-switch-runbook.md`. Product guard: PR #443 |
| **merge hygiene** | Hotfix без alembic: узкий PR (`93669ece7`), не тащить merge `scripts` — иначе `migration-ephemeral-pg` блокирует не из‑за фикса |

**kubectl (read-only, redact tokens):**

```text
kubectl logs deployment/adv-bot-asq-worker -n prod-adv-bot --since=12h
kubectl logs deployment/wb-sky-bot -n prod-adv-bot --since=12h
```

---

## PAT-ADV-002 — Чат бота жив, ARQ create падает (proxy asymmetry)

| Поле | Значение |
|------|----------|
| **id** | PAT-ADV-002 |
| **symptom** | `wb-sky-bot` отвечает в Telegram; `adv-bot-asq-worker` падает на outbound `sendMessage` |
| **FACT** | `wb-sky-bot`: `PROXY=http://xray-client:8080`; без `HTTP_PROXY`. `adv-bot-asq-worker`: те же + **`HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY` → xray** — aiogram Telegram идёт через SOCKS; WB в job часто без таймаута |
| **misread** | «Прокси мёртв» / «надо только увеличить timeout» |
| **OPSX route** | Product: PAT-ADV-001 / PR #443. Infra: `/opsx-devops INVESTIGATE` xray telegram outbound (runbook), не restart без GO |
| **evidence** | [Fix proxy/campaign creation prod](bc-ff7b79e3-b875-5d0e-9748-257c4e2ec38a) 2026-09-30 |

---

## PAT-ADV-003 — «Да» на создать обе — тишина, воркер молчит

| Поле | Значение |
|------|----------|
| **id** | PAT-ADV-003 |
| **symptom** | Нажали «Да» на create both; нет «в очереди»; `adv-bot-asq-worker` без `create_complex_advs` |
| **FACT** | `wb-sky-bot`: `ce_create_both:confirm` → **Update is not handled** — FSM не `waiting_confirm_create_both` (старая inline-кнопка / сброшен state после `/start`) |
| **misread** | «Нужен больший timeout SOCKS» / «воркер не раскатан» |
| **OPSX route** | Owner: свежий проход сценария; product (техдолг, не P0): `/opsx-fix-bug` — friendly reply при confirm без state |
| **fix** | Draft [#447](https://github.com/revoluxe-ai/adv-bot/pull/447) — fallback «сессия истекла»; deploy `wb-sky-bot` after merge |
| **priority** | Was tech debt; escalated after repeat clicks 22:45–22:55 ([Urgent create both failure logs](bc-214b912c-d9bb-522d-9079-59178201ab2d)) |
| **evidence** | `902646424`; 22:45–22:55 not handled; nmid `138252141` РК already at 22:14 |

---

## PAT-OPSX-001 — Очередь vs бизнес-логика

| Поле | Значение |
|------|----------|
| **id** | PAT-OPSX-001 |
| **pattern** | Пользователь видит «добавлено в очередь» = enqueue **успешен**; отсутствие результата ≠ «не поставили в очередь» |
| **check order** | 1) wb-sky-bot enqueue 2) adv-bot-asq-worker job start/end 3) первая exception в task 4) WB API только после прохождения ранних `send_message` |
| **OPSX route** | `/opsx-devops` focus=logs → product task file |

---

## PAT-WB-001 — CH migration numbering

| Поле | Значение |
|------|----------|
| **id** | PAT-WB-001 |
| **invariant** | Файл SQL ≠ applied на target; не создавать параллельный `006` / второй runner |
| **order** | `clickhouse-migrations-control-plane` merge → официальный shop-wide `006` → потом `007+` (price history и т.д.) |
| **OPSX route** | change в P0 worktree; не `/opsx-apply` product DRR CH до unblock |

---

*Следующая запись: новый id PAT-&lt;area&gt;-&lt;nnn&gt;.*
