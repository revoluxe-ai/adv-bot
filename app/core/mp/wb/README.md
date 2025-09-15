# WB API Module

Современный модуль для работы с API Wildberries с поддержкой версионирования, dependency injection и типизации.

## Overview

Модуль `app/core/mp/wb` представляет собой новую архитектуру для работы с WB API, которая заменяет устаревший
`app/core/wb_api`. Основные преимущества:

### 🚀 Ключевые особенности

- **Версионирование API** - поддержка разных версий API для каждого домена
- **Dependency Injection** - управление зависимостями через DI контейнер
- **Миксины** - гибкое создание специализированных клиентов
- **Типизация** - полная поддержка типов TypeScript-стиля
- **Асинхронность** - все операции выполняются асинхронно
- **Адаптеры** - абстракция над generated клиентами
- **Централизованная конфигурация** - управление версиями через settings

### 🏗️ Архитектура

```
app/core/mp/wb/
├── base_wb_api.py          # Базовый класс WB API
├── mixins/                 # Бизнес-миксины
│   └── cpm_update_mixin.py # Миксин для работы со ставками
├── adapters/               # Адаптеры для разных версий API
│   └── promotion/
│       ├── v1_adapter.py   # Адаптер для Promotion API v1
│       └── factory.py      # Фабрика адаптеров
├── containers.py           # DI контейнер
├── factory.py              # Фабрика клиентов
├── exceptions.py           # Исключения модуля
└── _api_client/           # Generated клиенты из OpenAPI
```

### 🔄 Принцип работы

1. **Бизнес-код** использует утилитарные клиенты (например, `WBApi`)
2. **Утилитарные клиенты** собираются из базового класса и миксинов
3. **Миксины** содержат бизнес-логику и работают с адаптерами
4. **Адаптеры** скрывают различия версий и работают с generated клиентами
5. **Generated клиенты** автоматически созданы из OpenAPI спецификаций

## Installation

### Требования

- Python 3.11+
- Установленные зависимости из `requirements.txt`

### Основные зависимости

```bash
pip install httpx>=0.25.0 pydantic>=2.0.0 dependency-injector>=4.0.0 python-dateutil>=2.8.0 attrs>=23.0.0
```

### Для разработки

```bash
pip install pytest>=7.0.0 pytest-asyncio>=0.21.0 ruff>=0.1.0 mypy>=1.5.0 types-python-dateutil>=2.9.0
```

### Проверка установки

```python
# Проверьте, что все импорты работают
from app.core.mp.wb import BaseWBApi, mixins
from app.core.mp.wb.factory import create_wb_api_client
from app.settings.wb_api import WBApiVersionConfig

print("✅ WB API модуль установлен корректно")
```

## Quick Start

### 1. Создание специализированного клиента

```python
# app/modules/your_module/legacy-wb_api_clients.py
from app.core.mp.wb import BaseWBApi, mixins


class WBApi(mixins.CPMUpdateMixin, BaseWBApi):
    """Специализированный WB API клиент для работы со ставками."""
    pass
```

### 2. Использование в бизнес-логике

```python
# app/modules/your_module/manager.py
from app.core.mp.wb.factory import create_wb_api_client
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from app.modules.common_slaves.wildberries.models import AdvSetting
from .wb_api import WBApi


class YourManager:
    def __init__(self, access: WBCabinetAccess):
        self._shop_id = access.shop_id
        # Создаем WB API клиент через фабрику с DI
        self._wb_api = create_wb_api_client(WBApi, access)

    async def get_min_cpm_for_campaign(self, adv_setting: AdvSetting) -> int:
        """Получить минимальную CPM ставку для кампании."""
        try:
            # Получаем минимальные ставки для всех товаров
            min_cpms = await self._wb_api.get_min_cpms_for_adv_setting(adv_setting)

            if not min_cpms:
                return 1  # Дефолтная ставка

            # Возвращаем максимальную из минимальных ставок
            return max(min_cpms.values())

        except Exception as e:
            print(f"Ошибка получения минимальной ставки: {e}")
            return 1

    async def update_campaign_bids(self, adv_setting: AdvSetting, new_bid: float) -> bool:
        """Обновить ставки для всех товаров в кампании."""
        try:
            # Получаем текущие минимальные ставки
            min_cpms = await self._wb_api.get_min_cpms_for_adv_setting(adv_setting)

            # Создаем новые ставки (не ниже минимальных)
            new_bids = {
                nmid: max(new_bid, min_cpm)
                for nmid, min_cpm in min_cpms.items()
            }

            # Обновляем ставки
            success = await self._wb_api.update_cpms_for_adv_setting(adv_setting, new_bids)

            if success:
                print(f"Успешно обновлены ставки для {len(new_bids)} товаров")

            return success

        except Exception as e:
            print(f"Ошибка обновления ставок: {e}")
            return False
```

### 3. Настройка версий API

```python
# Управление версиями API
from app.settings.wb_api import WBApiVersionConfig

# Получить текущие версии
versions = WBApiVersionConfig.get_versions()
print(versions)  # {'promotion': 'v1', 'media': 'v1', 'statistics': 'v1'}

# Обновить версию для конкретного домена
WBApiVersionConfig.update_version('promotion', 'v2')

# Переключить версию в рантайме для конкретного клиента
wb_api.set_domain_version('promotion', 'v2')
```

### 4. Создание собственных миксинов

```python
# app/core/mp/wb/mixins/my_custom_mixin.py
import logging
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from ..base_wb_api import BaseWBApi

logger = logging.getLogger(__name__)

class MyCustomMixin:
    """Пример создания собственного миксина."""
    
    async def my_custom_method(self: 'BaseWBApi', param: str) -> List[dict]:
        """Пример метода миксина."""
        try:
            # Получаем адаптер для нужного домена
            adapter = self._get_adapter("promotion")
            
            # Вызываем метод адаптера
            result = await adapter.some_method(param=param)
            
            logger.info(f"[{self.shop_id}] Выполнен custom метод")
            return result
            
        except Exception as e:
            logger.error(f"[{self.shop_id}] Ошибка custom метода: {e}")
            raise

# Использование в клиенте
class MyWBApi(MyCustomMixin, mixins.CPMUpdateMixin, BaseWBApi):
    """Клиент с дополнительной функциональностью."""
    pass
```

## Конфигурация

### Настройка версий API

```python
# app/settings/legacy-wb_api_clients.py
class WBApiVersionConfig:
    DOMAIN_VERSIONS: Dict[str, str] = {
        "promotion": "v1",  # Рекламные кампании
        "media": "v1",  # Медиа контент  
        "statistics": "v1",  # Статистика
    }
```

### Настройка HTTP клиента

```python
# app/core/mp/wb/containers.py
http_client = providers.Singleton(
    httpx.AsyncClient,
    timeout=httpx.Timeout(30.0),  # Таймаут запросов
    headers={"User-Agent": "WB-Bot/1.0"},
    limits=httpx.Limits(
        max_keepalive_connections=20,
        max_connections=100
    )
)
```

## Тестирование

```python
import pytest
from app.core.mp.wb.factory import create_wb_api_client
from app.modules.your_module.wb_api import WBApi


@pytest.mark.asyncio
async def test_wb_api_client():
    """Тест создания WB API клиента."""
    # Мокаем access
    mock_access = MockWBCabinetAccess()

    # Создаем клиент
    wb_api = create_wb_api_client(WBApi, mock_access)

    assert wb_api is not None
    assert wb_api.shop_id == mock_access.shop_id
```

### Подмена адаптеров в тестах

В тестах удобно подменять адаптеры через DI контейнер `WBApiDIContainer`.

Пример подмены адаптера в pytest:

```python
from app.core.di.wb_api_clients.wb_api_container import WBApiDIContainer
from app.core.mp.wb.adapters.promotion.v1_adapter import PromotionV1Adapter


def test_with_mock_adapter(monkeypatch):
    container = WBApiDIContainer()

    # Заменяем провайдер адаптера на мок
    container.promotion.v1.adapter.override(lambda: MockPromotionAdapter())

    # В процессе вызовов Provide[...] будет возвращён мок
    wb_api = create_wb_api_client(WBApi, mock_access)
    # Ваши тесты...

    # Сбросить переопределение
    container.promotion.v1.adapter.reset_override()
```

Также доступен `WBApiDIContainer.current_adapter` — alias на текущий адаптер, его удобно подменять целиком.

## Миграция со старого API

Если вы используете старый `app/core/wb_api`, вот как мигрировать:

### Было:

```python
from app.core.wb_api import WBApi

wb_api = WBApi(access)
result = wb_api.get_min_bids(adv_id, nm_ids)
```

### Стало:

```python
from app.core.mp.wb.factory import create_wb_api_client
from your_module.wb_api import WBApi

wb_api = create_wb_api_client(WBApi, access)
result = await wb_api.get_min_cpms_for_adv_setting(adv_setting)
```

## Поддержка

- 📖 Документация: [USAGE.md](./USAGE.md)
- 🐛 Обработка ошибок: [ERRORS.md](./ERRORS.md)
- 🔧 Примеры использования: [examples/](./examples/)

## Лицензия

Внутренний проект компании.
