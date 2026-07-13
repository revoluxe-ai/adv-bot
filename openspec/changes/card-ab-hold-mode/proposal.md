## Why

При A/B-тесте карточки (инфографика / главное фото) CTR и конверсия зависят не только от креатива, но и от рекламного профиля РК: состав ключей, белый список, целевые позиции и ставки. Пока идёт обычный автоапдейтер, тест становится «грязным»: непонятно, что дало прирост — креатив или смена рекламы. Клиентам уже нужен понятный self-service сценарий: зафиксировать целевые позиции по факту, отключить их автообновление и оставить биддер работающим — без ручной сборки legacy-флагов и без полного отключения бота.

## What Changes

### Intent

Один paid automation-режим **A/B Hold**: один раз привести РК к стабильному профилю для теста карточки; на период теста **зафиксировать позиции** (целевая позиция = текущая фактическая) и **отключить обновление целевых позиций**, при этом **биддер продолжает работать**; при выключении режима снова включить обновление ЦП и обычные апдейтеры — без restore настроек.

### Current behavior

- Автоапдейтер (V2/V3) на каждом тике может менять whitelist, целевые позиции, режимы ключей и включать новые ключи.
- Типичный «ручной» обход — выключить `bot_active` целиком: тогда останавливается и updater. Это не подходит для A/B: **биддер в режиме A/B Hold останавливать нельзя — он MUST продолжать работать**; полный off бота как способ «заморозить» РК недопустим.
- Ручное выключение отдельных auto-флагов для V3 не даёт явного «ЦП зафиксированы + обновление ЦП выкл + биддер ON» и не гарантирует чистый setup; между подами bot и shop-runner нет согласованного прерывания текущего тика.
- Отдельного режима A/B-теста карточки в продукте нет.

### Desired behavior

- Режим доступен **только paid**: при `bot_active is False` пункт меню / экран A/B Hold MUST быть **скрыт**; включение режима через UI, Excel или иные пути MUST NOT выполняться (reject / no-op). При `bot_active is True` — доступен экран инструкции и кнопки включить / выключить / назад.
- **ENTER:** система один раз готовит профиль РК, затем переводит кампанию в hold.
- **Критерий setup (ENTER):**
  - PASS: `pay_for_order` ключа **≤ max CPO плана** (не resolve) **и** показов за недельное окно статистики ключа (тот же источник, что в карточке ключа) **≥ 100**;
  - FAIL (иначе, включая отсутствие `pay_for_order`): ключ **OFF** (выключается / снимается с БС);
  - для PASS: целевая позиция фиксируется на **текущей** позиции; состав БС после setup считается зафиксированным.
- **HOLD:** целевые позиции остаются теми, что зафиксированы на ENTER (текущая фактическая); **обновление целевых позиций выключено**; **биддер продолжает работать** (подтягивает ставки к зафиксированным ЦП); структурные изменения БС / разгон / enable ключей не выполняются; допускаются только защиты от перерасхода относительно max CPO.
- **EXIT:** режим снимается — снова **включается обновление целевых позиций** и обычные апдейтеры; snapshot/restore настроек не требуется.
- Координация между bot-подом и shop-runner-подом идёт через Redis-сигнал прерывания: текущий normal-тик может быть остановлен до apply с ответом «остановлено, безопасно, можно продолжать».
- В справке MUST быть: перед включением прогреть РК с не зажатым max CPO и запасом плана продаж; полки рекомендуется выключить (не hard block — на усмотрение пользователя, если без полок нет трафика); не менять цену на период теста.
- Настройка режима MUST быть доступна в Excel roundtrip **только для paid** (`bot_active is True`); для inactive — колонку не применять / скрывать по тому же paid-boundary.

### Scope in

- Paid-only access: UI скрыт при `bot_active is False`; write/enable пути гейтятся тем же условием.
- Paid bot UI: экран инструкции + вкл/выкл режима.
- Состояния режима кампании (выкл / подготовка / активен).
- Setup ENTER + hold + exit для V3 (paid automation).
- Cross-pod Redis coordination (signal / abort ack / setup lock) по project Redis-паттернам.
- ACT-защита параллельных structural write-путей на время режима.
- Excel-колонка режима (paid-only).
- Тесты-first: gates structural freeze + paid visibility (`bot_active=False` → скрыто / не включается).

### Out of scope

- Встроенный A/B инструмент Wildberries и интерпретация его метрик.
- Управление ценой товара и price-management клиента.
- Hard-block режима полок (только рекомендация в справке).
- Обязательный backup/restore настроек РК (Excel snapshot) при выходе.
- Safe mode / pull-down при ухудшении экономики (отдельная идея из WORKLOG).
- Free bot / `bot_active is False`: режим — paid automation core; UI MUST быть скрыт; enable MUST NOT выполняться.
- Изменение алгоритма обычного V3 preamble вне ветки A/B Hold.

### Risk

High-risk зона: ставки, CPO/CPA, V3 updater, ApplyManager, WB write actions, перерасход / отсутствие трафика. Ошибки setup могут массово выключить ключи с малой статистикой; ошибки hold могут либо «протечь» в normal updater, либо заморозить профиль слишком жёстко. Нужна координация multi-pod и regression gates.

### Rollback idea

Выключить режим на кампании (EXIT) или не включать на новых; при проблеме — откат релиза: поле режима по умолчанию выкл, Redis-ключи с TTL сами истекают, ordinary V3 scheduling восстанавливается.

### Architecture Decision References

- Relevant accepted: `openspec/decisions/mode-defaults-policy-ownership/decision.md` — дефолт режима A/B Hold (выкл) при paid/free overlays принадлежит declarative mode policy overlays, а не transition-helper.
- Proposed (this change): `openspec/changes/card-ab-hold-mode/decisions/card-ab-hold-write-path-ownership/decision.md` — ownership setup/hold write-path, structural freeze ACT, PG vs Redis, paid-only enable.

## Capabilities

### New Capabilities

- `card-ab-hold-mode`: paid-only режим A/B Hold (`bot_active is True`; при False — UI скрыт, enable запрещён) — ENTER (pay_for_order ≤ max CPO + ≥100 показов, FAIL→OFF, ЦП := текущая фактическая), HOLD (обновление ЦП выкл, биддер работает, guard перерасхода), EXIT (снова ЦП + апдейтеры, без restore), UI-инструкция, Excel, cross-pod interrupt.

### Modified Capabilities

- Нет (в `openspec/specs/` пока нет связанных capabilities с requirement-level изменениями).

## Impact

Затрагивает paid automation shop-runner (планирование V3 vs hold/setup), координацию bot ↔ runner через Redis, состояние кампании в БД, Telegram UI меню РК, Excel roundtrip и тестовый контур write-gates. Не расширяет Free path. Change не apply-ready, пока не зафиксирован proposed architecture decision по ownership hold write-path.
