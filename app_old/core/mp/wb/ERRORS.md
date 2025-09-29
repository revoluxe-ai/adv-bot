# Обработка ошибок WB API

Полная документация по исключениям и их обработке в модуле WB API.

## Иерархия исключений

```
WBApiError (базовое исключение)
├── WBApiHttpError (HTTP ошибки)
│   ├── WBApiForbiddenError (403 Forbidden)
│   └── WBApiTooManyRequestsError (429 Too Many Requests)
├── WBApiValidationError (ошибки валидации)
├── WBApiAdapterError (ошибки адаптера)
└── WBApiVersionError (ошибки версионирования)
```

## Таблица исключений

| Исключение                  | Код        | Описание                      | Причина                                    | Решение                                       |
|-----------------------------|------------|-------------------------------|--------------------------------------------|-----------------------------------------------|
| `WBApiError`                | -          | Базовое исключение модуля     | Любая ошибка в модуле                      | Проверить детали в дочерних исключениях       |
| `WBApiHttpError`            | Любой HTTP | HTTP ошибка при запросе к API | Сетевые проблемы, ошибки сервера           | Проверить статус код и повторить запрос       |
| `WBApiForbiddenError`       | 403        | Доступ запрещен               | Неверный/истекший токен                    | Обновить токен доступа                        |
| `WBApiTooManyRequestsError` | 429        | Превышен лимит запросов       | Слишком частые запросы                     | Добавить задержку, использовать rate limiting |
| `WBApiValidationError`      | -          | Ошибка валидации данных       | Неверные входные параметры                 | Проверить формат данных                       |
| `WBApiAdapterError`         | -          | Ошибка в адаптере             | Проблемы с версией API или generated кодом | Проверить версию API                          |
| `WBApiVersionError`         | -          | Ошибка версионирования        | Неподдерживаемая версия API                | Обновить версию в конфигурации                |

## Обработка ошибок

### 1. Базовая обработка

```python
from app.core.mp.wb.exceptions import WBApiError, WBApiForbiddenError, WBApiTooManyRequestsError


async def safe_wb_api_call():
    try:
        result = await wb_api.get_min_cpms_for_adv_setting(adv_setting)
        return result

    except WBApiForbiddenError as e:
        # Проблемы с доступом - нужно обновить токен
        logger.error(f"Доступ запрещен: {e}")
        await refresh_token()
        return None

    except WBApiTooManyRequestsError as e:
        # Rate limit - добавляем задержку
        logger.warning(f"Превышен лимит запросов: {e}")
        await asyncio.sleep(60)  # Ждем минуту
        return await safe_wb_api_call()  # Повторяем запрос

    except WBApiError as e:
        # Любая другая ошибка модуля
        logger.error(f"Ошибка WB API: {e}")
        return None

    except Exception as e:
        # Неожиданная ошибка
        logger.error(f"Неожиданная ошибка: {e}", exc_info=True)
        return None
```

### 2. Обработка с повторными попытками

```python
import asyncio
from typing import Optional, TypeVar, Callable
from app.core.mp.wb.exceptions import WBApiTooManyRequestsError, WBApiForbiddenError

T = TypeVar('T')


async def retry_wb_api_call(
        func: Callable[[], Awaitable[T]],
        max_retries: int = 3,
        base_delay: float = 1.0
) -> Optional[T]:
    """
    Выполнить WB API вызов с повторными попытками.
    
    Args:
        func: Асинхронная функция для вызова
        max_retries: Максимальное количество попыток
        base_delay: Базовая задержка между попытками
    
    Returns:
        Результат вызова или None при неудаче
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func()

        except WBApiTooManyRequestsError as e:
            # Rate limit - экспоненциальная задержка
            delay = base_delay * (2 ** attempt)
            logger.warning(f"Rate limit (попытка {attempt + 1}), ждем {delay}с")
            await asyncio.sleep(delay)
            last_exception = e

        except WBApiForbiddenError as e:
            # Проблемы с токеном - не повторяем
            logger.error(f"Ошибка доступа: {e}")
            return None

        except WBApiError as e:
            # Другие ошибки API - повторяем с задержкой
            if attempt < max_retries:
                delay = base_delay * (attempt + 1)
                logger.warning(f"Ошибка API (попытка {attempt + 1}), повтор через {delay}с")
                await asyncio.sleep(delay)
            last_exception = e

    logger.error(f"Все попытки исчерпаны. Последняя ошибка: {last_exception}")
    return None


# Использование
result = await retry_wb_api_call(
    lambda: wb_api.get_min_cpms_for_adv_setting(adv_setting),
    max_retries=3,
    base_delay=2.0
)
```

### 3. Контекстный менеджер для обработки ошибок

```python
from contextlib import asynccontextmanager
from app.core.mp.wb.exceptions import WBApiError


@asynccontextmanager
async def wb_api_error_handler(operation_name: str, shop_id: int):
    """
    Контекстный менеджер для обработки ошибок WB API.
    
    Args:
        operation_name: Название операции для логирования
        shop_id: ID магазина для контекста
    """
    try:
        logger.info(f"[{shop_id}] Начало операции: {operation_name}")
        yield
        logger.info(f"[{shop_id}] Операция завершена успешно: {operation_name}")

    except WBApiForbiddenError as e:
        logger.error(f"[{shop_id}] Доступ запрещен в операции {operation_name}: {e}")
        # Можно добавить уведомление администратора
        await notify_token_expired(shop_id)
        raise

    except WBApiTooManyRequestsError as e:
        logger.warning(f"[{shop_id}] Rate limit в операции {operation_name}: {e}")
        raise

    except WBApiError as e:
        logger.error(f"[{shop_id}] Ошибка WB API в операции {operation_name}: {e}")
        raise

    except Exception as e:
        logger.error(f"[{shop_id}] Неожиданная ошибка в операции {operation_name}: {e}", exc_info=True)
        raise


# Использование
async def update_campaign_bids(adv_setting: AdvSetting, new_bids: dict):
    async with wb_api_error_handler("update_campaign_bids", adv_setting.shop_id):
        result = await wb_api.update_cpms_for_adv_setting(adv_setting, new_bids)
        return result
```

### 4. Декоратор для автоматической обработки

```python
from functools import wraps
from app.core.mp.wb.exceptions import WBApiError


def handle_wb_api_errors(operation_name: str = None):
    """
    Декоратор для автоматической обработки ошибок WB API.
    
    Args:
        operation_name: Название операции (по умолчанию - имя функции)
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            op_name = operation_name or func.__name__

            try:
                return await func(*args, **kwargs)

            except WBApiForbiddenError as e:
                logger.error(f"Ошибка доступа в {op_name}: {e}")
                return None

            except WBApiTooManyRequestsError as e:
                logger.warning(f"Rate limit в {op_name}: {e}")
                # Можно добавить автоматическую задержку
                await asyncio.sleep(60)
                return None

            except WBApiError as e:
                logger.error(f"Ошибка WB API в {op_name}: {e}")
                return None

        return wrapper

    return decorator


# Использование
@handle_wb_api_errors("get_min_cpms")
async def get_min_cpms_safe(adv_setting: AdvSetting):
    return await wb_api.get_min_cpms_for_adv_setting(adv_setting)
```

## Логирование ошибок

### Настройка логгера

```python
import logging

# Настройка логгера для WB API
wb_api_logger = logging.getLogger('app.core.mp.wb')
wb_api_logger.setLevel(logging.INFO)

# Форматтер для логов
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(shop_id)s] - %(message)s'
)

# Обработчик для файла
file_handler = logging.FileHandler('legacy-wb_api_clients.log')
file_handler.setFormatter(formatter)
wb_api_logger.addHandler(file_handler)
```

### Структурированное логирование ошибок

```python
def log_wb_api_error(error: WBApiError, context: dict = None):
    """
    Структурированное логирование ошибок WB API.
    
    Args:
        error: Исключение WB API
        context: Дополнительный контекст (shop_id, operation, etc.)
    """
    context = context or {}
    
    log_data = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'shop_id': context.get('shop_id'),
        'operation': context.get('operation'),
        'adv_id': context.get('adv_id'),
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if isinstance(error, WBApiHttpError):
        log_data.update({
            'status_code': error.status_code,
            'response_text': error.response_text[:500] if error.response_text else None
        })
    
    logger.error(f"WB API Error: {log_data}")
```

## Мониторинг и алерты

### Метрики ошибок

```python
from collections import defaultdict
from datetime import datetime, timedelta


class WBApiErrorMonitor:
    """Монитор ошибок WB API."""

    def __init__(self):
        self.error_counts = defaultdict(int)
        self.last_reset = datetime.utcnow()

    def record_error(self, error: WBApiError, shop_id: int):
        """Записать ошибку для мониторинга."""
        error_key = f"{type(error).__name__}:{shop_id}"
        self.error_counts[error_key] += 1

        # Сброс счетчиков каждый час
        if datetime.utcnow() - self.last_reset > timedelta(hours=1):
            self.reset_counters()

    def reset_counters(self):
        """Сбросить счетчики ошибок."""
        self.error_counts.clear()
        self.last_reset = datetime.utcnow()

    def get_error_rate(self, error_type: str, shop_id: int) -> int:
        """Получить количество ошибок за текущий час."""
        error_key = f"{error_type}:{shop_id}"
        return self.error_counts.get(error_key, 0)

    def should_alert(self, error_type: str, shop_id: int, threshold: int = 10) -> bool:
        """Проверить, нужно ли отправлять алерт."""
        return self.get_error_rate(error_type, shop_id) >= threshold


# Глобальный монитор
error_monitor = WBApiErrorMonitor()
```

## FAQ по ошибкам

### Q: Что делать при ошибке 403 Forbidden?

**A:** Проверить токен доступа, возможно он истек или неверный. Обновить токен в настройках магазина.

### Q: Как обработать ошибку 429 Too Many Requests?

**A:** Добавить задержку между запросами. Рекомендуется экспоненциальная задержка: 1с, 2с, 4с, 8с...

### Q: Что означает WBApiVersionError?

**A:** Попытка использовать неподдерживаемую версию API. Проверить конфигурацию версий в `WBApiVersionConfig`.

### Q: Как отладить проблемы с generated клиентом?

**A:** Включить debug логирование для httpx и проверить raw HTTP запросы/ответы.

### Q: Что делать при постоянных ошибках адаптера?

**A:** Проверить соответствие версии API и generated кода. Возможно нужно перегенерировать клиент.

## Примеры кода

Полные примеры обработки ошибок смотрите в [USAGE.md](./USAGE.md).
