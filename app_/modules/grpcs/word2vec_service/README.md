# Word2Vec gRPC Service

Микросервис для получения векторов Word2Vec через gRPC API.

## Структура модуля

```
app/modules/word2vec_service/
├── __init__.py                 # Основные экспорты модуля
├── word2vec.py                 # Класс Word2Vec с методом average_vector_from_sentence
├── service_impl.py             # Реализация gRPC сервиса
├── server.py                   # gRPC сервер с предзагрузкой модели
├── generate_proto.py           # Скрипт генерации proto артефактов
├── README.md                   # Документация
├── protos/
│   ├── __init__.py
│   └── word2vec.proto          # Proto контракт
├── grpc_service/
│   ├── __init__.py
│   ├── word2vec_pb2.py         # Сгенерированные proto классы
│   └── word2vec_pb2_grpc.py    # Сгенерированные gRPC классы
└── word2vec_client/
    ├── __init__.py
    └── client.py               # Асинхронный клиент
```

## Установка зависимостей

```bash
pip install grpcio grpcio-tools gensim numpy
```

## Генерация proto артефактов

Перед первым запуском необходимо сгенерировать Python файлы из proto:

```bash
cd app/modules/word2vec_service
python generate_proto.py
```

## Запуск сервера

```bash
python -m app.modules.word2vec_service.server --host 0.0.0.0 --port 50051
```

### Параметры запуска

- `--host`: Хост для привязки сервера (по умолчанию: 0.0.0.0)
- `--port`: Порт для привязки сервера (по умолчанию: 50051)

## Использование клиента

```python
import asyncio
from app.modules.word2vec_service import Word2VecClient

async def main():
    async with Word2VecClient("localhost", 50051) as client:
        vector = await client._get_word_vector("машина")
        print(vector)

asyncio.run(main())
```

Пример получения объекта для Neo4j:

```python
async with Word2VecClient("localhost", 50051) as client:
    phrase_data = await client.get_phrase_data("машинное обучение")
    print(phrase_data)
```

## API

### gRPC Service: Word2VecGetter

#### Метод: get_vector

**Запрос (GetVectorRequest):**
- `phrase` (string): Фраза для векторизации

**Ответ (GetVectorResponse):**
- `vector` (repeated float): Вектор фразы

### Коды ошибок

- `INVALID_ARGUMENT`: Пустая или содержащая только пробелы фраза
- `INTERNAL`: Внутренняя ошибка сервера

## Особенности

1. **Предзагрузка модели**: Модель Word2Vec загружается при старте сервера
2. **Автоматическое скачивание**: При отсутствии модели она автоматически скачивается
3. **Асинхронность**: Полностью асинхронный API на основе grpc.aio
4. **Логирование**: Подробное логирование всех операций
5. **Валидация**: Проверка входных данных на стороне сервера

## Модель Word2Vec

Для тестирования создается простая модель с базовыми словами (100-мерные векторы).
Модель автоматически создается при первом запуске и сохраняется локально.

**Примечание**: Для продакшена рекомендуется заменить тестовую модель на полноценную предобученную модель Google News или другую подходящую модель.

## Тестирование

Сервис был протестирован и работает корректно:
- ✅ Запуск сервера с предзагрузкой модели
- ✅ Получение векторов для существующих фраз
- ✅ Обработка несуществующих фраз (возврат None, False)
- ✅ Валидация входных данных (ValueError для пустых строк)
- ✅ Логирование всех операций
