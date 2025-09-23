# Примеры использования WB API

Практические примеры использования модуля WB API с подробными объяснениями.

## 📋 Содержание

1. [Получение минимальных ставок](#1-получение-минимальных-ставок)
2. [Обновление CPM ставок](#2-обновление-cpm-ставок)
3. [Смена версии домена](#3-смена-версии-домена)
4. [Дополнительные примеры](#4-дополнительные-примеры)

---

## 1. Получение минимальных ставок

### Базовый пример

```python
import asyncio
from app.core.mp.wb.factory import create_wb_api_client
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.service_manager.services.update_cpm.wb_api import WBApi


async def get_min_bids_example():
    """Пример получения минимальных ставок для кампании."""

    # 1. Подготовка данных
    access = WBCabinetAccess(
        shop_id=12345,
        token="your_wb_token_here"
    )

    adv_setting = AdvSetting(
        adv_id=67890,
        nmids=[123456789, 987654321, 456789123]  # Артикулы товаров
    )

    # 2. Создание WB API клиента
    wb_api = create_wb_api_client(WBApi, access)

    try:
        # 3. Получение минимальных ставок
        min_cpms = await wb_api.get_min_cpms_for_adv_setting(adv_setting)

        # 4. Обработка результата
        if min_cpms:
            print(f"✅ Получены минимальные ставки для {len(min_cpms)} товаров:")
            for nmid, min_cpm in min_cpms.items():
                print(f"  - Артикул {nmid}: {min_cpm} ₽")

            # Найти максимальную минимальную ставку
            max_min_cpm = max(min_cpms.values())
            print(f"📊 Рекомендуемая ставка для кампании: {max_min_cpm} ₽")

        else:
            print("⚠️ Минимальные ставки не получены")

    except Exception as e:
        print(f"❌ Ошибка получения минимальных ставок: {e}")

    return min_cpms


# Запуск примера
if __name__ == "__main__":
    result = asyncio.run(get_min_bids_example())
```

### Расширенный пример с обработкой ошибок

```python
import asyncio
import logging
from typing import Optional, Dict
from app.core.mp.wb.exceptions import WBApiForbiddenError, WBApiTooManyRequestsError, WBApiError

logger = logging.getLogger(__name__)


async def get_min_bids_safe(
        wb_api: WBApi,
        adv_setting: AdvSetting,
        retry_count: int = 3
) -> Optional[Dict[int, float]]:
    """
    Безопасное получение минимальных ставок с обработкой ошибок.
    
    Args:
        wb_api: Клиент WB API
        adv_setting: Настройки рекламной кампании
        retry_count: Количество попыток при ошибках
    
    Returns:
        Словарь {nmid: min_cpm} или None при ошибке
    """
    for attempt in range(retry_count):
        try:
            logger.info(
                f"[{wb_api.shop_id}] Попытка {attempt + 1}: получение минимальных ставок для кампании {adv_setting.adv_id}")

            min_cpms = await wb_api.get_min_cpms_for_adv_setting(adv_setting)

            if min_cpms:
                logger.info(f"[{wb_api.shop_id}] Успешно получены минимальные ставки для {len(min_cpms)} товаров")
                return min_cpms
            else:
                logger.warning(f"[{wb_api.shop_id}] Пустой ответ при получении минимальных ставок")
                return {}

        except WBApiForbiddenError as e:
            logger.error(f"[{wb_api.shop_id}] Доступ запрещен: {e}")
            # При ошибке доступа не повторяем
            return None

        except WBApiTooManyRequestsError as e:
            delay = 2 ** attempt  # Экспоненциальная задержка
            logger.warning(f"[{wb_api.shop_id}] Rate limit, ждем {delay}с: {e}")
            await asyncio.sleep(delay)

        except WBApiError as e:
            logger.error(f"[{wb_api.shop_id}] Ошибка WB API (попытка {attempt + 1}): {e}")
            if attempt == retry_count - 1:
                return None
            await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"[{wb_api.shop_id}] Неожиданная ошибка: {e}", exc_info=True)
            return None

    return None


# Использование
async def example_with_error_handling():
    access = WBCabinetAccess(shop_id=12345, token="token")
    wb_api = create_wb_api_client(WBApi, access)
    adv_setting = AdvSetting(adv_id=67890, nmids=[123456789])

    min_cpms = await get_min_bids_safe(wb_api, adv_setting)

    if min_cpms is not None:
        print(f"Результат: {min_cpms}")
    else:
        print("Не удалось получить минимальные ставки")
```

---

## 2. Обновление CPM ставок

### Базовый пример

```python
async def update_cpms_example():
    """Пример обновления CPM ставок для кампании."""

    # 1. Подготовка данных
    access = WBCabinetAccess(
        shop_id=12345,
        token="your_wb_token_here"
    )

    adv_setting = AdvSetting(
        adv_id=67890,
        nmids=[123456789, 987654321, 456789123]
    )

    # Новые ставки для каждого товара
    new_bids = {
        123456789: 50.0,  # 50 рублей за клик
        987654321: 75.0,  # 75 рублей за клик  
        456789123: 60.0  # 60 рублей за клик
    }

    # 2. Создание клиента
    wb_api = create_wb_api_client(WBApi, access)

    try:
        # 3. Обновление ставок
        success = await wb_api.update_cpms_for_adv_setting(adv_setting, new_bids)

        if success:
            print(f"✅ Успешно обновлены ставки для {len(new_bids)} товаров")
            for nmid, bid in new_bids.items():
                print(f"  - Артикул {nmid}: {bid} ₽")
        else:
            print("❌ Не удалось обновить ставки")

    except Exception as e:
        print(f"❌ Ошибка обновления ставок: {e}")

    return success


# Запуск
result = asyncio.run(update_cpms_example())
```

### Умное обновление с учетом минимальных ставок

```python
async def smart_update_cpms(
        wb_api: WBApi,
        adv_setting: AdvSetting,
        target_bid: float,
        margin_percent: float = 10.0
) -> bool:
    """
    Умное обновление ставок с учетом минимальных значений.
    
    Args:
        wb_api: Клиент WB API
        adv_setting: Настройки кампании
        target_bid: Целевая ставка
        margin_percent: Процент запаса над минимальной ставкой
    
    Returns:
        True если обновление успешно
    """
    try:
        # 1. Получаем минимальные ставки
        logger.info(f"[{wb_api.shop_id}] Получение минимальных ставок для кампании {adv_setting.adv_id}")
        min_cpms = await wb_api.get_min_cpms_for_adv_setting(adv_setting)

        if not min_cpms:
            logger.warning(f"[{wb_api.shop_id}] Не удалось получить минимальные ставки")
            return False

        # 2. Рассчитываем новые ставки
        new_bids = {}
        for nmid, min_cpm in min_cpms.items():
            # Минимальная ставка + запас
            min_with_margin = min_cpm * (1 + margin_percent / 100)

            # Выбираем максимум из целевой ставки и минимальной с запасом
            final_bid = max(target_bid, min_with_margin)
            new_bids[nmid] = round(final_bid, 2)

        logger.info(f"[{wb_api.shop_id}] Рассчитаны новые ставки:")
        for nmid, bid in new_bids.items():
            min_cpm = min_cpms[nmid]
            logger.info(f"  - Артикул {nmid}: {bid} ₽ (мин: {min_cpm} ₽)")

        # 3. Обновляем ставки
        success = await wb_api.update_cpms_for_adv_setting(adv_setting, new_bids)

        if success:
            logger.info(f"[{wb_api.shop_id}] Успешно обновлены ставки для {len(new_bids)} товаров")
        else:
            logger.error(f"[{wb_api.shop_id}] Не удалось обновить ставки")

        return success

    except Exception as e:
        logger.error(f"[{wb_api.shop_id}] Ошибка умного обновления ставок: {e}", exc_info=True)
        return False


# Пример использования
async def example_smart_update():
    access = WBCabinetAccess(shop_id=12345, token="token")
    wb_api = create_wb_api_client(WBApi, access)
    adv_setting = AdvSetting(adv_id=67890, nmids=[123456789, 987654321])

    # Устанавливаем целевую ставку 100 рублей с запасом 15% над минимумом
    success = await smart_update_cpms(wb_api, adv_setting, 100.0, 15.0)

    if success:
        print("Ставки успешно обновлены")
    else:
        print("Не удалось обновить ставки")
```

### Массовое обновление нескольких кампаний

```python
async def batch_update_campaigns(
        wb_api: WBApi,
        campaigns: List[AdvSetting],
        bid_strategy: Dict[int, float]  # {adv_id: target_bid}
) -> Dict[int, bool]:
    """
    Массовое обновление ставок для нескольких кампаний.
    
    Args:
        wb_api: Клиент WB API
        campaigns: Список настроек кампаний
        bid_strategy: Стратегия ставок {adv_id: target_bid}
    
    Returns:
        Результаты обновления {adv_id: success}
    """
    results = {}

    for adv_setting in campaigns:
        adv_id = adv_setting.adv_id
        target_bid = bid_strategy.get(adv_id, 50.0)  # Дефолтная ставка

        try:
            logger.info(f"[{wb_api.shop_id}] Обновление кампании {adv_id}, целевая ставка: {target_bid}")

            success = await smart_update_cpms(wb_api, adv_setting, target_bid)
            results[adv_id] = success

            # Задержка между кампаниями для избежания rate limit
            await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"[{wb_api.shop_id}] Ошибка обновления кампании {adv_id}: {e}")
            results[adv_id] = False

    return results


# Пример использования
async def example_batch_update():
    access = WBCabinetAccess(shop_id=12345, token="token")
    wb_api = create_wb_api_client(WBApi, access)

    campaigns = [
        AdvSetting(adv_id=111, nmids=[123456789]),
        AdvSetting(adv_id=222, nmids=[987654321]),
        AdvSetting(adv_id=333, nmids=[456789123])
    ]

    bid_strategy = {
        111: 80.0,  # Кампания 111 - 80 рублей
        222: 120.0,  # Кампания 222 - 120 рублей  
        333: 60.0  # Кампания 333 - 60 рублей
    }

    results = await batch_update_campaigns(wb_api, campaigns, bid_strategy)

    print("Результаты обновления:")
    for adv_id, success in results.items():
        status = "✅" if success else "❌"
        print(f"{status} Кампания {adv_id}: {'успех' if success else 'ошибка'}")
```

---

## 3. Смена версии домена

### Глобальная смена версии

```python
from app.settings.wb_api import WBApiVersionConfig


def change_global_api_version():
    """Пример изменения версии API глобально."""

    # 1. Проверяем текущие версии
    current_versions = WBApiVersionConfig.get_versions()
    print("Текущие версии API:")
    for domain, version in current_versions.items():
        print(f"  - {domain}: {version}")

    # 2. Обновляем версию для домена promotion
    print("\n🔄 Обновляем Promotion API с v1 на v2...")
    WBApiVersionConfig.update_version('promotion', 'v2')

    # 3. Проверяем обновленные версии
    updated_versions = WBApiVersionConfig.get_versions()
    print("\nОбновленные версии API:")
    for domain, version in updated_versions.items():
        print(f"  - {domain}: {version}")

    print("\n✅ Версия API успешно обновлена!")


# Запуск
change_global_api_version()
```

### Смена версии для конкретного клиента

```python
async def change_client_api_version():
    """Пример изменения версии API для конкретного клиента."""

    # 1. Создаем клиент
    access = WBCabinetAccess(shop_id=12345, token="token")
    wb_api = create_wb_api_client(WBApi, access)

    # 2. Проверяем текущую версию (через внутренние методы)
    print("Текущие версии клиента:")
    for domain, version in wb_api._domain_versions.items():
        print(f"  - {domain}: {version}")

    # 3. Меняем версию для конкретного домена
    print("\n🔄 Переключаем Promotion API на v2 для этого клиента...")
    wb_api.set_domain_version('promotion', 'v2')

    # 4. Проверяем обновленные версии
    print("\nОбновленные версии клиента:")
    for domain, version in wb_api._domain_versions.items():
        print(f"  - {domain}: {version}")

    # 5. Тестируем работу с новой версией
    try:
        adv_setting = AdvSetting(adv_id=67890, nmids=[123456789])
        min_cpms = await wb_api.get_min_cpms_for_adv_setting(adv_setting)

        if min_cpms:
            print(f"\n✅ API v2 работает! Получены данные для {len(min_cpms)} товаров")
        else:
            print("\n⚠️ API v2 вернул пустой результат")

    except Exception as e:
        print(f"\n❌ Ошибка при работе с API v2: {e}")

        # Откатываемся на v1
        print("🔄 Откатываемся на v1...")
        wb_api.set_domain_version('promotion', 'v1')


# Запуск
asyncio.run(change_client_api_version())
```

### Автоматическое переключение версий

```python
async def auto_version_switching(wb_api: WBApi, adv_setting: AdvSetting):
    """
    Автоматическое переключение версий API при ошибках.
    
    Args:
        wb_api: Клиент WB API
        adv_setting: Настройки кампании
    
    Returns:
        Результат выполнения операции
    """
    # Список версий для попыток (от новой к старой)
    versions_to_try = ['v2', 'v1']

    for version in versions_to_try:
        try:
            logger.info(f"[{wb_api.shop_id}] Попытка использовать Promotion API {version}")

            # Устанавливаем версию
            wb_api.set_domain_version('promotion', version)

            # Пробуем выполнить операцию
            min_cpms = await wb_api.get_min_cpms_for_adv_setting(adv_setting)

            if min_cpms:
                logger.info(f"[{wb_api.shop_id}] Успешно использован API {version}")
                return min_cpms

        except WBApiVersionError as e:
            logger.warning(f"[{wb_api.shop_id}] API {version} не поддерживается: {e}")
            continue

        except Exception as e:
            logger.error(f"[{wb_api.shop_id}] Ошибка API {version}: {e}")
            continue

    logger.error(f"[{wb_api.shop_id}] Все версии API не работают")
    return None


# Пример использования
async def example_auto_switching():
    access = WBCabinetAccess(shop_id=12345, token="token")
    wb_api = create_wb_api_client(WBApi, access)
    adv_setting = AdvSetting(adv_id=67890, nmids=[123456789])

    result = await auto_version_switching(wb_api, adv_setting)

    if result:
        print(f"Получены данные: {result}")
    else:
        print("Не удалось получить данные ни с одной версией API")
```

### Тестирование совместимости версий

```python
async def test_api_versions_compatibility(wb_api: WBApi):
    """
    Тестирование совместимости разных версий API.
    
    Args:
        wb_api: Клиент WB API
    """
    test_adv_setting = AdvSetting(adv_id=67890, nmids=[123456789])
    versions_to_test = ['v1', 'v2']

    compatibility_results = {}

    for version in versions_to_test:
        try:
            logger.info(f"Тестирование API {version}...")

            # Устанавливаем версию
            wb_api.set_domain_version('promotion', version)

            # Тестируем основные методы
            tests = {
                'get_min_cpms': lambda: wb_api.get_min_cpms_for_adv_setting(test_adv_setting),
                'update_cpms': lambda: wb_api.update_cpms_for_adv_setting(
                    test_adv_setting, {123456789: 50.0}
                )
            }

            version_results = {}

            for test_name, test_func in tests.items():
                try:
                    result = await test_func()
                    version_results[test_name] = {
                        'success': True,
                        'result': result
                    }
                    logger.info(f"  ✅ {test_name}: успех")

                except Exception as e:
                    version_results[test_name] = {
                        'success': False,
                        'error': str(e)
                    }
                    logger.error(f"  ❌ {test_name}: {e}")

            compatibility_results[version] = version_results

        except Exception as e:
            logger.error(f"Критическая ошибка при тестировании {version}: {e}")
            compatibility_results[version] = {'error': str(e)}

    # Выводим результаты
    print("\n📊 Результаты тестирования совместимости:")
    for version, results in compatibility_results.items():
        print(f"\n🔹 API {version}:")

        if 'error' in results:
            print(f"  ❌ Критическая ошибка: {results['error']}")
            continue

        for test_name, test_result in results.items():
            status = "✅" if test_result['success'] else "❌"
            print(f"  {status} {test_name}")

            if not test_result['success']:
                print(f"      Ошибка: {test_result['error']}")

    return compatibility_results


# Запуск тестирования
async def run_compatibility_test():
    access = WBCabinetAccess(shop_id=12345, token="token")
    wb_api = create_wb_api_client(WBApi, access)

    results = await test_api_versions_compatibility(wb_api)

    # Определяем рекомендуемую версию
    recommended_version = None
    for version, results in results.items():
        if all(test['success'] for test in results.values() if 'success' in test):
            recommended_version = version
            break

    if recommended_version:
        print(f"\n🎯 Рекомендуемая версия: {recommended_version}")
        WBApiVersionConfig.update_version('promotion', recommended_version)
        print("Версия автоматически установлена в конфигурации")
    else:
        print("\n⚠️ Ни одна версия не прошла все тесты")
```

---

## 4. Дополнительные примеры

### Создание собственного миксина

```python
# app/core/mp/wb/mixins/analytics_mixin.py
from typing import TYPE_CHECKING, Dict, List
import logging

if TYPE_CHECKING:
    from ..base_wb_api import BaseWBApi

logger = logging.getLogger(__name__)


class AnalyticsMixin:
    """Миксин для аналитики кампаний."""

    async def get_campaign_analytics(
            self: 'BaseWBApi',
            adv_setting: AdvSetting,
            days: int = 7
    ) -> Dict:
        """Получить аналитику по кампании за указанный период."""
        try:
            adapter = self._get_adapter("statistics")

            analytics = await adapter.get_campaign_stats(
                advert_id=adv_setting.adv_id,
                days=days
            )

            logger.info(f"[{self.shop_id}] Получена аналитика кампании {adv_setting.adv_id}")
            return analytics

        except Exception as e:
            logger.error(f"[{self.shop_id}] Ошибка получения аналитики: {e}")
            raise


# Использование в клиенте
class AdvancedWBApi(AnalyticsMixin, mixins.CPMUpdateMixin, BaseWBApi):
    """Продвинутый клиент с аналитикой."""
    pass


# Пример использования
async def analytics_example():
    access = WBCabinetAccess(shop_id=12345, token="token")
    wb_api = create_wb_api_client(AdvancedWBApi, access)

    adv_setting = AdvSetting(adv_id=67890, nmids=[123456789])

    analytics = await wb_api.get_campaign_analytics(adv_setting, days=14)
    print(f"Аналитика за 14 дней: {analytics}")
```

### Кеширование результатов

```python
import asyncio
from datetime import datetime, timedelta
from typing import Optional


class CachedWBApiManager:
    """Менеджер с кешированием результатов WB API."""

    def __init__(self, wb_api: WBApi):
        self.wb_api = wb_api
        self._min_cpms_cache = {}
        self._cache_ttl = timedelta(minutes=5)  # TTL кеша 5 минут

    async def get_min_cpms_cached(self, adv_setting: AdvSetting) -> Optional[Dict[int, float]]:
        """Получить минимальные ставки с кешированием."""
        cache_key = f"{adv_setting.adv_id}:{hash(tuple(adv_setting.nmids))}"

        # Проверяем кеш
        if cache_key in self._min_cpms_cache:
            cached_data, cached_time = self._min_cpms_cache[cache_key]

            if datetime.utcnow() - cached_time < self._cache_ttl:
                logger.info(f"[{self.wb_api.shop_id}] Используем кешированные данные для кампании {adv_setting.adv_id}")
                return cached_data

        # Получаем свежие данные
        try:
            min_cpms = await self.wb_api.get_min_cpms_for_adv_setting(adv_setting)

            # Сохраняем в кеш
            self._min_cpms_cache[cache_key] = (min_cpms, datetime.utcnow())

            logger.info(
                f"[{self.wb_api.shop_id}] Получены и закешированы минимальные ставки для кампании {adv_setting.adv_id}")
            return min_cpms

        except Exception as e:
            logger.error(f"[{self.wb_api.shop_id}] Ошибка получения минимальных ставок: {e}")
            return None

    def clear_cache(self):
        """Очистить кеш."""
        self._min_cpms_cache.clear()
        logger.info(f"[{self.wb_api.shop_id}] Кеш очищен")


# Пример использования
async def cached_example():
    access = WBCabinetAccess(shop_id=12345, token="token")
    wb_api = create_wb_api_client(WBApi, access)
    cached_manager = CachedWBApiManager(wb_api)

    adv_setting = AdvSetting(adv_id=67890, nmids=[123456789])

    # Первый вызов - данные получаются из API
    min_cpms1 = await cached_manager.get_min_cpms_cached(adv_setting)
    print(f"Первый вызов: {min_cpms1}")

    # Второй вызов - данные берутся из кеша
    min_cpms2 = await cached_manager.get_min_cpms_cached(adv_setting)
    print(f"Второй вызов (из кеша): {min_cpms2}")
```

### Мониторинг производительности

```python
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class PerformanceMetric:
    operation: str
    duration: float
    success: bool
    timestamp: datetime


class WBApiPerformanceMonitor:
    """Монитор производительности WB API."""

    def __init__(self):
        self.metrics: List[PerformanceMetric] = []

    @asynccontextmanager
    async def measure_operation(self, operation_name: str):
        """Контекстный менеджер для измерения времени операции."""
        start_time = time.time()
        success = False

        try:
            yield
            success = True
        finally:
            duration = time.time() - start_time

            metric = PerformanceMetric(
                operation=operation_name,
                duration=duration,
                success=success,
                timestamp=datetime.utcnow()
            )

            self.metrics.append(metric)
            logger.info(f"Операция {operation_name}: {duration:.2f}с, успех: {success}")

    def get_average_duration(self, operation: str) -> float:
        """Получить среднее время выполнения операции."""
        relevant_metrics = [m for m in self.metrics if m.operation == operation and m.success]

        if not relevant_metrics:
            return 0.0

        return sum(m.duration for m in relevant_metrics) / len(relevant_metrics)

    def get_success_rate(self, operation: str) -> float:
        """Получить процент успешных операций."""
        relevant_metrics = [m for m in self.metrics if m.operation == operation]

        if not relevant_metrics:
            return 0.0

        successful = sum(1 for m in relevant_metrics if m.success)
        return (successful / len(relevant_metrics)) * 100


# Пример использования
async def performance_monitoring_example():
    access = WBCabinetAccess(shop_id=12345, token="token")
    wb_api = create_wb_api_client(WBApi, access)
    monitor = WBApiPerformanceMonitor()

    adv_setting = AdvSetting(adv_id=67890, nmids=[123456789])

    # Выполняем операции с мониторингом
    async with monitor.measure_operation("get_min_cpms"):
        min_cpms = await wb_api.get_min_cpms_for_adv_setting(adv_setting)

    async with monitor.measure_operation("update_cpms"):
        success = await wb_api.update_cpms_for_adv_setting(adv_setting, {123456789: 50.0})

    # Получаем статистику
    avg_duration = monitor.get_average_duration("get_min_cpms")
    success_rate = monitor.get_success_rate("get_min_cpms")

    print(f"Среднее время получения минимальных ставок: {avg_duration:.2f}с")
    print(f"Процент успешных операций: {success_rate:.1f}%")
```

---

## 🚀 Заключение

Эти примеры показывают основные сценарии использования модуля WB API:

1. **Получение минимальных ставок** - с обработкой ошибок и retry логикой
2. **Обновление CPM ставок** - умное обновление с учетом минимумов
3. **Смена версии домена** - глобально и для конкретных клиентов
4. **Дополнительные возможности** - кеширование, мониторинг, собственные миксины

Для более подробной информации смотрите:

- [README.md](./README.md) - общий обзор модуля
- [ERRORS.md](./ERRORS.md) - обработка ошибок и исключений
