# Image Vector gRPC Service

Микросервис для извлечения признаковых векторов из изображений с помощью VGG19 через gRPC API.

## Структура модуля

```
app/modules/image_vector_service/
├── __init__.py                 # Основные экспорты модуля
├── vgg_vectorizer.py           # Класс VGGVectorizer с методом get_vector
├── service_impl.py             # Реализация gRPC сервиса
├── server.py                   # gRPC сервер с предзагрузкой модели
├── generate_proto.py           # Скрипт генерации proto артефактов
├── test_service.py             # Тестовый скрипт
├── README.md                   # Документация
├── protos/
│   ├── __init__.py
│   └── image_vector.proto      # Proto контракт
├── grpc_service/
│   ├── __init__.py
│   ├── image_vector_pb2.py     # Сгенерированные proto классы
│   └── image_vector_pb2_grpc.py # Сгенерированные gRPC классы
└── image_vector_client/
    ├── __init__.py
    └── client.py               # Асинхронный клиент
```

## Установка зависимостей

```bash
pip install grpcio grpcio-tools tensorflow keras pillow faiss-cpu numpy
```

## Генерация proto артефактов

Перед первым запуском необходимо сгенерировать Python файлы из proto:

```bash
cd app/modules/image_vector_service
python generate_proto.py
```

## Запуск сервера

```bash
python -m app.modules.image_vector_service.server --host 0.0.0.0 --port 50052
```

### Параметры запуска

- `--host`: Хост для привязки сервера (по умолчанию: 0.0.0.0)
- `--port`: Порт для привязки сервера (по умолчанию: 50052)

## Использование клиента

```python
import asyncio
from app.modules.image_vector_service import ImageVectorClient
import PIL.Image

async def main():
    # Создание клиента
    async with ImageVectorClient("localhost:50052") as client:
        # Загрузка изображения из файла
        image_bytes = ImageVectorClient.from_path("path/to/image.jpg")
        
        # Получение вектора
        vector, found = await client.get_vector(image_bytes, mime="image/jpeg")
        
        if found:
            print(f"Вектор размерности {len(vector)} получен успешно")
        else:
            print("Не удалось извлечь вектор")

# Запуск
asyncio.run(main())
```

## API

### VGGVectorizer

Основной класс для извлечения векторов признаков:

```python
from app.modules.image_vector_service import VGGVectorizer
import PIL.Image

vectorizer = VGGVectorizer()
image = PIL.Image.open("image.jpg")
vector = vectorizer.get_vector(image)  # np.ndarray float32
```

### ImageVectorClient

Асинхронный клиент для gRPC сервиса:

```python
async with ImageVectorClient("localhost:50052") as client:
    # Из PIL изображения
    image_bytes = ImageVectorClient.from_pil(pil_image, format="JPEG")
    vector, found = await client.get_vector(image_bytes)
    
    # Из файла
    image_bytes = ImageVectorClient.from_path("image.jpg")
    vector, found = await client.get_vector(image_bytes)
```

## Тестирование

Запустите тестовый скрипт для проверки работы сервиса:

```bash
# Убедитесь, что сервер запущен
python -m app.modules.image_vector_service.server --port 50052

# В другом терминале запустите тесты
python app/modules/image_vector_service/test_service.py
```

## Особенности реализации

1. **Предзагрузка модели**: VGG19 загружается один раз при старте сервера
2. **L2-нормализация**: Векторы нормализуются с помощью faiss.normalize_L2
3. **Обработка ошибок**: Корректная обработка невалидных изображений
4. **Асинхронность**: Полностью асинхронный gRPC сервер и клиент
5. **Типизация**: Строгая типизация с поддержкой Python 3.11+

## Требования

- Python 3.11+
- TensorFlow/Keras
- PIL/Pillow
- faiss-cpu
- grpcio
- numpy

## Производительность

- Модель VGG19 предзагружается при старте
- Векторы извлекаются с помощью feature extractor (без классификатора)
- Размерность выходного вектора: 25088 (7×7×512)
- Поддержка форматов: JPEG, PNG, WEBP
