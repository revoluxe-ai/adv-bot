Переключить всех на корзины - они опять появились
 CH: иногда 500 на тяжёлых запросах
 отписать WB на форум о проблеме с корзинами
 Метрики оплаты: sent → click → paid
 Сделать RAG в бот
 Стать ментором в Solvery, завести ютуб канал
 Автоматическое переключение анализа с корзин на заказы, если нет данных
 Написать статью: порядок бьет класс
 Переделать Harbor на свой домен
 Написать статью: максимальная ставка
 Сделать рефакторинг Факта (короткое окно)
 Стать ментором в Solvery
 Убрать максимальную ставку (определять по первому месту, верхний ключ бустить без ограничений)
 Сделать регулировку агрессивности работы бота, которая будет определять сколько ключей без заказов (корзин) может быть активно в моменте.
 Сделать рассылку по боту с целью реанимации клиентской базы
 Переписать офФЕРТУ, ЧТОБЫ НЕ МОГЛИ ТРЕБОВАТЬ ВОЗВРАТА ДЕНЕГ
 Добавить ДРР в контрольные метрики бота т.к. клиентам это важно
 Сделать, чтобы багаз не обрабатывался, если не токена, то дой поры, пока рабочий токен не добавят
 Добавить в РК статус бота и статусы РК
 TODO_1
 Сделать чтобы РК создавались сразу с правильными настройками
 Сделать простое подключение старых РК к боту
 Сделать отключение фраз на последнем этапе раскрутки - без этого бот не выводит на целевую себестоимость
 Централизовать получение данных из баз через единый сервис (кликхаус в первую очередь)
 Добавить в учет рейтинга по ключу инфу по продажам за весь период
 наладить мониторинг ошибок
 Проверить: работают ли уведомления об истечении баланса
 Выставить счет картинам за дальнейшее использование
 Переработать офферту в боте
 Сделать фиксацию проблемного токена с отключением магазина, если токен не работает, и включением, если обновили токен
 Переработать отображение списка РК - показывать только подключенные к боту, сделать отключение.
 Автоматизировать работу Авто-кампаний - авто-тест
 Сделать инструкцию по боту
 Сделаль уведомлялку, что у вас все плохо, чтобы расылалось само через бот
 Тарифы: 10 - 30000, 11 - 16500, прям криво-криво сделано
 Исправить падение на update.py
 Навести порядок в тестах
 Переделай WBToken  в DTO
 Сделать менеджер очередей для задач для корутин
 Добавить проверку на повторы артикулов при создании РК
 Переделать тарифы
 Сделать рефакторинг с созданием сущности более высокого порядка - карточки товара, куда будет входить РК, к которой он относится, стата этой карточки, план-факт и т.д. и оперироовать в рамках бота с ней
 Срочно переделать все на нормальный DI, а то хрень получается
 Оптимизировать получение и обработку данных в боте, все централизовать, кешировать
 Сделать контроль остатков и отключение от биллинга и других корутин, если остатков нет
 Проверить, чтобы уведомления о Токенах и Балансе отправлялось во все боты
 Сделать фиксацию органических заказов
 Настроить основные - резервные источники репозиториев образов
 Сделай все таблицы в кликхаусе создание
 Сделать детектор-реакция проблем у WB, чтобы если что случись - бот не делал не правильных вещей
 Все долгие запросы из фронта вынести в воркер
 Привести логику включения платных опций к единому финансовому паттерну
 Сделать пометку для явно и не явно подключенных к боту РК (не явно - только для загрузки статы). И не отображать не явно, но грузить из них стату
 Поделить тесты на типы и встроить в CI/CD
 Убрать НЕ релеватные фразы
 Cделать, чтобы после привязки старых РК перекидывало сразу в эту РК
 Навести порядок с деактивацией режима раскрутки полок
 Проверить: только для Авто-тарифа должны в бидере отрабатывать прогноз ставки для места  Точнее даже сделать, СРОЧНО!!!!
 Сделать отдельную Макс ставку для общей В Аукционе
 В настройках времени показа включить копирование на всю неделю
 Сделать, чтобы в рейтинг подставлялась последняя установленная ставка
 унифицировать выгрузку ключей
 Нужно, чтобы если не может занять позицию ниже из-за ставки, то принималось решение: либо удаляем, либо ставим на другую позицию
 Time settings: сессии и блокировки в памяти — при рестарте/мультиворкерах теряется сессия и нет межпроцессного лока. Варианты решений (Redis сессии + Redis лок): [docs/time_settings_sessions_and_locks.md](../docs/time_settings_sessions_and_locks.md)
 Усовершенствовать сброс ключей при перерасходе: вычитать органику и убирать ключи, которые с учетом них превышают см
 Сделать фиксатор времени подключения РК к боту, чтобы статистический отчет вести от этой точки
 Скорректировать поведение бота при вкл. полках: сначала держим режим самые дешевые места, когда ключей больше нет - работаем на конверсию Без полок - до раскрутки макс конверсия, после - мин себестоимость
 Синхронизировать выгрузку с данными по ключам
 Сделать норм объект дефолтных настроек, который будет и в модель пробрасываться, и служить инструментом применения для сущ РК
 Сделать, чтобы Grace Period не работал для бонусов. И сделать ручную пополнялку для баланса
 Сделать, чтобы контроль активности был выключен по дефолту, а то при подключении бот ставит на паузу - народ пугается
 Перепроверить логику при не свежей стате и аварийном режиме. Переделать нормально
 Сделать бекапы настроек РК (ключи, ставки все)
 План продаж в для режима раскрутки полок и обычного режима !!!
 Добавить настройки тестирования полок: количество и пауза
 Добавить тест CPC
 Сделать уведомлялку о том, что падает ранжирование карточки
 Проверить сброс общей ставки
 Органичение ставки-места при макс конверсии
 Навести порядок в списке кампаний
Убрать легаси-пинг-проверку прав, заменить на единую новую  Legacy альтернатива (app/core/wb_api/check_righter.py)
Переделать подключение новых РК: 1. Сначала выбор ввод ID Или выбор существующей, если выбор существующей - не ищем, а запрашиваем только ее
Сделать кеш-таблицу подключаемых РК. Если не нашли в кеше - предлагаем обновить данные из кабинета, если уверены, что есть. Но если обновлений не делали изначально - обновляем
Сделать, чтобы после подключения новой РК ставились мин.ставки
сделать, чтобы после подключения новой РК возвращались настройки этой РК
 Выпилить AdvKeywords
 Сделать защиту с уведомлением в UI о том, что у нас в РК только 1 nmid
 Проверить и добавить, если надо, нужные права на запись Цены товара в корутине инкремента статы Полок (рекомендаций)
Испарвить причину, по которой падает основной магазинный воркер, а потом после перезагрузки пода начинает работать
Добавить в shelf-инкремент запись цены с учетом СПП
Сделать переключалку в боте на разные VPN
Сделать PR на мастер
Добавить в ключи, где текущее место выше цели при минимальной ставке инфу о текущем статусе
Добавить показы в статистику карточки
Добавить тексты в линтеры
Поменять тесты ставки в Авто Время из PG на CH
TEMP DEBUG: DEBUG_CLUSTER_BID_TRACE (ветка fix-clusters-bidder)
- Зачем: prod-логов недостаточно, чтобы понять где пропадает NewBid(560) в update_cluster_bids для exact кейса.
- Exact case: shop_id=db28efff-f7a9-52f8-8342-f1a58f7d8ed3, adv_id=32824944, search_adv_id=29734515, nmid=10749810, ks_id=17783715, key="антивозрастной матирующий крем".
- Включение: DEBUG_CLUSTER_BID_TRACE=1 + env DEBUG_CLUSTER_BID_TRACE_* (см. env.sample). No-op при !=1.
- Batch per-shop: CoroutinesManager → ClusterBidsManagerContainer(shop_id) → WBManager(shop_id); trace shop_id = wb_manager._shop_id, не advs[0].
- После root cause: выключить env на prod, удалить cluster_bid_trace.py + trace calls + test_cluster_bid_trace.py (или оставить guard под флагом, если решим оставить навсегда).
- сделать модуль заметок для РК и магазина с кнопкой выполения, потом развить в таск менеджер


 UI message test infra:
 - централизовать HTML escaping для всех HTML-экранов
 - убрать оставшиеся локальные лимиты 4096/1024
 - постепенно покрыть все message builders documentation regression tests
 - вынести user-facing copy из handlers в view/message layer
 - добавить warning-linter для сырых технических строк
 - ввести pattern "? Что это?" для сложных экранов
- централизовать в v3 экзекуторах получение фраз
- сделать в v3 экзекуторах нормальную только релеватные фразы фильтрацию






проверить


Сделать тарифы на основе python-данных
пересмотреть и исправить тарифы, чтобы бились!

Сделать отдельное контрольное окно-проверка сроков обновления кеша. И блок ошибок таких вещей в боте, для пользователя и адмима (подумать)
Проверить skip-тесты
сделать, что если все ключи OFF, а план выполняется, то РК на паузу, если факт > resolve TODO: СРОЧНО ИСПРАВИТЬ ТЕСТ, ПОПРАВИТЬ ТАРИФЫ
- CalclulatedKeyword.cpm может вернуть 0, если None Надо это испаправить

для авто сейчас работает распределение в часы вокруг артикула (кажется), разумнее - по категории, так больше данных - точнее прогноз
сделать, чтобы делалать попытка пополнения баланса РК вне зависимости от того, есть на счете деньги или нет (каскадом по всем источникам)


## Decision: временно не делать прогноз max CPO / объёма

Рассматривалась фича: прогнозировать, какой max CPO нужно поставить, чтобы получить нужный объём показов/кликов/заказов.

Вывод: фича потенциально сильная и может закрывать проблему непонимания настроек, но сейчас слишком рискованно уходить в сложную разработку. Есть риск потратить неделю+ на прогнозы вместо решения главной бизнес-проблемы — отсутствия стабильного притока новых пользователей.

Текущее решение:

* вернуться к задачам привлечения клиентов и бесплатному боту;
* проблему выбора max CPO закрыть инструкцией и предупреждением в продукте;
* явно объяснять пользователю, что max CPO влияет не только на себестоимость, но и на объём трафика/заказов;
* предупредить, что слишком низкий max CPO может привести к малому числу показов и ощущению, что “бот не работает”;
* прогноз max CPO оставить как перспективную платную диагностическую фичу на будущее.

Приоритет сейчас:

1. бесплатный бот как канал привлечения;
2. понятный onboarding;
3. сбор контактов;
4. простая инструкция по настройке max CPO;
5. продажи/рассылки по новым лидам.

Внедрить в свою работу vim


Сделать, наконец, норм alembic migration flow с проверкой - тестом миграции на локали, а потом примерение миграции уже в проде

Добавить фиксацию ошибок в получении статистики, дабы валидировать в том числе аб-тест мод
Проанализировать расход токенов и продумать стратегию экономии - высокий риск, может стопорнуться разработка.
Пересобрать и структурировать WORKLOG
Разобраться как собирает туду и WORKLOG opnx-explrer
Сделать скрипт-анализатор команд и config, который будет проверять не раздулись ли они слишком сильно
Сделать 2-уровневую (а то и трех) партнерку, чтобы у партнеров была мотивация привлекать других партнеров.


разобраться со старыми ветками, стешем они неимоверно разрослись, скоро стрельнем себе в ногу

связать openspec разработку в четкий граф и согласовать все входы-выходы между командами - сильно ускорит разработку
перейти на pyright без strict, а то стрельнем в ногу.


## BUG (out_of_scope от card-ab-hold-mode, разбирать отдельным change): V3 keyword strategy_mode жёстко связан с AdvSetting.strategy

- Дата: 2026-07-15, ветка implement-ab-wb-card-test-mode. Классификация: out_of_scope / needs_openspec_update (нужен отдельный OpenSpec change + decision, а не патч в текущем change). Вторая часть (сам декаплинг кода) — разбираю в другом чате.
- Симптом (ошибка дизайна): активный strategy_mode ключей БС (hard_status=2) и фикс.фраз (hard_status=4) в V3 берётся из AdvSetting.strategy (MIN_CPO→MIN_CPA, MAX_CONV→MAX_CONVERSION). Источник — app/modules/shop_runner/service_manager/services/v3_status_mode_sync.py (docstring 1-10, keyword_strategy_mode_for_adv_strategy). Надо развязать: по фикс.фразам позиции/режим должны выставляться руками или на автомате, НЕ через авто-переключатель стратегии РК.
- Кто пишет AdvSetting.strategy: корутина change_adv_strategy (manager.py:1894) — БЕЗ V3-фильтра, гейт только auto_update_strategy (default true) → крутит поле и у V3-РК ~каждые 60с. То есть флип MIN_CPO↔MAX_CONV латентно протекает в strategy_mode ключей БС/фикс.фраз при следующем keyword-write/sync/backfill.
- Достижимость: PROVEN. 8+ живых call sites синка: keywords_manager.py:107, wb_adv_updater/data_manager.py:671/713/811/818, relevant_phrase_manager.py:85, wb_manager.py:364, manager.py:1447, white_list_trimmer.py:71, v3_status_mode_backfill.py:46; ручные правки add_white_phrases.py:121, keyword_settings.py:736.
- Корневая причина (кто виноват, процессно, без персонального блейма): связка внесена БЕЗ Architecture Decision про ownership стратегии («кто владеет V3 keyword strategy_mode и связан ли он с V2 AdvSetting.strategy»). Коммиты: 080929364 (revoluxe-ai, 2026-05-26 «Add V3 strategy_mode synchronization and backfill logic»), 6e39cded4 (2026-06-04 «Add explicit adv_strategy parameter to sync calls»), b3cba16ec (2026-06-18). Change card-ab-hold-mode проблему НЕ создал — только вскрыл при freeze-анализе write-boundary.
- Нужный фикс (для отдельного change): развязать V3 keyword strategy_mode от AdvSetting.strategy; для фикс.фраз/БС — ручная или авто-установка независимо от change_adv_strategy. Оформить как OpenSpec proposal + decision v3-keyword-strategy-mode-ownership. Regression: флип AdvSetting.strategy не меняет strategy_mode фикс.фраз/БС; ручная/авто-установка позиций сохраняется. Verify: poetry run pytest tests\unit\test_v3_status_mode_sync.py -q.
- Связанные находки этой сессии (тоже НЕ вносились в код, отдельным решением): (1) change_adv_strategy не морозит AdvSetting.strategy во время A/B Hold PENDING/ACTIVE — нет filter_structural_act_candidates, в отличие от 6 siblings (spec-scope gap: strategy не перечислен в freeze-скоупе spec.md/decision §3); (2) предложено: A/B Hold enable требует automatic_version==3 (сейчас гейт только bot_active); (3) при card_ab_hold_mode ∈ {PENDING_SETUP, ACTIVE} запретить переход на V2 (toggle_auto_updater_version сейчас без гарда). Требуют /opsx-update card-ab-hold-mode + продуктовое решение Q: должен ли change_adv_strategy вообще работать для V3.
Связанные находки этой сессии:
(1) V3-gate для A/B Hold и запрет downgrade на V2 при PENDING_SETUP/ACTIVE реализованы в card-ab-hold-mode section 14.
(2) change_adv_strategy / AdvSetting.strategy не чинить внутри card-ab-hold-mode.
(3) Остаточный архитектурный долг: V3 keyword strategy_mode жёстко связан с AdvSetting.strategy. Разбирать отдельным change: decouple-v3-keyword-strategy-mode-from-adv-strategy.
Встроить в Cursor Codex, посмотреть что там за возможности
- навести порядок в веткаххх!!!!
провести ревизию доков в проекте

<!-- LEARNING_ENTRY_BEGIN -->

## LEARN-20260716-103045-pending-liveness

- status: captured
- optimization_status: pending
- captured_at: 2026-07-16T10:30:45+03:00
- source: opsx-learn-from-bug
- change_id: card-ab-hold-mode
- affected_area: card_ab_hold / PENDING_SETUP liveness / process_ab_setup / enable-flow
- promoted_to: none

### Raw learning input

Нашли очень опасный баг, по запаху: что-то нашел Багbot, затем начали проверять через команду bug-hunt, он квалифицировал как баг за пределами scope или что-то вроде этого, но потом я сбросил отчеты во внешний чат и выявили более глубокий и потенциально очень опасный баг.

1. Пользователь нажимает Enable A/B Hold.
2. Enable-flow проходит текущие гейты.
3. Код пишет card_ab_hold_mode = PENDING_SETUP / ENTER.
4. ordinary automation начинает исключать campaign, потому что mode != OFF.
5. На ближайшем setup tick process_ab_setup проверяет max_price_for_order.
6. Если max_price_for_order missing или <= 0 — setup просто return.
7. mode остаётся PENDING_SETUP.
8. На следующем тике повторяется то же самое.
9. Пользователь видит generic "Подготовка…", но не видит причину.

Bugbot (Cursor): Missing max CPO stalls PENDING — Medium. Симптом: при missing/non-positive max_price_for_order process_ab_setup return без снятия PENDING_SETUP.

Классификация по workflow:
- /opsx-fix-bug (literal early return в pipelines.py): false_positive — код соблюдает spec «не ACTIVE без snapshot»; sibling precedent пустой allowed-set → остаётся PENDING (test_setup_empty_allowed_set_aborts_before_active).
- /opsx-bug-hunt (PENDING_SETUP liveness invariant): needs_openspec_update — реальный liveness-hazard, но контракт слабый.
- /opsx-classify-bug: spec_bug — код следует принятым артефактам; виноват контракт, не early return.

Достижимость PROVEN:
- entrypoint: WBShopUpdateManager.adv_settings_auto_update @while_coroutine_decorator(5*60)
- chain: filter_ab_hold_pipeline_candidates(advs) → process_ab_setup
- ordinary exclusion PROVEN: manager.py V2/V3 loops continue if ab_mode != OFF; filter_structural_act_candidates drops PENDING/ACTIVE

Детерминированные блокеры setup (indefinite PENDING при excluded automation):
- plan_max <= 0 (max_price_for_order missing) — deterministic/user-fixable; ENTER не гейтит max CPO (гейты: bot_active, no-op, V3, freshness §2a, view-volume §2c)
- empty allowed_texts — mixed transient vs deterministic (all BAD / no keyword surface)

Нет: timestamp PENDING entry (models.py только card_ab_hold_mode/snapshot/degraded); owned setup-abort-to-OFF (только Telegram EXIT); actionable UI reason в enter_status (generic «Подготовка…»).

Правильный invariant (liveness):
Для durable mode/state, гейтящего ordinary automation, spec MUST: gate deterministic prerequisites до входа; post-entry deterministic blockers — user-visible actionable reason + bounded recovery / explicit retry class / owned abort; transient retry только если явно классифицирован; deterministic non-transient MUST NOT оставлять silent indefinite limbo при excluded automation.

Next command: /opsx-update card-ab-hold-mode (ENTER-гейт max_price_for_order>0; actionable PENDING status; recovery semantics). НЕ патчить process_ab_setup «move off PENDING» — неверная граница.

Попытка /opsx-learn-from-bug GO learning patch (config.yaml rules.specs + opsx-bug-hunt.md): REVERT — guard strict ввёл новые FAIL (config.yaml grew baseline +619; opsx-bug-hunt.md 8087>8001; scenarios opsx_continue/propose/update/verify). База уже over budget: rules.specs ~3512>3501 fail, rules section >14001. Пользователь: переполнение файлов проигнорируй при capture.

Предложенный текст learning patch (pending optimization):
- rules.specs: liveness semantics для durable mode, исключающего ordinary automation (4 пункта: entry gate prerequisites; post-entry actionable + recovery/retry/abort; transient explicit; no silent limbo)
- opsx-bug-hunt hard rule: durable state excluding automation = liveness surface; deterministic indefinite trap without entry gate/actionable reason/recovery/abort = candidate finding even without forbidden write

<!-- LEARNING_ENTRY_END -->

<!-- LEARNING_ENTRY_BEGIN -->

## LEARN-20260716-103130-dead-surface

- status: captured
- optimization_status: pending
- captured_at: 2026-07-16T10:31:30+03:00
- source: opsx-learn-from-bug
- change_id: card-ab-hold-mode
- affected_area: card_ab_hold / scheduling.py / dead surface after implementation
- promoted_to: none

### Raw learning input

3. [dead legacy] should_schedule_ordinary_updater is exported but never called

File: card_ab_hold/scheduling.py:38 (+ export in __init__.py)
Evidence: no call site in app/**. Ordinary V2/V3 exclusion is actually done via inline normalize_card_ab_hold_mode(...) != OFF checks in adv_settings_auto_update (587, 599, 611) — which are correct and cover both versions.
Risk: none functionally; only dead surface that can mislead future edits.
Recommended action: cleanup task (remove or wire it in), not a hotfix. No fix under this hunt.

Это уже не в первые раз: мертный код после имплементации. Тратим на это время.

Пользователь: Так это не баг в чистов виде? Править ничего не надо?

Ответ workflow: да, не production-баг. Вердикт plan_only / no_fix. Инвариант (ordinary V2/V3 только при OFF) уже enforced инлайном в manager.py:587/599/611. Мёртвый предикат unreachable из runtime.

Sibling dead surface (тот же паттерн, hunt отметил только 1 из 3):
- should_schedule_ordinary_updater (scheduling.py:38)
- should_run_ab_setup (scheduling.py:28)
- should_run_ab_hold (scheduling.py:33)
Все три: определены + экспортированы + callers только tests/**; runtime заменён filter_ab_hold_pipeline_candidates (manager.py:562) и inline != OFF.

Вариант A cleanup: удалить 3 предиката + exports + осиротевшие тест-ассерты; manager не трогать.
Вариант B wire-in: централизовать в scheduling.py по аналогии с filter_ab_hold_pipeline_candidates; семантика без изменений.

Learning patch APPLIED (GO):
- target: .cursor/commands/opsx-apply.md Guardrails +1 буллет (~220 chars):
  "After implementing tasks, treat any new production/exported symbol whose only callers are tests as dead surface: wire it into a runtime-reachable path or remove it before completion. Passing tests do not prove wiring."

Follow-up (пользователь выбрал cleanup_first):
1) Сначала reduction-only чистка pre-existing guard FAIL (config.yaml::rules, rules.specs, scenario opsx_verify baseline stale) — без бампа baseline, ~285 chars уплотнения rules.specs.
2) Потом enforceable verify-backstop: rules.verify NO_GO + opsx-verify.md + бамп openspec_guard.yaml baselines.

Пользователь: /opsx-learn-from-bug Проведи обучение, переполнение файлов проигноруй

Предложенный текст learning patch (pending optimization, после cleanup):
- rules.verify: Verify должен ставить NO_GO, если change добавил production/exported символ, у которого единственные callers — тесты (dead surface); test-only reachability не доказывает wiring.
- opsx-verify.md: одна проверка step 6 + NO_GO step 8 (dead surface / test-only reachability).

<!-- LEARNING_ENTRY_END -->



### Deferred: ClickHouse enable-path performance risk

Discovered during `card-ab-hold-mode` review.

The change reuses existing ClickHouse freshness and keyword-view readers. Static review found:

* `clusters_adv_stats` freshness query filters by `adv_id`, while `adv_id` is not in the table `ORDER BY` prefix;
* reused enable-path reads have semaphore/acquire protection but may lack a bounded operation timeout.

Disposition:

* pre-existing shared ClickHouse debt;
* not a blocker for `card-ab-hold-mode` without production `EXPLAIN indexes=1`, `system.query_log` metrics or an observed timeout;
* do not add an index, projection, MV or schema change inside the current change;
* investigate separately after release;
* consider reuse of `mv_clusters_daily_agg.ts_state` only after proving semantic equivalence.

Provenance: discovered while reviewing `card-ab-hold-mode`; root cause predates the change.

opsx-bug-team to commant native

opsx-bug-team - тест развилки от bug-hunt

тесты на команды и team

## Deferred from change card-ab-hold-mode (2026-07-28)

Parked via `/opsx-bound-scope:GO` — not owed DoD of current change until
`/opsx-update` + `REENTER_CONFIRMED`.

- [ ] [deferred-from:card-ab-hold-mode] Pre-start safety policy picker (hard|soft|self)
  source: owner TZ (explore) + openspec/changes/card-ab-hold-mode/proposal.md (Out of scope / risk context)
  reason: out_of_current_mvp | owner_park
  notes: До старта эксперимента выбор — жёсткая (abort/reset при сбое статы), мягкая (freeze decide; возможен ограниченный перерасход), сам слежу (+ аварийная кнопка). Сейчас change не раздувать; future change e.g. ab-hold-safety-policy-modes.

- [ ] [deferred-from:card-ab-hold-mode] Anti-drain emergency kill switch
  source: owner TZ (explore); related OUT_OF_SCOPE_FOLLOW_ON emergency-stop in proposal.md (product anti-drain ≠ financial latch)
  reason: out_of_current_mvp | owner_park
  notes: Не просто EXIT из Hold — аварийное гашение трат (ключи/пауза/блок). Отдельная продуктовая идея; не смешивать с Forbidden §18 epoch spend cap / financial latch в текущем Hold.

- [ ] [deferred-from:card-ab-hold-mode] Mid-sync stale UX options (wait|force-apply|EXIT)
  source: owner TZ (explore)
  reason: oversized | owner_park
  notes: Не обязательный MVP. Форс apply snapshot / честное ожидание — возможны позже внутри soft; сейчас не owed DoD.

## Bound confirmed card-ab-hold-mode (2026-07-30)

Via `/opsx-bound-scope:GO` — no new deferred checklist rows (picker / anti-drain /
mid-sync already parked 2026-07-28; skip_reappend).

KEEP_MVP_BOUNDARY (owed now, handoff → `/opsx-update`):
- Soft-only: freeze decide-class on stale, including epoch-managed setup FAIL→OFF
  (close PBH-001 / ROOT-001 hole under §17); do not abort/reset epoch on stale alone;
  PBH-005 apply-snapshot carve-out unchanged.
- Soft-policy RU disclaimer at Enable and/or hold status (user monitors test;
  wording must not say «ослабим защиту» if behavior is freeze-decide).
- Pre-start hard|soft|self picker, anti-drain, mid-sync UX — remain out of DoD
  until REENTER_CONFIRMED.

## Deferred from change openspec-guard-size-recovery (2026-07-30)

Parked via `/opsx-bound-scope:GO` — not owed DoD of any current OpenSpec change
until `/opsx-new` (or equivalent) + `/opsx-update` + `REENTER_CONFIRMED`.
No `openspec/changes/openspec-guard-size-recovery/` folder yet (WORKLOG-only park).

- [ ] [deferred-from:openspec-guard-size-recovery] Guard size recovery / openspec compress tooling
  source: /opsx-admin-command-design-command (OPTION_A recommended; OPTION_B optional) + explore 2026-07-30
  reason: out_of_current_mvp | owner_park | needs_test_design
  notes: Сложная команда; нужен способ тестировать. Сейчас НЕ implement.
    OPTION_A: playbook при guard FAIL + ranked offenders в /opsx-update(+siblings) + guard --report-offenders.
    OPTION_B: /opsx-admin-openspec-size-reduce (GO-gated), FORBIDDEN default write openspec/changes/**.
    ≠ /opsx-bound-scope (scope drift ≠ char shrink).
    Временно: baseline opsx_update bumped to 89948 (2026-07-30) — не вечный substitute for reduce.

- [ ] [deferred-from:openspec-guard-size-recovery] Test strategy for guard reduce / recovery
  source: owner (explore/design follow-up)
  reason: oversized | owner_park
  notes: Придумать harness: synthetic oversized fixture → FAIL → plan → GO reduce → GREEN;
    запрет semantic loss на process contracts; не трогать product change specs.

Анализ материализации решения багов для обучения системы супер-классам ошибок
Внедрить практики, риски

Сделать мета-команды по ремонту-доработке обучению команд, которые обслуживают другие команды


сжать и вернуть лимиты [openspec_guard.yaml](https://github.com/revoluxe-ai/adv-bot/blob/dcc432e9297566c380de9888c4955f37bff54a00/tools/openspec/openspec_guard.yaml#L57)

## Deferred from change fix-bug-with-remove-ch-db-name-from-queries (2026-07-31)

Parked via `/opsx-bound-scope:GO` — not owed DoD of current change until
`/opsx-update` + `REENTER_CONFIRMED`.

- [ ] [deferred-from:fix-bug-with-remove-ch-db-name-from-queries] CH database from env → client.database
  source: explore NOW_LATER + owner split (2026-07-31); openspec/changes/fix-bug-with-remove-ch-db-name-from-queries/proposal.md (Scope out)
  reason: out_of_current_mvp | owner_park
  notes: Host/user/password уже из env; database в client hardcoded. Полный env wiring — отдельно от фикса «DB в тексте CH query».

- [ ] [deferred-from:fix-bug-with-remove-ch-db-name-from-queries] Mass CH SQL qualification / unqualify strategy
  source: explore + owner park (2026-07-31)
  reason: oversized | owner_park
  notes: Не трогать все CH readers в этом change. После фикса текущего класса багов — отдельная волна + возможно ADL.

- [ ] [deferred-from:fix-bug-with-remove-ch-db-name-from-queries] Reusable ADL: CH DB qualification policy
  source: explore Architecture Decision Missing (2026-07-31)
  reason: out_of_current_mvp
  notes: Env vs hardcoded default_db vs unqualified+client.database — registry later; сейчас change-local MUST qualify in CH SQL.

## Deferred from change drop-unused-neo4j-config (2026-08-01)

Raw notes from `/opsx-bound-scope:GO`. Not current change DoD. Return via `/opsx-update` + `REENTER_CONFIRMED`.

- [ ] [deferred-from:drop-unused-neo4j-config] Зачистка docs/docker/monitoring Neo4j
  source: openspec/changes/drop-unused-neo4j-config/proposal.md (Out of scope); design Non-Goals
  reason: out_of_current_mvp
  notes: FACT_SHEET, k8s/monitoring/NEO4J_*, dockers/neo4j — не блокируют AppConfig

- [ ] [deferred-from:drop-unused-neo4j-config] Удалить commented ML/graph Neo4j-код и entry scripts
  source: proposal Out of scope; design Non-Goals
  reason: oversized | out_of_current_mvp
  notes: graph_vector_updater / hard_ml / run_update_cards_data_in_neo4j — уже не runtime

- [ ] [deferred-from:drop-unused-neo4j-config] Починить или удалить image_master2._neo4j методы
  source: design Non-Goals
  reason: out_of_current_mvp
  notes: __init__ не создаёт _neo4j; не hot path shop-runner

- [ ] [deferred-from:drop-unused-neo4j-config] Cluster teardown live Neo4j (если ещё в cluster)
  source: proposal Out of scope; explore Unconfirmed
  reason: owner_park | infra
  notes: отдельный infra GO; не часть appconfig change

- [ ] [deferred-from:drop-unused-neo4j-config] Прочие unit-кластеры после Neo4j (TG_TOKENS, shelf, calculated_keywords)
  source: proposal Out of scope
  reason: out_of_current_mvp
  notes: отдельные triage; не смешивать с drop Neo4j config

внедрить нагрузочные тесты