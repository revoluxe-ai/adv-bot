# Инструкции по запуску Image Vector gRPC сервиса

## Быстрый старт

### 1. Установка зависимостей
```bash
# Активируйте виртуальное окружение
.venv\Scripts\Activate.ps1

# Установите зависимости (если не установлены)
pip install grpcio grpcio-tools tensorflow keras pillow faiss-cpu numpy
```

### 2. Генерация proto артефактов
```bash
cd app/modules/image_vector_service
python generate_proto.py
```

### 3. Запуск сервера
```bash
# Из корневой директории проекта
python -m app.modules.image_vector_service.server --host 0.0.0.0 --port 50052
```

### 4. Тестирование клиента
```bash
# В отдельном терминале
python app/modules/image_vector_service/quick_test.py
```

## Структура созданного модуля

```
app/modules/image_vector_service/
├── __init__.py                 # Основные экспорты
├── vgg_vectorizer.py           # Класс VGGVectorizer с методом get_vector
├── service_impl.py             # Реализация gRPC сервиса
├── server.py                   # gRPC сервер с предзагрузкой модели
├── generate_proto.py           # Скрипт генерации proto артефактов
├── quick_test.py               # Быстрый тест
├── test_service.py             # Полный набор тестов
├── README.md                   # Подробная документация
├── INSTRUCTIONS.md             # Данные инструкции
├── protos/
│   └── image_vector.proto      # Proto контракт
├── grpc_service/
│   ├── image_vector_pb2.py     # Сгенерированные proto классы
│   └── image_vector_pb2_grpc.py # Сгенерированные gRPC классы
└── image_vector_client/
    └── client.py               # Асинхронный клиент
```

## Примеры использования

### Базовое использование клиента
```python
import asyncio
from app.modules.image_vector_service import ImageVectorClient
import PIL.Image

async def main():
    async with ImageVectorClient("localhost:50052") as client:
        # Из PIL изображения
        image = PIL.Image.open("image.jpg")
        image_bytes = ImageVectorClient.from_pil(image, format="JPEG")
        vector, found = await client.get_vector(image_bytes)
        
        if found:
            print(f"Вектор размерности {len(vector)} получен")

asyncio.run(main())
```

### Прямое использование VGGVectorizer
```python
from app.modules.image_vector_service import VGGVectorizer
import PIL.Image

vectorizer = VGGVectorizer()
image = PIL.Image.open("image.jpg")
vector = vectorizer.get_vector(image)  # np.ndarray float32
print(f"Размерность вектора: {len(vector)}")
```

## Особенности

- **Предзагрузка модели**: VGG19 загружается один раз при старте сервера
- **L2-нормализация**: Векторы нормализуются с помощью faiss.normalize_L2
- **Асинхронность**: Полностью асинхронный gRPC сервер и клиент
- **Обработка ошибок**: Корректная обработка невалидных изображений
- **Размерность вектора**: 25088 (7×7×512) - feature extractor без классификатора

## Требования

- Python 3.11+
- TensorFlow 2.20+
- Keras 3.11+
- PIL/Pillow
- faiss-cpu
- grpcio
- numpy
