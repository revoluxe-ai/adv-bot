# 🔍 Code Review Checklist для модуля WB API

Этот чеклист обеспечивает качество кода и соответствие архитектурным принципам при review изменений в модуле `app/core/mp/wb`.

## 📋 Обязательные проверки

### 1. 🏗️ Dependency Injection (DI)

**Что проверять:**
- [ ] HTTP клиент (`httpx.AsyncClient`) инжектируется через DI контейнер как Singleton
- [ ] `WBCabinetAccess` передается как параметр, не инжектируется
- [ ] Адаптеры получают зависимости через конструктор
- [ ] Нет прямого создания `httpx.AsyncClient` в бизнес-коде
- [ ] DI контейнер правильно настроен в `containers.py`

**Примеры правильного использования:**
```python
# ✅ Правильно
class PromotionV1Adapter:
    def __init__(self, http_client: httpx.AsyncClient, wb_access: WBCabinetAccess):
        self.http_client = http_client  # Injected Singleton
        self.wb_access = wb_access      # Passed parameter

# ❌ Неправильно
class BadAdapter:
    def __init__(self, wb_access: WBCabinetAccess):
        self.http_client = httpx.AsyncClient()  # Direct creation
```

### 2. 💾 Кеширование адаптеров (LRU Cache)

**Что проверять:**
- [ ] Адаптеры кешируются по ключу `{domain}_{version}`
- [ ] Кеш очищается при смене версий API
- [ ] `clear_adapters_cache()` работает корректно
- [ ] `_clear_domain_cache()` очищает только нужный домен
- [ ] Нет утечек памяти в кеше

**Проверка кеширования:**
```python
# ✅ Правильное кеширование
def _get_adapter(self, domain: str) -> Any:
    domain_version = self._domain_versions.get(domain, self.api_version)
    cache_key = f"{domain}_{domain_version}"
    
    if cache_key in self._adapters_cache:
        return self._adapters_cache[cache_key]  # Из кеша
    
    adapter = self._create_domain_adapter(domain, domain_version)
    self._adapters_cache[cache_key] = adapter
    return adapter
```

### 3. 📝 Логирование с контекстными полями

**Что проверять:**
- [ ] Все логи содержат `shop_id` для идентификации магазина
- [ ] Логи ошибок содержат `adv_id` для идентификации кампании
- [ ] Используется структурированное логирование
- [ ] Логи содержат достаточно контекста для debugging
- [ ] Нет логирования чувствительных данных (токены, пароли)

**Примеры правильного логирования:**
```python
# ✅ Правильно - с контекстом
logger.error(
    f"[{self.shop_id}] [{adv_setting.adv_id}] Ошибка получения минимальных ставок CPM: {e}",
    exc_info=True
)

# ❌ Неправильно - без контекста
logger.error(f"Error: {e}")
```

### 4. 🔄 Async/Await паттерны

**Что проверять:**
- [ ] Все внешние вызовы (HTTP, DB) используют `async/await`
- [ ] Нет блокирующих операций в async функциях
- [ ] Правильное использование `AsyncMock` в тестах
- [ ] `httpx.AsyncClient` используется корректно
- [ ] Нет `asyncio.run()` внутри async функций

**Правильные async паттерны:**
```python
# ✅ Правильно
async def get_min_cpms_for_adv_setting(self, adv_setting: AdvSetting) -> Dict[int, float]:
    adapter = self._get_adapter("promotion")
    response = await adapter.get_min_bids(...)  # await для HTTP вызова
    return self._process_response(response)

# ❌ Неправильно
def sync_method(self):
    response = requests.get(url)  # Блокирующий вызов
```

### 5. 🎯 Типизация и Type Hints

**Что проверять:**
- [ ] Все публичные методы имеют type hints
- [ ] Возвращаемые типы указаны корректно
- [ ] Используются Generic типы где необходимо
- [ ] `mypy` проходит без ошибок
- [ ] Импорты типов правильные (`from typing import ...`)

**Примеры правильной типизации:**
```python
# ✅ Правильно
async def get_min_cpms_for_adv_setting(
    self, 
    adv_setting: AdvSetting
) -> Dict[int, float]:
    ...

# ❌ Неправильно - нет типов
async def get_data(self, setting):
    ...
```

### 6. ⚠️ Обработка исключений

**Что проверять:**
- [ ] Используются кастомные исключения модуля (`WBApiError`, etc.)
- [ ] HTTP ошибки правильно мапятся на доменные исключения
- [ ] Исключения содержат достаточно информации для debugging
- [ ] `try/except` блоки не слишком широкие
- [ ] Исключения логируются с контекстом

**Правильная обработка ошибок:**
```python
# ✅ Правильно
try:
    response = await adapter.get_min_bids(...)
except httpx.HTTPStatusError as e:
    if e.response.status_code == 403:
        raise WBApiForbiddenError("Доступ запрещен", e.response.text)
    elif e.response.status_code == 429:
        raise WBApiTooManyRequestsError("Превышен лимит запросов")
    else:
        raise WBApiHttpError(f"HTTP error: {e}", e.response.status_code)
```

### 7. 🔄 Версионирование API

**Что проверять:**
- [ ] Версии API управляются через `WBApiVersionConfig`
- [ ] Поддержка динамического переключения версий
- [ ] Версии доменов независимы друг от друга
- [ ] Обратная совместимость при смене версий
- [ ] Корректная обработка неподдерживаемых версий

**Проверка версионирования:**
```python
# ✅ Правильно
def _get_adapter(self, domain: str) -> Any:
    domain_version = self._domain_versions.get(domain, self.api_version)
    return self._create_domain_adapter(domain, domain_version)

# ✅ Правильная обработка ошибок версий
if version not in SUPPORTED_VERSIONS:
    raise WBApiVersionError(f"Unsupported {domain} API version: {version}")
```

### 8. 🧪 Тестируемость кода

**Что проверять:**
- [ ] Код легко мокается для unit тестов
- [ ] Зависимости инжектируются (не создаются внутри)
- [ ] Методы имеют единую ответственность
- [ ] Нет прямых вызовов внешних сервисов без абстракции
- [ ] Тесты покрывают основные сценарии и edge cases

**Тестируемый код:**
```python
# ✅ Тестируемо - зависимости инжектируются
class CPMUpdateMixin:
    async def get_min_cpms(self, adv_setting: AdvSetting):
        adapter = self._get_adapter("promotion")  # Mockable
        return await adapter.get_min_bids(...)

# ❌ Сложно тестировать - прямые зависимости
class BadMixin:
    async def get_min_cpms(self, adv_setting: AdvSetting):
        client = httpx.AsyncClient()  # Hard to mock
        response = await client.get(...)
```

### 9. 🏛️ Архитектурные принципы

**Что проверять:**
- [ ] Соблюдение принципа единой ответственности (SRP)
- [ ] Миксины содержат только бизнес-логику
- [ ] Адаптеры изолируют generated код от бизнес-логики
- [ ] Нет циклических зависимостей
- [ ] Четкое разделение слоев (business → adapter → generated)

**Архитектурные слои:**
```
Business Logic (Mixins) 
    ↓
Adapters (Version abstraction)
    ↓  
Generated Clients (WB API)
```

### 10. 📊 Производительность и ресурсы

**Что проверять:**
- [ ] HTTP connections переиспользуются (connection pooling)
- [ ] Нет создания множественных HTTP клиентов
- [ ] Кеш адаптеров не растет бесконечно
- [ ] Async операции не блокируют event loop
- [ ] Нет memory leaks в долгоживущих объектах

**Проверка ресурсов:**
```python
# ✅ Правильно - Singleton HTTP client
container.http_client = providers.Singleton(
    httpx.AsyncClient,
    timeout=httpx.Timeout(30.0),
    limits=httpx.Limits(max_keepalive_connections=20)
)

# ❌ Неправильно - новый клиент каждый раз
def get_data(self):
    client = httpx.AsyncClient()  # Resource leak
```

## 🔧 Дополнительные проверки

### Code Style
- [ ] Код соответствует PEP 8
- [ ] `ruff` проходит без ошибок
- [ ] Docstrings для публичных методов
- [ ] Комментарии на русском языке (согласно проекту)

### Security
- [ ] Токены не логируются
- [ ] Нет hardcoded credentials
- [ ] Валидация входных данных
- [ ] Безопасная обработка HTTP ответов

### Documentation
- [ ] README обновлен при изменении API
- [ ] CHANGELOG содержит описание изменений
- [ ] Примеры кода актуальны
- [ ] Комментарии в коде понятны

## ✅ Чеклист для reviewer'а

Перед approve PR убедитесь:

- [ ] Все 10 основных пунктов проверены
- [ ] CI/CD pipeline проходит успешно
- [ ] Code coverage не снизился
- [ ] Нет breaking changes без migration guide
- [ ] Документация обновлена
- [ ] Тесты покрывают новую функциональность

## 🚨 Red Flags - Что должно вызвать вопросы

- ❌ Создание `httpx.AsyncClient` в бизнес-коде
- ❌ Отсутствие обработки ошибок в HTTP вызовах  
- ❌ Синхронные вызовы в async методах
- ❌ Логи без `shop_id` контекста
- ❌ Прямое использование generated клиентов в миксинах
- ❌ Отсутствие тестов для новой функциональности
- ❌ Нарушение архитектурных слоев
- ❌ Утечки памяти в кеше
- ❌ Hardcoded версии API
- ❌ Блокирующие операции в async коде

---

**Помните**: Этот чеклист помогает поддерживать высокое качество кода и архитектурную целостность модуля. При сомнениях лучше задать вопрос, чем пропустить потенциальную проблему.
