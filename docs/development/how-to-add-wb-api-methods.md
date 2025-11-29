### Инструкция: как быстро собрать новый высокоуровневый метод над WB API

---

#### 1. Определи контекст и менеджер
- **Выбери доменного менеджера** (`app/core/mp/wb/api/domain_managers/...`).
  Например, методы по работе с продвижением идут в `PromotionManager`.
- Если менеджера нет — создай файл и зарегистрируй его в DI-контейнере (`app/core/di/...`).

---

#### 2. Найди адаптер секции WB API
- Все клиенты и адаптеры лежат в `app/core/mp/wb/api/adapter`.
- Для Promotion секции используем `promotion_client`. Там:
  - `PromotionClient` агрегирует секционные адаптеры.
  - Каждый адаптер (`minus_phrases.adapter`, `keywords.adapter` и т.д.) знает, как вызвать конкретные методы WB API.
- В менеджер передаётся `PromotionClient`, из него берём нужный адаптер через property.

```python
# app/core/mp/wb/api/adapter/promotion_client/promotion_client.py
class PromotionClient:
    def __init__(self, minus_phrases_adapter: MinusPhrasesAdapter) -> None:
        self.__minus_phrases_adapter = minus_phrases_adapter

    @property
    def minus_phrases_adapter(self) -> MinusPhrasesAdapter:
        return self.__minus_phrases_adapter
```

---

#### 3. Найди сгенерированный метод WB API
- Сгенерированный клиент лежит в `app/core/mp/wb/api/generated`.
  Структура: `generated/<section>/<service>/api/<resource>/<method>.py`.
- Внутри будет функция `asyncio_detailed` (или аналогичная), модель запроса и `Response`.

---

#### 4. Создай слой адаптера
1. В папке адаптера (`app/core/mp/wb/api/adapter/promotion_client/<feature>/`)
   создай файлы:
   - `command.py` — dataclass с полями бизнес-уровня.
   - `__init__` под реэкспорт.
   - `<method_name>.py` — функция `command_to_body`, которая переводит `Command` в сгенерированную модель.
2. В `adapter.py` добавь асинхронный метод, который:
   - принимает `Command`,
   - конвертирует в body,
   - берёт `client = await self.auth_client_handler.get_proxy_client(self)`,
   - вызывает `with_raise_errors(asyncio_detailed, client, body)`,
   - добавляет `@retry_decorator` при необходимости.

```python
# app/core/mp/wb/api/adapter/promotion_client/minus_phrases/command.py
@dataclass
class SetMinusPhrasesCommand:
    advert_id: int
    nm_id: int
    norm_queries: list[str]

# app/core/mp/wb/api/adapter/promotion_client/minus_phrases/adapter.py
class MinusPhrasesAdapter(BaseSectionAdapter):
    @retry_decorator(period=1, limit=5)
    async def post_adv_v0_normquery_set_minus(
        self, command: SetMinusPhrasesCommand
    ) -> None:
        body = command_to_body(command)
        client = await self.auth_client_handler.get_proxy_client(self)
        await with_raise_errors(asyncio_detailed, client, body)
```

---

#### 5. Высокоуровневый метод в доменном менеджере
- В нужном менеджере импортируй `request` из `domain_managers/.../methods/...`.
- Создай `Command` и передай в адаптер напрямую, либо через helper-функцию (`request`) для общих сценариев.

```python
# app/core/mp/wb/api/domain_managers/promotion/promotion_manager.py
from .methods.set_minus_phrases import request
from app.core.mp.wb.api.adapter.promotion_client.minus_phrases.post_adv_v0_normquery_set_minus.command import (
    SetMinusPhrasesCommand,
)

class PromotionManager:
    ...

    async def set_minus_phrases(
        self, advert_id: int, nm_id: int, phrases: list[str]
    ) -> None:
        command = SetMinusPhrasesCommand(
            advert_id=advert_id, nm_id=nm_id, norm_queries=phrases
        )
        await request(
            self._client.minus_phrases_adapter.post_adv_v0_normquery_set_minus,
            command,
        )
```

(Если helper уже создаёт `Command`, менеджер может просто передавать примитивные аргументы.)

---

#### 6. Слой `methods`
- Каждая доменная операция имеет файл `domain_managers/<...>/methods/<method>.py`.
- Функция `request` принимает строго типизированный `Callable[[Command], Awaitable[None]]`.
  Здесь размещаем дополнительную бизнес-логику: валидации, логирование, преобразования.

```python
# app/core/mp/wb/api/domain_managers/promotion/methods/set_minus_phrases.py
async def request(
    method: Callable[[SetMinusPhrasesCommand], Awaitable[None]],
    advert_id: int,
    nm_id: int,
    phrases: list[str],
) -> None:
    command = SetMinusPhrasesCommand(
        advert_id=advert_id, nm_id=nm_id, norm_queries=phrases
    )
    await method(command)
```

(Если helper уже создаёт `Command`, менеджер может просто передавать примитивные аргументы.)

---

#### 7. Типизация и pyright
- Всегда импортируй конкретные типы (`SetMinusPhrasesCommand`, `Callable[[...], Awaitable[...]]`).
- Не используй `Any`, если можно описать тип (иначе получишь `reportUnknownVariableType`).
- В адаптерах аннотируй возвращаемые типы (`-> None`), чтобы pyright видел полную сигнатуру.
- В менеджере аннотируй аргументы и возвращаемое значение.

---

#### 8. DI и проброс
- Зарегистрируй адаптер и менеджер в контейнерах (`app/core/di/...`).
  Обычно: адаптер в `AdapterContainer`, секционный клиент в `ClientContainer`, менеджер в `DomainManagerContainer`.
- Убедись, что нужный контейнер отдаёт менеджер туда, где он будет использоваться (например, в сервисах `app/modules/...`).

---

#### 9. Проверка
1. `poetry run pyright app/core/mp/wb/api/domain_managers/.../promotion_manager.py`
2. `poetry run pytest` (или более узкие тесты).
3. При необходимости добавь тесты для `request`/менеджера (можно мокать адаптер через `AsyncMock`).

---

### Чеклист: шаги при добавлении нового метода
1. [ ] Определить доменный менеджер (и добавить его в DI, если нового нет).
2. [ ] Найти или создать секционный адаптер + команду.
3. [ ] Смаппить команду на сгенерированную модель.
4. [ ] Реализовать асинхронный метод адаптера с retry/raise_errors.
5. [ ] Добавить helper `request` (если есть общая логика).
6. [ ] Добавить метод в менеджер, создать `Command`, вызвать адаптер.
7. [ ] Пробросить менеджер через DI до места использования.
8. [ ] Проверить pyright и тесты.

С этой схемой достаточно один раз назвать желаемый high-level метод (`“нужно обновлять X в продвижении”`), и по шагам можно без лишних вопросов реализовать его для WB API.
