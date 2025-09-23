# Инструкции по запуску Word2Vec gRPC сервиса

## Быстрый старт

### 1. Установка зависимостей
```bash
# Активируйте виртуальное окружение
.venv\Scripts\Activate.ps1

# Установите зависимости (если не установлены)
pip install grpcio grpcio-tools gensim numpy
```

### 2. Генерация proto артефактов
```bash
cd app/modules/word2vec_service
python generate_proto.py
```

### 3. Запуск сервера
```bash
# Из корневой директории проекта
python -m app.modules.word2vec_service.server --host 0.0.0.0 --port 50051
```

### 4. Тестирование клиента
```bash
# В отдельном терминале
python app/modules/word2vec_service/test_service.py
```

## Структура созданного модуля

```
app/modules/word2vec_service/
├── __init__.py                 # Основные экспорты
├── word2vec.py                 # Класс Word2Vec с методом average_vector_from_sentence
├── service_impl.py             # Реализация gRPC сервиса
├── server.py                   # gRPC сервер с предзагрузкой модели
├── generate_proto.py           # Скрипт генерации proto артефактов
├── test_service.py             # Тестовый скрипт
├── README.md                   # Подробная документация
├── INSTRUCTIONS.md             # Данные инструкции
├── protos/
│   └── word2vec.proto          # Proto контракт
├── grpc_service/
│   ├── word2vec_pb2.py         # Сгенерированные proto классы
│   └── word2vec_pb2_grpc.py    # Сгенерированные gRPC классы
└── word2vec_client/
    └── client.py               # Асинхронный клиент
```

## API контракт

### Новый API
- get_vector_from_word (gRPC, только одно слово)
- get_phrase_data (клиент, фраза -> список слов с векторами + усредненный вектор)

## Использование клиента

```python
import asyncio
from app.modules.word2vec_service import Word2VecClient

async def main():
    async with Word2VecClient("localhost", 50051) as client:
        vector = await client.get_vector("example phrase")
        print(f"Vector: {vector}")

asyncio.run(main())
```

## Особенности реализации

1. **Предзагрузка модели**: Модель Word2Vec загружается при старте сервера
2. **Автоматическое скачивание**: При отсутствии модели она автоматически скачивается
3. **Асинхронность**: Полностью асинхронный API на основе grpc.aio
4. **Валидация**: Проверка входных данных на стороне сервера
5. **Обработка ошибок**: Корректная обработка gRPC ошибок

## Коды ошибок

- `INVALID_ARGUMENT`: Пустая или содержащая только пробелы фраза
- `INTERNAL`: Внутренняя ошибка сервера

## Логирование

Сервер выводит подробные логи:
- INFO: Старт/загрузка модели
- WARNING: Вектор не найден (found=false)
- ERROR: Исключения и ошибки
