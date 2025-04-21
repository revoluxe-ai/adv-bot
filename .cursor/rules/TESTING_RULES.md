# Правила тестирования проекта

## Основные принципы
1. Каждый тест должен быть независимым и изолированным
2. Следовать принципу AAA (Arrange-Act-Assert)
3. Использовать говорящие имена тестов
4. Тестировать один аспект функциональности за раз
5. ЗАПРЕЩЕНО изменять код приложения при написании тестов
6. Каждый новый функционал должен быть покрыт тестами
7. При обнаружении ошибки сначала писать тест, воспроизводящий ее, затем исправлять

## Структура проекта тестов
```
tests/
├── conftest.py              # Общие фикстуры и моки
├── pytest.ini              # Конфигурация pytest
├── mocks.py               # Базовые классы моков
├── test_process_cabinet_api.py  # Тесты API кабинета
└── modules/               # Тесты отдельных модулей
    ├── test_wb_keywords_parser.py
    ├── test_wb_adv_updater.py
    └── ...
```

## Конвенции именования
- Файлы тестов: `test_*.py`
- Функции тестов: `test_*`
- Классы тестов: `Test*`
- Фикстуры: существительное, отражающее суть объекта (например, `test_user`, `test_wb_cabinet`)

## Критические области тестирования
1. Telegram бот:
   - Обработка команд
   - FSM состояния
   - Взаимодействие с пользователем
   - Валидация входных данных

2. Wildberries API:
   - Авторизация и токены
   - Работа с кабинетами
   - Парсинг данных
   - Обработка ошибок API

3. База данных:
   - Модели и их взаимосвязи
   - Транзакции
   - Миграции
   - Целостность данных

4. Парсер ключевых слов:
   - Корректность парсинга
   - Обработка ошибок
   - Производительность
   - Валидация данных

## Работа с фикстурами

### Базовые фикстуры
```python
@pytest.fixture
async def test_async_db():
    """Фикстура для создания тестовой базы данных"""
    session = MockAsyncSession()
    yield session

@pytest.fixture
def test_user():
    """Фикстура для создания тестового пользователя"""
    return MockUser(
        id=1,
        user_telegram_id=12345,
        username="test_user"
    )

@pytest.fixture
def test_wb_token():
    """Фикстура для создания тестового токена WB"""
    return MockWBToken(
        id=1,
        api_key="test_api_key",
        shop_id="test_shop_id"
    )
```

### Моки для Telegram
```python
@pytest.fixture
def bot():
    """Создает мок объекта бота"""
    class MockBot:
        async def send_message(self, chat_id: int, text: str, **kwargs):
            self.last_message = {
                "chat_id": chat_id,
                "text": text,
                **kwargs
            }
            return None
    return MockBot()

@pytest.fixture
def state():
    """Создает мок объекта состояния FSM"""
    class MockState:
        def __init__(self):
            self.state_data = {}
            self.current_state = None

        async def get_state(self):
            return self.current_state

        async def set_state(self, new_state=None):
            self.current_state = new_state

        async def get_data(self):
            return self.state_data

        async def update_data(self, **kwargs):
            self.state_data.update(kwargs)
    return MockState()
```

## Примеры тестов

### Тест обработки API кабинета
```python
@pytest.mark.asyncio
async def test_process_cabinet_api(
    test_async_db,
    test_user,
    test_wb_token,
    test_wb_cabinet,
    test_wb_user_cabinet,
    bot,
    state,
    message
):
    """Тестирование обработки API кабинета"""
    # Arrange
    message.text = "test_api_key"
    
    # Act
    result = await process_cabinet_api(message, state, bot)
    
    # Assert
    assert result is not None
    assert test_wb_token.api_key == "test_api_key"
    assert test_wb_cabinet.shop_id == "test_shop_id"
    assert test_wb_user_cabinet.name == "Test Cabinet"
```

## Запуск тестов

### Основные команды
```bash
# Запуск всех тестов
python -m pytest

# Запуск с подробным выводом
python -m pytest -v

# Запуск конкретного теста
python -m pytest tests/test_process_cabinet_api.py::test_function_name

# Запуск с выводом print-сообщений
python -m pytest -s

# Запуск тестов по маркерам
python -m pytest -m "asyncio"
```

## Работа с асинхронными тестами

### Настройка pytest.ini
```ini
[pytest]
asyncio_mode = auto
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

### Маркировка асинхронных тестов
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

## Моки и патчи

### Патч внешних зависимостей
```python
@pytest.fixture(autouse=True)
def mock_wb_parser():
    """Мок для парсера WB API"""
    mock_response = {
        'data': {
            'products': [
                {
                    'id': 12345,
                    'log': {
                        'advertId': 'test_adv_id',
                        'cpm': 100,
                        'position': 1
                    }
                }
            ],
            'total': 100
        }
    }
    
    with patch('app.modules.wb_keywords_parser.parser.ParserService', 
              new_callable=AsyncMock) as mock:
        mock.return_value = mock_response
        yield mock
```

## Отладка тестов

### Шаги при падении теста
1. Запустить тест с подробным выводом:
   ```bash
   python -m pytest test_file.py::test_name -vv
   ```
2. Проверить моки и фикстуры
3. Проанализировать стек ошибок
4. Проверить состояние базы данных
5. Логировать промежуточные результаты

### Типичные проблемы и решения
1. Проблемы с асинхронностью:
   - Использовать правильные моки (AsyncMock)
   - Проверить все await выражения
   - Использовать корректные фикстуры

2. Проблемы с базой данных:
   - Проверить транзакции
   - Использовать правильные моки сессий
   - Проверить миграции

3. Проблемы с Telegram API:
   - Проверить моки бота
   - Проверить состояния FSM
   - Валидировать входные данные

## Рекомендации по покрытию кода
1. Стремиться к покрытию >80%
2. Обязательно тестировать:
   - Обработчики команд бота
   - Работу с API Wildberries
   - Критические бизнес-процессы
   - Обработку ошибок
3. Использовать pytest-cov для анализа покрытия 