# ТЗ Нового модуля управления ставкой

# Техническое задание (ТЗ)

Система: обновление CPM-ставок в поисковых рекламных кампаниях Wildberries.

Цель: обеспечить стабильную работу конвейера расчёта и отправки новых ставок с учётом позиций, ограничений и политики ошибок.

## 1. Термины и сокращения

- Adv (advert): рекламная кампания в WB.
- nmid: идентификатор артикула WB.
- CPM bid (cpm): ставка в рекламной кампании WB.
- DTO: объект передачи данных между слоями.

## 2. Область работ (Scope)

Реализовать/доработать:

- Локальные WB API менеджеры чтения/записи ставок (тонкие обёртки над адаптерами).
- Менеджер UpdateCPMManager, считающий новые ставки параллельно (Futures + TaskGroup).
- Оркестратор BidUpdateOrchestrator по схеме producer-consumer с очередью и батчингом на отправку в WB.
- Политику ошибок, таймауты, уровни логирования.
- Получение текущей позиции из Redis (заглушка) и skip-правила.
- Минимальный DI wiring для сборки зависимостей под задачу.

Вне scope: любые функции парсера позиций, UI, БД-схемы и миграции.

## 3. Архитектурные решения

- Все сетевые вызовы к WB выполняются через адаптер PromotionAdapter. Ретраи и 401 обрабатываются ТОЛЬКО в адаптерах. Менеджеры исключения не глушат, не ретраят.
- Параллелизм: вычисление new_bid для разных nmid — через asyncio.TaskGroup и Futures.
- Отправка в WB: producer складывает результаты в asyncio.Queue, один consumer агрегирует по adv_id, режет по max_batch_size и вызывает Updater для PATCH.

## 4. Контракты интерфейсов

### 4.1 PromotionAdapter

Примечание по current bids для кампаний с ручной ставкой:

- Источник текущей ставки кампании (manual bid): GET /adv/v0/auction/adverts. Используем поле [bids.search](http://bids.search) из ответа как текущую ставку кампании по зоне поиска и маппим её на все nmids этой кампании, т.к. при ручной ставке она едина для кампании.[[1]](https://dev.wildberries.ru/openapi/promotion)
- Если кампания не в режиме ручной ставки или зона search отсутствует в ответе — считаем, что данных нет, и возвращаем пустой dict (менеджер трактует current_bid как 0, с debug-логом).
- get_min_bids(client, adv_id: int, nmids: list[int], timeout=5.0) -> dict[int, int]
- get_current_bids(client, adv_id: int, nmids: list[int], timeout=5.0) -> dict[int, int]
- update_bids(client, payload: PatchAdvV0BidsBody, timeout=10.0) -> None
    - PatchAdvV0BidsBody: { bids: list[V0AdvertMultibid] }
    - V0AdvertMultibid: { advert_id: int, nm_bids: list[V0AdvertMultiBidItem] }
    - V0AdvertMultiBidItem: { nm: int, cpm: int }

Требования:

- 401 — через token_refresh_decorator (обновление токена и повтор запроса).
- Ретраи сетевых/5xx: 3 попытки, backoff 0.5/1/2 сек; на попытках — error, после исчерпания — critical и raise.
- Таймауты: GET=5s, PATCH=10s.

### 4.2 WBApi менеджеры (тонкие обёртки)

WBApiDataGetter:

- get_min_bid_for_nmids(shop_id, *, adv_id, nmids) -> dict[int, int]
- get_current_bids(shop_id, *, adv_id, nmids) -> dict[int, int]

WBApiCpmUpdater:

- update_bids(shop_id, *, adv_id, nm_bids: list[{nm:int, cpm:int}]) -> None
- Формирует PatchAdvV0BidsBody с единичным V0AdvertMultibid(advert_id=adv_id, nm_bids=[...]) и вызывает PromotionAdapter.update_bids(...).

### 4.3 DTO входа в расчёт

UpdateBidsInSearchAdvDTO:

- adv_id: int
- nmids: list[int]
- target_position: int
- max_cpm_bid: int
- min_bid: int | None
- bidder_step: int | None
- calculated_keywords_coro: Coroutine[Any, Any, Optional[CalculatedKeyword]]

### 4.4 Redis позиции

- KeywordPosition: { position: int }
- RedisManager.get_keyword_position(text: str, nmid: int) -> Optional[KeywordPosition]

Правило: position == 0 или None — неприменимая позиция (skip).

## 5. Логика UpdateCPMManager

- Конструктор сохраняет shop_id и инициализирует: WBApiDataGetter, WBApiCpmUpdater, RedisManager.
- __get_update_batch(tg, dtos): для каждого DTO создаёт Futures: best_keyword, min_bids, current_bids; для каждого nmid — Future новой ставки; сеттеры запускаются в общем TaskGroup.
- _get_new_bid(...):
    - Получает kw из best_keyword. Если None — debug и skip.
    - Получает min_map и curr_map. Ошибки адаптера не глушатся (см. §7).
    - min_bid = min_map.get(nmid, dto.min_bid or 0); current_bid = curr_map.get(nmid, 0).
    - pos = RedisManager.get_keyword_position(kw.text, nmid); если not pos или pos.position in {0, None} — debug и skip.
    - Считает через BidCalculator(BidCalculationParams):
        - current_bid, min_bid, max_bid = dto.max_cpm_bid, current_position=pos.position,
            
            target_position=[dto.target](http://dto.target)_position, bidder_step=dto.bidder_step or 2.
            
    - Если calculate_new_bid вернул None или new_bid == current_bid — debug и skip.
    - Возвращает int(new_bid).

## 6. Оркестратор (BidUpdateOrchestrator)

- Инициализация: shop_id, cpm_updater, max_batch_size=50, queue_size=200.
- Producer: ждёт [task.new](http://task.new)_bid_coro, кладёт BidUpdateResult(adv_id, nmid, new_bid) в очередь если new_bid != None.
- Consumer: циклически читает очередь, агрегирует batch, отстреливает по таймауту 1 сек или при заполнении, вызывает _send_batch(batch).
- _send_batch(batch):
    - Группирует по adv_id в nm_bids: list[{nm, cpm}].
    - Режет на чанки по max_batch_size и вызывает WBApiCpmUpdater.update_bids(shop_id, adv_id, nm_bids=chunk).

## 7. Политика ошибок

- API-ошибки адаптера: ретраим 3 раза; при исчерпании — logging.critical и исключение вверх, процесс падает.
- Ошибки логики (например, валидация BidCalculationParams) — logging.critical и исключение вверх, процесс падает.
- Не критично и не падаем: нет позиции, нет лучшего ключа, новая ставка не меняется — logging.debug и skip.

## 8. Логирование

- Уровни: debug, error, critical. Без info.
- Примеры:
    - debug: причины skip, шаги расчёта.
    - error: «API attempt k/3 failed: <e>» внутри адаптера.
    - critical: «API failed after 3 attempts: <e>»; «logic error: <e>».

## 9. Таймауты и параллелизм

- Адаптер: GET=5s, PATCH=10s. Batch бюджет ≈ 15s.
- Оркестратор: consumer таймаут ожидания элемента — 1s.
- Расчёты и сеттеры запускаются внутри одного asyncio.TaskGroup для централизованной отмены при критической ошибке.

## 10. DI wiring (пример)

- Создание под задачу свежих экземпляров зависимостей через контейнер.

Пример (псевдокод):

```python
from dependency_injector import containers, providers

class WBApiClients(containers.DeclarativeContainer):
    client_factory = providers.Factory(WBClientFactory)
    promotion_adapter = providers.Factory(PromotionAdapter)

class Services(containers.DeclarativeContainer):
    wb = providers.Container(WBApiClients)
    data_getter = providers.Factory(WBApiDataGetter, promotion_adapter=wb.promotion_adapter, client_factory=wb.client_factory)
    cpm_updater = providers.Factory(WBApiCpmUpdater, promotion_adapter=wb.promotion_adapter, client_factory=wb.client_factory)
```

## 11. Acceptance criteria

- При отсутствующей позиции (0/None) ставки по соответствующим nmid пропускаются без падения, в логах debug-причина.
- При недоступности WB API после 3 попыток с backoff — критическая ошибка, процесс завершается с исключением.
- PATCH формируется строго по контракту PatchAdvV0BidsBody с группировкой по adv_id и чанками до 50 nmid.
- Ретраи и 401 отсутствуют на уровне менеджеров, присутствуют в адаптерах.
- Все указанные сигнатуры методов и DTO соответствуют реализованным функциям.

## 12. Минимальные тест-кейсы

- min_bids недоступны (после ретраев) → critical и исключение.
- current_bids недоступны (после ретраев) → critical и исключение.
- position == 0 → skip без исключения.
- new_bid == current_bid → skip без исключения.
- Корректная отправка: 120 nmid в одной Adv → 3 PATCH вызова по 50, 50, 20.
- Негативная валидация BidCalculationParams (min_bid > max_bid) → critical и исключение.

## 13. Пример кода (фрагменты)

### Adapter

```python
class PromotionAdapter:
    @token_refresh_decorator
    async def get_min_bids(self, *, client, adv_id: int, nmids: list[int], timeout: float = 5.0) -> dict[int, int]:
        ...
    @token_refresh_decorator
    async def get_current_bids(self, *, client, adv_id: int, nmids: list[int], timeout: float = 5.0) -> dict[int, int]:
        ...
    @token_refresh_decorator
    async def update_bids(self, *, client, payload: PatchAdvV0BidsBody, timeout: float = 10.0) -> None:
        ...
```

### UpdateCPMManager._get_new_bid (ядро)

```python
params = BidCalculationParams(
    current_bid=current_bid,
    min_bid=min_bid,
    max_bid=int(max_bid),
    current_position=int(pos.position),
    target_position=int(target_position or 5),
    bidder_step=int(bidder_step or 2),
)
new_bid = BidCalculator().calculate_new_bid(params)
if new_bid is None or int(new_bid) == int(current_bid):
    return None
return int(new_bid)
```

### Orchestrator._send_batch

## 14. Уточнения и решения (финал)

Ниже — финальные ответы на вопросы разработчика. Эти правила считаются частью ТЗ и обязательны к реализации.

### 14.1 PATCH формат и батчинг

- Payload строго: PatchAdvV0BidsBody { bids: list[V0AdvertMultibid] }, V0AdvertMultibid { advert_id, nm_bids: list[{nm, cpm}] }.
- Один HTTP PATCH — один advert_id и до 50 nm_bids. Если >50, отправляем несколько PATCH подряд для этой кампании.
- Оркестратор группирует по adv_id и режет nm_bids чанками по 50.

### 14.2 PromotionAdapter (эндпоинты, таймауты, ретраи)

- Реализовать:
    - get_min_bids(client, adv_id, nmids, timeout=5s) -> dict[int,int]
    - get_current_bids(client, adv_id, nmids, timeout=5s) -> dict[int,int]
    - update_bids(client, payload, timeout=10s) -> None
- Ретраи и 401 только в адаптере: 3 попытки, backoff 0.5/1/2; попытки — error, исчерпание — critical+raise. 401 — через token_refresh_decorator; повтор после рефреша. Повторный 401 после рефреша на последней попытке приведёт к critical и raise.
- Если в сгенерированном клиенте нет готовых методов для min/current, допустима временная заглушка (возвращать {}), пометить TODO с точным указанием требуемых эндпоинтов. Предпочтительно сразу подключить корректные вызовы.

### 14.3 Тонкие WBApi менеджеры

- Создать WBApiDataGetter и WBApiCpmUpdater. Они НЕ делают ретраи — только вызывают адаптеры.
- DataGetter: get_min_bid_for_nmids и get_current_bids.
- Updater: update_bids(shop_id, adv_id, nm_bids=[{nm,cpm}]). Формирует 1 V0AdvertMultibid и вызывает PromotionAdapter.update_bids.

### 14.4 DTO и параллелизм в UpdateCPMManager

- calculated_keywords_coro может возвращать список. Внутри менеджера выбираем лучший keyword.
- Для одного adv делаем по одному запросу на min_bids и current_bids для всего списка nmids.
- bidder_step: если None — использовать 2.

### 14.5 Расчёт ставки и дефолты

- Позиция None или 0 — debug + skip.
- new_bid is None или new_bid == current_bid — debug + skip.
- Ошибки валидации (напр. min_bid > max_bid) — critical + raise.
- current_bid по умолчанию 0, если не вернулся. Логировать debug «нет текущей ставки, считаем от 0» и продолжать.
- int(new_bid) достаточно, дополнительная квантизация не нужна. Калькулятор ограничивает ставку в [min_bid, max_bid]. Нижний порог 0 уже обеспечен через эти границы.
- Если min_bid не пришёл и dto.min_bid не задан — использовать 0. Это не логическая ошибка.

### 14.6 Redis позиции

- Используем поле position (не promo_position). Вызов асинхронный, при 0/None — skip.
- Ключ для позиции: best_keyword.text без нормализации. Если в вашей системе хранения позиций применяется нормализация, использовать одинаковую нормализацию при записи и чтении.

### 14.7 Оркестратор

- Реализовать новую версию по ТЗ: один consumer, timeout 1s, группировка по adv_id, резка по max_batch_size, вызов WBApiCpmUpdater. Старые реализации не используем (можно оставить файлы, но вызывать новый оркестратор).
- 0 — валидная ставка: если new_bid == 0 и отличается от current_bid, её отправляем. В очередь кладём все new_bid != None.

### 14.8 Логирование и падения

- Уровни: только debug, error, critical (без info) во всех новых компонентах.
- При critical прокидываем исключение наружу, процесс падает — это ожидаемое поведение.

### 14.9 Таймауты и общий бюджет

- Адаптер-таймауты (GET 5s, PATCH 10s) обязательны.
- Общий лимит 15s на batch можно не вводить. По желанию можно обернуть batch в asyncio.timeout(15) и при истечении времени логировать critical и падать.

### 14.10 DI / wiring

- Используем существующий DI слой (inject/mixins). Внедряем PromotionAdapter и ClientFactory в WBApiDataGetter/WBApiCpmUpdater. Переход на dependency_injector не обязателен.

### 14.11 Тесты

- Добавить/обновить unit-тесты под новый контракт: критические падения при недоступности min/current, корректная резка батчей, skip при позиции 0/None и при неизменной ставке, валидационные ошибки калькулятора.

### 14.12 Совместимость с существующим кодом

## 15. ТокенМенеджер (TokenManager)

Цель: централизованное управление токенами WB для каждого магазина (shop_id), с учётом отказов, чёрных списков на период выполнения, обновления из БД и интеграции с token_refresh_decorator в адаптерах.

### 15.1 Требования и поведение

- Экземпляр TokenManager на каждый shop_id (scoped per shop). В рамках одного процесса — singleton на shop_id.
- Источник истины по токенам — БД. При инициализации и исчерпании пула менеджер загружает список валидных токенов из БД.
- Контекст «раздела» (scope/section): токены сегментируются по разделам использования (например: promotion_api, auction_api, reports и т.п.). Менеджер ведёт независимые пулы токенов по разделам.
- Не рабочие токены в рамках текущего окна выполнения помещаются в чёрный список (in-memory blacklist) для соответствующего раздела.
- При 401 (или «доступ запрещён» по спецификации клиента) адаптерный декоратор сообщает менеджеру о нерабочем токене. Менеджер помечает токен как bad для раздела и на следующей итерации выдает новый токен из пула.
- Если токены раздела исчерпались (все оказались bad), менеджер выполняет принудительное обновление пула из БД и сбрасывает in-memory blacklist. Если после обновления список пуст — поднимается исключение NoAvailableTokensError.
- Потокобезопасность/асинхронность: операции получения/возврата токенов и пометки bad защищены asyncio.Lock на уровне раздела.
- Кэширование: в памяти хранится текущий пул и blacklist до конца процесса или до явно заданного TTL (настройка). При refresh из БД пул полностью заменяется.
- Метрики/логи: debug при выдаче токена; warning при пометке как bad; critical при отсутствии токенов после refresh.

### 15.2 Контракты интерфейса

```python
class TokenManager:
    def __init__(self, shop_id: str, repo: TokenRepository, *, ttl_seconds: int | None = None):
        ...
    async def get_token(self, section: str) -> str:
        """Выдать рабочий токен для заданного раздела (например, 'promotion_api').
        Если текущий токен помечен как bad или отсутствует — выдать следующий.
        При исчерпании пула — refresh из БД. Если пусто — NoAvailableTokensError.
        """
    async def mark_bad(self, section: str, token: str, *, reason: str | None = None) -> None:
        """Пометить токен как нерабочий в рамках раздела (in-memory blacklist)."""
    async def refresh_from_db(self, section: str) -> None:
        """Принудительно обновить пул токенов из БД для раздела и очистить blacklist."""
```

TokenRepository (пример контракта):

```python
class TokenRepository:
    async def get_tokens(self, shop_id: str, section: str) -> list[str]:
        """Вернуть актуальный список токенов из БД для shop_id и раздела."""
```

### 15.3 Интеграция с адаптерами (token_refresh_decorator)

- token_refresh_decorator при выполнении запроса получает токен через TokenManager.get_token(section) и устанавливает его в клиент.
- При перехвате 401/доступ запрещён декоратор вызывает TokenManager.mark_bad(section, token, reason='401') и повторяет запрос с новым токеном (до исчерпания попыток ретрая в адаптере).
- Если адаптер исчерпал попытки (включая смены токенов) — поднимается исключение (critical лог в адаптере), управление выходит вверх по цепочке.

Псевдокод декоратора:

```python
def token_refresh_decorator(fn):
    async def wrapped(self, *args, **kwargs):
        section = kwargs.pop('token_section', 'promotion_api')
        tm: TokenManager = self.token_manager  # внедряется через DI
        attempt = 0
        last_exc = None
        while True:
            token = await tm.get_token(section)
            client = self.client_factory.get_client(shop_id=kwargs['client'].shop_id, token=token)
            try:
                return await fn(self, *args, client=client, **kwargs)
            except ClientError as e:
                if e.status_code == 401:
                    await tm.mark_bad(section, token, reason='401')
                    attempt += 1
                    last_exc = e
                    # переход к новой попытке со следующим токеном
                    continue
                raise
        raise last_exc
    return wrapped
```

Примечания:

- Проверка 401 должна соответствовать типу исключения вашего HTTP-клиента. Допустимы варианты e.status_code==401 или e.response.status==401.
- Раздел section должен задаваться явно из вызова адаптера: для методов PromotionAdapter использовать section='promotion_api'; для аукционных — 'auction_api', и т.п.

### 15.4 Формат хранения и выбор токена

- Порядок выбора: round-robin по списку токенов, исключая токены из blacklist.
- blacklist хранится в множестве per section: bad_tokens[section]: set[str].
- При refresh_from_db TokenManager полностью заменяет пул tokens[section] и очищает bad_tokens[section].
- TTL (опционально): если задан ttl_seconds, по истечении TTL при первом запросе выполняется автоматический refresh_from_db.

### 15.5 DI и область жизни

- TokenManager внедряется через DI как factory per shop_id: один экземпляр на магазин.
- PromotionAdapter и любые сервисы, которым нужен токен, получают ссылку на TokenManager из DI.

Пример wiring:

```python
class Services(containers.DeclarativeContainer):
    token_repo = providers.Factory(TokenRepository)
    token_manager_factory = providers.Factory(TokenManager, repo=token_repo)

# получение менеджера под задачу
async def build_for_shop(shop_id: str):
    token_manager = Services.token_manager_factory(shop_id=shop_id)
    adapter = PromotionAdapter(token_manager=token_manager, client_factory=WBClientFactory())
    return token_manager, adapter
```

### 15.6 Логирование и метрики

- debug: выдача токена, refresh из БД (с количеством токенов), причины skip в выборке.
- warning: пометка токена как bad (section, shop_id, причина).
- critical: отсутствие токенов после refresh, исключение NoAvailableTokensError.
- Метрики: счётчики bad-токенов, успешных/неуспешных refresh, распределение по разделам.

### 15.7 Тест-кейсы для TokenManager

- Выдача токенов по round-robin, исключая blacklist.
- Пометка токена как bad → следующий вызов get_token не возвращает его.
- Исчерпание пула → вызов refresh_from_db и повторная выдача.
- Пустая БД после refresh → NoAvailableTokensError и critical лог.
- Параллельные get_token/mark_bad под одним section не приводят к гонкам (покрыть с asyncio.gather).
- Интеграция с декоратором: первая попытка 401 помечает token bad и повторяет вызов с новым токеном; при исчерпании — исключение.
- UpdateCPMManager переписать по ТЗ, старые незавершённые участки законсервировать/не использовать.
- Старые оркестраторы — не использовать в новых вызовах, подключить новый по ТЗ.
- PromotionV1Adapter: привести payload к V0AdvertMultibid-формату (advert_id + nm_bids[{nm,cpm}]) и добавить ретраи/таймауты.
- Везде унифицировать на position вместо promo_position.
- Убрать info-логи в затронутых модулях.

```python
grouped: dict[int, list[dict[str, int]]] = {}
for r in batch:
    if [r.new](http://r.new)_bid is None:
        continue
    grouped.setdefault(r.adv_id, []).append({"nm": int(r.nmid), "cpm": int([r.new](http://r.new)_bid)})
for adv_id, nm_bids in grouped.items():
    for i in range(0, len(nm_bids), self._max_batch_size):
        chunk = nm_bids[i:i + self._max_batch_size]
        await self._cpm_updater.update_bids(self._shop_id, adv_id=adv_id, nm_bids=chunk)
```